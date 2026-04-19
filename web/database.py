import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Literal, Tuple, Union

ConnKind = Literal["sqlite", "postgres"]
Conn = Union[sqlite3.Connection, Any]


def get_database_url() -> str | None:
    raw = os.getenv("DATABASE_URL")
    if raw is None or not str(raw).strip():
        return None
    return str(raw).strip()


def _use_sqlite(url: str | None) -> bool:
    if url is None:
        return True
    return url.lower().startswith("sqlite:")


def _sqlite_file(url: str | None) -> Path:
    if not url:
        return (Path(__file__).resolve().parent / "web_runs.db").resolve()
    if not url.lower().startswith("sqlite:"):
        raise ValueError("expected sqlite URL")
    prefix = "sqlite:///"
    if url.startswith(prefix):
        rest = url[len(prefix) :]
        p = Path(rest)
        if not p.is_absolute():
            return (Path(__file__).resolve().parent / p).resolve()
        return p.resolve()
    raise ValueError("use sqlite:///relative.db or sqlite:///C:/path.db")


@contextmanager
def get_conn() -> Generator[Tuple[ConnKind, Conn], None, None]:
    url = get_database_url()
    if _use_sqlite(url):
        path = _sqlite_file(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        try:
            yield ("sqlite", conn)
        finally:
            conn.close()
        return
    assert url is not None
    import psycopg2

    conn = psycopg2.connect(url)
    try:
        yield ("postgres", conn)
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as (kind, conn):
        if kind == "sqlite":
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS run_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    tickets_processed INTEGER NOT NULL,
                    workers_used INTEGER NOT NULL,
                    summary TEXT NOT NULL
                );
                """
            )
            conn.commit()
        else:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS run_history (
                        id SERIAL PRIMARY KEY,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        tickets_processed INTEGER NOT NULL,
                        workers_used INTEGER NOT NULL,
                        summary JSONB NOT NULL
                    );
                    """
                )
            conn.commit()


def save_run(tickets_processed: int, workers_used: int, summary: dict[str, Any]) -> int:
    payload = json.dumps(summary)
    with get_conn() as (kind, conn):
        if kind == "sqlite":
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO run_history (tickets_processed, workers_used, summary)
                VALUES (?, ?, ?);
                """,
                (tickets_processed, workers_used, payload),
            )
            conn.commit()
            return int(cur.lastrowid)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO run_history (tickets_processed, workers_used, summary)
                VALUES (%s, %s, %s)
                RETURNING id;
                """,
                (tickets_processed, workers_used, payload),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return int(new_id)


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    s = out.get("summary")
    if isinstance(s, str):
        out["summary"] = json.loads(s)
    return out


def list_runs(limit: int = 20) -> list[dict[str, Any]]:
    with get_conn() as (kind, conn):
        if kind == "sqlite":
            cur = conn.execute(
                """
                SELECT id, created_at, tickets_processed, workers_used, summary
                FROM run_history
                ORDER BY id DESC
                LIMIT ?;
                """,
                (limit,),
            )
            rows = [dict(r) for r in cur.fetchall()]
            return [_normalize_row(r) for r in rows]
        from psycopg2.extras import RealDictCursor

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, created_at, tickets_processed, workers_used, summary
                FROM run_history
                ORDER BY id DESC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = [dict(r) for r in cur.fetchall()]
            return [_normalize_row(r) for r in rows]
