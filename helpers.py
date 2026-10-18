import datetime
try:
    from num2words import num2words
except ImportError:
    num2words = None

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

def terbilang(val):
    try:
        n = int(round(float(val or 0)))
        if n == 0:
            return "Nol Rupiah"
        if num2words:
            kata = num2words(n, lang='id').title()
            return f"{kata} Rupiah"
        else:
            # Fallback indonesian terbilang
            return _terbilang_manual(n) + " Rupiah"
    except Exception as e:
        return f"{val} Rupiah"

def _terbilang_manual(n):
    satuan = ["", "Satu", "Dua", "Tiga", "Empat", "Lima", "Enam", "Tujuh", "Delapan", "Sembilan", "Sepuluh", "Sebelas"]
    if n < 12:
        return satuan[n]
    elif n < 20:
        return _terbilang_manual(n - 10) + " Belas"
    elif n < 100:
        return _terbilang_manual(n // 10) + " Puluh " + _terbilang_manual(n % 10)
    elif n < 200:
        return "Seratus " + _terbilang_manual(n - 100)
    elif n < 1000:
        return _terbilang_manual(n // 100) + " Ratus " + _terbilang_manual(n % 100)
    elif n < 2000:
        return "Seribu " + _terbilang_manual(n - 1000)
    elif n < 1000000:
        return _terbilang_manual(n // 1000) + " Ribu " + _terbilang_manual(n % 1000)
    elif n < 1000000000:
        return _terbilang_manual(n // 1000000) + " Juta " + _terbilang_manual(n % 1000000)
    elif n < 1000000000000:
        return _terbilang_manual(n // 1000000000) + " Miliar " + _terbilang_manual(n % 1000000000)
    else:
        return _terbilang_manual(n // 1000000000000) + " Triliun " + _terbilang_manual(n % 1000000000000)

def format_tanggal(val):
    if not val:
        return "-"
    try:
        if isinstance(val, str):
            dt = datetime.datetime.strptime(val.strip(), "%Y-%m-%d")
        else:
            dt = val
        return f"{dt.day} {BULAN_INDONESIA.get(dt.month, '')} {dt.year}"
    except Exception:
        return str(val)

def hitung_hari(tgl_mulai, tgl_selesai):
    try:
        d1 = datetime.datetime.strptime(tgl_mulai.strip(), "%Y-%m-%d")
        d2 = datetime.datetime.strptime(tgl_selesai.strip(), "%Y-%m-%d")
        delta = (d2 - d1).days + 1
        return max(1, delta)
    except Exception:
        return 1
