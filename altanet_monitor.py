#!/usr/bin/env python3
"""
Altanet ST20 — Monitor de señal GSM con LED
Fabrifor Diagnósticos SRL

LED GPIO 26:
  Apagado         → Sin datos / sin SIM
  Fijo encendido  → Señal buena o regular
  Parpadeo lento  → Señal mala (0.5 Hz)
  Parpadeo rápido → Sin conexión PPP (2 Hz)
"""

import requests
import base64
import time
import logging
from gpiozero import LED

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


# ── Umbrales de señal ────────────────────────────────────────────────────────

def evaluar_estado(rsrp: int, sinr: int) -> str:
    """
    Devuelve 'buena', 'regular' o 'mala' según RSRP y SINR.
    Si alguno degrada, baja el estado.
    """
    if rsrp > -95 and sinr > 5:
        return "buena"
    elif rsrp >= -105 and sinr >= 0:
        return "regular"
    else:
        return "mala"


# ── Cliente Altanet ST20 ─────────────────────────────────────────────────────

class AltanetDongle:
    HEADERS = {
        "Referer": "http://10.10.10.1/index.html",
        "X-Requested-With": "XMLHttpRequest",
    }

    def __init__(self, host="192.168.6.1", user="admin", password="admin"):
        self.base_url = f"http://{host}"
        self.user = user
        self.password = password
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def login(self) -> bool:
        url = f"{self.base_url}/reqproc/proc_post"
        payload = {
            "isTest": "false",
            "goformId": "LOGIN",
            "username": base64.b64encode(self.user.encode()).decode(),
            "password": base64.b64encode(self.password.encode()).decode(),
        }
        r = self.session.post(url, data=payload, timeout=3)
        ok = r.json().get("result") == "0"
        log.info("Login: %s", "OK" if ok else "FALLO")
        return ok

    def get_signal(self) -> dict | None:
        url = f"{self.base_url}/reqproc/proc_get"
        params = {
            "isTest": "false",
            "cmd": "network_type,sub_network_type,rssi,lte_rsrp,lte_rsrq,lte_sinr,lte_band,ppp_status",
            "multi_data": "1",
        }
        r = self.session.get(url, params=params, timeout=3)
        data = r.json()
        # Sesión caída → rssi viene vacío
        if data.get("rssi") == "":
            return None
        return data


# ── Display en consola ───────────────────────────────────────────────────────

DESCRIPCIONES = {
    "rssi":    "Potencia total",
    "lte_rsrp": "Señal referencia",
    "lte_rsrq": "Calidad señal",
    "lte_sinr": "Ruido/interferencia",
}

UNIDADES = {
    "rssi":    "dBm",
    "lte_rsrp": "dBm",
    "lte_rsrq": "dB",
    "lte_sinr": "dB",
}

def clasificar(key: str, val: int) -> str:
    umbrales = {
        "rssi":     [(-80, "Buena"),   (-90,  "Regular")],
        "lte_rsrp": [(-95, "Buena"),   (-105, "Regular")],
        "lte_rsrq": [(-10, "Buena"),   (-15,  "Regular")],
        "lte_sinr": [(10,  "Buena"),   (0,    "Regular")],
    }
    for umbral, etiqueta in umbrales.get(key, []):
        if val >= umbral:
            return etiqueta
    return "Mala"

def mostrar(data: dict, estado: str):
    red  = data.get("network_type", "?")
    sub  = data.get("sub_network_type", "")
    band = data.get("lte_band", "?")
    ppp  = data.get("ppp_status", "")
    ppp_str = "Conectado" if ppp == "ppp_connected" else "Sin conexión"

    print()
    print("─" * 55)
    print("  ALTANET ST20 — Estado GSM")
    print("─" * 55)
    print(f"  Red         {red} {sub}  /  Banda {band}")
    print(f"  Conexión    {ppp_str}")
    print(f"  Estado GSM  {estado.upper()}")
    print()
    print(f"  {'Parámetro':<14} {'Descripción':<22} {'Raw':<12} Estado")
    print("  " + "─" * 53)

    for key, desc in DESCRIPCIONES.items():
        raw_str = data.get(key, "?")
        try:
            val = int(raw_str)
            raw_fmt = f"{val} {UNIDADES[key]}"
            estado_param = clasificar(key, val)
        except (ValueError, TypeError):
            raw_fmt = "?"
            estado_param = "?"
        print(f"  {key:<14} {desc:<22} {raw_fmt:<12} {estado_param}")

    print("─" * 55)


# ── Control de LED ───────────────────────────────────────────────────────────

class LedSenal:
    def __init__(self, pin: int):
        self.led = LED(pin)
        self._estado_actual = None

    def aplicar(self, estado: str, ppp_ok: bool):
        nuevo = (estado, ppp_ok)
        if nuevo == self._estado_actual:
            return  # sin cambio, no interrumpir blink en curso

        self._estado_actual = nuevo

        if not ppp_ok:
            self.led.blink(on_time=0.25, off_time=0.25)  # rápido → sin PPP
        elif estado == "mala":
            self.led.blink(on_time=1.0, off_time=1.0)    # lento → mala señal
        else:
            self.led.on()                                  # fijo → buena/regular

    def apagar(self):
        self.led.off()
        self._estado_actual = None


# ── Loop principal ───────────────────────────────────────────────────────────

INTERVALO = 30  # segundos entre polls

def main():
    dongle = AltanetDongle()
    led    = LedSenal(pin=26)

    dongle.login()

    while True:
        try:
            data = dongle.get_signal()

            if data is None:
                log.warning("Sin datos (sesión caída o sin SIM)")
                led.apagar()
            else:
                rsrp = int(data.get("lte_rsrp", -999))
                sinr = int(data.get("lte_sinr", -999))
                ppp_ok = data.get("ppp_status") == "ppp_connected"
                estado = evaluar_estado(rsrp, sinr)

                mostrar(data, estado)
                led.aplicar(estado, ppp_ok)

        except Exception as e:
            log.error("Error: %s", e)
            led.apagar()

        time.sleep(INTERVALO)


if __name__ == "__main__":
    main()