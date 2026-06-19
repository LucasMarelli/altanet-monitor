# Altanet ST20 — Monitor de señal GSM

Monitor de conectividad 4G para el dongle Altanet ST20. Corre en una Raspberry Pi, consulta métricas de señal cada 30 segundos y las indica visualmente mediante un LED en GPIO 26.

## Comportamiento del LED

| Estado del LED | Significado |
|---|---|
| Apagado | Sin datos / sin SIM |
| Fijo encendido | Señal buena o regular |
| Parpadeo lento (0.5 Hz) | Señal mala |
| Parpadeo rápido (2 Hz) | Sin conexión PPP (internet caído) |

## Requisitos

- Raspberry Pi con Python 3
- Dongle Altanet ST20 conectado (accesible en `192.168.6.1`)
- LED conectado en GPIO 26

### Dependencias Python

```bash
pip install requests gpiozero
```

## Instalación como servicio systemd

```bash
# 1. Copiar el script
cp router-api.py /home/fabrifor/altanet_monitor.py

# 2. Copiar el archivo de servicio
sudo cp altanet-monitor.service /etc/systemd/system/

# 3. Recargar systemd y habilitar el servicio
sudo systemctl daemon-reload
sudo systemctl enable altanet-monitor

# 4. Arrancar el servicio
sudo systemctl start altanet-monitor

# 5. Verificar que esté corriendo
sudo systemctl status altanet-monitor
```

## Uso

### Ver logs en tiempo real

```bash
journalctl -u altanet-monitor -f
```

### Detener / reiniciar el servicio

```bash
sudo systemctl stop altanet-monitor
sudo systemctl restart altanet-monitor
```

### Ejecutar manualmente (sin servicio)

```bash
python3 router-api.py
```

## Configuración

Los siguientes valores están hardcodeados en `router-api.py` y pueden modificarse según el entorno:

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `host` | `192.168.6.1` | IP del dongle |
| `user` | `admin` | Usuario web del dongle |
| `password` | `admin` | Contraseña web del dongle |
| `pin` | `26` | GPIO del LED |
| `INTERVALO` | `30` | Segundos entre cada consulta |

## Umbrales de señal

| Parámetro | Buena | Regular | Mala |
|---|---|---|---|
| RSRP | > -95 dBm | ≥ -105 dBm | < -105 dBm |
| SINR | > 5 dB | ≥ 0 dB | < 0 dB |
