"""Penghitungan kata dan frasa yang sering muncul pada kelompok sentimen.

Modul ini menggunakan clean_text (hasil preprocessing model), tanpa stemming.
Kata umum dihapus, sedangkan kata negasi tetap dipertahankan. Frekuensi dihitung
secara deterministik oleh Python; Llama hanya menerima daftar teratas untuk
menyusun interpretasi.
"""
from collections import Counter
from functools import lru_cache
import re

NEGASI = {"tidak", "bukan", "belum", "kurang", "jangan", "tanpa"}
# Kata percakapan/penegas yang berdiri sendiri tidak cukup informatif untuk
# menunjukkan topik opini, misalnya partikel "nya" atau penegas "banget".
STOPWORD_TAMBAHAN = {"nya", "banget", "sangat", "sekali", "sih", "dong", "deh", "nih", "tuh", "aja", "kok", "lah"}
_TOKEN = re.compile(r"[^\W\d_]+", re.UNICODE)
_RENTANG_FRASA = (2, 3)


@lru_cache(maxsize=1)
def _ambil_stopword():
    """Ambil daftar stopword Sastrawi satu kali selama layanan berjalan."""
    from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

    stopword = set(StopWordRemoverFactory().get_stop_words())
    stopword.update(STOPWORD_TAMBAHAN)
    stopword.difference_update(NEGASI)
    return stopword


def _teratas(counter, batas):
    """Urutkan berdasarkan frekuensi menurun, lalu alfabetis untuk hasil stabil."""
    return [
        {"teks": teks, "frekuensi": int(jumlah)}
        for teks, jumlah in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:batas]
    ]


def hitung_frekuensi(daftar_teks, batas_kata=10, batas_frasa=10):
    """Hitung frekuensi kata dan frasa dua/tiga kata pada satu kelompok sentimen.

    Frekuensi menunjukkan jumlah kemunculan, bukan jumlah responden unik.
    Frasa dihitung dari kata yang berurutan. Frasa yang memuat kata negasi tetap
    dipertahankan meskipun di dalamnya terdapat kata umum, misalnya "tidak ada".
    """
    batas_kata = max(0, int(batas_kata))
    batas_frasa = max(0, int(batas_frasa))
    stopword = _ambil_stopword()
    hitung_kata = Counter()
    hitung_frasa = Counter()
    jumlah_tanggapan = 0

    for teks in daftar_teks:
        teks = str(teks or "").strip().lower()
        if not teks:
            continue
        jumlah_tanggapan += 1
        token = _TOKEN.findall(teks)
        if not token:
            continue

        kata_bermakna = [k for k in token if k not in stopword]
        hitung_kata.update(kata_bermakna)

        for ukuran in _RENTANG_FRASA:
            for awal in range(max(0, len(token) - ukuran + 1)):
                frasa = token[awal : awal + ukuran]
                # Jangan membentuk frasa baru dengan melompati kata umum.
                # Pengecualian diberikan untuk frasa yang memuat kata negasi.
                if all(k not in stopword for k in frasa) or any(k in NEGASI for k in frasa):
                    hitung_frasa[" ".join(frasa)] += 1

    return {
        "jumlah_tanggapan": jumlah_tanggapan,
        "kata": _teratas(hitung_kata, batas_kata),
        "frasa": _teratas(hitung_frasa, batas_frasa),
        "jumlah_kata_unik": len(hitung_kata),
        "jumlah_frasa_unik": len(hitung_frasa),
        "batas_kata": batas_kata,
        "batas_frasa": batas_frasa,
    }
