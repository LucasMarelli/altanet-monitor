# 1. Copiar el script
cp altanet_monitor.py /home/fabrifor/

# 2. Copiar el servicio
sudo cp altanet-monitor.service /etc/systemd/system/

# 3. Activar y arrancar
sudo systemctl daemon-reload
sudo systemctl enable altanet-monitor
sudo systemctl start altanet-monitor

# 4. Verificar estado
sudo systemctl status altanet-monitor

# 5. Ver logs en tiempo real
journalctl -u altanet-monitor -f