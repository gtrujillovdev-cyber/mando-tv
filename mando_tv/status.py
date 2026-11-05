"""Diagnóstico de estado."""
import asyncio
import os
import socket
import time
from .config import Color, IP_LG, IP_XIAOMI, TIMER_FILE_LG
from .lg import enviar_comando_lg
from .xiaomi import ejecutar_adb_xiaomi


def estado_sistema():
    print(f"\n{Color.BOLD}======================================================================{Color.END}")
    print(f"{Color.BOLD} 📊 ESTADO DEL SISTEMA MULTI-TV & CONTROL HOGAR{Color.END}")
    print(f"{Color.BOLD}======================================================================{Color.END}")

    # LG 65"
    s_lg = socket.socket()
    s_lg.settimeout(0.5)
    lg_online = (s_lg.connect_ex((IP_LG, 3000)) == 0)
    s_lg.close()

    print(f"{Color.BOLD}📺 LG 65\" ({IP_LG}):{Color.END}")
    if lg_online:
        app_activa = asyncio.run(enviar_comando_lg("status")) or "Encendida"
        print(f"  • Estado: {Color.GREEN}🟢 ENCENDIDA / ONLINE{Color.END}")
        print(f"  • App en primer plano: {Color.CYAN}{app_activa}{Color.END}")
    else:
        print(f"  • Estado: {Color.YELLOW}⚪ EN REPOSO / APAGADA{Color.END}")

    # Timer LG
    if os.path.exists(TIMER_FILE_LG):
        try:
            with open(TIMER_FILE_LG, "r") as f:
                parts = f.read().strip().split(":")
                if len(parts) >= 3:
                    _, duracion, inicio = parts
                    restante = max(0, int(duracion) - int(time.time() - int(inicio)))
                    print(f"  • Temporizador: {Color.MAGENTA}⏱️ ACTIVO (~{restante // 60}m restantes para apagar){Color.END}")
                else:
                    print(f"  • Temporizador: {Color.MAGENTA}⏱️ ACTIVO (PID en ejecución){Color.END}")
        except Exception:
            print(f"  • Temporizador: {Color.MAGENTA}⏱️ ACTIVO{Color.END}")
    else:
        print(f"  • Temporizador: Inactivo")

    # Xiaomi TV
    s_xm = socket.socket()
    s_xm.settimeout(0.5)
    xm_online = (s_xm.connect_ex((IP_XIAOMI, 5555)) == 0)
    s_xm.close()

    print(f"\n{Color.BOLD}📺 Xiaomi TV ({IP_XIAOMI}):{Color.END}")
    if xm_online:
        wake = ejecutar_adb_xiaomi("dumpsys power | grep -i mWakefulness").stdout
        is_awake = "Awake" in wake
        estado_xm = f"{Color.GREEN}🟢 ENCENDIDA (Awake){Color.END}" if is_awake else f"{Color.YELLOW}⚪ EN REPOSO (Asleep){Color.END}"
        print(f"  • Estado: {estado_xm}")

        # Comprobar timer en Xiaomi
        timer_pid = ejecutar_adb_xiaomi("cat /data/local/tmp/tv_sleep_timer.pid 2>/dev/null").stdout.strip()
        if timer_pid:
            proc_check = ejecutar_adb_xiaomi(f"ps -A | grep {timer_pid}").stdout.strip()
            if proc_check:
                print(f"  • Temporizador: {Color.MAGENTA}⏱️ ACTIVO (Nativo en Android kernel - PID {timer_pid}){Color.END}")
            else:
                print(f"  • Temporizador: Inactivo")
        else:
            print(f"  • Temporizador: Inactivo")
    else:
        print(f"  • Estado: {Color.YELLOW}⚪ DESCONECTADA / APAGADA{Color.END}")

    print(f"{Color.BOLD}======================================================================{Color.END}\n")
