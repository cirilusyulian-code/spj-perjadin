import json
import urllib.request
import urllib.error
from database import get_settings

SYSTEM_PROMPT_LAPORAN = """Anda adalah asisten penyusun dokumen resmi kedinasan pemerintah daerah (Tata Naskah Dinas Pemerintahan Republik Indonesia).
Tugas Anda adalah menyusun narasi Bab IV (Kegiatan yang Dilaksanakan), Bab V (Hasil yang Dicapai), dan Bab VI (Kesimpulan dan Saran / Rekomendasi) untuk Laporan Hasil Perjalanan Dinas.

PEDOMAN GAYA BAHASA & KUALITAS (WAJIB DIPATUHI SECARA KETAT):
1. Bahasa Resmi Pemerintahan (Birokratis Bersih): Gunakan kosakata baku bahasa Indonesia formal kedinasan (contoh: koordinasi, sinkronisasi data, inventarisasi kendala, verifikasi berkas, asistensi teknis, tindak lanjut).
2. DILARANG KERAS MENGGUNAKAN AI-SLOP & KATA KLISE:
   - Dilarang memakai kata: mendalam/delve, permadani/tapestry, lanskap/landscape, bukti nyata/testament, sangat penting/pivotal, mercusuar/beacon, melepaskan/unleash, meningkatkan/elevate, mulus/tanpa hambatan/seamless, memupuk/foster, dinamis/vibrant, game-changer, dsb.
   - Dilarang membuat kalimat kontras biner klise: "Bukan hanya sekadar X, melainkan Y" atau sejenisnya.
   - Dilarang membuat kalimat penutup dramatis klise: "Hal ini mengubah segalanya", dll.
   - Dilarang pembuka basa-basi (throat-clearing): "Dalam era digital yang serba cepat...", "Tidak dapat dipungkiri bahwa...", dsb.
3. Struktur Konkret & Humanis:
   - Bab IV (Kegiatan yang Dilaksanakan): Tulis dalam bentuk butir-butir bernomor (1, 2, 3...) yang runut secara kronologis mengenai aktivitas nyata yang dilaksanakan selama bertugas.
   - Bab V (Hasil yang Dicapai): Tulis dalam bentuk butir-butir bernomor (1, 2, 3...) memuat output nyata, kesepakatan, dokumen/data yang diperoleh, atau status penyelesaian agenda.
   - Bab VI (Kesimpulan dan Rekomendasi): Tulis butir padat atau paragraf ringkas mengenai evaluasi penugasan dan saran tindak lanjut operasional yang realistis bagi dinas.

FORMAT OUTPUT WAJIB BERUPA VALID JSON MURNI DENGAN KUNCI:
{
  "kegiatan_dilaksanakan": "1. ...\\n2. ...\\n3. ...",
  "hasil_kegiatan": "1. ...\\n2. ...\\n3. ...",
  "kesimpulan_saran": "1. ...\\n2. ..."
}
Pastikan hanya mengembalikan teks JSON tersebut tanpa backticks markdown tambahan.
"""

def test_9router_connection(base_url, api_key, model):
    """
    Uji konektivitas ke 9Router endpoint.
    """
    clean_base = base_url.rstrip('/')
    url = f"{clean_base}/models"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "User-Agent": "e-SPJ-Perjadin/2.4"
    }

    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=8) as response:
            if response.status == 200:
                raw_data = response.read().decode('utf-8')
                data = json.loads(raw_data)
                models = [m.get('id', '') for m in data.get('data', [])] if 'data' in data else []
                return True, f"Koneksi berhasil! Ditemukan {len(models)} model di 9Router.", models
            return False, f"Server merespons kode status {response.status}", []
    except urllib.error.HTTPError as e:
        if e.code in [404, 405]:
            return _test_chat_ping(clean_base, api_key, model)
        return False, f"HTTP Error {e.code}: {e.reason}", []
    except urllib.error.URLError as e:
        return False, f"Tidak dapat terhubung ke 9Router di {base_url} ({e.reason}).", []
    except Exception as e:
        return False, f"Kesalahan koneksi: {str(e)}", []

def _test_chat_ping(clean_base, api_key, model):
    url = f"{clean_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "User-Agent": "e-SPJ-Perjadin/2.4"
    }
    payload = json.dumps({
        "model": model or "gemini/gemini-3.6-flash",
        "stream": True,
        "messages": [{"role": "user", "content": "ping"}]
    }).encode('utf-8')

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=12) as response:
            if response.status == 200:
                return True, "Koneksi berhasil ke endpoint 9Router!", [model]
            return False, f"Respons status {response.status}", []
    except urllib.error.HTTPError as e:
        return False, f"HTTP Error {e.code}: {e.reason}", []
    except Exception as e:
        return False, f"Kesalahan: {str(e)}", []

def generate_laporan_narasi(spj_data, catatan_user=""):
    """
    Panggil 9Router untuk menghasilkan narasi Bab IV, Bab V, Bab VI berdasarkan data SPJ dan catatan user.
    Menggunakan streaming accumulator untuk performa respons cepat tanpa timeout.
    """
    s = get_settings()
    base_url = (s.get('ai_base_url') or 'http://43.157.211.23:20128/v1').rstrip('/')
    api_key = (s.get('ai_api_key') or 'sk-6b3ac6ef8e3b70c9-8rhqas-c25f1e04').strip()
    model = (s.get('ai_model') or 'gemini/gemini-3.6-flash').strip()

    pelaksana_names = [p['nama'] for p in spj_data.get('peserta', [])]
    pelaksana_str = ", ".join(pelaksana_names) if pelaksana_names else "Tim Pelaksana Dinas"

    user_prompt = f"""DATA TUGAS PERJALANAN DINAS:
- Maksud / Agenda Tugas: {spj_data.get('maksud', '-')}
- Tujuan / Lokasi: {spj_data.get('tujuan', '-')} (Instansi: {spj_data.get('instansi_tujuan', '-')})
- Waktu Pelaksanaan: {spj_data.get('tanggal_berangkat', '-')} s.d. {spj_data.get('tanggal_pulang', '-')} ({spj_data.get('lama_hari', 1)} hari)
- Angkutan: {spj_data.get('angkutan', '-')}
- Pegawai Pelaksana: {pelaksana_str}
- Catatan Khusus / Poin Lapangan dari Petugas:
\"\"\"{catatan_user.strip() if catatan_user else 'Tidak ada catatan khusus tambahan. Kembangkan berdasarkan agenda penugasan resmi di atas secara profesional dan proporsional.'}\"\"\"

Instruksi: Susun Bab IV (kegiatan konkret), Bab V (hasil terukur & dokumen/informasi yang diperoleh), dan Bab VI (kesimpulan & saran/rekomendasi OPD).
Keluarkan murni JSON dengan kunci: 'kegiatan_dilaksanakan', 'hasil_kegiatan', 'kesimpulan_saran'.
"""

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "e-SPJ-Perjadin/2.4"
    }

    # Coba streaming terlebih dahulu (cepat & tidak terblokir buffering router)
    content = ""
    try:
        payload = json.dumps({
            "model": model,
            "stream": True,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_LAPORAN},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3
        }).encode('utf-8')

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=45) as response:
            if response.status != 200:
                raise Exception(f"Server AI mengembalikan status {response.status}")
            
            for line in response:
                line_str = line.decode('utf-8', errors='ignore').strip()
                if line_str.startswith('data: '):
                    data_part = line_str[6:].strip()
                    if data_part == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data_part)
                        delta = chunk['choices'][0].get('delta', {})
                        if 'content' in delta and delta['content']:
                            content += delta['content']
                    except Exception:
                        pass

    except Exception as stream_err:
        # Fallback non-streaming jika streaming gagal
        try:
            payload_sync = json.dumps({
                "model": model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_LAPORAN},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3
            }).encode('utf-8')
            req_sync = urllib.request.Request(url, data=payload_sync, headers=headers, method="POST")
            with urllib.request.urlopen(req_sync, timeout=45) as resp_sync:
                body = json.loads(resp_sync.read().decode('utf-8'))
                content = body['choices'][0]['message']['content'].strip()
        except Exception as e:
            return {
                "success": False,
                "error": f"Kesalahan AI: {str(e)} (Stream err: {str(stream_err)})"
            }

    content = content.strip()
    if not content:
        return {"success": False, "error": "AI tidak mengembalikan teks jawaban."}

    # Bersihkan markdown formatting jika AI membungkus dengan ```json ... ```
    if content.startswith('```'):
        lines = content.split('\n')
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].startswith('```'):
            lines = lines[:-1]
        content = '\n'.join(lines).strip()

    try:
        parsed = json.loads(content)
        return {
            "success": True,
            "kegiatan_dilaksanakan": parsed.get("kegiatan_dilaksanakan", ""),
            "hasil_kegiatan": parsed.get("hasil_kegiatan", ""),
            "kesimpulan_saran": parsed.get("kesimpulan_saran", "")
        }
    except json.JSONDecodeError:
        # Parsing fallback jika AI mengembalikan teks semi-terstruktur
        return {
            "success": True,
            "kegiatan_dilaksanakan": content,
            "hasil_kegiatan": "Data tersaji pada Bab IV.",
            "kesimpulan_saran": "Tindak lanjut penugasan disesuaikan dengan rekomendasi teknis."
        }
