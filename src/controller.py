#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
controller.py - Hardware Abstraction Layer for Smart TVs
Supports:
  1. LG Smart TV (webOS) via SSAP WebSocket & Wake-on-LAN.
  2. Xiaomi MiTV / Android TV via ADB (Android Debug Bridge).
  3. Presets: Modo Noche, Día, Cine, Juego, Solo Audio.
  4. Non-blocking asynchronous timers and soft-standby (0% backlight preservation).
"""

import os
import json
import time
import socket
import asyncio
import subprocess
import threading
from typing import Optional, Dict, Any


class TVConfig:
    IP_LG = os.environ.get("LG_TV_IP", "192.168.1.250")
    MAC_LG = os.environ.get("LG_TV_MAC", "20:fc:da:90:54:1d")
    PORT_LG = int(os.environ.get("LG_TV_PORT", "3000"))

    IP_XIAOMI = os.environ.get("XIAOMI_TV_IP", "192.168.1.238")
    PORT_XIAOMI = int(os.environ.get("XIAOMI_TV_PORT", "5555"))

    CONFIG_LG_FILE = os.path.expanduser("~/.config/lg_tv/config.json")


def enviar_wake_on_lan(mac_address: str) -> bool:
    """Envía un paquete mágico Wake-on-LAN para encender dispositivos en la red local."""
    try:
        mac_limpia = mac_address.replace(":", "").replace("-", "")
        if len(mac_limpia) != 12:
            return False
        payload = bytes.fromhex("FF" * 6 + mac_limpia * 16)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(payload, ("255.255.255.255", 9))
            s.sendto(payload, ("192.168.1.255", 9))
        return True
    except Exception:
        return False


class LGWebOSController:
    """Controlador para LG webOS mediante WebSocket SSAP y WoL."""

    def __init__(self, ip: str = TVConfig.IP_LG, mac: str = TVConfig.MAC_LG, port: int = TVConfig.PORT_LG):
        self.ip = ip
        self.mac = mac
        self.port = port
        self.client_key = self._cargar_client_key()
        self.timer_cancel_event: Optional[threading.Event] = None
        self.timer_fin: float = 0.0

    def _cargar_client_key(self) -> Optional[str]:
        if os.path.exists(TVConfig.CONFIG_LG_FILE):
            try:
                with open(TVConfig.CONFIG_LG_FILE, "r") as f:
                    data = json.load(f)
                    return data.get("client_key")
            except Exception:
                pass
        return None

    def is_online(self) -> bool:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.15)
        res = s.connect_ex((self.ip, self.port)) == 0
        s.close()
        return res

    def encender(self) -> bool:
        return enviar_wake_on_lan(self.mac)

    async def enviar_comando_ssap(self, comando: str, payload: Optional[Dict] = None) -> bool:
        """Envía comandos mediante WebSocket al bus SSAP de LG webOS."""
        try:
            import websockets
        except ImportError:
            # Fallback en caso de no tener librería websockets externa instalada
            return False

        uri = f"ws://{self.ip}:{self.port}"
        try:
            async with websockets.connect(uri, timeout=1.5) as ws:
                # Handshake de registro
                handshake = {
                    "type": "register",
                    "id": "register_mando",
                    "payload": {
                        "forcePairing": False,
                        "pairingType": "PROMPT",
                        "client-key": self.client_key or ""
                    }
                }
                await ws.send(json.dumps(handshake))
                await ws.recv()

                # Despacho de comando específico
                msg = None
                if comando == "toast":
                    msg = {
                        "type": "request",
                        "id": f"req_{time.time()}",
                        "uri": "ssap://system.notifications/createToast",
                        "payload": {"message": payload.get("mensaje", "")}
                    }
                elif comando == "retroiluminacion":
                    val = max(0, min(100, int(payload.get("valor", 100))))
                    msg = {
                        "type": "request",
                        "id": f"req_{time.time()}",
                        "uri": "ssap://com.webos.service.tv.display/setBacklight",
                        "payload": {"backlight": val}
                    }
                elif comando == "volumen":
                    val = max(0, min(100, int(payload.get("valor", 20))))
                    msg = {
                        "type": "request",
                        "id": f"req_{time.time()}",
                        "uri": "ssap://audio/setVolume",
                        "payload": {"volume": val}
                    }
                elif comando == "mute":
                    msg = {
                        "type": "request",
                        "id": f"req_{time.time()}",
                        "uri": "ssap://audio/setMute",
                        "payload": {"mute": payload.get("mute", True)}
                    }
                elif comando == "apagar":
                    msg = {
                        "type": "request",
                        "id": f"req_{time.time()}",
                        "uri": "ssap://system/turnOff"
                    }
                elif comando == "pantalla_off":
                    msg = {
                        "type": "request",
                        "id": f"req_{time.time()}",
                        "uri": "ssap://com.webos.service.tvpower/power/turnOffScreen"
                    }
                elif comando == "audio_output":
                    out = payload.get("output", "external_arc")
                    msg = {
                        "type": "request",
                        "id": f"req_{time.time()}",
                        "uri": "ssap://audio/changeSoundOutput",
                        "payload": {"output": out}
                    }
                elif comando == "vol_up":
                    msg = {
                        "type": "request",
                        "id": f"req_{time.time()}",
                        "uri": "ssap://audio/volumeUp"
                    }
                elif comando == "vol_down":
                    msg = {
                        "type": "request",
                        "id": f"req_{time.time()}",
                        "uri": "ssap://audio/volumeDown"
                    }
                elif comando == "app":
                    msg = {
                        "type": "request",
                        "id": f"req_{time.time()}",
                        "uri": "ssap://system.launcher/open",
                        "payload": {
                            "id": payload.get("id", ""),
                            "params": payload.get("params", {})
                        }
                    }
                elif comando == "tecla":
                    # Teclas comunes vía luna service
                    tecla = payload.get("tecla", "")
                    mapping = {
                        "UP": "ssap://media.controls/fastForward",
                        "DOWN": "ssap://media.controls/rewind",
                        "PLAY": "ssap://media.controls/play",
                        "PAUSE": "ssap://media.controls/pause",
                        "STOP": "ssap://media.controls/stop",
                        "REWIND": "ssap://media.controls/rewind",
                        "FASTFORWARD": "ssap://media.controls/fastForward"
                    }
                    if tecla in mapping:
                        msg = {"type": "request", "id": f"req_{time.time()}", "uri": mapping[tecla]}

                if msg:
                    await ws.send(json.dumps(msg))
                return True
        except Exception:
            return False

    def apagar(self):
        self.cancelar_timer()
        asyncio.run(self.enviar_comando_ssap("apagar"))

    def programar_timer(self, minutos: float = 90.0):
        self.cancelar_timer()
        self.timer_cancel_event = threading.Event()
        self.timer_fin = time.time() + (minutos * 60)

        def _hilo(evt, duracion):
            if not evt.wait(duracion):
                self.apagar()

        t = threading.Thread(target=_hilo, args=(self.timer_cancel_event, minutos * 60), daemon=True)
        t.start()

    def cancelar_timer(self):
        if self.timer_cancel_event:
            self.timer_cancel_event.set()
            self.timer_cancel_event = None
        self.timer_fin = 0.0

    def tiempo_restante_timer(self) -> int:
        if self.timer_fin > time.time():
            return int((self.timer_fin - time.time()) / 60)
        return 0


class AndroidTVController:
    """Controlador para Xiaomi MiTV / Android TV vía ADB ultra-optimizado."""

    def __init__(self, ip: str = TVConfig.IP_XIAOMI, port: int = TVConfig.PORT_XIAOMI):
        self.ip = ip
        self.port = port
        self.timer_cancel_event: Optional[threading.Event] = None
        self.timer_fin: float = 0.0

    def is_online(self) -> bool:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.15)
        res = s.connect_ex((self.ip, self.port)) == 0
        s.close()
        return res

    def ejecutar_adb(self, comando: str) -> bool:
        """Ejecuta comando ADB en la TV sin reconectar innecesariamente."""
        target = f"{self.ip}:{self.port}"
        full_cmd = f"adb -s {target} shell {comando}"
        try:
            res = subprocess.run(full_cmd, shell=True, capture_output=True, timeout=2.5)
            if res.returncode != 0:
                # Si falló, intentar reconectar una vez
                subprocess.run(f"adb connect {target}", shell=True, capture_output=True, timeout=2.0)
                subprocess.run(full_cmd, shell=True, capture_output=True, timeout=2.0)
            return True
        except Exception:
            return False

    def encender(self) -> bool:
        """Enciende o despierta la TV restaurando retroiluminación y audio."""
        target = f"{self.ip}:{self.port}"
        subprocess.run(f"adb connect {target}", shell=True, capture_output=True, timeout=1.5)
        # Despertar y restaurar brillo de seguridad
        cmds = (
            "input keyevent 224 && "
            "settings put system screen_brightness 128 && "
            "cmd audio set-volume 3 15 && "
            "cmd audio set-volume-mute 3 false"
        )
        return self.ejecutar_adb(cmds)

    def apagar_standby(self):
        """
        MODO STANDBY INTELIGENTE:
        Mantiene el Wi-Fi y ADB vivos bajando retroiluminación a 0%, volumen a 0%
        y pausando reproducción. Esto soluciona la pérdida de Wi-Fi al apagar.
        """
        self.cancelar_timer()
        cmds = (
            "input keyevent 86 || input keyevent 127 ; "
            "settings put system screen_brightness 0 ; "
            "cmd audio set-volume 3 0 ; "
            "cmd audio set-volume-mute 3 true"
        )
        self.ejecutar_adb(cmds)

    def apagar_total(self):
        """Apagado profundo de hardware (corta Wi-Fi)."""
        self.cancelar_timer()
        self.ejecutar_adb("input keyevent 26")

    def programar_timer(self, minutos: float = 90.0):
        self.cancelar_timer()
        self.timer_cancel_event = threading.Event()
        self.timer_fin = time.time() + (minutos * 60)

        def _hilo(evt, duracion):
            if not evt.wait(duracion):
                self.apagar_standby()

        t = threading.Thread(target=_hilo, args=(self.timer_cancel_event, minutos * 60), daemon=True)
        t.start()

    def cancelar_timer(self):
        if self.timer_cancel_event:
            self.timer_cancel_event.set()
            self.timer_cancel_event = None
        self.timer_fin = 0.0

    def tiempo_restante_timer(self) -> int:
        if self.timer_fin > time.time():
            return int((self.timer_fin - time.time()) / 60)
        return 0


class UnifiedTVController:
    """Controlador unificado que orquesta ambas pantallas y gestiona los presets."""

    def __init__(self):
        self.lg = LGWebOSController()
        self.xiaomi = AndroidTVController()

    def modo_noche(self, minutos: float = 90.0):
        """Brillo 6%, volumen suave y temporizador de 90m."""
        # LG
        threading.Thread(target=lambda: asyncio.run(self.lg.enviar_comando_ssap("retroiluminacion", {"valor": 6})), daemon=True).start()
        threading.Thread(target=lambda: asyncio.run(self.lg.enviar_comando_ssap("volumen", {"valor": 12})), daemon=True).start()
        self.lg.programar_timer(minutos)
        # Xiaomi
        threading.Thread(target=lambda: self.xiaomi.ejecutar_adb("settings put system screen_brightness 15 && cmd audio set-volume 3 5"), daemon=True).start()
        self.xiaomi.programar_timer(minutos)

    def modo_dia(self):
        """Brillo 100%, volumen normal y cancelación de timers."""
        self.lg.cancelar_timer()
        self.xiaomi.cancelar_timer()
        threading.Thread(target=lambda: asyncio.run(self.lg.enviar_comando_ssap("retroiluminacion", {"valor": 100})), daemon=True).start()
        threading.Thread(target=lambda: asyncio.run(self.lg.enviar_comando_ssap("volumen", {"valor": 25})), daemon=True).start()
        threading.Thread(target=lambda: self.xiaomi.ejecutar_adb("settings put system screen_brightness 255 && cmd audio set-volume 3 15"), daemon=True).start()

    def modo_cine(self):
        """Ambiente oscuro: Brillo 30%, volumen óptimo."""
        threading.Thread(target=lambda: asyncio.run(self.lg.enviar_comando_ssap("retroiluminacion", {"valor": 30})), daemon=True).start()
        threading.Thread(target=lambda: self.xiaomi.ejecutar_adb("settings put system screen_brightness 75"), daemon=True).start()

    def modo_juego(self):
        """Máxima reactividad y brillo dinámico."""
        threading.Thread(target=lambda: asyncio.run(self.lg.enviar_comando_ssap("retroiluminacion", {"valor": 90})), daemon=True).start()
        threading.Thread(target=lambda: self.xiaomi.ejecutar_adb("settings put system screen_brightness 220"), daemon=True).start()

    def solo_audio(self):
        """Apaga panel OLED / LCD manteniendo streaming de audio."""
        threading.Thread(target=lambda: asyncio.run(self.lg.enviar_comando_ssap("pantalla_off")), daemon=True).start()
        threading.Thread(target=lambda: self.xiaomi.ejecutar_adb("settings put system screen_brightness 0"), daemon=True).start()


tv_hub = UnifiedTVController()
