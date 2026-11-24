-- Migrasi database lama: penamaan tabel dan penambahan akun pengguna tanpa menghapus data.
-- Dapat dijalankan pada database lama yang masih memakai nama tabel awal maupun skema v2.
-- Jalankan saat seluruh layanan/job dihentikan dan setelah membuat backup database.

BEGIN;

DO $$
BEGIN
    IF to_regclass('public.import_batches') IS NOT NULL THEN
        IF to_regclass('public.batches') IS NOT NULL THEN
            RAISE EXCEPTION 'Tabel import_batches dan batches sama-sama tersedia. Periksa database sebelum migrasi.';
        END IF;
        ALTER TABLE public.import_batches RENAME TO batches;
    END IF;

    IF to_regclass('public.interpretation_runs') IS NOT NULL THEN
        IF to_regclass('public.interpretations') IS NOT NULL THEN
            RAISE EXCEPTION 'Tabel interpretation_runs dan interpretations sama-sama tersedia. Periksa database sebelum migrasi.';
        END IF;
        ALTER TABLE public.interpretation_runs RENAME TO interpretations;
    END IF;

    IF to_regclass('public.interpretation_stages') IS NOT NULL THEN
        IF to_regclass('public.interpretation_results') IS NOT NULL THEN
            RAISE EXCEPTION 'Tabel interpretation_stages dan interpretation_results sama-sama tersedia. Periksa database sebelum migrasi.';
        END IF;
        ALTER TABLE public.interpretation_stages RENAME TO interpretation_results;
    END IF;
END
$$;

DO $$
BEGIN
    IF to_regclass('public.interpretation_results') IS NOT NULL THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'interpretation_results'
              AND column_name = 'run_id'
        ) AND NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'interpretation_results'
              AND column_name = 'interpretation_id'
        ) THEN
            ALTER TABLE public.interpretation_results RENAME COLUMN run_id TO interpretation_id;
        ELSIF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'interpretation_results'
              AND column_name = 'run_id'
        ) AND EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'interpretation_results'
              AND column_name = 'interpretation_id'
        ) THEN
            RAISE EXCEPTION 'Kolom run_id dan interpretation_id sama-sama tersedia. Periksa tabel interpretation_results.';
        END IF;
    END IF;
END
$$;

-- Pastikan setiap tanggapan terhubung ke satu proses impor, sesuai relasi 1:N pada ERD.
-- Migrasi dihentikan jika masih ada tanggapan tanpa batch agar data tidak diubah diam-diam.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'responses'
          AND column_name = 'batch_id'
    ) THEN
        IF EXISTS (SELECT 1 FROM public.responses WHERE batch_id IS NULL) THEN
            RAISE EXCEPTION 'Migrasi dibatalkan: terdapat data responses dengan batch_id NULL. Periksa dan tentukan batch untuk data tersebut terlebih dahulu.';
        END IF;
        ALTER TABLE public.responses ALTER COLUMN batch_id SET NOT NULL;
    END IF;
END
$$;

-- Siapkan autentikasi akun. Kolom user_id dibuat nullable sementara agar akun pertama
-- dapat dibuat melalui create_user.py dan data lama dapat dikaitkan tanpa menghapus data.
CREATE TABLE IF NOT EXISTS public.users (
    id            SERIAL PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.batches ADD COLUMN IF NOT EXISTS user_id INTEGER;
ALTER TABLE public.interpretations ADD COLUMN IF NOT EXISTS user_id INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.batches'::regclass
          AND conname = 'batches_user_id_fkey'
    ) THEN
        ALTER TABLE public.batches
            ADD CONSTRAINT batches_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.interpretations'::regclass
          AND conname = 'interpretations_user_id_fkey'
    ) THEN
        ALTER TABLE public.interpretations
            ADD CONSTRAINT interpretations_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE RESTRICT;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS batches_user_idx ON public.batches (user_id, id DESC);
CREATE INDEX IF NOT EXISTS interpretations_user_idx ON public.interpretations (user_id, id DESC);

-- Nama sequence dan indeks disesuaikan agar konsisten. Data dan nilai sequence tetap dipertahankan.
DO $$
BEGIN
    IF to_regclass('public.import_batches_id_seq') IS NOT NULL
       AND to_regclass('public.batches_id_seq') IS NULL THEN
        ALTER SEQUENCE public.import_batches_id_seq RENAME TO batches_id_seq;
    END IF;
    IF to_regclass('public.interpretation_runs_id_seq') IS NOT NULL
       AND to_regclass('public.interpretations_id_seq') IS NULL THEN
        ALTER SEQUENCE public.interpretation_runs_id_seq RENAME TO interpretations_id_seq;
    END IF;
    IF to_regclass('public.runs_media_idx') IS NOT NULL
       AND to_regclass('public.interpretations_media_idx') IS NULL THEN
        ALTER INDEX public.runs_media_idx RENAME TO interpretations_media_idx;
    END IF;
END
$$;

COMMIT;
