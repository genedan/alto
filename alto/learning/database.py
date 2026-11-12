"""The SQLite store: profiles, every answer given, and what is known about each question. Pure Python (no Qt)."""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE profiles (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    created_at  REAL NOT NULL
);

-- One row per answer given, including wrong ones: a question answered on the third try has three rows.
CREATE TABLE attempts (
    id          INTEGER PRIMARY KEY,
    profile_id  INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    exercise    TEXT NOT NULL,
    item_key    TEXT NOT NULL,
    attempt_no  INTEGER NOT NULL,   -- 1 for the first answer to this showing of the question
    answer      TEXT NOT NULL,
    correct     INTEGER NOT NULL,
    duration_ms INTEGER NOT NULL,   -- from the question appearing (first attempt) or the previous attempt (later ones)
    answered_at REAL NOT NULL
);
CREATE INDEX attempts_by_item ON attempts(profile_id, exercise, item_key);

-- What the learner's history says about one question. `strain` is how much practice it needs (higher is more).
CREATE TABLE items (
    profile_id       INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    exercise         TEXT NOT NULL,
    item_key         TEXT NOT NULL,
    strain           REAL NOT NULL,
    seen             INTEGER NOT NULL DEFAULT 0,  -- times the question was shown and answered
    first_try_right  INTEGER NOT NULL DEFAULT 0,
    wrong_attempts   INTEGER NOT NULL DEFAULT 0,
    total_first_ms   INTEGER NOT NULL DEFAULT 0,  -- time to the first answer, summed over showings
    last_seen        REAL NOT NULL,
    signature        TEXT NOT NULL,               -- the exercise settings it was asked under
    payload          TEXT NOT NULL,               -- the question itself, so it can be asked again
    PRIMARY KEY (profile_id, exercise, item_key)
);
"""


@dataclass(frozen=True)
class Profile:
    id: int
    name: str


@dataclass(frozen=True)
class ItemRecord:
    strain: float
    seen: int
    first_try_right: int
    wrong_attempts: int
    total_first_ms: int
    last_seen: float
    signature: str
    payload: str
    item_key: str = ""


class Database:
    def __init__(self, path: str | Path = ":memory:"):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def _migrate(self) -> None:
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            with self.conn:
                self.conn.executescript(_SCHEMA)
                self.conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def close(self) -> None:
        self.conn.close()

    # -- profiles --------------------------------------------------------------------------------------------

    def profiles(self) -> list[Profile]:
        rows = self.conn.execute("SELECT id, name FROM profiles ORDER BY name COLLATE NOCASE").fetchall()
        return [Profile(r["id"], r["name"]) for r in rows]

    def profile(self, profile_id: int) -> Profile | None:
        r = self.conn.execute("SELECT id, name FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        return Profile(r["id"], r["name"]) if r else None

    def add_profile(self, name: str) -> Profile:
        """Create a profile. Raises ValueError for an empty name or one that is taken (case does not matter)."""
        name = " ".join(name.split())
        if not name:
            raise ValueError("Enter a name for the profile.")
        try:
            with self.conn:
                cur = self.conn.execute("INSERT INTO profiles (name, created_at) VALUES (?, ?)", (name, time.time()))
        except sqlite3.IntegrityError:
            raise ValueError(f"There is already a profile called {name}.") from None
        return Profile(cur.lastrowid, name)

    def delete_profile(self, profile_id: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))

    # -- answers and what they say about each question -----------------------------------------------------------

    def get_item(self, profile_id: int, exercise: str, item_key: str) -> ItemRecord | None:
        r = self.conn.execute("SELECT * FROM items WHERE profile_id = ? AND exercise = ? AND item_key = ?",
                              (profile_id, exercise, item_key)).fetchone()
        return self._item(r) if r else None

    def save_item(self, profile_id: int, exercise: str, item_key: str, item: ItemRecord) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO items (profile_id, exercise, item_key, strain, seen, first_try_right, wrong_attempts, "
                "total_first_ms, last_seen, signature, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (profile_id, exercise, item_key) DO UPDATE SET strain = excluded.strain, "
                "seen = excluded.seen, first_try_right = excluded.first_try_right, "
                "wrong_attempts = excluded.wrong_attempts, total_first_ms = excluded.total_first_ms, "
                "last_seen = excluded.last_seen, signature = excluded.signature, payload = excluded.payload",
                (profile_id, exercise, item_key, item.strain, item.seen, item.first_try_right, item.wrong_attempts,
                 item.total_first_ms, item.last_seen, item.signature, item.payload))

    def add_attempt(self, profile_id: int, exercise: str, item_key: str, attempt_no: int, answer: str, correct: bool,
                    duration_ms: int, answered_at: float) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO attempts (profile_id, exercise, item_key, attempt_no, answer, correct, duration_ms, "
                "answered_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (profile_id, exercise, item_key, attempt_no, answer, int(correct), duration_ms, answered_at))

    def attempts(self, profile_id: int, exercise: str | None = None) -> list[sqlite3.Row]:
        sql, args = "SELECT * FROM attempts WHERE profile_id = ?", [profile_id]
        if exercise:
            sql, args = sql + " AND exercise = ?", args + [exercise]
        return self.conn.execute(sql + " ORDER BY id", args).fetchall()

    @staticmethod
    def _scope(profile_ids: list[int] | None, exercise: str | None, time_column: str, since: float | None) -> tuple[str, list]:
        """The WHERE clause shared by the statistics queries: which profiles, which exercise, and from when."""
        clauses, args = ["1 = 1"], []
        if profile_ids is not None:
            clauses.append(f"profile_id IN ({','.join('?' * len(profile_ids)) or 'NULL'})")
            args += list(profile_ids)
        if exercise:
            clauses.append("exercise = ?")
            args.append(exercise)
        if since is not None:
            clauses.append(f"{time_column} >= ?")
            args.append(since)
        return " AND ".join(clauses), args

    def attempts_in(self, profile_ids: list[int] | None = None, exercise: str | None = None,
                    since: float | None = None) -> list[sqlite3.Row]:
        """Answers given, oldest first. `profile_ids` of None means every profile."""
        where, args = self._scope(profile_ids, exercise, "answered_at", since)
        return self.conn.execute("SELECT exercise, attempt_no, correct, duration_ms, answered_at FROM attempts "
                                 f"WHERE {where} ORDER BY answered_at, id", args).fetchall()

    def strained_items(self, profile_ids: list[int] | None = None, exercise: str | None = None,
                       since: float | None = None, min_strain: float = 0.0, limit: int = 10) -> list[sqlite3.Row]:
        """The questions that need most practice, the same question from different profiles counted together."""
        where, args = self._scope(profile_ids, exercise, "last_seen", since)
        return self.conn.execute(
            "SELECT exercise, item_key, AVG(strain) AS strain, SUM(seen) AS seen, SUM(wrong_attempts) AS wrong, "
            "MAX(payload) AS payload FROM items "
            f"WHERE {where} GROUP BY exercise, item_key HAVING SUM(seen) > 0 AND AVG(strain) >= ? "
            "ORDER BY strain DESC, wrong DESC LIMIT ?", (*args, min_strain, limit)).fetchall()

    # -- for browsing ----------------------------------------------------------------------------------------------

    def count_attempts(self, profile_id: int) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM attempts WHERE profile_id = ?", (profile_id,)).fetchone()[0]

    def attempt_rows(self, profile_id: int, limit: int = 10000) -> list[sqlite3.Row]:
        """The newest answers first, each with the stored question it was an answer to (if that is still known)."""
        return self.conn.execute(
            "SELECT a.answered_at, a.exercise, a.item_key, a.answer, a.correct, a.attempt_no, a.duration_ms, i.payload "
            "FROM attempts a LEFT JOIN items i ON i.profile_id = a.profile_id AND i.exercise = a.exercise "
            "AND i.item_key = a.item_key WHERE a.profile_id = ? ORDER BY a.id DESC LIMIT ?", (profile_id, limit)).fetchall()

    def item_rows(self, profile_id: int, limit: int = 10000) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM items WHERE profile_id = ? ORDER BY strain DESC, last_seen DESC LIMIT ?",
                                 (profile_id, limit)).fetchall()

    def profile_rows(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT p.id, p.name, p.created_at, (SELECT COUNT(*) FROM attempts a WHERE a.profile_id = p.id) AS attempts, "
            "(SELECT COUNT(*) FROM items i WHERE i.profile_id = p.id) AS questions FROM profiles p "
            "ORDER BY p.name COLLATE NOCASE").fetchall()

    def replay_candidates(self, profile_id: int, exercise: str, signature: str, hardest: int = 25,
                          random_extra: int = 10) -> list[ItemRecord]:
        """Questions asked before under these same settings: the ones that need most practice, plus a few at random."""
        base = "FROM items WHERE profile_id = ? AND exercise = ? AND signature = ?"
        args = (profile_id, exercise, signature)
        rows = self.conn.execute(f"SELECT * {base} ORDER BY strain DESC, last_seen ASC LIMIT ?", (*args, hardest)).fetchall()
        rows += self.conn.execute(f"SELECT * {base} ORDER BY RANDOM() LIMIT ?", (*args, random_extra)).fetchall()
        seen, out = set(), []
        for r in rows:
            if r["item_key"] not in seen:
                seen.add(r["item_key"])
                out.append(self._item(r))
        return out

    @staticmethod
    def _item(r: sqlite3.Row) -> ItemRecord:
        return ItemRecord(r["strain"], r["seen"], r["first_try_right"], r["wrong_attempts"], r["total_first_ms"],
                          r["last_seen"], r["signature"], r["payload"], r["item_key"])
