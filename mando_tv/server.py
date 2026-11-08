"""Servidor HTTP: mando web, hub Siri y API."""
from . import config
from . import lg
from . import scenes
from . import timers
from . import xiaomi
import socketserver
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import socket
import urllib.parse
from .config import PUERTO
from .lg import encender_lg
from .streaming import reproducir_streaming
from .xiaomi import encender_xiaomi


def _leer_web(nombre: str) -> bytes:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", nombre), "rb") as f:
        return f.read()


class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class MandoHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)

        try:
            if url.path in ["/", "/index.html"]:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(_leer_web("index.html"))

            elif url.path in ["/siri", "/siri.html"]:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                host = self.headers.get("Host") or "localhost"
                self.wfile.write(_leer_web("siri.html").replace(b"__HOST__", host.encode()))

            elif url.path == "/api/status":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                
                lg_st = lg.estado_lg()
                xm_on = lg.puerto_abierto(config.IP_XIAOMI, 5555)
                data = {
                    "lg_online": lg_st == "on",
                    "lg_state": lg_st,
                    "xiaomi_online": xm_on,
                    "xiaomi_state": "on" if xm_on else "standby",
                    "timer_lg": timers.obtener_tiempo_restante_timer("lg"),
                    "timer_xiaomi": timers.obtener_tiempo_restante_timer("xiaomi")
                }
                self.wfile.write(json.dumps(data).encode("utf-8"))

            elif url.path == "/api/action":
                qs = urllib.parse.parse_qs(url.query)
                cmd = qs.get("cmd", [""])[0]
                target = qs.get("target", ["xiaomi"])[0]
                val = qs.get("val", ["0"])[0]

                # Respuesta HTTP instantánea (<10ms para el móvil)
                labels = {
                    "vol_up": "Volumen +", "vol_down": "Volumen -", "mute": "Mute",
                    "ch_up": "Canal +", "ch_down": "Canal -",
                    "up": "▲ Arriba", "down": "▼ Abajo", "left": "◄ Izquierda", "right": "► Derecha", "enter": "OK",
                    "play_pause": "Play / Pausa", "rewind": "⏪ -10s", "fast_forward": "⏩ +10s",
                    "back": "↩ Atrás", "home": "🏠 Inicio", "settings": "⚙️ Ajustes", "info": "ℹ️ Info", "source": "🔌 HDMI",
                    "dia": "☀️ Modo Día (100%)", "noche": "🌙 Modo Noche (6% + 90m)",
                    "cine": "🎬 Modo Cine", "juego": "🎮 Modo Juego", "descanso": "👁️ Modo Descanso", "solo_audio": "📻 Solo Audio",
                    "encender": "⚡ Encendiendo...", "apagar": "🔌 Apagando...",
                    "set_brillo": f"☀️ Brillo: {val}%", "set_volumen": f"🔊 Vol: {val}%",
                    "smarttube": "📺 SmartTube",
                    "audio_sharp": "📢 Barra Sharp (ARC)", "audio_tv": "📺 Altavoces TV"
                }
                mensaje = labels.get(cmd, f"{cmd.upper()}")

                # Si la tele destino no está encendida, avisar en vez de fingir éxito.
                if cmd not in ("encender", "cancelar_timer"):
                    estados = []
                    if target in ("lg", "ambas"):
                        estados.append(("LG", lg.estado_lg()))
                    if target in ("xiaomi", "ambas"):
                        estados.append(("XIAOMI", "on" if lg.puerto_abierto(config.IP_XIAOMI, 5555) else "standby"))
                    if estados and not any(st == "on" for _, st in estados):
                        nombre, st = estados[0]
                        msg = f"{nombre} ARRANCANDO..." if st == "booting" else f"{nombre} APAGADA · PULSA ON"
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"ok": False, "mensaje": msg}).encode("utf-8"))
                        return

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "mensaje": mensaje}).encode("utf-8"))

                # Ejecución en segundo plano sin bloquear el navegador
                threading.Thread(target=self.ejecutar_comando, args=(cmd, target, val), daemon=True).start()

            elif url.path == "/api/voice":
                qs = urllib.parse.parse_qs(url.query)
                query = qs.get("q", [""])[0] or qs.get("query", [""])[0]
                platform = qs.get("platform", ["smarttube"])[0] or qs.get("plat", ["smarttube"])[0]
                target = qs.get("target", ["xiaomi"])[0]

                # Despacho en segundo plano
                def _do_stream():
                    reproducir_streaming(query, platform, target)
                threading.Thread(target=_do_stream, daemon=True).start()

                nombres = {"smarttube": "SmartTube", "netflix": "Netflix", "prime": "Prime Video", "disney": "Disney+", "spotify": "Spotify", "youtube": "YouTube"}
                nombre_p = nombres.get(platform, platform.capitalize())
                msg = f"▶ Buscando '{query}' en {nombre_p}" if query else f"Abriendo {nombre_p}"

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

                respuesta_siri = self.procesar_comando_siri(action, target, q, platform, val)

                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(respuesta_siri.encode("utf-8"))

            else:
                self.send_response(404)
                self.end_headers()

        except (BrokenPipeError, ConnectionResetError):
            pass

    def procesar_comando_siri(self, action: str, target: str, q: str, platform: str, val: str) -> str:
        """Genera respuestas en lenguaje natural hablado para Siri y despacha la acción."""
        disp_nombre = "la televisión LG" if target == "lg" else ("la Xiaomi" if target == "xiaomi" else "ambas televisiones")

        if action == "noche":
            def _n():
                if target == "lg": lg.lg_noche(90)
                elif target == "xiaomi": xiaomi.xiaomi_noche(90)
                else: scenes.modo_noche(90)
            threading.Thread(target=_n, daemon=True).start()
            if target == "lg":
                return "Modo Noche activado en la televisión LG. Retroiluminación al 6% y temporizador de 90 minutos."
            elif target == "xiaomi":
                return "Modo Noche activado en la Xiaomi. Retroiluminación tenue y temporizador de 90 minutos."
            else:
                return "Modo Noche activado en ambas televisiones con retroiluminación al 6% y temporizador de 90 minutos."

        elif action == "dia":
            def _d():
                if target == "lg": lg.lg_dia()
                elif target == "xiaomi": xiaomi.xiaomi_dia()
                else: scenes.modo_dia()
            threading.Thread(target=_d, daemon=True).start()
            if target == "lg":
                return "Modo Día activado en la televisión LG con retroiluminación al 100%."
            elif target == "xiaomi":
                return "Modo Día activado en la Xiaomi con retroiluminación al 100%."
            else:
                return "Modo Día activado en ambas televisiones al 100%."

        elif action == "cine":
            def _c():
                if target == "lg": lg.lg_cine()
                elif target == "xiaomi": xiaomi.xiaomi_cine()
                else: scenes.modo_cine()
            threading.Thread(target=_c, daemon=True).start()
            return f"Modo Cine activado en {disp_nombre}."

        elif action == "juego":
            def _j():
                if target == "lg": lg.lg_juego()
                elif target == "xiaomi": xiaomi.xiaomi_juego()
                else: scenes.modo_juego()
            threading.Thread(target=_j, daemon=True).start()
            return f"Modo Juego de ultra baja latencia activado en {disp_nombre}."

        elif action == "descanso":
            def _des():
                if target == "lg": lg.lg_descanso()
                elif target == "xiaomi": xiaomi.xiaomi_descanso()
                else: scenes.modo_descanso()
            threading.Thread(target=_des, daemon=True).start()
            return f"Modo Descanso Visual activado en {disp_nombre}."

        elif action == "encender":
            def _e():
                if target in ["lg", "ambas"]: encender_lg()
                if target in ["xiaomi", "ambas"]: encender_xiaomi()
            threading.Thread(target=_e, daemon=True).start()
            if target == "lg": return "Televisión LG encendida."
            elif target == "xiaomi": return "Televisión Xiaomi encendida."
            else: return "Ambas televisiones encendidas."

        elif action == "apagar":
            def _a():
                if target in ["lg", "ambas"]: lg.apagar_lg()
                if target in ["xiaomi", "ambas"]: xiaomi.apagar_xiaomi()
            threading.Thread(target=_a, daemon=True).start()
            if target == "lg": return "Televisión LG apagada."
            elif target == "xiaomi": return "Televisión Xiaomi apagada y en modo de bajo consumo."
            else: return "Ambas televisiones apagadas."

        elif action == "volumen":
            try: v = int(val)
            except ValueError: v = 20
            def _v():
                if target in ["lg", "ambas"]: lg.lg_volumen(v)
                if target in ["xiaomi", "ambas"]: xiaomi.xiaomi_volumen(v)
            threading.Thread(target=_v, daemon=True).start()
            return f"Volumen de {disp_nombre} ajustado al {v}%."

        elif action in ["silenciar", "mute"]:
            def _m():
                if target in ["lg", "ambas"]: lg.lg_mute()
                if target in ["xiaomi", "ambas"]: xiaomi.xiaomi_mute()
            threading.Thread(target=_m, daemon=True).start()
            return f"Silenciando {disp_nombre}."

        elif action in ["play", "play_pause", "pausa"]:
            def _pp():
                if target in ["lg", "ambas"]: lg.run_lg("tecla", {"tecla": "PLAY"})
                if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("input keyevent 85")
            threading.Thread(target=_pp, daemon=True).start()
            return "Reproducción alternada."

        elif action in ["retroceder", "rewind"]:
            def _rw():
                if target in ["lg", "ambas"]: lg.run_lg("tecla", {"tecla": "REWIND"})
                if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("input keyevent 89")
            threading.Thread(target=_rw, daemon=True).start()
            return f"Retrocediendo 10 segundos en {disp_nombre}."

        elif action in ["adelantar", "fastforward"]:
            def _ff():
                if target in ["lg", "ambas"]: lg.run_lg("tecla", {"tecla": "FASTFORWARD"})
                if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("input keyevent 90")
            threading.Thread(target=_ff, daemon=True).start()
            return f"Avanzando 10 segundos en {disp_nombre}."

        elif action == "vol_up":
            def _vu():
                if target in ["lg", "ambas"]: lg.run_lg("vol_up", {})
                if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("input keyevent 24")
            threading.Thread(target=_vu, daemon=True).start()
            return f"Subiendo volumen de {disp_nombre}."

        elif action == "vol_down":
            def _vd():
                if target in ["lg", "ambas"]: lg.run_lg("vol_down", {})
                if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("input keyevent 25")
            threading.Thread(target=_vd, daemon=True).start()
            return f"Bajando volumen de {disp_nombre}."

        elif action == "audio_tv":
            def _at():
                if target in ["lg", "ambas"]: lg.run_lg("audio_output", {"output": "tv_speaker"})
            threading.Thread(target=_at, daemon=True).start()
            return "Audio cambiado a los altavoces de la televisión LG."

        elif action in ["ver", "buscar", "poner", "reproducir"]:
            nombres = {"smarttube": "SmartTube", "netflix": "Netflix", "prime": "Prime Video", "disney": "Disney+", "spotify": "Spotify", "youtube": "YouTube"}
            nombre_p = nombres.get(platform, platform.capitalize())
            def _v():
                reproducir_streaming(q, platform, target)
            threading.Thread(target=_v, daemon=True).start()
            lugar = f" en {disp_nombre}" if target != "ambas" else ""
            if q:
                return f"Poniendo {q} en {nombre_p}{lugar}."
            else:
                return f"Abriendo {nombre_p}{lugar}."

        elif action == "status":
            s_lg = socket.socket(); s_lg.settimeout(0.12)
            lg_on = (s_lg.connect_ex((config.IP_LG, 3000)) == 0); s_lg.close()
            s_xm = socket.socket(); s_xm.settimeout(0.12)
            xm_on = (s_xm.connect_ex((config.IP_XIAOMI, 5555)) == 0); s_xm.close()
            lg_str = "encendida" if lg_on else "en espera"
            xm_str = "encendida" if xm_on else "en espera"
            return f"Estado actual: La televisión LG está {lg_str} y la televisión Xiaomi está {xm_str}."

        else:
            return "Comando de voz recibido."

    def ejecutar_comando(self, cmd: str, target: str, val: str = "0") -> str:
        # 1. ENCENDIDO (Power ON)
        if cmd == "encender":
            if target in ["lg", "ambas"]: encender_lg()
            if target in ["xiaomi", "ambas"]: encender_xiaomi()
            return "Encendido enviado"

        # 2. APAGADO (Power OFF)
        elif cmd == "apagar":
            if target in ["lg", "ambas"]: lg.apagar_lg()
            if target in ["xiaomi", "ambas"]: xiaomi.apagar_xiaomi()
            return "Apagado enviado"

        # 3. SLIDERS (Brillo & Volumen)
        elif cmd == "set_brillo":
            try: v = max(0, min(100, int(val)))
            except ValueError: v = 50
            if target in ["xiaomi", "ambas"]:
                xiaomi.ejecutar_adb_xiaomi(f"settings put global picture_backlight {v}")
            if target in ["lg", "ambas"]:
                lg.run_lg("ajustes", {
                    "category": "picture", "settings": {"backlight": str(v)},
                    "mensaje": f"Retroiluminación: {v}%"
                })
            return f"☀️ Retroiluminación: {v}%"

        elif cmd == "set_volumen":
            try: v = max(0, min(100, int(val)))
            except ValueError: v = 15
            if target in ["lg", "ambas"]: lg.lg_volumen(v)
            if target in ["xiaomi", "ambas"]: xiaomi.xiaomi_volumen(v)
            return f"🔊 Volumen: {v}%"

        # 4. MODOS DE IMAGEN & SUEÑO
        elif cmd == "noche":
            try: mins = max(10.0, min(360.0, float(val)))
            except (ValueError, TypeError): mins = 90.0
            if target == "lg": lg.lg_noche(mins); return f"🌙 LG: Modo Noche (6% + {int(mins)}m)"
            elif target == "xiaomi": xiaomi.xiaomi_noche(mins); return f"🌙 Xiaomi: Modo Noche (6% + {int(mins)}m)"
            else: scenes.modo_noche(mins); return f"🌙 Ambas: Modo Noche (6% + {int(mins)}m)"

        elif cmd == "cine":
            if target == "lg": lg.lg_cine(); return "🎬 LG: Filmmaker Mode D65"
            elif target == "xiaomi": xiaomi.xiaomi_cine(); return "🎬 Xiaomi: Modo Película"
            else: scenes.modo_cine(); return "🎬 Ambas: Modo Cine"

        elif cmd == "juego":
            if target == "lg": lg.lg_juego(); return "🎮 LG: Modo Juego (~9ms)"
            elif target == "xiaomi": xiaomi.xiaomi_juego(); return "🎮 Xiaomi: Modo Juego"
            else: scenes.modo_juego(); return "🎮 Ambas: Modo Juego"

        elif cmd == "descanso":
            if target == "lg": lg.lg_descanso(); return "👁️ LG: Modo Descanso Visual"
            elif target == "xiaomi": xiaomi.xiaomi_descanso(); return "👁️ Xiaomi: Modo Descanso Visual"
            else: scenes.modo_descanso(); return "👁️ Ambas: Modo Descanso Visual"

        elif cmd == "dia":
            if target == "lg": lg.lg_dia(); return "☀️ LG: Modo Día (100%)"
            elif target == "xiaomi": xiaomi.xiaomi_dia(); return "☀️ Xiaomi: Modo Día (100%)"
            else: scenes.modo_dia(); return "☀️ Ambas: Modo Día"

        elif cmd == "solo_audio":
            if target in ["lg", "ambas"]: lg.lg_solo_audio()
            return "📻 Solo Audio activado"

        elif cmd == "audio_sharp":
            if target in ["lg", "ambas"]: lg.run_lg("audio_output", {"output": "external_arc"})
            return "📢 Audio: Barra Sharp (HDMI ARC)"

        elif cmd == "audio_tv":
            if target in ["lg", "ambas"]: lg.run_lg("audio_output", {"output": "tv_speaker"})
            return "📺 Audio: Altavoces TV"

        elif cmd == "cancelar_timer":
            if target == "lg": lg.cancelar_temporizador_lg()
            elif target == "xiaomi": xiaomi.cancelar_temporizador_xiaomi()
            else: scenes.cancelar_todos_temporizadores()
            return "⏱️ Temporizador cancelado"

        # 5. CRUCETA DIRECCIONAL (D-Pad)
        elif cmd in ["up", "down", "left", "right", "enter"]:
            mapping_lg = {"up": "UP", "down": "DOWN", "left": "LEFT", "right": "RIGHT", "enter": "ENTER"}
            mapping_xm = {"up": "19", "down": "20", "left": "21", "right": "22", "enter": "23"}

            if target in ["lg", "ambas"]:
                lg.run_lg("tecla", {"tecla": mapping_lg[cmd]})
            if target in ["xiaomi", "ambas"]:
                xiaomi.ejecutar_adb_xiaomi(f"input keyevent {mapping_xm[cmd]}")
            return f"Tecla: {cmd.upper()}"

        # 6. ROCKER DE VOLUMEN & CANALES (CH)
        elif cmd == "vol_up":
            if target in ["lg", "ambas"]: lg.run_lg("vol_up", {})
            if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("input keyevent 24")
            return "Volumen +"
        elif cmd == "vol_down":
            if target in ["lg", "ambas"]: lg.run_lg("vol_down", {})
            if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("input keyevent 25")
            return "Volumen -"
        elif cmd == "ch_up":
            if target in ["lg", "ambas"]: lg.run_lg("tecla", {"tecla": "CHANNELUP"})
            if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("input keyevent 166")
            return "Canal +"
        elif cmd == "ch_down":
            if target in ["lg", "ambas"]: lg.run_lg("tecla", {"tecla": "CHANNELDOWN"})
            if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("input keyevent 167")
            return "Canal -"
        elif cmd == "mute":
            if target in ["lg", "ambas"]: lg.lg_mute()
            if target in ["xiaomi", "ambas"]: xiaomi.xiaomi_mute()
            return "Silenciar (Mute)"

        # 7. CONTROLES DE REPRODUCCIÓN (PLAYBACK)
        elif cmd == "play_pause":
            if target in ["lg", "ambas"]: lg.run_lg("tecla", {"tecla": "PLAY"})
            if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("input keyevent 85")
            return "Play / Pausa"
        elif cmd == "rewind":
            if target in ["lg", "ambas"]: lg.run_lg("tecla", {"tecla": "REWIND"})
            if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("input keyevent 89")
            return "Rebobinar -10s"
        elif cmd == "fast_forward":
            if target in ["lg", "ambas"]: lg.run_lg("tecla", {"tecla": "FASTFORWARD"})
            if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("input keyevent 90")
            return "Avanzar +10s"

        # 8. TECLAS DE SISTEMA (HOME, ATRÁS, AJUSTES, SOURCE, INFO)
        elif cmd == "back":
            if target in ["lg", "ambas"]: lg.run_lg("tecla", {"tecla": "BACK"})
            if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("input keyevent 4")
            return "Atrás"
        elif cmd == "home":
            if target in ["lg", "ambas"]: lg.run_lg("tecla", {"tecla": "HOME"})
            if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("input keyevent 3")
            return "Inicio (Home)"
        elif cmd == "settings":
            if target in ["lg", "ambas"]: lg.run_lg("tecla", {"tecla": "MENU"})
            if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("input keyevent 176 || input keyevent 82")
            return "Ajustes"
        elif cmd == "source":
            if target in ["lg", "ambas"]: lg.run_lg("tecla", {"tecla": "INPUT"})
            if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("input keyevent 178")
            return "Entrada HDMI / Source"
        elif cmd == "info":
            if target in ["lg", "ambas"]: lg.run_lg("tecla", {"tecla": "INFO"})
            if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("input keyevent 165")
            return "Info"

        # 9. APPS DIRECTAS
        elif cmd == "smarttube":
            reproducir_streaming("", "smarttube", target)
            return "Lanzando SmartTube"

        return f"Comando '{cmd}' ejecutado"


def _ip_local() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "localhost"


def _adb_keepalive():
    """Mantiene la conexión ADB con la Xiaomi viva en segundo plano."""
    while True:
        time.sleep(60)
        xiaomi.conectar_adb_xiaomi()


def iniciar_servidor():
    lg.precalentar()
    xiaomi.conectar_adb_xiaomi()
    threading.Thread(target=_adb_keepalive, daemon=True, name="adb-keepalive").start()
    server = ThreadingHTTPServer(("0.0.0.0", PUERTO), MandoHandler)
    print(f"\n{'='*70}")
    print(f" 🎛️  MANDO UNIVERSAL & HUB SIRI EN LÍNEA (iPhone 16 Calibrado)")
    print(f"{'='*70}")
    print(f"  • Mando Móvil:       http://{_ip_local()}:{PUERTO}")
    print(f"  • Hub Atajos Siri:   http://{_ip_local()}:{PUERTO}/siri")
    print(f"  • Webhook Siri API:  http://{_ip_local()}:{PUERTO}/api/siri")
    print(f"{'='*70}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Deteniendo servidor...")
        server.server_close()


if __name__ == "__main__":
    iniciar_servidor()
