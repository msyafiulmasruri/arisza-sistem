import unittest
from unittest.mock import patch
from pathlib import Path

from app import config
from app.lazy_hybrid import LazyHybridService


class HybridPalsu:
    slang_map = {"gpp": "tidak apa-apa"}

    def predict(self, texts, batch_size=16):
        return [{"text": t, "status": "ok"} for t in texts]


class UjiKonfigurasiTetap(unittest.TestCase):
    def test_parameter_model_ditetapkan_di_kode(self):
        self.assertEqual(config.LLAMA_MODEL_ID, "meta-llama/Llama-3.2-3B-Instruct")
        self.assertEqual(config.LLAMA_DTYPE, "bfloat16")
        self.assertEqual(config.LLAMA_MAX_INPUT_TOKENS, 8192)
        self.assertEqual(config.LLAMA_MAX_NEW_POLA, 220)
        self.assertEqual(config.LLAMA_MAX_NEW_SARAN, 280)
        self.assertEqual(config.MAX_PREDICT_TEXTS, 200)
        self.assertEqual(config.PREDICT_BATCH_SIZE, 16)
        self.assertEqual(config.MAX_JOBS_KEPT, 50)
        env_example = (Path(__file__).resolve().parents[1] / ".env.example").read_text(encoding="utf-8")
        self.assertNotIn("LLAMA_", env_example)
        self.assertNotIn("PREDICT_BATCH_SIZE", env_example)
        self.assertNotIn("MAX_JOBS_KEPT", env_example)
        hybrid_source = (Path(__file__).resolve().parents[1] / "app" / "hybrid_model.py").read_text(encoding="utf-8")
        self.assertIn("token=config.HF_TOKEN or None", hybrid_source)


class UjiLazyHybrid(unittest.TestCase):
    def test_model_tidak_dimuat_saat_proxy_dibuat(self):
        with patch("app.lazy_hybrid._muat_hybrid") as muat:
            service = LazyHybridService()
            self.assertFalse(service.loaded)
            self.assertIsNone(service.load_error)
            muat.assert_not_called()

    def test_model_dimuat_saat_predict_dipanggil(self):
        model = HybridPalsu()
        with patch("app.lazy_hybrid._muat_hybrid", return_value=model) as muat:
            service = LazyHybridService()
            hasil = service.predict(["contoh"], batch_size=8)
            self.assertTrue(service.loaded)
            self.assertEqual(hasil[0]["text"], "contoh")
            self.assertEqual(service.slang_map, model.slang_map)
            muat.assert_called_once()

    def test_kegagalan_load_dicatat_dan_bisa_dicoba_ulang(self):
        model = HybridPalsu()
        with patch("app.lazy_hybrid._muat_hybrid", side_effect=[OSError("unduhan gagal"), model]) as muat:
            service = LazyHybridService()
            with self.assertLogs("arisza", level="ERROR"):
                with self.assertRaisesRegex(RuntimeError, "Model Hybrid gagal dimuat"):
                    service.predict(["contoh"])
            self.assertFalse(service.loaded)
            self.assertIn("unduhan gagal", service.load_error)
            service.predict(["contoh"])
            self.assertTrue(service.loaded)
            self.assertIsNone(service.load_error)
            self.assertEqual(muat.call_count, 2)


if __name__ == "__main__":
    unittest.main()
