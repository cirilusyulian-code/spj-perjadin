@echo off
title e-SPJ Dinas v2.0 - Server Perjalanan Dinas
cd /d "%~dp0"

echo ========================================================
echo       APLIKASI e-SPJ DINAS v2.0 - LOCAL SERVICE
echo ========================================================
echo.
echo Sedang memeriksa dan menjalankan aplikasi...
echo.
echo Alamat Lokal : http://127.0.0.1:5000
echo Akun Login   : admin / admin123
echo.
echo (Jendela ini jangan ditutup selama menggunakan aplikasi)
echo Tekan CTRL + C untuk menghentikan server.
echo ========================================================
echo.

:: Buka browser otomatis setelah delay singkat
start "" http://127.0.0.1:5000

:: Jalankan Flask server menggunakan Python
python app.py

pause

