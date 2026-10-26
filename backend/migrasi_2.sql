-- Jalankan sekali di Neon (SQL Editor) bila database sudah dibuat dengan schema.sql versi lama.
-- Aman dijalankan ulang.
alter table responses add column if not exists text_clean text;
alter table interpretation_stages add column if not exists chunks_done int not null default 0;
alter table interpretation_stages add column if not exists chunks_total int;
