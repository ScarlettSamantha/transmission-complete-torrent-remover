```bash
vim transmission_complete_torrent_remove_manager.service
vim main.py
sudo systemctl enable ./transmission_complete_torrent_remove_manager.service
sudo systemctl start transmission_complete_torrent_remove_manager.service
sudo systemctl status transmission_complete_torrent_remove_manager.service
tail -f daemon.log
```
