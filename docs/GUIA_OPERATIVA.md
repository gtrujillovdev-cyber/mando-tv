# Guía Operativa — Uso y Mantenimiento

Referencia práctica para el día a día: qué hacer cuando algo falla, cómo actualizar y cómo añadir funcionalidades.

---

## Infraestructura de red

| Dispositivo | IP LAN | IP Tailscale | Puerto |
|---|---|---|---|
| Raspberry Pi (servidor) | 192.168.1.141 | 100.95.199.1 | 8899 |
| LG 65" webOS | 192.168.1.250 | — | 3000 (SSAP) |
| Xiaomi MiTV Android TV | 192.168.1.238 | — | 5555 (ADB) |

**Acceso SSH a la Pi:** `ssh rpi` (alias en `~/.ssh/config` del M4)

---

## Uso diario

### Mando táctil (iPhone, navegador)
Abre desde Safari y añade a la pantalla de inicio:
```
http://192.168.1.141:8899
```

### Siri (voz)
Los atajos están importados en el iPhone. Con Apple Intelligence activo (iOS 26+) di directamente el nombre del atajo:

> "Oye Siri, enciende la tele LG"
> "Oye Siri, baja el volumen Xiaomi"
> "Oye Siri, abre SmartTube"
> "Oye Siri, busca en Netflix" → pide el título por teclado/voz

Catálogo completo en `docs/SIRI_GUIDE.md`.

### CLI desde el M4
```bash
cd projects/mando-tv

python3 -m mando_tv.cli --status           # Estado de ambas TVs y timers
python3 -m mando_tv.cli --modo-noche       # Noche en ambas (brillo 6% + timer 90m)
python3 -m mando_tv.cli --apagar-tvs       # Apagar ambas
python3 -m mando_tv.cli --lg-cine          # Filmmaker Mode en LG
python3 -m mando_tv.cli --xiaomi-volumen 8 # Volumen Xiaomi (0-15)
python3 -m mando_tv.cli --help             # Ver todos los comandos
```

---

## Estado del servidor

```bash
# Ver si está corriendo
ssh rpi "systemctl status mando-tv --no-pager"

# Ver últimas líneas del log
ssh rpi "journalctl -u mando-tv -n 40 --no-pager"

# Reiniciar manualmente
ssh rpi "sudo systemctl restart mando-tv"
```

---

## Despliegue de actualizaciones

Tras cualquier cambio en `mando_tv/`:

```bash
cd projects/mando-tv
./deploy/deploy.sh raspberry@100.95.199.1
```

El script hace:
1. `rsync` del paquete `mando_tv/` a `~/mando-tv/` en la Pi
2. Copia `~/.config/lg_tv/config.json` (clave de emparejamiento LG)
3. `systemctl restart mando-tv`

---

## Problemas frecuentes y soluciones

### La LG no responde (volumen, modos, apps...)

**Causa:** El puerto SSAP 3000 solo está disponible cuando la LG está encendida.

```bash
# Verificar si la LG está encendida
ssh rpi "python3 -c \"import socket; s=socket.socket(); s.settimeout(2); print('LG:', 'ON' if s.connect_ex(('192.168.1.250',3000))==0 else 'OFF'); s.close()\""
```

**Solución:** Encender primero con WoL y esperar ~10 segundos:
```bash
# Desde Siri:
"Oye Siri, enciende la tele LG"

# Desde CLI:
python3 -m mando_tv.cli --encender-lg
```

---

### La Xiaomi no responde (ADB unauthorized o disconnected)

**Causa A — No conectada:** ADB se desconecta tras reinicio del servicio o de la TV.
```bash
ssh rpi "adb devices"
# Si muestra vacío o 'offline': reconectar
ssh rpi "adb connect 192.168.1.238:5555"
```

**Causa B — Unauthorized:** La Pi no está autorizada en la Xiaomi.
```bash
ssh rpi "adb connect 192.168.1.238:5555"
# La Xiaomi muestra diálogo en pantalla → aceptar con el mando
# Marcar "Permitir siempre desde este equipo"
ssh rpi "adb devices"   # debe mostrar 'device', no 'unauthorized'
```

> El servidor ya auto-conecta ADB en cada comando y al arrancar, pero si la Xiaomi se reinicia y el diálogo de autorización vuelve a aparecer, hay que aceptarlo físicamente una vez más.

---

### El servidor no arranca en la Pi

```bash
ssh rpi "journalctl -u mando-tv -n 50 --no-pager"
```

Causas comunes:
- **`websockets` no instalado:** `ssh rpi "pip3 install --break-system-packages websockets"`
- **Puerto 8899 ocupado:** `ssh rpi "sudo lsof -i :8899"` → matar proceso y reiniciar
- **Error de sintaxis en código:** ejecutar `python3 -m mando_tv` localmente en el M4 para ver el error

---

### La LG pierde el emparejamiento SSAP

La clave `client_key` en `~/.config/lg_tv/config.json` puede caducar o invalidarse si se restablece la TV.

**Re-emparejar:**
```bash
# Borrar la clave vieja
echo '{"ip":"192.168.1.250","client_key":""}' > ~/.config/lg_tv/config.json

# Arrancar el servidor localmente (la LG pedirá autorización en pantalla)
cd projects/mando-tv
python3 -m mando_tv

# La LG mostrará "¿Permitir control remoto?" → aceptar
# La nueva client_key se guarda automáticamente en config.json

# Redesplegar con la nueva clave
./deploy/deploy.sh raspberry@100.95.199.1
```

---

### Los atajos de Siri no funcionan fuera de casa

Los atajos usan la IP de LAN `192.168.1.141`. Fuera del WiFi de casa la Pi no es alcanzable por esa IP.

**Solución — Tailscale:**
La Pi tiene Tailscale en `100.95.199.1`. Genera atajos con esa IP para que funcionen desde cualquier red:

```
http://100.95.199.1:8899/api/siri?action=encender&target=lg
```

Para regenerar los atajos del iPhone con IP de Tailscale:
```bash
cd projects/mando-tv
# Cambiar BASE en el script de generación a http://100.95.199.1:8899
# y volver a ejecutar el script de importación
```

---

### Añadir un nuevo atajo de Siri

1. Identificar la URL de la API (ver `docs/SIRI_GUIDE.md`)
2. Generar el archivo `.shortcut`, firmarlo e importarlo:

```python
# Ejecutar en el M4 desde projects/mando-tv
python3 - <<'EOF'
import plistlib, uuid, subprocess, time

nombre = "Mi nuevo atajo"
url    = "http://192.168.1.141:8899/api/siri?action=ACCION&target=TARGET"
uid    = str(uuid.uuid4()).upper()

plist = {
    "WFWorkflowActions": [
        {"WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
         "WFWorkflowActionParameters": {"UUID": uid, "WFURL": url, "WFHTTPMethod": "GET"}},
        {"WFWorkflowActionIdentifier": "is.workflow.actions.speaktext",
         "WFWorkflowActionParameters": {"WFText": {
             "Value": {"attachmentsByRange": {"{0, 1}": {"OutputName": "Contents of URL", "OutputUUID": uid, "Type": "ActionOutput"}}, "string": "\ufffc"},
             "WFSerializationType": "WFTextTokenString"}}},
    ],
    "WFWorkflowClientVersion": "1300.0.0.0", "WFWorkflowHasShortcutInputVariables": False,
    "WFWorkflowIcon": {"WFWorkflowIconGlyphNumber": 59511, "WFWorkflowIconStartColor": 4274264319},
    "WFWorkflowImportQuestions": [], "WFWorkflowInputContentItemClasses": [],
    "WFWorkflowMinimumClientVersion": 900, "WFWorkflowMinimumClientVersionString": "900",
    "WFWorkflowName": nombre, "WFWorkflowOutputContentItemClasses": [],
    "WFWorkflowTypes": ["NCWidget", "WatchKit"],
}
with open(f"/tmp/{nombre}.shortcut", "wb") as f:
    plistlib.dump(plist, f, fmt=plistlib.FMT_BINARY)

subprocess.run(["shortcuts", "sign", "--mode", "people-who-know-me",
                "--input", f"/tmp/{nombre}.shortcut",
                "--output", f"/tmp/{nombre}_signed.shortcut"])
subprocess.run(["open", f"/tmp/{nombre}_signed.shortcut"])
time.sleep(2)
subprocess.run(["osascript", "-e",
    'tell application "System Events" to tell process "Shortcuts" to click button 2 of scroll area 1 of group 1 of window 1'])
print(f"Atajo '{nombre}' importado. Sincronizará al iPhone via iCloud.")
EOF
```

> El nombre del archivo `.shortcut` es el nombre que verá Siri. Usar `people-who-know-me` para que sincronice vía iCloud.

---

### Añadir una nueva acción a la API Siri

Editar `mando_tv/server.py` → método `procesar_comando_siri()`:

```python
elif action == "mi_accion":
    def _fn():
        if target in ["lg", "ambas"]:   asyncio.run(lg.enviar_comando_lg("...", {}))
        if target in ["xiaomi", "ambas"]: xiaomi.ejecutar_adb_xiaomi("...")
    threading.Thread(target=_fn, daemon=True).start()
    return "Respuesta hablada en español para Siri."
```

Luego redesplegar:
```bash
./deploy/deploy.sh raspberry@100.95.199.1
```

---

## Checklist de mantenimiento mensual

- [ ] `ssh rpi "df -h"` — verificar espacio en disco de la Pi
- [ ] `ssh rpi "journalctl -u mando-tv --since '30 days ago' | grep -i error"` — revisar errores
- [ ] `ssh rpi "adb devices"` — confirmar que ADB sigue autorizado en la Xiaomi
- [ ] Verificar que la LG no ha cambiado de IP (reservar en el router si no está fijo)
- [ ] `shortcuts list | wc -l` — confirmar que los 34 atajos siguen en el Mac
