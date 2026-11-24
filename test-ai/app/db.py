"""Akses PostgreSQL (Neon). Satu koneksi pendek per operasi agar aman saat Neon tidur."""
import psycopg
from psycopg.rows import dict_row

from . import config


def _buka():
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL belum diatur pada Space.")
    return psycopg.connect(
        config.DATABASE_URL, row_factory=dict_row, autocommit=True,
        prepare_threshold=None, connect_timeout=15,
    )


def jalankan(sql, params=()):
    with _buka() as c:
        c.execute(sql, params)


def ambil(sql, params=()):
    with _buka() as c:
        return c.execute(sql, params).fetchall()


def ambil_satu(sql, params=()):
    with _buka() as c:
        return c.execute(sql, params).fetchone()


def banyak(sql, daftar):
    with _buka() as c:
        with c.cursor() as cur:
            cur.executemany(sql, daftar)
