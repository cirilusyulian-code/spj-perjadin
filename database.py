import sqlite3
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'spj_database.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Settings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    ''')

    # SPJ table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS spj (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nomor_spt TEXT,
        nomor_sppd TEXT,
        jenis_spt TEXT DEFAULT 'staf', -- 'kadis' or 'staf'
        tujuan TEXT NOT NULL,
        instansi_tujuan TEXT,
        maksud TEXT NOT NULL,
        dasar_hukum TEXT,
        tanggal_berangkat DATE NOT NULL,
        tanggal_pulang DATE NOT NULL,
        lama_hari INTEGER DEFAULT 1,
        tempat_berangkat TEXT DEFAULT 'Tempat Kedudukan',
        angkutan TEXT DEFAULT 'Pesawat Udara',
        mata_anggaran TEXT DEFAULT '5.1.02.04.01.0001 (Belanja Perjalanan Dinas Biasa)',
        status TEXT DEFAULT 'Draft', -- 'Draft', 'Disetujui', 'Selesai'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # SPJ Peserta
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS spj_peserta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        spj_id INTEGER NOT NULL,
        nama TEXT NOT NULL,
        nip TEXT,
        pangkat_golongan TEXT,
        jabatan TEXT,
        urutan INTEGER DEFAULT 1,
        FOREIGN KEY (spj_id) REFERENCES spj (id) ON DELETE CASCADE
    )
    ''')

    # SPJ Biaya (Per Item Rincian)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS spj_biaya (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        spj_id INTEGER NOT NULL,
        jenis_biaya TEXT NOT NULL, -- 'uang_harian', 'taxi', 'transportasi', 'hotel', 'tiket_pesawat', 'tiket_kapal', 'lainnya'
        keterangan TEXT NOT NULL,
        kuantitas REAL DEFAULT 1,
        satuan TEXT DEFAULT 'Hari',
        tarif REAL DEFAULT 0,
        total REAL DEFAULT 0,
        termasuk_riil INTEGER DEFAULT 0, -- 1 if included in Pengeluaran Riil
        FOREIGN KEY (spj_id) REFERENCES spj (id) ON DELETE CASCADE
    )
    ''')

    # SPJ Laporan
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS spj_laporan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        spj_id INTEGER UNIQUE NOT NULL,
        pendahuluan TEXT,
        kegiatan_dilaksanakan TEXT,
        hasil_kegiatan TEXT,
        kesimpulan_saran TEXT,
        FOREIGN KEY (spj_id) REFERENCES spj (id) ON DELETE CASCADE
    )
    ''')

    conn.commit()

    # Seed Default User if not exists
    cursor.execute('SELECT COUNT(*) as cnt FROM users')
    if cursor.fetchone()['cnt'] == 0:
        cursor.execute('''
        INSERT INTO users (username, password_hash, full_name, role)
        VALUES (?, ?, ?, ?)
        ''', ('admin', generate_password_hash('admin123'), 'Administrator SPJ', 'admin'))

    # Seed Default Settings if not exists
    default_settings = {
        'instansi_nama_induk': 'PEMERINTAH DAERAH',
        'instansi_nama': 'DINAS KOMUNIKASI DAN INFORMATIKA',
        'instansi_alamat': 'Jl. Protokol No. 12, Kompleks Perkantoran Terpadu',
        'instansi_kontak': 'Telp. (021) 7890123 | Email: diskominfo@pemda.go.id | Kode Pos 10110',
        'instansi_kota': 'Jakarta',
        'pejabat_kadis_nama': 'Dr. H. Bambang Setiawan, M.Si.',
        'pejabat_kadis_nip': '19740615 199903 1 005',
        'pejabat_kadis_pangkat': 'Pembina Utama Muda (IV/c)',
        'pejabat_kadis_jabatan': 'Kepala Dinas Komunikasi dan Informatika',
        'pejabat_ppk_nama': 'Hendro Wibowo, S.T., M.M.',
        'pejabat_ppk_nip': '19820412 200604 1 012',
        'pejabat_ppk_pangkat': 'Pembina (IV/a)',
        'pejabat_ppk_jabatan': 'Pejabat Pembuat Komitmen (PPK)',
        'pejabat_bendahara_nama': 'Dewi Anggraini, S.E.',
        'pejabat_bendahara_nip': '19880918 201101 2 007',
        'pejabat_bendahara_pangkat': 'Penata Tk. I (III/d)',
        'pejabat_bendahara_jabatan': 'Bendahara Pengeluaran',
        'template_spt_kadis': 'Berdasarkan Disposisi Pimpinan Daerah dan DPA SKPD Dinas Komunikasi dan Informatika Tahun Anggaran 2026 tentang Program Peningkatan Tata Kelola Pemerintahan Berbasis Elektronik (SPBE).',
        'template_spt_staf': 'Berdasarkan Peraturan Bupati/Walikota tentang Pedoman Pelaksanaan Perjalanan Dinas dan Dokumen Pelaksanaan Anggaran (DPA) Dinas Komunikasi dan Informatika Tahun Anggaran 2026.',
        'template_pengeluaran_riil': 'Dengan ini menyatakan dengan sesungguhnya bahwa biaya perjalanan dinas di bawah ini yang tidak dapat diperoleh bukti-bukti pengeluarannya meliputi biaya transportasi lokal/taksi dan pengeluaran darat riil, benar-benar dikeluarkan untuk keperluan pelaksanaan tugas dan apabila di kemudian hari terdapat kelebihan atas pembayaran tersebut kami bersedia menyetorkan kelebihan tersebut ke Kas Daerah.',
        'template_kwitansi': 'Sudah terima dari Bendahara Pengeluaran Dinas Komunikasi dan Informatika sejumlah uang untuk pembayaran biaya pelaksanaan perjalanan dinas sesuai Surat Perintah Tugas dan Surat Perintah Perjalanan Dinas.',
        'template_rincian_biaya': 'Rincian Perhitungan Biaya Perjalanan Dinas berdasarkan Standar Biaya Masukan (SBM) yang berlaku.',
        'template_laporan': json.dumps({
            "pendahuluan": "Perjalanan dinas ini dilaksanakan dalam rangka memenuhi undangan dan tindak lanjut program koordinasi implementasi SPBE di tingkat nasional.",
            "kegiatan": "1. Menghadiri rapat pleno pembukaan dan pengarahan teknis.\n2. Diskusi panel dan konsultasi meja kerja tata kelola arsitektur data.\n3. Perumusan rekomendasi percepatan integrasi layanan publik digital.",
            "hasil": "1. Diperoleh pemahaman komprehensif mengenai integrasi portal layanan nasional.\n2. Jadwal asistensi lanjutan bersama tim teknis pusat telah disepakati.\n3. Bahan panduan dan instrumen monev berhasil dihimpun untuk ditindaklanjuti.",
            "kesimpulan": "Pelaksanaan tugas perjalanan dinas telah berlangsung dengan tertib, lancar, dan mencapai sasaran. Disarankan segera dibentuk tim kerja tindak lanjut di tingkat OPD."
        })
    }

    for k, v in default_settings.items():
        cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (k, v))

    conn.commit()
    conn.close()

def get_settings():
    conn = get_db()
    rows = conn.execute('SELECT key, value FROM settings').fetchall()
    conn.close()
    return {r['key']: r['value'] for r in rows}

def update_settings(data_dict):
    conn = get_db()
    for k, v in data_dict.items():
        conn.execute('INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?', (k, v, v))
    conn.commit()
    conn.close()

def verify_user(username, password):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None

def change_password(user_id, new_password):
    conn = get_db()
    conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (generate_password_hash(new_password), user_id))
    conn.commit()
    conn.close()

def create_sample_data():
    conn = get_db()
    # Check if there is any SPJ
    cnt = conn.execute('SELECT COUNT(*) as c FROM spj').fetchone()['c']
    if cnt == 0:
        cursor = conn.cursor()
        # Sample 1: SPT Kepala Dinas
        cursor.execute('''
        INSERT INTO spj (nomor_spt, nomor_sppd, jenis_spt, tujuan, instansi_tujuan, maksud, dasar_hukum, tanggal_berangkat, tanggal_pulang, lama_hari, angkutan, mata_anggaran, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            '090/102/SPT/DISKOMINFO/2026',
            '094/102/SPPD/DISKOMINFO/2026',
            'kadis',
            'Jakarta Pusat',
            'Kementerian Komunikasi dan Digital RI',
            'Menghadiri Rapat Koordinasi Nasional Penyelenggaraan Transformasi Digital dan Keterpaduan Layanan Publik Digital 2026',
            'Surat Undangan Menteri Komunikasi dan Digital RI Nomor: UND-241/KOMDIGI/SJ/10/2026',
            '2026-10-22',
            '2026-10-24',
            3,
            'Pesawat Udara',
            '5.1.02.04.01.0001 - Belanja Perjalanan Dinas Biasa',
            'Disetujui'
        ))
        spj1_id = cursor.lastrowid
        
        # Peserta SPJ 1
        cursor.execute('''
        INSERT INTO spj_peserta (spj_id, nama, nip, pangkat_golongan, jabatan, urutan)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (spj1_id, 'Dr. H. Bambang Setiawan, M.Si.', '19740615 199903 1 005', 'Pembina Utama Muda (IV/c)', 'Kepala Dinas Komunikasi dan Informatika', 1))

        # Biaya SPJ 1
        biaya1 = [
            ('uang_harian', 'Uang Harian (3 Hari)', 3, 'Hari', 530000, 1590000, 0),
            ('tiket_pesawat', 'Tiket Pesawat Garuda Indonesia (PP Jakarta)', 1, 'PP', 3450000, 3450000, 0),
            ('hotel', 'Akomodasi / Hotel Santika Premiere (2 Malam)', 2, 'Malam', 850000, 1700000, 0),
            ('taxi', 'Taksi Bandara Soekarno Hatta - Hotel PP', 2, 'Kali', 225000, 450000, 1),
            ('transportasi', 'Transportasi Lokal Kedinasan Dalam Kota', 2, 'Hari', 180000, 360000, 1)
        ]
        for b in biaya1:
            cursor.execute('''
            INSERT INTO spj_biaya (spj_id, jenis_biaya, keterangan, kuantitas, satuan, tarif, total, termasuk_riil)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (spj1_id, b[0], b[1], b[2], b[3], b[4], b[5], b[6]))

        # Sample 2: SPT Staf (Tim Teknis)
        cursor.execute('''
        INSERT INTO spj (nomor_spt, nomor_sppd, jenis_spt, tujuan, instansi_tujuan, maksud, dasar_hukum, tanggal_berangkat, tanggal_pulang, lama_hari, angkutan, mata_anggaran, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            '090/108/SPT/DISKOMINFO/2026',
            '094/108/SPPD/DISKOMINFO/2026',
            'staf',
            'Surabaya, Jawa Timur',
            'Dinas Kominfo Provinsi Jawa Timur',
            'Studi Tiru dan Asistensi Teknis Pengelolaan Computer Security Incident Response Team (CSIRT) dan Keamanan Informasi',
            'Surat Kepala Dinas Kominfo Provinsi Jawa Timur Perihal Kesediaan Penerimaan Kunjungan Teknis No: 005/782/114.2/2026',
            '2026-11-04',
            '2026-11-06',
            3,
            'Pesawat Udara',
            '5.1.02.04.01.0001 - Belanja Perjalanan Dinas Biasa',
            'Draft'
        ))
        spj2_id = cursor.lastrowid

        # Peserta SPJ 2 (3 orang tim)
        peserta2 = [
            (spj2_id, 'Rahmat Hidayat, S.Kom.', '19870311 201001 1 009', 'Penata Tk. I (III/d)', 'Pranata Komputer Ahli Muda', 1),
            (spj2_id, 'Fajar Nugroho, S.Tr.Kom.', '19930724 201802 1 002', 'Penata Muda Tk. I (III/b)', 'Manggala Informatika Ahli Pertama', 2),
            (spj2_id, 'Dinda Permata, A.Md.', '19980519 202103 2 004', 'Pengatur (II/c)', 'Pranata Komputer Terampil', 3),
        ]
        for p in peserta2:
            cursor.execute('''
            INSERT INTO spj_peserta (spj_id, nama, nip, pangkat_golongan, jabatan, urutan)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', p)

        # Biaya SPJ 2
        biaya2 = [
            ('uang_harian', 'Uang Harian 3 Orang x 3 Hari', 9, 'OH', 410000, 3690000, 0),
            ('tiket_pesawat', 'Tiket Pesawat PP Surabaya (3 Orang)', 3, 'Orang', 2600000, 7800000, 0),
            ('hotel', 'Hotel Twin Bed 2 Kamar x 2 Malam', 4, 'Kamar/Malam', 650000, 2600000, 0),
            ('taxi', 'Taksi Bandara Juanda - Pusat Kota PP (Pengeluaran Riil)', 2, 'Kali', 190000, 380000, 1),
            ('transportasi', 'Transport Lokal / Sewa Kendaraan Tim CSIRT', 2, 'Hari', 450000, 900000, 1)
        ]
        for b in biaya2:
            cursor.execute('''
            INSERT INTO spj_biaya (spj_id, jenis_biaya, keterangan, kuantitas, satuan, tarif, total, termasuk_riil)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (spj2_id, b[0], b[1], b[2], b[3], b[4], b[5], b[6]))

        conn.commit()
    conn.close()
