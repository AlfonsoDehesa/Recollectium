"""Versioned schema migrations for Recollectium SQLite storage."""

from __future__ import annotations

from recollectium.migrations.runner import Migration
from recollectium.migrations.versions import (
    v001_initial_memory_schema,
    v002_embedding_chunks_and_jobs,
    v003_workspace_aliases,
)


def list_migrations() -> list[Migration]:
    return [
        Migration(
            version=1,
            name="initial_memory_schema",
            upgrade=v001_initial_memory_schema.upgrade,
        ),
        Migration(
            version=2,
            name="embedding_chunks_and_jobs",
            upgrade=v002_embedding_chunks_and_jobs.upgrade,
        ),
        Migration(
            version=3,
            name="workspace_aliases",
            upgrade=v003_workspace_aliases.upgrade,
        ),
    ]
