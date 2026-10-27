-- MIGRASI 2 (versi lengkap dan aman dijalankan ulang)
-- Jalankan di Neon (SQL Editor), pada database yang sama dengan DATABASE_URL backend.
--
--  * Database BARU/KOSONG   -> membuat semua tabel.
--  * Database LAMA          -> tabel lama dibiarkan, hanya kolom/tabel baru yang ditambahkan.
--
-- Bila muncul galat 'relation ... does not exist', periksa dulu project, branch, dan database
-- yang dipilih di bagian atas SQL Editor.

create table if not exists import_batches (
  id          serial primary key,
  filename    text not null,
  total       int  not null default 0,
  status      text not null default 'queued' check (status in ('queued','running','done','failed')),
  error       text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create table if not exists responses (
  id          bigserial primary key,
  batch_id    int references import_batches(id) on delete cascade,
  media       text not null,
  text        text not null,
  status      text not null default 'pending' check (status in ('pending','ok','empty')),
  label       text check (label in ('negative','neutral','positive')),
  confidence  real,
  clean_text  text,   -- teks hasil preprocessing
  wc_text     text,   -- teks untuk Word Cloud (tanpa stopword, di-stem)
  created_at  timestamptz not null default now()
);
create index if not exists responses_media_idx on responses (media);
create index if not exists responses_batch_idx on responses (batch_id, status);

create table if not exists interpretation_runs (
  id              serial primary key,
  media           text not null,
  status          text not null default 'queued' check (status in ('queued','running','done','failed')),
  n_texts         int,
  top_k           int,
  max_new_tokens  int,
  chunk_size      int,
  catatan         text,
  error           text,
  created_at      timestamptz not null default now(),
  started_at      timestamptz,
  finished_at     timestamptz,
  updated_at      timestamptz not null default now()
);
create index if not exists runs_media_idx on interpretation_runs (media, id desc);

create table if not exists interpretation_stages (
  run_id       int not null references interpretation_runs(id) on delete cascade,
  stage        text not null check (stage in ('positive','neutral','negative','saran')),
  status       text not null default 'waiting' check (status in ('waiting','running','done','failed')),
  result       text,
  texts_used   int,
  texts_total  int,
  duration     real,
  chunks_total int,
  chunks_done  int,
  detail       jsonb,
  error        text,
  started_at   timestamptz,
  finished_at  timestamptz,
  primary key (run_id, stage)
);

create table if not exists wordclouds (
  media       text not null,
  label       text not null check (label in ('positive','neutral','negative')),
  image       bytea not null,
  n_texts     int not null,
  updated_at  timestamptz not null default now(),
  primary key (media, label)
);

-- ---- Untuk database LAMA: tambahkan kolom yang belum ada (tidak berpengaruh bila sudah ada) ----
alter table responses            add column if not exists clean_text   text;   -- teks hasil preprocessing
alter table responses            add column if not exists wc_text      text;   -- teks untuk Word Cloud
alter table interpretation_runs  add column if not exists chunk_size   int;    -- teks unik per bagian
alter table interpretation_stages add column if not exists chunks_total int;   -- jumlah langkah Llama
alter table interpretation_stages add column if not exists chunks_done  int;
alter table interpretation_stages add column if not exists detail       jsonb; -- waktu tiap langkah

-- ---- Bila Space memakai akun terpisah, beri hak yang cukup (buka komentar dan sesuaikan) ----
-- grant select, update on responses to arisza_space;
-- grant select, update on import_batches to arisza_space;
-- grant select, update on interpretation_runs, interpretation_stages to arisza_space;
-- grant select, insert, update, delete on wordclouds to arisza_space;
-- grant usage, select on all sequences in schema public to arisza_space;