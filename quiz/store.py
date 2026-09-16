from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from quiz import DATA_DIR


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AttemptStore:
    def __init__(self, path: Path | None = None) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.path = path or (DATA_DIR / "attempts.sqlite")
        self._init()
        self.backfill_logs()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def create(self, set_id: str, mode: str, time_limit_min: int, order: list[str]) -> str:
        attempt_id = uuid.uuid4().hex[:12]
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO attempts (
                    id, set_id, mode, started_at, time_limit_min, question_order_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (attempt_id, set_id, mode, _now(), time_limit_min, json.dumps(order)),
            )
        return attempt_id

    def get(self, attempt_id: str) -> dict | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM attempts WHERE id = ?", (attempt_id,)
            ).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["answers"] = json.loads(data.pop("answers_json") or "{}")
        data["flags"] = json.loads(data.pop("flags_json") or "[]")
        data["question_order"] = json.loads(data.pop("question_order_json") or "[]")
        result = data.pop("result_json")
        data["result"] = json.loads(result) if result else None
        return data

    def save_answers(self, attempt_id: str, answers: dict, flags: list[str]) -> None:
        with self._connect() as con:
            con.execute(
                """
                UPDATE attempts
                SET answers_json = ?, flags_json = ?
                WHERE id = ? AND finished_at IS NULL
                """,
                (json.dumps(answers, ensure_ascii=False), json.dumps(flags), attempt_id),
            )

    def finish(self, attempt_id: str, result: dict) -> None:
        with self._connect() as con:
            con.execute(
                """
                UPDATE attempts
                SET finished_at = ?, result_json = ?
                WHERE id = ?
                """,
                (_now(), json.dumps(result, ensure_ascii=False), attempt_id),
            )
        attempt = self.get(attempt_id)
        if attempt:
            self.log_attempt_result(attempt)

    def _init(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS attempts (
                    id TEXT PRIMARY KEY,
                    set_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    time_limit_min INTEGER NOT NULL,
                    answers_json TEXT NOT NULL DEFAULT '{}',
                    flags_json TEXT NOT NULL DEFAULT '[]',
                    question_order_json TEXT NOT NULL,
                    result_json TEXT
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS question_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id TEXT,
                    qid TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    ok INTEGER NOT NULL,
                    selected_json TEXT NOT NULL DEFAULT '[]',
                    source TEXT NOT NULL,
                    logged_at TEXT NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS memos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    qid TEXT,
                    title TEXT NOT NULL DEFAULT '',
                    body TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS schedule_days (
                    date TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    title TEXT NOT NULL,
                    target_questions INTEGER NOT NULL DEFAULT 12,
                    done INTEGER NOT NULL DEFAULT 0,
                    note TEXT NOT NULL DEFAULT ''
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    qid TEXT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def log_practice(self, attempt_id: str, qid: str, domain: str, ok: bool, selected: list[str]) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO question_logs
                    (attempt_id, qid, domain, ok, selected_json, source, logged_at)
                VALUES (?, ?, ?, ?, ?, 'practice', ?)
                """,
                (attempt_id, qid, domain, 1 if ok else 0, json.dumps(selected), _now()),
            )

    def log_attempt_result(self, attempt: dict) -> None:
        result = attempt.get("result") or {}
        details = result.get("details") or []
        if not details:
            return
        with self._connect() as con:
            exists = con.execute(
                """
                SELECT 1 FROM question_logs
                WHERE attempt_id = ? AND source = 'exam'
                LIMIT 1
                """,
                (attempt["id"],),
            ).fetchone()
            if exists:
                return
            for row in details:
                con.execute(
                    """
                    INSERT INTO question_logs
                        (attempt_id, qid, domain, ok, selected_json, source, logged_at)
                    VALUES (?, ?, ?, ?, ?, 'exam', ?)
                    """,
                    (
                        attempt["id"],
                        row["id"],
                        row["domain"],
                        1 if row["ok"] else 0,
                        json.dumps(row.get("selected") or []),
                        attempt.get("finished_at") or _now(),
                    ),
                )

    def list_attempts(self) -> list[dict]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT id, mode, started_at, finished_at, result_json
                FROM attempts
                WHERE finished_at IS NOT NULL
                ORDER BY finished_at DESC
                LIMIT 30
                """
            ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            result = json.loads(item.pop("result_json") or "null")
            item["result"] = result
            out.append(item)
        return out

    def question_stats(self) -> list[dict]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT qid, domain,
                       COUNT(*) AS n,
                       SUM(ok) AS correct,
                       MAX(logged_at) AS last_at
                FROM question_logs
                GROUP BY qid, domain
                ORDER BY (1.0 * SUM(ok) / COUNT(*)) ASC, n DESC
                """
            ).fetchall()
        out = []
        for row in rows:
            n = row["n"]
            correct = row["correct"] or 0
            out.append(
                {
                    "qid": row["qid"],
                    "domain": row["domain"],
                    "n": n,
                    "correct": correct,
                    "wrong": n - correct,
                    "percent": round(100 * correct / n) if n else 0,
                    "last_at": row["last_at"],
                }
            )
        return out

    def domain_stats(self) -> dict[str, dict]:
        stats: dict[str, dict] = {}
        for row in self.question_stats():
            bucket = stats.setdefault(row["domain"], {"n": 0, "correct": 0})
            bucket["n"] += row["n"]
            bucket["correct"] += row["correct"]
        for domain, bucket in stats.items():
            n = bucket["n"]
            bucket["percent"] = round(100 * bucket["correct"] / n) if n else 0
        return stats

    def weakest_domain(self) -> str | None:
        stats = self.domain_stats()
        if not stats:
            return None
        return min(stats.items(), key=lambda kv: kv[1]["percent"])[0]

    def recent_wrongs(self, limit: int = 8) -> list[dict]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT qid, domain, selected_json, logged_at
                FROM question_logs
                WHERE ok = 0
                ORDER BY logged_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "qid": row["qid"],
                "domain": row["domain"],
                "selected": json.loads(row["selected_json"] or "[]"),
                "logged_at": row["logged_at"],
            }
            for row in rows
        ]

    def get_setting(self, key: str, default: str = "") -> str:
        with self._connect() as con:
            row = con.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as con:
            con.execute(
                "INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def list_memos(self) -> list[dict]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM memos ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_memo(self, memo_id: int) -> dict | None:
        with self._connect() as con:
            row = con.execute("SELECT * FROM memos WHERE id = ?", (memo_id,)).fetchone()
        return dict(row) if row else None

    def save_memo(self, title: str, body: str, qid: str | None = None, memo_id: int | None = None) -> int:
        now = _now()
        qid = qid or None
        with self._connect() as con:
            if memo_id:
                con.execute(
                    """
                    UPDATE memos SET title = ?, body = ?, qid = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (title, body, qid, now, memo_id),
                )
                return memo_id
            cur = con.execute(
                """
                INSERT INTO memos (qid, title, body, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (qid, title, body, now, now),
            )
            return int(cur.lastrowid)

    def delete_memo(self, memo_id: int) -> None:
        with self._connect() as con:
            con.execute("DELETE FROM memos WHERE id = ?", (memo_id,))

    def memos_for_qid(self, qid: str) -> list[dict]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM memos WHERE qid = ? ORDER BY updated_at DESC",
                (qid,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_schedule(self) -> list[dict]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM schedule_days ORDER BY date"
            ).fetchall()
        return [dict(row) for row in rows]

    def replace_schedule(self, rows: list[dict]) -> None:
        with self._connect() as con:
            con.execute("DELETE FROM schedule_days")
            for row in rows:
                con.execute(
                    """
                    INSERT INTO schedule_days (date, domain, title, target_questions, done, note)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["date"],
                        row["domain"],
                        row["title"],
                        row["target_questions"],
                        row.get("done", 0),
                        row.get("note", ""),
                    ),
                )

    def toggle_schedule_day(self, day: str) -> None:
        with self._connect() as con:
            con.execute(
                "UPDATE schedule_days SET done = CASE done WHEN 1 THEN 0 ELSE 1 END WHERE date = ?",
                (day,),
            )

    def add_chat(self, role: str, content: str, qid: str | None = None) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO chat_messages (qid, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (qid or None, role, content, _now()),
            )

    def clear_chat(self, qid: str | None = None) -> None:
        with self._connect() as con:
            if qid:
                con.execute("DELETE FROM chat_messages WHERE qid = ?", (qid,))
            else:
                con.execute("DELETE FROM chat_messages WHERE qid IS NULL")

    def backfill_logs(self) -> None:
        with self._connect() as con:
            n = con.execute("SELECT COUNT(*) AS n FROM question_logs").fetchone()["n"]
        if n:
            return
        for row in self.list_attempts():
            full = self.get(row["id"])
            if full and full.get("result"):
                self.log_attempt_result(full)

    def list_chat(self, qid: str | None = None, limit: int = 40) -> list[dict]:
        with self._connect() as con:
            if qid:
                rows = con.execute(
                    """
                    SELECT * FROM chat_messages
                    WHERE qid = ?
                    ORDER BY id DESC LIMIT ?
                    """,
                    (qid, limit),
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT * FROM chat_messages WHERE qid IS NULL ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return list(reversed([dict(row) for row in rows]))

