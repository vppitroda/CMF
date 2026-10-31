"""PostgreSQL access: migration + connection. SQL for each command lives next to the command (cli.py)."""
from __future__ import annotations

from pathlib import Path

import psycopg

MIGRATION = Path(__file__).resolve().parents[2] / "db" / "001_init.sql"


def connect(dsn: str) -> psycopg.Connection:
    return psycopg.connect(dsn)


def migrate(conn: psycopg.Connection) -> None:
    """001_init.sql is written with IF NOT EXISTS, so running it every time is a no-op once applied."""
    with conn.cursor() as cur:
        cur.execute(MIGRATION.read_text(encoding="utf-8"))
    conn.commit()
