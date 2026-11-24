import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = (ROOT / "backend" / "schema.sql").read_text(encoding="utf-8").lower()
MIGRATION = (ROOT / "backend" / "migrasi_penamaan_tabel.sql").read_text(encoding="utf-8").lower()
MIGRATION_INTERPRET = (ROOT / "backend" / "migrasi_interpretasi_teks_asli.sql").read_text(encoding="utf-8").lower()
BACKEND = (ROOT / "backend" / "app.py").read_text(encoding="utf-8").lower()
FRONTEND = (ROOT / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8").lower()
DASBOR = (ROOT / "frontend" / "src" / "Dasbor.jsx").read_text(encoding="utf-8").lower()
IMPOR = (ROOT / "frontend" / "src" / "Impor.jsx").read_text(encoding="utf-8").lower()
TABEL = (ROOT / "frontend" / "src" / "Tabel.jsx").read_text(encoding="utf-8").lower()
INTERPRETASI = (ROOT / "frontend" / "src" / "Interpretasi.jsx").read_text(encoding="utf-8").lower()
API = (ROOT / "frontend" / "src" / "api.js").read_text(encoding="utf-8").lower()
TASKS = (ROOT / "test-ai" / "app" / "tasks.py").read_text(encoding="utf-8").lower()
AI_MAIN = (ROOT / "test-ai" / "app" / "main.py").read_text(encoding="utf-8").lower()
AI_INTERPRET = (ROOT / "test-ai" / "app" / "interpret.py").read_text(encoding="utf-8").lower()


class UjiSkemaDatabase(unittest.TestCase):
    def test_skema_memuat_enam_tabel(self):
        for table in ("users", "batches", "responses", "interpretations", "interpretation_results", "wordclouds"):
            self.assertIn(f"create table if not exists {table}", SCHEMA)

    def test_tabel_pengguna_menyimpan_email_dan_hash_password(self):
        self.assertIn("email         text not null unique", SCHEMA)
        self.assertIn("password_hash text not null", SCHEMA)
        self.assertNotIn("admin_password", SCHEMA)

    def test_relasi_foreign_key_sesuai_erd(self):
        self.assertRegex(SCHEMA, r"user_id\s+integer not null references users\(id\) on delete restrict")
        self.assertRegex(SCHEMA, r"batch_id\s+integer not null references batches\(id\) on delete cascade")
        self.assertRegex(SCHEMA, r"interpretation_id\s+integer not null\s+references interpretations\(id\) on delete cascade")
        self.assertIn("primary key (interpretation_id, stage)", SCHEMA)
        self.assertIn("primary key (media, label)", SCHEMA)

    def test_migrasi_menambahkan_pengguna_dan_mempertahankan_data(self):
        self.assertIn("rename to batches", MIGRATION)
        self.assertIn("rename to interpretations", MIGRATION)
        self.assertIn("rename to interpretation_results", MIGRATION)
        self.assertIn("rename column run_id to interpretation_id", MIGRATION)
        self.assertIn("create table if not exists public.users", MIGRATION)
        self.assertIn("add column if not exists user_id integer", MIGRATION)
        self.assertNotIn("drop table", MIGRATION)
        self.assertNotIn("truncate", MIGRATION)

    def test_backend_menggunakan_login_email_password_dan_token(self):
        self.assertIn('@app.post("/api/auth/login")', BACKEND)
        self.assertIn("select id, email, password_hash from users", BACKEND)
        self.assertIn("authorization: str = header", BACKEND)
        self.assertIn("depends(get_current_user)", BACKEND)
        self.assertNotIn("admin_password", BACKEND)
        self.assertNotIn("x-admin-key", BACKEND)

    def test_backend_mencatat_pengguna_pada_impor_dan_interpretasi(self):
        self.assertIn("insert into batches (user_id, filename, total)", BACKEND)
        self.assertIn("insert into interpretations (user_id, media)", BACKEND)

    def test_frontend_login_meminta_email_dan_password(self):
        self.assertIn('type="email"', FRONTEND)
        self.assertIn('type="password"', FRONTEND)
        self.assertIn("api.masuk(email, sandi)", FRONTEND)
        self.assertIn("headers.authorization = `bearer ${token}`", API)
        self.assertNotIn("x-admin-key", API)

    def test_frontend_mengikuti_struktur_wireframe_revisi(self):
        for menu in ("dashboard", "impor data", "data tanggapan", "interpretasi", "logout"):
            self.assertIn(menu, FRONTEND)
        for bagian in ("total tanggapan", "distribusi sentimen", "hasil per media digital", "word cloud"):
            self.assertIn(bagian, DASBOR)
        for bagian in ("unggah dataset", "pilih file", "status file", "proses klasifikasi", "riwayat unggah"):
            self.assertIn(bagian, IMPOR)
        for kolom in ("no", "media digital", "isi tanggapan", "sentimen", "unduh hasil"):
            self.assertIn(kolom, TABEL)
        for bagian in ("jalankan interpretasi", "pola opini", "saran tindak lanjut"):
            self.assertIn(bagian, INTERPRETASI)

    def test_ai_worker_mengakses_nama_tabel_baru(self):
        for table in ("batches", "responses", "interpretations", "interpretation_results", "wordclouds"):
            self.assertIn(table, TASKS)
        for table in ("import_batches", "interpretation_runs", "interpretation_stages"):
            self.assertNotRegex(TASKS, rf"\b{table}\b")
        self.assertNotIn("run_id", TASKS)

    def test_kontrak_job_interpretasi_menggunakan_interpretation_id(self):
        self.assertIn("class interpretationrequest", AI_MAIN)
        self.assertIn("interpretation_id: int", AI_MAIN)
        self.assertNotIn("run_id", AI_MAIN)

    def test_metode_interpretasi_menggunakan_teks_asli_dan_batch(self):
        self.assertIn("teks_asli_batch_v2", AI_INTERPRET)
        self.assertIn("select text, label from responses", TASKS)
        self.assertIn("max_input_tokens", SCHEMA)
        self.assertNotIn("frekuensi_v1", TASKS)
        self.assertNotIn("llama_top_words", TASKS)

    def test_migrasi_menambahkan_batas_masukan_llama(self):
        self.assertIn("add column if not exists max_input_tokens", MIGRATION_INTERPRET)
        self.assertNotIn("drop column", MIGRATION_INTERPRET)
        self.assertIn("default 8192", MIGRATION_INTERPRET)

    def test_backend_menandai_metode_lama_perlu_diperbarui(self):
        self.assertIn("teks_asli_batch_v2", BACKEND)
        self.assertNotIn("frekuensi_v1", BACKEND)


if __name__ == "__main__":
    unittest.main()
