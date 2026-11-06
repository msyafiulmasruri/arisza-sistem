-- Skema PostgreSQL untuk sistem analisis sentimen Arisza Library & Learning.
-- Untuk database baru: jalankan file ini sekali melalui SQL Editor Neon.
-- Untuk database lama: jalankan migrasi_penamaan_tabel.sql terlebih dahulu.

CREATE TABLE IF NOT EXISTS batches (
    id          SERIAL PRIMARY KEY,
    filename    TEXT NOT NULL,
    total       INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued', 'running', 'done', 'failed')),
    error       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS responses (
    id          BIGSERIAL PRIMARY KEY,
    batch_id    INTEGER REFERENCES batches(id) ON DELETE CASCADE,
    media       TEXT NOT NULL,
    text        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'ok', 'empty')),
    label       TEXT CHECK (label IN ('negative', 'neutral', 'positive')),
    confidence  REAL,
    clean_text  TEXT,
    wc_text     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS responses_media_idx ON responses (media);
CREATE INDEX IF NOT EXISTS responses_batch_idx ON responses (batch_id, status);

CREATE TABLE IF NOT EXISTS interpretations (
    id              SERIAL PRIMARY KEY,
    media           TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'queued'
                    CHECK (status IN ('queued', 'running', 'done', 'failed')),
    n_texts         INTEGER,
    top_words       INTEGER DEFAULT 10,
    top_phrases     INTEGER DEFAULT 10,
    max_new_pola    INTEGER DEFAULT 220,
    max_new_saran   INTEGER DEFAULT 280,
    catatan         TEXT,
    error           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS interpretations_media_idx ON interpretations (media, id DESC);

CREATE TABLE IF NOT EXISTS interpretation_results (
    interpretation_id INTEGER NOT NULL
                       REFERENCES interpretations(id) ON DELETE CASCADE,
    stage             TEXT NOT NULL
                      CHECK (stage IN ('positive', 'neutral', 'negative', 'saran')),
    status            TEXT NOT NULL DEFAULT 'waiting'
                      CHECK (status IN ('waiting', 'running', 'done', 'failed')),
    result            TEXT,
    texts_used        INTEGER,
    texts_total       INTEGER,
    duration          REAL,
    detail            JSONB,
    error             TEXT,
    started_at        TIMESTAMPTZ,
    finished_at       TIMESTAMPTZ,
    PRIMARY KEY (interpretation_id, stage)
);

CREATE TABLE IF NOT EXISTS wordclouds (
    media       TEXT NOT NULL,
    label       TEXT NOT NULL CHECK (label IN ('positive', 'neutral', 'negative')),
    image       BYTEA NOT NULL,
    n_texts     INTEGER NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (media, label)
);
