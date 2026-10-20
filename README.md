# Aplikasi e-SPJ Perjalanan Dinas Daerah

Sistem aplikasi web lengkap untuk pembuatan, pengelolaan, dan pencetakan dokumen pertanggungjawaban (SPJ) perjalanan dinas pemerintahan daerah sesuai standar Permendagri & PMK.

---

## 🌟 Fitur Utama

1. **Autentikasi & Keamanan:**
   - Halaman Login modern dan aman.
   - User default: `admin` / `admin123`.

2. **Formulir Input SPJ Terpadu:**
   - Kota / Daerah Tujuan & Instansi yang dituju.
   - Maksud dan keperluan perjalanan dinas.
   - **Multi-Pelaksana:** Input dinamis nama-nama pegawai yang melakukan perjalanan dinas (Nama, NIP, Pangkat/Golongan, Jabatan).
   - Tanggal berangkat dan tanggal pulang (otomatis hitung lama hari / durasi).
   - **Rincian Biaya Fleksibel & Terkalkulasi Otomatis:**
     - Biaya Harian (Uang Harian x hari).
     - Biaya Additional: Taksi bandara/stasiun, transportasi lokal, hotel/penginapan, tiket pesawat atau tiket kapal.
     - Penandaan khusus (*checkbox*) untuk pos yang masuk ke Daftar Pengeluaran Riil.
     - Otomatis kalkulasi Total Biaya & Terbilang Bahasa Indonesia.

3. **Manajemen Pengaturan Template Dokumen:**
   - **Template SPT 2 Tipe:**
     - **Tipe 1:** SPT untuk Kepala Dinas (berdasarkan disposisi pimpinan daerah).
     - **Tipe 2:** SPT untuk Staf / Pejabat di bawah Kadis (ditandatangani oleh Kepala Dinas).
   - **Template 4 Dokumen Pendukung Lainnya:**
     - **Pengeluaran Riil:** Pernyataan Tanggung Jawab Mutlak (SPTJM) bermaterai.
     - **Kwitansi Pembayaran:** Tanda terima 3 tanda tangan (PPK, Bendahara Pengeluaran, Pelaksana).
     - **Rincian Biaya:** Tabel perincian biaya lengkap dengan dasar perhitungan SBM.
     - **Laporan Perjalanan Dinas:** Sistematika bab pelaporan kedinasan (I. Dasar, II. Maksud, III. Waktu & Tempat, IV. Kegiatan, V. Hasil, VI. Kesimpulan/Saran).
   - **Kop Surat & Pejabat:**
     - Nama Instansi Induk, Nama Dinas, Alamat, Kontak, Logo & Garis ganda resmi.
     - Data lengkap Kepala Dinas, PPK, dan Bendahara Pengeluaran.

4. **Siap Cetak & Export PDF:**
   - Tombol cetak per lembar dokumen.
   - Tombol **"Cetak 1 Bundel Lengkap"** untuk mencetak seluruh 5 dokumen sekaligus dengan page-break otomatis standar kertas F4 / Folio (215 x 330 mm).

---

## 💻 Menjalankan di Laptop (Lokal dengan Antigravity)

1. Buka terminal di folder proyek:
   ```powershell
   cd C:\Users\Cirilusyulian\.gemini\antigravity\scratch\spj-perjadin
   ```
2. Jalankan aplikasi:
   ```powershell
   python app.py
   ```
3. Buka browser dan akses:
   👉 **http://127.0.0.1:5000**
   - Username: `admin`
   - Password: `admin123`

---

## 🚀 Menjalankan di VPS Ubuntu & Menghubungkan ke Laptop / Antigravity

Aplikasi ini telah dirancang 100% *self-contained* sehingga dapat berjalan mulus di VPS Ubuntu 20.04 / 22.04 / 24.04.

### Metode 1: Melalui Git (Sangat Direkomendasikan)
Metode ini memudahkan Anda mengubah kode di Antigravity di laptop, lalu meng-update VPS secara instan.

1. **Di Laptop (Terminal Antigravity):**
   ```powershell
   cd C:\Users\Cirilusyulian\.gemini\antigravity\scratch\spj-perjadin
   git init
   git add .
   git commit -m "e-SPJ initial release"
   # Buat repository privat di GitHub / GitLab, lalu hubungkan:
   git remote add origin https://github.com/USERNAME/spj-perjadin.git
   git branch -M main
   git push -u origin main
   ```

2. **Di Ubuntu VPS:**
   Login ke VPS via SSH, lalu jalankan:
   ```bash
   sudo git clone https://github.com/USERNAME/spj-perjadin.git /var/www/spj-perjadin
   cd /var/www/spj-perjadin
   chmod +x deploy_vps.sh
   ./deploy_vps.sh
   ```
   Script `deploy_vps.sh` akan otomatis:
   - Menginstall Python3, Nginx, dan dependencies.
   - Mengonfigurasi Gunicorn & Systemd background service.
   - Mengonfigurasi Nginx Reverse Proxy di port 80.
   - Menyiapkan firewall.

3. **Sinkronisasi Pembaruan Kode Selanjutnya:**
   - Setelah mengedit kode di Antigravity di laptop:
     ```powershell
     git add .
     git commit -m "Update template"
     git push
     ```
   - Di VPS Ubuntu tinggal jalankan:
     ```bash
     cd /var/www/spj-perjadin && git pull && sudo systemctl restart spj-perjadin
     ```

---

### Metode 2: Upload Langsung via SCP / Rsync dari Laptop
Jika belum ingin memakai GitHub:
```powershell
# Jalankan dari PowerShell di laptop Anda:
scp -r C:\Users\Cirilusyulian\.gemini\antigravity\scratch\spj-perjadin\* root@IP_VPS_ANDA:/var/www/spj-perjadin/
```
Lalu di VPS:
```bash
cd /var/www/spj-perjadin
chmod +x deploy_vps.sh
./deploy_vps.sh
```

---

### Metode 3: Menjalankan via Docker di VPS
Jika VPS Anda sudah memiliki Docker:
```bash
cd /var/www/spj-perjadin
docker-compose up -d --build
```
Aplikasi akan langsung online di port `5000` (atau dihubungkan ke Nginx).

---

## 📁 Struktur Berkas

```
spj-perjadin/
├── app.py                      # Aplikasi Flask & Controller Routes
├── database.py                 # Skema SQLite, User & Inisialisasi Default
├── helpers.py                  # Format Rupiah, Terbilang ID, Tanggal Indo
├── requirements.txt            # Dependensi Python
├── deploy_vps.sh               # Script auto-install Nginx + Gunicorn di Ubuntu
├── docker-compose.yml          # Konfigurasi Docker
├── Dockerfile                  # Container build
├── README.md                   # Dokumentasi
├── static/
│   └── css/
│       └── print.css           # Styling presisi cetak standar naskah dinas
└── templates/
    ├── base.html               # Layout dasar Tailwind CSS & Phosphor Icons
    ├── login.html              # Halaman Login
    ├── dashboard.html          # Dashboard statistik SPJ
    ├── spj_list.html           # Daftar & pencarian SPJ
    ├── spj_form.html           # Form input SPJ dinamis (Kadis vs Staf)
    ├── spj_detail.html         # Document Hub preview 5 dokumen
    ├── settings.html           # Pengaturan Kop, Pejabat & 5 Template
    └── print/
        ├── spt_print.html              # Cetak SPT (Kadis & Staf)
        ├── pengeluaran_riil_print.html  # Cetak Daftar Pengeluaran Riil (SPTJM)
        ├── kwitansi_print.html          # Cetak Kwitansi Tanda Terima
        ├── rincian_biaya_print.html     # Cetak Rincian Biaya
        ├── laporan_print.html           # Cetak Laporan Perjalanan Dinas
        └── semua_print.html             # Cetak 1 Bundel 5 Dokumen Lengkap
```
