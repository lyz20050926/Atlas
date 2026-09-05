from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel

from src.models import LearningGoal, PlanRevision, ReadingPath, RecommendationResult, UserProfile

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS goals (
  user_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reading_paths (
  path_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  user_id TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (path_id, version)
);
CREATE TABLE IF NOT EXISTS plan_revisions (
  path_id TEXT NOT NULL,
  new_version INTEGER NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (path_id, new_version)
);
CREATE TABLE IF NOT EXISTS reading_sessions (
  session_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reading_progress (
  user_id TEXT NOT NULL,
  canonical_id TEXT NOT NULL,
  progress_percent INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'planned',
  is_current INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, canonical_id)
);
CREATE TABLE IF NOT EXISTS book_feedback (
  feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  canonical_id TEXT NOT NULL,
  stage_number INTEGER NOT NULL,
  reason TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS mentor_messages (
  message_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  scope TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  action_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS mentor_messages_lookup
  ON mentor_messages(user_id, scope, message_id);
CREATE TABLE IF NOT EXISTS mentor_settings (
  user_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS recommendations (
  user_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS plan_snapshots (
  user_id TEXT NOT NULL,
  snapshot_id TEXT NOT NULL,
  payload TEXT NOT NULL,
  profile_json TEXT,
  goal_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, snapshot_id)
);
CREATE TABLE IF NOT EXISTS api_cache (
  cache_key TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  source TEXT NOT NULL,
  retrieved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class AtlasDatabase:
    MENTOR_PREFERENCE_KEYS = (
        "cadence", "tone", "target_minutes", "accountability_enabled", "companion_enabled",
    )

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @staticmethod
    def _json(model: BaseModel) -> str:
        return model.model_dump_json()

    @staticmethod
    def _language_scoped_user_id(user_id: str, language: str | None) -> str:
        """Keep English and Chinese workspaces independent without a destructive migration."""
        normalized_language = (language or "").strip().lower()
        return f"{user_id}::{normalized_language}" if normalized_language in {"en", "zh"} else user_id

    def save_user(
        self,
        profile: UserProfile,
        goal: LearningGoal,
        language: str | None = None,
    ) -> None:
        storage_user_id = self._language_scoped_user_id(profile.user_id, language)
        with self.connect() as connection:
            self._archive_current(connection, storage_user_id)
            connection.execute(
                "INSERT OR REPLACE INTO users(user_id,payload,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)",
                (storage_user_id, self._json(profile)),
            )
            connection.execute(
                "INSERT OR REPLACE INTO goals(user_id,payload,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)",
                (storage_user_id, self._json(goal)),
            )

    def load_user(
        self,
        user_id: str,
        language: str | None = None,
    ) -> tuple[UserProfile, LearningGoal] | None:
        storage_ids = [self._language_scoped_user_id(user_id, language)]
        if language and storage_ids[0] != user_id:
            # Existing installations stored one unscoped record. Read it only when
            # its payload language matches the requested workspace.
            storage_ids.append(user_id)
        with self.connect() as connection:
            for storage_id in storage_ids:
                row = connection.execute(
                    "SELECT users.payload, goals.payload FROM users JOIN goals USING(user_id) WHERE user_id=?",
                    (storage_id,),
                ).fetchone()
                if not row:
                    continue
                profile = UserProfile.model_validate_json(row[0])
                goal = LearningGoal.model_validate_json(row[1])
                if storage_id == user_id and language and goal.interface_language != language:
                    continue
                return profile, goal
        return None

    def save_path(self, path: ReadingPath) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO reading_paths(path_id,version,user_id,payload) VALUES(?,?,?,?)",
                (path.path_id, path.version, path.user_id, self._json(path)),
            )

    def save_recommendation(
        self,
        user_id: str,
        result: RecommendationResult,
        language: str | None = None,
    ) -> None:
        storage_user_id = self._language_scoped_user_id(user_id, language)
        with self.connect() as connection:
            self._archive_current(connection, storage_user_id)
            connection.execute(
                "INSERT OR REPLACE INTO recommendations(user_id,payload,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)",
                (storage_user_id, self._json(result)),
            )
            self._archive_current(connection, storage_user_id)

    @staticmethod
    def snapshot_id(result: RecommendationResult) -> str:
        return hashlib.sha256(result.reading_path.model_dump_json().encode()).hexdigest()[:24]

    @classmethod
    def _archive_current(cls, connection: sqlite3.Connection, storage_user_id: str) -> None:
        row = connection.execute(
            "SELECT payload,updated_at FROM recommendations WHERE user_id=?", (storage_user_id,),
        ).fetchone()
        if not row:
            return
        result = RecommendationResult.model_validate_json(row[0])
        context = connection.execute(
            "SELECT users.payload,goals.payload FROM users JOIN goals USING(user_id) WHERE user_id=?",
            (storage_user_id,),
        ).fetchone()
        connection.execute(
            "INSERT OR IGNORE INTO plan_snapshots"
            "(user_id,snapshot_id,payload,profile_json,goal_json,created_at) VALUES(?,?,?,?,?,?)",
            (storage_user_id, cls.snapshot_id(result), row[0],
             context[0] if context else None, context[1] if context else None, row[1]),
        )

    def list_plan_snapshots(self, user_id: str, language: str) -> list[dict]:
        """Migrate active snapshots additively; legacy outlines stay explicitly read-only."""
        storage_id = self._language_scoped_user_id(user_id, language)
        with self.connect() as connection:
            self._archive_current(connection, storage_id)
            rows = connection.execute(
                "SELECT snapshot_id,payload,profile_json,goal_json,created_at FROM plan_snapshots "
                "WHERE user_id=? ORDER BY created_at DESC,rowid DESC", (storage_id,),
            ).fetchall()
            items = []
            known = set()
            path_ids = set()
            for key, payload, profile, goal, created_at in rows:
                result = RecommendationResult.model_validate_json(payload)
                path = result.reading_path
                known.add((path.path_id, path.version))
                path_ids.add(path.path_id)
                revision = connection.execute(
                    "SELECT payload FROM plan_revisions WHERE path_id=? AND new_version=?",
                    (path.path_id, path.version),
                ).fetchone()
                items.append(dict(snapshot_id=key, result=result, path=path,
                                  profile=UserProfile.model_validate_json(profile) if profile else None,
                                  goal=LearningGoal.model_validate_json(goal) if goal else None,
                                  created_at=created_at,
                                  reason=json.loads(revision[0]).get('trigger', '') if revision else '',
                                  restorable=bool(profile and goal)))
            # Never infer a legacy path's language from user_id alone.
            for path_id in sorted(path_ids):
                for payload, created_at in connection.execute(
                    "SELECT payload,created_at FROM reading_paths WHERE path_id=? ORDER BY version DESC",
                    (path_id,),
                ).fetchall():
                    path = ReadingPath.model_validate_json(payload)
                    if (path.path_id, path.version) not in known:
                        items.append(dict(snapshot_id=f"legacy:{path.path_id}:{path.version}",
                                          path=path, result=None, profile=None, goal=None,
                                          created_at=created_at, reason='', restorable=False))
        return items

    def activate_plan_snapshot(self, user_id: str, language: str, snapshot_id: str) -> None:
        """Explicit activation is atomic and never overwrites reading progress or history."""
        storage_id = self._language_scoped_user_id(user_id, language)
        with self.connect() as connection:
            row = connection.execute(
                "SELECT payload,profile_json,goal_json FROM plan_snapshots WHERE user_id=? AND snapshot_id=?",
                (storage_id, snapshot_id),
            ).fetchone()
            if not row or not row[1] or not row[2]:
                raise ValueError("This plan has no complete restorable snapshot")
            goal = LearningGoal.model_validate_json(row[2])
            profile = UserProfile.model_validate_json(row[1])
            if goal.interface_language != language or profile.user_id != user_id:
                raise ValueError("Plan belongs to another workspace")
            self._archive_current(connection, storage_id)
            for table, payload in zip(('recommendations', 'users', 'goals'), row, strict=True):
                connection.execute(
                    f"INSERT OR REPLACE INTO {table}(user_id,payload,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)",
                    (storage_id, payload),
                )

    def load_recommendation(
        self,
        user_id: str,
        language: str | None = None,
    ) -> RecommendationResult | None:
        storage_ids = [self._language_scoped_user_id(user_id, language)]
        if language and storage_ids[0] != user_id:
            storage_ids.append(user_id)
        with self.connect() as connection:
            for storage_id in storage_ids:
                row = connection.execute(
                    "SELECT payload FROM recommendations WHERE user_id=?", (storage_id,)
                ).fetchone()
                if row:
                    return RecommendationResult.model_validate_json(row[0])
        return None

    def save_api_cache(self, cache_key: str, payload: object, source: str) -> None:
        """Persist a normalized external API response without storing credentials."""
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO api_cache(cache_key,payload,source,retrieved_at)
                VALUES(?,?,?,CURRENT_TIMESTAMP)
                ON CONFLICT(cache_key) DO UPDATE SET
                  payload=excluded.payload,
                  source=excluded.source,
                  retrieved_at=CURRENT_TIMESTAMP
                """,
                (
                    cache_key,
                    json.dumps(payload, ensure_ascii=False, default=str),
                    source.strip()[:80],
                ),
            )

    def load_api_cache(
        self,
        cache_key: str,
        *,
        max_age_hours: float,
    ) -> object | None:
        """Return a recent API snapshot, or ``None`` when it is absent or stale."""
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT payload
                FROM api_cache
                WHERE cache_key=?
                  AND (julianday('now') - julianday(retrieved_at)) * 24 <= ?
                """,
                (cache_key, float(max_age_hours)),
            ).fetchone()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except (TypeError, json.JSONDecodeError):
            return None

    def load_paths(self, path_id: str) -> list[ReadingPath]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM reading_paths WHERE path_id=? ORDER BY version", (path_id,)
            ).fetchall()
        return [ReadingPath.model_validate_json(row[0]) for row in rows]

    def save_revision(self, path_id: str, revision: PlanRevision) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO plan_revisions(path_id,new_version,payload) VALUES(?,?,?)",
                (path_id, revision.new_version, self._json(revision)),
            )

    def save_reading_session(self, user_id: str, payload: dict) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO reading_sessions(user_id,payload) VALUES(?,?)",
                (user_id, json.dumps(payload, ensure_ascii=False, default=str)),
            )

    def save_reading_progress(
        self,
        user_id: str,
        canonical_id: str,
        progress_percent: int,
        status: str,
        *,
        is_current: bool = False,
        language: str | None = None,
    ) -> None:
        """Persist a learner-controlled reading state for one language workspace."""
        if not 0 <= progress_percent <= 100:
            raise ValueError("progress_percent must be between 0 and 100")
        if status not in {"planned", "reading", "paused", "completed"}:
            raise ValueError("Unsupported reading status")
        if status == "completed" or progress_percent == 100:
            progress_percent, status = 100, "completed"
        elif progress_percent > 0 and status == "planned":
            status = "reading"
        storage_user_id = self._language_scoped_user_id(user_id, language)
        with self.connect() as connection:
            if is_current:
                connection.execute(
                    "UPDATE reading_progress SET is_current=0 WHERE user_id=?",
                    (storage_user_id,),
                )
            connection.execute(
                """
                INSERT INTO reading_progress(
                  user_id,canonical_id,progress_percent,status,is_current,updated_at
                ) VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)
                ON CONFLICT(user_id,canonical_id) DO UPDATE SET
                  progress_percent=excluded.progress_percent,
                  status=excluded.status,
                  is_current=excluded.is_current,
                  updated_at=CURRENT_TIMESTAMP
                """,
                (
                    storage_user_id,
                    canonical_id,
                    int(progress_percent),
                    status,
                    int(is_current),
                ),
            )

    def load_reading_progress(
        self,
        user_id: str,
        language: str | None = None,
    ) -> dict[str, dict[str, object]]:
        storage_user_id = self._language_scoped_user_id(user_id, language)
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT canonical_id,progress_percent,status,is_current,updated_at
                FROM reading_progress WHERE user_id=?
                """,
                (storage_user_id,),
            ).fetchall()
        progress: dict[str, dict[str, object]] = {}
        for row in rows:
            progress_percent = int(row[1])
            status = str(row[2])
            if status == "completed" or progress_percent == 100:
                progress_percent, status = 100, "completed"
            elif progress_percent > 0 and status == "planned":
                status = "reading"
            progress[str(row[0])] = {
                "progress_percent": progress_percent,
                "status": status,
                "is_current": bool(row[3]),
                "updated_at": str(row[4]),
            }
        return progress

    def save_book_feedback(
        self,
        user_id: str,
        canonical_id: str,
        stage_number: int,
        reason: str,
        note: str = "",
        *,
        language: str | None = None,
    ) -> int:
        """Store recommendation feedback without mixing English and Chinese workspaces."""
        storage_user_id = self._language_scoped_user_id(user_id, language)
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO book_feedback(user_id,canonical_id,stage_number,reason,note)
                VALUES(?,?,?,?,?)
                """,
                (storage_user_id, canonical_id, int(stage_number), reason, note.strip()[:1000]),
            )
            return int(cursor.lastrowid)

    def load_book_feedback(
        self,
        user_id: str,
        language: str | None = None,
    ) -> list[dict[str, object]]:
        storage_user_id = self._language_scoped_user_id(user_id, language)
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT feedback_id,canonical_id,stage_number,reason,note,created_at
                FROM book_feedback WHERE user_id=? ORDER BY feedback_id DESC
                """,
                (storage_user_id,),
            ).fetchall()
        return [
            {
                "feedback_id": int(row[0]),
                "canonical_id": str(row[1]),
                "stage_number": int(row[2]),
                "reason": str(row[3]),
                "note": str(row[4]),
                "created_at": str(row[5]),
            }
            for row in rows
        ]

    def save_mentor_message(
        self,
        user_id: str,
        scope: str,
        role: str,
        content: str,
        action: dict | None = None,
        *,
        language: str | None = None,
    ) -> int:
        """Append one message to a language- and context-scoped mentor conversation."""
        if role not in {"user", "assistant"}:
            raise ValueError("role must be user or assistant")
        storage_user_id = self._language_scoped_user_id(user_id, language)
        safe_scope = scope.strip()[:240] or "path"
        safe_content = content.strip()[:6000]
        if not safe_content:
            raise ValueError("message content cannot be empty")
        with self.connect() as connection:
            if safe_scope == "path":
                safe_scope = self._path_mentor_scope(connection, storage_user_id)
            cursor = connection.execute(
                """
                INSERT INTO mentor_messages(user_id,scope,role,content,action_json)
                VALUES(?,?,?,?,?)
                """,
                (
                    storage_user_id,
                    safe_scope,
                    role,
                    safe_content,
                    json.dumps(action or {}, ensure_ascii=False, default=str),
                ),
            )
            return int(cursor.lastrowid)

    def load_mentor_messages(
        self,
        user_id: str,
        scope: str,
        *,
        language: str | None = None,
        limit: int = 24,
        archived: bool = False,
    ) -> list[dict[str, object]]:
        storage_user_id = self._language_scoped_user_id(user_id, language)
        safe_limit = max(1, min(int(limit), 100))
        with self.connect() as connection:
            safe_scope = scope.strip()[:240] or "path"
            if safe_scope == "path":
                safe_scope = self._path_mentor_scope(connection, storage_user_id)
            if archived and scope != "path":
                raise ValueError("Archived conversations are available for path scope only")
            scope_filter = (
                "scope != ? AND (scope = 'path' OR scope LIKE 'path:%')"
                if archived else "scope = ?"
            )
            rows = connection.execute(
                f"""
                SELECT message_id,role,content,action_json,created_at
                FROM mentor_messages
                WHERE user_id=? AND {scope_filter}
                ORDER BY message_id DESC LIMIT ?
                """,
                (storage_user_id, safe_scope, safe_limit),
            ).fetchall()
        messages = []
        for row in reversed(rows):
            try:
                action = json.loads(row[3])
            except (TypeError, json.JSONDecodeError):
                action = {}
            messages.append(
                {
                    "message_id": int(row[0]),
                    "role": str(row[1]),
                    "content": str(row[2]),
                    "action": action,
                    "created_at": str(row[4]),
                }
            )
        return messages

    @staticmethod
    def _path_mentor_scope(connection: sqlite3.Connection, storage_user_id: str) -> str:
        """Resolve the active path, never attach legacy unscoped chat to a new plan."""
        row = connection.execute(
            "SELECT payload FROM recommendations WHERE user_id=?", (storage_user_id,),
        ).fetchone()
        if not row:
            return "path"
        path = json.loads(row[0])["reading_path"]
        return AtlasDatabase.mentor_scope_for_path(ReadingPath.model_validate(path))

    @staticmethod
    def mentor_scope_for_path(reading_path: ReadingPath) -> str:
        path = reading_path.model_dump()
        identity = {
            "path_id": path["path_id"],
            "version": path["version"],
            "stages": [
                [stage["stage_number"], stage["books"], stage["learning_objective"]]
                for stage in path["stages"]
            ],
        }
        digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:32]
        return f"path:{digest}"

    def path_mentor_scope(self, user_id: str, *, language: str | None = None) -> str:
        with self.connect() as connection:
            return self._path_mentor_scope(connection, self._language_scoped_user_id(user_id, language))

    def save_mentor_settings(
        self,
        user_id: str,
        payload: dict,
        *,
        language: str | None = None,
    ) -> None:
        storage_user_id = self._language_scoped_user_id(user_id, language)
        with self.connect() as connection:
            scope = self._path_mentor_scope(connection, storage_user_id)
            settings_user_id = storage_user_id if scope == "path" else f"{storage_user_id}::{scope}"
            # Personal preferences carry across paths; tasks, timers and follow-ups do not.
            if settings_user_id != storage_user_id:
                previous = connection.execute(
                    "SELECT payload FROM mentor_settings WHERE user_id=?", (storage_user_id,),
                ).fetchone()
                preferences = json.loads(previous[0]) if previous else {}
                preferences.update({key: payload[key] for key in self.MENTOR_PREFERENCE_KEYS if key in payload})
                connection.execute(
                    "INSERT OR REPLACE INTO mentor_settings(user_id,payload) VALUES(?,?)",
                    (storage_user_id, json.dumps(preferences, ensure_ascii=False, default=str)),
                )
            connection.execute(
                """
                INSERT INTO mentor_settings(user_id,payload,updated_at)
                VALUES(?,?,CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                  payload=excluded.payload,
                  updated_at=CURRENT_TIMESTAMP
                """,
                (
                    settings_user_id,
                    json.dumps(payload, ensure_ascii=False, default=str),
                ),
            )

    def dismiss_reading_followup(self, user_id: str, *, language: str, path: ReadingPath) -> None:
        """Dismiss only this path's invitation; preserve reports, progress and other settings."""
        storage_user_id = self._language_scoped_user_id(user_id, language)
        scope = self.mentor_scope_for_path(path)
        settings_user_id = storage_user_id if scope == "path" else f"{storage_user_id}::{scope}"
        with self.connect() as connection:
            row = connection.execute("SELECT payload FROM mentor_settings WHERE user_id=?", (settings_user_id,)).fetchone()
            if row:
                payload = json.loads(row[0])
                payload.pop("pending_session_followup", None)
                connection.execute("UPDATE mentor_settings SET payload=?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                                   (json.dumps(payload, ensure_ascii=False), settings_user_id))

    def load_mentor_settings(
        self,
        user_id: str,
        *,
        language: str | None = None,
        path: ReadingPath | None = None,
    ) -> dict[str, object]:
        storage_user_id = self._language_scoped_user_id(user_id, language)
        with self.connect() as connection:
            scope = self.mentor_scope_for_path(path) if path else self._path_mentor_scope(connection, storage_user_id)
            settings_user_id = storage_user_id if scope == "path" else f"{storage_user_id}::{scope}"
            base = connection.execute(
                "SELECT payload FROM mentor_settings WHERE user_id=?", (storage_user_id,),
            ).fetchone()
            base_payload = json.loads(base[0]) if base else {}
            preferences = {key: base_payload[key] for key in self.MENTOR_PREFERENCE_KEYS if key in base_payload}
            row = connection.execute(
                "SELECT payload FROM mentor_settings WHERE user_id=?",
                (settings_user_id,),
            ).fetchone()
        if not row:
            return preferences
        try:
            payload = json.loads(row[0])
        except (TypeError, json.JSONDecodeError):
            return {}
        return {**payload, **preferences} if isinstance(payload, dict) else preferences
