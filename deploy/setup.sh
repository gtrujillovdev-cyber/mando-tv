#!/usr/bin/env bash
# ==============================================================================
# Mando TV - Universal Remote & Siri Voice Hub Setup Script
# ==============================================================================
set -e

echo "🎛️  Instalando dependencias de Mando TV..."

# Verificar Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 no está instalado."
    exit 1
fi

# Instalar websockets si pip está disponible
if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt || true
elif command -v pip &> /dev/null; then
    pip install -r requirements.txt || true
fi

# Verificar adb
if ! command -v adb &> /dev/null; then
    echo "⚠️  Aviso: 'adb' no está en el PATH. Instálalo con 'brew install android-platform-tools' (macOS) o 'sudo apt install adb' (Debian/Ubuntu/Raspberry Pi)."
else
    echo "✅ ADB detectado correctamente."
fi

echo "🚀 Todo listo. Puedes iniciar el servidor con: python3 -m src.server 8899"
