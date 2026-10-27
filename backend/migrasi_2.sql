-- Migrasi 2: kolom teks hasil preprocessing, Word Cloud berbentuk gambar, dan progres interpretasi bertahap.
-- Jalankan sekali di Neon (SQL Editor) pada database yang sudah ada. Aman dijalankan ulang.

alter table responses add column if not exists clean_text text;   -- teks hasil preprocessing
alter table responses add column if not exists wc_text text;      -- teks untuk Word Cloud (tanpa stopword, di-stem)

alter table interpretation_runs   add column if not exists chunk_size int;     -- jumlah teks unik per bagian
alter table interpretation_stages add column if not exists chunks_total int;   -- jumlah langkah Llama pada tahap ini
alter table interpretation_stages add column if not exists chunks_done int;
alter table interpretation_stages add column if not exists detail jsonb;       -- waktu tiap langkah

create table if not exists wordclouds (
  media       text not null,
  label       text not null check (label in ('positive','neutral','negative')),
  image       bytea not null,
  n_texts     int not null,
  updated_at  timestamptz not null default now(),
  primary key (media, label)
);

-- Bila Space memakai akun terpisah, beri hak yang cukup:
-- grant select, insert, update, delete on wordclouds to arisza_space;
