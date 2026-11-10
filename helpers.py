import datetime
from markupsafe import Markup

BULAN_INDONESIA = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
    5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
    9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
}

def format_rupiah(val):
    try:
        val = float(val or 0)
        return "Rp " + "{:,.0f}".format(val).replace(",", ".")
    except Exception:
        return "Rp 0"

def angka_murni(val):
    try:
        val = float(val or 0)
        return "{:,.0f}".format(val).replace(",", ".")
    except Exception:
        return "0"

def terbilang_kata(val):
    try:
        n = int(round(float(val or 0)))
        if n == 0:
            return "Nol"
        if n < 0:
            return "Minus " + terbilang_kata(abs(n))
        return ' '.join(_terbilang_manual(n).split())
    except Exception:
        return str(val)

def terbilang(val):
    try:
        n = int(round(float(val or 0)))
        if n == 0:
            return "Nol Rupiah"
        if n < 0:
            return f"Minus {terbilang_kata(abs(n))} Rupiah"
        kata = ' '.join(_terbilang_manual(n).split())
        return f"{kata} Rupiah"
    except Exception:
        return f"{val} Rupiah"

def _terbilang_manual(n):
    if n <= 0:
        return ""
    satuan = ["", "Satu", "Dua", "Tiga", "Empat", "Lima", "Enam", "Tujuh", "Delapan", "Sembilan", "Sepuluh", "Sebelas"]
    if n < 12:
        return satuan[n]
    elif n < 20:
        return _terbilang_manual(n - 10) + " Belas"
    elif n < 100:
        return (_terbilang_manual(n // 10) + " Puluh " + _terbilang_manual(n % 10)).strip()
    elif n < 200:
        return ("Seratus " + _terbilang_manual(n - 100)).strip()
    elif n < 1000:
        return (_terbilang_manual(n // 100) + " Ratus " + _terbilang_manual(n % 100)).strip()
    elif n < 2000:
        return ("Seribu " + _terbilang_manual(n - 1000)).strip()
    elif n < 1000000:
        return (_terbilang_manual(n // 1000) + " Ribu " + _terbilang_manual(n % 1000)).strip()
    elif n < 1000000000:
        return (_terbilang_manual(n // 1000000) + " Juta " + _terbilang_manual(n % 1000000)).strip()
    elif n < 1000000000000:
        return (_terbilang_manual(n // 1000000000) + " Miliar " + _terbilang_manual(n % 1000000000)).strip()
    elif n < 1000000000000000:
        return (_terbilang_manual(n // 1000000000000) + " Triliun " + _terbilang_manual(n % 1000000000000)).strip()
    else:
        return (_terbilang_manual(n // 1000000000000000) + " Kuadriliun " + _terbilang_manual(n % 1000000000000000)).strip()

def format_nomor_spasi(nomor):
    """
    Format nomor penomoran dengan spasi non-breaking (&nbsp;)
    sehingga setiap spasi yang diinput user atau ada pada penomoran dokumen
    tidak diciutkan (collapse) oleh browser menjadi 1 spasi.
    """
    if not nomor:
        return ""
    s = str(nomor)
    # Jika format 800// tanpa spasi sama sekali, beri spasi default non-breaking
    if "800//" in s:
        s = s.replace("800//", "800/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;/")
    # Konversi Unicode non-breaking space (\u00a0) dan spasi biasa (' ') menjadi &nbsp;
    s = s.replace('\u00a0', '&nbsp;').replace(' ', '&nbsp;')
    return Markup(s)

def format_tanggal_dmy(val):
    """
    Format tanggal ke format dd/mm/yyyy.
    Contoh: '2026-11-25' -> '25/11/2026'
    """
    if not val:
        return ""
    try:
        if isinstance(val, str):
            val_clean = val.strip()
            # Jika sudah format dd/mm/yyyy
            if '/' in val_clean:
                parts = val_clean.split('/')
                if len(parts) == 3 and len(parts[0]) <= 2:
                    return val_clean
            dt = None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    dt = datetime.datetime.strptime(val_clean, fmt)
                    break
                except ValueError:
                    pass
            if not dt:
                return val_clean
        else:
            dt = val
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return str(val)

def parse_date_dmy_or_ymd(val):
    """
    Konversi input tanggal dari format dd/mm/yyyy atau yyyy-mm-dd menjadi string ISO yyyy-mm-dd
    agar selalu konsisten disimpan di database SQLite.
    """
    if not val:
        return ""
    val_clean = str(val).strip()
    # Coba YYYY-MM-DD
    try:
        dt = datetime.datetime.strptime(val_clean, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    # Coba DD/MM/YYYY atau DD-MM-YYYY
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            dt = datetime.datetime.strptime(val_clean, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return val_clean

def format_tanggal(val):
    if not val:
        return "-"
    try:
        if isinstance(val, str):
            val_clean = val.strip()
            dt = None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    dt = datetime.datetime.strptime(val_clean, fmt)
                    break
                except ValueError:
                    pass
            if not dt:
                return str(val)
        else:
            dt = val
        return f"{dt.day} {BULAN_INDONESIA.get(dt.month, '')} {dt.year}"
    except Exception:
        return str(val)

def hitung_hari(tgl_mulai, tgl_selesai):
    if not tgl_mulai or not tgl_selesai:
        return 1
    try:
        d1 = None
        d2 = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                if not d1:
                    d1 = datetime.datetime.strptime(str(tgl_mulai).strip(), fmt)
            except Exception:
                pass
            try:
                if not d2:
                    d2 = datetime.datetime.strptime(str(tgl_selesai).strip(), fmt)
            except Exception:
                pass
        if d1 and d2:
            delta = (d2 - d1).days + 1
            return max(1, delta)
        return 1
    except Exception:
        return 1

import re

def clean_uraian(keterangan, nama=None):
    if not keterangan:
        return ""
    text = str(keterangan).strip()
    if nama and str(nama).strip():
        clean_nama = re.escape(str(nama).strip())
        text = re.sub(rf'\s*-\s*{clean_nama}.*$', '', text, flags=re.IGNORECASE)
    # Also strip any generic " - Pelaksana \d+"
    text = re.sub(r'\s*-\s*Pelaksana\s*\d+.*$', '', text, flags=re.IGNORECASE)
    return text.strip()
