"""Teks untuk Word Cloud: stopword dibuang lalu di-stem, sama dengan notebook.

Kata negasi (tidak, bukan, belum, kurang, jangan, tanpa) tetap dipertahankan.
"""
import threading

_kunci = threading.Lock()
_stopword = None
_stemmer = None


def _siapkan():
    global _stopword, _stemmer
    with _kunci:
        if _stemmer is None:
            from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
            from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

            stop = set(StopWordRemoverFactory().get_stop_words())
            for kata in ("tidak", "bukan", "belum", "kurang", "jangan", "tanpa"):
                stop.discard(kata)
            _stopword = stop
            _stemmer = StemmerFactory().create_stemmer()


def buat(clean_text):
    _siapkan()
    tanpa_stop = " ".join(k for k in str(clean_text).split() if k not in _stopword)
    return _stemmer.stem(tanpa_stop)
