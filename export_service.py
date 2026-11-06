"""
export_service.py - Modul Ekspor Dokumen SPJ ke Microsoft Word (.docx) & Microsoft Excel (.xlsx)

Standar Tata Naskah Dinas Pemerintah Daerah:
- Kertas: F4 / Folio (215 mm x 330 mm)
- Margin: Pias Atas 2 cm, Pias Bawah 2 cm, Pias Kiri 3 cm, Pias Kanan 2 cm
  Lebar Area Cetak = 21.5 - 3.0 - 2.0 = 16.5 cm
- Font: Arial di seluruh dokumen
  * Kop Pemda: Arial 14pt, Bold, All Caps (atau sesuai pengaturan size_induk)
  * Kop Satker/Dinas: Arial 18pt, Bold, All Caps (atau sesuai pengaturan size_nama)
  * Alamat & Kontak: Arial 11pt, Normal
  * Judul Dokumen: Arial 12pt, Bold, All Caps, Center (Bergaris Bawah untuk SPT, Kwitansi, Pengeluaran Riil, Laporan; Tanpa Garis Bawah untuk SPD)
  * Nomor Dokumen: Arial 12pt, Normal, Center, tepat di bawah judul
  * Batang Tubuh / Konsiderans: Arial 12pt, Normal, Justified
  * Tabel Rincian / Data: Arial 11pt (bisa 10pt jika padat)
  * Penandatanganan: Arial 12pt. Nama Pejabat Bold, Kapital, TANPA GARIS BAWAH.
"""

import os
import io
import copy
import zipfile
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

import docx
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn

from helpers import (
    format_rupiah,
    terbilang,
    terbilang_kata,
    format_tanggal,
    clean_uraian,
    format_nomor_spasi
)

# ----------------- HELPER NORMALISASI DATA -----------------

def to_dict(obj):
    """Konversi sqlite3.Row atau object mapping ke Python dict murni agar aman menggunakan .get()"""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    try:
        return dict(obj)
    except Exception:
        return obj

# ----------------- HELPER STYLING DOCX -----------------

def setup_docx_f4_page(doc):
    """
    Konfigurasi ukuran kertas F4 (215 x 330 mm) dengan margin standar Pemda:
    Atas: 2.0 cm, Bawah: 2.0 cm, Kiri: 3.0 cm, Kanan: 2.0 cm.
    Default font: Arial 12pt.
    """
    section = doc.sections[0]
    section.page_width = Cm(21.5)
    section.page_height = Cm(33.0)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(2.0)

    # Set default normal style ke Arial 12pt
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(12)
    font.color.rgb = RGBColor(0, 0, 0)
    return section

def add_run_arial(paragraph, text="", size_pt=12, bold=False, italic=False, underline=False):
    """
    Menambahkan run teks dengan font Arial murni (ascii, hAnsi, cs) agar konsisten di semua versi Word.
    """
    run = paragraph.add_run(text)
    run.font.name = "Arial"
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.italic = italic
    run.font.underline = underline

    # Tambahkan rFonts eksplisit untuk Word
    rPr = run._r.get_or_add_rPr()
    existing_rFonts = rPr.find(qn('w:rFonts'))
    if existing_rFonts is not None:
        rPr.remove(existing_rFonts)
    rFonts = parse_xml(f'<w:rFonts {nsdecls("w")} w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>')
    rPr.append(rFonts)
    return run

def set_cell_margins(cell, top=60, bottom=60, left=100, right=100):
    """Set padding dalam sel tabel (dalam dxa, 20 dxa = 1 pt)"""
    tcPr = cell._tc.get_or_add_tcPr()
    existing_mar = tcPr.find(qn('w:tcMar'))
    if existing_mar is not None:
        tcPr.remove(existing_mar)
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}>'
                      f'<w:top w:w="{top}" w:type="dxa"/>'
                      f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
                      f'<w:left w:w="{left}" w:type="dxa"/>'
                      f'<w:right w:w="{right}" w:type="dxa"/>'
                      f'</w:tcMar>')
    tcPr.append(tcMar)

def set_cell_border(cell, **kwargs):
    """Set border per sisi: top, bottom, left, right, insideH, insideV"""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    existing_borders = tcPr.find(qn('w:tcBorders'))
    if existing_borders is not None:
        tcPr.remove(existing_borders)
    tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}/>')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        edge_data = kwargs.get(edge)
        if edge_data:
            tag = f'<w:{edge} {nsdecls("w")} '
            for key, val in edge_data.items():
                tag += f'w:{key}="{val}" '
            tag += '/>'
            tcBorders.append(parse_xml(tag))
    tcPr.append(tcBorders)

def set_cell_shading(cell, color_hex="F2F2F2"):
    """Set background color sel tabel"""
    tcPr = cell._tc.get_or_add_tcPr()
    existing_shd = tcPr.find(qn('w:shd'))
    if existing_shd is not None:
        tcPr.remove(existing_shd)
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    tcPr.append(shd)

def add_kop_surat_docx(doc, s, jenis_spt='staf', force_kop=None, root_path=''):
    """
    Tambahkan Kop Surat resmi ke dokumen Word:
    - Simetri 3 Kolom jika ada logo: Kolom 0 (Logo 2.2 cm), Kolom 1 (Teks Tengah 12.1 cm), Kolom 2 (Spacer 2.2 cm)
    - Teks Kop: Pemda (Arial 14pt Bold Caps), Dinas (Arial 18pt Bold Caps), Alamat & Kontak (Arial 11pt Normal)
    - Garis ganda pembatas kop surat (double underline border)
    """
    s = to_dict(s)
    eff_jenis = force_kop if force_kop else (jenis_spt or 'staf')
    is_kadis = (eff_jenis == 'kadis')
    prefix = 'kop_kadis_' if is_kadis else 'kop_staf_'

    instansi_induk = s.get(f'{prefix}instansi_induk') or s.get('instansi_nama_induk', 'PEMERINTAH KABUPATEN KEPAHIANG')
    instansi_nama = s.get(f'{prefix}instansi_nama') or s.get('instansi_nama', 'DINAS KEPENDUDUKAN DAN PENCATATAN SIPIL')
    alamat = s.get(f'{prefix}alamat') or s.get('instansi_alamat', 'Jalan Komplek Perkantoran Kelobak Kode Pos 39172')
    kontak = s.get(f'{prefix}kontak') or s.get('instansi_kontak', 'KEPAHIANG – BENGKULU')
    logo_rel = s.get(f'{prefix}logo', '')

    raw_sz_induk = str(s.get(f'{prefix}size_induk') or '14pt').replace('pt', '').strip()
    raw_sz_nama = str(s.get(f'{prefix}size_nama') or '18pt').replace('pt', '').strip()
    try:
        sz_induk = float(raw_sz_induk)
    except Exception:
        sz_induk = 14.0
    try:
        sz_nama = float(raw_sz_nama)
    except Exception:
        sz_nama = 18.0

    logo_path = os.path.join(root_path, logo_rel.lstrip('/\\')) if logo_rel else ''
    has_logo = bool(logo_path and os.path.exists(logo_path))

    if has_logo:
        # 3 Kolom untuk simetri sempurna teks di tengah halaman
        table = doc.add_table(rows=1, cols=3)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False

        col_w_logo = Cm(2.2)
        col_w_text = Cm(12.1)
        col_w_spacer = Cm(2.2)

        table.columns[0].width = col_w_logo
        table.columns[1].width = col_w_text
        table.columns[2].width = col_w_spacer

        cell_logo = table.cell(0, 0)
        cell_text = table.cell(0, 1)
        cell_spacer = table.cell(0, 2)

        cell_logo.width = col_w_logo
        cell_text.width = col_w_text
        cell_spacer.width = col_w_spacer

        cell_logo.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        cell_text.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        cell_spacer.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

        set_cell_margins(cell_logo, top=0, bottom=40, left=0, right=40)
        set_cell_margins(cell_text, top=0, bottom=40, left=40, right=40)
        set_cell_margins(cell_spacer, top=0, bottom=40, left=40, right=0)

        # Insert Logo
        p_logo = cell_logo.paragraphs[0]
        p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_logo.paragraph_format.space_before = Pt(0)
        p_logo.paragraph_format.space_after = Pt(0)
        run_logo = p_logo.add_run()
        run_logo.add_picture(logo_path, width=Cm(2.0))

        # Spacer Cell
        p_spc = cell_spacer.paragraphs[0]
        p_spc.text = ""
        p_spc.paragraph_format.space_before = Pt(0)
        p_spc.paragraph_format.space_after = Pt(0)

    else:
        # 1 Kolom teks tengah jika tanpa logo
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        table.columns[0].width = Cm(16.5)
        cell_text = table.cell(0, 0)
        cell_text.width = Cm(16.5)
        cell_text.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_margins(cell_text, top=0, bottom=40, left=0, right=0)

    # Teks Kop Surat
    p_text = cell_text.paragraphs[0]
    p_text.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_text.paragraph_format.line_spacing = 1.15
    p_text.paragraph_format.space_before = Pt(0)
    p_text.paragraph_format.space_after = Pt(0)

    # Baris 1: Pemda (Arial 14 Bold)
    add_run_arial(p_text, instansi_induk.upper() + "\n", size_pt=sz_induk, bold=True)

    # Baris 2: Dinas (Arial 18 Bold)
    add_run_arial(p_text, instansi_nama.upper() + "\n", size_pt=sz_nama, bold=True)

    # Baris 3: Alamat & Kontak (Arial 11 Normal)
    alamat_kontak = f"{alamat}\n{kontak}" if kontak else alamat
    add_run_arial(p_text, alamat_kontak, size_pt=11, bold=False)

    # Garis Ganda Pembatas Kop Surat (Double Line Border)
    p_line = doc.add_paragraph()
    p_line.paragraph_format.line_spacing = Pt(1)
    p_line.paragraph_format.space_before = Pt(2)
    p_line.paragraph_format.space_after = Pt(12)
    r_empty = p_line.add_run()
    r_empty.font.size = Pt(1)
    pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="double" w:sz="18" w:space="1" w:color="000000"/></w:pBdr>')
    p_line._p.get_or_add_pPr().append(pBdr)

def format_tujuan_lengkap(spj):
    """
    Format teks tujuan konsisten dengan pratinjau HTML:
    instansi tujuan dulu baru tujuan (kota/kecamatan).
    """
    spj = to_dict(spj)
    instansi = (spj.get('instansi_tujuan') or '').rstrip('. ').strip()
    tujuan = (spj.get('tujuan') or '').rstrip('. ').strip()

    if instansi and instansi != tujuan:
        return f"{instansi} di {tujuan}"
    elif instansi:
        return instansi
    else:
        return tujuan

# ----------------- 1. EXCEL EXPORTERS -----------------

def export_spd_excel(spj, peserta_list, s, tpl_path='template spj/template spd.xlsx'):
    """
    Ekspor dokumen SPD ke Microsoft Excel (.xlsx) menggunakan template resmi 10 poin.
    Tiap pelaksana dibuatkan sheet terpisah jika peserta lebih dari 1.
    """
    spj = to_dict(spj)
    s = to_dict(s)
    peserta_list = [to_dict(p) for p in (peserta_list or [])]

    if not os.path.exists(tpl_path):
        raise FileNotFoundError(f"Template Excel SPD tidak ditemukan di: {tpl_path}")

    wb = openpyxl.load_workbook(tpl_path)
    base_sheet = wb.active

    target_peserta = peserta_list if peserta_list else [{
        'nama': s.get('pejabat_kadis_nama', ''),
        'nip': s.get('pejabat_kadis_nip', ''),
        'pangkat_golongan': s.get('pejabat_kadis_pangkat', ''),
        'jabatan': s.get('pejabat_kadis_jabatan', '')
    }]

    tujuan_lengkap = format_tujuan_lengkap(spj)
    nomor_sppd = spj.get('nomor_sppd') or '800/      /SPPD/Dukcapil-Kph/2026'

    # Siapkan data penandatangan
    is_kadis = (spj.get('jenis_spt') == 'kadis')
    if is_kadis and spj.get('spt_penandatangan_nama'):
        ttd_an = spj.get('spt_penandatangan_an') or s.get('pejabat_ttd_kadis_an')
        ttd_jabatan = spj.get('spt_penandatangan_jabatan') or s.get('pejabat_ttd_kadis_jabatan') or 'Sekretaris Daerah'
        ttd_nama = spj.get('spt_penandatangan_nama') or s.get('pejabat_ttd_kadis_nama')
        ttd_pangkat = spj.get('spt_penandatangan_pangkat') or s.get('pejabat_ttd_kadis_pangkat') or ''
        ttd_nip = spj.get('spt_penandatangan_nip') or s.get('pejabat_ttd_kadis_nip') or ''
    else:
        ttd_an = None
        ttd_jabatan = "Pengguna Anggaran / Kuasa Pengguna Anggaran"
        ttd_nama = s.get('pejabat_kadis_nama', '')
        ttd_pangkat = s.get('pejabat_kadis_pangkat', '')
        ttd_nip = s.get('pejabat_kadis_nip', '')

    for idx, p in enumerate(target_peserta):
        if idx == 0:
            ws = base_sheet
        else:
            ws = wb.copy_worksheet(base_sheet)

        clean_nama = "".join([c for c in p['nama'] if c.isalnum() or c in ' -_'])[:25].strip()
        ws.title = f"SPD - {clean_nama}" if clean_nama else f"SPD {idx+1}"

        # 1. Nomor Surat
        ws['A8'] = f"Nomor : {nomor_sppd}"

        # 2. Butir 1 s.d 10 Format Resmi
        ws['E10'] = f"KEPALA {s.get('instansi_nama', 'DINAS KEPENDUDUKAN DAN PENCATATAN SIPIL')} {s.get('instansi_nama_induk', 'PEMERINTAH KABUPATEN KEPAHIANG')}"
        ws['E11'] = f"{p['nama']} / {p.get('nip') or '-'}"
        ws['F12'] = p.get('pangkat_golongan') or '-'
        ws['F13'] = p.get('jabatan') or '-'
        ws['F14'] = "-"
        ws['E15'] = spj.get('maksud') or ''
        ws['E17'] = spj.get('angkutan') or 'Kendaraan Roda Empat'
        ws['F18'] = "Kepahiang"
        ws['F19'] = tujuan_lengkap
        ws['F20'] = f"{spj.get('lama_hari')} ( {terbilang_kata(spj.get('lama_hari'))} ) hari"
        ws['F21'] = format_tanggal(spj.get('tanggal_berangkat'))
        ws['F22'] = format_tanggal(spj.get('tanggal_pulang'))

        # Butir 8. Pengikut (hardcoded strip-strip)
        for r_num in range(24, 28):
            ws[f'E{r_num}'] = "-"
            ws[f'I{r_num}'] = "-"

        # Butir 9 & 10
        ws['F29'] = s.get('instansi_nama', 'Dinas Kependudukan dan Pencatatan Sipil')
        ws['F30'] = spj.get('mata_anggaran') or ''
        ws['E31'] = "-"

        # Tanda Tangan
        kota_terbit = s.get('kop_kadis_kota') or s.get('instansi_kota') or 'Kepahiang'
        tgl_terbit = format_tanggal(spj.get('tanggal_spt') or spj.get('tanggal_berangkat'))
        ws['H34'] = f": {kota_terbit}"
        ws['H35'] = f": {tgl_terbit}"

        if ttd_an:
            ws['E37'] = ttd_an
            ws['E38'] = ttd_jabatan
        else:
            ws['E37'] = "Pengguna Anggaran"
            ws['E38'] = "/ Kuasa Pengguna Anggaran"

        ws['E42'] = ttd_nama
        ws['E43'] = ttd_pangkat
        ws['E44'] = f"NIP. {ttd_nip}" if ttd_nip else "-"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

def export_rincian_biaya_excel(spj, peserta_list, biaya_list, s):
    """
    Ekspor lembar Rincian Biaya Perjalanan Dinas ke Microsoft Excel (.xlsx)
    Format multi-sheet per pelaksana.
    """
    spj = to_dict(spj)
    s = to_dict(s)
    peserta_list = [to_dict(p) for p in (peserta_list or [])]
    biaya_list = [to_dict(b) for b in (biaya_list or [])]

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    target_peserta = peserta_list if peserta_list else [{
        'nama': s.get('pejabat_kadis_nama', ''),
        'nip': s.get('pejabat_kadis_nip', ''),
        'pangkat_golongan': s.get('pejabat_kadis_pangkat', ''),
        'jabatan': s.get('pejabat_kadis_jabatan', '')
    }]

    font_title = Font(name='Arial', size=12, bold=True)
    font_bold = Font(name='Arial', size=11, bold=True)
    font_regular = Font(name='Arial', size=11)
    font_small = Font(name='Arial', size=9, italic=True)
    border_thin = Side(border_style="thin", color="000000")
    box_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)

    for idx, p in enumerate(target_peserta):
        clean_nama = "".join([c for c in p['nama'] if c.isalnum() or c in ' -_'])[:25].strip()
        sheet_title = f"Rincian - {clean_nama}" if clean_nama else f"Rincian {idx+1}"
        ws = wb.create_sheet(title=sheet_title)

        ws.column_dimensions['A'].width = 6
        ws.column_dimensions['B'].width = 38
        ws.column_dimensions['C'].width = 18
        ws.column_dimensions['D'].width = 18

        # Judul
        ws['A2'] = "RINCIAN BIAYA PERJALANAN DINAS"
        ws['A2'].font = font_title
        ws.merge_cells('A2:D2')
        ws['A2'].alignment = Alignment(horizontal='center')

        # Lampiran SPT & Tanggal
        ws['A4'] = "Lampiran SPT Nomor"
        ws['A4'].font = font_regular
        ws['B4'] = f": {spj.get('nomor_spt')}"
        ws['B4'].font = font_regular

        ws['A5'] = "Tanggal Berangkat"
        ws['A5'].font = font_regular
        ws['B5'] = f": {format_tanggal(spj.get('tanggal_berangkat'))}"
        ws['B5'].font = font_regular

        ws['A6'] = "Nama Pelaksana"
        ws['A6'].font = font_regular
        ws['B6'] = f": {p['nama']}"
        ws['B6'].font = font_bold

        # Header Tabel
        headers = ["No.", "Perincian Biaya", "Jumlah (Rp)", "Keterangan"]
        for c_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=8, column=c_idx, value=h)
            cell.font = font_bold
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = box_border
            cell.fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')

        # Filter biaya peserta ini
        pelaksana_biaya = [b for b in biaya_list if b.get('peserta_nama') == p['nama'] or not b.get('peserta_nama') or len(target_peserta) == 1]
        current_r = 9
        subtotal = 0.0

        for b_idx, b in enumerate(pelaksana_biaya, 1):
            val_total = float(b.get('total') or 0)
            subtotal += val_total

            ws.cell(row=current_r, column=1, value=f"{b_idx}.").alignment = Alignment(horizontal='center')
            ws.cell(row=current_r, column=2, value=clean_uraian(b.get('keterangan'), p['nama']))

            c_amt = ws.cell(row=current_r, column=3, value=val_total)
            c_amt.number_format = '#,##0'
            c_amt.alignment = Alignment(horizontal='right')

            ket_str = "Pengeluaran Riil" if b.get('termasuk_riil') else "Bukti Terlampir"
            ws.cell(row=current_r, column=4, value=ket_str).alignment = Alignment(horizontal='center')

            for col in range(1, 5):
                ws.cell(row=current_r, column=col).font = font_regular
                ws.cell(row=current_r, column=col).border = box_border

            current_r += 1

        # Baris Jumlah Total
        ws.cell(row=current_r, column=1, value="")
        ws.cell(row=current_r, column=2, value="JUMLAH").font = font_bold
        ws.cell(row=current_r, column=2).alignment = Alignment(horizontal='center')

        c_tot = ws.cell(row=current_r, column=3, value=subtotal)
        c_tot.font = font_bold
        c_tot.number_format = '#,##0'
        c_tot.alignment = Alignment(horizontal='right')

        ws.cell(row=current_r, column=4, value="")

        for col in range(1, 5):
            cell = ws.cell(row=current_r, column=col)
            cell.border = box_border
            cell.fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')

        current_r += 2
        ws.cell(row=current_r, column=1, value=f"Terbilang : {terbilang(subtotal)}").font = font_small
        ws.merge_cells(start_row=current_r, start_column=1, end_row=current_r, end_column=4)

        # Tanda Tangan
        current_r += 3
        kota = s.get('instansi_kota') or 'Kepahiang'
        tgl_pulang = format_tanggal(spj.get('tanggal_pulang'))

        ws.cell(row=current_r, column=1, value="Bendahara Pengeluaran,").font = font_bold
        ws.cell(row=current_r, column=3, value=f"{kota}, {tgl_pulang}").font = font_regular
        current_r += 1
        ws.cell(row=current_r, column=3, value="Pengguna Anggaran / KPA,").font = font_bold

        current_r += 4
        ws.cell(row=current_r, column=1, value=s.get('pejabat_bendahara_nama', '')).font = font_bold
        ws.cell(row=current_r, column=3, value=s.get('pejabat_kadis_nama', '')).font = font_bold

        current_r += 1
        ws.cell(row=current_r, column=1, value=f"NIP. {s.get('pejabat_bendahara_nip', '')}").font = font_regular
        ws.cell(row=current_r, column=3, value=f"NIP. {s.get('pejabat_kadis_nip', '')}").font = font_regular

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

def export_rekap_excel(spj, peserta_list, biaya_list, s):
    """
    Ekspor tabel rekapitulasi pembayaran SPJ per orang ke Microsoft Excel (.xlsx)
    """
    spj = to_dict(spj)
    s = to_dict(s)
    peserta_list = [to_dict(p) for p in (peserta_list or [])]
    biaya_list = [to_dict(b) for b in (biaya_list or [])]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rekapitulasi SPJ"

    font_title = Font(name='Arial', size=14, bold=True)
    font_bold = Font(name='Arial', size=11, bold=True)
    font_regular = Font(name='Arial', size=11)
    fill_header = PatternFill(start_color='E2E8F0', end_color='E2E8F0', fill_type='solid')
    border_thin = Side(border_style="thin", color="000000")
    box_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)

    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 24
    ws.column_dimensions['D'].width = 22
    ws.column_dimensions['E'].width = 20
    ws.column_dimensions['F'].width = 20

    ws['A1'] = "REKAPITULASI BIAYA PERJALANAN DINAS"
    ws['A1'].font = font_title
    ws['A2'] = f"Nomor SPT : {spj.get('nomor_spt')}  |  Kegiatan: {spj.get('maksud')}"
    ws['A2'].font = font_regular

    start_r = 4
    headers = ["No", "Nama Pegawai", "NIP", "Jabatan", "Total Biaya (Rp)", "Tanda Tangan"]
    for c_idx, h in enumerate(headers, 1):
        c = ws.cell(row=start_r, column=c_idx, value=h)
        c.font = font_bold
        c.fill = fill_header
        c.alignment = Alignment(horizontal='center', vertical='center')
        c.border = box_border

    curr_r = start_r + 1
    for i, p in enumerate(peserta_list, 1):
        subtotal = sum(float(b.get('total') or 0) for b in biaya_list if b.get('peserta_nama') == p['nama'] or not b.get('peserta_nama') or len(peserta_list) == 1)

        ws.cell(row=curr_r, column=1, value=i).alignment = Alignment(horizontal='center')
        ws.cell(row=curr_r, column=2, value=p['nama'])
        ws.cell(row=curr_r, column=3, value=p.get('nip') or '-')
        ws.cell(row=curr_r, column=4, value=p.get('jabatan') or '-')
        c_sub = ws.cell(row=curr_r, column=5, value=subtotal)
        c_sub.number_format = '#,##0'
        ws.cell(row=curr_r, column=6, value=f"{i}. ..............")

        for c in range(1, 7):
            ws.cell(row=curr_r, column=c).font = font_regular
            ws.cell(row=curr_r, column=c).border = box_border
        curr_r += 1

    # Total keseluruhan
    ws.cell(row=curr_r, column=1, value="")
    ws.cell(row=curr_r, column=2, value="TOTAL KESELURUHAN").font = font_bold
    ws.cell(row=curr_r, column=2).alignment = Alignment(horizontal='right')
    c_tot = ws.cell(row=curr_r, column=5, value=f"=SUM(E{start_r+1}:E{curr_r-1})")
    c_tot.font = font_bold
    c_tot.number_format = '#,##0'

    for c in range(1, 7):
        ws.cell(row=curr_r, column=c).border = box_border

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

# ----------------- 2. WORD (DOCX) EXPORTERS -----------------

def export_spt_word(spj, peserta_list, s, root_path=''):
    """
    Ekspor Surat Tugas (SPT) ke Microsoft Word (.docx).
    100% Presisi dengan spt_print.html:
    - Kop Surat resmi (Kadis vs Staf) dengan 3-kolom simetris
    - Judul: SURAT TUGAS (Arial 12pt Bold Underline Center)
    - Nomor: Nomor: {nomor_spt} (Arial 12pt Center)
    - Dasar: Konsiderans Justified
    - Diktum: MENUGASKAN : (Arial 12pt Bold Center)
    - Kepada: Rincian Nama (Bold), NIP, Pangkat/Gol, Jabatan
    - Untuk: {maksud} yang bertempat di {instansi_tujuan} di {tujuan}.
    - Tanggal: Tanggal penugasan
    - Penutup: Teks resmi sesuai jenis SPT
    - Tanda Tangan: Dikeluarkan di, Pada Tanggal, Jabatan, Nama Bold TANPA Garis Bawah, Pangkat, NIP.
    """
    spj = to_dict(spj)
    s = to_dict(s)
    peserta_list = [to_dict(p) for p in (peserta_list or [])]

    doc = docx.Document()
    setup_docx_f4_page(doc)
    add_kop_surat_docx(doc, s, jenis_spt=spj.get('jenis_spt', 'staf'), root_path=root_path)

    # Judul Surat: SURAT TUGAS (underline per naskah dinas spt_print.html)
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(4)
    p_title.paragraph_format.space_after = Pt(2)
    add_run_arial(p_title, "SURAT TUGAS", size_pt=12, bold=True, underline=True)

    # Nomor Surat
    p_no = doc.add_paragraph()
    p_no.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_no.paragraph_format.space_after = Pt(12)
    add_run_arial(p_no, f"Nomor: {spj.get('nomor_spt')}", size_pt=12, bold=False)

    # 1. Tabel Dasar
    tbl_dasar = doc.add_table(rows=1, cols=3)
    tbl_dasar.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_dasar.autofit = False

    w_col0 = Cm(2.0)
    w_col1 = Cm(0.4)
    w_col2 = Cm(14.1)

    tbl_dasar.columns[0].width = w_col0
    tbl_dasar.columns[1].width = w_col1
    tbl_dasar.columns[2].width = w_col2

    c0, c1, c2 = tbl_dasar.rows[0].cells
    c0.width, c1.width, c2.width = w_col0, w_col1, w_col2
    set_cell_margins(c0, 30, 30, 0, 0)
    set_cell_margins(c1, 30, 30, 0, 0)
    set_cell_margins(c2, 30, 30, 0, 0)

    add_run_arial(c0.paragraphs[0], "Dasar", size_pt=12, bold=True)
    add_run_arial(c1.paragraphs[0], ":", size_pt=12)

    dasar_text = spj.get('dasar_hukum') or (s.get('template_spt_kadis') if spj.get('jenis_spt') == 'kadis' else s.get('template_spt_staf', ''))
    p_dasar_val = c2.paragraphs[0]
    p_dasar_val.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_dasar_val.paragraph_format.line_spacing = 1.35
    add_run_arial(p_dasar_val, dasar_text, size_pt=12)

    # 2. Diktum: MENUGASKAN :
    p_diktum = doc.add_paragraph()
    p_diktum.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_diktum.paragraph_format.space_before = Pt(10)
    p_diktum.paragraph_format.space_after = Pt(8)
    add_run_arial(p_diktum, "MENUGASKAN :", size_pt=12, bold=True)

    # 3. Tabel Kepada, Untuk, Tanggal
    tbl_body = doc.add_table(rows=3, cols=3)
    tbl_body.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_body.autofit = False

    tbl_body.columns[0].width = w_col0
    tbl_body.columns[1].width = w_col1
    tbl_body.columns[2].width = w_col2

    # --- Baris Kepada ---
    r_kpd = tbl_body.rows[0]
    r_kpd.cells[0].width, r_kpd.cells[1].width, r_kpd.cells[2].width = w_col0, w_col1, w_col2
    set_cell_margins(r_kpd.cells[0], 40, 40, 0, 0)
    set_cell_margins(r_kpd.cells[1], 40, 40, 0, 0)
    set_cell_margins(r_kpd.cells[2], 40, 40, 0, 0)

    add_run_arial(r_kpd.cells[0].paragraphs[0], "Kepada", size_pt=12, bold=True)
    add_run_arial(r_kpd.cells[1].paragraphs[0], ":", size_pt=12)

    cell_peserta = r_kpd.cells[2]
    target_peserta = peserta_list if peserta_list else [{
        'nama': s.get('pejabat_kadis_nama', ''),
        'nip': s.get('pejabat_kadis_nip', ''),
        'pangkat_golongan': s.get('pejabat_kadis_pangkat', ''),
        'jabatan': s.get('pejabat_kadis_jabatan', '')
    }]

    for idx, p in enumerate(target_peserta):
        p_p = cell_peserta.paragraphs[0] if idx == 0 else cell_peserta.add_paragraph()
        p_p.paragraph_format.space_after = Pt(6) if idx < len(target_peserta) - 1 else Pt(2)
        p_p.paragraph_format.line_spacing = 1.25

        prefix_no = f"{idx+1}. " if len(target_peserta) > 1 else ""
        add_run_arial(p_p, f"{prefix_no}Nama\t: ", size_pt=12)
        add_run_arial(p_p, f"{p['nama']}\n", size_pt=12, bold=True)

        indent_prefix = "\t  " if len(target_peserta) > 1 else ""
        add_run_arial(p_p, f"{indent_prefix}NIP\t: {p.get('nip') or '-'}\n", size_pt=12)
        add_run_arial(p_p, f"{indent_prefix}Pangkat\t: {p.get('pangkat_golongan') or '-'}\n", size_pt=12)
        add_run_arial(p_p, f"{indent_prefix}Jabatan\t: {p.get('jabatan') or '-'}", size_pt=12)

    # --- Baris Untuk ---
    r_unt = tbl_body.rows[1]
    r_unt.cells[0].width, r_unt.cells[1].width, r_unt.cells[2].width = w_col0, w_col1, w_col2
    set_cell_margins(r_unt.cells[0], 60, 40, 0, 0)
    set_cell_margins(r_unt.cells[1], 60, 40, 0, 0)
    set_cell_margins(r_unt.cells[2], 60, 40, 0, 0)

    add_run_arial(r_unt.cells[0].paragraphs[0], "Untuk", size_pt=12, bold=True)
    add_run_arial(r_unt.cells[1].paragraphs[0], ":", size_pt=12)

    tujuan_str = format_tujuan_lengkap(spj)
    maksud_str = (spj.get('maksud') or '').rstrip('. ')
    untuk_text = f"{maksud_str} yang bertempat di {tujuan_str}."

    p_unt = r_unt.cells[2].paragraphs[0]
    p_unt.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_unt.paragraph_format.line_spacing = 1.35
    add_run_arial(p_unt, untuk_text, size_pt=12)

    # --- Baris Tanggal ---
    r_tgl = tbl_body.rows[2]
    r_tgl.cells[0].width, r_tgl.cells[1].width, r_tgl.cells[2].width = w_col0, w_col1, w_col2
    set_cell_margins(r_tgl.cells[0], 50, 40, 0, 0)
    set_cell_margins(r_tgl.cells[1], 50, 40, 0, 0)
    set_cell_margins(r_tgl.cells[2], 50, 40, 0, 0)

    add_run_arial(r_tgl.cells[0].paragraphs[0], "Tanggal", size_pt=12, bold=True)
    add_run_arial(r_tgl.cells[1].paragraphs[0], ":", size_pt=12)

    tgl_berangkat = spj.get('tanggal_berangkat')
    tgl_pulang = spj.get('tanggal_pulang')
    if tgl_berangkat == tgl_pulang:
        jadwal_str = format_tanggal(tgl_berangkat)
    else:
        jadwal_str = f"{format_tanggal(tgl_berangkat)} s.d. {format_tanggal(tgl_pulang)} ({spj.get('lama_hari')} hari)"

    p_tgl = r_tgl.cells[2].paragraphs[0]
    add_run_arial(p_tgl, jadwal_str, size_pt=12)

    # 4. Penutup Surat
    p_penutup = doc.add_paragraph()
    p_penutup.paragraph_format.space_before = Pt(10)
    p_penutup.paragraph_format.space_after = Pt(14)
    p_penutup.paragraph_format.line_spacing = 1.35
    p_penutup.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    if spj.get('jenis_spt') == 'kadis':
        penutup_txt = "Demikian untuk dilaksanakan dengan penuh rasa tanggung jawab dan melaporkan hasilnya kepada Bupati Kepahiang."
    else:
        penutup_txt = "Demikian untuk dilaksanakan dengan penuh rasa tanggung jawab dan melaporkan hasilnya setelah selesai melaksanakan tugas."
    add_run_arial(p_penutup, penutup_txt, size_pt=12)

    # 5. Tanda Tangan (Sisi Kanan)
    tbl_ttd = doc.add_table(rows=1, cols=2)
    tbl_ttd.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_ttd.autofit = False
    tbl_ttd.columns[0].width = Cm(8.0)
    tbl_ttd.columns[1].width = Cm(8.5)

    c_ttd = tbl_ttd.rows[0].cells[1]
    c_ttd.width = Cm(8.5)
    set_cell_margins(c_ttd, top=0, bottom=0, left=40, right=0)

    p_ttd = c_ttd.paragraphs[0]
    p_ttd.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ttd.paragraph_format.line_spacing = 1.25

    kota_terbit = s.get('kop_kadis_kota') or s.get('instansi_kota') or 'Kepahiang'
    tgl_terbit = format_tanggal(spj.get('tanggal_spt') or spj.get('tanggal_berangkat'))

    add_run_arial(p_ttd, f"Dikeluarkan di : {kota_terbit}\nPada Tanggal : {tgl_terbit}\n", size_pt=12)

    if spj.get('jenis_spt') == 'kadis':
        ttd_an = spj.get('spt_penandatangan_an') or s.get('pejabat_ttd_kadis_an')
        ttd_jabatan = spj.get('spt_penandatangan_jabatan') or s.get('pejabat_ttd_kadis_jabatan') or 'Sekretaris Daerah'
        ttd_nama = spj.get('spt_penandatangan_nama') or s.get('pejabat_ttd_kadis_nama') or 'Dr. HARTONO, S.Pd., S.H,. M.Pd,. M.H'
        ttd_pangkat = spj.get('spt_penandatangan_pangkat') or s.get('pejabat_ttd_kadis_pangkat') or 'Pembina Utama Madya (IV/d)'
        ttd_nip = spj.get('spt_penandatangan_nip') or s.get('pejabat_ttd_kadis_nip') or '19701229 199409 1 001'

        if ttd_an:
            add_run_arial(p_ttd, f"{ttd_an}\n", size_pt=12, bold=True)
        add_run_arial(p_ttd, f"{ttd_jabatan}\n\n\n\n", size_pt=12, bold=True)
        # Nama Bold TANPA Garis Bawah
        add_run_arial(p_ttd, f"{ttd_nama}\n", size_pt=12, bold=True, underline=False)
        if ttd_pangkat:
            add_run_arial(p_ttd, f"{ttd_pangkat}\n", size_pt=12)
        if ttd_nip:
            add_run_arial(p_ttd, f"NIP. {ttd_nip}", size_pt=12)
    else:
        add_run_arial(p_ttd, "Kepala,\n\n\n\n", size_pt=12, bold=True)
        add_run_arial(p_ttd, f"{s.get('pejabat_kadis_nama', '')}\n", size_pt=12, bold=True, underline=False)
        if s.get('pejabat_kadis_pangkat'):
            add_run_arial(p_ttd, f"{s.get('pejabat_kadis_pangkat')}\n", size_pt=12)
        if s.get('pejabat_kadis_nip'):
            add_run_arial(p_ttd, f"NIP. {s.get('pejabat_kadis_nip')}", size_pt=12)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def export_spd_word(spj, peserta_list, s, root_path=''):
    """
    Ekspor dokumen Surat Perjalanan Dinas (SPD) ke Microsoft Word (.docx).
    100% Presisi dengan spd_print.html:
    - Kop Surat resmi
    - Judul: SURAT PERJALANAN DINAS (SPD) (Arial 12pt Bold Center, TANPA Underline sesuai standar naskah)
    - Nomor: Nomor : {nomor_sppd} (Arial 12pt Center)
    - Tabel 10 Poin Resmi:
      1. KEPALA {instansi_nama} {instansi_nama_induk}
      2. Nama / NIP Pegawai
      3. a. Pangkat/Gol, b. Jabatan/Instansi, c. Tingkat Biaya Perjalanan Dinas (-)
      4. Maksud Perjalanan Dinas
      5. Alat angkutan yang dipergunakan
      6. a. Kepahiang, b. {instansi_tujuan} di {tujuan}
      7. a. Lama hari, b. Tanggal berangkat, c. Tanggal pulang
      8. Pengikut: 4 baris strip (-)
      9. a. Instansi, b. Mata Anggaran
      10. Keterangan Lain - lain (-)
    - Tanda Tangan: Dikeluarkan di, Tanggal, Pengguna Anggaran / KPA, Nama Pejabat Bold TANPA Garis Bawah, Pangkat, NIP.
    """
    spj = to_dict(spj)
    s = to_dict(s)
    peserta_list = [to_dict(p) for p in (peserta_list or [])]

    doc = docx.Document()
    setup_docx_f4_page(doc)

    target_peserta = peserta_list if peserta_list else [{
        'nama': s.get('pejabat_kadis_nama', ''),
        'nip': s.get('pejabat_kadis_nip', ''),
        'pangkat_golongan': s.get('pejabat_kadis_pangkat', ''),
        'jabatan': s.get('pejabat_kadis_jabatan', '')
    }]

    tujuan_lengkap = format_tujuan_lengkap(spj)
    nomor_sppd = spj.get('nomor_sppd') or '800/      /SPPD/Dukcapil-Kph/2026'

    for idx, p in enumerate(target_peserta):
        if idx > 0:
            doc.add_page_break()

        add_kop_surat_docx(doc, s, jenis_spt=spj.get('jenis_spt', 'staf'), root_path=root_path)

        # Judul SPD (Tanpa Garis Bawah sesuai HTML line 93: text-decoration: none !important)
        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_title.paragraph_format.space_before = Pt(4)
        p_title.paragraph_format.space_after = Pt(2)
        add_run_arial(p_title, "SURAT PERJALANAN DINAS (SPD)", size_pt=12, bold=True, underline=False)

        # Nomor SPD
        p_no = doc.add_paragraph()
        p_no.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_no.paragraph_format.space_after = Pt(12)
        add_run_arial(p_no, f"Nomor : {nomor_sppd}", size_pt=12, bold=False)

        # Tabel SPD 10 Poin Resmi
        tbl = doc.add_table(rows=21, cols=3)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False

        w0, w1, w2 = Cm(0.9), Cm(6.8), Cm(8.8)
        tbl.columns[0].width = w0
        tbl.columns[1].width = w1
        tbl.columns[2].width = w2

        border_kw = {
            'top': {'val': 'single', 'sz': '4', 'color': '000000'},
            'bottom': {'val': 'single', 'sz': '4', 'color': '000000'},
            'left': {'val': 'single', 'sz': '4', 'color': '000000'},
            'right': {'val': 'single', 'sz': '4', 'color': '000000'}
        }

        # Data 21 baris tabel
        rows_content = [
            # 0: Poin 1
            ("1.", "Pengguna Anggaran/ Kuasa Pengguna Anggaran", f"KEPALA {s.get('instansi_nama')} {s.get('instansi_nama_induk')}", False),
            # 1: Poin 2
            ("2.", "Nama / NIP Pegawai yang Melaksanakan Perjalanan Dinas", f"{p['nama']} / {p.get('nip') or '-'}", True),
            # 2, 3, 4: Poin 3
            ("3.", "a. Pangkat dan Golongan", f"a. {p.get('pangkat_golongan') or '-'}", False),
            ("", "b. Jabatan / Instansi", f"b. {p.get('jabatan') or '-'}", False),
            ("", "c. Tingkat Biaya Perjalanan Dinas", "c. -", False),
            # 5: Poin 4
            ("4.", "Maksud Perjalanan Dinas", spj.get('maksud') or '', False),
            # 6: Poin 5
            ("5.", "Alat angkutan yang dipergunakan", spj.get('angkutan') or 'Kendaraan Roda Empat', False),
            # 7, 8: Poin 6
            ("6.", "a. Tempat Berangkat", "a. Kepahiang", False),
            ("", "b. Tempat Tujuan", f"b. {tujuan_lengkap}", False),
            # 9, 10, 11: Poin 7
            ("7.", "a. Lama Perjalanan Dinas", f"a. {spj.get('lama_hari')} ( {terbilang_kata(spj.get('lama_hari'))} ) hari", False),
            ("", "b. Tanggal Berangkat", f"b. {format_tanggal(spj.get('tanggal_berangkat'))}", False),
            ("", "c. Tanggal Harus Kembali/tiba ditempat baru", f"c. {format_tanggal(spj.get('tanggal_pulang'))}", False),
            # 12, 13, 14, 15, 16: Poin 8
            ("8.", "Pengikut :                         Nama :", "Tanggal Lahir           Keterangan", False),
            ("", "1. -", "-                                  -", False),
            ("", "2. -", "-                                  -", False),
            ("", "3. -", "-                                  -", False),
            ("", "4. -", "-                                  -", False),
            # 17, 18, 19: Poin 9
            ("9.", "Pembebanan Anggaran", "", False),
            ("", "a. Instansi", f"a. {s.get('instansi_nama')}", False),
            ("", "b. Mata Anggaran", f"b. {spj.get('mata_anggaran')}", False),
            # 20: Poin 10
            ("10.", "Keterangan Lain - lain", "-", False)
        ]

        for r_idx, (c0_txt, c1_txt, c2_txt, is_val_bold) in enumerate(rows_content):
            row = tbl.rows[r_idx]
            cell0, cell1, cell2 = row.cells[0], row.cells[1], row.cells[2]
            cell0.width, cell1.width, cell2.width = w0, w1, w2

            set_cell_margins(cell0, top=50, bottom=50, left=40, right=40)
            set_cell_margins(cell1, top=50, bottom=50, left=80, right=60)
            set_cell_margins(cell2, top=50, bottom=50, left=80, right=60)

            set_cell_border(cell0, **border_kw)
            set_cell_border(cell1, **border_kw)
            set_cell_border(cell2, **border_kw)

            p0 = cell0.paragraphs[0]
            p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.paragraph_format.line_spacing = 1.15
            p0.paragraph_format.space_before = Pt(0)
            p0.paragraph_format.space_after = Pt(0)
            add_run_arial(p0, c0_txt, size_pt=11)

            p1 = cell1.paragraphs[0]
            p1.paragraph_format.line_spacing = 1.15
            p1.paragraph_format.space_before = Pt(0)
            p1.paragraph_format.space_after = Pt(0)
            add_run_arial(p1, c1_txt, size_pt=11)

            p2 = cell2.paragraphs[0]
            p2.paragraph_format.line_spacing = 1.15
            p2.paragraph_format.space_before = Pt(0)
            p2.paragraph_format.space_after = Pt(0)
            if r_idx == 5:
                p2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            add_run_arial(p2, c2_txt, size_pt=11, bold=is_val_bold)

        # Merge Col 0 untuk kelompok Poin dengan sub-poin (3, 6, 7, 8, 9)
        tbl.cell(2, 0).merge(tbl.cell(4, 0))   # Poin 3 (3 baris)
        tbl.cell(7, 0).merge(tbl.cell(8, 0))   # Poin 6 (2 baris)
        tbl.cell(9, 0).merge(tbl.cell(11, 0))  # Poin 7 (3 baris)
        tbl.cell(12, 0).merge(tbl.cell(16, 0)) # Poin 8 (5 baris)
        tbl.cell(17, 0).merge(tbl.cell(19, 0)) # Poin 9 (3 baris)

        # Tanda Tangan SPD (Sisi Kanan)
        tbl_ttd = doc.add_table(rows=1, cols=2)
        tbl_ttd.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl_ttd.autofit = False
        tbl_ttd.columns[0].width = Cm(8.0)
        tbl_ttd.columns[1].width = Cm(8.5)

        c_ttd = tbl_ttd.rows[0].cells[1]
        c_ttd.width = Cm(8.5)
        set_cell_margins(c_ttd, top=0, bottom=0, left=40, right=0)

        p_ttd = c_ttd.paragraphs[0]
        p_ttd.paragraph_format.space_before = Pt(12)
        p_ttd.paragraph_format.line_spacing = 1.25
        p_ttd.alignment = WD_ALIGN_PARAGRAPH.CENTER

        kota_terbit = s.get('kop_kadis_kota') or s.get('instansi_kota') or 'Kepahiang'
        tgl_terbit = format_tanggal(spj.get('tanggal_spt') or spj.get('tanggal_berangkat'))

        add_run_arial(p_ttd, f"Dikeluarkan di : {kota_terbit}\nPada Tanggal : {tgl_terbit}\n", size_pt=11)

        is_kadis = (spj.get('jenis_spt') == 'kadis')
        if is_kadis and spj.get('spt_penandatangan_nama'):
            ttd_an = spj.get('spt_penandatangan_an') or s.get('pejabat_ttd_kadis_an')
            ttd_jabatan = spj.get('spt_penandatangan_jabatan') or s.get('pejabat_ttd_kadis_jabatan') or 'Sekretaris Daerah'
            ttd_nama = spj.get('spt_penandatangan_nama') or s.get('pejabat_ttd_kadis_nama') or s.get('pejabat_kadis_nama')
            ttd_pangkat = spj.get('spt_penandatangan_pangkat') or s.get('pejabat_ttd_kadis_pangkat') or s.get('pejabat_kadis_pangkat')
            ttd_nip = spj.get('spt_penandatangan_nip') or s.get('pejabat_ttd_kadis_nip') or s.get('pejabat_kadis_nip')

            if ttd_an:
                add_run_arial(p_ttd, f"{ttd_an}\n", size_pt=11, bold=True)
            add_run_arial(p_ttd, f"{ttd_jabatan}\n\n\n\n", size_pt=11, bold=True)
            add_run_arial(p_ttd, f"{ttd_nama}\n", size_pt=11, bold=True, underline=False)
            if ttd_pangkat:
                add_run_arial(p_ttd, f"{ttd_pangkat}\n", size_pt=11)
            if ttd_nip:
                add_run_arial(p_ttd, f"NIP. {ttd_nip}", size_pt=11)
        else:
            add_run_arial(p_ttd, "Pengguna Anggaran\n/ Kuasa Pengguna Anggaran\n\n\n\n", size_pt=11, bold=True)
            add_run_arial(p_ttd, f"{s.get('pejabat_kadis_nama', '')}\n", size_pt=11, bold=True, underline=False)
            if s.get('pejabat_kadis_pangkat'):
                add_run_arial(p_ttd, f"{s.get('pejabat_kadis_pangkat')}\n", size_pt=11)
            if s.get('pejabat_kadis_nip'):
                add_run_arial(p_ttd, f"NIP. {s.get('pejabat_kadis_nip')}", size_pt=11)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def export_kwitansi_word(spj, peserta_list, biaya_list, s, root_path=''):
    """
    Ekspor dokumen Kwitansi Pembayaran ke Microsoft Word (.docx).
    100% Presisi dengan kwitansi_print.html:
    - Kop Surat resmi Staf (force_kop='staf')
    - Header: No Kuitansi (kiri) & Tahun Anggaran (kanan)
    - Judul: KUITANSI (Arial 12pt Bold Underline Center)
    - Isian: Sudah terima dari, Sebesar (Bold), Terbilang Rupiah (Bold Italic), Untuk Pengeluaran
    - Sub-daftar Dengan rincian (Tabel biaya No, Uraian, Rp, Jumlah, garis atas total)
    - 4 Kolom Tanda Tangan: Bendahara Pengeluaran, Penerima, Pengguna Anggaran, PPTK
      Nama Pejabat Bold TANPA Garis Bawah.
    """
    spj = to_dict(spj)
    s = to_dict(s)
    peserta_list = [to_dict(p) for p in (peserta_list or [])]
    biaya_list = [to_dict(b) for b in (biaya_list or [])]

    doc = docx.Document()
    setup_docx_f4_page(doc)

    target_peserta = peserta_list if peserta_list else [{
        'nama': s.get('pejabat_kadis_nama', ''),
        'nip': s.get('pejabat_kadis_nip', ''),
        'pangkat_golongan': s.get('pejabat_kadis_pangkat', ''),
        'jabatan': s.get('pejabat_kadis_jabatan', '')
    }]

    nomor_sppd = spj.get('nomor_sppd') or ''
    th_anggaran = spj.get('tanggal_berangkat', '2026')[:4] if spj.get('tanggal_berangkat') else '2026'
    if nomor_sppd and 'SPPD' in nomor_sppd:
        nomor_kw = nomor_sppd
    else:
        nomor_kw = f"800/      /SPPD/Dukcapil-Kph/{th_anggaran}"

    tujuan_lengkap = format_tujuan_lengkap(spj)
    maksud_str = (spj.get('maksud') or '').rstrip('. ')

    tgl_berangkat = spj.get('tanggal_berangkat')
    tgl_pulang = spj.get('tanggal_pulang')
    if tgl_berangkat == tgl_pulang:
        tgl_str = format_tanggal(tgl_berangkat)
    else:
        tgl_str = f"{format_tanggal(tgl_berangkat)} s.d. {format_tanggal(tgl_pulang)}"

    for idx, p in enumerate(target_peserta):
        if idx > 0:
            doc.add_page_break()

        add_kop_surat_docx(doc, s, jenis_spt='staf', force_kop='staf', root_path=root_path)

        # Header No Kuitansi & Tahun Anggaran
        tbl_meta = doc.add_table(rows=1, cols=2)
        tbl_meta.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl_meta.autofit = False
        tbl_meta.columns[0].width = Cm(11.0)
        tbl_meta.columns[1].width = Cm(5.5)

        c_meta0, c_meta1 = tbl_meta.rows[0].cells
        c_meta0.width, c_meta1.width = Cm(11.0), Cm(5.5)
        set_cell_margins(c_meta0, 0, 0, 0, 0)
        set_cell_margins(c_meta1, 0, 0, 0, 0)

        p_m0 = c_meta0.paragraphs[0]
        p_m0.paragraph_format.space_before = Pt(0)
        p_m0.paragraph_format.space_after = Pt(8)
        add_run_arial(p_m0, f"No Kuitansi : {nomor_kw}", size_pt=12, bold=False)

        p_m1 = c_meta1.paragraphs[0]
        p_m1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_m1.paragraph_format.space_before = Pt(0)
        p_m1.paragraph_format.space_after = Pt(8)
        add_run_arial(p_m1, f"Tahun Anggaran : {th_anggaran}", size_pt=12, bold=False)

        # Judul: KUITANSI
        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_title.paragraph_format.space_before = Pt(4)
        p_title.paragraph_format.space_after = Pt(14)
        add_run_arial(p_title, "KUITANSI", size_pt=12, bold=True, underline=True)

        # Hitung biaya pelaksana
        pelaksana_biaya = [b for b in biaya_list if b.get('peserta_nama') == p['nama'] or not b.get('peserta_nama') or len(target_peserta) == 1]
        total_sub = sum(float(b.get('total') or 0) for b in pelaksana_biaya)

        # Tabel Data Isian Kuitansi
        tbl_info = doc.add_table(rows=4, cols=3)
        tbl_info.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl_info.autofit = False
        tbl_info.columns[0].width = Cm(4.0)
        tbl_info.columns[1].width = Cm(0.4)
        tbl_info.columns[2].width = Cm(12.1)

        an_peserta = f"\na.n. {p['nama']} ({p.get('jabatan') or p.get('pangkat_golongan') or 'Pelaksana'})" if len(target_peserta) > 1 else ""
        rows_info = [
            ("Sudah terima dari", "Bendahara Pengeluaran", False, False),
            ("Sebesar", f"Rp {format_rupiah(total_sub).replace('Rp ', '')},-", True, False),
            ("Terbilang Rupiah", f"{terbilang(total_sub)}", True, True),
            ("Untuk Pengeluaran", f"Biaya Perjalanan Dinas Dalam Rangka {maksud_str} ke {tujuan_lengkap} tanggal {tgl_str}{an_peserta}", False, False)
        ]

        for r_i, (lbl, val, is_b, is_it) in enumerate(rows_info):
            r_c0, r_c1, r_c2 = tbl_info.rows[r_i].cells
            r_c0.width, r_c1.width, r_c2.width = Cm(4.0), Cm(0.4), Cm(12.1)
            set_cell_margins(r_c0, 40, 40, 0, 0)
            set_cell_margins(r_c1, 40, 40, 0, 0)
            set_cell_margins(r_c2, 40, 40, 0, 0)

            p_0 = r_c0.paragraphs[0]
            p_0.paragraph_format.line_spacing = 1.35
            add_run_arial(p_0, lbl, size_pt=12)

            p_1 = r_c1.paragraphs[0]
            p_1.paragraph_format.line_spacing = 1.35
            add_run_arial(p_1, ":", size_pt=12)

            p_2 = r_c2.paragraphs[0]
            p_2.paragraph_format.line_spacing = 1.35
            if r_i == 3:
                p_2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            add_run_arial(p_2, val, size_pt=12, bold=is_b, italic=is_it)

        # Sub-daftar: Dengan rincian
        p_rin = doc.add_paragraph()
        p_rin.paragraph_format.left_indent = Cm(0.8)
        p_rin.paragraph_format.space_before = Pt(10)
        p_rin.paragraph_format.space_after = Pt(4)
        add_run_arial(p_rin, "Dengan rincian", size_pt=11, bold=True)

        tbl_rin = doc.add_table(rows=len(pelaksana_biaya) + 1, cols=4)
        tbl_rin.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl_rin.autofit = False

        w_r0, w_r1, w_r2, w_r3 = Cm(0.8), Cm(9.2), Cm(1.2), Cm(3.3)
        tbl_rin.columns[0].width = w_r0
        tbl_rin.columns[1].width = w_r1
        tbl_rin.columns[2].width = w_r2
        tbl_rin.columns[3].width = w_r3

        for b_i, b in enumerate(pelaksana_biaya):
            row_c = tbl_rin.rows[b_i]
            c0, c1, c2, c3 = row_c.cells[0], row_c.cells[1], row_c.cells[2], row_c.cells[3]
            c0.width, c1.width, c2.width, c3.width = w_r0, w_r1, w_r2, w_r3
            set_cell_margins(c0, 20, 20, 0, 0)
            set_cell_margins(c1, 20, 20, 0, 0)
            set_cell_margins(c2, 20, 20, 0, 0)
            set_cell_margins(c3, 20, 20, 0, 0)

            p0 = c0.paragraphs[0]
            add_run_arial(p0, f"{b_i+1}.", size_pt=11)

            p1 = c1.paragraphs[0]
            add_run_arial(p1, clean_uraian(b.get('keterangan'), p['nama']), size_pt=11)

            p2 = c2.paragraphs[0]
            p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            add_run_arial(p2, "Rp", size_pt=11)

            p3 = c3.paragraphs[0]
            p3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            val_fmt = format_rupiah(b.get('total') or 0).replace('Rp ', '')
            add_run_arial(p3, val_fmt, size_pt=11)

        # Baris Jumlah Total
        row_tot = tbl_rin.rows[-1]
        c0, c1, c2, c3 = row_tot.cells[0], row_tot.cells[1], row_tot.cells[2], row_tot.cells[3]
        c0.width, c1.width, c2.width, c3.width = w_r0, w_r1, w_r2, w_r3
        set_cell_margins(c0, 30, 20, 0, 0)
        set_cell_margins(c1, 30, 20, 0, 0)
        set_cell_margins(c2, 30, 20, 0, 0)
        set_cell_margins(c3, 30, 20, 0, 0)

        p1_tot = c1.paragraphs[0]
        p1_tot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        add_run_arial(p1_tot, "Jumlah", size_pt=11, bold=True)

        border_top_kw = {'top': {'val': 'single', 'sz': '6', 'color': '000000'}}
        set_cell_border(c2, **border_top_kw)
        set_cell_border(c3, **border_top_kw)

        p2_tot = c2.paragraphs[0]
        p2_tot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        add_run_arial(p2_tot, "Rp", size_pt=11, bold=True)

        p3_tot = c3.paragraphs[0]
        p3_tot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        tot_fmt = format_rupiah(total_sub).replace('Rp ', '')
        add_run_arial(p3_tot, tot_fmt, size_pt=11, bold=True)

        # Tanda Tangan 4 Kolom
        kota = s.get('instansi_kota') or 'Kepahiang'
        p_tgl_ttd = doc.add_paragraph()
        p_tgl_ttd.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_tgl_ttd.paragraph_format.space_before = Pt(14)
        p_tgl_ttd.paragraph_format.space_after = Pt(6)
        add_run_arial(p_tgl_ttd, f"{kota},            {format_tanggal(tgl_pulang)}", size_pt=12)

        tbl_ttd = doc.add_table(rows=2, cols=2)
        tbl_ttd.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl_ttd.autofit = False
        tbl_ttd.columns[0].width = Cm(8.2)
        tbl_ttd.columns[1].width = Cm(8.3)

        # Baris 1: Bendahara & Penerima
        c_bend, c_prm = tbl_ttd.rows[0].cells
        c_bend.width, c_prm.width = Cm(8.2), Cm(8.3)
        set_cell_margins(c_bend, 0, 0, 20, 20)
        set_cell_margins(c_prm, 0, 0, 20, 20)

        p_bend = c_bend.paragraphs[0]
        p_bend.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_bend.paragraph_format.line_spacing = 1.25
        add_run_arial(p_bend, "Bendahara Pengeluaran\n\n\n\n", size_pt=12)
        add_run_arial(p_bend, f"{s.get('pejabat_bendahara_nama', '')}\n", size_pt=12, bold=True, underline=False)
        add_run_arial(p_bend, f"NIP. {s.get('pejabat_bendahara_nip', '')}", size_pt=12)

        p_prm = c_prm.paragraphs[0]
        p_prm.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_prm.paragraph_format.line_spacing = 1.25
        add_run_arial(p_prm, "Penerima,\n\n\n\n", size_pt=12)
        add_run_arial(p_prm, f"{p['nama']}\n", size_pt=12, bold=True, underline=False)
        add_run_arial(p_prm, f"NIP. {p.get('nip') or '-'}", size_pt=12)

        # Baris 2: PA & PPTK
        c_pa, c_pptk = tbl_ttd.rows[1].cells
        c_pa.width, c_pptk.width = Cm(8.2), Cm(8.3)
        set_cell_margins(c_pa, 80, 0, 20, 20)
        set_cell_margins(c_pptk, 80, 0, 20, 20)

        p_pa = c_pa.paragraphs[0]
        p_pa.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_pa.paragraph_format.line_spacing = 1.25
        add_run_arial(p_pa, "Mengetahui,\nPengguna Anggaran\n\n\n\n", size_pt=12)
        add_run_arial(p_pa, f"{s.get('pejabat_kadis_nama', '')}\n", size_pt=12, bold=True, underline=False)
        add_run_arial(p_pa, f"NIP. {s.get('pejabat_kadis_nip', '')}", size_pt=12)

        p_pptk = c_pptk.paragraphs[0]
        p_pptk.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_pptk.paragraph_format.line_spacing = 1.25
        add_run_arial(p_pptk, "PPTK\n\n\n\n\n", size_pt=12)
        add_run_arial(p_pptk, f"{s.get('pejabat_pptk_nama', '')}\n", size_pt=12, bold=True, underline=False)
        add_run_arial(p_pptk, f"NIP. {s.get('pejabat_pptk_nip', '')}", size_pt=12)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def export_pengeluaran_riil_word(spj, peserta_list, biaya_list, s, root_path=''):
    """
    Ekspor Daftar Pengeluaran Riil ke Microsoft Word (.docx).
    100% Presisi dengan pengeluaran_riil_print.html:
    - Kop Surat resmi Staf (force_kop='staf')
    - Judul: DAFTAR PENGELUARAN RIIL (Arial 12pt Bold Underline Center)
    - Identitas: Nama (Bold), NIP, Jabatan
    - Konsiderans: SPD Nomor {nomor_sppd} butir 1
    - Tabel Biaya Riil (hanya b['termasuk_riil'] == 1, shading abu-abu F2F2F2, border box)
    - Klausul Penutup butir 2
    - Tanda Tangan 2 Kolom: Mengetahui/ Menyetujui PA/KPA & Pejabat/Pegawai Yang Melakukan Perjadin
      Nama Pejabat Bold TANPA Garis Bawah.
    """
    spj = to_dict(spj)
    s = to_dict(s)
    peserta_list = [to_dict(p) for p in (peserta_list or [])]
    biaya_list = [to_dict(b) for b in (biaya_list or [])]

    doc = docx.Document()
    setup_docx_f4_page(doc)

    target_peserta = peserta_list if peserta_list else [{
        'nama': s.get('pejabat_kadis_nama', ''),
        'nip': s.get('pejabat_kadis_nip', ''),
        'pangkat_golongan': s.get('pejabat_kadis_pangkat', ''),
        'jabatan': s.get('pejabat_kadis_jabatan', '')
    }]

    border_kw = {
        'top': {'val': 'single', 'sz': '4', 'color': '000000'},
        'bottom': {'val': 'single', 'sz': '4', 'color': '000000'},
        'left': {'val': 'single', 'sz': '4', 'color': '000000'},
        'right': {'val': 'single', 'sz': '4', 'color': '000000'}
    }

    for idx, p in enumerate(target_peserta):
        if idx > 0:
            doc.add_page_break()

        add_kop_surat_docx(doc, s, jenis_spt='staf', force_kop='staf', root_path=root_path)

        # Judul Dokumen
        p_t = doc.add_paragraph()
        p_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_t.paragraph_format.space_before = Pt(4)
        p_t.paragraph_format.space_after = Pt(14)
        add_run_arial(p_t, "DAFTAR PENGELUARAN RIIL", size_pt=12, bold=True, underline=True)

        # Identitas Pelaksana
        p_id_hdr = doc.add_paragraph()
        p_id_hdr.paragraph_format.space_before = Pt(0)
        p_id_hdr.paragraph_format.space_after = Pt(2)
        add_run_arial(p_id_hdr, "Yang bertanda tangan di bawah ini :", size_pt=12)

        tbl_id = doc.add_table(rows=3, cols=3)
        tbl_id.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl_id.autofit = False
        tbl_id.columns[0].width = Cm(2.8)
        tbl_id.columns[1].width = Cm(0.4)
        tbl_id.columns[2].width = Cm(13.3)

        id_rows = [
            ("Nama", p['nama'], True),
            ("NIP", p.get('nip') or '-', False),
            ("Jabatan", p.get('jabatan') or '-', False)
        ]

        for r_i, (k, v, is_b) in enumerate(id_rows):
            c0, c1, c2 = tbl_id.rows[r_i].cells
            c0.width, c1.width, c2.width = Cm(2.8), Cm(0.4), Cm(13.3)
            set_cell_margins(c0, 20, 20, 0, 0)
            set_cell_margins(c1, 20, 20, 0, 0)
            set_cell_margins(c2, 20, 20, 0, 0)

            p0 = c0.paragraphs[0]
            add_run_arial(p0, k, size_pt=12)

            p1 = c1.paragraphs[0]
            add_run_arial(p1, ":", size_pt=12)

            p2 = c2.paragraphs[0]
            add_run_arial(p2, v, size_pt=12, bold=is_b)

        # Konsiderans SPD
        p_desc = doc.add_paragraph()
        p_desc.paragraph_format.space_before = Pt(8)
        p_desc.paragraph_format.space_after = Pt(4)
        p_desc.paragraph_format.line_spacing = 1.35
        p_desc.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        tgl_berangkat = format_tanggal(spj.get('tanggal_berangkat'))
        nomor_sppd = spj.get('nomor_sppd') or ''
        add_run_arial(p_desc, f"Berdasarkan Surat Perjalanan Dinas (SPD) tanggal {tgl_berangkat} Nomor ", size_pt=12)
        add_run_arial(p_desc, f"{nomor_sppd}", size_pt=12, bold=True)
        add_run_arial(p_desc, " Dengan ini kami menyatakan dengan sesungguhnya bahwa:", size_pt=12)

        p_point1 = doc.add_paragraph()
        p_point1.paragraph_format.space_before = Pt(0)
        p_point1.paragraph_format.space_after = Pt(6)
        p_point1.paragraph_format.line_spacing = 1.35
        p_point1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_run_arial(p_point1, "1. Biaya transportasi pegawai dan/atau biaya penginapan di bawah ini tidak dapat diperoleh bukti-bukti pengeluaran meliputi :", size_pt=12)

        # Filter hanya biaya yang termasuk_riil == 1
        pelaksana_biaya = [b for b in biaya_list if (b.get('peserta_nama') == p['nama'] or not b.get('peserta_nama') or len(target_peserta) == 1) and (b.get('termasuk_riil') == 1)]
        total_riil = sum(float(b.get('total') or 0) for b in pelaksana_biaya)

        # Tabel Pengeluaran Riil (3 Kolom)
        num_rows = len(pelaksana_biaya) if pelaksana_biaya else 1
        tbl = doc.add_table(rows=num_rows + 2, cols=3)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False

        w0, w1, w2 = Cm(1.2), Cm(10.8), Cm(4.5)
        tbl.columns[0].width = w0
        tbl.columns[1].width = w1
        tbl.columns[2].width = w2

        # Header Tabel
        h0, h1, h2 = tbl.rows[0].cells
        h0.width, h1.width, h2.width = w0, w1, w2
        for h, text, align in [(h0, "No", WD_ALIGN_PARAGRAPH.CENTER),
                               (h1, "Uraian", WD_ALIGN_PARAGRAPH.LEFT),
                               (h2, "Jumlah", WD_ALIGN_PARAGRAPH.RIGHT)]:
            set_cell_margins(h, 40, 40, 60, 60)
            set_cell_border(h, **border_kw)
            set_cell_shading(h, "F2F2F2")
            p_h = h.paragraphs[0]
            p_h.alignment = align
            add_run_arial(p_h, text, size_pt=11, bold=True)

        if not pelaksana_biaya:
            # Baris default jika tidak ada biaya riil
            r_c = tbl.rows[1]
            c0, c1, c2 = r_c.cells[0], r_c.cells[1], r_c.cells[2]
            c0.width, c1.width, c2.width = w0, w1, w2
            for c in (c0, c1, c2):
                set_cell_margins(c, 40, 40, 60, 60)
                set_cell_border(c, **border_kw)

            p0 = c0.paragraphs[0]
            p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_run_arial(p0, "1", size_pt=11)

            p1 = c1.paragraphs[0]
            add_run_arial(p1, "Biaya Transportasi Lokal / Taksi", size_pt=11)

            p2 = c2.paragraphs[0]
            p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            add_run_arial(p2, "Rp. -", size_pt=11)
        else:
            for b_i, b in enumerate(pelaksana_biaya, 1):
                r_c = tbl.rows[b_i]
                c0, c1, c2 = r_c.cells[0], r_c.cells[1], r_c.cells[2]
                c0.width, c1.width, c2.width = w0, w1, w2
                for c in (c0, c1, c2):
                    set_cell_margins(c, 40, 40, 60, 60)
                    set_cell_border(c, **border_kw)

                p0 = c0.paragraphs[0]
                p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
                add_run_arial(p0, str(b_i), size_pt=11)

                p1 = c1.paragraphs[0]
                add_run_arial(p1, clean_uraian(b.get('keterangan'), p['nama']), size_pt=11)

                p2 = c2.paragraphs[0]
                p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                val_fmt = format_rupiah(b.get('total') or 0).replace('Rp ', '')
                add_run_arial(p2, f"Rp. {val_fmt}", size_pt=11)

        # Baris Jumlah Total
        r_tot = tbl.rows[-1]
        c0, c1, c2 = r_tot.cells[0], r_tot.cells[1], r_tot.cells[2]
        c0.width, c1.width, c2.width = w0, w1, w2
        for c in (c0, c1, c2):
            set_cell_margins(c, 40, 40, 60, 60)
            set_cell_border(c, **border_kw)
            set_cell_shading(c, "F2F2F2")

        p1_tot = c1.paragraphs[0]
        p1_tot.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_run_arial(p1_tot, "JUMLAH", size_pt=11, bold=True)

        p2_tot = c2.paragraphs[0]
        p2_tot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        tot_fmt = format_rupiah(total_riil).replace('Rp ', '')
        add_run_arial(p2_tot, f"Rp. {tot_fmt}", size_pt=11, bold=True)

        # Klausul Penutup
        p_close1 = doc.add_paragraph()
        p_close1.paragraph_format.space_before = Pt(8)
        p_close1.paragraph_format.space_after = Pt(4)
        p_close1.paragraph_format.line_spacing = 1.35
        p_close1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_run_arial(p_close1, "2. Jumlah uang tersebut pada angka 1 diatas benar-benar dikeluarkan untuk pelaksanaan perjalanan dinas dimaksud dan apabila dikemudian hari terdapat kelebihan atas pembayaran kami bersedia untuk menyetorkan kelebihan tersebut ke kas daerah.", size_pt=12)

        p_close2 = doc.add_paragraph()
        p_close2.paragraph_format.space_before = Pt(0)
        p_close2.paragraph_format.space_after = Pt(14)
        p_close2.paragraph_format.line_spacing = 1.35
        p_close2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_run_arial(p_close2, "Demikian pernyataan ini dibuat dengan sebenarnya, untuk dipergunakan sebagaimana mestinya.", size_pt=12)

        # Tanda Tangan 2 Kolom
        kota = s.get('instansi_kota') or 'Kepahiang'
        tgl_pulang = format_tanggal(spj.get('tanggal_pulang'))

        p_tgl_ttd = doc.add_paragraph()
        p_tgl_ttd.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_tgl_ttd.paragraph_format.space_before = Pt(4)
        p_tgl_ttd.paragraph_format.space_after = Pt(6)
        add_run_arial(p_tgl_ttd, f"{kota},            {tgl_pulang}", size_pt=12)

        tbl_ttd = doc.add_table(rows=1, cols=2)
        tbl_ttd.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl_ttd.autofit = False
        tbl_ttd.columns[0].width = Cm(8.2)
        tbl_ttd.columns[1].width = Cm(8.3)

        c_pa, c_peg = tbl_ttd.rows[0].cells
        c_pa.width, c_peg.width = Cm(8.2), Cm(8.3)
        set_cell_margins(c_pa, 0, 0, 20, 20)
        set_cell_margins(c_peg, 0, 0, 20, 20)

        p_pa = c_pa.paragraphs[0]
        p_pa.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_pa.paragraph_format.line_spacing = 1.25
        add_run_arial(p_pa, "Mengetahui/ Menyetujui\nPA/ KPA\n\n\n\n", size_pt=12)
        add_run_arial(p_pa, f"{s.get('pejabat_kadis_nama', '')}\n", size_pt=12, bold=True, underline=False)
        add_run_arial(p_pa, f"NIP. {s.get('pejabat_kadis_nip', '')}", size_pt=12)

        p_peg = c_peg.paragraphs[0]
        p_peg.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_peg.paragraph_format.line_spacing = 1.25
        add_run_arial(p_peg, "Pejabat Negara/ Pegawai Negeri\nYang melakukan perjalanan dinas,\n\n\n\n", size_pt=12)
        add_run_arial(p_peg, f"{p['nama']}\n", size_pt=12, bold=True, underline=False)
        add_run_arial(p_peg, f"NIP. {p.get('nip') or '-'}", size_pt=12)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def export_laporan_word(spj, laporan, peserta_list, s, root_path=''):
    """
    Ekspor dokumen Laporan Hasil Perjalanan Dinas ke Microsoft Word (.docx).
    100% Presisi dengan laporan_print.html:
    - Kop Surat resmi Staf (force_kop='staf')
    - Judul: LAPORAN HASIL PERJALANAN DINAS (Arial 12pt Bold Underline Center)
    - Nomor: Lampiran SPT Nomor : {nomor_spt}
    - Memo Pengantar: Kepada Yth., Dari, Tanggal Laporan, Perihal
    - Isi 6 Bab Terstruktur (Arial 12pt Justified, Indentasi Bab rapi):
      I. DASAR PELAKSANAAN
      II. MAKSUD DAN TUJUAN
      III. WAKTU DAN TEMPAT PELAKSANAAN
      IV. KEGIATAN YANG DILAKSANAKAN
      V. HASIL YANG DICAPAI
      VI. KESIMPULAN DAN REKOMENDASI
    - Penutup Laporan
    - Tanda Tangan: Yang Melaporkan (Daftar seluruh pelaksana penugasan)
    """
    spj = to_dict(spj)
    laporan = to_dict(laporan)
    s = to_dict(s)
    peserta_list = [to_dict(p) for p in (peserta_list or [])]

    doc = docx.Document()
    setup_docx_f4_page(doc)
    add_kop_surat_docx(doc, s, jenis_spt='staf', force_kop='staf', root_path=root_path)

    # Judul Dokumen
    p_t = doc.add_paragraph()
    p_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_t.paragraph_format.space_before = Pt(4)
    p_t.paragraph_format.space_after = Pt(2)
    add_run_arial(p_t, "LAPORAN HASIL PERJALANAN DINAS", size_pt=12, bold=True, underline=True)

    # Nomor Dokumen
    p_no = doc.add_paragraph()
    p_no.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_no.paragraph_format.space_after = Pt(12)
    add_run_arial(p_no, f"Lampiran SPT Nomor : {spj.get('nomor_spt')}", size_pt=12, bold=False)

    # Header Memo Pengantar
    tbl_meta = doc.add_table(rows=4, cols=3)
    tbl_meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_meta.autofit = False
    tbl_meta.columns[0].width = Cm(3.5)
    tbl_meta.columns[1].width = Cm(0.4)
    tbl_meta.columns[2].width = Cm(12.6)

    dari_str = ", ".join([f"{p['nama']} ({p.get('jabatan') or '-'})" for p in peserta_list]) if peserta_list else s.get('pejabat_kadis_nama', '')
    meta_rows = [
        ("Kepada Yth.", s.get('pejabat_kadis_jabatan', 'Kepala Dinas'), False),
        ("Dari", dari_str, False),
        ("Tanggal Laporan", format_tanggal(spj.get('tanggal_pulang')), False),
        ("Perihal", f"Laporan Hasil Pelaksanaan Perjalanan Dinas ke {spj.get('tujuan')}", True)
    ]

    for i, (k, v, is_v_bold) in enumerate(meta_rows):
        r_c = tbl_meta.rows[i]
        c0, c1, c2 = r_c.cells[0], r_c.cells[1], r_c.cells[2]
        c0.width, c1.width, c2.width = Cm(3.5), Cm(0.4), Cm(12.6)
        set_cell_margins(c0, 20, 20, 0, 0)
        set_cell_margins(c1, 20, 20, 0, 0)
        set_cell_margins(c2, 20, 20, 0, 0)

        p0 = c0.paragraphs[0]
        add_run_arial(p0, k, size_pt=12, bold=True)

        p1 = c1.paragraphs[0]
        add_run_arial(p1, ":", size_pt=12)

        p2 = c2.paragraphs[0]
        add_run_arial(p2, v, size_pt=12, bold=is_v_bold)

    # Garis Pemisah Tipis Memo
    p_div = doc.add_paragraph()
    p_div.paragraph_format.line_spacing = Pt(1)
    p_div.paragraph_format.space_before = Pt(4)
    p_div.paragraph_format.space_after = Pt(10)
    r_d = p_div.add_run()
    r_d.font.size = Pt(1)
    pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="6" w:space="1" w:color="CCCCCC"/></w:pBdr>')
    p_div._p.get_or_add_pPr().append(pBdr)

    # Isi 6 Bab Terstruktur
    tujuan_lengkap = format_tujuan_lengkap(spj)
    kegiatan = (laporan and laporan.get('kegiatan_dilaksanakan')) or "Melaksanakan koordinasi dan konsultasi teknis terkait pelaksanaan program kerja."
    hasil = (laporan and laporan.get('hasil_kegiatan')) or "Tersusunnya bahan sinkronisasi dan kesepakatan tindak lanjut pelaksanaan kegiatan dinas."
    kesimpulan = (laporan and laporan.get('kesimpulan_saran')) or "Kegiatan perjalanan dinas telah berjalan lancar sesuai rencana dan target yang ditetapkan."

    tgl_spt_str = format_tanggal(spj.get('tanggal_spt') or spj.get('tanggal_berangkat'))
    tgl_brgkt_str = format_tanggal(spj.get('tanggal_berangkat'))
    tgl_plng_str = format_tanggal(spj.get('tanggal_pulang'))
    instansi_tujuan_paren = f" ({spj.get('instansi_tujuan')})" if spj.get('instansi_tujuan') else ""

    bab_list = [
        ("I. DASAR PELAKSANAAN",
         f"Surat Perintah Tugas (SPT) Kepala Dinas Nomor: {spj.get('nomor_spt')} tanggal {tgl_spt_str} dan Surat Perintah Perjalanan Dinas (SPPD) Nomor: {spj.get('nomor_sppd')}."),
        ("II. MAKSUD DAN TUJUAN",
         f"{spj.get('maksud')} yang berlokasi di {spj.get('tujuan')}{instansi_tujuan_paren}."),
        ("III. WAKTU DAN TEMPAT PELAKSANAAN",
         f"Kegiatan dinas ini dilaksanakan selama {spj.get('lama_hari')} ({spj.get('lama_hari')}) hari, terhitung mulai tanggal {tgl_brgkt_str} sampai dengan {tgl_plng_str} bertempat di {spj.get('tujuan')} dengan menggunakan sarana transportasi {spj.get('angkutan')}."),
        ("IV. KEGIATAN YANG DILAKSANAKAN", kegiatan),
        ("V. HASIL YANG DICAPAI", hasil),
        ("VI. KESIMPULAN DAN REKOMENDASI", kesimpulan)
    ]

    for b_title, b_content in bab_list:
        p_bt = doc.add_paragraph()
        p_bt.paragraph_format.space_before = Pt(8)
        p_bt.paragraph_format.space_after = Pt(2)
        add_run_arial(p_bt, b_title, size_pt=12, bold=True)

        p_bc = doc.add_paragraph()
        p_bc.paragraph_format.left_indent = Cm(0.7)
        p_bc.paragraph_format.line_spacing = 1.35
        p_bc.paragraph_format.space_before = Pt(0)
        p_bc.paragraph_format.space_after = Pt(4)
        p_bc.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_run_arial(p_bc, b_content, size_pt=12)

    # Penutup Laporan
    p_close = doc.add_paragraph()
    p_close.paragraph_format.space_before = Pt(10)
    p_close.paragraph_format.space_after = Pt(14)
    p_close.paragraph_format.line_spacing = 1.35
    add_run_arial(p_close, "Demikian laporan ini dibuat, sebagai salah satu bentuk pertanggungjawaban.", size_pt=12)

    # Tanda Tangan: Yang Melaporkan (Sisi Kanan)
    tbl_ttd = doc.add_table(rows=1, cols=2)
    tbl_ttd.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_ttd.autofit = False
    tbl_ttd.columns[0].width = Cm(8.0)
    tbl_ttd.columns[1].width = Cm(8.5)

    c_ttd = tbl_ttd.rows[0].cells[1]
    c_ttd.width = Cm(8.5)
    set_cell_margins(c_ttd, top=0, bottom=0, left=40, right=0)

    p_ttd_hdr = c_ttd.paragraphs[0]
    p_ttd_hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ttd_hdr.paragraph_format.space_before = Pt(8)
    p_ttd_hdr.paragraph_format.space_after = Pt(12)
    add_run_arial(p_ttd_hdr, "Yang Melaporkan,\n", size_pt=12, bold=True)

    target_pelapor = peserta_list if peserta_list else [{'nama': s.get('pejabat_kadis_nama', '')}]
    for i, p in enumerate(target_pelapor, 1):
        p_pelapor = c_ttd.add_paragraph()
        p_pelapor.paragraph_format.line_spacing = 1.25
        p_pelapor.paragraph_format.space_before = Pt(0)
        p_pelapor.paragraph_format.space_after = Pt(20) if i < len(target_pelapor) else Pt(4)

        prefix = f"{i}. " if len(target_pelapor) > 1 else "   "
        add_run_arial(p_pelapor, prefix, size_pt=12)
        add_run_arial(p_pelapor, f"{p['nama']}\n\n", size_pt=12, bold=True, underline=False)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# ----------------- 3. BUNDLE ZIP EXPORTER -----------------

def export_bundel_zip(spj, peserta_list, biaya_list, laporan, s, root_path=''):
    """
    Ekspor seluruh dokumen SPJ (Word & Excel) ke dalam satu file arsip .ZIP
    """
    spj = to_dict(spj)
    laporan = to_dict(laporan)
    s = to_dict(s)
    peserta_list = [to_dict(p) for p in (peserta_list or [])]
    biaya_list = [to_dict(b) for b in (biaya_list or [])]

    clean_no = "".join([c for c in (spj.get('nomor_spt') or 'SPJ') if c.isalnum() or c in '-_'])
    zip_buf = io.BytesIO()

    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. SPT (Word)
        spt_doc = export_spt_word(spj, peserta_list, s, root_path=root_path)
        zf.writestr(f"01_SPT_{clean_no}.docx", spt_doc.getvalue())

        # 2. SPD (Excel & Word)
        try:
            spd_xls = export_spd_excel(spj, peserta_list, s)
            zf.writestr(f"02_SPD_{clean_no}.xlsx", spd_xls.getvalue())
        except Exception as e:
            print("Gagal generate SPD Excel:", e)

        spd_doc = export_spd_word(spj, peserta_list, s, root_path=root_path)
        zf.writestr(f"02_SPD_{clean_no}.docx", spd_doc.getvalue())

        # 3. Pengeluaran Riil (Word)
        pengeluaran_doc = export_pengeluaran_riil_word(spj, peserta_list, biaya_list, s, root_path=root_path)
        zf.writestr(f"03_Pengeluaran_Riil_{clean_no}.docx", pengeluaran_doc.getvalue())

        # 4. Kwitansi (Word)
        kwitansi_doc = export_kwitansi_word(spj, peserta_list, biaya_list, s, root_path=root_path)
        zf.writestr(f"04_Kwitansi_{clean_no}.docx", kwitansi_doc.getvalue())

        # 5. Rincian Biaya (Excel & Rekap Excel)
        rincian_xls = export_rincian_biaya_excel(spj, peserta_list, biaya_list, s)
        zf.writestr(f"05_Rincian_Biaya_{clean_no}.xlsx", rincian_xls.getvalue())

        rekap_xls = export_rekap_excel(spj, peserta_list, biaya_list, s)
        zf.writestr(f"05_Rekapitulasi_Biaya_{clean_no}.xlsx", rekap_xls.getvalue())

        # 6. Laporan Hasil (Word)
        laporan_doc = export_laporan_word(spj, laporan, peserta_list, s, root_path=root_path)
        zf.writestr(f"06_Laporan_Hasil_{clean_no}.docx", laporan_doc.getvalue())

    zip_buf.seek(0)
    return zip_buf
