"""Integration tests for MCP stdio server tool registration and round-trips."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import anyio
import pytest
from mcp.server.fastmcp.exceptions import ToolError

from recollectium.core import RecollectiumCore
from recollectium.errors import RecollectiumError
from recollectium.mcp_server import create_mcp_server
from recollectium.retrieval import UNSET


def test_create_mcp_server_registers_tools(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    tools = mcp._tool_manager._tools
    expected = {
        "search_user_memory",
        "search_workspace_memory",
        "add_memory",
        "get_memory",
        "update_memory",
        "archive_memory",
        "list_memories",
        "list_workspaces",
        "rename_workspace",
        "resolve_workspace",
        "add_workspace_alias",
        "list_workspace_aliases",
        "remove_workspace_alias",
        "embedding_status",
        "embedding_jobs",
        "get_embedding_job",
        "refresh_embeddings",
        "clear_embedding_jobs",
        "health",
        "version",
        "capabilities",
    }
    assert set(tools.keys()) == expected


def test_mcp_tool_verbosity_schema_is_discoverable(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    for tool in mcp._tool_manager._tools.values():
        properties = tool.parameters["properties"]
        verbosity_schema = properties["verbosity"]
        assert verbosity_schema["default"] is None
        assert "compact" in verbosity_schema["description"]
        assert "verbose" in verbosity_schema["description"]
        assert {"compact", "verbose"} in [
            set(option["enum"])
            for option in verbosity_schema["anyOf"]
            if "enum" in option
        ]


def test_mcp_search_override_schemas_are_discoverable(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    for tool_name in ("search_user_memory", "search_workspace_memory"):
        tool = mcp._tool_manager._tools[tool_name]
        properties = tool.parameters["properties"]

        assert "protected_minimum" not in tool.parameters["required"]
        protected_minimum_schema = properties["protected_minimum"]
        assert protected_minimum_schema["type"] == "integer"
        assert protected_minimum_schema["minimum"] == 0
        assert "default" not in protected_minimum_schema
        assert "null" not in json.dumps(protected_minimum_schema)

        assert "match_threshold" not in tool.parameters["required"]
        match_threshold_schema = properties["match_threshold"]
        assert "default" not in match_threshold_schema
        threshold_options = match_threshold_schema["anyOf"]
        numeric_option = next(
            option for option in threshold_options if option.get("type") == "number"
        )
        assert numeric_option["minimum"] == 0.0
        assert numeric_option["maximum"] == 1.0
        assert {"type": "null"} in threshold_options
        assert {
            "const": "model_recommended_default",
            "type": "string",
        } in threshold_options


def test_mcp_schemas_restrict_embedding_job_states_and_empty_strings(
    tmp_path: Path,
) -> None:
    mcp = create_mcp_server(RecollectiumCore(db_path=tmp_path / "schema.db"))
    embedding_state = mcp._tool_manager._tools["embedding_jobs"].parameters[
        "properties"
    ]["state"]
    assert json.dumps(embedding_state).count("queued") == 0
    assert json.dumps(embedding_state).count("running") == 0
    assert set(embedding_state["anyOf"][0]["enum"]) == {
        "pending",
        "in_progress",
        "completed",
        "failed",
    }

    for tool_name, field_name in (
        ("search_user_memory", "type"),
        ("search_workspace_memory", "type"),
        ("search_workspace_memory", "workspace_uid"),
        ("list_memories", "type"),
        ("add_memory", "sensitivity"),
        ("update_memory", "id"),
        ("resolve_workspace", "uid"),
    ):
        schema = mcp._tool_manager._tools[tool_name].parameters["properties"][
            field_name
        ]
        encoded = json.dumps(schema)
        assert '"minLength": 1' in encoded


@pytest.mark.anyio
async def test_mcp_tool_run_rejects_unknown_extra_arguments(tmp_path: Path) -> None:
    mcp = create_mcp_server(RecollectiumCore(db_path=tmp_path / "extras.db"))
    tool = mcp._tool_manager._tools["health"]
    with pytest.raises(ValueError, match="unknown argument"):
        await tool.run({"verbosity": "compact", "extra": True})


def test_mcp_search_overrides_reject_invalid_values(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)
    search_fn = mcp._tool_manager._tools["search_user_memory"].fn

    invalid_cases = [
        {"protected_minimum": -1},
        {"protected_minimum": None},
        {"match_threshold": -0.1},
        {"match_threshold": 1.1},
        {"match_threshold": "bad"},
        {"match_threshold": "0.5"},
        {"match_threshold": {}},
        {"limit": "5"},
        {"limit": True},
        {"include_archived": 1},
    ]
    for overrides in invalid_cases:
        result = json.loads(search_fn(query="anything", **overrides))
        assert "error" in result


def test_mcp_search_overrides_accept_valid_explicit_values(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "valid-search-overrides.db")
    core.add_memory(space="user", type="fact", content="valid overrides")
    core.add_memory(
        space="workspace",
        type="fact",
        content="valid workspace overrides",
        workspace_uid="ws",
    )
    mcp = create_mcp_server(core)

    user_search = mcp._tool_manager._tools["search_user_memory"].fn
    assert isinstance(
        json.loads(
            user_search(
                query="valid",
                protected_minimum=0,
                match_threshold=0.5,
                include_archived=False,
            )
        ),
        list,
    )
    assert isinstance(
        json.loads(
            user_search(query="valid", match_threshold="model_recommended_default")
        ),
        list,
    )
    assert isinstance(
        json.loads(user_search(query="valid", match_threshold=None)), list
    )

    workspace_search = mcp._tool_manager._tools["search_workspace_memory"].fn
    workspace_error = json.loads(
        workspace_search(query="valid", workspace_uid="ws", include_archived=1)
    )
    assert "error" in workspace_error


def test_mcp_search_overrides_preserve_omitted_vs_null_semantics() -> None:
    class CapturingCore:
        config = None

        def __init__(self) -> None:
            self.user_calls: list[dict[str, Any]] = []

        def search_user_memories(self, **kwargs: Any) -> list[Any]:
            self.user_calls.append(kwargs)
            return []

    core = CapturingCore()
    mcp = create_mcp_server(cast(RecollectiumCore, core))
    search_fn = mcp._tool_manager._tools["search_user_memory"].fn

    json.loads(search_fn(query="anything"))
    omitted_call = core.user_calls[-1]
    assert omitted_call["protected_minimum"] is UNSET
    assert omitted_call["match_threshold"] is UNSET

    json.loads(search_fn(query="anything", match_threshold=None))
    null_call = core.user_calls[-1]
    assert null_call["protected_minimum"] is UNSET
    assert null_call["match_threshold"] is None


def test_mcp_tool_add_memory_round_trip(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    add_fn = mcp._tool_manager._tools["add_memory"].fn
    result_json = add_fn(
        space="user",
        type="preference",
        content="I prefer dark mode",
        verbosity="verbose",
    )
    memory = json.loads(result_json)
    assert memory["space"] == "user"
    assert memory["type"] == "preference"
    assert memory["content"] == "I prefer dark mode"
    assert "id" in memory

    list_fn = mcp._tool_manager._tools["list_memories"].fn
    list_json = list_fn(space="user", type="preference", limit=1)
    memories = json.loads(list_json)
    assert len(memories) >= 1
    assert memories[0]["content"] == "I prefer dark mode"


def test_mcp_tool_search_user_memory(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    added = core.add_memory(
        space="user", type="fact", content="Recollectium stores memories locally"
    )
    mcp = create_mcp_server(core)

    search_fn = mcp._tool_manager._tools["search_user_memory"].fn
    result_json = search_fn(
        query="local memory storage", type="fact", verbosity="verbose"
    )
    results = json.loads(result_json)
    assert len(results) >= 1
    assert results[0]["memory"]["id"] == added.id
    assert results[0]["memory"]["content"] == "Recollectium stores memories locally"


def test_mcp_tool_search_user_memory_compact_and_verbose(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    added = core.add_memory(
        space="user", type="fact", content="Compact search returns match score"
    )
    mcp = create_mcp_server(core)

    search_fn = mcp._tool_manager._tools["search_user_memory"].fn
    compact = json.loads(
        search_fn(query="match score", type="fact", verbosity="compact")
    )
    assert compact[0]["id"] == added.id
    assert compact[0]["content"] == "Compact search returns match score"
    assert "match" in compact[0]
    assert "memory" not in compact[0]

    verbose = json.loads(
        search_fn(query="match score", type="fact", verbosity="verbose")
    )
    assert verbose[0]["memory"]["id"] == added.id
    assert verbose[0]["memory"]["content"] == "Compact search returns match score"
    assert "score" in verbose[0]


def test_mcp_tool_mutations_compact(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    add_fn = mcp._tool_manager._tools["add_memory"].fn
    added = json.loads(add_fn(space="user", type="fact", content="compact mutation"))
    assert set(added) == {"id", "status"}
    assert added["status"] == "saved"

    update_fn = mcp._tool_manager._tools["update_memory"].fn
    updated = json.loads(update_fn(id=added["id"], content="updated"))
    assert updated == {"id": added["id"], "status": "updated"}

    archive_fn = mcp._tool_manager._tools["archive_memory"].fn
    archived = json.loads(archive_fn(id=added["id"]))
    assert archived == {"id": added["id"], "status": "archived"}


def test_mcp_tool_invalid_verbosity_returns_error(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    search_fn = mcp._tool_manager._tools["search_user_memory"].fn
    result = json.loads(search_fn(query="anything", verbosity="full"))
    assert result == {"error": "verbosity must be one of: compact, verbose"}


def test_mcp_tool_default_verbosity_uses_config(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    core.config.effective_config["response_verbosity"] = "verbose"
    added = core.add_memory(
        space="user", type="fact", content="Configured verbose default"
    )
    mcp = create_mcp_server(core)

    search_fn = mcp._tool_manager._tools["search_user_memory"].fn
    result = json.loads(search_fn(query="verbose default", type="fact"))
    assert result[0]["memory"]["id"] == added.id
    assert result[0]["memory"]["content"] == "Configured verbose default"


def test_mcp_tool_get_memory(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    added = core.add_memory(space="user", type="fact", content="Get this memory")
    mcp = create_mcp_server(core)

    get_fn = mcp._tool_manager._tools["get_memory"].fn
    result_json = get_fn(id=added.id)
    memory = json.loads(result_json)
    assert memory["id"] == added.id
    assert memory["content"] == "Get this memory"
    assert memory["space"] == "user"


def test_mcp_tool_archive_memory(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    added = core.add_memory(space="user", type="note", content="Old idea to archive")
    mcp = create_mcp_server(core)

    archive_fn = mcp._tool_manager._tools["archive_memory"].fn
    result_json = archive_fn(id=added.id)
    archived = json.loads(result_json)
    assert archived["id"] == added.id
    assert archived["status"] == "archived"

    list_fn = mcp._tool_manager._tools["list_memories"].fn
    list_json = list_fn(space="user")
    memories = json.loads(list_json)
    assert all(m["id"] != added.id for m in memories)


def test_mcp_tool_update_memory(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    added = core.add_memory(space="user", type="fact", content="Original content")
    mcp = create_mcp_server(core)

    update_fn = mcp._tool_manager._tools["update_memory"].fn
    result_json = update_fn(
        id=added.id, type="note", content="Updated content", verbosity="verbose"
    )
    updated = json.loads(result_json)
    assert updated["id"] == added.id
    assert updated["content"] == "Updated content"
    assert updated["type"] == "note"


def test_mcp_tool_errors(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    add_fn = mcp._tool_manager._tools["add_memory"].fn
    result_json = add_fn(space="invalid", type="fact", content="test content")
    data = json.loads(result_json)
    assert "error" in data
    assert "space must be one of" in data["error"]


def test_search_user_memory_validation_error(tmp_path: Path) -> None:
    """search_user_memory with an empty query returns an error JSON."""
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    search_fn = mcp._tool_manager._tools["search_user_memory"].fn
    result_json = search_fn(query="", limit=5)
    data = json.loads(result_json)
    assert "error" in data


def test_search_workspace_memory_missing_workspace_uid(tmp_path: Path) -> None:
    """search_workspace_memory with an empty workspace UID returns an error JSON."""
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    search_fn = mcp._tool_manager._tools["search_workspace_memory"].fn
    result_json = search_fn(query="test query", workspace_uid="", limit=5)
    data = json.loads(result_json)
    assert "error" in data


def test_update_memory_not_found_error(tmp_path: Path) -> None:
    """update_memory with a non-existent ID returns an error JSON."""
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    update_fn = mcp._tool_manager._tools["update_memory"].fn
    result_json = update_fn(id="nonexistent-id", content="new content")
    data = json.loads(result_json)
    assert "error" in data


def test_archive_memory_not_found_error(tmp_path: Path) -> None:
    """archive_memory with a non-existent ID returns an error JSON."""
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    archive_fn = mcp._tool_manager._tools["archive_memory"].fn
    result_json = archive_fn(id="nonexistent-id")
    data = json.loads(result_json)
    assert "error" in data


def test_get_memory_not_found_error(tmp_path: Path) -> None:
    """get_memory with a non-existent ID returns an error JSON."""
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    get_fn = mcp._tool_manager._tools["get_memory"].fn
    result_json = get_fn(id="nonexistent-id")
    data = json.loads(result_json)
    assert "error" in data


def test_add_memory_workspace_space_mismatch(tmp_path: Path) -> None:
    """add_memory with workspace space but no workspace_uid returns an error JSON."""
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    add_fn = mcp._tool_manager._tools["add_memory"].fn
    result_json = add_fn(space="workspace", type="fact", content="test content")
    data = json.loads(result_json)
    assert "error" in data
    assert "workspace_uid is required" in data["error"]


def test_list_memories_invalid_limit(tmp_path: Path) -> None:
    """list_memories with an invalid limit returns an error JSON."""
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    list_fn = mcp._tool_manager._tools["list_memories"].fn
    result_json = list_fn(limit=0)
    data = json.loads(result_json)
    assert "error" in data
    assert "limit must be" in data["error"]


def test_search_workspace_memory_round_trip(tmp_path: Path) -> None:
    """search_workspace_memory returns an added workspace memory."""
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    added = core.add_memory(
        space="workspace",
        type="fact",
        content="This project uses SQLite",
        workspace_uid="test-ws",
    )
    mcp = create_mcp_server(core)

    search_fn = mcp._tool_manager._tools["search_workspace_memory"].fn
    result_json = search_fn(
        query="SQLite database", workspace_uid="test-ws", verbosity="verbose"
    )
    results = json.loads(result_json)
    assert len(results) >= 1
    assert results[0]["memory"]["id"] == added.id


def test_mcp_list_workspaces_returns_array(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    core.add_memory(space="workspace", type="fact", content="a", workspace_uid="ws-a")
    core.add_memory(space="workspace", type="fact", content="b", workspace_uid="ws-b")

    mcp = create_mcp_server(core)
    fn = mcp._tool_manager._tools["list_workspaces"].fn
    result = fn(include_archived=False)
    assert json.loads(result) == ["ws-a", "ws-b"]


def test_mcp_rename_workspace_returns_result(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    core.add_memory(space="workspace", type="fact", content="a", workspace_uid="old")

    mcp = create_mcp_server(core)
    fn = mcp._tool_manager._tools["rename_workspace"].fn
    result = fn(old_uid="old", new_uid="new")
    data = json.loads(result)
    assert data["old_uid"] == "old"
    assert data["new_uid"] == "new"
    assert data["memories_updated"] == 1


def test_mcp_rename_workspace_error_returns_json(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)

    mcp = create_mcp_server(core)
    fn = mcp._tool_manager._tools["rename_workspace"].fn
    result = fn(old_uid="nonexistent", new_uid="new")
    error = json.loads(result)
    assert "error" in error


def test_mcp_list_memories_error_returns_json(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "list-error.db")
    mcp = create_mcp_server(core)
    original = core.list_memories

    def raise_error(*args, **kwargs):
        raise RecollectiumError("list failed")

    core.list_memories = raise_error
    try:
        result = json.loads(mcp._tool_manager._tools["list_memories"].fn())
        assert result == {"error": "list failed"}
    finally:
        core.list_memories = original


def test_mcp_list_workspaces_error_returns_json(tmp_path: Path) -> None:
    """list_workspaces returns error JSON on RecollectiumError."""
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)

    # Force list_workspaces to raise by corrupting the db
    mcp = create_mcp_server(core)
    fn = mcp._tool_manager._tools["list_workspaces"].fn

    # Monkey-patch core to raise on list_workspaces
    original = core.list_workspaces

    def raise_error(*args, **kwargs):
        from recollectium.errors import RecollectiumError

        raise RecollectiumError("forced error for test")

    core.list_workspaces = raise_error

    try:
        result = fn(include_archived=False)
        error = json.loads(result)
        assert "error" in error
        assert "forced error" in error["error"]
    finally:
        core.list_workspaces = original


def test_mcp_workspace_alias_tools_round_trip(tmp_path: Path) -> None:
    db_path = str(tmp_path / "aliases-mcp.db")
    core = RecollectiumCore(db_path=db_path)
    core.add_memory(
        space="workspace", type="fact", content="a", workspace_uid="canonical"
    )
    mcp = create_mcp_server(core)

    expected_tools = {
        "resolve_workspace",
        "add_workspace_alias",
        "list_workspace_aliases",
        "remove_workspace_alias",
    }
    assert expected_tools <= set(mcp._tool_manager._tools)

    add_fn = mcp._tool_manager._tools["add_workspace_alias"].fn
    resolve_fn = mcp._tool_manager._tools["resolve_workspace"].fn
    list_workspaces_fn = mcp._tool_manager._tools["list_workspaces"].fn
    list_fn = mcp._tool_manager._tools["list_workspace_aliases"].fn
    remove_fn = mcp._tool_manager._tools["remove_workspace_alias"].fn

    added = json.loads(add_fn(canonical_uid="canonical", alias_uid="legacy"))
    assert added == {
        "alias_uid": "legacy",
        "canonical_uid": "canonical",
        "status": "added",
        "migrated_memories": 0,
    }
    assert json.loads(resolve_fn(uid="legacy")) == {
        "canonical_uid": "canonical",
        "resolved_by_alias": True,
    }
    compact_workspaces = json.loads(list_workspaces_fn(include_aliases=True))
    assert compact_workspaces == [
        {"workspace_uid": "canonical", "aliases": ["legacy"], "alias_count": 1}
    ]
    verbose_workspaces = json.loads(
        list_workspaces_fn(include_aliases=True, verbosity="verbose")
    )
    assert verbose_workspaces[0]["aliases"] == ["legacy"]
    assert verbose_workspaces[0]["alias_count"] == 1
    assert verbose_workspaces[0]["alias_records"][0]["alias_uid"] == "legacy"
    assert "created_at" in verbose_workspaces[0]["alias_records"][0]
    assert json.loads(list_fn(canonical_uid="canonical")) == [
        {"alias_uid": "legacy", "canonical_uid": "canonical"}
    ]
    verbose_aliases = json.loads(
        list_fn(canonical_uid="canonical", verbosity="verbose")
    )
    assert verbose_aliases[0]["alias_uid"] == "legacy"
    assert "created_at" in verbose_aliases[0]
    assert json.loads(remove_fn(alias_uid="legacy")) == {
        "alias_uid": "legacy",
        "canonical_uid": "canonical",
        "status": "removed",
    }


def test_mcp_workspace_alias_error_paths(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    resolve_fn = mcp._tool_manager._tools["resolve_workspace"].fn
    assert "error" in json.loads(resolve_fn(uid=""))

    add_alias_fn = mcp._tool_manager._tools["add_workspace_alias"].fn
    assert "error" in json.loads(add_alias_fn(canonical_uid="same", alias_uid="same"))

    list_aliases_fn = mcp._tool_manager._tools["list_workspace_aliases"].fn
    assert "error" in json.loads(list_aliases_fn(canonical_uid=""))

    remove_alias_fn = mcp._tool_manager._tools["remove_workspace_alias"].fn
    assert "error" in json.loads(remove_alias_fn(alias_uid="missing"))


def test_mcp_health_version_capabilities_tools_return_json(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-tools.db")
    mcp = create_mcp_server(core)

    assert json.loads(mcp._tool_manager._tools["health"].fn())["status"] == "ok"
    assert "recollectium_version" in json.loads(
        mcp._tool_manager._tools["version"].fn()
    )
    capabilities = json.loads(mcp._tool_manager._tools["capabilities"].fn())
    assert "capabilities" in capabilities
    assert "memory_types" in capabilities


def test_mcp_embedding_status_returns_json(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    fn = mcp._tool_manager._tools["embedding_status"].fn
    result = json.loads(fn())
    assert "provider_status" in result


def test_mcp_embedding_jobs_returns_json(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    fn = mcp._tool_manager._tools["embedding_jobs"].fn
    result = json.loads(fn())
    assert isinstance(result, list)


def test_mcp_get_embedding_job_returns_json(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    job_id = "job-1"
    core.store.create_embedding_job(
        job_id=job_id,
        state="queued",
        total_count=2,
        processed_count=0,
        succeeded_count=0,
        failed_count=0,
        provider="fake",
        model="fake-model",
        embedding_profile={"provider": "fake", "profile": "fake-v1"},
    )
    mcp = create_mcp_server(core)

    fn = mcp._tool_manager._tools["get_embedding_job"].fn
    result = json.loads(fn(job_id=job_id))
    assert result["id"] == job_id
    assert result["state"] == "queued"


def test_mcp_refresh_and_clear_embedding_jobs_return_json(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    core.store.create_embedding_job(
        job_id="pending-job",
        state="pending",
        total_count=1,
        processed_count=0,
        succeeded_count=0,
        failed_count=0,
        provider="fake",
        model="fake-model",
        embedding_profile=core.embedding_provider.embedding_profile,
    )
    mcp = create_mcp_server(core)

    refresh_fn = mcp._tool_manager._tools["refresh_embeddings"].fn
    refresh_result = json.loads(refresh_fn(space="user"))
    assert refresh_result["refreshed"] is False

    clear_fn = mcp._tool_manager._tools["clear_embedding_jobs"].fn
    clear_result = json.loads(clear_fn(states=["pending"]))
    assert clear_result == {"deleted_count": 1, "states": ["pending"]}


def test_mcp_memory_read_tools_compact_and_verbose(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    user = core.add_memory(
        space="user",
        type="fact",
        content="MCP compact memory read",
        metadata={"source": "test"},
        confidence=0.8,
    )
    workspace = core.add_memory(
        space="workspace",
        type="fact",
        content="MCP workspace compact search",
        workspace_uid="ws-compact",
        metadata={"source": "workspace-test"},
    )
    mcp = create_mcp_server(core)

    get_fn = mcp._tool_manager._tools["get_memory"].fn
    compact_get = json.loads(get_fn(id=user.id, verbosity="compact"))
    verbose_get = json.loads(get_fn(id=user.id, verbosity="verbose"))
    assert set(compact_get) == {"id", "content", "type", "space"}
    assert verbose_get["metadata"] == {"source": "test"}
    assert verbose_get["confidence"] == 0.8

    list_fn = mcp._tool_manager._tools["list_memories"].fn
    compact_list = json.loads(list_fn(space="user", verbosity="compact"))
    verbose_list = json.loads(list_fn(space="user", verbosity="verbose"))
    assert set(compact_list[0]) == {"id", "content", "type", "space"}
    assert "metadata" in verbose_list[0]

    search_fn = mcp._tool_manager._tools["search_workspace_memory"].fn
    compact_search = json.loads(
        search_fn(
            query="compact search", workspace_uid="ws-compact", verbosity="compact"
        )
    )
    verbose_search = json.loads(
        search_fn(
            query="compact search", workspace_uid="ws-compact", verbosity="verbose"
        )
    )
    assert compact_search[0]["id"] == workspace.id
    assert set(compact_search[0]) == {"id", "content", "match"}
    assert verbose_search[0]["memory"]["id"] == workspace.id
    assert "score" in verbose_search[0]


def test_mcp_embedding_tools_compact_and_verbose(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    core.store.create_embedding_job(
        job_id="job-verbosity",
        state="completed",
        total_count=2,
        processed_count=2,
        succeeded_count=2,
        failed_count=0,
        provider="fake",
        model="fake-model",
        embedding_profile=core.embedding_provider.embedding_profile,
    )
    mcp = create_mcp_server(core)

    status_fn = mcp._tool_manager._tools["embedding_status"].fn
    compact_status = json.loads(status_fn(verbosity="compact"))
    verbose_status = json.loads(status_fn(verbosity="verbose"))
    assert "provider_status" in compact_status
    assert "runtime" not in compact_status
    assert "runtime" in verbose_status

    jobs_fn = mcp._tool_manager._tools["embedding_jobs"].fn
    compact_jobs = json.loads(jobs_fn(verbosity="compact"))
    verbose_jobs = json.loads(jobs_fn(verbosity="verbose"))
    assert compact_jobs[0]["id"] == "job-verbosity"
    assert set(compact_jobs[0]) <= {
        "id",
        "state",
        "reason",
        "total_count",
        "succeeded_count",
        "failed_count",
    }
    assert "embedding_profile" in verbose_jobs[0]

    get_job_fn = mcp._tool_manager._tools["get_embedding_job"].fn
    compact_job = json.loads(get_job_fn(job_id="job-verbosity", verbosity="compact"))
    verbose_job = json.loads(get_job_fn(job_id="job-verbosity", verbosity="verbose"))
    assert compact_job["id"] == "job-verbosity"
    assert "embedding_profile" not in compact_job
    assert "embedding_profile" in verbose_job

    refresh_fn = mcp._tool_manager._tools["refresh_embeddings"].fn
    compact_refresh = json.loads(refresh_fn(space="user", verbosity="compact"))
    verbose_refresh = json.loads(refresh_fn(space="user", verbosity="verbose"))
    assert compact_refresh["refreshed"] is False
    assert compact_refresh["stale_count"] == 0
    assert "status_path" in compact_refresh
    assert verbose_refresh["refreshed"] is False

    clear_fn = mcp._tool_manager._tools["clear_embedding_jobs"].fn
    clear_result = json.loads(clear_fn(states=["completed"], verbosity="verbose"))
    assert clear_result == {
        "deleted_count": 1,
        "states": ["completed"],
        "deleted_job_ids": ["job-verbosity"],
    }


def test_mcp_get_embedding_job_missing_returns_error(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    fn = mcp._tool_manager._tools["get_embedding_job"].fn
    result = json.loads(fn(job_id="nonexistent"))
    assert "error" in result


class _EmbeddingErrorCore:
    def active_embedding_status(self) -> dict[str, object]:
        raise RecollectiumError("status failed")

    def list_embedding_jobs(
        self, state: str | None = None, limit: int | None = None
    ) -> list[dict[str, object]]:
        raise RecollectiumError("jobs failed")

    def refresh_stale_embeddings(
        self,
        *,
        space: str | None = None,
        workspace_uid: str | None = None,
        include_archived: bool = False,
    ) -> dict[str, object]:
        raise RecollectiumError("refresh failed")

    def clear_embedding_jobs(
        self, *, states: list[str] | None = None
    ) -> dict[str, object]:
        raise RecollectiumError("clear failed")


def test_mcp_embedding_status_error_returns_json() -> None:
    mcp = create_mcp_server(cast(RecollectiumCore, _EmbeddingErrorCore()))

    fn = mcp._tool_manager._tools["embedding_status"].fn
    result = json.loads(fn())
    assert result == {"error": "status failed"}


def test_mcp_embedding_jobs_error_returns_json() -> None:
    mcp = create_mcp_server(cast(RecollectiumCore, _EmbeddingErrorCore()))

    fn = mcp._tool_manager._tools["embedding_jobs"].fn
    result = json.loads(fn(state="queued", limit=5))
    assert result == {"error": "jobs failed"}


def test_mcp_refresh_and_clear_embedding_jobs_errors_return_json() -> None:
    mcp = create_mcp_server(cast(RecollectiumCore, _EmbeddingErrorCore()))

    refresh_fn = mcp._tool_manager._tools["refresh_embeddings"].fn
    assert json.loads(refresh_fn(space="user")) == {"error": "refresh failed"}

    clear_fn = mcp._tool_manager._tools["clear_embedding_jobs"].fn
    assert json.loads(clear_fn(states=["pending"])) == {"error": "clear failed"}


def test_mcp_add_memory_rejects_invalid_metadata_json(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    add_fn = mcp._tool_manager._tools["add_memory"].fn
    result = json.loads(
        add_fn(space="user", type="fact", content="test", metadata="{invalid")
    )
    assert "error" in result
    assert "valid JSON" in result["error"]


def test_mcp_add_memory_rejects_non_object_metadata(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    add_fn = mcp._tool_manager._tools["add_memory"].fn
    result = json.loads(
        add_fn(space="user", type="fact", content="test", metadata="[]")
    )
    assert "error" in result
    assert "JSON object" in result["error"]


def test_mcp_update_memory_rejects_invalid_metadata_json(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    add_fn = mcp._tool_manager._tools["add_memory"].fn
    mem = json.loads(add_fn(space="user", type="fact", content="test"))

    update_fn = mcp._tool_manager._tools["update_memory"].fn
    result = json.loads(update_fn(id=mem["id"], metadata="{bad"))
    assert "error" in result
    assert "valid JSON" in result["error"]


def test_mcp_update_memory_rejects_non_object_metadata(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    add_fn = mcp._tool_manager._tools["add_memory"].fn
    mem = json.loads(add_fn(space="user", type="fact", content="test"))

    update_fn = mcp._tool_manager._tools["update_memory"].fn
    result = json.loads(update_fn(id=mem["id"], metadata='"string"'))
    assert "error" in result
    assert "JSON object" in result["error"]


def test_mcp_tools_reject_coerced_scalar_values(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "strict-mcp.db")
    mcp = create_mcp_server(core)
    memory_id = json.loads(
        mcp._tool_manager._tools["add_memory"].fn(
            space="user", type="fact", content="strict scalar"
        )
    )["id"]

    invalid_calls = (
        (
            "add_memory",
            {"space": "user", "type": "fact", "content": "x", "confidence": "0.5"},
        ),
        (
            "add_memory",
            {"space": "user", "type": "fact", "content": "x", "confidence": -0.1},
        ),
        (
            "add_memory",
            {"space": "user", "type": "fact", "content": "x", "confidence": 1.1},
        ),
        (
            "add_memory",
            {"space": "user", "type": "fact", "content": "x", "workspace_uid": "ws"},
        ),
        (
            "add_memory",
            {"space": "user", "type": "fact", "content": "x", "metadata": 1},
        ),
        ("update_memory", {"id": memory_id}),
        ("update_memory", {"id": memory_id, "confidence": "0.5"}),
        ("list_memories", {"include_archived": 1}),
        ("list_memories", {"limit": "5"}),
        ("list_workspaces", {"include_archived": 0}),
        ("list_workspaces", {"include_aliases": 1}),
        (
            "add_workspace_alias",
            {"canonical_uid": "a", "alias_uid": "b", "migrate_existing": 1},
        ),
        ("embedding_jobs", {"limit": "5"}),
        ("refresh_embeddings", {"include_archived": 1}),
    )
    for tool_name, kwargs in invalid_calls:
        result = json.loads(mcp._tool_manager._tools[tool_name].fn(**kwargs))
        assert "error" in result

    user_workspace_uid_error = json.loads(
        mcp._tool_manager._tools["add_memory"].fn(
            space="user", type="fact", content="x", workspace_uid="ws"
        )
    )
    assert (
        user_workspace_uid_error["error"]
        == "workspace_uid is only valid for workspace memories"
    )


def test_mcp_tool_run_rejects_coerced_scalar_values(tmp_path: Path) -> None:
    """FastMCP Tool.run must reject string/int/bool coercions before tool bodies."""
    core = RecollectiumCore(db_path=tmp_path / "strict-tool-run.db")
    mcp = create_mcp_server(core)

    async def run_cases() -> None:
        invalid_calls = (
            ("search_user_memory", {"query": "anything", "limit": "5"}),
            ("search_user_memory", {"query": "anything", "include_archived": 1}),
            (
                "search_user_memory",
                {"query": "anything", "match_threshold": "0.5"},
            ),
            (
                "search_user_memory",
                {"query": "anything", "protected_minimum": "0"},
            ),
            (
                "search_workspace_memory",
                {"query": "anything", "workspace_uid": "ws", "limit": "5"},
            ),
            (
                "add_memory",
                {
                    "space": "user",
                    "type": "fact",
                    "content": "x",
                    "confidence": "0.5",
                },
            ),
            (
                "add_memory",
                {
                    "space": "user",
                    "type": "fact",
                    "content": "x",
                    "confidence": True,
                },
            ),
            ("list_memories", {"limit": "5"}),
            ("list_memories", {"include_archived": 1}),
            ("list_workspaces", {"include_archived": 0}),
            ("list_workspaces", {"include_aliases": 1}),
            (
                "add_workspace_alias",
                {"canonical_uid": "a", "alias_uid": "b", "migrate_existing": 1},
            ),
            ("embedding_jobs", {"limit": "5"}),
            ("refresh_embeddings", {"include_archived": 1}),
        )

        for tool_name, arguments in invalid_calls:
            with pytest.raises(ToolError):
                await mcp._tool_manager._tools[tool_name].run(arguments)

        accepted = await mcp._tool_manager._tools["add_memory"].run(
            {"space": "user", "type": "fact", "content": "x", "confidence": 0.5}
        )
        assert "error" not in json.loads(accepted)

    anyio.run(run_cases)


def test_mcp_capabilities_verbose_includes_response_verbosity(
    tmp_path: Path,
) -> None:
    core = RecollectiumCore(db_path=tmp_path / "capabilities-verbose.db")
    mcp = create_mcp_server(core)

    async def run_case() -> None:
        compact = json.loads(
            await mcp._tool_manager._tools["capabilities"].run({"verbosity": "compact"})
        )
        verbose = json.loads(
            await mcp._tool_manager._tools["capabilities"].run({"verbosity": "verbose"})
        )

        assert "response_verbosity" not in compact
        assert verbose["response_verbosity"] == "verbose"

    anyio.run(run_case)


def test_mcp_add_memory_with_metadata_object(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "metadata-object.db")
    mcp = create_mcp_server(core)

    add_fn = mcp._tool_manager._tools["add_memory"].fn
    result = json.loads(
        add_fn(
            space="user",
            type="fact",
            content="object metadata",
            metadata={"key": "value"},
            verbosity="verbose",
        )
    )
    assert result["metadata"] == {"key": "value"}


def test_mcp_add_memory_with_metadata_source_confidence_sensitivity(
    tmp_path: Path,
) -> None:
    db_path = str(tmp_path / "test.db")
    core = RecollectiumCore(db_path=db_path)
    mcp = create_mcp_server(core)

    add_fn = mcp._tool_manager._tools["add_memory"].fn
    result = json.loads(
        add_fn(
            space="user",
            type="preference",
            content="dark mode",
            metadata='{"key": "val"}',
            source="test-harness",
            confidence=0.9,
            sensitivity="internal",
            verbosity="verbose",
        )
    )
    assert result["space"] == "user"
    assert result["type"] == "preference"
    assert result["content"] == "dark mode"
    assert result["metadata"] == {"key": "val"}
    assert result["source"] == "test-harness"
    assert result["confidence"] == 0.9
    assert result["sensitivity"] == "internal"
