#!/usr/bin/env bash
# Tests basicos del API mando-tv
# Uso: ./tests/test_api.sh [host:puerto]
# Ejemplo con Pi: ./tests/test_api.sh 192.168.1.141:8899
# Ejemplo con Tailscale: ./tests/test_api.sh 100.95.199.1:8899
# Por defecto: 192.168.1.141:8899

HOST="${1:-192.168.1.141:8899}"
BASE="http://$HOST"
OK=0; FAIL=0

check() {
    local desc="$1" url="$2" expect="$3"
    local body
    body=$(curl -sf --max-time 4 "$url" 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo "FAIL [$desc] -> curl error (servidor caido o TV apagada)"
        FAIL=$((FAIL+1))
        return
    fi
    if echo "$body" | grep -q "$expect"; then
        echo "OK   [$desc]"
        OK=$((OK+1))
    else
        echo "FAIL [$desc] -> esperaba '$expect' en: ${body:0:120}"
        FAIL=$((FAIL+1))
    fi
}

echo "=== Tests mando-tv ($BASE) ==="
echo ""

# --- Paginas web ---
check "index.html sirve contenido"   "$BASE/"      "Mando"
check "siri.html sirve contenido"    "$BASE/siri"  "Siri"
check "siri.html sin IP hardcodeada" "$BASE/siri"  "$HOST"

# --- API status (siempre responde aunque la TV este apagada) ---
check "api/status devuelve JSON"     "$BASE/api/status"  "lg_online"
check "api/status tiene xiaomi"      "$BASE/api/status"  "xiaomi_online"
check "api/status tiene timers"      "$BASE/api/status"  "timer_lg"

# --- API action: respuesta instantanea (<100ms), accion va en background ---
check "action encender lg"           "$BASE/api/action?cmd=encender&target=lg"      '"ok": true'
check "action apagar lg"             "$BASE/api/action?cmd=apagar&target=lg"        '"ok": true'
check "action vol_up lg"             "$BASE/api/action?cmd=vol_up&target=lg"        '"ok": true'
check "action vol_down lg"           "$BASE/api/action?cmd=vol_down&target=lg"      '"ok": true'
check "action mute lg"               "$BASE/api/action?cmd=mute&target=lg"          '"ok": true'
check "action noche lg"              "$BASE/api/action?cmd=noche&target=lg"         '"ok": true'
check "action dia lg"                "$BASE/api/action?cmd=dia&target=lg"           '"ok": true'
check "action cine lg"               "$BASE/api/action?cmd=cine&target=lg"          '"ok": true'
check "action juego lg"              "$BASE/api/action?cmd=juego&target=lg"         '"ok": true'
check "action solo_audio lg"         "$BASE/api/action?cmd=solo_audio&target=lg"    '"ok": true'
check "action audio_sharp lg"        "$BASE/api/action?cmd=audio_sharp&target=lg"   '"ok": true'
check "action audio_tv lg"           "$BASE/api/action?cmd=audio_tv&target=lg"      '"ok": true'
check "action up xiaomi"             "$BASE/api/action?cmd=up&target=xiaomi"        '"ok": true'
check "action down xiaomi"           "$BASE/api/action?cmd=down&target=xiaomi"      '"ok": true'
check "action left xiaomi"           "$BASE/api/action?cmd=left&target=xiaomi"      '"ok": true'
check "action right xiaomi"          "$BASE/api/action?cmd=right&target=xiaomi"     '"ok": true'
check "action enter xiaomi"          "$BASE/api/action?cmd=enter&target=xiaomi"     '"ok": true'
check "action home xiaomi"           "$BASE/api/action?cmd=home&target=xiaomi"      '"ok": true'
check "action back xiaomi"           "$BASE/api/action?cmd=back&target=xiaomi"      '"ok": true'
check "action play_pause xiaomi"     "$BASE/api/action?cmd=play_pause&target=xiaomi" '"ok": true'
check "action smarttube xiaomi"      "$BASE/api/action?cmd=smarttube&target=xiaomi" '"ok": true'
check "action set_brillo slider"     "$BASE/api/action?cmd=set_brillo&target=lg&val=50"   '"ok": true'
check "action set_volumen slider"    "$BASE/api/action?cmd=set_volumen&target=lg&val=30"  '"ok": true'
check "action cancelar_timer ambas"  "$BASE/api/action?cmd=cancelar_timer&target=ambas"   '"ok": true'

# --- API Siri: devuelve texto en espanol para que Siri lo hable ---
check "siri encender lg"             "$BASE/api/siri?action=encender&target=lg"       "LG"
check "siri apagar lg"               "$BASE/api/siri?action=apagar&target=lg"         "LG"
check "siri encender xiaomi"         "$BASE/api/siri?action=encender&target=xiaomi"   "Xiaomi"
check "siri noche lg"                "$BASE/api/siri?action=noche&target=lg"          "Noche"
check "siri dia lg"                  "$BASE/api/siri?action=dia&target=lg"            "100"
check "siri cine lg"                 "$BASE/api/siri?action=cine&target=lg"           "Cine"
check "siri juego lg"                "$BASE/api/siri?action=juego&target=lg"          "Juego"
check "siri noche ambas"             "$BASE/api/siri?action=noche&target=ambas"       "ambas"
check "siri apagar ambas"            "$BASE/api/siri?action=apagar&target=ambas"      "apagadas"
check "siri volumen"                 "$BASE/api/siri?action=volumen&target=lg&val=25" "25"
check "siri silenciar"               "$BASE/api/siri?action=silenciar&target=ambas"   "Silenciando"
check "siri status responde"         "$BASE/api/siri?action=status"                   "está"

# --- Ruta inexistente debe devolver 404 ---
code=$(curl -so /dev/null -w "%{http_code}" --max-time 3 "$BASE/no-existe" 2>/dev/null)
if [ "$code" = "404" ]; then
    echo "OK   [404 en ruta invalida]"; OK=$((OK+1))
else
    echo "FAIL [404 en ruta invalida] -> codigo: $code"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== Resultado: $OK OK  |  $FAIL FAILED ==="
[ $FAIL -eq 0 ] && exit 0 || exit 1
