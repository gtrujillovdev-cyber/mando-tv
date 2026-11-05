"""Control de la LG webOS (SSAP por WebSocket)."""
import asyncio
import json
import os
import subprocess
import threading
import time
import uuid
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


PERMISOS = [
    "LAUNCH", "LAUNCH_WEBAPP", "APP_TO_APP", "CLOSE", "TEST_OPEN", "TEST_PROTECTED",
    "CONTROL_AUDIO", "CONTROL_DISPLAY", "CONTROL_INPUT_JOYSTICK", "CONTROL_INPUT_MEDIA_RECORDING",
    "CONTROL_INPUT_MEDIA_PLAYBACK", "CONTROL_INPUT_TV", "CONTROL_POWER", "CONTROL_TV_SCREEN",
    "CONTROL_TV_STANBY", "CONTROL_MOUSE_AND_KEYBOARD", "CONTROL_INPUT_TEXT",
    "READ_APP_STATUS", "READ_CURRENT_CHANNEL", "READ_INPUT_DEVICE_LIST", "READ_NETWORK_STATE",
    "READ_RUNNING_APPS", "READ_TV_CHANNEL_LIST", "READ_POWER_STATE", "READ_COUNTRY_INFO",
    "READ_SETTINGS", "READ_INSTALLED_APPS", "WRITE_NOTIFICATION_TOAST", "WRITE_NOTIFICATION_ALERT",
]

MANIFEST = {
    "manifestVersion": 1,
    "appVersion": "1.1",
    "permissions": PERMISOS,
    "signed": {
        "created": "20140509",
        "appId": "com.lge.test",
        "vendorId": "com.lge",
        "localizedAppNames": {"": "LG Remote App"},
        "localizedVendorNames": {"": "LG Electronics"},
        "permissions": PERMISOS,
        "serial": "2f930e2d2cfe083771f68e4fe54be0a1",
    },
}

# Teclas que se envían por el socket de puntero (latencia mínima, conexión persistente).
TECLAS_PUNTERO = {
    "UP", "DOWN", "LEFT", "RIGHT", "ENTER", "BACK", "EXIT", "MENU", "HOME", "INFO",
    "CHANNELUP", "CHANNELDOWN", "VOLUMEUP", "VOLUMEDOWN", "MUTE",
    "RED", "GREEN", "YELLOW", "BLUE",
}

# Teclas con endpoint SSAP nativo.
TECLAS_SSAP = {
    "INPUT": ("ssap://system.launcher/open", {"id": "com.webos.app.inputpicker"}),
    "PLAY": ("ssap://media.controls/play", None),
    "PAUSE": ("ssap://media.controls/pause", None),
    "REWIND": ("ssap://media.controls/rewind", None),
    "FASTFORWARD": ("ssap://media.controls/fastForward", None),
}

_loop_bg: Optional[asyncio.AbstractEventLoop] = None
_loop_lock = threading.Lock()


def _loop() -> asyncio.AbstractEventLoop:
    """Bucle asyncio en segundo plano que mantiene viva la conexión con la LG."""
    global _loop_bg
    with _loop_lock:
        if _loop_bg is None:
            _loop_bg = asyncio.new_event_loop()
            threading.Thread(target=_loop_bg.run_forever, name="lg-loop", daemon=True).start()
    return _loop_bg


class _Sesion:
    """Conexión SSAP persistente + socket de puntero persistente."""

    def __init__(self):
        self.ws = None
        self.ptr = None
        self.lock: Optional[asyncio.Lock] = None

    async def cerrar(self):
        for c in (self.ptr, self.ws):
            try:
                if c is not None:
                    await c.close()
            except Exception:
                pass
        self.ws = self.ptr = None

    async def conectar(self):
        import websockets
        cfg = cargar_config_lg()
        ws = await websockets.connect(f"ws://{cfg.get('ip', IP_LG)}:3000/", ping_interval=None, open_timeout=3.0)
        await ws.send(json.dumps({"type": "register", "id": "reg", "payload": {
            "forcePairing": False, "pairingType": "PROMPT",
            "client-key": cfg.get("client_key"), "manifest": MANIFEST}}))
        while True:  # esperar 'registered' (ignora 'response' del aviso de emparejamiento)
            msg = json.loads(await asyncio.wait_for(ws.recv(), 10))
            if msg.get("type") == "registered":
                break
            if msg.get("type") == "error":
                await ws.close()
                raise RuntimeError(msg.get("error"))
        self.ws = ws

    async def req(self, uri: str, payload: Optional[Dict] = None, timeout: float = 5.0) -> Dict:
        if self.ws is None:
            await self.conectar()
        rid = uuid.uuid4().hex[:8]
        msg = {"type": "request", "id": rid, "uri": uri}
        if payload:
            msg["payload"] = payload
        await self.ws.send(json.dumps(msg))
        while True:
            r = json.loads(await asyncio.wait_for(self.ws.recv(), timeout))
            if r.get("id") == rid:
                return r

    async def boton(self, nombre: str):
        import websockets
        if self.ptr is None:
            r = await self.req("ssap://com.webos.service.networkinput/getPointerInputSocket")
            sock = r.get("payload", {}).get("socketPath")
            if not sock:
                raise RuntimeError(r.get("error") or "sin socket de puntero")
            self.ptr = await websockets.connect(sock, ping_interval=None, open_timeout=3.0)
        await self.ptr.send(f"type:button\nname:{nombre}\n\n")


_sesion = _Sesion()


async def _con_reintento(fn):
    """Ejecuta fn(); si la conexión cayó, reconecta y reintenta una vez."""
    if _sesion.lock is None:
        _sesion.lock = asyncio.Lock()
    async with _sesion.lock:
        try:
            return await fn()
        except Exception:
            await _sesion.cerrar()
            return await fn()


async def _alerta_con_ajuste(mensaje: str, categoria: str, ajustes: Dict):
    """Aplica ajustes de sistema mediante una alerta con onclose (Luna) y la cierra al instante."""
    r = await _sesion.req("ssap://system.notifications/createAlert", {
        "message": mensaje, "modal": False, "buttons": [{"label": "OK", "focus": True}],
        "onclose": {"uri": "luna://com.webos.settingsservice/setSystemSettings",
                    "params": {"category": categoria, "settings": ajustes}},
        "type": "confirm", "isSysReq": True})
    aid = r.get("payload", {}).get("alertId")
    if aid:
        await asyncio.sleep(0.3)
        await _sesion.req("ssap://system.notifications/closeAlert", {"alertId": aid})


async def _ejecutar(accion: str, p: Dict):
    s = _sesion
    if accion == "apagar":
        await s.req("ssap://system/turnOff")
        print(f"{Color.GREEN}[✓] LG 65\": Apagada correctamente.{Color.END}")
        return True
    if accion == "toast":
        await s.req("ssap://system.notifications/createToast", {"message": p.get("mensaje", "")})
        return True
    if accion == "volumen":
        await s.req("ssap://audio/setVolume", {"volume": p.get("volumen", 15)})
        return True
    if accion == "mute":
        await s.req("ssap://audio/setMute", {"mute": p.get("mute", True)})
        return True
    if accion == "vol_up":
        await s.req("ssap://audio/volumeUp")
        return True
    if accion == "vol_down":
        await s.req("ssap://audio/volumeDown")
        return True
    if accion == "ajustes":
        await _alerta_con_ajuste(p.get("mensaje", "Aplicando configuración..."),
                                 p.get("category", "picture"), p.get("settings", {}))
        return True
    if accion == "solo_audio":
        await _alerta_con_ajuste("🌙 Pantalla apagada (Solo Audio). Pulsa cualquier tecla para reactivar.",
                                 "picture", {"energySaving": "screen_off"})
        return True
    if accion == "app":
        r = await s.req("ssap://system.launcher/open", {"id": p.get("id", "youtube.leanback.v4"), "params": p.get("params", {})})
        return r.get("payload", {}).get("returnValue", True)
    if accion == "audio_output":
        r = await s.req("ssap://audio/changeSoundOutput", {"output": p.get("output", "external_arc")})
        return r.get("payload", {}).get("returnValue", True)
    if accion == "status":
        r = await s.req("ssap://com.webos.applicationManager/getForegroundAppInfo")
        return r.get("payload", {}).get("appId", "Desconocida")
    if accion == "tecla":
        tecla = p.get("tecla", "ENTER").upper()
        if tecla in TECLAS_SSAP:
            uri, pl = TECLAS_SSAP[tecla]
            r = await s.req(uri, pl)
            return r.get("type") != "error"
        await s.boton(tecla)  # puntero: UP/DOWN/LEFT/RIGHT/ENTER/BACK/HOME/MENU/CH±...
        return True
    return False


async def enviar_comando_lg(accion: str, payload_extra: Optional[Dict] = None) -> bool:
    """Envía una acción a la LG reutilizando la conexión persistente (sin re-registro por pulsación)."""
    try:
        import websockets  # noqa: F401
    except ImportError:
        print(f"{Color.RED}[!] Librería 'websockets' no disponible.{Color.END}")
        return False
    p = payload_extra or {}
    fut = asyncio.run_coroutine_threadsafe(_con_reintento(lambda: _ejecutar(accion, p)), _loop())
    try:
        return await asyncio.wrap_future(fut)
    except Exception as e:
        print(f"{Color.YELLOW}[!] LG 65\" ({IP_LG}): {accion} falló: {e}{Color.END}")
        return False


def precalentar():
    """Abre la conexión con la LG al arrancar el servidor para que la primera pulsación sea instantánea."""
    asyncio.run_coroutine_threadsafe(_con_reintento(lambda: _ejecutar("status", {})), _loop())


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
                subprocess.run(f"pkill -P {pid} 2>/dev/null; kill -9 {pid} 2>/dev/null", shell=True)
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
