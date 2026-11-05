"""Wake-on-LAN."""
import socket
from .config import Color, IP_LG, IP_XIAOMI


def enviar_wol(mac: str) -> bool:
    """Envía Magic Packet Wake-on-LAN a través de múltiples broadcasts y puertos 9 y 7."""
    try:
        clean = mac.replace(":", "").replace("-", "")
        data = bytes.fromhex("FF" * 6 + clean * 16)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for dest in ("255.255.255.255", "192.168.1.255", IP_LG, IP_XIAOMI):
                try:
                    s.sendto(data, (dest, 9))
                    s.sendto(data, (dest, 7))
                except Exception:
                    pass
        return True
    except Exception as e:
        print(f"{Color.YELLOW}[!] Error enviando WoL ({mac}): {e}{Color.END}")
        return False
