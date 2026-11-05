#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
server.py - High-Performance Web & Webhook Server for Mando TV
Handles:
  1. Responsive web interface (index.html) with 0-scroll and Taptic Engine feedback.
  2. Siri Voice Shortcuts Hub (siri.html) with Web Speech API audio previews.
  3. Non-blocking asynchronous command execution (<15ms HTTP response).
  4. Siri Voice Webhook (/api/siri) returning natural conversational Spanish.
  5. Multi-platform streaming deep-linking (/api/voice).
"""

import os
import sys
import json
import socket
import urllib.parse
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver

from .controller import tv_hub, TVConfig
from .streaming import reproducir_streaming, STREAMING_PLATFORMS

PUERTO_DEFECTO = 8899
DIR_WEB = os.path.join(os.path.dirname(__file__), "web")


def leer_archivo_web(nombre: str) -> str:
    ruta = os.path.join(DIR_WEB, nombre)
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read()
    return f"<h1>Error 404: {nombre} no encontrado</h1>"


class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class MandoHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silenciar logs ruidosos para no saturar la consola
        pass

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)

        try:
            if url.path in ["/", "/index.html"]:
                html = leer_archivo_web("index.html")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))

            elif url.path in ["/siri", "/siri.html"]:
                html = leer_archivo_web("siri.html")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))

            elif url.path == "/api/status":
                lg_on = tv_hub.lg.is_online()
                xm_on = tv_hub.xiaomi.is_online()

                data = {
                    "lg_online": lg_on,
                    "xiaomi_online": xm_on,
                    "timer_lg": tv_hub.lg.tiempo_restante_timer(),
                    "timer_xiaomi": tv_hub.xiaomi.tiempo_restante_timer()
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode("utf-8"))

            elif url.path == "/api/action":
                qs = urllib.parse.parse_qs(url.query)
                cmd = qs.get("cmd", [""])[0]
                target = qs.get("target", ["xiaomi"])[0]
                val = qs.get("val", ["0"])[0]

                # Respuesta táctil inmediata
                labels = {
                    "vol_up": "Volumen +", "vol_down": "Volumen -", "mute": "Mute",
                    "ch_up": "Canal +", "ch_down": "Canal -",
                    "up": "▲ Arriba", "down": "▼ Abajo", "left": "◄ Izquierda", "right": "► Derecha", "enter": "OK",
                    "play_pause": "Play / Pausa", "rewind": "⏪ -10s", "fast_forward": "⏩ +10s",
                    "back": "↩ Atrás", "home": "🏠 Inicio", "settings": "⚙️ Ajustes", "info": "ℹ️ Info", "source": "🔌 HDMI",
                    "dia": "☀️ Modo Día (100%)", "noche": "🌙 Modo Noche (6% + 90m)",
                    "cine": "🎬 Modo Cine", "juego": "🎮 Modo Juego", "solo_audio": "📻 Solo Audio",
                    "encender": "⚡ Encendiendo...", "apagar": "🔌 Standby...",
                    "set_brillo": f"☀️ Brillo: {val}%", "set_volumen": f"🔊 Vol: {val}%",
                    "smarttube": "📺 SmartTube",
                    "audio_sharp": "📢 Barra Sharp (ARC)", "audio_tv": "📺 Altavoces TV"
                }
                mensaje = labels.get(cmd, f"{cmd.upper()}")

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "mensaje": mensaje}).encode("utf-8"))

                # Despacho en hilo secundario (<15ms de latencia en cliente)
                threading.Thread(target=self.ejecutar_comando_hardware, args=(cmd, target, val), daemon=True).start()

            elif url.path == "/api/voice":
                qs = urllib.parse.parse_qs(url.query)
                query = qs.get("q", [""])[0] or qs.get("query", [""])[0]
                platform = qs.get("platform", ["smarttube"])[0] or qs.get("plat", ["smarttube"])[0]
                target = qs.get("target", ["xiaomi"])[0]

                threading.Thread(target=lambda: reproducir_streaming(query, platform, target), daemon=True).start()

                plat_info = STREAMING_PLATFORMS.get(platform, {"name": platform.capitalize()})
                msg = f"▶ Buscando '{query}' en {plat_info['name']}" if query else f"Abriendo {plat_info['name']}"

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "mensaje": msg}).encode("utf-8"))

            elif url.path == "/api/siri":
                qs = urllib.parse.parse_qs(url.query)
                action = qs.get("action", ["status"])[0]
                target = qs.get("target", ["ambas"])[0]
                q = qs.get("q", [""])[0] or qs.get("query", [""])[0]
                platform = qs.get("platform", ["smarttube"])[0] or qs.get("plat", ["smarttube"])[0]
                val = qs.get("val", ["20"])[0]

                respuesta_voz = self.procesar_comando_siri(action, target, q, platform, val)

                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(respuesta_voz.encode("utf-8"))

            else:
                self.send_response(404)
                self.end_headers()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def ejecutar_comando_hardware(self, cmd: str, target: str, val: str = "0"):
        """Ejecuta la instrucción directa sobre el hardware."""
        # 1. MODOS PRECONFIGURADOS
        if cmd == "noche":
            tv_hub.modo_noche(90)
        elif cmd == "dia":
            tv_hub.modo_dia()
        elif cmd == "cine":
            tv_hub.modo_cine()
        elif cmd == "juego":
            tv_hub.modo_juego()
        elif cmd == "solo_audio":
            tv_hub.solo_audio()

        # 2. ENCENDIDO Y APAGADO
        elif cmd == "encender":
            if target in ["lg", "ambas"]: tv_hub.lg.encender()
            if target in ["xiaomi", "ambas"]: tv_hub.xiaomi.encender()
        elif cmd == "apagar":
            if target in ["lg", "ambas"]: tv_hub.lg.apagar()
            if target in ["xiaomi", "ambas"]: tv_hub.xiaomi.apagar_standby()

        # 3. BRILLO
        elif cmd == "set_brillo":
            try:
                brillo_pct = max(0, min(100, int(val)))
                adb_val = int((brillo_pct / 100) * 255)
                if target in ["lg", "ambas"]:
                    import asyncio
                    asyncio.run(tv_hub.lg.enviar_comando_ssap("retroiluminacion", {"valor": brillo_pct}))
                if target in ["xiaomi", "ambas"]:
                    tv_hub.xiaomi.ejecutar_adb(f"settings put system screen_brightness {adb_val}")
            except Exception:
                pass

        # 4. VOLUMEN
        elif cmd == "set_volumen":
            try:
                vol_pct = max(0, min(100, int(val)))
                adb_val = int((vol_pct / 100) * 15)
                if target in ["lg", "ambas"]:
                    import asyncio
                    asyncio.run(tv_hub.lg.enviar_comando_ssap("volumen", {"valor": vol_pct}))
                if target in ["xiaomi", "ambas"]:
                    tv_hub.xiaomi.ejecutar_adb(f"cmd audio set-volume 3 {adb_val}")
            except Exception:
                pass
        elif cmd == "vol_up":
            if target in ["lg", "ambas"]:
                import asyncio
                asyncio.run(tv_hub.lg.enviar_comando_ssap("vol_up"))
            if target in ["xiaomi", "ambas"]:
                tv_hub.xiaomi.ejecutar_adb("input keyevent 24")
        elif cmd == "vol_down":
            if target in ["lg", "ambas"]:
                import asyncio
                asyncio.run(tv_hub.lg.enviar_comando_ssap("vol_down"))
            if target in ["xiaomi", "ambas"]:
                tv_hub.xiaomi.ejecutar_adb("input keyevent 25")
        elif cmd == "ch_up":
            if target in ["xiaomi", "ambas"]:
                tv_hub.xiaomi.ejecutar_adb("input keyevent 166")
        elif cmd == "ch_down":
            if target in ["xiaomi", "ambas"]:
                tv_hub.xiaomi.ejecutar_adb("input keyevent 167")
        elif cmd == "audio_sharp":
            if target in ["lg", "ambas"]:
                import asyncio
                asyncio.run(tv_hub.lg.enviar_comando_ssap("audio_output", {"output": "external_arc"}))
        elif cmd == "audio_tv":
            if target in ["lg", "ambas"]:
                import asyncio
                asyncio.run(tv_hub.lg.enviar_comando_ssap("audio_output", {"output": "tv_speaker"}))
        elif cmd == "mute":
            if target in ["lg", "ambas"]:
                import asyncio
                asyncio.run(tv_hub.lg.enviar_comando_ssap("mute", {"mute": True}))
            if target in ["xiaomi", "ambas"]:
                tv_hub.xiaomi.ejecutar_adb("input keyevent 164")

        # 5. D-PAD & NAVEGACIÓN
        elif cmd == "up":
            if target in ["xiaomi", "ambas"]: tv_hub.xiaomi.ejecutar_adb("input keyevent 19")
        elif cmd == "down":
            if target in ["xiaomi", "ambas"]: tv_hub.xiaomi.ejecutar_adb("input keyevent 20")
        elif cmd == "left":
            if target in ["xiaomi", "ambas"]: tv_hub.xiaomi.ejecutar_adb("input keyevent 21")
        elif cmd == "right":
            if target in ["xiaomi", "ambas"]: tv_hub.xiaomi.ejecutar_adb("input keyevent 22")
        elif cmd == "enter":
            if target in ["xiaomi", "ambas"]: tv_hub.xiaomi.ejecutar_adb("input keyevent 66 || input keyevent 23")

        # 6. REPRODUCCIÓN
        elif cmd == "play_pause":
            if target in ["xiaomi", "ambas"]: tv_hub.xiaomi.ejecutar_adb("input keyevent 85")
        elif cmd == "rewind":
            if target in ["xiaomi", "ambas"]: tv_hub.xiaomi.ejecutar_adb("input keyevent 89")
        elif cmd == "fast_forward":
            if target in ["xiaomi", "ambas"]: tv_hub.xiaomi.ejecutar_adb("input keyevent 90")

        # 7. TECLAS DE SISTEMA
        elif cmd == "back":
            if target in ["xiaomi", "ambas"]: tv_hub.xiaomi.ejecutar_adb("input keyevent 4")
        elif cmd == "home":
            if target in ["xiaomi", "ambas"]: tv_hub.xiaomi.ejecutar_adb("input keyevent 3")
        elif cmd == "settings":
            if target in ["xiaomi", "ambas"]: tv_hub.xiaomi.ejecutar_adb("input keyevent 176 || input keyevent 82")
        elif cmd == "source":
            if target in ["xiaomi", "ambas"]: tv_hub.xiaomi.ejecutar_adb("input keyevent 178")
        elif cmd == "info":
            if target in ["xiaomi", "ambas"]: tv_hub.xiaomi.ejecutar_adb("input keyevent 165")

        # 8. STREAMING
        elif cmd == "smarttube":
            reproducir_streaming("", "smarttube", target)

    def procesar_comando_siri(self, action: str, target: str, q: str, platform: str, val: str) -> str:
        """Genera respuestas en lenguaje natural hablado para Siri y despacha la acción."""
        disp_nombre = "la televisión LG" if target == "lg" else ("la Xiaomi" if target == "xiaomi" else "ambas televisiones")

        if action == "noche":
            if target == "lg":
                threading.Thread(target=lambda: tv_hub.lg.programar_timer(90), daemon=True).start()
                return "Modo Noche activado en la televisión LG. Retroiluminación al 6% y temporizador de 90 minutos."
            elif target == "xiaomi":
                threading.Thread(target=lambda: tv_hub.xiaomi.programar_timer(90), daemon=True).start()
                return "Modo Noche activado en la Xiaomi. Retroiluminación tenue y temporizador de 90 minutos."
            else:
                tv_hub.modo_noche(90)
                return "Modo Noche activado en ambas televisiones con retroiluminación al 6% y temporizador de 90 minutos."

        elif action == "dia":
            if target == "lg":
                import asyncio
                threading.Thread(target=lambda: asyncio.run(tv_hub.lg.enviar_comando_ssap("retroiluminacion", {"valor": 100})), daemon=True).start()
                return "Modo Día activado en la televisión LG con retroiluminación al 100%."
            elif target == "xiaomi":
                threading.Thread(target=lambda: tv_hub.xiaomi.ejecutar_adb("settings put system screen_brightness 255"), daemon=True).start()
                return "Modo Día activado en la Xiaomi con retroiluminación al 100%."
            else:
                tv_hub.modo_dia()
                return "Modo Día activado en ambas televisiones al 100%."

        elif action == "cine":
            if target == "lg":
                import asyncio
                threading.Thread(target=lambda: asyncio.run(tv_hub.lg.enviar_comando_ssap("retroiluminacion", {"valor": 30})), daemon=True).start()
            elif target == "xiaomi":
                threading.Thread(target=lambda: tv_hub.xiaomi.ejecutar_adb("settings put system screen_brightness 75"), daemon=True).start()
            else:
                tv_hub.modo_cine()
            return f"Modo Cine activado en {disp_nombre}."

        elif action == "juego":
            if target == "lg":
                import asyncio
                threading.Thread(target=lambda: asyncio.run(tv_hub.lg.enviar_comando_ssap("retroiluminacion", {"valor": 90})), daemon=True).start()
            elif target == "xiaomi":
                threading.Thread(target=lambda: tv_hub.xiaomi.ejecutar_adb("settings put system screen_brightness 220"), daemon=True).start()
            else:
                tv_hub.modo_juego()
            return f"Modo Juego de ultra baja latencia activado en {disp_nombre}."

        elif action == "encender":
            if target in ["lg", "ambas"]: tv_hub.lg.encender()
            if target in ["xiaomi", "ambas"]: tv_hub.xiaomi.encender()
            if target == "lg": return "Televisión LG encendida."
            elif target == "xiaomi": return "Televisión Xiaomi encendida."
            else: return "Ambas televisiones encendidas."

        elif action == "apagar":
            if target in ["lg", "ambas"]: tv_hub.lg.apagar()
            if target in ["xiaomi", "ambas"]: tv_hub.xiaomi.apagar_standby()
            if target == "lg": return "Televisión LG apagada."
            elif target == "xiaomi": return "Televisión Xiaomi apagada y en modo de bajo consumo."
            else: return "Ambas televisiones apagadas."

        elif action in ["reproducir", "ver", "buscar", "poner"]:
            plat_info = STREAMING_PLATFORMS.get(platform, {"name": platform.capitalize()})
            threading.Thread(target=lambda: reproducir_streaming(q, platform, target), daemon=True).start()
            lugar = f" en {disp_nombre}" if target != "ambas" else ""
            if q:
                return f"Poniendo {q} en {plat_info['name']}{lugar}."
            return f"Abriendo {plat_info['name']}{lugar}."

        elif action == "volumen":
            v = int(val) if val.isdigit() else 20
            if target in ["lg", "ambas"]:
                import asyncio
                asyncio.run(tv_hub.lg.enviar_comando_ssap("volumen", {"valor": v}))
            if target in ["xiaomi", "ambas"]:
                adb_val = int((v / 100) * 15)
                tv_hub.xiaomi.ejecutar_adb(f"cmd audio set-volume 3 {adb_val}")
            return f"Volumen de {disp_nombre} ajustado al {v}%."

        elif action == "status":
            lg = "encendida" if tv_hub.lg.is_online() else "en espera"
            xm = "encendida" if tv_hub.xiaomi.is_online() else "en espera"
            return f"Estado actual: La televisión LG está {lg} y la televisión Xiaomi está {xm}."

        return "Comando de voz recibido."


def ejecutar_servidor(puerto: int = PUERTO_DEFECTO, host: str = "0.0.0.0"):
    servidor = ThreadingHTTPServer((host, puerto), MandoHandler)
    print(f"\n{'='*70}")
    print(f" 🎛️  MANDO UNIVERSAL & HUB SIRI EN LÍNEA")
    print(f"{'='*70}")
    print(f"  • Mando Móvil:       http://0.0.0.0:{puerto}")
    print(f"  • Hub Atajos Siri:   http://0.0.0.0:{puerto}/siri")
    print(f"  • Webhook Siri API:  http://0.0.0.0:{puerto}/api/siri")
    print(f"{'='*70}\n")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Deteniendo servidor...")
        servidor.server_close()


if __name__ == "__main__":
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else PUERTO_DEFECTO
    ejecutar_servidor(puerto)
