```bash
sudo apt install python3-full python3-pip
pip3 install -r requirements.txt
vim transmission_complete_torrent_remove_manager.service
vim main.py
sudo systemctl enable ./transmission_complete_torrent_remove_manager.service
sudo systemctl start transmission_complete_torrent_remove_manager.service
sudo systemctl status transmission_complete_torrent_remove_manager.service
tail -f daemon.log
```
