"""Add workspace UID alias mappings."""

from __future__ import annotations

import sqlite3


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_aliases (
            alias_uid TEXT PRIMARY KEY,
            canonical_uid TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (alias_uid <> canonical_uid)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workspace_aliases_canonical_uid
            ON workspace_aliases(canonical_uid)
        """
    )
