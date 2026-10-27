"""
Network Watcher Web - Main Flask Server & REST API
A web-based network device monitor and parameters watcher (like Wireless Network Watcher)
"""

import csv
import io
import json
import os
import socket
import subprocess
import sys
import threading
import time

# Ensure UTF-8 output on Windows console
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from flask import Flask, render_template, jsonify, request, Response

import net_stats
import scanner
from oui_lookup import get_mac_vendor

app = Flask(__name__, static_folder="static", template_folder="templates")
app.json.ensure_ascii = False

# Periodic background auto-scanner thread
_auto_scan_interval = 30  # seconds (default 30s)
_auto_scan_enabled = True
_auto_scan_thread = None
_auto_scan_stop = threading.Event()


def _auto_scan_worker():
    while not _auto_scan_stop.is_set():
        if _auto_scan_enabled and not scanner.get_scan_status()["is_scanning"]:
            try:
                scanner.run_network_scan()
            except Exception:
                pass
        # Sleep in small increments to allow instant cancel
        for _ in range(max(1, _auto_scan_interval * 2)):
            if _auto_scan_stop.is_set():
                break
            time.sleep(0.5)


def start_background_watcher():
    global _auto_scan_thread
    if _auto_scan_thread is None or not _auto_scan_thread.is_alive():
        _auto_scan_stop.clear()
        _auto_scan_thread = threading.Thread(target=_auto_scan_worker, daemon=True)
        _auto_scan_thread.start()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/network-stats")
def api_network_stats():
    """
    Returns real-time network parameters, Wi-Fi info, and live bandwidth.
    """
    stats = net_stats.get_all_network_stats()
    return jsonify(stats)


@app.route("/api/devices")
def api_devices():
    """
    Returns the list of all detected devices.
    """
    devices = scanner.get_all_devices()
    online_count = sum(1 for d in devices if d.get("status") == "online")
    offline_count = len(devices) - online_count
    status = scanner.get_scan_status()

    return jsonify({
        "devices": devices,
        "total_count": len(devices),
        "online_count": online_count,
        "offline_count": offline_count,
        "last_scan_time": status["last_scan_time"],
        "is_scanning": status["is_scanning"]
    })


@app.route("/api/scan", methods=["POST"])
def api_trigger_scan():
    """
    Trigger manual network scan.
    Optional JSON: { "range": "10.12.8.1-10.12.8.254" }
    """
    data = request.get_json(silent=True) or {}
    custom_range = data.get("range")
    if custom_range and not custom_range.strip():
        custom_range = None

    started = scanner.trigger_async_scan(custom_range)
    return jsonify({"success": started, "message": "Quét mạng đã bắt đầu" if started else "Đang có phiên quét đang chạy"})


@app.route("/api/scan-status")
def api_scan_status():
    """
    Get current progress of the network scan.
    """
    return jsonify(scanner.get_scan_status())


@app.route("/api/auto-scan-settings", methods=["GET", "POST"])
def api_auto_scan_settings():
    """
    Get or update auto-scan settings.
    """
    global _auto_scan_enabled, _auto_scan_interval
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        if "enabled" in data:
            _auto_scan_enabled = bool(data["enabled"])
        if "interval" in data:
            _auto_scan_interval = max(5, int(data["interval"]))
        return jsonify({"enabled": _auto_scan_enabled, "interval": _auto_scan_interval})

    return jsonify({"enabled": _auto_scan_enabled, "interval": _auto_scan_interval})


@app.route("/api/device/alias", methods=["POST"])
def api_device_alias():
    """
    Set custom name for a device by MAC or IP.
    """
    data = request.get_json(silent=True) or {}
    mac = data.get("mac", "")
    alias = data.get("alias", "")
    if not mac:
        return jsonify({"success": False, "error": "Thiếu địa chỉ MAC"}), 400

    scanner.set_device_alias(mac, alias)
    return jsonify({"success": True})


@app.route("/api/clear-history", methods=["POST"])
def api_clear_history():
    """
    Clear all saved devices and trigger a fresh scan.
    """
    scanner.clear_scan_history()
    scanner.trigger_async_scan()
    return jsonify({"success": True})


@app.route("/api/tools/ping", methods=["POST"])
def api_tool_ping():
    """
    Execute ping test to an IP or domain.
    """
    data = request.get_json(silent=True) or {}
    host = data.get("host", "").strip()
    if not host:
        return jsonify({"success": False, "error": "Thiếu IP hoặc tên miền"}), 400

    try:
        res = subprocess.run(
            ["ping", "-n", "4", host],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=8.0
        )
        return jsonify({
            "success": True,
            "host": host,
            "output": res.stdout,
            "returncode": res.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Quá thời gian chờ (Timeout)"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/tools/port-scan", methods=["POST"])
def api_tool_port_scan():
    """
    Quick port scan for common services (HTTP, HTTPS, SSH, SMB, RDP, etc.).
    """
    data = request.get_json(silent=True) or {}
    ip = data.get("ip", "").strip()
    if not ip:
        return jsonify({"success": False, "error": "Thiếu địa chỉ IP"}), 400

    common_ports = {
        21: "FTP",
        22: "SSH",
        23: "Telnet",
        53: "DNS",
        80: "HTTP (Web)",
        443: "HTTPS (Web SSL)",
        445: "SMB (Chia sẻ tệp)",
        3389: "RDP (Remote Desktop)",
        5000: "UPnP / Flask",
        8080: "HTTP-Proxy / Alt Web"
    }

    open_ports = []

    def check_port(port, service_name):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.6)
        try:
            if s.connect_ex((ip, port)) == 0:
                open_ports.append({"port": port, "service": service_name})
        except Exception:
            pass
        finally:
            s.close()

    threads = []
    for port, name in common_ports.items():
        t = threading.Thread(target=check_port, args=(port, name))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=1.5)

    return jsonify({
        "success": True,
        "ip": ip,
        "open_ports": sorted(open_ports, key=lambda x: x["port"])
    })


@app.route("/api/wifi-networks")
def api_wifi_networks():
    """
    Returns surrounding Wi-Fi networks and access points with signal in dBm and %.
    """
    networks = net_stats.scan_wifi_access_points()
    return jsonify({
        "success": True,
        "count": len(networks),
        "networks": networks
    })


@app.route("/api/tools/database-scan", methods=["POST"])
def api_tool_database_scan():
    """
    Scan for Database servers (MySQL, PostgreSQL, MongoDB, Redis, MSSQL, Oracle, etc.)
    Can scan a single target IP or all detected online devices.
    """
    data = request.get_json(silent=True) or {}
    target_ip = data.get("ip", "").strip()

    db_ports = {
        3306: "MySQL / MariaDB",
        5432: "PostgreSQL",
        1433: "Microsoft SQL Server (MSSQL)",
        27017: "MongoDB",
        6379: "Redis",
        1521: "Oracle Database",
        9200: "Elasticsearch",
        11211: "Memcached",
        8123: "ClickHouse (HTTP)",
        9000: "ClickHouse / MinIO"
    }

    if target_ip:
        ips_to_scan = [target_ip]
    else:
        # Scan all online detected devices
        devices = scanner.get_all_devices()
        ips_to_scan = [d["ip"] for d in devices if d.get("status") == "online"]
        if not ips_to_scan:
            local_ip, _ = net_stats.get_default_interface_and_ip()
            ips_to_scan = [local_ip]

    found_dbs = []

    def probe_db(ip, port, db_name):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.7)
        try:
            if s.connect_ex((ip, port)) == 0:
                found_dbs.append({
                    "ip": ip,
                    "port": port,
                    "database": db_name
                })
        except Exception:
            pass
        finally:
            s.close()

    threads = []
    for ip in ips_to_scan:
        for port, db_name in db_ports.items():
            t = threading.Thread(target=probe_db, args=(ip, port, db_name))
            threads.append(t)
            t.start()

    for t in threads:
        t.join(timeout=2.0)

    return jsonify({
        "success": True,
        "scanned_ips": ips_to_scan,
        "found_count": len(found_dbs),
        "databases": sorted(found_dbs, key=lambda x: (x["ip"], x["port"]))
    })


@app.route("/api/export/csv")
def api_export_csv():
    """
    Export devices as CSV (like NirSoft Wireless Network Watcher export).
    """
    devices = scanner.get_all_devices()
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "IP Address", "Device Name", "Custom Name", "MAC Address",
        "Network Card Company", "Device Type", "Status", "Ping (ms)",
        "First Detected", "Last Detected", "Detection Count"
    ])

    for d in devices:
        writer.writerow([
            d.get("ip", ""),
            d.get("hostname", ""),
            d.get("custom_name", ""),
            d.get("mac", ""),
            d.get("vendor", ""),
            d.get("device_type", ""),
            d.get("status", ""),
            d.get("latency_ms", ""),
            d.get("first_detected", ""),
            d.get("last_detected", ""),
            d.get("detection_count", 1)
        ])

    csv_data = output.getvalue().encode("utf-8-sig")
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=Network_Devices.csv"}
    )


@app.route("/api/export/json")
def api_export_json():
    """
    Export devices as formatted JSON file.
    """
    devices = scanner.get_all_devices()
    json_data = json.dumps(devices, indent=2, ensure_ascii=False)
    return Response(
        json_data,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=Network_Devices.json"}
    )


if __name__ == "__main__":
    # Start background scanner thread
    start_background_watcher()

    # Trigger initial scan
    scanner.trigger_async_scan()

    print("=" * 60)
    print(" 🚀 WIRELESS NETWORK WATCHER WEB (Trình theo dõi mạng)")
    print(" 🌐 Mở trình duyệt tại: http://localhost:5000 hoặc http://127.0.0.1:5000")
    print("=" * 60)

    # Listen on all interfaces (0.0.0.0) so user can also access from phone on same Wi-Fi
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
