# Protocolos de Comunicación y Hardware

Este documento describe en detalle las especificaciones técnicas de red y protocolos utilizados por `mando-tv` para comunicarse con cada ecosistema de televisión.

---

## 1. LG webOS: Protocolo SSAP (Smart Service Access Point)

LG webOS utiliza un servidor WebSocket local (típicamente en el puerto `3000` o `3001` para TLS) que implementa el protocolo SSAP sobre JSON-RPC.

### Proceso de Emparejamiento
1. El cliente envía un mensaje JSON de registro:
   ```json
   {
     "type": "register",
     "id": "register_client",
     "payload": {
       "forcePairing": false,
       "pairingType": "PROMPT",
       "client-key": "<CLAVE_GUARDADA_PREVIAMENTE>"
     }
   }
   ```
2. Si es la primera conexión, la televisión muestra un aviso en pantalla solicitando permiso al usuario. Al autorizar, la TV devuelve una clave criptográfica (`client-key`) que el cliente almacena localmente en `~/.config/lg_tv/config.json`.

### Endpoints SSAP Utilizados

| Funcionalidad | URI SSAP | Payload / Parámetros |
| :--- | :--- | :--- |
| **Retroiluminación** | `ssap://com.webos.service.tv.display/setBacklight` | `{"backlight": 0-100}` |
| **Volumen** | `ssap://audio/setVolume` | `{"volume": 0-100}` |
| **Silenciar** | `ssap://audio/setMute` | `{"mute": true/false}` |
| **Apagado** | `ssap://system/turnOff` | Ninguno |
| **Apagar Pantalla** | `ssap://com.webos.service.tvpower/power/turnOffScreen` | Ninguno |
| **Lanzar Apps** | `ssap://system.launcher/open` | `{"id": "app_id", "params": {...}}` |
| **Notificaciones** | `ssap://system.notifications/createToast` | `{"message": "Texto"}` |

---

## 2. Android TV / Xiaomi MiTV: ADB (Android Debug Bridge)

Xiaomi MiTV ejecuta una capa de Android TV que expone el demonio `adbd` sobre TCP/IP en el puerto `5555`.

### 2.1 Códigos Keyevent de Android Utilizados
- `KEYCODE_POWER` (`26`): Conmuta estado de encendido.
- `KEYCODE_WAKEUP` (`224`): Despierta la pantalla.
- `KEYCODE_DPAD_UP` (`19`), `DOWN` (`20`), `LEFT` (`21`), `RIGHT` (`22`), `CENTER` (`23`): Navegación.
- `KEYCODE_ENTER` (`66`): Confirmación.
- `KEYCODE_BACK` (`4`): Volver atrás.
- `KEYCODE_HOME` (`3`): Pantalla principal del Launcher.
- `KEYCODE_MENU` (`82`) / `SETTINGS` (`176`): Menú de ajustes.
- `KEYCODE_TV_INPUT` (`178`): Selector de fuentes HDMI.
- `KEYCODE_VOLUME_UP` (`24`), `DOWN` (`25`), `MUTE` (`164`).
- `KEYCODE_MEDIA_PLAY_PAUSE` (`85`), `STOP` (`86`), `REWIND` (`89`), `FAST_FORWARD` (`90`).

### 2.2 Inyección Directa de Brillo y Volumen de Sistema
Para evitar que se muestren barras OSD intrusivas en pantalla al cambiar ajustes de modo noche o modo día, se manipulan directamente las bases de datos de configuración de Android y el gestor de audio:
```bash
# Brillo directo (0 a 255):
settings put system screen_brightness 15

# Volumen directo (stream 3 = STREAM_MUSIC, de 0 a 15):
cmd audio set-volume 3 5
```

### 2.3 Deep-Linking mediante Android Intents
Para reproducir o buscar contenido directamente en apps de streaming sin pasar por la interfaz del menú:
```bash
# SmartTube búsqueda directa:
am start -a android.intent.action.VIEW \
  -d "https://www.youtube.com/results?search_query=lofi+hip+hop" \
  -n org.smarttube.stable/com.liskovsoft.smartyoutubetv2.tv.ui.main.SplashActivity

# Netflix búsqueda:
am start -a android.intent.action.VIEW \
  -d "https://www.netflix.com/search?q=Stranger+Things" \
  -n com.netflix.ninja/.MainActivity

# Spotify búsqueda:
am start -a android.intent.action.VIEW \
  -d "spotify:search:Daft+Punk" \
  -n com.spotify.tv.android/.MainActivity
```

---

## 3. Wake-on-LAN (WoL)

Para encender la televisión LG desde estado de apagado físico completo (cuando la interfaz de red Ethernet o Wi-Fi está en modo espera de baja energía):
- Se construye un paquete mágico UDP compuesto por 6 bytes de `0xFF` seguidos de 16 repeticiones de la dirección MAC física del dispositivo (ej. `20:fc:da:90:54:1d`).
- Se emite en broadcast local hacia `255.255.255.255:9` y `192.168.1.255:9`.
