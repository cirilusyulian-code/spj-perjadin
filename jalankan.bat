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

:: Deteksi executable python yang memiliki dependensi flask
set "PY_CMD=python"
python -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Programs\Python\Python37\python.exe" (
        set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python37\python.exe"
    ) else if exist "C:\Python37\python.exe" (
        set "PY_CMD=C:\Python37\python.exe"
    ) else (
        py -3.7 -c "import flask" >nul 2>&1 && set "PY_CMD=py -3.7"
    )
)

:: Buka browser otomatis setelah delay singkat
start "" http://127.0.0.1:5000

:: Jalankan Flask server menggunakan Python
"%PY_CMD%" app.py

pause

