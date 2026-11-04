# CHANGELOG - e-SPJ Dinas

Catatan riwayat rilis dan pembaruan versi sistem aplikasi **e-SPJ Dinas**.  
Format penomoran versi mengikuti standar **Semantic Versioning (MAJOR.MINOR.PATCH)**.

---

## [v2.2.1] - 2026-11-04
### Changed (Pembaruan & Penyesuaian Tata Naskah Dinas)
- **Standar Tipografi & Margin Dokumen F4:** Penyeragaman margin F4/Folio (Atas 2cm, Bawah 2cm, Kanan 2cm, Kiri 3cm) serta standar font Arial (Kop Pemda 14pt Bold, Dinas 18pt Bold, Kontak 11pt, Judul/Nomor/Batang Tubuh 12pt, Tabel Rincian 11pt) di seluruh dokumen cetak (`spt_print.html`, `spd_print.html`, `kwitansi_print.html`, `pengeluaran_riil_print.html`, `rincian_biaya_print.html`, `laporan_print.html`, `semua_print.html`).
- **Format Diktum "Untuk" pada SPT:** Mengikuti susunan `[maksud] yang bertempat di [instansi_tujuan] di [tujuan]`.
- **Tombol Reset Format Baku Dasar Hukum:** Menambahkan tombol reset pada input & edit SPJ untuk mengembalikan teks konsiderans dasar hukum ke format baku pengaturan (Kadis atau Staf).
- **Format Cetak SPD 10 Poin:** Poin 1 (Pengguna Anggaran) menggunakan `KEPALA [instansi_nama] [instansi_nama_induk]`, Tempat Berangkat baku `Kepahiang`, Tempat Tujuan `[instansi_tujuan] di [tujuan]`, dan Tabel Pengikut (Poin 8) dikosongkan dengan strip (`-`).
- **Format Cetak Kwitansi:** Nomor Kuitansi mengikuti register penomoran SPPD `800/      /SPPD/Dukcapil-Kph/2026`, dan klausul Untuk Pengeluaran mendahulukan instansi tujuan sebelum kota tujuan.
- **Deteksi Otomatis `jalankan.bat`:** Pengecekan cerdas executable Python yang memuat Flask pada peluncur lokal Windows.

---

## [v2.2.0] - 2026-10-30
### Added (Penambahan Fitur)
- **Surat Perjalanan Dinas (SPD per orang):** Integrasi format naskah dinas 10 poin resmi sesuai template Excel (`template spd.xlsx`), otomatis dicetak mandiri per pelaksana perjalanan dinas.
- **Tombol "Blanko SPPD" di Dashboard:** Tombol cepat satu-klik di samping tombol Pengaturan untuk membuka dan mencetak lembar belakang/visum SPPD kosong (`SPPD kosong.pdf`).
- **Pemusatan Konfigurasi Versi Terpadu (`version.py`):** Seluruh nomor versi sistem, tanggal rilis, dan cache busting CSS/JS kini terpusat pada satu variabel global (`APP_VERSION`).
- **Filter Cetak Pelaksana SPD:** Dropdown pemilihan pelaksana pada halaman cetak SPD untuk memilih cetak semua pelaksana atau perorangan.
- **Script Peluncur `jalankan.bat`:** Kemudahan menjalankan service lokal di Windows cukup dengan sekali dobel klik.

### Changed (Pembaruan)
- Fitur **"Cetak 1 Bundel Lengkap"** diperbarui menghasilkan 6 dokumen resmi sekaligus (termasuk SPD per orang).
- Pembaruan dokumen panduan pengguna di `USER_GUIDE.md`.

---

## [v2.1.0] - 2026-10-29
### Added
- Panduan pengguna komprehensif di `USER_GUIDE.md`.
- Penataan tata letak responsif formulir SPJ mobile & desktop.

---

## [v2.0.0] - 2026-10-25
### Initial Release (Rilis Awal Sistem Web e-SPJ)
- Sistem administrasi pembuatan dokumen SPJ Perjalanan Dinas berbasis Python Flask & Tailwind CSS.
- Pemisahan otomatis template **SPT Kepala Dinas** dan **SPT Staf/Pelaksana**.
- Otomasi pembuatan 5 dokumen naskah dinas standar F4/Folio: SPT, Daftar Pengeluaran Riil, Kwitansi Pembayaran, Rincian Biaya, dan Laporan Hasil Perjalanan Dinas.
- Master database 19 ASN Dukcapil dengan auto-fill Nama, NIP, Pangkat/Golongan, dan Jabatan.
- Preservasi spasi register penomoran surat non-breaking space.
- Dashboard ringkasan total SPJ, total realisasi anggaran, dan rincian penugasan terbaru.
