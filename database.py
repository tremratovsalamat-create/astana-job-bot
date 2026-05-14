import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)
DB_PATH = "jobs_bot.db"


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create all tables if not exist."""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id     INTEGER PRIMARY KEY,
                    username    TEXT DEFAULT '',
                    first_name  TEXT DEFAULT '',
                    joined_at   TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS saved_jobs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    job_id      TEXT NOT NULL,
                    job_data    TEXT NOT NULL,
                    saved_at    TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, job_id)
                );

                CREATE TABLE IF NOT EXISTS seen_jobs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    job_id      TEXT NOT NULL,
                    seen_at     TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, job_id)
                );

                CREATE TABLE IF NOT EXISTS resumes (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    file_id     TEXT NOT NULL,
                    filename    TEXT NOT NULL,
                    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS search_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    query       TEXT NOT NULL,
                    searched_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
        logger.info("Database initialized.")

    # ── Users ──────────────────────────────────────────────

    def add_user(self, user_id: int, username: str, first_name: str):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username, first_name)
            )
            conn.commit()

    def get_user(self, user_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def get_all_users(self) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT user_id FROM users").fetchall()
            return [dict(r) for r in rows]

    # ── Saved Jobs ─────────────────────────────────────────

    def save_job(self, user_id: int, job: dict):
        with self._get_conn() as conn:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO saved_jobs (user_id, job_id, job_data) VALUES (?, ?, ?)",
                    (user_id, job["id"], json.dumps(job, ensure_ascii=False))
                )
                conn.commit()
            except Exception as e:
                logger.error(f"save_job error: {e}")

    def unsave_job(self, user_id: int, job_id: str):
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM saved_jobs WHERE user_id = ? AND job_id = ?",
                (user_id, job_id)
            )
            conn.commit()

    def get_saved_jobs(self, user_id: int) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT job_id, job_data, saved_at FROM saved_jobs "
                "WHERE user_id = ? ORDER BY saved_at DESC",
                (user_id,)
            ).fetchall()
            result = []
            for row in rows:
                data = json.loads(row["job_data"])
                data["saved_at"] = row["saved_at"]
                result.append(data)
            return result

    def is_job_saved(self, user_id: int, job_id: str) -> bool:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM saved_jobs WHERE user_id = ? AND job_id = ?",
                (user_id, job_id)
            ).fetchone()
            return row is not None

    # ── Seen Jobs ──────────────────────────────────────────

    def mark_seen(self, user_id: int, job_id: str):
        with self._get_conn() as conn:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO seen_jobs (user_id, job_id) VALUES (?, ?)",
                    (user_id, job_id)
                )
                conn.commit()
            except Exception as e:
                logger.debug(f"mark_seen: {e}")

    def get_seen_jobs(self, user_id: int) -> set:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT job_id FROM seen_jobs WHERE user_id = ?",
                (user_id,)
            ).fetchall()
            return {r["job_id"] for r in rows}

    def clear_seen(self, user_id: int):
        """Clear seen history so user can see all jobs again."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM seen_jobs WHERE user_id = ?", (user_id,))
            conn.commit()

    # ── Resumes ────────────────────────────────────────────

    def save_resume(self, user_id: int, file_id: str, filename: str):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO resumes (user_id, file_id, filename) VALUES (?, ?, ?)",
                (user_id, file_id, filename)
            )
            conn.commit()

    def get_resumes(self, user_id: int) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT file_id, filename, uploaded_at FROM resumes "
                "WHERE user_id = ? ORDER BY uploaded_at DESC",
                (user_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_resume(self, user_id: int, file_id: str):
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM resumes WHERE user_id = ? AND file_id = ?",
                (user_id, file_id)
            )
            conn.commit()

    # ── Search History ─────────────────────────────────────

    def log_search(self, user_id: int, query: str):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO search_history (user_id, query) VALUES (?, ?)",
                (user_id, query)
            )
            conn.commit()

    def get_search_history(self, user_id: int, limit: int = 10) -> list[str]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT query FROM search_history "
                "WHERE user_id = ? ORDER BY searched_at DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
            return [r["query"] for r in rows]

    # ── Stats ──────────────────────────────────────────────

    def get_stats(self) -> dict:
        with self._get_conn() as conn:
            users = conn.execute("SELECT COUNT(*) as n FROM users").fetchone()["n"]
            saves = conn.execute("SELECT COUNT(*) as n FROM saved_jobs").fetchone()["n"]
            resumes = conn.execute("SELECT COUNT(*) as n FROM resumes").fetchone()["n"]
            searches = conn.execute("SELECT COUNT(*) as n FROM search_history").fetchone()["n"]
            return {
                "total_users": users,
                "total_saves": saves,
                "total_resumes": resumes,
                "total_searches": searches,
            }
