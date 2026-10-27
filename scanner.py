"""
Network Scanner Module - Equivalent to Wireless Network Watcher
Uses native Windows SendARP, system ARP cache, DNS resolution,
and vendor lookup to detect all connected network devices.
"""

import ctypes
import json
import os
import re
import socket
import struct
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Any, Optional

from oui_lookup import get_mac_vendor, is_randomized_mac
import net_stats

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HISTORY_FILE = os.path.join(DATA_DIR, "scan_history.json")
ALIASES_FILE = os.path.join(DATA_DIR, "device_aliases.json")

# Persistent storage
_history: Dict[str, Dict[str, Any]] = {}
_aliases: Dict[str, str] = {}
_history_lock = threading.Lock()

# Scan state
_scan_state = {
    "is_scanning": False,
    "progress": 0,
    "total": 0,
    "scanned": 0,
    "found_count": 0,
    "start_time": 0.0,
    "last_scan_time": "",
    "new_devices_found": []
}


def _load_persistence():
    global _history, _aliases
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                _history = json.load(f)
        except Exception:
            _history = {}

    if os.path.exists(ALIASES_FILE):
        try:
            with open(ALIASES_FILE, "r", encoding="utf-8") as f:
                _aliases = json.load(f)
        except Exception:
            _aliases = {}


def _save_persistence():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(_history, f, indent=2, ensure_ascii=False)
        with open(ALIASES_FILE, "w", encoding="utf-8") as f:
            json.dump(_aliases, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


_load_persistence()


def set_device_alias(ip_or_mac: str, alias: str):
    """
    Set a user-friendly custom name for a device.
    """
    key = ip_or_mac.strip().upper()
    with _history_lock:
        _aliases[key] = alias.strip()
        # Also update in history if present
        for mac, dev in _history.items():
            if mac == key or dev.get("ip") == ip_or_mac:
                dev["custom_name"] = alias.strip()
        _save_persistence()


def clear_scan_history():
    """
    Clear all saved device history.
    """
    global _history
    with _history_lock:
        _history = {}
        _save_persistence()


def send_arp(ip: str) -> Optional[str]:
    """
    Perform a direct native Windows SendARP request.
    Returns formatted MAC string ('AA:BB:CC:DD:EE:FF') or None.
    """
    try:
        dest_ip = struct.unpack('<I', socket.inet_aton(ip))[0]
        mac_bytes = (ctypes.c_ubyte * 6)()
        mac_len = ctypes.c_ulong(6)
        res = ctypes.windll.iphlpapi.SendARP(dest_ip, 0, ctypes.byref(mac_bytes), ctypes.byref(mac_len))
        if res == 0:
            return ":".join(f"{b:02X}" for b in mac_bytes)
    except Exception:
        pass
    return None


def resolve_hostname(ip: str) -> str:
    """
    Attempt to resolve hostname via socket.gethostbyaddr.
    """
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return ""


def ping_latency(ip: str) -> Optional[float]:
    """
    Measure ping latency in ms.
    """
    return net_stats.ping_host(ip, timeout_ms=300)


def get_system_arp_table() -> List[Dict[str, str]]:
    """
    Read Windows ARP table (`arp -a`).
    """
    devices = []
    try:
        out = subprocess.check_output(["arp", "-a"], text=True, errors="ignore")
        current_iface = None
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("Interface:"):
                parts = line.split()
                if len(parts) >= 2:
                    current_iface = parts[1]
            elif line:
                parts = line.split()
                if len(parts) >= 3:
                    ip, mac, tip = parts[0], parts[1], parts[2]
                    if (
                        re.match(r"^\d+\.\d+\.\d+\.\d+$", ip)
                        and not ip.startswith("224.")
                        and not ip.startswith("239.")
                        and not ip.endswith(".255")
                    ):
                        mac_clean = mac.replace("-", ":").upper()
                        if mac_clean != "FF:FF:FF:FF:FF:FF" and len(mac_clean) == 17:
                            devices.append({
                                "ip": ip,
                                "mac": mac_clean,
                                "interface": current_iface,
                                "type": tip
                            })
    except Exception:
        pass
    return devices


def guess_device_type(vendor: str, hostname: str, is_gateway: bool, is_localhost: bool) -> str:
    """
    Determine the category / icon of a device.
    """
    if is_localhost:
        return "Máy tính này (This PC)"
    if is_gateway:
        return "Bộ định tuyến / Router Wi-Fi"

    v_lower = (vendor or "").lower()
    h_lower = (hostname or "").lower()

    if any(k in v_lower for k in ["apple", "samsung", "xiaomi", "huawei", "oneplus", "oppo", "vivo", "realme", "randomized"]):
        return "Điện thoại / Tablet"
    if any(k in h_lower for k in ["iphone", "ipad", "android", "galaxy", "pixel", "redmi"]):
        return "Điện thoại / Tablet"
    if any(k in v_lower for k in ["espressif", "tuya", "sonoff", "smart", "tapo", "camera", "hikvision", "dahua"]):
        return "Thiết bị thông minh / IoT / Camera"
    if any(k in v_lower for k in ["dell", "hp", "lenovo", "asus", "acer", "intel", "realtek", "msi"]):
        return "Máy tính (PC / Laptop)"
    if any(k in v_lower for k in ["sony", "playstation", "nintendo", "xbox"]):
        return "Máy chơi game (Console)"
    if any(k in v_lower for k in ["cisco", "mikrotik", "ubiquiti", "tp-link", "d-link", "netgear", "tenda"]):
        return "Thiết bị mạng (Router / AP)"

    return "Thiết bị mạng (Device)"


def generate_ip_list_for_interface(local_ip: str, gateway: str, custom_range: Optional[str] = None) -> List[str]:
    """
    Generate target IP range to scan.
    Default: Local /24 subnet + Gateway.
    """
    if custom_range:
        # User defined e.g., "192.168.1.1-192.168.1.50" or "10.12.8.0/24"
        if "/" in custom_range:
            try:
                base, mask = custom_range.split("/")
                parts = [int(p) for p in base.split(".")]
                if mask == "24":
                    return [f"{parts[0]}.{parts[1]}.{parts[2]}.{i}" for i in range(1, 255)]
            except Exception:
                pass
        elif "-" in custom_range:
            try:
                start_ip, end_ip = [p.strip() for p in custom_range.split("-")]
                s_parts = [int(p) for p in start_ip.split(".")]
                e_parts = [int(p) for p in end_ip.split(".")]
                if s_parts[0:3] == e_parts[0:3]:
                    prefix = f"{s_parts[0]}.{s_parts[1]}.{s_parts[2]}"
                    return [f"{prefix}.{i}" for i in range(s_parts[3], e_parts[3] + 1)]
            except Exception:
                pass

    # Default: Scan the /24 around local IP
    ip_parts = local_ip.split(".")
    if len(ip_parts) == 4:
        prefix = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
        ips = [f"{prefix}.{i}" for i in range(1, 255)]
        if gateway and gateway not in ips:
            ips.append(gateway)
        return ips

    return [local_ip]


def run_network_scan(custom_range: Optional[str] = None):
    """
    Full background scan worker.
    """
    global _scan_state, _history

    if _scan_state["is_scanning"]:
        return

    _scan_state["is_scanning"] = True
    _scan_state["progress"] = 0
    _scan_state["scanned"] = 0
    _scan_state["found_count"] = 0
    _scan_state["new_devices_found"] = []
    _scan_state["start_time"] = time.time()

    try:
        # 1. Fetch current network info
        ip_info = net_stats.get_ipconfig_details()
        local_ip = ip_info.get("local_ip", "")
        local_mac = ip_info.get("mac_address", "")
        gateway_ip = ip_info.get("gateway", "")

        target_ips = generate_ip_list_for_interface(local_ip, gateway_ip, custom_range)
        _scan_state["total"] = len(target_ips)

        found_ips: Dict[str, str] = {}  # ip -> mac

        # Include local machine
        if local_ip and local_mac:
            found_ips[local_ip] = local_mac

        # 2. Multi-threaded SendARP probe
        def probe(ip):
            mac = send_arp(ip)
            return ip, mac

        with ThreadPoolExecutor(max_workers=60) as executor:
            futures = [executor.submit(probe, ip) for ip in target_ips]
            for fut in as_completed(futures):
                _scan_state["scanned"] += 1
                _scan_state["progress"] = int((_scan_state["scanned"] / max(1, _scan_state["total"])) * 80)
                try:
                    ip, mac = fut.result()
                    if mac:
                        found_ips[ip] = mac
                except Exception:
                    pass

        # 3. Read ARP cache to catch any passive or existing devices
        arp_cache = get_system_arp_table()
        for item in arp_cache:
            ip = item["ip"]
            mac = item["mac"]
            # Only include if in same network or relevant
            if ip not in found_ips:
                found_ips[ip] = mac

        _scan_state["found_count"] = len(found_ips)
        _scan_state["progress"] = 85

        # 4. Resolve details for each discovered device (Hostname, Vendor, Latency)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_devices = []

        def enrich(ip, mac):
            is_local = (ip == local_ip)
            is_gw = (ip == gateway_ip)
            
            hostname = socket.gethostname() if is_local else resolve_hostname(ip)
            vendor = get_mac_vendor(mac)
            latency = 0.5 if is_local else ping_latency(ip)
            dev_type = guess_device_type(vendor, hostname, is_gw, is_local)

            return {
                "ip": ip,
                "mac": mac,
                "hostname": hostname,
                "vendor": vendor,
                "latency_ms": latency,
                "device_type": dev_type,
                "is_gateway": is_gw,
                "is_localhost": is_local,
                "is_randomized_mac": is_randomized_mac(mac)
            }

        enriched_list = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            fut_map = {executor.submit(enrich, ip, mac): mac for ip, mac in found_ips.items()}
            for fut in as_completed(fut_map):
                try:
                    enriched_list.append(fut.result())
                except Exception:
                    pass

        _scan_state["progress"] = 95

        # 5. Merge with persistent history
        with _history_lock:
            # Mark existing history devices as offline first if they weren't seen in this scan
            current_macs = set()
            for dev in enriched_list:
                mac = dev["mac"]
                current_macs.add(mac)

                custom_name = _aliases.get(mac) or _aliases.get(dev["ip"]) or ""

                if mac not in _history:
                    # Brand new device!
                    dev["first_detected"] = now_str
                    dev["last_detected"] = now_str
                    dev["detection_count"] = 1
                    dev["status"] = "online"
                    dev["custom_name"] = custom_name
                    dev["is_new"] = True
                    _history[mac] = dev
                    new_devices.append(dev)
                else:
                    # Existing device
                    existing = _history[mac]
                    was_offline = (existing.get("status") == "offline")
                    existing["ip"] = dev["ip"]
                    existing["hostname"] = dev["hostname"] or existing.get("hostname", "")
                    existing["vendor"] = dev["vendor"]
                    existing["latency_ms"] = dev["latency_ms"]
                    existing["device_type"] = dev["device_type"]
                    existing["is_gateway"] = dev["is_gateway"]
                    existing["is_localhost"] = dev["is_localhost"]
                    existing["is_randomized_mac"] = dev["is_randomized_mac"]
                    existing["last_detected"] = now_str
                    existing["detection_count"] = existing.get("detection_count", 0) + 1
                    existing["status"] = "online"
                    existing["custom_name"] = custom_name or existing.get("custom_name", "")
                    existing["is_new"] = was_offline
                    if was_offline:
                        new_devices.append(existing)

            # Mark devices not found in this scan as offline
            for mac, dev in _history.items():
                if mac not in current_macs:
                    dev["status"] = "offline"
                    dev["latency_ms"] = None
                    dev["is_new"] = False

            _save_persistence()

        _scan_state["new_devices_found"] = new_devices
        _scan_state["last_scan_time"] = now_str
        _scan_state["progress"] = 100

    finally:
        _scan_state["is_scanning"] = False


def trigger_async_scan(custom_range: Optional[str] = None):
    """
    Launch scan in a background daemon thread.
    """
    if _scan_state["is_scanning"]:
        return False
    t = threading.Thread(target=run_network_scan, args=(custom_range,), daemon=True)
    t.start()
    return True


def get_scan_status() -> Dict[str, Any]:
    """
    Get current scanning progress and statistics.
    """
    elapsed = round(time.time() - _scan_state["start_time"], 1) if _scan_state["is_scanning"] else 0.0
    return {
        "is_scanning": _scan_state["is_scanning"],
        "progress": _scan_state["progress"],
        "total": _scan_state["total"],
        "scanned": _scan_state["scanned"],
        "found_count": _scan_state["found_count"],
        "elapsed_seconds": elapsed,
        "last_scan_time": _scan_state["last_scan_time"],
        "new_devices": _scan_state["new_devices_found"]
    }


def get_all_devices() -> List[Dict[str, Any]]:
    """
    Get all devices sorted by: Localhost first, Gateway second, then by IP address.
    """
    with _history_lock:
        devices = list(_history.values())

    def sort_key(d):
        if d.get("is_localhost"):
            return (0, 0)
        if d.get("is_gateway"):
            return (1, 0)
        # Parse IP into tuple of ints for numerical sorting
        ip = d.get("ip", "0.0.0.0")
        try:
            parts = [int(p) for p in ip.split(".")]
            return (2, tuple(parts))
        except Exception:
            return (3, (0, 0, 0, 0))

    return sorted(devices, key=sort_key)
