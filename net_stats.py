"""
Network Parameters & Live Statistics Module
Retrieves adapter properties, Wi-Fi parameters (netsh wlan),
live bandwidth speeds (upload/download), and ping latencies.
"""

import os
import re
import socket
import subprocess
import time
from typing import Dict, Any, Optional
import psutil

# Cache for bandwidth calculation
_last_io_sample = {
    "bytes_sent": 0,
    "bytes_recv": 0,
    "time": 0.0,
    "upload_speed": 0.0,
    "download_speed": 0.0
}


def get_default_interface_and_ip():
    """
    Find the local IP and active interface used for outbound traffic.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()
    
    # Match with psutil interfaces
    active_iface = None
    for iface_name, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and addr.address == local_ip:
                active_iface = iface_name
                break
        if active_iface:
            break
            
    return local_ip, active_iface


def get_wifi_details() -> Dict[str, Any]:
    """
    Get detailed Wi-Fi information using Windows `netsh wlan show interfaces`.
    """
    details = {
        "is_wifi": False,
        "ssid": "Không dây (Chưa kết nối)",
        "signal": 0,
        "rssi": None,
        "radio_type": "N/A",
        "channel": "N/A",
        "band": "N/A",
        "bssid": "N/A",
        "receive_rate": "N/A",
        "transmit_rate": "N/A",
        "adapter_desc": "N/A"
    }

    try:
        output = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"],
            stderr=subprocess.DEVNULL,
            text=True,
            errors="ignore"
        )
        if "State" in output and "connected" in output.lower():
            details["is_wifi"] = True
            for line in output.splitlines():
                line = line.strip()
                if ":" in line:
                    key, val = [p.strip() for p in line.split(":", 1)]
                    key_lower = key.lower()
                    if key_lower == "ssid":
                        details["ssid"] = val
                    elif key_lower == "description":
                        details["adapter_desc"] = val
                    elif key_lower == "signal":
                        # e.g., "92%"
                        num = re.sub(r"[^\d]", "", val)
                        details["signal"] = int(num) if num else 0
                    elif key_lower == "rssi":
                        details["rssi"] = val
                    elif key_lower == "radio type":
                        details["radio_type"] = val
                    elif key_lower == "channel":
                        details["channel"] = val
                    elif key_lower == "band":
                        details["band"] = val
                    elif key_lower == "bssid" or key_lower == "ap bssid":
                        details["bssid"] = val.upper()
                    elif key_lower == "receive rate (mbps)":
                        details["receive_rate"] = f"{val} Mbps"
                    elif key_lower == "transmit rate (mbps)":
                        details["transmit_rate"] = f"{val} Mbps"
    except Exception:
        pass

    return details


def get_ipconfig_details() -> Dict[str, Any]:
    """
    Parse ipconfig /all to get subnet mask, gateway, DNS servers, DHCP, etc.
    """
    info = {
        "local_ip": "",
        "subnet_mask": "255.255.255.0",
        "gateway": "",
        "dns_servers": [],
        "dhcp_enabled": True,
        "mac_address": ""
    }

    local_ip, _ = get_default_interface_and_ip()
    info["local_ip"] = local_ip

    try:
        output = subprocess.check_output(["ipconfig", "/all"], text=True, errors="ignore")
        sections = output.split("\n\n")
        
        for sec in sections:
            if local_ip in sec:
                # This section belongs to the active adapter
                lines = sec.splitlines()
                for line in lines:
                    line = line.strip()
                    if "Subnet Mask" in line:
                        parts = line.split(":")
                        if len(parts) > 1:
                            info["subnet_mask"] = parts[1].strip()
                    elif "Default Gateway" in line:
                        parts = line.split(":")
                        if len(parts) > 1:
                            gw = parts[1].strip()
                            if re.match(r"^\d+\.\d+\.\d+\.\d+$", gw):
                                info["gateway"] = gw
                    elif "DNS Servers" in line:
                        parts = line.split(":")
                        if len(parts) > 1:
                            dns = parts[1].strip()
                            if re.match(r"^\d+\.\d+\.\d+\.\d+$", dns):
                                info["dns_servers"].append(dns)
                    elif "Physical Address" in line:
                        parts = line.split(":")
                        if len(parts) > 1:
                            info["mac_address"] = parts[1].strip().replace("-", ":").upper()
    except Exception:
        pass

    # If gateway not found via ipconfig, try route print or fallback
    if not info["gateway"]:
        try:
            route_out = subprocess.check_output(["route", "print", "0.0.0.0"], text=True, errors="ignore")
            for line in route_out.splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                    if re.match(r"^\d+\.\d+\.\d+\.\d+$", parts[2]):
                        info["gateway"] = parts[2]
                        break
        except Exception:
            pass

    return info


def get_live_bandwidth() -> Dict[str, Any]:
    """
    Calculate live download & upload speed by delta byte count.
    """
    global _last_io_sample
    now = time.time()
    tot_io = psutil.net_io_counters()

    current_bytes_sent = tot_io.bytes_sent
    current_bytes_recv = tot_io.bytes_recv

    if _last_io_sample["time"] == 0.0:
        _last_io_sample = {
            "bytes_sent": current_bytes_sent,
            "bytes_recv": current_bytes_recv,
            "time": now,
            "upload_speed": 0.0,
            "download_speed": 0.0
        }
        return {
            "upload_speed_bytes": 0,
            "download_speed_bytes": 0,
            "upload_speed_str": "0 B/s",
            "download_speed_str": "0 B/s",
            "total_sent_str": format_bytes(current_bytes_sent),
            "total_recv_str": format_bytes(current_bytes_recv)
        }

    dt = now - _last_io_sample["time"]
    if dt < 0.2:
        # Avoid division by zero on very rapid requests
        upload_speed = _last_io_sample["upload_speed"]
        download_speed = _last_io_sample["download_speed"]
    else:
        upload_speed = max(0.0, (current_bytes_sent - _last_io_sample["bytes_sent"]) / dt)
        download_speed = max(0.0, (current_bytes_recv - _last_io_sample["bytes_recv"]) / dt)
        _last_io_sample["bytes_sent"] = current_bytes_sent
        _last_io_sample["bytes_recv"] = current_bytes_recv
        _last_io_sample["time"] = now
        _last_io_sample["upload_speed"] = upload_speed
        _last_io_sample["download_speed"] = download_speed

    return {
        "upload_speed_bytes": round(upload_speed),
        "download_speed_bytes": round(download_speed),
        "upload_speed_str": format_speed(upload_speed),
        "download_speed_str": format_speed(download_speed),
        "total_sent_str": format_bytes(current_bytes_sent),
        "total_recv_str": format_bytes(current_bytes_recv),
        "total_sent_raw": current_bytes_sent,
        "total_recv_raw": current_bytes_recv
    }


def format_bytes(b: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if b < 1024.0:
            return f"{b:.1f} {unit}"
        b /= 1024.0
    return f"{b:.1f} PB"


def format_speed(bytes_per_sec: float) -> str:
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.0f} B/s"
    elif bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    else:
        return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"


def ping_host(host: str, timeout_ms: int = 400) -> Optional[float]:
    """
    Ping a single host once and return latency in milliseconds, or None if failed.
    """
    try:
        res = subprocess.run(
            ["ping", "-n", "1", "-w", str(timeout_ms), host],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=(timeout_ms / 1000) + 1.0
        )
        if res.returncode == 0:
            match = re.search(r"time[<=](\d+)ms", res.stdout, re.IGNORECASE)
            if match:
                return float(match.group(1))
            if "time<1ms" in res.stdout.lower() or "time=0ms" in res.stdout.lower():
                return 0.5
    except Exception:
        pass
    return None


def get_all_network_stats() -> Dict[str, Any]:
    """
    Composite function returning all network statistics at once.
    """
    local_ip, iface_name = get_default_interface_and_ip()
    ip_cfg = get_ipconfig_details()
    wifi_cfg = get_wifi_details()
    bandwidth = get_live_bandwidth()

    # Quick internet ping check
    gw_ping = ping_host(ip_cfg["gateway"], timeout_ms=300) if ip_cfg["gateway"] else None
    dns_ping = ping_host("8.8.8.8", timeout_ms=500)

    # List of all physical and virtual adapters on this machine
    adapters = []
    for name, addrs in psutil.net_if_addrs().items():
        ipv4 = next((a.address for a in addrs if a.family == socket.AF_INET), None)
        mac = next((a.address.replace("-", ":").upper() for a in addrs if a.family == psutil.AF_LINK and a.address), None)
        stats = psutil.net_if_stats().get(name)
        is_up = stats.isup if stats else False
        speed = stats.speed if stats else 0
        if ipv4 and not ipv4.startswith("127."):
            adapters.append({
                "name": name,
                "ipv4": ipv4,
                "mac": mac,
                "is_up": is_up,
                "speed_mbps": speed,
                "is_active": (name == iface_name)
            })

    return {
        "local_ip": local_ip,
        "active_interface": iface_name or "Wi-Fi",
        "subnet_mask": ip_cfg.get("subnet_mask", "255.255.255.0"),
        "gateway": ip_cfg.get("gateway", ""),
        "dns_servers": ip_cfg.get("dns_servers", ["8.8.8.8"]),
        "mac_address": ip_cfg.get("mac_address", ""),
        "wifi": wifi_cfg,
        "bandwidth": bandwidth,
        "gateway_ping_ms": gw_ping,
        "internet_ping_ms": dns_ping,
        "is_online": (dns_ping is not None or gw_ping is not None),
        "adapters": adapters
    }


def scan_wifi_access_points() -> List[Dict[str, Any]]:
    """
    Scan surrounding Wi-Fi networks and access points (BSSIDs)
    with exact signal strength in dBm and percentage.
    """
    try:
        output = subprocess.check_output(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            text=True,
            errors="ignore",
            stderr=subprocess.DEVNULL
        )
    except Exception:
        return []

    networks = []
    current_ssid = "Hidden / Không tên"
    current_auth = "N/A"
    current_enc = "N/A"

    lines = output.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("SSID"):
            parts = line.split(":", 1)
            if len(parts) > 1:
                name = parts[1].strip()
                current_ssid = name if name else "(Mạng ẩn / Hidden SSID)"
        elif "Authentication" in line:
            parts = line.split(":", 1)
            if len(parts) > 1:
                current_auth = parts[1].strip()
        elif "Encryption" in line:
            parts = line.split(":", 1)
            if len(parts) > 1:
                current_enc = parts[1].strip()
        elif line.startswith("BSSID"):
            parts = line.split(":", 1)
            bssid_mac = parts[1].strip().upper() if len(parts) > 1 else ""
            
            sig_pct = 0
            radio = "N/A"
            band = "N/A"
            channel = "N/A"
            connected_stations = None

            i += 1
            while i < len(lines):
                sub = lines[i].strip()
                if sub.startswith("BSSID") or sub.startswith("SSID"):
                    i -= 1
                    break
                if sub.startswith("Signal"):
                    nums = re.findall(r"\d+", sub)
                    if nums:
                        sig_pct = int(nums[0])
                elif sub.startswith("Radio type"):
                    radio = sub.split(":", 1)[1].strip() if ":" in sub else sub
                elif sub.startswith("Band"):
                    band = sub.split(":", 1)[1].strip() if ":" in sub else sub
                elif sub.startswith("Channel"):
                    nums = re.findall(r"\d+", sub)
                    if nums:
                        channel = nums[0]
                elif "Connected Stations" in sub:
                    nums = re.findall(r"\d+", sub)
                    if nums:
                        connected_stations = int(nums[0])
                i += 1

            # Standard formula to convert Windows Wi-Fi % to dBm:
            # 100% -> -50 dBm, 50% -> -75 dBm, 0% -> -100 dBm
            dbm = round((sig_pct / 2.0) - 100)

            networks.append({
                "ssid": current_ssid,
                "bssid": bssid_mac,
                "signal_pct": sig_pct,
                "signal_dbm": dbm,
                "radio_type": radio,
                "band": band,
                "channel": channel,
                "connected_stations": connected_stations,
                "auth": current_auth,
                "encryption": current_enc
            })
        i += 1

    # Sort strongest signal first
    return sorted(networks, key=lambda x: x["signal_dbm"], reverse=True)

