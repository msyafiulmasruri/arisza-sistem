-- Migrasi nama tabel lama ke nama tabel baru tanpa menghapus data.
-- Jalankan satu kali pada database lama saat seluruh layanan/job dihentikan.
-- Ambil backup database sebelum menjalankan migrasi ini.

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
