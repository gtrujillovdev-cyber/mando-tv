"""Lanzador de contenido (SmartTube, Netflix, Prime, Disney+, Movistar+, DAZN...)."""
from . import discovery
from . import lg
from . import xiaomi
import socket
import urllib.parse
from .lg import encender_lg
from .xiaomi import encender_xiaomi


def reproducir_streaming(query: str, plataforma: str = "smarttube", target: str = "xiaomi") -> str:
    """
    Lanza contenido en la plataforma indicada (SmartTube, YouTube, Netflix, Prime, Disney+, Movistar+, DAZN)
    tanto en Xiaomi TV (Android TV intents verificados) como en LG 65" (webOS luna app IDs verificados).
    """
    q_clean = query.strip()
    q_enc = urllib.parse.quote_plus(q_clean) if q_clean else ""
    nombres = {
        "smarttube": "SmartTube", "youtube": "YouTube", "netflix": "Netflix",
        "prime": "Prime Video", "amazon": "Prime Video", "disney": "Disney+",
        "movistar": "Movistar Plus+", "dazn": "DAZN"
    }
    nombre_plat = nombres.get(plataforma, plataforma.capitalize())

    # 1. XIAOMI TV (Android TV Intents)
    if target in ["xiaomi", "ambas"]:
        ip_xm = discovery.resolver_ip_xiaomi()
        if not discovery.puerto_abierto(ip_xm, 5555, timeout=0.25):
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
                cmd = "am start -n org.smarttube.stable/com.liskovsoft.smartyoutubetv2.tv.ui.main.SplashActivity"
            xiaomi.ejecutar_adb_xiaomi(cmd)

        elif plataforma == "youtube":
            if q_clean:
                cmd = f"am start -a android.intent.action.VIEW -d 'https://www.youtube.com/results?search_query={q_enc}' -n com.google.android.youtube.tv/com.google.android.apps.youtube.tv.activity.ShellActivity || am start -a android.intent.action.VIEW -d 'https://www.youtube.com/results?search_query={q_enc}'"
            else:
                cmd = "am start -n com.google.android.youtube.tv/com.google.android.apps.youtube.tv.activity.ShellActivity || monkey -p com.google.android.youtube.tv 1"
            xiaomi.ejecutar_adb_xiaomi(cmd)

        elif plataforma == "netflix":
            if q_clean:
                cmd = f"am start -a android.intent.action.VIEW -d 'https://www.netflix.com/search?q={q_enc}' -n com.netflix.ninja/.MainActivity || am start -a android.intent.action.VIEW -d 'netflix://search/{q_enc}'"
            else:
                cmd = "am start -n com.netflix.ninja/.MainActivity"
            xiaomi.ejecutar_adb_xiaomi(cmd)

        elif plataforma in ["prime", "amazon"]:
            if q_clean:
                cmd = f"am start -a android.intent.action.VIEW -d 'https://app.primevideo.com/search?phrase={q_enc}' -n com.amazon.amazonvideo.livingroom/com.amazon.ignition.IgnitionActivity"
            else:
                cmd = "am start -n com.amazon.amazonvideo.livingroom/com.amazon.ignition.IgnitionActivity"
            xiaomi.ejecutar_adb_xiaomi(cmd)

        elif plataforma == "disney":
            if q_clean:
                cmd = f"am start -a android.intent.action.VIEW -d 'https://www.disneyplus.com/search?q={q_enc}' -n com.disney.disneyplus/com.bamtechmedia.dominguez.main.MainActivity"
            else:
                cmd = "am start -n com.disney.disneyplus/com.bamtechmedia.dominguez.main.MainActivity"
            xiaomi.ejecutar_adb_xiaomi(cmd)

        elif plataforma == "movistar":
            if q_clean:
                cmd = f"am start -a android.intent.action.VIEW -d 'https://ver.movistarplus.es/busqueda?q={q_enc}' -n com.movistarplus.androidtv/.MainActivity || am start -n com.movistarplus.androidtv/.MainActivity"
            else:
                cmd = "am start -n com.movistarplus.androidtv/.MainActivity"
            xiaomi.ejecutar_adb_xiaomi(cmd)

        elif plataforma == "dazn":
            if q_clean:
                cmd = f"am start -a android.intent.action.VIEW -d 'dazn://search?query={q_enc}' -n com.dazn/.MainActivity || am start -n com.dazn/.MainActivity"
            else:
                cmd = "am start -n com.dazn/.MainActivity"
            xiaomi.ejecutar_adb_xiaomi(cmd)

    # 2. LG 65" (webOS App IDs verificados)
    if target in ["lg", "ambas"]:
        ip_lg = discovery.resolver_ip_lg()
        if not discovery.puerto_abierto(ip_lg, 3000, timeout=0.25):
            encender_lg()

        mapping_lg = {
            "smarttube": "youtube.leanback.v4",
            "youtube": "youtube.leanback.v4",
            "netflix": "netflix",
            "prime": "amazon",
            "amazon": "amazon",
            "disney": "com.disney.disneyplus-prod",
            "movistar": "com.telefonica.app.nux",
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
