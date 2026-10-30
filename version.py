"""
Pusat Konfigurasi Versi Aplikasi e-SPJ Dinas
Format: Semantic Versioning (MAJOR.MINOR.PATCH)

Aturan Pembaruan:
- MAJOR: Perubahan arsitektur besar / alur kerja fundamental (misal: 3.0.0)
- MINOR: Penambahan fitur baru yang kompatibel ke belakang (misal: 2.1.0, 2.2.0)
- PATCH: Perbaikan bug kecil / perbaikan tata letak / styling (misal: 2.1.1)
- DATABASE: spj_database.db diatur skip-worktree agar data transaksi/operasional lokal tidak ikut ter-push kecuali jika ada migrasi struktur tabel.
"""

VERSION_MAJOR = 2
VERSION_MINOR = 2
VERSION_PATCH = 0

__version__ = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"
APP_VERSION = __version__
APP_RELEASE_DATE = "30 Oktober 2026"
APP_NAME = "e-SPJ Dinas"

def get_version_info():
    return {
        "version": APP_VERSION,
        "major": VERSION_MAJOR,
        "minor": VERSION_MINOR,
        "patch": VERSION_PATCH,
        "release_date": APP_RELEASE_DATE,
        "name": APP_NAME
    }

