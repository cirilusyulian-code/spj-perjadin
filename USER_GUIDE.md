# PANDUAN PENGGUNA (USER GUIDE)
# APLIKASI e-SPJ DINAS v2.0
**Sistem Informasi Pengelolaan Dokumen SPJ Perjalanan Dinas Terpadu**

---

## DAFTAR ISI
1. [Tentang Aplikasi](#1-tentang-aplikasi)
2. [Persyaratan & Akses Masuk (Login)](#2-persyaratan--akses-masuk-login)
3. [Alur Kerja Utama (Workflow)](#3-alur-kerja-utama-workflow)
4. [Pengaturan Master & Template Sistem](#4-pengaturan-master--template-sistem)
   - 4.1 Instansi & Kop Surat Dinas (Kadis vs Staf)
   - 4.2 Pejabat Penandatangan
   - 4.3 Template Naskah Dokumen
   - 4.4 Manajemen Master Data Pegawai
5. [Panduan Membuat SPJ Baru](#5-panduan-membuat-spj-baru)
   - 5.1 Memilih Tipe SPT (Kadis vs Staf)
   - 5.2 Penomoran Surat & Tanggal SPT
   - 5.3 Maksud, Tujuan, dan Jadwal Perjalanan
   - 5.4 Memilih Pelaksana / Pegawai yang Ditugaskan
   - 5.5 Rincian Biaya Per Pelaksana & Pengeluaran Riil
6. [Halaman Detail & Manajemen Narasi Laporan](#6-halaman-detail--manajemen-narasi-laporan)
7. [Panduan Cetak Dokumen (F4 / Folio)](#7-panduan-cetak-dokumen-f4--folio)
   - 7.1 Daftar 5 Dokumen yang Dihasilkan
   - 7.2 Cetak Per Lembar vs Cetak 1 Bundel Lengkap
   - 7.3 Pengaturan Printer Browser (Print Dialog)
8. [Pencarian, Filter, & Monitoring SPJ](#8-pencarian-filter--monitoring-spj)
9. [Tanya Jawab & Troubleshooting (FAQ)](#9-tanya-jawab--troubleshooting-faq)

---

## 1. Tentang Aplikasi
**e-SPJ Dinas v2.0** adalah aplikasi web administrasi keuangan dan penugasan dinas yang dirancang khusus untuk mempermudah, mempercepat, dan membakukan pembuatan dokumen Surat Perintah Tugas (SPT) dan Surat Pertanggungjawaban (SPJ) Perjalanan Dinas sesuai dengan standar tata naskah dinas pemerintah daerah.

### Fitur Unggulan:
- **Dua Template SPT Mandiri:** Membedakan secara otomatis tata naskah dinas untuk **SPT Kepala Dinas** (ditandatangani Bupati/Sekretaris Daerah) dan **SPT Staf/Pelaksana** (ditandatangani Kepala Dinas).
- **6 Dokumen Lengkap Sekali Input:** Otomatis menghasilkan 6 berkas resmi sekaligus:
  1. Surat Tugas (SPT)
  2. Surat Perjalanan Dinas (SPD) - Diterbitkan per orang pelaksana
  3. Pengeluaran Riil
  4. Kwitansi Pembayaran
  5. Rincian Biaya Perjalanan Dinas
  6. Laporan Pelaksanaan Perjalanan Dinas
- **Cetak 1 Bundel Terintegrasi:** Fitur cetak seluruh berkas SPJ sekaligus dalam format kertas standar **F4 / Folio (215 x 330 mm)** dengan pemisah halaman (*page-break*) yang presisi.
- **Master Data Pegawai:** Dilengkapi data ASN instansi sehingga operator cukup memilih pegawai dari dropdown, NIP, pangkat, dan jabatan otomatis terisi.
- **Rincian Biaya Fleksibel Per Orang:** Dilengkapi 5 komponen baku (Uang Harian, Transportasi PP, Penginapan, Uang Representasi, dan Taxi).
- **Dukungan Format Spasi Baku:** Mempertahankan spasi kosong non-breaking pada penomoran naskah dinas (misal: register nomor surat).
- **Cetak Cepat Blanko SPPD:** Tombol langsung *"Blanko SPPD"* di Dashboard untuk membuka dan mencetak lembar belakang/visum SPPD kosong (`SPPD kosong.pdf`).

---

## 2. Persyaratan & Akses Masuk (Login)

### Cara Mengakses Aplikasi:
1. Buka peramban (*web browser*) seperti **Google Chrome**, **Microsoft Edge**, atau **Mozilla Firefox**.
2. Masukkan alamat URL aplikasi (misal: `http://localhost:5000` atau URL server dinas Anda).
3. Halaman Login akan terbuka.

### Akun Bawaan (Default Credentials):
- **Username:** `admin`
- **Password:** `admin123`

> ⚠️ **Catatan Keamanan:** Disarankan untuk segera memperbarui kata sandi atau menjaga keamanan akses server jika aplikasi digunakan dalam jaringan publik.

---

## 3. Alur Kerja Utama (Workflow)

Berikut siklus penggunaan aplikasi dari awal hingga pencetakan berkas SPJ:

```
[ 1. Login ]
     │
     ▼
[ 2. Pengaturan (Satu Kali di Awal) ]
     ├─ Atur Kop Dinas & Upload Logo (Kadis & Staf)
     ├─ Atur Nama & NIP Pejabat Penandatangan
     └─ Periksa / Tambah Master Data Pegawai
     │
     ▼
[ 3. Pembuatan SPJ Baru (/spj/create) ]
     ├─ Pilih Tipe SPT (Kadis / Staf)
     ├─ Isi Nomor SPT & SPPD, Maksud, Tujuan, & Tanggal
     ├─ Pilih Pelaksana dari Daftar Pegawai
     └─ Isi Rincian Biaya (Uang Harian, Transport, Hotel, dll.)
     │
     ▼
[ 4. Halaman Detail SPJ (/spj/<id>) ]
     ├─ Cek Pratinjau 5 Dokumen di Iframe Interaktif
     └─ Sesuaikan Narasi Laporan Perjadin (Bab IV, V, VI)
     │
     ▼
[ 5. Pencetakan Dokumen ]
     ├─ Opsi A: Cetak 1 Bundel Lengkap (Semua 5 Dokumen)
     └─ Opsi B: Cetak Per Dokumen Tertentu (SPT / Kwitansi / Riil / dll.)
```

---

## 4. Pengaturan Master & Template Sistem

Menu **Pengaturan Template** (`/settings`) dapat diakses melalui menu navigasi atas. Pengaturan ini menentukan identitas surat dan pejabat yang akan muncul pada seluruh dokumen cetak.

### 4.1 Instansi & Kop Surat Dinas
Aplikasi menyediakan **dua jenis kop dinas mandiri**:
1. **Kop Surat Kepala Dinas:** Digunakan khusus pada berkas dinas perjalanan luar daerah Kepala Dinas.
   - Upload Logo (Lambang Pemda/Garuda) format PNG/JPG dengan latar transparan.
   - Nama Instansi Induk (contoh: `PEMERINTAH KABUPATEN KEPAHIANG`).
   - Nama Instansi / Dinas (contoh: `DINAS KEPENDUDUKAN DAN PENCATATAN SIPIL`).
   - Alamat, nomor kontak, surel, kode pos, dan nama kota kedudukan dinas.
2. **Kop Surat Staf & Pelaksana:** Digunakan untuk perjalanan staf dan pejabat di bawah kepala dinas.
   - Dilengkapi logo, ukuran font instansi induk dan instansi dinas yang dapat disesuaikan.

### 4.2 Pejabat Penandatangan
Isi nama lengkap, gelar, pangkat/golongan, dan NIP pejabat berikut:
- **Kepala Dinas:** Pejabat penandatangan Surat Tugas staf.
- **Pejabat Penandatangan SPT Kepala Dinas:** Pejabat atasan langsung saat Kepala Dinas bertugas (misal: `Sekretaris Daerah` a.n. `Bupati Kepahiang`).
- **Pejabat Pembuat Komitmen (PPK) / PPTK:** Pejabat yang menyetujui rincian biaya dan kwitansi.
- **Bendahara Pengeluaran:** Pejabat pembayar uang muka/ganti perjalanan dinas.

### 4.3 Template Naskah Dokumen
Anda dapat mengubah narasi dasar hukum default untuk:
- Dasar hukum SPT Kepala Dinas & Staf.
- Template pernyataan Daftar Pengeluaran Riil.
- Template Kwitansi dan Rincian Biaya.
- Template Bab Standar Laporan Hasil Perjalanan Dinas.

### 4.4 Manajemen Master Data Pegawai
Tab **Master Pegawai** memungkinkan Anda mengelola data pegawai yang sering ditugaskan dinas:
- **Tambah Pegawai Baru:** Masukkan Nama Lengkap & Gelar, NIP, NIK, Pangkat/Golongan, dan Jabatan.
- **Ubah / Hapus Data Pegawai:** Klik ikon edit atau hapus pada baris pegawai.
- **Otomatisasi:** Data di master ini langsung terhubung dengan form pembuatan SPJ.

---

## 5. Panduan Membuat SPJ Baru

Untuk membuat SPJ baru, klik tombol **"Buat SPJ Baru"** pada bilah navigasi atau dashboard.

### Langkah-langkah Pengisian Formulir:

### 5.1 Memilih Tipe Template SPT
Pilih salah satu dari 2 opsi radio button:
- **SPT Kepala Dinas:** Jika perjalanan dinas dilakukan oleh Kepala Dinas. Form tambahan *"Pejabat Penandatangan SPT Kepala Dinas"* akan otomatis muncul (default: a.n. Bupati, Sekda).
- **SPT Staf / Pejabat di Bawah Kadis:** Jika perjalanan dinas dilakukan oleh pejabat eselon III, IV, fungsional, atau staf pelaksana.

### 5.2 Nomor Surat & Tanggal SPT
- **Nomor SPT & SPPD:** Format baku register otomatis disiapkan (contoh: `800/      /Dukcapil-Kph/2026`). Spasi kosong dipertahankan agar dapat distempel nomor register dinas.
- **Tanggal SPT Dikeluarkan:** Tanggal penetapan surat tugas (klik *"Set Hari Ini"* untuk tanggal berjalan).

### 5.3 Tujuan, Maksud, & Jadwal Waktu
1. **Kota / Daerah Tujuan:** Masukkan kota atau kabupaten tujuan (misal: *Jakarta Pusat*).
2. **Instansi / Lokasi Tujuan:** Nama kementerian, dinas, atau tempat kegiatan (misal: *Direktorat Jenderal Kependudukan dan Pencatatan Sipil Kemendagri*).
3. **Maksud Perjalanan Dinas:** Uraikan tugas secara rinci dan jelas.
4. **Dasar Hukum / Undangan:** Nomor surat undangan atau telaahan staf yang mendasari penugasan.
5. **Waktu Pelaksanaan:**
   - Isi **Tanggal Berangkat** dan **Tanggal Pulang**.
   - Lama hari perjalanan akan **terhitung otomatis** oleh sistem.
6. **Alat Angkutan:** Pilih jenis transportasi (Kendaraan Dinas/Mobil, Pesawat Udara, Kereta Api, dsb.).
7. **Mata Anggaran:** Pilih kode rekening anggaran (misal: `5.1.02.04.001.00001 - Belanja Perjalanan Dinas Biasa`).

### 5.4 Memilih Pelaksana / Pegawai yang Ditugaskan
- **Tambah Cepat dari Master:** Gunakan dropdown `+ Tambah Pelaksana (ASN)` untuk memilih pegawai. Nama, NIP, Pangkat, dan Jabatan akan langsung terisi otomatis.
- **Tambah Baris Kosong:** Gunakan tombol `+ Baris Kosong` jika ingin mengetik manual pelaksana non-ASN atau tamu.
- **Multi-Pelaksana:** Anda dapat menambahkan banyak pelaksana dalam 1 nomor penugasan sekaligus. Pegawai pada urutan pertama otomatis ditetapkan sebagai pelaksana utama.

### 5.5 Rincian Biaya Per Pelaksana & Pengeluaran Riil
Setiap pelaksana yang ditambahkan akan memiliki kartu rincian biaya sendiri:
- **5 Template Komponen Biaya Otomatis:**
  1. *Uang Harian:* Kuantitas (OH) otomatis mengikuti lama hari tugas.
  2. *Biaya Transportasi:* Satuan PP (Pergi-Pulang).
  3. *Biaya Penginapan:* Satuan Malam/Hari.
  4. *Uang Representasi:* Otomatis diisi jika pelaksana memiliki hak representasi (Kadis/Pejabat Eselon).
  5. *Biaya Taxi:* Satuan Kali untuk transport bandara/lokal.
- **Centang "Masuk Pengeluaran Riil":**
  - Centang kotak ini untuk item pengeluaran yang masuk ke format resmi *Daftar Pengeluaran Riil* (sesuai ketentuan tanpa bukti pihak ketiga).
- **Grand Total & Terbilang:** Total biaya seluruh pelaksana terakumulasi otomatis beserta teks terbilang rupiah.
- **Status Dokumen:** Pilih *Draft*, *Disetujui*, atau *Selesai*.
- Klik **"Simpan & Buat Dokumen"**.

---

## 6. Halaman Detail & Manajemen Narasi Laporan

Setelah disimpan, Anda akan diarahkan ke halaman **Detail & Cetak Dokumen SPJ** (`/spj/<id>`):

1. **Ringkasan Cepat (Quick Info):**
   - Menampilkan total biaya, jumlah hari & tanggal perjalanan, jumlah pelaksana, dan moda angkutan.
2. **Pratinjau Interaktif (Document Viewer):**
   - Terdapat tab untuk berganti dokumen secara langsung:
     * *1. SPT*
     * *2. SPD (Surat Perjalanan Dinas per orang)*
     * *3. Pengeluaran Riil*
     * *3. Kwitansi*
     * *4. Rincian Biaya*
     * *5. Laporan Perjadin*
   - Dokumen langsung dimuat di dalam bingkai interaktif.
3. **Kustomisasi Narasi Laporan Perjadin:**
   - Pada bagian bawah halaman, Anda dapat mengedit teks laporan khusus penugasan tersebut:
     * **Bab IV. Kegiatan yang Dilaksanakan**
     * **Bab V. Hasil yang Dicapai**
     * **Bab VI. Kesimpulan dan Saran**
   - Klik **"Simpan Narasi Laporan"** dan pratinjau dokumen laporan akan langsung diperbarui.

---

## 7. Panduan Cetak Dokumen (F4 / Folio)

### 7.1 Daftar 6 Dokumen yang Dihasilkan
| No | Nama Dokumen | Keterangan & Kegunaan |
|:--:|:---|:---|
| 1 | **Surat Tugas (SPT)** | Surat resmi penugasan dinas luar dengan format kop resmi (Kadis/Staf), dasar penugasan, daftar nama pelaksana, dan tanda tangan pejabat berwenang. |
| 2 | **Surat Perjalanan Dinas (SPD)** | Dokumen resmi format 10 poin sesuai template perbup yang diterbitkan per orang pelaksana perjalanan dinas. |
| 3 | **Daftar Pengeluaran Riil** | Bukti pertanggungjawaban pengeluaran yang tidak diperoleh bukti resminya sesuai ketentuan perundang-undangan. |
| 3 | **Kwitansi Pembayaran** | Tanda bukti penerimaan uang dinas dari Bendahara Pengeluaran ke pelaksana tugas, disetujui PPTK/PPK. |
| 4 | **Rincian Biaya Perjalanan Dinas** | Rincian tabel seluruh komponen belanja (uang saku, transport, penginapan) yang telah dibayarkan per orang. |
| 5 | **Laporan Perjalanan Dinas** | Laporan pertanggungjawaban pelaksanaan kegiatan teknis berformat 6 bab lengkap dengan tanda tangan pelaksana. |

### 7.2 Cetak Per Lembar vs Cetak 1 Bundel Lengkap
- **Cetak 1 Lembar Spesifik:** Klik tombol salah satu dokumen pada tab, lalu klik tombol **"Cetak"** atau **"Layar Penuh"**.
- **Cetak 1 Bundel Lengkap (Disarankan):** Klik tombol biru besar **"Cetak 1 Bundel Lengkap"** di bagian atas. Seluruh 6 dokumen akan dibuka berurutan dalam satu halaman dengan batas halaman (*page-break*) otomatis.

### 7.3 Pengaturan Printer Browser (Print Dialog)
Untuk hasil cetak yang rapi, pas, dan tidak terpotong, atur pengaturan cetak di browser Anda sebagai berikut:

| Parameter Pengaturan | Nilai yang Disarankan |
|:---|:---|
| **Destination / Printer** | Pilih Printer Fisik Anda atau **Save as PDF** |
| **Paper Size (Ukuran Kertas)** | **Folio / F4** (atau *Legal / Custom 215 x 330 mm*) |
| **Orientation (Arah Kertas)** | **Portrait** (Tegak) |
| **Margins** | **Default** atau **None / Minimum** (CSS aplikasi sudah mengatur margin standar 1.2 cm - 1.5 cm) |
| **Scale (Skala)** | **100%** (atau *Fit to Printable Area*) |
| **Options > Background Graphics** | **Centang / Aktifkan** (Agar garis tabel dan warna kop tercetak sempurna) |
| **Options > Headers and footers** | **Nonaktifkan / Uncheck** (Agar tanggal browser dan URL tidak muncul di cetakan) |

---

## 8. Pencarian, Filter, & Monitoring SPJ

Daftar seluruh SPJ yang pernah dibuat dapat dipantau melalui menu **"Data SPJ"** (`/spj`):
1. **Kotak Pencarian:** Cari berdasarkan nomor SPT, nomor SPPD, kota tujuan, atau maksud perjalanan dinas.
2. **Filter Tipe SPT:** Filter khusus *SPT Kepala Dinas* atau *SPT Staf*.
3. **Filter Status Dokumen:** Filter berdasarkan status (*Draft*, *Disetujui*, *Selesai*).
4. **Tombol Aksi Cepat:**
   - Tombol Mata: Membuka detail & cetak berkas.
   - Tombol Pensil: Mengedit isi data SPJ.
   - Tombol Sampah: Menghapus data SPJ (disertai konfirmasi keamanan).

---

## 9. Tanya Jawab & Troubleshooting (FAQ)

**Q1: Bagaimana cara mencetak pada kertas Folio/F4 jika pilihan kertas F4 tidak ada di printer saya?**
> **Solusi:** Pilih ukuran **Legal** atau buat ukuran kertas kustom pada pengaturan driver printer Anda dengan ukuran lebar: `215 mm` (21.5 cm) dan tinggi: `330 mm` (33 cm).

**Q2: Mengapa garis kop atau logo dinas tidak muncul saat diprint?**
> **Solusi:** Pastikan pada jendela pratinjau cetak (*Print Preview*) browser Anda, opsi **"Background graphics"** (Grafis latar belakang) sudah dicentang.

**Q3: Bagaimana cara mengubah data pejabat penandatangan jika terjadi rotasi jabatan?**
> **Solusi:** Masuk ke menu **Pengaturan Template** > Tab **Pejabat Penandatangan**. Ubah nama, NIP, dan jabatan pejabat terkait, lalu klik **Simpan Pengaturan**. Perubahan ini akan langsung berlaku pada seluruh dokumen cetak berikutnya.

**Q4: Apakah data yang sudah disimpan masih bisa diedit?**
> **Solusi:** Ya. Buka dokumen SPJ yang bersangkutan, klik tombol **"Edit SPJ"**, lakukan perbaikan data, lalu klik **"Simpan Perubahan"**.

---

*Panduan Pengguna e-SPJ Dinas v2.0 • Hak Cipta © 2026 Pemerintah Daerah.*

