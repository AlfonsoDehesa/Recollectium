from __future__ import annotations

import re
import sqlite3
from collections import Counter
from pathlib import Path

from recollectium.dev_seed import (
    DEV_SEED_PROJECTS,
    DEV_SEED_USER_TOPICS,
    ensure_seeded_dev_database,
    reset_seeded_dev_database,
    seeded_dev_database_is_initialized,
)
from recollectium.core import RecollectiumCore
from recollectium.storage import SQLiteMemoryStore


def _sentence_count(content: str) -> int:
    return len(re.findall(r"[.!?](?:\s|$)", content.strip()))


class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.embedding_profile = {
            "provider": "fake",
            "model": "fake-model",
            "dimensions": 3,
            "version": "1",
            "profile": "fake-profile-v1",
            "max_tokens": 16,
            "chunk_tokens": 128,
            "chunk_overlap_tokens": 0,
            "query_prompt_policy": "raw",
        }

    def embed(self, text: str) -> list[float]:
        size = float(len(text))
        first = float(ord(text[0])) if text else 0.0
        return [size, first, 1.0]

    def similarity(self, first: list[float], second: list[float]) -> float:
        return sum(a * b for a, b in zip(first, second, strict=True))


def test_reset_seeded_dev_database_recreates_seed_state(tmp_path: Path) -> None:
    db_path = tmp_path / "dev.db"
    provider = FakeEmbeddingProvider()

    result = reset_seeded_dev_database(db_path, provider)

    store = SQLiteMemoryStore(db_path)
    user_memories = store.list_memories(space="user", include_archived=True)
    workspace_memories = store.list_memories(space="workspace", include_archived=True)
    workspaces = store.list_workspace_uids(include_archived=True)
    topics = {memory.metadata["dev_topic"] for memory in user_memories}

    assert result == {
        "status": "reset",
        "database": str(db_path),
        "user_memories": 100,
        "workspace_memories": 90,
        "workspaces": 3,
        "topics": 10,
    }
    assert len(user_memories) == 100
    assert len(workspace_memories) == 90
    assert len(workspaces) == 3
    assert len(topics) == 10
    assert seeded_dev_database_is_initialized(db_path)


def test_seeded_dev_database_uses_unique_public_safe_fictional_memories(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "dev.db"
    provider = FakeEmbeddingProvider()

    reset_seeded_dev_database(db_path, provider)

    store = SQLiteMemoryStore(db_path)
    user_memories = store.list_memories(space="user", include_archived=True)
    workspace_memories = store.list_memories(space="workspace", include_archived=True)
    user_contents = [memory.content for memory in user_memories]
    workspace_contents = [memory.content for memory in workspace_memories]
    all_contents = user_contents + workspace_contents

    assert len(user_contents) == 100
    assert len(workspace_contents) == 90
    assert len(set(user_contents)) == 100
    assert len(set(workspace_contents)) == 90
    assert len(set(all_contents)) == 190
    assert DEV_SEED_USER_TOPICS == (
        "travel",
        "transportation",
        "videogames",
        "books",
        "cooking",
        "fitness",
        "music",
        "pets",
        "learning",
        "home style",
    )
    assert DEV_SEED_PROJECTS == (
        {
            "uid": "proj-fic-cedarledger-01",
            "name": "CedarLedger",
        },
        {
            "uid": "proj-fic-northstar-forms-01",
            "name": "Northstar Forms",
        },
        {
            "uid": "proj-fic-harborpilot-01",
            "name": "HarborPilot",
        },
    )
    assert {memory.metadata["dev_topic"] for memory in user_memories} == set(
        DEV_SEED_USER_TOPICS
    )
    assert {
        topic: sum(
            1 for memory in user_memories if memory.metadata["dev_topic"] == topic
        )
        for topic in DEV_SEED_USER_TOPICS
    } == {topic: 10 for topic in DEV_SEED_USER_TOPICS}
    assert {memory.workspace_uid for memory in workspace_memories} == {
        project["uid"] for project in DEV_SEED_PROJECTS
    }
    assert {
        project["uid"]: sum(
            1 for memory in workspace_memories if memory.workspace_uid == project["uid"]
        )
        for project in DEV_SEED_PROJECTS
    } == {project["uid"]: 30 for project in DEV_SEED_PROJECTS}
    assert all(memory.metadata["fictional"] is True for memory in user_memories)
    assert all(memory.metadata["fictional"] is True for memory in workspace_memories)
    assert all(
        not content.startswith("Fictional dev user") for content in user_contents
    )
    assert all(" fact 1:" not in content for content in user_contents)
    assert all(
        "fictional project memory" not in content for content in workspace_contents
    )
    visible_label_terms = (
        "Fictional dev user",
        "fact 1:",
        "project memory",
        "seed data",
        "seeded demo",
        "seeded bookkeeping",
        "seeded scheduling",
        "public-safe",
        "safe for public screenshots",
        "fixture",
        "demo",
        "fabricated",
        "pretend",
        "imaginary",
        "make-believe",
        "fantasy",
        "storybook",
        "whimsical",
        "moonbeam",
    )
    assert not any(
        label.lower() in content.lower()
        for label in visible_label_terms
        for content in all_contents
    )
    assert all(1 <= _sentence_count(content) <= 3 for content in all_contents)
    assert {
        topic: Counter(
            _sentence_count(memory.content)
            for memory in user_memories
            if memory.metadata["dev_topic"] == topic
        )
        for topic in DEV_SEED_USER_TOPICS
    } == {topic: Counter({1: 4, 2: 3, 3: 3}) for topic in DEV_SEED_USER_TOPICS}
    assert {
        project["uid"]: Counter(
            _sentence_count(memory.content)
            for memory in workspace_memories
            if memory.workspace_uid == project["uid"]
        )
        for project in DEV_SEED_PROJECTS
    } == {
        project["uid"]: Counter({1: 10, 2: 10, 3: 10}) for project in DEV_SEED_PROJECTS
    }
    expected_project_names = {
        project["uid"]: project["name"] for project in DEV_SEED_PROJECTS
    }
    assert all(
        memory.workspace_uid is not None
        and memory.metadata["dev_project_name"]
        == expected_project_names[memory.workspace_uid]
        for memory in workspace_memories
    )
    assert all(
        memory.metadata["dev_project_uid"] == memory.workspace_uid
        for memory in workspace_memories
    )

    banned_public_seed_terms = (
        "Alfonso",
        "Kaylee",
        "NAS",
        "Recollectium",
        "OpenCode",
        "Hermes",
    )
    assert not any(
        banned_term.lower() in content.lower()
        for banned_term in banned_public_seed_terms
        for content in all_contents
    )


def test_core_seeded_workspace_uids_are_retrievable_with_default_normalization(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    regular_db = tmp_path / "regular.db"
    dev_db = tmp_path / "dev.db"
    config_path.write_text(
        "{"
        f'"database": {{"path": "{regular_db}"}}, '
        f'"development": {{"use_seeded_database": true, "seeded_database_path": "{dev_db}"}}'
        "}",
        encoding="utf-8",
    )

    core = RecollectiumCore(
        config_path=config_path,
        embedding_provider=FakeEmbeddingProvider(),
    )

    expected_uids = [
        "proj-fic-cedarledger-01",
        "proj-fic-northstar-forms-01",
        "proj-fic-harborpilot-01",
    ]
    assert set(core.list_workspaces(include_archived=True)) == set(expected_uids)
    for workspace_uid in expected_uids:
        underscored_input = workspace_uid.replace("-", "_")
        assert core.resolve_workspace(underscored_input) == {
            "input_uid": underscored_input,
            "normalized_uid": workspace_uid,
            "canonical_uid": workspace_uid,
            "resolved_by_alias": False,
        }
        listed = core.list_memories(
            space="workspace",
            workspace_uid=underscored_input,
            include_archived=True,
        )
        assert len(listed) == 30
        assert {memory.workspace_uid for memory in listed} == {workspace_uid}
        results = core.search_workspace_memories(
            "project dashboard task",
            workspace_uid=underscored_input,
            limit=3,
            include_archived=True,
        )
        assert len(results) == 3
        assert {result.memory.workspace_uid for result in results} == {workspace_uid}


def test_seeded_dev_database_is_reinitialized_after_mutation(tmp_path: Path) -> None:
    db_path = tmp_path / "dev.db"
    provider = FakeEmbeddingProvider()
    reset_seeded_dev_database(db_path, provider)
    store = SQLiteMemoryStore(db_path)
    first = store.list_memories(space="user", limit=1)[0]
    store.archive_memory(first.id)

    result = reset_seeded_dev_database(db_path, provider)

    store = SQLiteMemoryStore(db_path)
    assert result["status"] == "reset"
    assert len(store.list_memories(space="user", include_archived=True)) == 100
    assert len(store.list_memories(space="user")) == 100


def test_seeded_dev_database_rejects_mutated_same_count_content(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "dev.db"
    provider = FakeEmbeddingProvider()
    reset_seeded_dev_database(db_path, provider)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE memories SET content = ? WHERE id = ?",
            (
                "The user prefers a stale mutated memory with the same ID.",
                "dev-user-001",
            ),
        )

    assert not seeded_dev_database_is_initialized(db_path)

    result = ensure_seeded_dev_database(db_path, provider)

    store = SQLiteMemoryStore(db_path)
    assert result is not None
    assert result["status"] == "reset"
    assert store.get_memory("dev-user-001").content.startswith(
        "The user prefers trips that leave room"
    )


def test_seeded_dev_database_rejects_mutated_project_metadata(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "dev.db"
    provider = FakeEmbeddingProvider()
    reset_seeded_dev_database(db_path, provider)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            UPDATE memories
            SET metadata_json = json_set(metadata_json, '$.dev_project_name', 'Wrong Project')
            WHERE id = ?
            """,
            ("dev-workspace-01-001",),
        )

    assert not seeded_dev_database_is_initialized(db_path)

    result = ensure_seeded_dev_database(db_path, provider)

    store = SQLiteMemoryStore(db_path)
    repaired = store.get_memory("dev-workspace-01-001")
    assert result is not None
    assert result["status"] == "reset"
    assert repaired.metadata["dev_project_name"] == DEV_SEED_PROJECTS[0]["name"]
    assert repaired.metadata["dev_project_uid"] == DEV_SEED_PROJECTS[0]["uid"]


def test_seeded_dev_database_ensure_skips_complete_seed_state(tmp_path: Path) -> None:
    db_path = tmp_path / "dev.db"
    provider = FakeEmbeddingProvider()
    reset_seeded_dev_database(db_path, provider)

    result = ensure_seeded_dev_database(db_path, provider)

    assert result is None


def test_ensure_seeded_dev_database_creates_nested_parent_path(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "missing" / "nested" / "parent" / "dev.db"
    provider = FakeEmbeddingProvider()

    result = ensure_seeded_dev_database(db_path, provider)

    store = SQLiteMemoryStore(db_path)
    user_memories = store.list_memories(space="user", include_archived=True)
    workspace_memories = store.list_memories(space="workspace", include_archived=True)
    assert result == {
        "status": "reset",
        "database": str(db_path),
        "user_memories": 100,
        "workspace_memories": 90,
        "workspaces": 3,
        "topics": 10,
    }
    assert db_path.parent.is_dir()
    assert db_path.exists()
    assert len(user_memories) == 100
    assert len(workspace_memories) == 90
    assert len(store.list_workspace_uids(include_archived=True)) == 3
    assert seeded_dev_database_is_initialized(db_path)


def test_seeded_dev_database_rejects_wrong_workspace_uids(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "dev.db"
    provider = FakeEmbeddingProvider()
    reset_seeded_dev_database(db_path, provider)

    with sqlite3.connect(db_path) as connection:
        for project, wrong_uid in zip(
            DEV_SEED_PROJECTS,
            ("wrong-a", "wrong-b", "wrong-c"),
            strict=True,
        ):
            connection.execute(
                """
                UPDATE memories
                SET workspace_uid = ?
                WHERE space = 'workspace' AND workspace_uid = ?
                """,
                (wrong_uid, project["uid"]),
            )

    assert not seeded_dev_database_is_initialized(db_path)

    result = ensure_seeded_dev_database(db_path, provider)

    store = SQLiteMemoryStore(db_path)
    workspace_memories = store.list_memories(space="workspace", include_archived=True)
    assert result is not None
    assert result["status"] == "reset"
    assert {memory.workspace_uid for memory in workspace_memories} == {
        project["uid"] for project in DEV_SEED_PROJECTS
    }
    assert {
        project["uid"]: sum(
            1 for memory in workspace_memories if memory.workspace_uid == project["uid"]
        )
        for project in DEV_SEED_PROJECTS
    } == {project["uid"]: 30 for project in DEV_SEED_PROJECTS}


def test_core_uses_seeded_dev_database_when_configured(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    regular_db = tmp_path / "regular.db"
    dev_db = tmp_path / "dev.db"
    config_path.write_text(
        "{"
        f'"database": {{"path": "{regular_db}"}}, '
        f'"development": {{"use_seeded_database": true, "seeded_database_path": "{dev_db}"}}'
        "}",
        encoding="utf-8",
    )

    core = RecollectiumCore(
        config_path=config_path,
        embedding_provider=FakeEmbeddingProvider(),
    )

    assert core.store.db_path == dev_db
    assert dev_db.exists()
    assert not regular_db.exists()
    assert len(core.list_memories(space="user", include_archived=True)) == 100
