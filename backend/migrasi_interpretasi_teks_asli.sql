-- Migrasi non-destruktif untuk metode interpretasi berbasis teks tanggapan asli dan batch.
-- Jalankan satu kali pada database Neon yang sudah digunakan sebelum deploy versi kode terbaru.
-- Kolom top_words dan top_phrases lama tidak dihapus agar data lama tetap aman.

BEGIN;

ALTER TABLE public.interpretations
    ADD COLUMN IF NOT EXISTS max_input_tokens INTEGER DEFAULT 8192;

COMMENT ON COLUMN public.interpretations.max_input_tokens IS
    'Batas token masukan per pemanggilan Llama untuk pemrosesan teks tanggapan asli secara batch.';

COMMIT;
