import os
import time
import logging
from typing import Dict
from transmission_rpc import Client

class TransmissionManager:
    """
    A class to manage Transmission torrents
    """
    def __init__(self, config: Dict[str, str]):
        """
        :param config: A dictionary containing Transmission configuration
        """
        self.config = config
        self.logger = self.setup_logger()
        self.client = None
        self.connect_to_server()

    def connect_to_server(self):
        try:
            self.client = Client(
                host=self.config["host"],
                port=self.config["port"],
                username=self.config["username"],
                password=self.config["password"]
            )
            print("Successfully connected to the server.")
        except Exception as e:
            print(f"Failed to connect to the server: {e}")
            self.logger.error(f"Failed to connect to the server: {e}")
            raise e

    def setup_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(os.path.join(os.getcwd(), 'daemon.log'))
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def remove_completed_torrents(self):
        """
        Remove torrents which have completed downloading
        """
        self.logger.info('Checking for completed torrents')
        torrents = self.client.get_torrents()
        for torrent in torrents:
            if torrent.progress == 100:
                self.logger.info(f'Removing completed torrent: {torrent.name}')
                self.client.remove_torrent(torrent.id, delete_data=False)

def main():
    config = {
        # Without the default suffixes (/transmission/web)
        "host": "127.0.0.1",
        "port": 9090,
        "username": "user",
        "password": "password",
    }
    tm = TransmissionManager(config)
    while True:
        tm.remove_completed_torrents()
        time.sleep(60)

main()