import unittest
from unittest.mock import patch

from app.frequency import hitung_frekuensi

STOPWORDS_UJI = {"dan", "yang", "di", "ke", "ada", "dengan", "untuk", "saat", "ini"}


class UjiFrekuensi(unittest.TestCase):
    def hitung(self, teks, kata=10, frasa=10):
        with patch("app.frequency._ambil_stopword", return_value=STOPWORDS_UJI):
            return hitung_frekuensi(teks, kata, frasa)

    def test_menghitung_kata_dan_frasa(self):
        hasil = self.hitung([
            "pelayanan lambat dan kurang ramah",
            "pelayanan lambat dan tempat nyaman",
            "pelayanan kurang ramah",
            "tempat nyaman dan fasilitas lengkap",
        ])
        kata = {item["teks"]: item["frekuensi"] for item in hasil["kata"]}
        frasa = {item["teks"]: item["frekuensi"] for item in hasil["frasa"]}
        self.assertEqual(hasil["jumlah_tanggapan"], 4)
        self.assertEqual(hasil["batas_kata"], 10)
        self.assertEqual(hasil["batas_frasa"], 10)
        self.assertEqual(kata["pelayanan"], 3)
        self.assertEqual(kata["lambat"], 2)
        self.assertEqual(kata["kurang"], 2)
        self.assertEqual(frasa["pelayanan lambat"], 2)
        self.assertEqual(frasa["kurang ramah"], 2)
        self.assertEqual(frasa["tempat nyaman"], 2)

    def test_kata_negasi_dipertahankan_dan_frasa_negasi_dihitung(self):
        hasil = self.hitung(["tidak ada tempat parkir", "tidak nyaman"])
        kata = {item["teks"]: item["frekuensi"] for item in hasil["kata"]}
        frasa = {item["teks"]: item["frekuensi"] for item in hasil["frasa"]}
        self.assertEqual(kata["tidak"], 2)
        self.assertEqual(frasa["tidak ada"], 1)
        self.assertEqual(frasa["tidak ada tempat"], 1)
        self.assertEqual(frasa["tidak nyaman"], 1)


    def test_kata_pengisi_dan_penegas_tidak_masuk_frekuensi(self):
        stopword_tambahan = {"nya", "banget", "sangat", "sekali", "sih", "dong", "deh", "nih", "tuh", "aja", "kok", "lah"}
        with patch("app.frequency._ambil_stopword", return_value=STOPWORDS_UJI | stopword_tambahan):
            hasil = hitung_frekuensi(["tempat nyaman banget dan nya enak"], 10, 10)
        kata = {item["teks"] for item in hasil["kata"]}
        frasa = {item["teks"] for item in hasil["frasa"]}
        self.assertNotIn("nya", kata)
        self.assertNotIn("banget", kata)
        self.assertIn("nyaman", kata)
        self.assertIn("enak", kata)
        self.assertNotIn("nyaman banget", frasa)

    def test_stopword_tidak_dilompati_saat_membentuk_frasa(self):
        hasil = self.hitung(["tempat yang nyaman"])
        frasa = {item["teks"]: item["frekuensi"] for item in hasil["frasa"]}
        self.assertNotIn("tempat nyaman", frasa)

    def test_batas_jumlah_dan_urutan_stabil(self):
        hasil = self.hitung(["zebra apel zebra mangga apel"], kata=2, frasa=2)
        self.assertEqual(len(hasil["kata"]), 2)
        self.assertEqual(hasil["kata"][0]["teks"], "apel")
        self.assertEqual(hasil["kata"][1]["teks"], "zebra")

    def test_tanggapan_kosong_diabaikan(self):
        hasil = self.hitung(["", None, "   "])
        self.assertEqual(hasil["jumlah_tanggapan"], 0)
        self.assertEqual(hasil["kata"], [])
        self.assertEqual(hasil["frasa"], [])


if __name__ == "__main__":
    unittest.main()
