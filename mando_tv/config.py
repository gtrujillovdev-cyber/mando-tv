"""Configuración central (sobrescribible con variables de entorno)."""
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

IP_LG = os.environ.get("LG_TV_IP", "192.168.1.250")
IP_XIAOMI = os.environ.get("XIAOMI_TV_IP", "192.168.1.238")
MAC_LG = os.environ.get("LG_TV_MAC", "74:e6:b8:26:02:0e")
MAC_XIAOMI = os.environ.get("XIAOMI_TV_MAC", "50:e4:78:af:b2:e7")
PUERTO = int(os.environ.get("MANDO_PORT", "8899"))
LG_CONFIG_PATH = os.path.expanduser(os.environ.get("LG_CONFIG", "~/.config/lg_tv/config.json"))
TIMER_FILE_LG = "/tmp/lg_sleep_timer.pid"
TIMER_FILE_XIAOMI_META = "/tmp/xiaomi_sleep_timer.meta"


class Color:
    """Colores ANSI para la salida de terminal."""
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    END = '\033[0m'
