# CHANGELOG - e-SPJ Dinas

Catatan riwayat rilis dan pembaruan versi sistem aplikasi **e-SPJ Dinas**.  
Format penomoran versi mengikuti standar **Semantic Versioning (MAJOR.MINOR.PATCH)**.

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

