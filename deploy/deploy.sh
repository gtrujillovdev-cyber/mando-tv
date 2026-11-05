#!/usr/bin/env bash
# ==============================================================================
# Despliega el servidor del mando TV en un host 24/7 (Raspberry Pi o MBP1).
# Uso:  ./deploy/deploy.sh usuario@host
# Requiere: SSH sin contraseña (ssh-copy-id) y acceso a la misma LAN que las teles.
# Linux  -> servicio systemd (arranca al boot, reinicia si falla)
# macOS  -> LaunchAgent (necesita permiso "Red local" y sesión iniciada)
# ==============================================================================
set -euo pipefail

DEST="${1:?Uso: $0 usuario@host}"
DIR="$(cd "$(dirname "$0")" && pwd)"
LG_CFG="$HOME/.config/lg_tv/config.json"

[ -f "$LG_CFG" ] || { echo "❌ Falta $LG_CFG (empareja la LG antes)"; exit 1; }

OS="$(ssh "$DEST" 'uname -s')"
echo "🎛️  Destino: $DEST ($OS)"

ssh "$DEST" 'mkdir -p ~/mando-tv ~/.config/lg_tv'
rsync -a --delete --exclude __pycache__ "$DIR/../mando_tv" "$DEST:~/mando-tv/"
scp -q "$LG_CFG" "$DEST:~/.config/lg_tv/config.json"

if [ "$OS" = "Linux" ]; then
  ssh "$DEST" 'bash -s' <<'EOF'
set -e
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-websockets adb wakeonlan || sudo apt-get install -y -qq python3 python3-pip adb
python3 -c "import websockets" 2>/dev/null || pip3 install --break-system-packages websockets
sudo tee /etc/systemd/system/mando-tv.service >/dev/null <<UNIT
[Unit]
Description=Mando TV - mando web + Siri hub
After=network-online.target
Wants=network-online.target

[Service]
User=$USER
WorkingDirectory=$HOME/mando-tv
ExecStart=/usr/bin/python3 -m mando_tv
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable mando-tv
sudo systemctl restart mando-tv
sleep 2
systemctl is-active mando-tv
EOF
else
  ssh "$DEST" 'bash -s' <<'EOF'
set -e
PY="$(command -v python3)"
"$PY" -c "import websockets" 2>/dev/null || "$PY" -m pip install --user websockets
command -v adb >/dev/null || brew install android-platform-tools
P=~/Library/LaunchAgents/com.gtrujillo.mandotv.plist
cat > "$P" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.gtrujillo.mandotv</string>
<key>ProgramArguments</key><array><string>$PY</string><string>-m</string><string>mando_tv</string></array>
<key>WorkingDirectory</key><string>$HOME/mando-tv</string>
<key>EnvironmentVariables</key><dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string><key>PYTHONUNBUFFERED</key><string>1</string></dict>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
<key>StandardOutPath</key><string>/tmp/mando_tv.log</string>
<key>StandardErrorPath</key><string>/tmp/mando_tv_err.log</string>
</dict></plist>
PL
launchctl bootout gui/$(id -u)/com.gtrujillo.mandotv 2>/dev/null || true
launchctl bootstrap gui/$(id -u) "$P"
echo "✅ LaunchAgent cargado. Si ves 'No route to host' en /tmp/mando_tv_err.log: Ajustes > Privacidad > Red local."
EOF
fi

HOST_IP="${DEST#*@}"
echo "✅ Listo. Mando: http://$HOST_IP:8899  |  Siri: http://$HOST_IP:8899/api/siri"
echo "👉 Actualiza la IP en tus Atajos de Siri y el icono de la pantalla de inicio."
