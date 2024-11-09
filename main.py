import os
import logging
from typing import Dict, Optional, Any, Union, List
from datetime import datetime, timedelta
from transmission_rpc import Client, Torrent
import argparse
import threading
import signal

class TransmissionManager:
    """
    A class to manage Transmission torrents
    """
    def __init__(
        self,
        config: Dict[str, Union[str, int]],
        delay: int,
        sleep_duration: int,
        ratio: Optional[float]
    ) -> None:
        """
        :param config: A dictionary containing Transmission configuration
        :param delay: Delay in minutes before removing completed torrents
        :param sleep_duration: Sleep duration in seconds between checks
        :param ratio: Ratio at which to remove completed torrents
        """
        self.config: Dict[str, Union[str, int]] = config
        self.delay: int = delay
        self.ratio: Optional[float] = ratio
        self.sleep_duration: int = sleep_duration
        self.logger: logging.Logger = self.setup_logger()
        self.client: Optional[Client] = None  # Will be initialized in connect_to_server
        self.connect_to_server()
        self.completed_torrents: Dict[int, datetime] = {}
        self.stop_event: threading.Event = threading.Event()
        
    def connect_to_server(self) -> None:
        try:
            self.client = Client(
                host=str(self.config["host"]),
                port=int(self.config["port"]),
                username=str(self.config["username"]),
                password=str(self.config["password"]),
                protocol=str(self.config.get("protocol", "https" if self.config['port'] == 443 else "http")),  # Default to 'http' if not specified # type: ignore
                path=str(self.config.get("path", "/transmission/rpc/")),              # Default to '' if not specified
                timeout=5,
            )
            print("Successfully connected to the server.")
        except Exception as e:
            print(f"Failed to connect to the server: {e}")
            self.logger.error(f"Failed to connect to the server: {e}")
            raise e
        
    def setup_logger(self) -> logging.Logger:
        logger: logging.Logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        handler: logging.Handler = logging.FileHandler(os.path.join(os.getcwd(), 'daemon.log'))
        formatter: logging.Formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        if logger.hasHandlers():
            logger.handlers.clear()
        logger.addHandler(handler)
        return logger
    
    def remove_torrents_by_delay(self) -> None:
        """
        Remove torrents which have completed downloading after a specified delay
        """
        self.logger.info('Checking for completed torrents by delay')
        assert self.client is not None, "Transmission client is not connected"
        torrents: List[Torrent] = self.client.get_torrents()
        current_time: datetime = datetime.now()
        for torrent in torrents:
            # Remove from tracking if torrent is paused
            if torrent.status == 'stopped':
                if torrent.id in self.completed_torrents:
                    self.logger.info(f"Torrent '{torrent.name}' has been paused. Removing from tracking list.")
                    del self.completed_torrents[torrent.id]
                continue  # Skip further processing for paused torrents

            # Check if torrent is completed
            if torrent.status is not None and torrent.status in ('seeding', 'seed_pending'):
                if torrent.id not in self.completed_torrents:
                    self.completed_torrents[torrent.id] = current_time
                    self.logger.info(f"Torrent '{torrent.name}' completed at {current_time}")
                else:
                    time_since_completed: timedelta = current_time - self.completed_torrents[torrent.id]
                    if self.delay == 0 or time_since_completed >= timedelta(minutes=self.delay):
                        self.logger.info(f"Removing completed torrent: '{torrent.name}'")
                        self.client.stop_torrent(torrent.id)
                        del self.completed_torrents[torrent.id]
            else:
                # Remove from tracking if it's no longer completed
                if torrent.id in self.completed_torrents:
                    self.logger.info(f"Torrent '{torrent.name}' is no longer completed. Removing from tracking list.")
                    del self.completed_torrents[torrent.id]

    def remove_torrents_by_ratio(self) -> None:
        """
        Remove torrents which have reached the specified upload ratio
        """
        self.logger.info('Checking for completed torrents by ratio')
        assert self.client is not None, "Transmission client is not connected"
        torrents: List[Torrent] = self.client.get_torrents()
        for torrent in torrents:
            # Skip if torrent is paused
            if torrent.status == 'stopped':
                continue

            # Check if torrent has reached the specified ratio
            if torrent.ratio >= self.ratio if self.ratio else 1.0 and torrent.status in ('seeding', 'seed_pending'):
                self.logger.info(f"Torrent '{torrent.name}' has reached ratio {torrent.ratio:.2f}. Removing torrent.")
                self.client.stop_torrent(torrent.id)

    def run(self) -> None:
        def signal_handler(signum: int, frame: Any) -> None:
            print("Received signal to stop. Exiting...")
            self.stop_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        try:
            while not self.stop_event.is_set():
                if self.ratio is not None:
                    self.remove_torrents_by_ratio()
                else:
                    self.remove_torrents_by_delay()
                self.stop_event.wait(self.sleep_duration)
        except KeyboardInterrupt:
            print("Received interrupt signal. Exiting...")

def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description='''Transmission Manager Script

This script manages Transmission torrents by removing completed torrents either after a specified delay or when they reach a certain upload ratio.

By default, the script removes torrents immediately after they finish downloading. You can modify this behavior using the command-line options.

''',
        epilog='''Examples:

  Remove torrents immediately upon completion (default behavior):
    python script_name.py

  Remove torrents after a 15-minute delay:
    python script_name.py --delay 15

  Remove torrents when they reach an upload ratio of 2.0:
    python script_name.py --ratio 2.0

  Specify Transmission RPC connection parameters:
    python script_name.py --host 192.168.1.100 --port 9091 --username user --password pass

  Adjust the check interval to 30 seconds:
    python script_name.py --sleep 30

''',
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Transmission connection parameters
    parser.add_argument('--host', type=str, default='127.0.0.1',
                        help='Transmission RPC host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=9091,
                        help='Transmission RPC port (default: 9091)')
    parser.add_argument('--username', type=str, default='',
                        help='Transmission RPC username (default: "")')
    parser.add_argument('--password', type=str, default='',
                        help='Transmission RPC password (default: "")')
    parser.add_argument('--protocol', type=str, default='http', choices=['http', 'https'],
                        help='Transmission RPC protocol ("http" or "https") (default: "http")')
    parser.add_argument('--path', type=str, default='/transmission/rpc/',
                        help='Transmission RPC URL path (default: "/transmission/rpc/")')

    # Mutually exclusive group for delay and ratio
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--delay', type=int,
                       help='Delay in minutes before removing completed torrents (default: 0, immediate removal)')
    group.add_argument('--ratio', type=float,
                       help='Upload ratio at which to remove completed torrents')

    # Sleep duration parameter
    parser.add_argument('--sleep', type=int, default=60,
                        help='Sleep duration in seconds between checks (default: 60)')

    args: argparse.Namespace = parser.parse_args()

    config: Dict[str, Union[str, int]] = {
        "host": args.host,
        "port": args.port,
        "username": args.username,
        "password": args.password,
        "protocol": args.protocol,
        "path": args.path,
    }

    delay: int = args.delay if args.delay is not None else 0
    ratio: Optional[float] = args.ratio

    tm: TransmissionManager = TransmissionManager(config, delay, args.sleep, ratio)
    tm.run()

if __name__ == "__main__":
    main()
