#!/usr/bin/env bash
# ==============================================================================
# SCRIPT DEPLOYMENT OTOMATIS: e-SPJ PERJALANAN DINAS UNTUK UBUNTU VPS
# ==============================================================================
set -e

APP_DIR="/var/www/spj-perjadin"
SERVICE_NAME="spj-perjadin"
PORT="5000"

echo "=========================================================="
echo "🚀 Memulai Setup e-SPJ Perjalanan Dinas di Ubuntu VPS..."
echo "=========================================================="

# 1. Update sistem & instal paket dasar
echo "📦 Menginstall dependensi sistem..."
sudo apt update -y
sudo apt install -y python3 python3-pip python3-venv nginx git ufw curl

# 2. Buat direktori aplikasi jika belum ada
if [ ! -d "$APP_DIR" ]; then
    echo "📁 Membuat folder aplikasi di $APP_DIR..."
    sudo mkdir -p "$APP_DIR"
    sudo chown -R $USER:$USER "$APP_DIR"
fi

# 3. Setup Virtual Environment Python
echo "🐍 Membuat Python Virtual Environment..."
cd "$APP_DIR"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 4. Install dependencies
echo "📥 Menginstall pustaka python dari requirements.txt..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 5. Inisialisasi Database
echo "🗄️ Menginisialisasi database SQLite..."
./venv/bin/python3 -c "from database import init_db, create_sample_data; init_db(); create_sample_data(); print('DB Ready!')"

# 6. Buat Systemd Service Unit
echo "⚙️ Membuat systemd service ($SERVICE_NAME)..."
sudo bash -c "cat > /etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Gunicorn instance to serve e-SPJ Perjalanan Dinas
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=${APP_DIR}
Environment="PATH=${APP_DIR}/venv/bin"
ExecStart=${APP_DIR}/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:${PORT} app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload & start systemd service
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl restart ${SERVICE_NAME}

# 7. Konfigurasi Nginx Reverse Proxy
echo "🌐 Mengkonfigurasi Nginx Reverse Proxy..."
sudo bash -c "cat > /etc/nginx/sites-available/spj-perjadin" <<EOF
server {
    listen 80;
    server_name _;

    client_max_body_size 20M;

    location /static/ {
        alias ${APP_DIR}/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:${PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Aktifkan konfigurasi Nginx
sudo ln -sf /etc/nginx/sites-available/spj-perjadin /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# 8. Firewall setup (UFW)
echo "🛡️ Membuka port Nginx di Firewall..."
sudo ufw allow 'Nginx Full' || true

# Info Selesai
PUBLIC_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')
echo ""
echo "=========================================================="
echo "🎉 DEPLOYMENT BERHASIL!"
echo "=========================================================="
echo "Aplikasi SPJ Perjalanan Dinas sekarang aktif di:"
echo "👉 http://${PUBLIC_IP}"
echo ""
echo "Akun Default:"
echo "Username : admin"
echo "Password : admin123"
echo ""
echo "Untuk mengecek status service:"
echo "sudo systemctl status ${SERVICE_NAME}"
echo "=========================================================="
