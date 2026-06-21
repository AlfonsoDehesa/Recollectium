"""Tests for the dedicated Recollectium WebUI."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient
import pytest

from recollectium.config import RecollectiumConfig
from recollectium.errors import ValidationError
from recollectium.memory_spaces import DEFAULT_MEMORY_SPACE_KEY
from recollectium.models import Memory, SearchResult, SPACE_USER, SPACE_WORKSPACE
from recollectium.webui import create_app


class FakeCore:
    def __init__(self, config: RecollectiumConfig) -> None:
        self.config = config
        self._memories: dict[str, Memory] = {}
        self._aliases: dict[str, dict[str, Any]] = {}
        self._counter = 0

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _next_id(self) -> str:
        self._counter += 1
        return f"mem-{self._counter:03d}"

    def add_memory(
        self,
        space: str,
        type: str,
        content: str,
        workspace_uid: str | None = None,
        metadata: dict[str, object] | None = None,
        source: str | None = None,
        confidence: float | None = None,
        sensitivity: str | None = None,
        *,
        memory_space_key: str | None = None,
    ) -> Memory:
        if space == SPACE_WORKSPACE and not workspace_uid:
            raise ValidationError("workspace_uid is required for workspace memories")
        memory = Memory(
            id=self._next_id(),
            space=space,
            type=type,
            content=content,
            workspace_uid=workspace_uid,
            metadata=metadata or {},
            source=source,
            confidence=confidence,
            sensitivity=sensitivity,
            created_at=self._timestamp(),
            updated_at=self._timestamp(),
        )
        self._memories[memory.id] = memory
        return memory

    def list_memories(
        self,
        space: str | None = None,
        type: str | None = None,
        status: str | None = None,
        workspace_uid: str | None = None,
        include_archived: bool = False,
        limit: int | None = None,
        *,
        memory_space_key: str | None = None,
    ) -> list[Memory]:
        memories = list(self._memories.values())
        if space is not None:
            memories = [memory for memory in memories if memory.space == space]
        if type is not None:
            memories = [memory for memory in memories if memory.type == type]
        if status is not None:
            memories = [memory for memory in memories if memory.status == status]
        elif not include_archived:
            memories = [memory for memory in memories if memory.status != "archived"]
        if workspace_uid is not None:
            memories = [
                memory for memory in memories if memory.workspace_uid == workspace_uid
            ]
        memories.sort(key=lambda memory: memory.id)
        return memories[:limit] if limit is not None else memories

    def get_memory(
        self,
        memory_id: str,
        *,
        memory_space_key: str | None = None,
    ) -> Memory:
        return self._memories[memory_id]

    def update_memory(
        self,
        memory_id: str,
        content: str | None = None,
        type: str | None = None,
        metadata: dict[str, object] | None = None,
        source: str | None = None,
        confidence: float | None = None,
        sensitivity: str | None = None,
        *,
        memory_space_key: str | None = None,
    ) -> Memory:
        memory = self._memories[memory_id]
        if content is not None:
            memory.content = content
        if type is not None:
            memory.type = type
        if metadata is not None:
            memory.metadata = metadata
        if source is not None:
            memory.source = source
        if confidence is not None:
            memory.confidence = confidence
        if sensitivity is not None:
            memory.sensitivity = sensitivity
        memory.updated_at = self._timestamp()
        return memory

    def archive_memory(
        self, memory_id: str, *, memory_space_key: str | None = None
    ) -> Memory:
        memory = self._memories[memory_id]
        memory.status = "archived"
        memory.updated_at = self._timestamp()
        return memory

    def search_user_memories(
        self,
        query: str,
        limit: int = 20,
        include_archived: bool = False,
        type: str | None = None,
        protected_minimum: int | None = None,
        match_threshold: float | None | str = None,
        progress_callback=None,
        *,
        memory_space_key: str | None = None,
    ) -> list[SearchResult]:
        memories = [
            memory
            for memory in self.list_memories(
                space=SPACE_USER, include_archived=include_archived, type=type
            )
            if query.lower() in memory.content.lower()
        ]
        return [
            SearchResult(memory=memory, score=0.99 - index * 0.01, rank=index + 1)
            for index, memory in enumerate(memories[:limit])
        ]

    def search_workspace_memories(
        self,
        query: str,
        workspace_uid: str | None,
        limit: int = 20,
        include_archived: bool = False,
        type: str | None = None,
        protected_minimum: int | None = None,
        match_threshold: float | None | str = None,
        progress_callback=None,
        *,
        memory_space_key: str | None = None,
    ) -> list[SearchResult]:
        memories = [
            memory
            for memory in self.list_memories(
                space=SPACE_WORKSPACE,
                workspace_uid=workspace_uid,
                include_archived=include_archived,
                type=type,
            )
            if query.lower() in memory.content.lower()
        ]
        return [
            SearchResult(memory=memory, score=0.95, rank=index + 1)
            for index, memory in enumerate(memories[:limit])
        ]

    def list_workspaces(
        self,
        *,
        include_archived: bool = False,
        include_aliases: bool = False,
        include_alias_records: bool = False,
        memory_space_key: str | None = None,
    ) -> list[str] | list[dict[str, object]]:
        workspaces = sorted(
            {
                memory.workspace_uid
                for memory in self._memories.values()
                if memory.space == SPACE_WORKSPACE
                and (include_archived or memory.status != "archived")
                and memory.workspace_uid is not None
            }
        )
        if not include_aliases:
            return workspaces
        inventory: list[dict[str, object]] = []
        for uid in workspaces:
            aliases = [
                alias_uid
                for alias_uid, alias in self._aliases.items()
                if alias["canonical_uid"] == uid
            ]
            item: dict[str, object] = {"workspace_uid": uid, "aliases": aliases}
            if include_alias_records:
                item["alias_count"] = len(aliases)
                item["alias_records"] = [
                    {
                        "alias_uid": alias_uid,
                        "canonical_uid": uid,
                        "created_at": alias["created_at"],
                        "updated_at": alias["updated_at"],
                    }
                    for alias_uid, alias in self._aliases.items()
                    if alias["canonical_uid"] == uid
                ]
            inventory.append(item)
        return inventory

    def resolve_workspace(
        self, uid: str, *, memory_space_key: str | None = None
    ) -> dict[str, object]:
        canonical = self._aliases.get(uid, {}).get("canonical_uid", uid)
        return {
            "input_uid": uid,
            "normalized_uid": uid,
            "canonical_uid": canonical,
            "resolved_by_alias": canonical != uid,
        }

    def add_workspace_alias(
        self,
        canonical_uid: str,
        alias_uid: str,
        *,
        migrate_existing: bool = False,
        memory_space_key: str | None = None,
    ) -> dict[str, object]:
        self._aliases[alias_uid] = {
            "canonical_uid": canonical_uid,
            "created_at": self._timestamp(),
            "updated_at": self._timestamp(),
        }
        return {
            "alias": {
                "alias_uid": alias_uid,
                "canonical_uid": canonical_uid,
                "created_at": self._aliases[alias_uid]["created_at"],
                "updated_at": self._aliases[alias_uid]["updated_at"],
            },
            "migrated_memories": 0,
        }

    def list_workspace_aliases(
        self,
        canonical_uid: str | None = None,
        *,
        memory_space_key: str | None = None,
    ) -> list[dict[str, str]]:
        aliases = []
        for alias_uid, alias in sorted(self._aliases.items()):
            if canonical_uid is None or alias["canonical_uid"] == canonical_uid:
                aliases.append(
                    {
                        "alias_uid": alias_uid,
                        "canonical_uid": alias["canonical_uid"],
                        "created_at": alias["created_at"],
                        "updated_at": alias["updated_at"],
                    }
                )
        return aliases

    def remove_workspace_alias(
        self, alias_uid: str, *, memory_space_key: str | None = None
    ) -> dict[str, str]:
        alias = self._aliases.pop(alias_uid)
        return {
            "alias_uid": alias_uid,
            "canonical_uid": alias["canonical_uid"],
            "created_at": alias["created_at"],
            "updated_at": alias["updated_at"],
        }

    def rename_workspace(
        self,
        old_uid: str,
        new_uid: str,
        *,
        memory_space_key: str | None = None,
    ) -> dict[str, Any]:
        updated = 0
        for memory in self._memories.values():
            if memory.space == SPACE_WORKSPACE and memory.workspace_uid == old_uid:
                memory.workspace_uid = new_uid
                updated += 1
        aliases_updated = 0
        for alias in self._aliases.values():
            if alias["canonical_uid"] == old_uid:
                alias["canonical_uid"] = new_uid
                alias["updated_at"] = self._timestamp()
                aliases_updated += 1
        return {
            "old_uid": old_uid,
            "new_uid": new_uid,
            "memories_updated": updated,
            "aliases_updated": aliases_updated,
        }


def _make_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> RecollectiumConfig:
    for name in (
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_CACHE_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
    ):
        monkeypatch.setenv(name, str(tmp_path / name.lower()))
    config_path = tmp_path / "config.json"
    config_path.write_text("{}\n", encoding="utf-8")
    return RecollectiumConfig(config_path=config_path)


def _make_core(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeCore:
    config = _make_config(tmp_path, monkeypatch)
    core = FakeCore(config)
    core.add_memory(space=SPACE_USER, type="fact", content="remember the carrots")
    core.add_memory(
        space=SPACE_WORKSPACE,
        type="decision",
        content="choose the fast route",
        workspace_uid="project-alpha",
    )
    return core


def _client(core: FakeCore) -> TestClient:
    return TestClient(create_app(cast(Any, core)), raise_server_exceptions=False)


def test_webui_static_assets_expose_control_plane_contract() -> None:
    static_dir = (
        Path(__file__).resolve().parents[1] / "src" / "recollectium" / "webui_static"
    )
    assert (static_dir / "index.html").exists()
    assert (static_dir / "app.js").exists()
    assert (static_dir / "styles.css").exists()

    index_html = (static_dir / "index.html").read_text(encoding="utf-8")
    app_js = (static_dir / "app.js").read_text(encoding="utf-8")

    assert 'id="memory-search-form"' in index_html
    assert 'id="config-key-form"' in index_html
    assert 'id="workspace-form"' in index_html
    assert 'id="service-form"' in index_html
    assert 'id="diagnostics"' in index_html
    assert "/v1/webui/memories" in app_js
    assert "/v1/webui/workspaces" in app_js
    assert "/v1/webui/config" in app_js
    assert "/v1/webui/services" in app_js
    assert "/v1/webui/memory-spaces" in app_js


def test_webui_backend_supports_memory_workspace_config_and_service_controls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    core = _make_core(tmp_path, monkeypatch)

    def fake_discover(
        config: RecollectiumConfig, service_type: str | None = None
    ) -> dict[str, Any]:
        resolved = service_type or "api"
        return {
            "status": "running",
            "service": {
                "type": resolved,
                "pid": 1234,
                "endpoint": f"http://127.0.0.1:{8765 if resolved != 'webui' else 8766}",
            },
            "versions": {"service_api_version": "1", "recollectium_version": "dev"},
            "paths": {
                "config": str(config.config_file_path),
                "runtime_dir": str(config.xdg_dirs["runtime"]),
                "pid_file": "pid",
                "discovery_file": "disc",
            },
        }

    monkeypatch.setattr(
        "recollectium.webui.service_manager.discover_service", fake_discover
    )
    monkeypatch.setattr(
        "recollectium.webui.service_manager.start_service", lambda *args, **kwargs: 4321
    )
    monkeypatch.setattr(
        "recollectium.webui.service_manager.stop_service", lambda *args, **kwargs: 4321
    )

    client = _client(core)

    health = client.get("/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    context = client.get("/v1/webui/context")
    assert context.status_code == 200
    context_payload = context.json()
    assert context_payload["security"]["warning"]
    assert (
        context_payload["config"]["safe_paths"]["default_memory_space_key"]
        == DEFAULT_MEMORY_SPACE_KEY
    )

    spaces = client.get("/v1/webui/memory-spaces")
    assert spaces.status_code == 200
    assert spaces.json()["default_memory_space_key"] == DEFAULT_MEMORY_SPACE_KEY

    list_response = client.get("/v1/webui/memories")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 2

    search_response = client.post(
        "/v1/webui/memories/search",
        json={"query": "carrots", "scope": "user", "limit": 10},
    )
    assert search_response.status_code == 200
    assert search_response.json()["count"] == 1

    add_response = client.post(
        "/v1/webui/memories",
        json={
            "space": "workspace",
            "type": "note",
            "content": "remember the follow-up",
            "workspace_uid": "project-alpha",
            "memory_space_key": DEFAULT_MEMORY_SPACE_KEY,
        },
    )
    assert add_response.status_code == 200
    memory_id = add_response.json()["memory"]["id"]

    update_response = client.patch(
        f"/v1/webui/memories/{memory_id}",
        json={"content": "remember the updated follow-up"},
    )
    assert update_response.status_code == 200
    assert (
        update_response.json()["memory"]["content"] == "remember the updated follow-up"
    )

    archive_response = client.post(f"/v1/webui/memories/{memory_id}/archive")
    assert archive_response.status_code == 200
    assert archive_response.json()["memory"]["status"] == "archived"

    config_get = client.get("/v1/webui/config/service.port")
    assert config_get.status_code == 200
    assert config_get.json()["value"] == 8765

    config_set = client.put("/v1/webui/config/service.port", json={"value": 8877})
    assert config_set.status_code == 200
    assert config_set.json()["value"] == 8877
    assert (
        json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))["service"][
            "port"
        ]
        == 8877
    )

    config_unset = client.delete("/v1/webui/config/service.port")
    assert config_unset.status_code == 200
    assert config_unset.json()["status"] == "removed"

    workspaces = client.get("/v1/webui/workspaces")
    assert workspaces.status_code == 200
    assert workspaces.json()["count"] >= 1

    resolve = client.get("/v1/webui/workspaces/project-alpha/resolve")
    assert resolve.status_code == 200
    assert resolve.json()["canonical_uid"] == "project-alpha"

    alias_add = client.post(
        "/v1/webui/workspaces/project-alpha/aliases",
        json={"alias_uid": "alpha-alt", "migrate_existing": False},
    )
    assert alias_add.status_code == 200
    assert alias_add.json()["status"] == "added"

    alias_list = client.get("/v1/webui/workspaces/project-alpha/aliases")
    assert alias_list.status_code == 200
    assert alias_list.json()["count"] == 1

    alias_remove = client.delete("/v1/webui/workspaces/aliases/alpha-alt")
    assert alias_remove.status_code == 200
    assert alias_remove.json()["status"] == "removed"

    services = client.get("/v1/webui/services")
    assert services.status_code == 200
    assert len(services.json()["services"]) == 3

    api_start = client.post("/v1/webui/services/api/start", json={})
    assert api_start.status_code == 200
    assert api_start.json()["status"] == "started"

    api_restart = client.post("/v1/webui/services/api/restart", json={})
    assert api_restart.status_code == 200
    assert api_restart.json()["status"] == "restarted"

    webui_discover = client.get("/v1/webui/services/webui/discover")
    assert webui_discover.status_code == 200
    assert webui_discover.json()["service_type"] == "webui"

    webui_stop_guard = client.post("/v1/webui/services/webui/stop", json={})
    assert webui_stop_guard.status_code == 400
    assert "allow_self_stop" in webui_stop_guard.json()["error"]["message"]

    webui_stop_accepted = client.post(
        "/v1/webui/services/webui/stop",
        json={"allow_self_stop": True},
    )
    assert webui_stop_accepted.status_code == 200
    assert webui_stop_accepted.json()["status"] == "accepted"


def test_webui_root_serves_shell_and_bootstrap_endpoints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(_make_core(tmp_path, monkeypatch))

    root_response = client.get("/")
    assert root_response.status_code == 200
    assert "Recollectium WebUI" in root_response.text
    assert 'id="memory-search-form"' in root_response.text

    app_js = client.get("/assets/app.js")
    assert app_js.status_code == 200
    assert "/v1/webui/context" in app_js.text
    assert "/v1/webui/services/webui/stop" in app_js.text
