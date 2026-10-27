# 🌐 NetWatcher Web - Wireless Network Watcher trên Nền Web

**NetWatcher Web** là công cụ theo dõi thông số mạng và quét toàn bộ thiết bị đang kết nối Wi-Fi/LAN trong mạng nội bộ, hoạt động trực tiếp trên trình duyệt web tại `http://localhost:5000` (tương tự như phần mềm nổi tiếng **Wireless Network Watcher** của NirSoft nhưng có giao diện hiện đại, biểu đồ băng thông thời gian thực và nhiều tính năng nâng cao).

---

## ✨ Các Tính Năng Nổi Bật

### 1. 📡 Quét & Giám Sát Thiết Bị Mạng (Giống Wireless Network Watcher)
- **Tốc độ cực nhanh**: Sử dụng trực tiếp Windows API nguyên bản `SendARP` và bảng định tuyến ARP Cache của Windows.
- **Thông tin chi tiết từng thiết bị**:
  - Địa chỉ IP (với huy hiệu nhận diện Máy tính hiện tại và Router/Gateway).
  - Địa chỉ MAC vật lý.
  - Tên thiết bị (Hostname qua DNS/NetBIOS) & **khả năng tự đổi tên tùy ý** (ví dụ: "iPhone của tôi", "Smart TV").
  - Hãng sản xuất card mạng (Vendor) với kho dữ liệu OUI tích hợp sẵn (Apple, Samsung, Intel, Xiaomi, TP-Link, MikroTik, ASUS, v.v.).
  - **Nhận diện địa chỉ MAC ngẫu nhiên (Randomized MAC)** trên iOS và Android đời mới (Private Wi-Fi Address).
  - Trạng thái trực tuyến (🟢 Online / ⚪ Offline).
  - Độ trễ Ping (ms) từng thiết bị.
  - Thời điểm phát hiện lần đầu & lần cuối cùng xuất hiện.
- **Chuông báo âm thanh 🔔**: Khi có bất kỳ thiết bị mới nào vừa kết nối vào Wi-Fi, hệ thống sẽ phát âm thanh báo động và hiển thị thông báo.
- **Tự động quét định kỳ**: Cấu hình tự động quét lại mạng mỗi 10 giây, 30 giây hoặc 60 giây.
- **Xuất báo cáo**: Xuất danh sách thiết bị ra file CSV hoặc JSON chỉ với 1 click.

### 2. 📊 Theo Dõi Thông Số Mạng & Biểu Đồ Băng Thông
- **Thông số Wi-Fi chi tiết**:
  - Tên mạng Wi-Fi (SSID), BSSID (Địa chỉ MAC điểm phát sóng).
  - Cường độ tín hiệu Wi-Fi (%) & mức RSSI (dBm).
  - Chuẩn mạng Wi-Fi (802.11ax Wi-Fi 6, 802.11ac, v.v.).
  - Băng tần (2.4 GHz / 5 GHz) & số kênh phát sóng (Channel).
  - Tốc độ liên kết card mạng (Receive & Transmit Rate - Mbps).
- **Biểu đồ băng thông thời gian thực (Live Bandwidth Chart)**:
  - Tốc độ Tải xuống (Download) và Tải lên (Upload) cập nhật mỗi giây.
  - Tổng dung lượng mạng đã nhận và đã gửi kể từ khi mở máy.
- **Thông số IP & Card mạng**:
  - IPv4 cục bộ, Subnet Mask, Default Gateway (Router), DNS Server.
  - Danh sách tất cả các Card mạng trên máy (Wi-Fi, Ethernet, VMware, VPN...).

### 3. 🛠️ Bộ Công Cụ Mạng Tiện Ích Tích Hợp
- **Công cụ Ping (Interactive Ping)**: Kiểm tra chất lượng kết nối và độ trễ tới bất kỳ IP hoặc website nào (ví dụ `10.12.0.1`, `8.8.8.8`).
- **Quét cổng dịch vụ (Port Scanner)**: Kiểm tra nhanh các cổng phổ biến đang mở trên thiết bị (HTTP 80, HTTPS 443, SSH 22, SMB 445, RDP 3389, v.v.).

---

## 🚀 Hướng Dẫn Sử Dụng Nhanh

### Cách 1: Khởi động bằng 1-Click (Khuyên dùng trên Windows)
Chỉ cần nhấp đúp chuột vào file:
```
start.bat
```
File này sẽ tự động khởi động server và mở trình duyệt web tại `http://localhost:5000`.

### Cách 2: Khởi động bằng lệnh Terminal / PowerShell
1. Mở PowerShell hoặc Command Prompt tại thư mục dự án:
```powershell
cd C:\Users\hi\.gemini\antigravity\scratch\network-watcher-web
```
2. Chạy ứng dụng bằng Python trong môi trường ảo:
```powershell
.venv\Scripts\python.exe app.py
```
3. Truy cập vào trình duyệt web tại:
```
http://localhost:5000
```
*(Bạn cũng có thể mở từ điện thoại kết nối cùng mạng Wi-Fi bằng địa chỉ IP máy tính, ví dụ: `http://10.12.8.83:5000`)*.
