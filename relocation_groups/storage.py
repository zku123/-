from __future__ import annotations

import sqlite3
from datetime import datetime

from .models import Group

SCHEMA = """
CREATE TABLE IF NOT EXISTS groups (
    platform TEXT NOT NULL, ext_id TEXT NOT NULL,
    title TEXT, url TEXT, description TEXT, members INTEGER,
    last_activity TEXT, country TEXT, score REAL,
    first_seen TEXT, updated_at TEXT,
    PRIMARY KEY (platform, ext_id)
)"""


class Storage:
    def __init__(self, path: str = "groups.db"):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute(SCHEMA)

    def save(self, groups: list[Group]) -> int:
        """Сохраняет группы, возвращает число новых."""
        now = datetime.utcnow().isoformat()
        new = 0
        for g in groups:
            exists = self.db.execute(
                "SELECT 1 FROM groups WHERE platform=? AND ext_id=?", g.key
            ).fetchone()
            new += 0 if exists else 1
            self.db.execute(
                """INSERT INTO groups VALUES (?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(platform, ext_id) DO UPDATE SET
                   title=excluded.title, description=excluded.description,
                   members=excluded.members, last_activity=excluded.last_activity,
                   country=excluded.country, score=excluded.score,
                   updated_at=excluded.updated_at""",
                (g.platform, g.ext_id, g.title, g.url, g.description, g.members,
                 g.last_activity.isoformat() if g.last_activity else None,
                 g.country, g.score, now, now),
            )
        self.db.commit()
        return new

    def top(self, limit: int = 50, country: str | None = None) -> list[sqlite3.Row]:
        sql = "SELECT * FROM groups"
        args: list = []
        if country:
            sql += " WHERE country=?"
            args.append(country)
        sql += " ORDER BY score DESC LIMIT ?"
        args.append(limit)
        return self.db.execute(sql, args).fetchall()
