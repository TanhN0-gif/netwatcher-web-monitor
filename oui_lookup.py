"""
OUI Lookup Module - Network Card / Hardware Vendor Identification
Supports an extensive offline database of common vendors,
randomized MAC address detection (iOS/Android private addresses),
and smart online caching.
"""

import json
import os
import re
import urllib.request
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CACHE_FILE = os.path.join(DATA_DIR, "vendor_cache.json")

# Top major manufacturers and OUI prefixes (expandable)
EMBEDDED_OUI = {
    # Apple
    "00:03:93": "Apple, Inc.", "00:05:02": "Apple, Inc.", "00:0A:27": "Apple, Inc.",
    "00:0A:95": "Apple, Inc.", "00:0D:93": "Apple, Inc.", "00:10:FA": "Apple, Inc.",
    "00:11:24": "Apple, Inc.", "00:14:51": "Apple, Inc.", "00:16:CB": "Apple, Inc.",
    "00:17:F2": "Apple, Inc.", "00:19:E3": "Apple, Inc.", "00:1B:63": "Apple, Inc.",
    "00:1C:B3": "Apple, Inc.", "00:1D:4F": "Apple, Inc.", "00:1E:52": "Apple, Inc.",
    "00:1E:C2": "Apple, Inc.", "00:1F:5B": "Apple, Inc.", "00:1F:F3": "Apple, Inc.",
    "00:21:E9": "Apple, Inc.", "00:22:41": "Apple, Inc.", "00:23:12": "Apple, Inc.",
    "00:23:32": "Apple, Inc.", "00:23:6C": "Apple, Inc.", "00:23:DF": "Apple, Inc.",
    "00:24:36": "Apple, Inc.", "00:25:00": "Apple, Inc.", "00:25:4B": "Apple, Inc.",
    "00:25:BC": "Apple, Inc.", "00:26:08": "Apple, Inc.", "00:26:4A": "Apple, Inc.",
    "00:26:B0": "Apple, Inc.", "00:26:BB": "Apple, Inc.", "04:0C:CE": "Apple, Inc.",
    "04:15:52": "Apple, Inc.", "04:26:65": "Apple, Inc.", "04:48:9A": "Apple, Inc.",
    "04:54:53": "Apple, Inc.", "04:DB:56": "Apple, Inc.", "04:E5:36": "Apple, Inc.",
    "08:66:98": "Apple, Inc.", "0C:15:39": "Apple, Inc.", "10:1C:0C": "Apple, Inc.",
    "14:10:9F": "Apple, Inc.", "14:20:5E": "Apple, Inc.", "18:65:90": "Apple, Inc.",
    "18:AF:61": "Apple, Inc.", "20:A2:E4": "Apple, Inc.", "24:F0:94": "Apple, Inc.",
    "28:0B:5C": "Apple, Inc.", "28:CF:E9": "Apple, Inc.", "2C:BE:08": "Apple, Inc.",
    "30:07:4D": "Apple, Inc.", "34:36:3B": "Apple, Inc.", "38:CA:DA": "Apple, Inc.",
    "3C:07:54": "Apple, Inc.", "40:6C:8F": "Apple, Inc.", "48:D7:05": "Apple, Inc.",
    "50:BC:96": "Apple, Inc.", "54:4E:90": "Apple, Inc.", "58:55:CA": "Apple, Inc.",
    "60:F4:45": "Apple, Inc.", "64:B0:A6": "Apple, Inc.", "68:96:7B": "Apple, Inc.",
    "70:11:24": "Apple, Inc.", "78:7B:8A": "Apple, Inc.", "7C:04:D0": "Apple, Inc.",
    "80:49:71": "Apple, Inc.", "84:FC:AC": "Apple, Inc.", "88:66:5A": "Apple, Inc.",
    "8C:85:90": "Apple, Inc.", "90:72:40": "Apple, Inc.", "94:E9:79": "Apple, Inc.",
    "98:01:A7": "Apple, Inc.", "9C:20:7B": "Apple, Inc.", "A4:83:E7": "Apple, Inc.",
    "A8:66:7F": "Apple, Inc.", "AC:BC:32": "Apple, Inc.", "B0:34:95": "Apple, Inc.",
    "B4:F0:AB": "Apple, Inc.", "B8:78:26": "Apple, Inc.", "BC:D1:1F": "Apple, Inc.",
    "C0:CC:F8": "Apple, Inc.", "C4:B3:01": "Apple, Inc.", "C8:3C:85": "Apple, Inc.",
    "CC:08:8D": "Apple, Inc.", "D0:25:98": "Apple, Inc.", "D4:61:9D": "Apple, Inc.",
    "D8:96:95": "Apple, Inc.", "DC:2B:61": "Apple, Inc.", "E0:B6:55": "Apple, Inc.",
    "E4:CE:8F": "Apple, Inc.", "E8:80:2E": "Apple, Inc.", "EC:35:86": "Apple, Inc.",
    "F0:18:98": "Apple, Inc.", "F4:0F:24": "Apple, Inc.", "F8:62:14": "Apple, Inc.",

    # Samsung Electronics
    "00:07:AB": "Samsung Electronics", "00:12:47": "Samsung Electronics", "00:15:99": "Samsung Electronics",
    "00:16:32": "Samsung Electronics", "00:17:C9": "Samsung Electronics", "00:1A:8A": "Samsung Electronics",
    "00:1D:25": "Samsung Electronics", "00:21:19": "Samsung Electronics", "00:23:D7": "Samsung Electronics",
    "00:24:54": "Samsung Electronics", "00:26:37": "Samsung Electronics", "08:37:3D": "Samsung Electronics",
    "0C:14:20": "Samsung Electronics", "10:30:47": "Samsung Electronics", "14:49:E0": "Samsung Electronics",
    "18:22:7E": "Samsung Electronics", "1C:5A:3E": "Samsung Electronics", "20:55:31": "Samsung Electronics",
    "24:4B:81": "Samsung Electronics", "28:BA:B5": "Samsung Electronics", "30:07:4D": "Samsung Electronics",
    "34:23:BA": "Samsung Electronics", "38:0B:40": "Samsung Electronics", "3C:62:00": "Samsung Electronics",
    "40:40:A7": "Samsung Electronics", "44:F4:59": "Samsung Electronics", "48:44:F7": "Samsung Electronics",
    "4C:63:71": "Samsung Electronics", "50:01:D9": "Samsung Electronics", "54:92:BE": "Samsung Electronics",
    "5C:0A:5B": "Samsung Electronics", "60:6C:66": "Samsung Electronics", "64:1C:AE": "Samsung Electronics",
    "68:EB:AE": "Samsung Electronics", "70:2C:1F": "Samsung Electronics", "78:4B:87": "Samsung Electronics",
    "7C:F8:51": "Samsung Electronics", "84:25:DB": "Samsung Electronics", "88:32:9B": "Samsung Electronics",
    "8C:77:12": "Samsung Electronics", "90:18:7C": "Samsung Electronics", "94:35:0A": "Samsung Electronics",
    "98:1D:FA": "Samsung Electronics", "A0:0B:BA": "Samsung Electronics", "A8:7C:01": "Samsung Electronics",
    "B0:47:BF": "Samsung Electronics", "B8:5A:73": "Samsung Electronics", "BC:44:86": "Samsung Electronics",
    "C0:BD:D1": "Samsung Electronics", "C4:42:02": "Samsung Electronics", "C8:19:F7": "Samsung Electronics",
    "CC:07:AB": "Samsung Electronics", "D4:E6:B7": "Samsung Electronics", "DC:71:44": "Samsung Electronics",
    "E4:E0:C5": "Samsung Electronics", "EC:1F:72": "Samsung Electronics", "F4:7B:5E": "Samsung Electronics",

    # Intel
    "00:02:B3": "Intel Corporate", "00:03:47": "Intel Corporate", "00:04:23": "Intel Corporate",
    "00:0C:F1": "Intel Corporate", "00:0E:0C": "Intel Corporate", "00:13:02": "Intel Corporate",
    "00:13:E8": "Intel Corporate", "00:15:00": "Intel Corporate", "00:16:76": "Intel Corporate",
    "00:19:D1": "Intel Corporate", "00:1B:21": "Intel Corporate", "00:1C:C0": "Intel Corporate",
    "00:1E:67": "Intel Corporate", "00:21:6A": "Intel Corporate", "00:22:FB": "Intel Corporate",
    "00:23:14": "Intel Corporate", "00:24:D7": "Intel Corporate", "00:27:0E": "Intel Corporate",
    "08:11:96": "Intel Corporate", "24:77:03": "Intel Corporate", "34:13:E8": "Intel Corporate",
    "3C:FD:FE": "Intel Corporate", "40:A8:F0": "Intel Corporate", "48:51:B7": "Intel Corporate",
    "4C:79:BA": "Intel Corporate", "5C:87:9C": "Intel Corporate", "68:05:CA": "Intel Corporate",
    "70:77:81": "Intel Corporate", "78:2B:CB": "Intel Corporate", "84:A9:3E": "Intel Corporate",
    "88:AE:DD": "Intel Corporate", "8C:8D:28": "Intel Corporate", "94:65:9C": "Intel Corporate",
    "9C:B6:54": "Intel Corporate", "A4:4C:C8": "Intel Corporate", "B4:96:91": "Intel Corporate",
    "C8:F7:50": "Intel Corporate", "DC:53:60": "Intel Corporate", "E8:F4:08": "Intel Corporate",
    "F4:6D:04": "Intel Corporate",

    # Xiaomi / POCO / Redmi
    "00:9E:C8": "Xiaomi Communications", "04:CF:8C": "Xiaomi Communications", "10:2A:B3": "Xiaomi Communications",
    "18:59:36": "Xiaomi Communications", "20:34:FB": "Xiaomi Communications", "28:6C:07": "Xiaomi Communications",
    "34:80:B3": "Xiaomi Communications", "38:A4:ED": "Xiaomi Communications", "44:23:7C": "Xiaomi Communications",
    "50:64:2B": "Xiaomi Communications", "58:44:98": "Xiaomi Communications", "5C:E9:1E": "Xiaomi Communications",
    "64:09:80": "Xiaomi Communications", "64:57:25": "Xiaomi Communications", "74:51:BA": "Xiaomi Communications",
    "78:11:DC": "Xiaomi Communications", "7C:49:EB": "Xiaomi Communications", "84:F3:EB": "Xiaomi Communications",
    "8C:BE:BE": "Xiaomi Communications", "94:87:E0": "Xiaomi Communications", "98:FA:E3": "Xiaomi Communications",
    "A4:77:33": "Xiaomi Communications", "AC:C1:EE": "Xiaomi Communications", "B0:E2:35": "Xiaomi Communications",
    "C4:0B:CB": "Xiaomi Communications", "D4:97:0B": "Xiaomi Communications", "E4:AA:EC": "Xiaomi Communications",
    "F0:18:98": "Xiaomi Communications", "F8:A4:5F": "Xiaomi Communications",

    # TP-Link
    "00:1D:0F": "TP-Link Technologies", "00:23:CD": "TP-Link Technologies", "00:25:86": "TP-Link Technologies",
    "14:CC:20": "TP-Link Technologies", "18:A6:F7": "TP-Link Technologies", "20:DC:E6": "TP-Link Technologies",
    "30:B5:C2": "TP-Link Technologies", "40:A5:EF": "TP-Link Technologies", "50:C7:BF": "TP-Link Technologies",
    "54:C8:0F": "TP-Link Technologies", "60:32:B1": "TP-Link Technologies", "70:4F:57": "TP-Link Technologies",
    "84:16:F9": "TP-Link Technologies", "90:F6:52": "TP-Link Technologies", "98:48:27": "TP-Link Technologies",
    "A0:F3:C1": "TP-Link Technologies", "B0:95:75": "TP-Link Technologies", "C0:25:E9": "TP-Link Technologies",
    "C4:6E:1F": "TP-Link Technologies", "D8:07:B6": "TP-Link Technologies", "E4:C3:2A": "TP-Link Technologies",
    "E8:48:B8": "TP-Link Technologies", "EC:08:6B": "TP-Link Technologies", "F4:EC:38": "TP-Link Technologies",

    # Huawei Technologies
    "00:18:82": "Huawei Technologies", "00:1E:10": "Huawei Technologies", "00:25:9E": "Huawei Technologies",
    "04:02:1F": "Huawei Technologies", "08:19:A6": "Huawei Technologies", "10:1B:54": "Huawei Technologies",
    "10:C6:1F": "Huawei Technologies", "24:69:A5": "Huawei Technologies", "38:4C:90": "Huawei Technologies",
    "40:CB:A8": "Huawei Technologies", "48:46:FB": "Huawei Technologies", "54:89:98": "Huawei Technologies",
    "60:DE:44": "Huawei Technologies", "70:54:F5": "Huawei Technologies", "88:28:B3": "Huawei Technologies",
    "90:17:AC": "Huawei Technologies", "AC:E2:15": "Huawei Technologies", "C4:07:2F": "Huawei Technologies",
    "D8:49:0B": "Huawei Technologies", "E4:68:A3": "Huawei Technologies", "F4:55:9C": "Huawei Technologies",

    # MikroTik / Routerboard
    "00:0C:42": "MikroTik (RouterBOARD)", "08:55:31": "MikroTik", "18:FD:74": "MikroTik",
    "2C:C8:1B": "MikroTik", "48:8F:5A": "MikroTik", "64:D1:54": "MikroTik", "74:4D:28": "MikroTik",
    "B8:69:F4": "MikroTik", "C4:AD:34": "MikroTik", "CC:2D:E0": "MikroTik", "D4:01:C3": "MikroTik",
    "E4:8D:8C": "MikroTik",

    # Espressif (ESP8266, ESP32 IoT)
    "18:FE:34": "Espressif Systems (ESP IoT)", "24:0A:C4": "Espressif Systems (ESP IoT)",
    "24:62:AB": "Espressif Systems (ESP IoT)", "24:6F:28": "Espressif Systems (ESP IoT)",
    "24:B2:DE": "Espressif Systems (ESP IoT)", "2C:F4:32": "Espressif Systems (ESP IoT)",
    "30:AE:A4": "Espressif Systems (ESP IoT)", "3C:61:05": "Espressif Systems (ESP IoT)",
    "3C:71:BF": "Espressif Systems (ESP IoT)", "4C:11:AE": "Espressif Systems (ESP IoT)",
    "4C:75:25": "Espressif Systems (ESP IoT)", "54:5A:A6": "Espressif Systems (ESP IoT)",
    "5C:CF:7F": "Espressif Systems (ESP IoT)", "60:01:94": "Espressif Systems (ESP IoT)",
    "68:C6:3A": "Espressif Systems (ESP IoT)", "70:03:9F": "Espressif Systems (ESP IoT)",
    "84:0D:8E": "Espressif Systems (ESP IoT)", "84:CC:A8": "Espressif Systems (ESP IoT)",
    "84:F3:EB": "Espressif Systems (ESP IoT)", "90:97:D5": "Espressif Systems (ESP IoT)",
    "A0:20:A6": "Espressif Systems (ESP IoT)", "A4:7B:9D": "Espressif Systems (ESP IoT)",
    "A4:CF:12": "Espressif Systems (ESP IoT)", "AC:67:B2": "Espressif Systems (ESP IoT)",
    "B4:E6:2D": "Espressif Systems (ESP IoT)", "BC:DD:C2": "Espressif Systems (ESP IoT)",
    "C4:4F:33": "Espressif Systems (ESP IoT)", "CC:50:E3": "Espressif Systems (ESP IoT)",
    "D8:A0:1D": "Espressif Systems (ESP IoT)", "DC:4F:22": "Espressif Systems (ESP IoT)",

    # Cisco Systems
    "00:00:0C": "Cisco Systems", "00:01:42": "Cisco Systems", "00:01:63": "Cisco Systems",
    "00:02:16": "Cisco Systems", "00:05:31": "Cisco Systems", "00:0C:85": "Cisco Systems",
    "00:11:20": "Cisco Systems", "00:1D:70": "Cisco Systems", "00:22:55": "Cisco Systems",
    "00:26:0B": "Cisco Systems", "28:52:61": "Cisco Systems", "70:81:05": "Cisco Systems",

    # Google
    "00:1A:11": "Google, Inc.", "3C:5A:37": "Google, Inc.", "54:60:09": "Google, Inc.",
    "70:3E:AC": "Google, Inc.", "94:EB:CD": "Google, Inc.", "A4:77:33": "Google, Inc.",
    "D8:6C:63": "Google, Inc.", "F8:8F:CA": "Google, Inc.",

    # Amazon
    "00:FC:8B": "Amazon Technologies", "0C:47:C9": "Amazon Technologies", "18:74:2E": "Amazon Technologies",
    "38:F7:3D": "Amazon Technologies", "44:65:0D": "Amazon Technologies", "50:F5:DA": "Amazon Technologies",
    "68:54:FD": "Amazon Technologies", "74:C2:46": "Amazon Technologies", "84:D6:D0": "Amazon Technologies",
    "AC:63:BE": "Amazon Technologies", "F0:27:2D": "Amazon Technologies",

    # Dell
    "00:06:5B": "Dell Inc.", "00:0B:DB": "Dell Inc.", "00:11:43": "Dell Inc.", "00:14:22": "Dell Inc.",
    "00:18:8B": "Dell Inc.", "00:1A:A0": "Dell Inc.", "14:FE:B5": "Dell Inc.", "18:03:73": "Dell Inc.",
    "24:B6:FD": "Dell Inc.", "44:A8:42": "Dell Inc.", "74:86:7A": "Dell Inc.", "98:90:96": "Dell Inc.",
    "B8:2A:72": "Dell Inc.", "D4:BE:D9": "Dell Inc.", "E4:F0:04": "Dell Inc.",

    # HP / Hewlett Packard
    "00:01:E6": "Hewlett Packard", "00:08:02": "Hewlett Packard", "00:0E:7F": "Hewlett Packard",
    "00:17:A4": "Hewlett Packard", "00:1E:0B": "Hewlett Packard", "00:21:5A": "Hewlett Packard",
    "10:1F:74": "Hewlett Packard", "30:8D:99": "Hewlett Packard", "3C:D9:2B": "Hewlett Packard",
    "70:5A:0F": "Hewlett Packard", "94:57:A5": "Hewlett Packard", "B4:99:BA": "Hewlett Packard",

    # Lenovo
    "00:21:CC": "Lenovo Mobile", "04:76:6E": "Lenovo", "18:66:DA": "Lenovo", "20:76:93": "Lenovo",
    "30:52:CB": "Lenovo", "54:EE:75": "Lenovo", "70:72:0D": "Lenovo", "80:FA:5B": "Lenovo",
    "A4:4E:31": "Lenovo", "AC:38:70": "Lenovo", "E8:6A:64": "Lenovo",

    # ASUS
    "00:0C:6E": "ASUSTek Computer", "00:11:D8": "ASUSTek Computer", "00:15:F2": "ASUSTek Computer",
    "00:1E:8C": "ASUSTek Computer", "04:D9:F5": "ASUSTek Computer", "10:BF:48": "ASUSTek Computer",
    "1C:87:2C": "ASUSTek Computer", "2C:4D:54": "ASUSTek Computer", "38:D5:47": "ASUSTek Computer",
    "50:46:5D": "ASUSTek Computer", "60:45:CB": "ASUSTek Computer", "70:8B:CD": "ASUSTek Computer",
    "AC:9E:17": "ASUSTek Computer", "BC:EE:7B": "ASUSTek Computer", "F0:2F:74": "ASUSTek Computer",

    # Acer
    "00:01:24": "Acer Incorporated", "00:03:7F": "Acer Incorporated", "00:60:67": "Acer Incorporated",
    "00:A0:60": "Acer Incorporated", "20:6A:8A": "Acer Incorporated", "40:61:86": "Acer Incorporated",
    "60:EB:69": "Acer Incorporated", "74:E5:43": "Acer Incorporated", "88:25:2C": "Acer Incorporated",

    # Realtek
    "00:07:0E": "Realtek Semiconductor", "00:10:22": "Realtek Semiconductor", "00:E0:4C": "Realtek Semiconductor",
    "20:76:93": "Realtek Semiconductor", "52:54:4C": "Realtek Semiconductor", "B4:B5:2F": "Realtek Semiconductor",

    # VMware / VirtualBox / Hyper-V
    "00:05:69": "VMware, Inc.", "00:0C:29": "VMware, Inc.", "00:1C:14": "VMware, Inc.",
    "00:50:56": "VMware, Inc.", "08:00:27": "PCS Systemtechnik (VirtualBox)", "00:15:5D": "Microsoft Hyper-V",

    # Ubiquiti
    "00:15:6D": "Ubiquiti Networks", "00:27:22": "Ubiquiti Networks", "24:A4:3C": "Ubiquiti Networks",
    "68:D7:9A": "Ubiquiti Networks", "78:8A:20": "Ubiquiti Networks", "80:2A:A8": "Ubiquiti Networks",
    "AC:8B:A9": "Ubiquiti Networks", "B4:FB:E4": "Ubiquiti Networks", "DC:9F:DB": "Ubiquiti Networks",
    "F0:9F:C2": "Ubiquiti Networks",

    # D-Link
    "00:05:5D": "D-Link Corporation", "00:0D:88": "D-Link Corporation", "00:15:E9": "D-Link Corporation",
    "00:1E:58": "D-Link Corporation", "14:D6:4D": "D-Link Corporation", "28:10:7B": "D-Link Corporation",
    "78:54:2E": "D-Link Corporation", "90:94:E4": "D-Link Corporation", "B8:A3:86": "D-Link Corporation",

    # Netgear
    "00:09:5B": "Netgear", "00:0F:B5": "Netgear", "00:14:6C": "Netgear", "00:1E:2A": "Netgear",
    "20:4E:7F": "Netgear", "2C:B0:5D": "Netgear", "44:94:FC": "Netgear", "A0:04:60": "Netgear",
    "C0:FF:D4": "Netgear", "E0:46:9A": "Netgear",

    # Sony / PlayStation
    "00:01:4A": "Sony Corporation", "00:04:1F": "Sony Interactive Entertainment", "00:13:A9": "Sony Corporation",
    "00:15:C1": "Sony Corporation", "00:1D:BA": "Sony Interactive Entertainment", "00:1F:A7": "Sony Corporation",
    "00:24:8D": "Sony Interactive Entertainment", "70:9E:29": "Sony Interactive Entertainment",

    # Nintendo
    "00:09:BF": "Nintendo Co., Ltd.", "00:17:AB": "Nintendo Co., Ltd.", "00:19:1D": "Nintendo Co., Ltd.",
    "00:1B:7A": "Nintendo Co., Ltd.", "00:1E:35": "Nintendo Co., Ltd.", "00:21:47": "Nintendo Co., Ltd.",
    "00:24:44": "Nintendo Co., Ltd.", "34:AF:2C": "Nintendo Co., Ltd.", "7C:BB:8A": "Nintendo Co., Ltd.",
    "98:B6:E9": "Nintendo Co., Ltd.", "B8:AE:6E": "Nintendo Co., Ltd.", "DC:68:EB": "Nintendo Co., Ltd.",

    # LG Electronics
    "00:05:F9": "LG Electronics", "00:1C:62": "LG Electronics", "10:F9:6F": "LG Electronics",
    "20:3D:66": "LG Electronics", "34:FC:EF": "LG Electronics", "58:A2:B5": "LG Electronics",
    "74:A7:22": "LG Electronics", "98:93:CC": "LG Electronics", "A8:23:FE": "LG Electronics",

    # OnePlus / Oppo / Vivo (BBK Electronics)
    "94:65:2D": "OnePlus Technology", "54:B1:21": "OnePlus Technology", "48:2C:A0": "OnePlus Technology",
    "40:4E:34": "OnePlus Technology", "88:C9:B3": "OPPO / Realme", "A0:C9:A0": "OPPO / Realme",
    "CC:F3:5C": "Vivo Mobile", "24:DF:6A": "Vivo Mobile", "E0:76:D0": "Vivo Mobile",
}

# Cache for resolved vendors
_vendor_cache = {}


def _load_cache():
    global _vendor_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _vendor_cache = json.load(f)
        except Exception:
            _vendor_cache = {}


def _save_cache():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_vendor_cache, f, indent=2)
    except Exception:
        pass


_load_cache()


def is_randomized_mac(mac: str) -> bool:
    """
    Check if the MAC address has the 'Locally Administered' bit set.
    Modern iOS, Android, and Windows 10/11 use randomized MACs on Wi-Fi
    where the second hex digit is 2, 6, A, or E.
    e.g., DA:57:C7:22:3D:94 (second digit is A -> Randomized)
          92:8E:FB:57:A3:59 (second digit is 2 -> Randomized)
    """
    clean = mac.replace(":", "").replace("-", "").upper()
    if len(clean) >= 2:
        second_nibble = clean[1]
        return second_nibble in ("2", "6", "A", "E")
    return False


def get_mac_vendor(mac: str) -> str:
    """
    Look up the hardware manufacturer from a MAC address.
    """
    if not mac or mac == "FF:FF:FF:FF:FF:FF":
        return "Broadcast"

    # Normalize MAC
    clean = re.sub(r"[^0-9A-Fa-f]", "", mac).upper()
    if len(clean) < 6:
        return "Unknown"

    prefix = f"{clean[0:2]}:{clean[2:4]}:{clean[4:6]}"

    # 1. Check embedded OUI database
    if prefix in EMBEDDED_OUI:
        return EMBEDDED_OUI[prefix]

    # 2. Check local disk cache
    if prefix in _vendor_cache:
        return _vendor_cache[prefix]

    # 3. Check if randomized (Private MAC address)
    if is_randomized_mac(mac):
        vendor = "Thiết bị di động (Địa chỉ MAC riêng tư / Randomized)"
        _vendor_cache[prefix] = vendor
        _save_cache()
        return vendor

    # 4. Fallback online lookup
    try:
        url = f"https://api.macvendors.com/{prefix}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=2.0) as res:
            vendor = res.read().decode("utf-8", errors="ignore").strip()
            if vendor and "error" not in vendor.lower() and len(vendor) < 100:
                _vendor_cache[prefix] = vendor
                _save_cache()
                return vendor
    except Exception:
        pass

    return "Không rõ hãng (Unknown)"
