"""Temporizadores de apagado."""
import os
import time
from .config import TIMER_FILE_LG, TIMER_FILE_XIAOMI_META


def obtener_tiempo_restante_timer(dispositivo: str) -> int:
    """Devuelve los segundos restantes del temporizador o 0 si no hay."""
    if dispositivo == "lg" and os.path.exists(TIMER_FILE_LG):
        try:
            with open(TIMER_FILE_LG, "r") as f:
                parts = f.read().strip().split(":")
            if len(parts) >= 3:
                _, dur, ini = parts
                restante = int(dur) - (int(time.time()) - int(ini))
                return max(0, restante)
        except Exception:
            pass
    elif dispositivo == "xiaomi" and os.path.exists(TIMER_FILE_XIAOMI_META):
        try:
            with open(TIMER_FILE_XIAOMI_META, "r") as f:
                parts = f.read().strip().split(":")
            if len(parts) >= 2:
                dur, ini = parts
                restante = int(dur) - (int(time.time()) - int(ini))
                return max(0, restante)
        except Exception:
            pass
    return 0
