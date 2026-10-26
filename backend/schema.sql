-- Jalankan sekali di Neon (SQL Editor).

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
  text_clean  text,
  label       text check (label in ('negative','neutral','positive')),
  confidence  real,
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
  chunks_done  int not null default 0,
  chunks_total int,
  duration     real,
  error        text,
  started_at   timestamptz,
  finished_at  timestamptz,
  primary key (run_id, stage)
);

-- Disarankan: akun terpisah untuk Space dengan hak terbatas.
-- create role arisza_space login password 'GANTI_DENGAN_KATA_SANDI_KUAT';
-- grant select, update on responses to arisza_space;
-- grant select, update on import_batches to arisza_space;
-- grant select, update on interpretation_runs, interpretation_stages to arisza_space;
-- grant usage, select on all sequences in schema public to arisza_space;
