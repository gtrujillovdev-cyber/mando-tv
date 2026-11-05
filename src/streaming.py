#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
streaming.py - Universal Deep-Link Streaming Launcher
Dispatches direct playback or searches to:
  - SmartTube (Android TV ad-free YouTube client)
  - YouTube
  - Netflix
  - Amazon Prime Video
  - Disney+
  - Spotify
"""

import urllib.parse
import asyncio
from typing import Dict
from .controller import tv_hub


STREAMING_PLATFORMS: Dict[str, Dict[str, str]] = {
    "smarttube": {
        "name": "SmartTube",
        "android_pkg": "org.smarttube.stable",
        "android_activity": "com.liskovsoft.smartyoutubetv2.tv.ui.main.SplashActivity",
        "lg_app_id": "youtube.leanback.v4"
    },
    "youtube": {
        "name": "YouTube",
        "android_pkg": "com.google.android.youtube.tv",
        "android_activity": "com.google.android.apps.youtube.tv.activity.ShellActivity",
        "lg_app_id": "youtube.leanback.v4"
    },
    "netflix": {
        "name": "Netflix",
        "android_pkg": "com.netflix.ninja",
        "android_activity": ".MainActivity",
        "lg_app_id": "netflix"
    },
    "prime": {
        "name": "Prime Video",
        "android_pkg": "com.amazon.amazonvideo.livingroom",
        "android_activity": "com.amazon.ignition.IgnitionActivity",
        "lg_app_id": "amazon"
    },
    "disney": {
        "name": "Disney+",
        "android_pkg": "com.disney.disneyplus",
        "android_activity": "com.bamtechmedia.dominguez.main.MainActivity",
        "lg_app_id": "disneyplus"
    },
    "spotify": {
        "name": "Spotify",
        "android_pkg": "com.spotify.tv.android",
        "android_activity": ".MainActivity",
        "lg_app_id": "spotify-medialink-20"
    }
}


def reproducir_streaming(query: str, plataforma: str = "smarttube", target: str = "xiaomi") -> str:
    """
    Construye y despacha los intents o URIs de streaming hacia las pantallas seleccionadas.
    """
    plat_key = plataforma.lower().strip()
    plat_info = STREAMING_PLATFORMS.get(plat_key, STREAMING_PLATFORMS["smarttube"])
    nombre_plat = plat_info["name"]

    q_clean = query.strip()
    q_enc = urllib.parse.quote_plus(q_clean) if q_clean else ""

    # 1. XIAOMI / ANDROID TV
    if target in ["xiaomi", "ambas"]:
        tv_hub.xiaomi.encender()

        if plat_key == "smarttube":
            if q_clean:
                if "youtube.com" in q_clean or "youtu.be" in q_clean:
                    url_target = q_clean
                else:
                    url_target = f"https://www.youtube.com/results?search_query={q_enc}"
                cmd = f"am start -a android.intent.action.VIEW -d '{url_target}' -n {plat_info['android_pkg']}/{plat_info['android_activity']}"
            else:
                cmd = f"monkey -p {plat_info['android_pkg']} -c android.intent.category.LAUNCHER 1"
            tv_hub.xiaomi.ejecutar_adb(cmd)

        elif plat_key == "youtube":
            if q_clean:
                cmd = f"am start -a android.intent.action.VIEW -d 'https://www.youtube.com/results?search_query={q_enc}' -n {plat_info['android_pkg']}/{plat_info['android_activity']} || am start -a android.intent.action.VIEW -d 'https://www.youtube.com/results?search_query={q_enc}'"
            else:
                cmd = f"monkey -p {plat_info['android_pkg']} -c android.intent.category.LAUNCHER 1"
            tv_hub.xiaomi.ejecutar_adb(cmd)

        elif plat_key == "netflix":
            if q_clean:
                cmd = f"am start -a android.intent.action.VIEW -d 'https://www.netflix.com/search?q={q_enc}' -n {plat_info['android_pkg']}/{plat_info['android_activity']} || am start -a android.intent.action.VIEW -d 'netflix://search/{q_enc}'"
            else:
                cmd = f"monkey -p {plat_info['android_pkg']} -c android.intent.category.LAUNCHER 1"
            tv_hub.xiaomi.ejecutar_adb(cmd)

        elif plat_key in ["prime", "amazon"]:
            if q_clean:
                cmd = f"am start -a android.intent.action.VIEW -d 'https://app.primevideo.com/search?phrase={q_enc}' -n {plat_info['android_pkg']}/{plat_info['android_activity']}"
            else:
                cmd = f"monkey -p {plat_info['android_pkg']} -c android.intent.category.LAUNCHER 1"
            tv_hub.xiaomi.ejecutar_adb(cmd)

        elif plat_key == "disney":
            if q_clean:
                cmd = f"am start -a android.intent.action.VIEW -d 'https://www.disneyplus.com/search?q={q_enc}' -n {plat_info['android_pkg']}/{plat_info['android_activity']}"
            else:
                cmd = f"monkey -p {plat_info['android_pkg']} -c android.intent.category.LAUNCHER 1"
            tv_hub.xiaomi.ejecutar_adb(cmd)

        elif plat_key == "spotify":
            if q_clean:
                cmd = f"am start -a android.intent.action.VIEW -d 'spotify:search:{q_enc}' -n {plat_info['android_pkg']}/{plat_info['android_activity']}"
            else:
                cmd = f"monkey -p {plat_info['android_pkg']} -c android.intent.category.LAUNCHER 1"
            tv_hub.xiaomi.ejecutar_adb(cmd)

    # 2. LG webOS (Luna Bus)
    if target in ["lg", "ambas"]:
        tv_hub.lg.encender()
        app_id = plat_info["lg_app_id"]
        params = {}
        if q_clean:
            if "youtube" in app_id:
                params["contentTarget"] = f"https://www.youtube.com/results?search_query={q_enc}"
            elif "netflix" in app_id:
                params["query"] = q_clean

        asyncio.run(tv_hub.lg.enviar_comando_ssap("app", {"id": app_id, "params": params}))

    if q_clean:
        return f"▶ Buscando '{q_clean}' en {nombre_plat}"
    return f"Abriendo {nombre_plat}"
