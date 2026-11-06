# Mando TV

Control unificado del salón desde el iPhone — sin mandos físicos.

Servidor Python ligero alojado en una **Raspberry Pi** que conecta simultáneamente una **LG 65" webOS** (via WebSocket SSAP) y una **Xiaomi MiTV Android TV** (via ADB) y los expone como una API REST simple. El iPhone lo controla todo: por voz con Siri, con un mando táctil web o con la app Atajos.

---

## Qué puede hacer

| Función | LG 65" | Xiaomi MiTV |
|---|:---:|:---:|
| Encender / Apagar | WoL + SSAP | WoL + ADB |
| Volumen, mute | SSAP | ADB keyevent |
| Navegación D-Pad | SSAP puntero | ADB keyevent |
| Modos imagen (Noche, Día, Cine, Juego) | SSAP settings | ADB settings |
| Timer apagado automático | Proceso Pi | Proceso Android |
| Abrir Netflix, Prime, Disney+, Spotify | webOS luna | Android intent |
| Buscar en SmartTube / Netflix / YouTube | webOS luna | Android intent |
| Cambiar audio a barra Sharp (HDMI ARC) | SSAP audio | — |
| Solo audio (pantalla apagada) | SSAP energySaving | — |

---

## Cómo controlarlo

### 1 — Voz (Siri)
34 atajos instalados en el iPhone. Con Apple Intelligence activo (iOS 26+) di directamente el nombre:

```
"Oye Siri, enciende la tele LG"
"Oye Siri, baja el volumen Xiaomi"
"Oye Siri, abre Netflix en la LG"
"Oye Siri, busca en SmartTube"      ← te pide el título
"Oye Siri, modo noche LG"
"Oye Siri, apaga las teles"
```

Catálogo completo → [`docs/SIRI_GUIDE.md`](docs/SIRI_GUIDE.md)

### 2 — Mando táctil web (iPhone, cualquier navegador)
```
http://192.168.1.141:8899
```
PWA instalable desde Safari → pantalla de inicio del iPhone. D-pad táctil, rocker de volumen/canales, modos y lanzadores de streaming. Latencia < 15ms.

### 3 — CLI desde el Mac
```bash
python3 -m mando_tv.cli --status          # Estado completo
python3 -m mando_tv.cli --modo-noche      # Noche en ambas TVs
python3 -m mando_tv.cli --apagar-tvs      # Apagar todo
python3 -m mando_tv.cli --help
```

---

## Arquitectura

```
iPhone
  ├── Siri ("Oye Siri, enciende la LG")
  ├── Safari PWA  (mando táctil)
  └── App Atajos  (automatizaciones)
           │
           │  HTTP GET  (LAN 192.168.1.141:8899)
           ▼
    Raspberry Pi 3B
    ├── Python HTTP server (puerto 8899, ThreadingHTTPServer)
    ├── Hilo keepalive ADB (reconecta Xiaomi cada 60s)
    ├── Bucle asyncio LG (conexión SSAP persistente + socket puntero)
    │
    ├── LG 65"  192.168.1.250 ──── WebSocket SSAP (puerto 3000)
    └── Xiaomi  192.168.1.238 ──── ADB TCP/IP    (puerto 5555)
                                        └── HDMI ARC ── Barra Sharp
```

**Por qué la latencia es < 15ms:** el servidor devuelve `200 OK` al iPhone de inmediato y delega el comando de red a un hilo en segundo plano. El móvil nunca espera la respuesta de la TV.

---

## Puesta en marcha

### Prerequisitos
- Raspberry Pi en la misma LAN que las TVs
- LG: `Ajustes → Conexión → Red → Wake-on-LAN: ON`
- Xiaomi: `Opciones desarrollador → Depuración ADB por red: ON (puerto 5555)`
- Mac con `~/.config/lg_tv/config.json` (clave de emparejamiento LG)

### Despliegue
```bash
git clone <repo>
cd mando-tv

# Desplegar en Raspberry Pi (crea servicio systemd que arranca en boot)
./deploy/deploy.sh raspberry@<IP_PI>

# Acceder
# Mando:  http://<IP_PI>:8899
# Siri:   http://<IP_PI>:8899/siri
```

### Variables de entorno (opcionales)
| Variable | Por defecto |
|---|---|
| `LG_TV_IP` | `192.168.1.250` |
| `LG_TV_MAC` | `74:e6:b8:26:02:0e` |
| `XIAOMI_TV_IP` | `192.168.1.238` |
| `XIAOMI_TV_MAC` | `50:e4:78:af:b2:e7` |
| `MANDO_PORT` | `8899` |
| `LG_CONFIG` | `~/.config/lg_tv/config.json` |

---

## API

### `GET /api/action` — Mando táctil
| Parámetro | Valores |
|---|---|
| `cmd` | `encender`, `apagar`, `vol_up`, `vol_down`, `mute`, `up`, `down`, `left`, `right`, `enter`, `back`, `home`, `play_pause`, `rewind`, `fast_forward`, `noche`, `dia`, `cine`, `juego`, `audio_sharp`, `audio_tv`, `smarttube`, `set_brillo`, `set_volumen` |
| `target` | `lg` / `xiaomi` / `ambas` |
| `val` | Valor numérico (para `set_brillo`, `set_volumen`) |

Responde `{"ok": true, "mensaje": "Volumen +"}` en < 15ms.

### `GET /api/siri` — Voz
| Parámetro | Valores |
|---|---|
| `action` | `encender`, `apagar`, `noche`, `dia`, `cine`, `juego`, `vol_up`, `vol_down`, `volumen`, `silenciar`, `pausa`, `retroceder`, `adelantar`, `reproducir`, `audio_sharp`, `audio_tv`, `status` |
| `target` | `lg` / `xiaomi` / `ambas` |
| `platform` | `smarttube`, `netflix`, `prime`, `disney`, `spotify`, `youtube` |
| `q` | Búsqueda (texto) |
| `val` | Nivel de volumen (0-100) |

Responde `text/plain` en español para que Siri lo hable directamente.

### `GET /api/status` — Estado
```json
{
  "lg_online": true,
  "xiaomi_online": true,
  "timer_lg": 3240,
  "timer_xiaomi": 0
}
```

---

## Troubleshooting rápido

| Síntoma | Causa | Solución |
|---|---|---|
| LG no responde | TV apagada (SSAP solo funciona con TV on) | Di "enciende la tele LG" primero |
| Xiaomi no responde | ADB desconectado | El servidor reconecta solo cada 60s; el cron de la Pi cada 3min |
| Xiaomi muestra diálogo ADB | Claves no persistidas tras reinicio TV | Aceptar una vez con el mando; ya no volverá mientras la TV no se reinicie |
| LG pierde emparejamiento | `client_key` caducada | Ver `docs/GUIA_OPERATIVA.md` → "LG pierde el emparejamiento SSAP" |
| Siri no llega al servidor fuera de casa | IP LAN no alcanzable | Usar IP Tailscale `100.95.199.1:8899` en los atajos |

Guía completa → [`docs/GUIA_OPERATIVA.md`](docs/GUIA_OPERATIVA.md)

---

## Estructura del proyecto

```
mando_tv/
├── server.py     # HTTP server, router /api/action /api/siri /api/status
├── lg.py         # LG webOS: SSAP WebSocket, modos, timers
├── xiaomi.py     # Xiaomi Android TV: ADB, modos, timers
├── streaming.py  # Lanzador SmartTube / Netflix / Prime / Disney+ / Spotify
├── scenes.py     # Acciones conjuntas (ambas TVs)
├── timers.py     # Temporizadores de apagado
├── wol.py        # Wake-on-LAN
├── cli.py        # CLI de línea de comandos
├── config.py     # IPs, puertos, rutas (env vars)
└── web/
    ├── index.html   # Mando táctil PWA (vintage Hi-Fi, 100dvh, haptic)
    └── siri.html    # Hub visual de atajos Siri
deploy/
└── deploy.sh     # Despliegue remoto → systemd (Linux) / LaunchAgent (macOS)
docs/
├── GUIA_OPERATIVA.md   # Uso diario, mantenimiento y troubleshooting
├── SIRI_GUIDE.md       # Catálogo completo de comandos de voz
├── PROTOCOLS.md        # Especificaciones técnicas SSAP, ADB, WoL
└── ARCHITECTURE.md     # Diagrama de topología
```

---

## Licencia

MIT
