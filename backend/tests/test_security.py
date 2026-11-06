import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from security import create_access_token, hash_password, verify_access_token, verify_password


class UjiKeamananAkun(unittest.TestCase):
    def test_password_disimpan_dalam_hash_dan_dapat_diverifikasi(self):
        encoded = hash_password("KataSandiContoh!2026")
        self.assertNotEqual(encoded, "KataSandiContoh!2026")
        self.assertTrue(verify_password("KataSandiContoh!2026", encoded))
        self.assertFalse(verify_password("KataSandiSalah!2026", encoded))

    def test_password_minimal_dua_belas_karakter(self):
        with self.assertRaises(ValueError):
            hash_password("pendek")

    def test_token_valid_dan_memuat_identitas_pengguna(self):
        secret = "s" * 48
        token = create_access_token(7, "admin@example.com", secret, 3600)
        payload = verify_access_token(token, secret)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["sub"], 7)
        self.assertEqual(payload["email"], "admin@example.com")

    def test_token_ditolak_jika_secret_berbeda(self):
        token = create_access_token(7, "admin@example.com", "s" * 48, 3600)
        self.assertIsNone(verify_access_token(token, "x" * 48))

    def test_token_kedaluwarsa_ditolak(self):
        token = create_access_token(7, "admin@example.com", "s" * 48, -1)
        self.assertIsNone(verify_access_token(token, "s" * 48))


if __name__ == "__main__":
    unittest.main()
