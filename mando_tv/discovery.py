"""Descubrimiento automático y resolución dinámica de IPs por dirección MAC."""
import json
import os
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
from . import config


_ip_lg_actual: str = config.IP_LG
_ip_xiaomi_actual: str = config.IP_XIAOMI
_ts_lg_ok: float = 0.0
_ts_xm_ok: float = 0.0
_lock = threading.Lock()
_ultimo_escaneo: float = 0.0


def _normalizar_mac(mac_str: str) -> str:
    """Normaliza cualquier formato MAC (con o sin ceros a la izquierda) a xx:xx:xx:xx:xx:xx."""
    try:
        partes = mac_str.strip().lower().replace("-", ":").split(":")
        if len(partes) == 6:
            return ":".join(f"{int(p, 16):02x}" for p in partes)
    except Exception:
        pass
    return mac_str.strip().lower()


def puerto_abierto(ip: str, puerto: int, timeout: float = 0.3) -> bool:
    """Verifica de forma no bloqueante si un puerto TCP está abierto."""
    if not ip:
        return False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((ip, puerto)) == 0
    except Exception:
        return False


def obtener_ips_arp_por_mac(mac_objetivo: str) -> List[str]:
    """Obtiene todas las IPs asociadas a una MAC en la tabla ARP del sistema."""
    mac_norm = _normalizar_mac(mac_objetivo)
    ips: List[str] = []

    # 1. En Linux (/proc/net/arp)
    if os.path.exists("/proc/net/arp"):
        try:
            with open("/proc/net/arp", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 4 and _normalizar_mac(parts[3]) == mac_norm:
                        ips.append(parts[0])
            if ips:
                return ips
        except Exception:
            pass

    # 2. En macOS / BSD (comando arp -an, que trunca ceros ej: 74:e6:b8:26:2:e)
    try:
        salida = subprocess.check_output(["arp", "-an"], text=True, stderr=subprocess.DEVNULL)
        for linea in salida.splitlines():
            partes = linea.split()
            if len(partes) >= 4:
                mac_candidata = _normalizar_mac(partes[3])
                if mac_candidata == mac_norm:
                    ip_raw = partes[1].strip("()")
                    ips.append(ip_raw)
    except Exception:
        pass

    return ips


def escanear_subred(puerto: int, subred_base: str = "192.168.1.", timeout: float = 0.25) -> List[str]:
    """Escanea la subred completa /24 en paralelo (<1.5s) buscando un puerto específico."""
    ips_a_probar = [f"{subred_base}{i}" for i in range(1, 255)]
    abiertas: List[str] = []

    def _probar(ip: str) -> Optional[str]:
        if puerto_abierto(ip, puerto, timeout=timeout):
            return ip
        return None

    with ThreadPoolExecutor(max_workers=50) as pool:
        for resultado in pool.map(_probar, ips_a_probar):
            if resultado:
                abiertas.append(resultado)

    return abiertas


def resolver_ip_lg(forzar: bool = False) -> str:
    """Resuelve la IP viva de la televisión LG 65\"."""
    global _ultimo_escaneo, _ts_lg_ok
    ahora = time.time()
    with _lock:
        # Caching ultrarrápido: si fue verificada hace menos de 20s y no se fuerza, retornar de inmediato
        if not forzar and (ahora - _ts_lg_ok < 20.0):
            return _ip_lg_actual

        # 1. Si la IP actual responde en puerto 3000, mantenerla
        if not forzar and puerto_abierto(_ip_lg_actual, 3000, timeout=0.2):
            _ts_lg_ok = ahora
            return _ip_lg_actual

        # 2. Buscar en la tabla ARP por la MAC normalizada de la LG
        ips_arp = obtener_ips_arp_por_mac(config.MAC_LG)
        for ip in ips_arp:
            if puerto_abierto(ip, 3000, timeout=0.25):
                _actualizar_ip_lg(ip)
                _ts_lg_ok = ahora
                return ip

        # 3. Si no responde y hace más de 10s desde el último escaneo, barrido de subred
        if ahora - _ultimo_escaneo > 10:
            _ultimo_escaneo = ahora
            subred_ips = escanear_subred(3000)
            if subred_ips:
                for ip in subred_ips:
                    _actualizar_ip_lg(ip)
                    _ts_lg_ok = ahora
                    return ip

        return _ip_lg_actual


def resolver_ip_xiaomi(forzar: bool = False) -> str:
    """Resuelve la IP viva de la televisión Xiaomi."""
    global _ts_xm_ok
    ahora = time.time()
    with _lock:
        if not forzar and (ahora - _ts_xm_ok < 20.0):
            return _ip_xiaomi_actual

        if not forzar and puerto_abierto(_ip_xiaomi_actual, 5555, timeout=0.2):
            _ts_xm_ok = ahora
            return _ip_xiaomi_actual

        ips_arp = obtener_ips_arp_por_mac(config.MAC_XIAOMI)
        for ip in ips_arp:
            if puerto_abierto(ip, 5555, timeout=0.25):
                _actualizar_ip_xiaomi(ip)
                _ts_xm_ok = ahora
                return ip

        subred_ips = escanear_subred(5555)
        if subred_ips:
            _actualizar_ip_xiaomi(subred_ips[0])
            _ts_xm_ok = ahora
            return subred_ips[0]

        return _ip_xiaomi_actual


def _actualizar_ip_lg(nueva_ip: str):
    """Actualiza la IP de la LG en memoria y en ~/.config/lg_tv/config.json."""
    global _ip_lg_actual
    if _ip_lg_actual != nueva_ip:
        print(f"📡 [DISCOVERY] LG TV detectada en nueva IP: {nueva_ip} (anterior: {_ip_lg_actual})")
        _ip_lg_actual = nueva_ip
        config.IP_LG = nueva_ip
        # Actualizar archivo config.json si existe
        try:
            ruta = config.LG_CONFIG_PATH
            if os.path.exists(ruta):
                with open(ruta, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                datos["ip"] = nueva_ip
                with open(ruta, "w", encoding="utf-8") as f:
                    json.dump(datos, f, indent=2)
        except Exception:
            pass


def _actualizar_ip_xiaomi(nueva_ip: str):
    """Actualiza la IP de Xiaomi en memoria."""
    global _ip_xiaomi_actual
    if _ip_xiaomi_actual != nueva_ip:
        print(f"📡 [DISCOVERY] Xiaomi TV detectada en nueva IP: {nueva_ip} (anterior: {_ip_xiaomi_actual})")
        _ip_xiaomi_actual = nueva_ip
        config.IP_XIAOMI = nueva_ip
