"""Control de la Xiaomi TV (Android TV vía ADB)."""
import os
import subprocess
import time
from .config import Color, IP_XIAOMI, MAC_XIAOMI, TIMER_FILE_XIAOMI_META
from .wol import enviar_wol
from . import discovery


def encender_xiaomi() -> bool:
    """Despierta la Xiaomi TV restaurando retroiluminación al 50% y volumen."""
    ip = discovery.resolver_ip_xiaomi()
    print(f"{Color.CYAN}[*] Despertando Xiaomi TV ({ip})...{Color.END}")
    enviar_wol(MAC_XIAOMI)
    conectar_adb_xiaomi()
    cmd = (
        "settings put global picture_backlight 50; "
        "settings put system screen_brightness 128; "
        "settings put system volume_music_speaker 5; "
        "input keyevent 224; "
        "input keyevent 3"
    )
    ejecutar_adb_xiaomi(cmd)
    print(f"{Color.GREEN}[✓] Xiaomi TV: Pantalla encendida y audio restaurado.{Color.END}")
    return True


_adb_conectado: bool = False


def conectar_adb_xiaomi() -> bool:
    global _adb_conectado
    ip = discovery.resolver_ip_xiaomi()
    if not discovery.puerto_abierto(ip, 5555, timeout=0.2):
        _adb_conectado = False
        return False
    try:
        res = subprocess.run(
            ["adb", "connect", f"{ip}:5555"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2
        )
        _adb_conectado = (res.returncode == 0)
    except Exception:
        _adb_conectado = False
    return _adb_conectado


def ejecutar_adb_xiaomi(comando_shell: str):
    global _adb_conectado
    ip = discovery.resolver_ip_xiaomi()
    if not _adb_conectado:
        if not conectar_adb_xiaomi():
            return None
    try:
        res = subprocess.run(
            ["adb", "-s", f"{ip}:5555", "shell", comando_shell],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5
        )
        if res.returncode != 0 and ("device not found" in res.stderr.lower() or "offline" in res.stderr.lower()):
            if conectar_adb_xiaomi():
                res = subprocess.run(
                    ["adb", "-s", f"{ip}:5555", "shell", comando_shell],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5
                )
        return res
    except Exception:
        _adb_conectado = False
        return None


def programar_temporizador_xiaomi(minutos: float = 90.0):
    """Programa el apagado en el kernel de Android TV (persiste aunque el Mac se apague)."""
    cancelar_temporizador_xiaomi(silencioso=True)
    segundos = int(minutos * 60)
    ip = discovery.resolver_ip_xiaomi()
    conectar_adb_xiaomi()
    cmd = f"adb -s {ip}:5555 shell 'nohup sh -c \"sleep {segundos} && input keyevent 26\" </dev/null >/dev/null 2>&1 & echo $! > /data/local/tmp/tv_sleep_timer.pid'"
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        with open(TIMER_FILE_XIAOMI_META, "w") as f:
            f.write(f"{segundos}:{int(time.time())}")
    except Exception:
        pass


def cancelar_temporizador_xiaomi(silencioso: bool = False):
    ip = discovery.resolver_ip_xiaomi()
    conectar_adb_xiaomi()
    cancel_cmd = f"adb -s {ip}:5555 shell 'kill -9 $(cat /data/local/tmp/tv_sleep_timer.pid 2>/dev/null) 2>/dev/null; pkill -P $(cat /data/local/tmp/tv_sleep_timer.pid 2>/dev/null) 2>/dev/null; rm -f /data/local/tmp/tv_sleep_timer.pid'"
    subprocess.run(cancel_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(TIMER_FILE_XIAOMI_META):
        try:
            os.remove(TIMER_FILE_XIAOMI_META)
        except Exception:
            pass
    if not silencioso:
        print(f"{Color.GREEN}[✓] Xiaomi TV: Temporizador de apagado cancelado.{Color.END}")


def apagar_xiaomi(forzar_apagado_total: bool = False):
    print(f"{Color.CYAN}[*] Apagando Xiaomi TV (pantalla off, Wi-Fi activo)...{Color.END}")
    cancelar_temporizador_xiaomi(silencioso=True)
    if forzar_apagado_total:
        ejecutar_adb_xiaomi("input keyevent 26")
        print(f"{Color.YELLOW}[!] Xiaomi TV: Apagado profundo total (Wi-Fi cortado).{Color.END}")
    else:
        # Soft-standby: pantalla negra pero sistema despierto y Wi-Fi activo.
        # - stay_on_while_plugged_in 7 → nunca suspende mientras la TV está enchufada (AC+USB+wireless)
        # - wifi_sleep_policy 2        → Wi-Fi nunca duerme
        # - backlight/brightness 0     → pantalla visualmente apagada sin invocar KEYCODE_SLEEP
        cmd = (
            "settings put global stay_on_while_plugged_in 7; "
            "settings put global wifi_sleep_policy 2; "
            "input keyevent 85 2>/dev/null; "
            "settings put global picture_backlight 0; "
            "settings put system screen_brightness 0; "
            "settings put system volume_music_speaker 0; "
            "input keyevent 164; "
            "input keyevent 3"
        )
        ejecutar_adb_xiaomi(cmd)
        print(f"{Color.GREEN}[✓] Xiaomi TV: Pantalla apagada, Wi-Fi y ADB activos.{Color.END}")


def xiaomi_noche(minutos: float = 90.0):
    print(f"\n{Color.BOLD}🌙 [XIAOMI TV] ACTIVANDO MODO NOCHE...{Color.END}")
    print(f"  • Retroiluminación: {Color.CYAN}6%{Color.END}")
    print(f"  • Temporizador de apagado: {Color.CYAN}{minutos} minutos ({minutos/60:.1f}h nativo Android){Color.END}")

    ejecutar_adb_xiaomi("settings put global picture_backlight 6 && settings put system screen_brightness 15")
    programar_temporizador_xiaomi(minutos)
    print(f"{Color.GREEN}[✓] Xiaomi TV: Retroiluminación al 6% y temporizador de {minutos}m activado en Android.{Color.END}\n")


def xiaomi_dia():
    print(f"\n{Color.BOLD}☀️ [XIAOMI TV] ACTIVANDO MODO DÍA...{Color.END}")
    ejecutar_adb_xiaomi("settings put global picture_backlight 100 && settings put system screen_brightness 255")
    print(f"{Color.GREEN}[✓] Xiaomi TV: Retroiluminación al 100% y brillo máximo activado.{Color.END}\n")


def xiaomi_cine():
    print(f"\n{Color.BOLD}🎬 [XIAOMI TV] ACTIVANDO MODO CINE (MODO PELÍCULA)...{Color.END}")
    ejecutar_adb_xiaomi("settings put global picture_mode 1 && settings put system tv_picture_video_game_mode 0 && settings put global tv_picture_video_allm 0")
    print(f"{Color.GREEN}[✓] Xiaomi TV: Modo Película D65 activo.{Color.END}\n")


def xiaomi_juego():
    print(f"\n{Color.BOLD}🎮 [XIAOMI TV] ACTIVANDO MODO JUEGO (LATENCIA MÍNIMA Y ALLM)...{Color.END}")
    ejecutar_adb_xiaomi("settings put global picture_mode 5 && settings put system tv_picture_video_game_mode 1 && settings put global tv_picture_video_allm 1")
    print(f"{Color.GREEN}[✓] Xiaomi TV: Modo Juego activo (Bypass de procesado y ALLM activado).{Color.END}\n")


def xiaomi_descanso():
    print(f"\n{Color.BOLD}👁️ [XIAOMI TV] ACTIVANDO MODO DESCANSO VISUAL...{Color.END}")
    ejecutar_adb_xiaomi("settings put global picture_backlight 25 && settings put system screen_brightness 40")
    print(f"{Color.GREEN}[✓] Xiaomi TV: Modo Descanso Visual activado (brillo atenuado para no forzar la vista).{Color.END}\n")


def xiaomi_vol_up():
    ejecutar_adb_xiaomi("cmd media_session volume --show --stream 3 --adj raise")


def xiaomi_vol_down():
    ejecutar_adb_xiaomi("cmd media_session volume --show --stream 3 --adj lower")


def xiaomi_play_pause():
    ejecutar_adb_xiaomi("cmd media_session dispatch play-pause")


def xiaomi_rewind():
    ejecutar_adb_xiaomi("cmd media_session dispatch rewind")


def xiaomi_fast_forward():
    ejecutar_adb_xiaomi("cmd media_session dispatch fast-forword")


def xiaomi_volumen(nivel: int):
    # Android TV suele manejar volumen 0 a 15
    nivel_android = max(0, min(15, int(nivel * 15 / 100))) if nivel > 15 else nivel
    ejecutar_adb_xiaomi(f"cmd media_session volume --show --set {nivel_android}")
    print(f"{Color.GREEN}[✓] Xiaomi TV: Volumen ajustado a {nivel_android}/15.{Color.END}")


def xiaomi_mute():
    ejecutar_adb_xiaomi("input keyevent 164")
    print(f"{Color.GREEN}[✓] Xiaomi TV: Mute conmutado.{Color.END}")


def obtener_info_xiaomi() -> dict:
    """Lee retroiluminación y volumen actuales de la Xiaomi vía ADB."""
    vol = 0
    backlight = 0
    try:
        ip = discovery.resolver_ip_xiaomi()
        if not discovery.puerto_abierto(ip, 5555):
            return {"volume": 0, "backlight": 0}
        res = ejecutar_adb_xiaomi("settings get system screen_brightness 2>/dev/null; settings get system volume_music_speaker 2>/dev/null")
        if res and res.stdout:
            lines = res.stdout.strip().split()
            if len(lines) >= 1 and lines[0].isdigit():
                val_b = int(lines[0])
                backlight = min(100, max(0, round((val_b / 255.0) * 100)))
            if len(lines) >= 2 and lines[1].isdigit():
                val_v = int(lines[1])
                vol = min(100, max(0, round((val_v / 15.0) * 100)))
    except Exception:
        pass
    return {"volume": vol, "backlight": backlight}

