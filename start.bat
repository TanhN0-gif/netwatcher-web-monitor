@echo off
title NetWatcher Web - Wireless Network Watcher
chcp 65001 >nul
cls

echo =====================================================================
echo    🚀 NETWATCHER WEB - TRÌNH THEO DÕI THIẾT BỊ VÀ THÔNG SỐ MẠNG
echo =====================================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [!] Không tìm thấy môi trường ảo .venv. Đang tạo mới...
    python -m venv .venv
    echo [*] Đang cài đặt thư viện cần thiết...
    .venv\Scripts\pip.exe install -r requirements.txt
)

echo [*] Đang khởi động Server NetWatcher trên cổng 5000...
echo [*] Mở trình duyệt tại: http://localhost:5000
echo.

:: Tự động mở trình duyệt sau 1.5 giây
start "" http://localhost:5000

:: Chạy ứng dụng Python
.venv\Scripts\python.exe app.py

pause
