"""Escenas conjuntas y control del Mac anfitrión."""
import subprocess
from .config import Color
from .lg import apagar_lg, cancelar_temporizador_lg, encender_lg, lg_cine, lg_descanso, lg_dia, lg_juego, lg_noche
from .xiaomi import apagar_xiaomi, cancelar_temporizador_xiaomi, encender_xiaomi, xiaomi_cine, xiaomi_descanso, xiaomi_dia, xiaomi_juego, xiaomi_noche


def encender_ambas():
    encender_lg()
    encender_xiaomi()


def modo_noche(minutos: float = 90.0):
    print(f"\n{Color.BOLD}╔══════════════════════════════════════════════════════════════════╗{Color.END}")
    print(f"{Color.BOLD}║ 🌙 ACTIVANDO MODO NOCHE EN AMBAS TELEVISIONES                    ║{Color.END}")
    print(f"{Color.BOLD}║    Retroiluminación: 6% | Temporizador de apagado: {minutos} min      ║{Color.END}")
    print(f"{Color.BOLD}╚══════════════════════════════════════════════════════════════════╝{Color.END}")
    lg_noche(minutos)
    xiaomi_noche(minutos)


def modo_dia():
    print(f"\n{Color.BOLD}☀️ ACTIVANDO MODO DÍA (100% BRILLO) EN AMBAS TELEVISIONES...{Color.END}")
    lg_dia()
    xiaomi_dia()


def modo_cine():
    print(f"\n{Color.BOLD}🎬 ACTIVANDO MODO CINE (FILMMAKER / D65) EN AMBAS TELEVISIONES...{Color.END}")
    lg_cine()
    xiaomi_cine()


def modo_juego():
    print(f"\n{Color.BOLD}🎮 ACTIVANDO MODO JUEGO (LATENCIA MÍNIMA) EN AMBAS TELEVISIONES...{Color.END}")
    lg_juego()
    xiaomi_juego()


def modo_descanso():
    print(f"\n{Color.BOLD}👁️ ACTIVANDO MODO DESCANSO VISUAL EN AMBAS TELEVISIONES...{Color.END}")
    lg_descanso()
    xiaomi_descanso()


def apagar_ambas_tvs():
    print(f"\n{Color.BOLD}🔌 APAGANDO AMBAS TELEVISIONES...{Color.END}")
    apagar_lg()
    apagar_xiaomi()
    print(f"{Color.GREEN}[✓] Ambas televisiones apagadas con éxito.{Color.END}\n")


def cancelar_todos_temporizadores():
    print(f"\n{Color.CYAN}[*] Cancelando temporizadores de sueño en ambas televisiones...{Color.END}")
    cancelar_temporizador_lg()
    cancelar_temporizador_xiaomi()
    print(f"{Color.GREEN}[✓] Todos los temporizadores cancelados.{Color.END}\n")


# ==============================================================================
# 4. CONTROL DEL MAC M4 (Apagado / Suspensión)
# ==============================================================================
def apagar_m4():
    print(f"{Color.RED}[!] Apagando Mac M4...{Color.END}")
    subprocess.run("osascript -e 'tell app \"System Events\" to shut down'", shell=True)


def dormir_m4():
    print(f"{Color.CYAN}[*] Poniendo Mac M4 en reposo inmediato...{Color.END}")
    subprocess.run("pmset sleepnow", shell=True)
