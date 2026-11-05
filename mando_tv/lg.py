"""Control de la LG webOS (SSAP por WebSocket)."""
import asyncio
import json
import os
import subprocess
import time
from typing import Dict, Optional
from .config import Color, IP_LG, LG_CONFIG_PATH, MAC_LG, ROOT_DIR, TIMER_FILE_LG
from .wol import enviar_wol


def encender_lg() -> bool:
    """Despierta la televisión LG 65\" webOS mediante Wake-on-LAN."""
    print(f"{Color.CYAN}[*] Enviando señal Wake-on-LAN a LG 65\" ({MAC_LG} / {IP_LG})...{Color.END}")
    ok = enviar_wol(MAC_LG)
    if ok:
        print(f"{Color.GREEN}[✓] Señal WoL enviada con éxito a LG 65\".{Color.END}")
    return ok


def cargar_config_lg() -> Dict:
    ruta = LG_CONFIG_PATH
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"ip": IP_LG, "client_key": ""}


async def enviar_comando_lg(accion: str, payload_extra: Optional[Dict] = None) -> bool:
    try:
        import websockets
    except ImportError:
        print(f"{Color.RED}[!] Librería 'websockets' no disponible.{Color.END}")
        return False

    cfg = cargar_config_lg()
    ip = cfg.get("ip", IP_LG)
    key = cfg.get("client_key")
    uri = f"ws://{ip}:3000/"

    manifest = {
        "manifestVersion": 1,
        "appVersion": "1.1",
        "signed": {
            "created": "20261104",
            "appId": "com.antigravity.macm4",
            "vendorId": "antigravity",
            "localizedAppNames": {"": "Mac M4 Master Controller"},
            "permissions": [
                "LAUNCH", "LAUNCH_WEBAPP", "APP_TO_APP", "CLOSE", "TEST_OPEN",
                "CONTROL_AUDIO", "CONTROL_DISPLAY", "CONTROL_INPUT_JOYSTICK",
                "CONTROL_POWER", "READ_APP_STATUS", "READ_CURRENT_CHANNEL",
                "READ_INPUT_DEVICE_LIST", "READ_NETWORK_STATUS", "READ_RUNNING_APPS",
                "READ_TV_CHANNEL_LIST", "WRITE_NOTIFICATION_TOAST", "READ_POWER_STATE",
                "READ_COUNTRY_INFO"
            ],
            "serial": "12345678"
        },
        "permissions": [
            "LAUNCH", "LAUNCH_WEBAPP", "APP_TO_APP", "CLOSE", "TEST_OPEN",
            "CONTROL_AUDIO", "CONTROL_DISPLAY", "CONTROL_INPUT_JOYSTICK",
            "CONTROL_POWER", "READ_APP_STATUS", "READ_CURRENT_CHANNEL",
            "READ_INPUT_DEVICE_LIST", "READ_NETWORK_STATUS", "READ_RUNNING_APPS",
            "READ_TV_CHANNEL_LIST", "WRITE_NOTIFICATION_TOAST", "READ_POWER_STATE",
            "READ_COUNTRY_INFO"
        ]
    }

    try:
        async with websockets.connect(uri, ping_interval=None, open_timeout=2.0) as ws:
            # Autenticación
            await ws.send(json.dumps({"type": "register", "id": "reg", "payload": {"client-key": key, "manifest": manifest}}))
            await ws.recv()

            if accion == "apagar":
                await ws.send(json.dumps({"type": "request", "id": "p_off", "uri": "ssap://system/turnOff"}))
                print(f"{Color.GREEN}[✓] LG 65\": Apagada correctamente.{Color.END}")
                return True

            elif accion == "toast":
                msg = (payload_extra or {}).get("mensaje", "")
                await ws.send(json.dumps({"type": "request", "id": "t", "uri": "ssap://system.notifications/createToast", "payload": {"message": msg}}))
                return True

            elif accion == "volumen":
                vol = (payload_extra or {}).get("volumen", 15)
                await ws.send(json.dumps({"type": "request", "id": "vol", "uri": "ssap://audio/setVolume", "payload": {"volume": vol}}))
                print(f"{Color.GREEN}[✓] LG 65\": Volumen fijado a {vol}.{Color.END}")
                return True

            elif accion == "mute":
                mute_state = (payload_extra or {}).get("mute", True)
                await ws.send(json.dumps({"type": "request", "id": "mut", "uri": "ssap://audio/setMute", "payload": {"mute": mute_state}}))
                estado_str = "Silenciada" if mute_state else "Sonido activado"
                print(f"{Color.GREEN}[✓] LG 65\": {estado_str}.{Color.END}")
                return True

            elif accion == "ajustes":
                # Inyección autorizada con sistema Luna Alert Bridge
                cat = payload_extra.get("category", "picture")
                settings = payload_extra.get("settings", {})
                alert_payload = {
                    "message": payload_extra.get("mensaje", "Aplicando configuración..."),
                    "modal": False,
                    "buttons": [{"label": "OK", "focus": True}],
                    "onclose": {
                        "uri": "luna://com.webos.settingsservice/setSystemSettings",
                        "params": {"category": cat, "settings": settings}
                    },
                    "type": "confirm",
                    "isSysReq": True
                }
                await ws.send(json.dumps({"type": "request", "id": "al_req", "uri": "ssap://system.notifications/createAlert", "payload": alert_payload}))
                res = json.loads(await ws.recv())
                aid = res.get("payload", {}).get("alertId")
                if aid:
                    await asyncio.sleep(0.6)
                    await ws.send(json.dumps({"type": "request", "id": "cl_req", "uri": "ssap://system.notifications/closeAlert", "payload": {"alertId": aid}}))
                    await ws.recv()
                return True

            elif accion == "solo_audio":
                # Apagar panel LED manteniendo sonido (óptico/altavoces)
                alert_payload = {
                    "message": "🌙 Apagando pantalla (Modo Solo Audio). Pulsa cualquier tecla para reactivar el panel.",
                    "modal": False,
                    "buttons": [{"label": "OK", "focus": True}],
                    "onclose": {
                        "uri": "luna://com.webos.settingsservice/setSystemSettings",
                        "params": {"category": "picture", "settings": {"energySaving": "screen_off"}}
                    },
                    "type": "confirm",
                    "isSysReq": True
                }
                await ws.send(json.dumps({"type": "request", "id": "scr_off", "uri": "ssap://system.notifications/createAlert", "payload": alert_payload}))
                res = json.loads(await ws.recv())
                aid = res.get("payload", {}).get("alertId")
                if aid:
                    await asyncio.sleep(0.6)
                    await ws.send(json.dumps({"type": "request", "id": "cl_scr", "uri": "ssap://system.notifications/closeAlert", "payload": {"alertId": aid}}))
                    await ws.recv()
                print(f"{Color.GREEN}[✓] LG 65\": Pantalla apagada (Modo Solo Audio activo). Pulsa cualquier tecla del mando para reactivar el vídeo.{Color.END}")
                return True

            elif accion == "app":
                app_id = payload_extra.get("id", "youtube.leanback.v4")
                params = payload_extra.get("params", {})
                await ws.send(json.dumps({
                    "type": "request",
                    "id": "open_app",
                    "uri": "ssap://system.launcher/open",
                    "payload": {"id": app_id, "params": params}
                }))
                res = json.loads(await ws.recv())
                return res.get("payload", {}).get("returnValue", True)

            elif accion == "audio_output":
                output = (payload_extra or {}).get("output", "external_arc")
                await ws.send(json.dumps({
                    "type": "request",
                    "id": "snd_out",
                    "uri": "ssap://audio/changeSoundOutput",
                    "payload": {"output": output}
                }))
                res = json.loads(await ws.recv())
                return res.get("payload", {}).get("returnValue", True)

            elif accion == "vol_up":
                await ws.send(json.dumps({"type": "request", "id": "vup", "uri": "ssap://audio/volumeUp"}))
                return True

            elif accion == "vol_down":
                await ws.send(json.dumps({"type": "request", "id": "vdn", "uri": "ssap://audio/volumeDown"}))
                return True

            elif accion == "tecla":
                tecla = (payload_extra or {}).get("tecla", "ENTER").upper()
                # 1) Endpoints SSAP nativos (no requieren socket de puntero)
                nativos = {
                    "HOME": ("ssap://system.launcher/open", {"id": "com.webos.app.home"}),
                    "MENU": ("ssap://system.launcher/open", {"id": "com.palm.app.settings"}),
                    "INPUT": ("ssap://system.launcher/open", {"id": "com.webos.app.inputpicker"}),
                    "PLAY": ("ssap://media.controls/play", None),
                    "PAUSE": ("ssap://media.controls/pause", None),
                    "REWIND": ("ssap://media.controls/rewind", None),
                    "FASTFORWARD": ("ssap://media.controls/fastForward", None),
                    "CHANNELUP": ("ssap://tv/channelUp", None),
                    "CHANNELDOWN": ("ssap://tv/channelDown", None),
                }
                if tecla in nativos:
                    uri_n, pl = nativos[tecla]
                    msg = {"type": "request", "id": "k_nat", "uri": uri_n}
                    if pl:
                        msg["payload"] = pl
                    await ws.send(json.dumps(msg))
                    res = json.loads(await ws.recv())
                    if res.get("type") != "error":
                        return True
                    if tecla == "PLAY":  # algunas apps solo aceptan pause
                        await ws.send(json.dumps({"type": "request", "id": "k_p", "uri": "ssap://media.controls/pause"}))
                        await ws.recv()
                        return True
                # 2) Socket de puntero (flechas, OK, atrás)
                await ws.send(json.dumps({"type": "request", "id": "k_ptr", "uri": "ssap://com.webos.service.networkinput/getPointerInputSocket"}))
                res = json.loads(await ws.recv())
                sock = res.get("payload", {}).get("socketPath")
                if sock:
                    async with websockets.connect(sock, ping_interval=None, open_timeout=2.0) as pws:
                        await pws.send(f"type:button\nname:{tecla}\n\n")
                        await asyncio.sleep(0.05)
                    return True
                # 3) Fallbacks sin socket
                if tecla == "ENTER":
                    await ws.send(json.dumps({"type": "request", "id": "k_ent", "uri": "ssap://com.webos.service.ime/sendEnterKey"}))
                    await ws.recv()
                    return True
                print(f"{Color.YELLOW}[!] LG: tecla {tecla} requiere permiso de puntero: {res.get('error')}{Color.END}")
                return False

            elif accion == "status":
                await ws.send(json.dumps({"type": "request", "id": "app", "uri": "ssap://com.webos.applicationManager/getForegroundAppInfo"}))
                res = json.loads(await ws.recv())
                app_id = res.get("payload", {}).get("appId", "Desconocida")
                return app_id

    except Exception as e:
        print(f"{Color.YELLOW}[!] LG 65\" ({ip}): No responde (en reposo o apagada): {e}{Color.END}")
        return False


def programar_temporizador_lg(minutos: float = 90.0):
    """Lanza un proceso en segundo plano en el Mac para apagar la LG."""
    cancelar_temporizador_lg(silencioso=True)
    segundos = int(minutos * 60)
    
    cmd = (
        f"nohup bash -c 'sleep {segundos} && python3 -c \""
        f"import sys; sys.path.insert(0, \\\"{ROOT_DIR}\\\"); "
        f"from mando_tv.lg import apagar_lg; apagar_lg()\"' >/dev/null 2>&1 & echo $!"
    )
    try:
        pid = subprocess.check_output(cmd, shell=True, text=True).strip()
        with open(TIMER_FILE_LG, "w") as f:
            f.write(f"{pid}:{segundos}:{int(time.time())}")
    except Exception as e:
        print(f"{Color.RED}[!] Error programando timer LG: {e}{Color.END}")


def cancelar_temporizador_lg(silencioso: bool = False):
    if os.path.exists(TIMER_FILE_LG):
        try:
            with open(TIMER_FILE_LG, "r") as f:
                contenido = f.read().strip()
            pid = contenido.split(":")[0] if ":" in contenido else contenido
            if pid:
                subprocess.run(f"kill -9 {pid} 2>/dev/null", shell=True)
            os.remove(TIMER_FILE_LG)
            if not silencioso:
                asyncio.run(enviar_comando_lg("toast", {"mensaje": "⏱️ Temporizador de apagado LG: CANCELADO"}))
                print(f"{Color.GREEN}[✓] LG 65\": Temporizador de apagado cancelado.{Color.END}")
        except Exception:
            pass
    elif not silencioso:
        print(f"{Color.CYAN}[*] LG 65\": No había temporizadores activos.{Color.END}")


def apagar_lg():
    print(f"{Color.CYAN}[*] Apagando LG 65\" ({IP_LG})...{Color.END}")
    cancelar_temporizador_lg(silencioso=True)
    asyncio.run(enviar_comando_lg("apagar"))


def lg_noche(minutos: float = 90.0):
    print(f"\n{Color.BOLD}🌙 [LG 65\"] ACTIVANDO MODO NOCHE...{Color.END}")
    print(f"  • Retroiluminación: {Color.CYAN}6%{Color.END}")
    print(f"  • Temporizador de apagado: {Color.CYAN}{minutos} minutos ({minutos/60:.1f}h){Color.END}")

    asyncio.run(enviar_comando_lg("ajustes", {
        "category": "picture",
        "settings": {
            "backlight": "6",
            "brightness": "45",
            "energySaving": "min"
        },
        "mensaje": f"🌙 Modo Noche: Retroiluminación al 6% | Temporizador {minutos}m"
    }))
    asyncio.run(enviar_comando_lg("toast", {
        "mensaje": f"🌙 Modo Noche LG: Retroiluminación 6% | Apagado automático en {int(minutos)}m"
    }))
    programar_temporizador_lg(minutos)
    print(f"{Color.GREEN}[✓] LG 65\": Retroiluminación reducida al 6% y temporizador de {minutos}m activado.{Color.END}\n")


def lg_dia():
    print(f"\n{Color.BOLD}☀️ [LG 65\"] ACTIVANDO MODO DÍA...{Color.END}")
    asyncio.run(enviar_comando_lg("ajustes", {
        "category": "picture",
        "settings": {
            "backlight": "100",
            "brightness": "55",
            "contrast": "95",
            "energySaving": "off"
        },
        "mensaje": "☀️ Modo Día: Brillo máximo (100%)"
    }))
    asyncio.run(enviar_comando_lg("toast", {"mensaje": "☀️ Modo Día LG: Brillo al 100% para máxima claridad"}))
    print(f"{Color.GREEN}[✓] LG 65\": Brillo al 100%, contraste 95% y ahorro de energía desactivado.{Color.END}\n")


def lg_cine():
    print(f"\n{Color.BOLD}🎬 [LG 65\"] ACTIVANDO MODO CINE (FILMMAKER MODE D65)...{Color.END}")
    asyncio.run(enviar_comando_lg("ajustes", {
        "category": "picture",
        "settings": {
            "pictureMode": "filmMaker",
            "energySaving": "off",
            "truMotion": "off"
        },
        "mensaje": "🎬 Modo Cine: Filmmaker Mode D65 activo"
    }))
    asyncio.run(enviar_comando_lg("toast", {"mensaje": "🎬 Modo Cine LG: Filmmaker Mode ON | 24fps puras | TruMotion OFF"}))
    print(f"{Color.GREEN}[✓] LG 65\": Filmmaker Mode activo (colores D65 de director, sin suavizado artificial).{Color.END}\n")


def lg_juego():
    print(f"\n{Color.BOLD}🎮 [LG 65\"] ACTIVANDO MODO JUEGO (LATENCIA MÍNIMA ~9ms)...{Color.END}")
    asyncio.run(enviar_comando_lg("ajustes", {
        "category": "picture",
        "settings": {
            "pictureMode": "game",
            "energySaving": "off",
            "truMotion": "off",
            "gameMode": "on",
            "hdrGameHGiG": "on"
        },
        "mensaje": "🎮 Modo Juego: Game Optimizer ON | ALLM ON | HGiG ON"
    }))
    asyncio.run(enviar_comando_lg("toast", {"mensaje": "🎮 Modo Juego LG: Input Lag ~9ms | ALLM ON | HGiG ON"}))
    print(f"{Color.GREEN}[✓] LG 65\": Game Optimizer ON (~9ms lag, ALLM para consolas/PC, HGiG calibrado).{Color.END}\n")


def lg_descanso():
    print(f"\n{Color.BOLD}👁️ [LG 65\"] ACTIVANDO MODO DESCANSO VISUAL (CONFORT OCULAR)...{Color.END}")
    asyncio.run(enviar_comando_lg("ajustes", {
        "category": "picture",
        "settings": {
            "backlight": "30",
            "brightness": "48",
            "colorTemperature": "warm50",
            "energySaving": "med"
        },
        "mensaje": "👁️ Confort Ocular: Temperatura Cálida (Warm 50) | Filtro Azul"
    }))
    asyncio.run(enviar_comando_lg("toast", {"mensaje": "👁️ Confort Ocular LG: Filtro de luz azul activado (Warm 50)"}))
    print(f"{Color.GREEN}[✓] LG 65\": Modo Descanso Visual activado (filtra luz azul y relaja la vista).{Color.END}\n")


def lg_solo_audio():
    print(f"\n{Color.BOLD}📻 [LG 65\"] ACTIVANDO MODO SOLO AUDIO...{Color.END}")
    asyncio.run(enviar_comando_lg("solo_audio"))


def lg_volumen(nivel: int):
    nivel = max(0, min(100, nivel))
    asyncio.run(enviar_comando_lg("volumen", {"volumen": nivel}))


def lg_mute():
    asyncio.run(enviar_comando_lg("mute", {"mute": True}))
