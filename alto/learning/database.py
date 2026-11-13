"""
The SQLite store: profiles, every answer given, and what is known about each question. Pure Python (no Qt).

Examples
--------
>>> db = Database()
>>> ada = db.add_profile("Ada")
>>> db.add_attempt(ada.id, exercise="NoteNames", item_key="k", attempt_no=1, answer="C", correct=True,
...                duration_ms=2000, answered_at=100.0)
>>> db.count_attempts(ada.id)
1
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import (
    KW_ONLY,
    dataclass,
)
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
    """
    A person who practises: their answers are kept apart from everyone else's.

    Attributes
    ----------
    id : int
        The profile's row number in the database.
    name : str
        The name shown in the interface. Keyword-only.

    Examples
    --------
    >>> Profile(1, name="Ada")
    Profile(id=1, name='Ada')
    """

    id: int
    _: KW_ONLY
    name: str


@dataclass(frozen=True)
class ItemRecord:
    """
    What a profile's history says about one question.

    Attributes
    ----------
    strain : float
        How much practice the question needs; higher means it comes back sooner.
    seen : int
        How many times the question was shown and answered. Keyword-only.
    first_try_right : int
        How many of those showings were answered right first time. Keyword-only.
    wrong_attempts : int
        How many wrong answers there have been in all. Keyword-only.
    total_first_ms : int
        Time to the first answer, summed over the showings, in milliseconds. Keyword-only.
    last_seen : float
        When the question was last answered, as a timestamp. Keyword-only.
    signature : str
        The exercise settings it was asked under; it is only asked again while these are unchanged. Keyword-only.
    payload : str
        The question itself as JSON, so it can be asked again. Keyword-only.
    item_key : str, default ""
        The question's identity. Empty when the record is built to be saved, filled in when it is read back. Keyword-only.

    Examples
    --------
    >>> record = ItemRecord(2.0, seen=3, first_try_right=1, wrong_attempts=2, total_first_ms=9000,
    ...                     last_seen=100.0, signature="s", payload="{}")
    >>> record.seen
    3
    """

    strain: float
    _: KW_ONLY
    seen: int
    first_try_right: int
    wrong_attempts: int
    total_first_ms: int
    last_seen: float
    signature: str
    payload: str
    item_key: str = ""


class Database:
    """
    The SQLite database behind profiles, answers and per-question history.

    Attributes
    ----------
    conn : sqlite3.Connection
        The open connection, with rows returned as `sqlite3.Row` so columns can be read by name.

    Examples
    --------
    >>> db = Database()  # in memory; give a path to keep it on disk
    >>> db.profiles()
    []
    >>> db.add_profile("Ada")
    Profile(id=1, name='Ada')
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        """
        Open the database, creating it and its tables if they do not exist.

        Parameters
        ----------
        path : str or Path, default ":memory:"
            The file to use, whose folder is created if needed, or ":memory:" for a throwaway database.

        Examples
        --------
        >>> db = Database()
        >>> db.conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        True
        """
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def _migrate(self) -> None:
        """
        Create the tables if the database is new.

        Examples
        --------
        >>> db = Database()
        >>> db._migrate()  # already up to date: nothing happens
        >>> sorted(r["name"] for r in db.conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'"))
        ['attempts', 'items', 'profiles']
        """
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            with self.conn:
                self.conn.executescript(_SCHEMA)
                self.conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def close(self) -> None:
        """
        Close the connection.

        Examples
        --------
        >>> db = Database()
        >>> db.close()
        """
        self.conn.close()

    # -- profiles --------------------------------------------------------------------------------------------

    def profiles(self) -> list[Profile]:
        """
        Return every profile, sorted by name without regard to case.

        Returns
        -------
        list of Profile
            The profiles.

        Examples
        --------
        >>> db = Database()
        >>> _ = db.add_profile("ben")
        >>> _ = db.add_profile("Ada")
        >>> [p.name for p in db.profiles()]
        ['Ada', 'ben']
        """
        rows = self.conn.execute("SELECT id, name FROM profiles ORDER BY name COLLATE NOCASE").fetchall()
        return [Profile(r["id"], name=r["name"]) for r in rows]

    def profile(self, profile_id: int) -> Profile | None:
        """
        Return one profile by its id.

        Parameters
        ----------
        profile_id : int
            The profile's id.

        Returns
        -------
        Profile or None
            The profile, or None if there is none with that id.

        Examples
        --------
        >>> db = Database()
        >>> ada = db.add_profile("Ada")
        >>> # noinspection PyUnresolvedReferences
        >>> db.profile(ada.id).name
        'Ada'
        >>> db.profile(999) is None
        True
        """
        r = self.conn.execute("SELECT id, name FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        return Profile(r["id"], name=r["name"]) if r else None

    def add_profile(self, name: str) -> Profile:
        """
        Create a profile.

        Parameters
        ----------
        name : str
            The name. Runs of spaces are collapsed to one, and case does not matter when checking for a duplicate.

        Returns
        -------
        Profile
            The new profile.

        Raises
        ------
        ValueError
            If the name is empty, or is already taken.

        Examples
        --------
        >>> db = Database()
        >>> db.add_profile("  Ada   Lovelace ")
        Profile(id=1, name='Ada Lovelace')
        >>> db.add_profile("ada lovelace")
        Traceback (most recent call last):
            ...
        ValueError: There is already a profile called ada lovelace.
        """
        name = " ".join(name.split())
        if not name:
            raise ValueError("Enter a name for the profile.")
        try:
            with self.conn:
                cur = self.conn.execute("INSERT INTO profiles (name, created_at) VALUES (?, ?)", (name, time.time()))
        except sqlite3.IntegrityError:
            raise ValueError(f"There is already a profile called {name}.") from None
        row_id = cur.lastrowid
        assert row_id is not None  # an INSERT always gives the new row an id
        return Profile(row_id, name=name)

    def delete_profile(self, profile_id: int) -> None:
        """
        Delete a profile together with all of its answers and question history.

        Parameters
        ----------
        profile_id : int
            The profile's id.

        Examples
        --------
        >>> db = Database()
        >>> ada = db.add_profile("Ada")
        >>> db.delete_profile(ada.id)
        >>> db.profiles()
        []
        """
        with self.conn:
            self.conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))

    # -- answers and what they say about each question -----------------------------------------------------------

    def get_item(
        self,
        profile_id: int,
        *,
        exercise: str,
        item_key: str,
    ) -> ItemRecord | None:
        """
        Return what is known about one question for a profile.

        Parameters
        ----------
        profile_id : int
            The profile's id.
        exercise : str
            The exercise's class name. Keyword-only.
        item_key : str
            The question's identity. Keyword-only.

        Returns
        -------
        ItemRecord or None
            The record, or None if the question has never been answered.

        Examples
        --------
        >>> db = Database()
        >>> ada = db.add_profile("Ada")
        >>> db.get_item(ada.id, exercise="NoteNames", item_key="k") is None
        True
        """
        r = self.conn.execute(
            "SELECT * FROM items WHERE profile_id = ? AND exercise = ? AND item_key = ?",
            (profile_id, exercise, item_key),
        ).fetchone()
        return self._item(r) if r else None

    def save_item(
        self,
        profile_id: int,
        *,
        exercise: str,
        item_key: str,
        item: ItemRecord,
    ) -> None:
        """
        Store what is known about a question, replacing any earlier record of it.

        Parameters
        ----------
        profile_id : int
            The profile's id.
        exercise : str
            The exercise's class name. Keyword-only.
        item_key : str
            The question's identity. Keyword-only.
        item : ItemRecord
            What to store. Keyword-only.

        Examples
        --------
        >>> db = Database()
        >>> ada = db.add_profile("Ada")
        >>> record = ItemRecord(2.0, seen=1, first_try_right=0, wrong_attempts=1, total_first_ms=3000,
        ...                     last_seen=100.0, signature="s", payload="{}")
        >>> db.save_item(ada.id, exercise="NoteNames", item_key="k", item=record)
        >>> # noinspection PyUnresolvedReferences
        >>> db.get_item(ada.id, exercise="NoteNames", item_key="k").strain
        2.0
        """
        with self.conn:
            self.conn.execute(
                "INSERT INTO items (profile_id, exercise, item_key, strain, seen, first_try_right, wrong_attempts, "
                "total_first_ms, last_seen, signature, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (profile_id, exercise, item_key) DO UPDATE SET strain = excluded.strain, "
                "seen = excluded.seen, first_try_right = excluded.first_try_right, "
                "wrong_attempts = excluded.wrong_attempts, total_first_ms = excluded.total_first_ms, "
                "last_seen = excluded.last_seen, signature = excluded.signature, payload = excluded.payload",
                (
                    profile_id,
                    exercise,
                    item_key,
                    item.strain,
                    item.seen,
                    item.first_try_right,
                    item.wrong_attempts,
                    item.total_first_ms,
                    item.last_seen,
                    item.signature,
                    item.payload,
                ),
            )

    def add_attempt(
        self,
        profile_id: int,
        *,
        exercise: str,
        item_key: str,
        attempt_no: int,
        answer: str,
        correct: bool,
        duration_ms: int,
        answered_at: float,
    ) -> None:
        """
        Log one answer, right or wrong.

        Parameters
        ----------
        profile_id : int
            The profile's id.
        exercise : str
            The exercise's class name. Keyword-only.
        item_key : str
            The question's identity. Keyword-only.
        attempt_no : int
            1 for the first answer to this showing of the question, 2 for the second and so on. Keyword-only.
        answer : str
            What was answered. Keyword-only.
        correct : bool
            Whether it was right. Keyword-only.
        duration_ms : int
            How long it took, in milliseconds. Keyword-only.
        answered_at : float
            When it was answered, as a timestamp. Keyword-only.

        Examples
        --------
        >>> db = Database()
        >>> ada = db.add_profile("Ada")
        >>> db.add_attempt(ada.id, exercise="NoteNames", item_key="k", attempt_no=1, answer="C", correct=False,
        ...                duration_ms=1500, answered_at=50.0)
        >>> [(r["answer"], r["correct"]) for r in db.attempts(ada.id)]
        [('C', 0)]
        """
        with self.conn:
            self.conn.execute(
                "INSERT INTO attempts (profile_id, exercise, item_key, attempt_no, answer, correct, duration_ms, "
                "answered_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    profile_id,
                    exercise,
                    item_key,
                    attempt_no,
                    answer,
                    int(correct),
                    duration_ms,
                    answered_at,
                ),
            )

    def attempts(
        self,
        profile_id: int,
        *,
        exercise: str | None = None,
    ) -> list[sqlite3.Row]:
        """
        Return all of a profile's answers in the order they were given.

        Parameters
        ----------
        profile_id : int
            The profile's id.
        exercise : str or None, default None
            Only answers to this exercise (its class name); every exercise if None. Keyword-only.

        Returns
        -------
        list of sqlite3.Row
            Every column of each answer.

        Examples
        --------
        >>> db = Database()
        >>> ada = db.add_profile("Ada")
        >>> for i, name in enumerate(["NoteNames", "IntervalNames"]):
        ...     db.add_attempt(ada.id, exercise=name, item_key="k", attempt_no=1, answer="x", correct=True,
        ...                    duration_ms=1000, answered_at=float(i))
        >>> [r["exercise"] for r in db.attempts(ada.id)]
        ['NoteNames', 'IntervalNames']
        >>> [r["exercise"] for r in db.attempts(ada.id, exercise="IntervalNames")]
        ['IntervalNames']
        """
        sql, args = "SELECT * FROM attempts WHERE profile_id = ?", [profile_id]
        if exercise:
            sql, args = sql + " AND exercise = ?", args + [exercise]
        return self.conn.execute(sql + " ORDER BY id", args).fetchall()

    @staticmethod
    def _scope(
        profile_ids: list[int] | None,
        *,
        exercise: str | None,
        time_column: str,
        since: float | None,
    ) -> tuple[str, list]:
        """
        Return the WHERE clause shared by the statistics queries: which profiles, which exercise, and from when.

        Parameters
        ----------
        profile_ids : list of int or None
            The profiles to include; every profile if None.
        exercise : str or None
            Only this exercise (its class name); every exercise if None. Keyword-only.
        time_column : str
            The column that `since` is compared with. Keyword-only.
        since : float or None
            Only rows from this timestamp on; the whole history if None. Keyword-only.

        Returns
        -------
        tuple of (str, list)
            The SQL condition, with `?` placeholders, and the values for them.

        Examples
        --------
        >>> Database._scope([1, 2], exercise="NoteNames", time_column="answered_at", since=10.0)
        ('1 = 1 AND profile_id IN (?,?) AND exercise = ? AND answered_at >= ?', [1, 2, 'NoteNames', 10.0])
        >>> Database._scope(None, exercise=None, time_column="answered_at", since=None)
        ('1 = 1', [])
        """
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

    def attempts_in(
        self,
        profile_ids: list[int] | None = None,
        *,
        exercise: str | None = None,
        since: float | None = None,
    ) -> list[sqlite3.Row]:
        """
        Return answers given, oldest first, for some profiles, an exercise and a period.

        Parameters
        ----------
        profile_ids : list of int or None, default None
            The profiles to include; every profile if None.
        exercise : str or None, default None
            Only this exercise (its class name); every exercise if None. Keyword-only.
        since : float or None, default None
            Only answers from this timestamp on; the whole history if None. Keyword-only.

        Returns
        -------
        list of sqlite3.Row
            Each answer's exercise, attempt number, correctness, duration in milliseconds and time.

        Examples
        --------
        >>> db = Database()
        >>> ada = db.add_profile("Ada")
        >>> for t in (10.0, 20.0, 30.0):
        ...     db.add_attempt(ada.id, exercise="NoteNames", item_key="k", attempt_no=1, answer="C", correct=True,
        ...                    duration_ms=1000, answered_at=t)
        >>> [r["answered_at"] for r in db.attempts_in([ada.id], since=15.0)]
        [20.0, 30.0]
        """
        where, args = self._scope(
            profile_ids,
            exercise=exercise,
            time_column="answered_at",
            since=since,
        )
        return self.conn.execute(
            "SELECT exercise, attempt_no, correct, duration_ms, answered_at FROM attempts "
            f"WHERE {where} ORDER BY answered_at, id",
            args,
        ).fetchall()

    def strained_items(
        self,
        profile_ids: list[int] | None = None,
        *,
        exercise: str | None = None,
        since: float | None = None,
        min_strain: float = 0.0,
        limit: int = 10,
    ) -> list[sqlite3.Row]:
        """
        Return the questions that need most practice, the same question from different profiles counted together.

        Parameters
        ----------
        profile_ids : list of int or None, default None
            The profiles to include; every profile if None.
        exercise : str or None, default None
            Only this exercise (its class name); every exercise if None. Keyword-only.
        since : float or None, default None
            Only questions last seen from this timestamp on; the whole history if None. Keyword-only.
        min_strain : float, default 0.0
            Leave out questions with less strain than this. Keyword-only.
        limit : int, default 10
            The most questions to return. Keyword-only.

        Returns
        -------
        list of sqlite3.Row
            Each question's exercise, key, average strain, times seen, wrong attempts and stored payload, most strained first.

        Examples
        --------
        >>> db = Database()
        >>> ada = db.add_profile("Ada")
        >>> for key, strain in (("easy", 0.5), ("hard", 4.0)):
        ...     item = ItemRecord(strain, seen=1, first_try_right=0, wrong_attempts=1, total_first_ms=1000,
        ...                       last_seen=1.0, signature="s", payload="{}")
        ...     db.save_item(ada.id, exercise="NoteNames", item_key=key, item=item)
        >>> [r["item_key"] for r in db.strained_items([ada.id], min_strain=1.0)]
        ['hard']
        """
        where, args = self._scope(
            profile_ids,
            exercise=exercise,
            time_column="last_seen",
            since=since,
        )
        return self.conn.execute(
            "SELECT exercise, item_key, AVG(strain) AS strain, SUM(seen) AS seen, SUM(wrong_attempts) AS wrong, "
            "MAX(payload) AS payload FROM items "
            f"WHERE {where} GROUP BY exercise, item_key HAVING SUM(seen) > 0 AND AVG(strain) >= ? "
            "ORDER BY strain DESC, wrong DESC LIMIT ?",
            (*args, min_strain, limit),
        ).fetchall()

    # -- for browsing ----------------------------------------------------------------------------------------------

    def count_attempts(self, profile_id: int) -> int:
        """
        Return how many answers a profile has given.

        Parameters
        ----------
        profile_id : int
            The profile's id.

        Returns
        -------
        int
            The number of answers, wrong ones included.

        Examples
        --------
        >>> db = Database()
        >>> ada = db.add_profile("Ada")
        >>> db.count_attempts(ada.id)
        0
        """
        return self.conn.execute("SELECT COUNT(*) FROM attempts WHERE profile_id = ?", (profile_id,)).fetchone()[0]

    def attempt_rows(
        self,
        profile_id: int,
        *,
        limit: int = 10000,
    ) -> list[sqlite3.Row]:
        """
        Return the newest answers first, each with the stored question it was an answer to (if that is still known).

        Parameters
        ----------
        profile_id : int
            The profile's id.
        limit : int, default 10000
            The most rows to return. Keyword-only.

        Returns
        -------
        list of sqlite3.Row
            Each answer's time, exercise, question key, answer, correctness, attempt number, duration and question payload.

        Examples
        --------
        >>> db = Database()
        >>> ada = db.add_profile("Ada")
        >>> for t in (1.0, 2.0):
        ...     db.add_attempt(ada.id, exercise="NoteNames", item_key="k", attempt_no=1, answer="C", correct=True,
        ...                    duration_ms=1000, answered_at=t)
        >>> [r["answered_at"] for r in db.attempt_rows(ada.id)]
        [2.0, 1.0]
        """
        return self.conn.execute(
            "SELECT a.answered_at, a.exercise, a.item_key, a.answer, a.correct, a.attempt_no, a.duration_ms, i.payload "
            "FROM attempts a LEFT JOIN items i ON i.profile_id = a.profile_id AND i.exercise = a.exercise "
            "AND i.item_key = a.item_key WHERE a.profile_id = ? ORDER BY a.id DESC LIMIT ?",
            (profile_id, limit),
        ).fetchall()

    def item_rows(
        self,
        profile_id: int,
        *,
        limit: int = 10000,
    ) -> list[sqlite3.Row]:
        """
        Return what is known about each of a profile's questions, the most strained first.

        Parameters
        ----------
        profile_id : int
            The profile's id.
        limit : int, default 10000
            The most rows to return. Keyword-only.

        Returns
        -------
        list of sqlite3.Row
            Every column of each question's record.

        Examples
        --------
        >>> db = Database()
        >>> ada = db.add_profile("Ada")
        >>> db.item_rows(ada.id)
        []
        """
        return self.conn.execute(
            "SELECT * FROM items WHERE profile_id = ? ORDER BY strain DESC, last_seen DESC LIMIT ?",
            (profile_id, limit),
        ).fetchall()

    def profile_rows(self) -> list[sqlite3.Row]:
        """
        Return every profile with how many answers and questions it has.

        Returns
        -------
        list of sqlite3.Row
            Each profile's id, name, creation time, number of answers and number of questions, sorted by name.

        Examples
        --------
        >>> db = Database()
        >>> _ = db.add_profile("Ada")
        >>> [(r["name"], r["attempts"], r["questions"]) for r in db.profile_rows()]
        [('Ada', 0, 0)]
        """
        return self.conn.execute(
            "SELECT p.id, p.name, p.created_at, (SELECT COUNT(*) FROM attempts a WHERE a.profile_id = p.id) AS attempts, "
            "(SELECT COUNT(*) FROM items i WHERE i.profile_id = p.id) AS questions FROM profiles p "
            "ORDER BY p.name COLLATE NOCASE",
        ).fetchall()

    def replay_candidates(
        self,
        profile_id: int,
        *,
        exercise: str,
        signature: str,
        hardest: int = 25,
        random_extra: int = 10,
    ) -> list[ItemRecord]:
        """
        Return questions asked before under these same settings: the ones that need most practice, plus a few at random.

        Parameters
        ----------
        profile_id : int
            The profile's id.
        exercise : str
            The exercise's class name. Keyword-only.
        signature : str
            The exercise's current settings signature; only questions asked under it qualify. Keyword-only.
        hardest : int, default 25
            How many of the most strained questions to include. Keyword-only.
        random_extra : int, default 10
            How many more to pick at random. Keyword-only.

        Returns
        -------
        list of ItemRecord
            The questions, each at most once.

        Examples
        --------
        >>> db = Database()
        >>> ada = db.add_profile("Ada")
        >>> item = ItemRecord(3.0, seen=1, first_try_right=0, wrong_attempts=1, total_first_ms=1000,
        ...                   last_seen=1.0, signature="s1", payload="{}")
        >>> db.save_item(ada.id, exercise="NoteNames", item_key="k", item=item)
        >>> [row_.item_key for row_ in db.replay_candidates(ada.id, exercise="NoteNames", signature="s1")]
        ['k']
        >>> db.replay_candidates(ada.id, exercise="NoteNames", signature="other settings")
        []
        """
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
        """
        Turn a row of the items table into an `ItemRecord`.

        Parameters
        ----------
        r : sqlite3.Row
            A row with every column of the items table.

        Returns
        -------
        ItemRecord
            The same data as a record.

        Examples
        --------
        >>> db = Database()
        >>> ada = db.add_profile("Ada")
        >>> item = ItemRecord(1.0, seen=2, first_try_right=1, wrong_attempts=0, total_first_ms=10,
        ...                   last_seen=5.0, signature="s", payload="{}")
        >>> db.save_item(ada.id, exercise="NoteNames", item_key="k", item=item)
        >>> row = db.conn.execute("SELECT * FROM items").fetchone()
        >>> Database._item(row).item_key
        'k'
        """
        return ItemRecord(
            r["strain"],
            seen=r["seen"],
            first_try_right=r["first_try_right"],
            wrong_attempts=r["wrong_attempts"],
            total_first_ms=r["total_first_ms"],
            last_seen=r["last_seen"],
            signature=r["signature"],
            payload=r["payload"],
            item_key=r["item_key"],
        )
