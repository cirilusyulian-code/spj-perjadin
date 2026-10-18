import os
import json
import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, jsonify

from database import init_db, get_db, get_settings, update_settings, verify_user, create_sample_data
from helpers import format_rupiah, terbilang, format_tanggal, hitung_hari, angka_murni

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'spj-secret-key-super-secure-2026-vps')

# Register custom Jinja filters
app.jinja_env.filters['format_rupiah'] = format_rupiah
app.jinja_env.filters['terbilang'] = terbilang
app.jinja_env.filters['format_tanggal'] = format_tanggal
app.jinja_env.globals.update(
    format_rupiah=format_rupiah,
    terbilang=terbilang,
    format_tanggal=format_tanggal,
    angka_murni=angka_murni
)

# Login requirement decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan masuk (login) terlebih dahulu untuk mengakses sistem.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ----------------- AUTHENTICATION -----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = verify_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            flash(f'Selamat datang kembali, {user["full_name"]}!', 'success')
            next_url = request.args.get('next') or url_for('dashboard')
            return redirect(next_url)
        else:
            flash('Username atau password tidak cocok.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah berhasil keluar dari sistem.', 'info')
    return redirect(url_for('login'))

# ----------------- DASHBOARD -----------------
@app.route('/')
@login_required
def dashboard():
    conn = get_db()
    total_spj = conn.execute('SELECT COUNT(*) as c FROM spj').fetchone()['c']
    spj_kadis = conn.execute("SELECT COUNT(*) as c FROM spj WHERE jenis_spt = 'kadis'").fetchone()['c']
    spj_staf = conn.execute("SELECT COUNT(*) as c FROM spj WHERE jenis_spt = 'staf'").fetchone()['c']

    # Total all expenses
    total_biaya_row = conn.execute('SELECT SUM(total) as s FROM spj_biaya').fetchone()
    total_biaya = total_biaya_row['s'] if total_biaya_row and total_biaya_row['s'] else 0

    # Recent SPJ
    recent_rows = conn.execute('''
        SELECT s.*, 
            COALESCE((SELECT SUM(b.total) FROM spj_biaya b WHERE b.spj_id = s.id), 0) as total_biaya
        FROM spj s
        ORDER BY s.id DESC
        LIMIT 6
    ''').fetchall()
    conn.close()

    return render_template('dashboard.html',
        total_spj=total_spj,
        spj_kadis=spj_kadis,
        spj_staf=spj_staf,
        total_biaya=total_biaya,
        recent_spj=recent_rows
    )

# ----------------- SPJ LIST & SEARCH -----------------
@app.route('/spj')
@login_required
def spj_list():
    q = request.args.get('q', '').strip()
    jenis = request.args.get('jenis', '').strip()
    status = request.args.get('status', '').strip()

    sql = '''
        SELECT s.*,
            COALESCE((SELECT SUM(b.total) FROM spj_biaya b WHERE b.spj_id = s.id), 0) as total_biaya,
            (SELECT COUNT(*) FROM spj_peserta p WHERE p.spj_id = s.id) as jumlah_peserta,
            (SELECT p.nama FROM spj_peserta p WHERE p.spj_id = s.id ORDER BY p.urutan ASC LIMIT 1) as nama_peserta_pertama
        FROM spj s
        WHERE 1=1
    '''
    params = []

    if q:
        sql += ' AND (s.nomor_spt LIKE ? OR s.nomor_sppd LIKE ? OR s.tujuan LIKE ? OR s.maksud LIKE ?)'
        wildcard = f'%{q}%'
        params.extend([wildcard, wildcard, wildcard, wildcard])

    if jenis:
        sql += ' AND s.jenis_spt = ?'
        params.append(jenis)

    if status:
        sql += ' AND s.status = ?'
        params.append(status)

    sql += ' ORDER BY s.id DESC'

    conn = get_db()
    items = conn.execute(sql, params).fetchall()
    conn.close()

    return render_template('spj_list.html',
        spj_items=items,
        query_q=q,
        query_jenis=jenis,
        query_status=status
    )

# ----------------- CREATE SPJ -----------------
@app.route('/spj/create', methods=['GET', 'POST'])
@login_required
def spj_create():
    s = get_settings()
    today_str = datetime.date.today().strftime('%Y-%m-%d')

    if request.method == 'POST':
        nomor_spt = request.form.get('nomor_spt', '').strip()
        nomor_sppd = request.form.get('nomor_sppd', '').strip()
        jenis_spt = request.form.get('jenis_spt', 'staf').strip()
        tujuan = request.form.get('tujuan', '').strip()
        instansi_tujuan = request.form.get('instansi_tujuan', '').strip()
        maksud = request.form.get('maksud', '').strip()
        dasar_hukum = request.form.get('dasar_hukum', '').strip()
        tanggal_berangkat = request.form.get('tanggal_berangkat', today_str).strip()
        tanggal_pulang = request.form.get('tanggal_pulang', today_str).strip()
        lama_hari = int(request.form.get('lama_hari', 1))
        angkutan = request.form.get('angkutan', 'Pesawat Udara').strip()
        mata_anggaran = request.form.get('mata_anggaran', '').strip()
        status = request.form.get('status', 'Draft').strip()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO spj (
                nomor_spt, nomor_sppd, jenis_spt, tujuan, instansi_tujuan, maksud, dasar_hukum,
                tanggal_berangkat, tanggal_pulang, lama_hari, angkutan, mata_anggaran, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            nomor_spt, nomor_sppd, jenis_spt, tujuan, instansi_tujuan, maksud, dasar_hukum,
            tanggal_berangkat, tanggal_pulang, lama_hari, angkutan, mata_anggaran, status
        ))
        spj_id = cursor.lastrowid

        # Insert Peserta
        peserta_nama = request.form.getlist('peserta_nama[]')
        peserta_nip = request.form.getlist('peserta_nip[]')
        peserta_pangkat = request.form.getlist('peserta_pangkat[]')
        peserta_jabatan = request.form.getlist('peserta_jabatan[]')

        for idx, nama in enumerate(peserta_nama):
            if nama.strip():
                nip = peserta_nip[idx].strip() if idx < len(peserta_nip) else ''
                pangkat = peserta_pangkat[idx].strip() if idx < len(peserta_pangkat) else ''
                jabatan = peserta_jabatan[idx].strip() if idx < len(peserta_jabatan) else ''
                cursor.execute('''
                    INSERT INTO spj_peserta (spj_id, nama, nip, pangkat_golongan, jabatan, urutan)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (spj_id, nama.strip(), nip, pangkat, jabatan, idx + 1))

        # Insert Biaya
        biaya_jenis = request.form.getlist('biaya_jenis[]')
        biaya_keterangan = request.form.getlist('biaya_keterangan[]')
        biaya_kuantitas = request.form.getlist('biaya_kuantitas[]')
        biaya_satuan = request.form.getlist('biaya_satuan[]')
        biaya_tarif = request.form.getlist('biaya_tarif[]')

        for idx, jenis_b in enumerate(biaya_jenis):
            ket = biaya_keterangan[idx].strip() if idx < len(biaya_keterangan) else ''
            if ket:
                qty = float(biaya_kuantitas[idx]) if idx < len(biaya_kuantitas) and biaya_kuantitas[idx] else 1.0
                sat = biaya_satuan[idx].strip() if idx < len(biaya_satuan) else 'Hari'
                tarif = float(biaya_tarif[idx]) if idx < len(biaya_tarif) and biaya_tarif[idx] else 0.0
                total = qty * tarif
                is_riil = 1 if request.form.get(f'biaya_riil_{idx}') == '1' else 0

                cursor.execute('''
                    INSERT INTO spj_biaya (spj_id, jenis_biaya, keterangan, kuantitas, satuan, tarif, total, termasuk_riil)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (spj_id, jenis_b, ket, qty, sat, tarif, total, is_riil))

        conn.commit()
        conn.close()

        flash('Dokumen SPJ Perjalanan Dinas berhasil dibuat! 5 Dokumen siap dicetak.', 'success')
        return redirect(url_for('spj_detail', spj_id=spj_id))

    # Auto-generate next suggested number
    conn = get_db()
    current_cnt = conn.execute('SELECT COUNT(*) as c FROM spj').fetchone()['c'] + 1
    conn.close()
    year = datetime.date.today().year
    default_nomor_spt = f"090/{current_cnt:03d}/SPT/DISKOMINFO/{year}"
    default_nomor_sppd = f"094/{current_cnt:03d}/SPPD/DISKOMINFO/{year}"

    return render_template('spj_form.html',
        spj=None,
        peserta_list=[],
        biaya_list=[],
        today_date=today_str,
        default_nomor_spt=default_nomor_spt,
        default_nomor_sppd=default_nomor_sppd,
        default_dasar_hukum=s.get('template_spt_staf', ''),
        default_pelaksana_nama=s.get('pejabat_kadis_nama', ''),
        default_pelaksana_nip=s.get('pejabat_kadis_nip', ''),
        default_pelaksana_pangkat=s.get('pejabat_kadis_pangkat', ''),
        default_pelaksana_jabatan=s.get('pejabat_kadis_jabatan', '')
    )

# ----------------- EDIT SPJ -----------------
@app.route('/spj/<int:spj_id>/edit', methods=['GET', 'POST'])
@login_required
def spj_edit(spj_id):
    conn = get_db()
    spj = conn.execute('SELECT * FROM spj WHERE id = ?', (spj_id,)).fetchone()
    if not spj:
        conn.close()
        abort(404)

    s = get_settings()

    if request.method == 'POST':
        nomor_spt = request.form.get('nomor_spt', '').strip()
        nomor_sppd = request.form.get('nomor_sppd', '').strip()
        jenis_spt = request.form.get('jenis_spt', 'staf').strip()
        tujuan = request.form.get('tujuan', '').strip()
        instansi_tujuan = request.form.get('instansi_tujuan', '').strip()
        maksud = request.form.get('maksud', '').strip()
        dasar_hukum = request.form.get('dasar_hukum', '').strip()
        tanggal_berangkat = request.form.get('tanggal_berangkat', '').strip()
        tanggal_pulang = request.form.get('tanggal_pulang', '').strip()
        lama_hari = int(request.form.get('lama_hari', 1))
        angkutan = request.form.get('angkutan', 'Pesawat Udara').strip()
        mata_anggaran = request.form.get('mata_anggaran', '').strip()
        status = request.form.get('status', 'Draft').strip()

        cursor = conn.cursor()
        cursor.execute('''
            UPDATE spj SET
                nomor_spt = ?, nomor_sppd = ?, jenis_spt = ?, tujuan = ?, instansi_tujuan = ?, maksud = ?, dasar_hukum = ?,
                tanggal_berangkat = ?, tanggal_pulang = ?, lama_hari = ?, angkutan = ?, mata_anggaran = ?, status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            nomor_spt, nomor_sppd, jenis_spt, tujuan, instansi_tujuan, maksud, dasar_hukum,
            tanggal_berangkat, tanggal_pulang, lama_hari, angkutan, mata_anggaran, status, spj_id
        ))

        # Re-sync Peserta
        cursor.execute('DELETE FROM spj_peserta WHERE spj_id = ?', (spj_id,))
        peserta_nama = request.form.getlist('peserta_nama[]')
        peserta_nip = request.form.getlist('peserta_nip[]')
        peserta_pangkat = request.form.getlist('peserta_pangkat[]')
        peserta_jabatan = request.form.getlist('peserta_jabatan[]')

        for idx, nama in enumerate(peserta_nama):
            if nama.strip():
                nip = peserta_nip[idx].strip() if idx < len(peserta_nip) else ''
                pangkat = peserta_pangkat[idx].strip() if idx < len(peserta_pangkat) else ''
                jabatan = peserta_jabatan[idx].strip() if idx < len(peserta_jabatan) else ''
                cursor.execute('''
                    INSERT INTO spj_peserta (spj_id, nama, nip, pangkat_golongan, jabatan, urutan)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (spj_id, nama.strip(), nip, pangkat, jabatan, idx + 1))

        # Re-sync Biaya
        cursor.execute('DELETE FROM spj_biaya WHERE spj_id = ?', (spj_id,))
        biaya_jenis = request.form.getlist('biaya_jenis[]')
        biaya_keterangan = request.form.getlist('biaya_keterangan[]')
        biaya_kuantitas = request.form.getlist('biaya_kuantitas[]')
        biaya_satuan = request.form.getlist('biaya_satuan[]')
        biaya_tarif = request.form.getlist('biaya_tarif[]')

        for idx, jenis_b in enumerate(biaya_jenis):
            ket = biaya_keterangan[idx].strip() if idx < len(biaya_keterangan) else ''
            if ket:
                qty = float(biaya_kuantitas[idx]) if idx < len(biaya_kuantitas) and biaya_kuantitas[idx] else 1.0
                sat = biaya_satuan[idx].strip() if idx < len(biaya_satuan) else 'Hari'
                tarif = float(biaya_tarif[idx]) if idx < len(biaya_tarif) and biaya_tarif[idx] else 0.0
                total = qty * tarif
                is_riil = 1 if request.form.get(f'biaya_riil_{idx}') == '1' else 0

                cursor.execute('''
                    INSERT INTO spj_biaya (spj_id, jenis_biaya, keterangan, kuantitas, satuan, tarif, total, termasuk_riil)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (spj_id, jenis_b, ket, qty, sat, tarif, total, is_riil))

        conn.commit()
        conn.close()

        flash('Perubahan data SPJ berhasil disimpan!', 'success')
        return redirect(url_for('spj_detail', spj_id=spj_id))

    peserta_list = conn.execute('SELECT * FROM spj_peserta WHERE spj_id = ? ORDER BY urutan ASC', (spj_id,)).fetchall()
    biaya_list = conn.execute('SELECT * FROM spj_biaya WHERE spj_id = ? ORDER BY id ASC', (spj_id,)).fetchall()
    conn.close()

    return render_template('spj_form.html',
        spj=spj,
        peserta_list=peserta_list,
        biaya_list=biaya_list,
        today_date=spj['tanggal_berangkat'],
        default_nomor_spt=spj['nomor_spt'],
        default_nomor_sppd=spj['nomor_sppd'],
        default_dasar_hukum=spj['dasar_hukum']
    )

# ----------------- DELETE SPJ -----------------
@app.route('/spj/<int:spj_id>/delete', methods=['POST'])
@login_required
def spj_delete(spj_id):
    conn = get_db()
    conn.execute('DELETE FROM spj_peserta WHERE spj_id = ?', (spj_id,))
    conn.execute('DELETE FROM spj_biaya WHERE spj_id = ?', (spj_id,))
    conn.execute('DELETE FROM spj_laporan WHERE spj_id = ?', (spj_id,))
    conn.execute('DELETE FROM spj WHERE id = ?', (spj_id,))
    conn.commit()
    conn.close()
    flash('Dokumen SPJ berhasil dihapus.', 'info')
    return redirect(url_for('spj_list'))

# ----------------- SPJ DETAIL & VIEWER -----------------
@app.route('/spj/<int:spj_id>')
@login_required
def spj_detail(spj_id):
    conn = get_db()
    spj = conn.execute('SELECT * FROM spj WHERE id = ?', (spj_id,)).fetchone()
    if not spj:
        conn.close()
        abort(404)

    peserta = conn.execute('SELECT * FROM spj_peserta WHERE spj_id = ? ORDER BY urutan ASC', (spj_id,)).fetchall()
    biaya = conn.execute('SELECT * FROM spj_biaya WHERE spj_id = ? ORDER BY id ASC', (spj_id,)).fetchall()
    laporan = conn.execute('SELECT * FROM spj_laporan WHERE spj_id = ?', (spj_id,)).fetchone()
    conn.close()

    s = get_settings()
    laporan_defaults = json.loads(s.get('template_laporan', '{}'))
    total_biaya = sum(b['total'] for b in biaya)

    return render_template('spj_detail.html',
        spj=spj,
        peserta=peserta,
        biaya=biaya,
        laporan=laporan,
        s=s,
        laporan_defaults=laporan_defaults,
        total_biaya=total_biaya
    )

# ----------------- UPDATE LAPORAN NARASI -----------------
@app.route('/spj/<int:spj_id>/laporan/update', methods=['POST'])
@login_required
def update_laporan(spj_id):
    conn = get_db()
    kegiatan = request.form.get('kegiatan_dilaksanakan', '')
    hasil = request.form.get('hasil_kegiatan', '')
    kesimpulan = request.form.get('kesimpulan_saran', '')

    cursor = conn.cursor()
    cursor.execute('SELECT id FROM spj_laporan WHERE spj_id = ?', (spj_id,))
    row = cursor.fetchone()
    if row:
        cursor.execute('''
            UPDATE spj_laporan SET kegiatan_dilaksanakan = ?, hasil_kegiatan = ?, kesimpulan_saran = ?
            WHERE spj_id = ?
        ''', (kegiatan, hasil, kesimpulan, spj_id))
    else:
        cursor.execute('''
            INSERT INTO spj_laporan (spj_id, kegiatan_dilaksanakan, hasil_kegiatan, kesimpulan_saran)
            VALUES (?, ?, ?, ?)
        ''', (spj_id, kegiatan, hasil, kesimpulan))

    conn.commit()
    conn.close()
    flash('Narasi Laporan Hasil Perjalanan Dinas berhasil diperbarui!', 'success')
    return redirect(url_for('spj_detail', spj_id=spj_id))

# ----------------- PRINTING ROUTES -----------------
@app.route('/spj/<int:spj_id>/cetak/spt')
@login_required
def cetak_spt(spj_id):
    conn = get_db()
    spj = conn.execute('SELECT * FROM spj WHERE id = ?', (spj_id,)).fetchone()
    peserta = conn.execute('SELECT * FROM spj_peserta WHERE spj_id = ? ORDER BY urutan ASC', (spj_id,)).fetchall()
    conn.close()
    s = get_settings()
    return render_template('print/spt_print.html', spj=spj, peserta=peserta, s=s)

@app.route('/spj/<int:spj_id>/cetak/pengeluaran-riil')
@login_required
def cetak_pengeluaran_riil(spj_id):
    conn = get_db()
    spj = conn.execute('SELECT * FROM spj WHERE id = ?', (spj_id,)).fetchone()
    peserta = conn.execute('SELECT * FROM spj_peserta WHERE spj_id = ? ORDER BY urutan ASC', (spj_id,)).fetchall()
    biaya = conn.execute('SELECT * FROM spj_biaya WHERE spj_id = ? ORDER BY id ASC', (spj_id,)).fetchall()
    conn.close()
    s = get_settings()
    return render_template('print/pengeluaran_riil_print.html', spj=spj, peserta=peserta, biaya=biaya, s=s)

@app.route('/spj/<int:spj_id>/cetak/kwitansi')
@login_required
def cetak_kwitansi(spj_id):
    conn = get_db()
    spj = conn.execute('SELECT * FROM spj WHERE id = ?', (spj_id,)).fetchone()
    peserta = conn.execute('SELECT * FROM spj_peserta WHERE spj_id = ? ORDER BY urutan ASC', (spj_id,)).fetchall()
    biaya = conn.execute('SELECT * FROM spj_biaya WHERE spj_id = ? ORDER BY id ASC', (spj_id,)).fetchall()
    conn.close()
    s = get_settings()
    total_biaya = sum(b['total'] for b in biaya)
    return render_template('print/kwitansi_print.html', spj=spj, peserta=peserta, biaya=biaya, total_biaya=total_biaya, s=s)

@app.route('/spj/<int:spj_id>/cetak/rincian-biaya')
@login_required
def cetak_rincian_biaya(spj_id):
    conn = get_db()
    spj = conn.execute('SELECT * FROM spj WHERE id = ?', (spj_id,)).fetchone()
    peserta = conn.execute('SELECT * FROM spj_peserta WHERE spj_id = ? ORDER BY urutan ASC', (spj_id,)).fetchall()
    biaya = conn.execute('SELECT * FROM spj_biaya WHERE spj_id = ? ORDER BY id ASC', (spj_id,)).fetchall()
    conn.close()
    s = get_settings()
    return render_template('print/rincian_biaya_print.html', spj=spj, peserta=peserta, biaya=biaya, s=s)

@app.route('/spj/<int:spj_id>/cetak/laporan')
@login_required
def cetak_laporan(spj_id):
    conn = get_db()
    spj = conn.execute('SELECT * FROM spj WHERE id = ?', (spj_id,)).fetchone()
    peserta = conn.execute('SELECT * FROM spj_peserta WHERE spj_id = ? ORDER BY urutan ASC', (spj_id,)).fetchall()
    laporan = conn.execute('SELECT * FROM spj_laporan WHERE spj_id = ?', (spj_id,)).fetchone()
    conn.close()
    s = get_settings()
    laporan_defaults = json.loads(s.get('template_laporan', '{}'))
    return render_template('print/laporan_print.html', spj=spj, peserta=peserta, laporan=laporan, s=s, laporan_defaults=laporan_defaults)

@app.route('/spj/<int:spj_id>/cetak/semua')
@login_required
def cetak_semua(spj_id):
    conn = get_db()
    spj = conn.execute('SELECT * FROM spj WHERE id = ?', (spj_id,)).fetchone()
    peserta = conn.execute('SELECT * FROM spj_peserta WHERE spj_id = ? ORDER BY urutan ASC', (spj_id,)).fetchall()
    biaya = conn.execute('SELECT * FROM spj_biaya WHERE spj_id = ? ORDER BY id ASC', (spj_id,)).fetchall()
    laporan = conn.execute('SELECT * FROM spj_laporan WHERE spj_id = ?', (spj_id,)).fetchone()
    conn.close()
    s = get_settings()
    laporan_defaults = json.loads(s.get('template_laporan', '{}'))
    total_biaya = sum(b['total'] for b in biaya)

    return render_template('print/semua_print.html',
        spj=spj,
        peserta=peserta,
        biaya=biaya,
        laporan=laporan,
        s=s,
        laporan_defaults=laporan_defaults,
        total_biaya=total_biaya
    )

# ----------------- SETTINGS & TEMPLATES -----------------
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings_view():
    if request.method == 'POST':
        # Update text settings
        keys = [
            'instansi_nama_induk', 'instansi_nama', 'instansi_alamat', 'instansi_kontak', 'instansi_kota',
            'pejabat_kadis_nama', 'pejabat_kadis_nip', 'pejabat_kadis_pangkat', 'pejabat_kadis_jabatan',
            'pejabat_ppk_nama', 'pejabat_ppk_nip', 'pejabat_ppk_pangkat', 'pejabat_ppk_jabatan',
            'pejabat_bendahara_nama', 'pejabat_bendahara_nip', 'pejabat_bendahara_pangkat', 'pejabat_bendahara_jabatan',
            'template_spt_kadis', 'template_spt_staf', 'template_pengeluaran_riil', 'template_kwitansi', 'template_rincian_biaya'
        ]
        data = {}
        for k in keys:
            data[k] = request.form.get(k, '').strip()

        # Update JSON template for laporan
        laporan_json = {
            "pendahuluan": request.form.get('laporan_pendahuluan', ''),
            "kegiatan": request.form.get('laporan_kegiatan', ''),
            "hasil": request.form.get('laporan_hasil', ''),
            "kesimpulan": request.form.get('laporan_kesimpulan', '')
        }
        data['template_laporan'] = json.dumps(laporan_json)

        update_settings(data)
        flash('Pengaturan template, kop dinas, dan data pejabat berhasil disimpan!', 'success')
        return redirect(url_for('settings_view'))

    s = get_settings()
    laporan_defaults = json.loads(s.get('template_laporan', '{}'))

    return render_template('settings.html', s=s, laporan_defaults=laporan_defaults)

# ----------------- INIT & RUN -----------------
init_db()
create_sample_data()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[INFO] Server SPJ Perjalanan Dinas running on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
