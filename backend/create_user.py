"""Create an Arisza login account and attach legacy unowned records to the first account."""
from __future__ import annotations

import argparse
import getpass
import os
import re
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

# Muat konfigurasi backend/.env untuk penggunaan lokal; environment yang sudah ada tetap diprioritaskan.
load_dotenv(Path(__file__).resolve().with_name(".env"), override=False)

from security import hash_password

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def main() -> int:
    parser = argparse.ArgumentParser(description="Membuat akun login Arisza Library & Learning.")
    parser.add_argument("--email", help="Email akun. Jika tidak diisi, email akan diminta secara interaktif.")
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print("DATABASE_URL belum diatur.", file=sys.stderr)
        return 1

    email = (args.email or input("Email akun: ")).strip().lower()
    if len(email) > 254 or not EMAIL_RE.fullmatch(email):
        print("Format email tidak valid atau melebihi 254 karakter.", file=sys.stderr)
        return 1

    password = getpass.getpass("Kata sandi (minimal 12 karakter): ")
    confirmation = getpass.getpass("Ulangi kata sandi: ")
    if password != confirmation:
        print("Konfirmasi kata sandi tidak sama.", file=sys.stderr)
        return 1

    try:
        password_hash = hash_password(password)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        with psycopg.connect(database_url) as conn:
            created = conn.execute(
                "INSERT INTO users (email, password_hash) VALUES (%s, %s) "
                "ON CONFLICT (email) DO NOTHING RETURNING id",
                (email, password_hash),
            ).fetchone()
            if not created:
                raise RuntimeError("Email tersebut sudah terdaftar. Gunakan email lain.")
            user_id = created[0]

            # Pada migrasi database lama, user_id ditambahkan nullable agar akun pertama
            # dapat mengambil alih record lama sebelum kolom diwajibkan (NOT NULL).
            conn.execute("UPDATE batches SET user_id = %s WHERE user_id IS NULL", (user_id,))
            conn.execute("UPDATE interpretations SET user_id = %s WHERE user_id IS NULL", (user_id,))

            sisa_batch = conn.execute("SELECT count(*) FROM batches WHERE user_id IS NULL").fetchone()[0]
            sisa_interpretasi = conn.execute(
                "SELECT count(*) FROM interpretations WHERE user_id IS NULL"
            ).fetchone()[0]
            if sisa_batch or sisa_interpretasi:
                raise RuntimeError("Masih ada data tanpa pemilik. Transaksi dibatalkan; periksa database.")

            conn.execute("ALTER TABLE batches ALTER COLUMN user_id SET NOT NULL")
            conn.execute("ALTER TABLE interpretations ALTER COLUMN user_id SET NOT NULL")

        print(f"Akun {email} berhasil dibuat.")
        print("Data lama yang belum memiliki akun telah dikaitkan dengan akun ini jika tersedia.")
        return 0
    except Exception as exc:
        print(f"Gagal membuat akun: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
