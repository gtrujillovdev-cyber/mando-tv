"""Lanzador de contenido (SmartTube, Netflix, Prime, Disney+, Movistar+, DAZN...)."""
from . import lg
from . import xiaomi
import socket
import urllib.parse
from .config import IP_LG, IP_XIAOMI
from .lg import encender_lg, esperar_lg
from .xiaomi import encender_xiaomi


def _is_online(ip: str, port: int, timeout: float = 0.5) -> bool:
    with socket.socket() as s:
        s.settimeout(timeout)
        return s.connect_ex((ip, port)) == 0


def reproducir_streaming(query: str, plataforma: str = "smarttube", target: str = "xiaomi") -> str:
    """
    Lanza contenido en la plataforma indicada (SmartTube, YouTube, Netflix, Prime, Disney+, Movistar+, DAZN)
    tanto en Xiaomi TV (Android TV intents) como en LG 65" (webOS luna).
    """
    q_clean = query.strip()
    q_enc = urllib.parse.quote_plus(q_clean) if q_clean else ""
    nombres = {
        "smarttube": "SmartTube", "youtube": "YouTube", "netflix": "Netflix",
        "prime": "Prime Video", "disney": "Disney+", "movistar": "Movistar Plus+", "dazn": "DAZN"
    }
    nombre_plat = nombres.get(plataforma, plataforma.capitalize())

    # 1. XIAOMI TV (Android TV Intents)
    if target in ["xiaomi", "ambas"]:
        if not _is_online(IP_XIAOMI, 5555):
            encender_xiaomi()
        else:
            xiaomi.conectar_adb_xiaomi()

        if plataforma == "smarttube":
            if q_clean:
                if "youtube.com" in q_clean or "youtu.be" in q_clean:
                    url_target = q_clean
                else:
                    url_target = f"https://www.youtube.com/results?search_query={q_enc}"
                cmd = f"am start -a android.intent.action.VIEW -d '{url_target}' -n org.smarttube.stable/com.liskovsoft.smartyoutubetv2.tv.ui.main.SplashActivity"
            else:
                cmd = "monkey -p org.smarttube.stable -c android.intent.category.LAUNCHER 1"
            xiaomi.ejecutar_adb_xiaomi(cmd)

        elif plataforma == "youtube":
            if q_clean:
                cmd = f"am start -a android.intent.action.VIEW -d 'https://www.youtube.com/results?search_query={q_enc}' -n com.google.android.youtube.tv/com.google.android.apps.youtube.tv.activity.ShellActivity || am start -a android.intent.action.VIEW -d 'https://www.youtube.com/results?search_query={q_enc}'"
            else:
                cmd = "monkey -p com.google.android.youtube.tv -c android.intent.category.LAUNCHER 1"
            xiaomi.ejecutar_adb_xiaomi(cmd)

        elif plataforma == "netflix":
            if q_clean:
                cmd = f"am start -a android.intent.action.VIEW -d 'https://www.netflix.com/search?q={q_enc}' -n com.netflix.ninja/.MainActivity || am start -a android.intent.action.VIEW -d 'netflix://search/{q_enc}'"
            else:
                cmd = "monkey -p com.netflix.ninja -c android.intent.category.LAUNCHER 1"
            xiaomi.ejecutar_adb_xiaomi(cmd)

        elif plataforma in ["prime", "amazon"]:
            if q_clean:
                cmd = f"am start -a android.intent.action.VIEW -d 'https://app.primevideo.com/search?phrase={q_enc}' -n com.amazon.amazonvideo.livingroom/com.amazon.ignition.IgnitionActivity"
            else:
                cmd = "monkey -p com.amazon.amazonvideo.livingroom -c android.intent.category.LAUNCHER 1"
            xiaomi.ejecutar_adb_xiaomi(cmd)

        elif plataforma == "disney":
            if q_clean:
                cmd = f"am start -a android.intent.action.VIEW -d 'https://www.disneyplus.com/search?q={q_enc}' -n com.disney.disneyplus/com.bamtechmedia.dominguez.main.MainActivity"
            else:
                cmd = "monkey -p com.disney.disneyplus -c android.intent.category.LAUNCHER 1"
            xiaomi.ejecutar_adb_xiaomi(cmd)

        elif plataforma == "movistar":
            if q_clean:
                cmd = f"am start -a android.intent.action.VIEW -d 'https://ver.movistarplus.es/busqueda?q={q_enc}' -n es.plus.o2o/.ui.splash.SplashActivity || monkey -p es.plus.o2o -c android.intent.category.LAUNCHER 1"
            else:
                cmd = "monkey -p es.plus.o2o -c android.intent.category.LAUNCHER 1 || monkey -p com.movistar.plus -c android.intent.category.LAUNCHER 1"
            xiaomi.ejecutar_adb_xiaomi(cmd)

        elif plataforma == "dazn":
            if q_clean:
                cmd = f"am start -a android.intent.action.VIEW -d 'dazn://search?query={q_enc}' -n com.dazn/.MainActivity || monkey -p com.dazn -c android.intent.category.LAUNCHER 1"
            else:
                cmd = "monkey -p com.dazn -c android.intent.category.LAUNCHER 1"
            xiaomi.ejecutar_adb_xiaomi(cmd)

    # 2. LG 65" (webOS luna commands)
    if target in ["lg", "ambas"]:
        if not _is_online(IP_LG, 3000):
            encender_lg()
            if not esperar_lg(45):
                return "La LG no ha arrancado (revisa 'Encender con Wi-Fi' en la tele)"
        mapping_lg = {
            "smarttube": "youtube.leanback.v4",
            "youtube": "youtube.leanback.v4",
            "netflix": "netflix",
            "prime": "amazon",
            "amazon": "amazon",
            "disney": "disneyplus",
            "movistar": "com.movistar.es",
            "dazn": "dazn"
        }
        app_id = mapping_lg.get(plataforma, "youtube.leanback.v4")
        params = {}
        if q_clean:
            if "youtube" in app_id:
                params["contentTarget"] = f"https://www.youtube.com/results?search_query={q_enc}"
            elif "netflix" in app_id:
                params["query"] = q_clean
        
        lg.run_lg("app", {"id": app_id, "params": params, "mensaje": f"Abriendo {nombre_plat}"})

    if q_clean:
        return f"▶ Buscando '{q_clean}' en {nombre_plat}"
    else:
        return f"Abriendo {nombre_plat}"
