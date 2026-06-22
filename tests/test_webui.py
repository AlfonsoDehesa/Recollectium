"""Tests for the dedicated Recollectium WebUI."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from pathlib import Path
from types import SimpleNamespace
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
        self._embedding_jobs: dict[str, dict[str, Any]] = {
            "job-001": {
                "id": "job-001",
                "state": "completed",
                "reason": "seed",
                "provider": "fake",
                "model": "fake-model",
                "total_count": 1,
                "succeeded_count": 1,
                "failed_count": 0,
            }
        }
        self.embedding_provider = SimpleNamespace(
            embedding_profile={
                "provider": "fake",
                "model": "fake-model",
                "profile": "fake-profile",
                "dimensions": 8,
            },
            cache_dir=None,
        )
        self.model_ready_calls: list[dict[str, Any]] = []

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

    def list_embedding_jobs(
        self,
        *,
        state: str | None = None,
        limit: int | None = None,
        memory_space_key: str | None = None,
    ) -> list[dict[str, Any]]:
        jobs = list(self._embedding_jobs.values())
        if state is not None:
            jobs = [job for job in jobs if job["state"] == state]
        jobs.sort(key=lambda job: job["id"])
        return jobs[:limit] if limit is not None else jobs

    def get_embedding_job(
        self, job_id: str, *, memory_space_key: str | None = None
    ) -> dict[str, Any]:
        return self._embedding_jobs[job_id]

    def clear_embedding_jobs(
        self,
        *,
        states: tuple[str, ...] | list[str] | None = None,
        memory_space_key: str | None = None,
    ) -> dict[str, Any]:
        selected_states = tuple(states) if states is not None else ("completed",)
        deleted = [
            job_id
            for job_id, job in list(self._embedding_jobs.items())
            if job["state"] in selected_states
        ]
        for job_id in deleted:
            self._embedding_jobs.pop(job_id, None)
        return {
            "deleted_count": len(deleted),
            "states": list(selected_states),
            "deleted_job_ids": deleted,
        }

    def refresh_stale_embeddings(
        self,
        *,
        space: str | None = None,
        workspace_uid: str | None = None,
        include_archived: bool = False,
        progress_callback=None,
        memory_space_key: str | None = None,
    ) -> dict[str, Any]:
        job = next(iter(self._embedding_jobs.values()), None)
        if job is None:
            job = {
                "id": "job-001",
                "state": "completed",
                "reason": "seed",
                "provider": "fake",
                "model": "fake-model",
                "total_count": 1,
                "succeeded_count": 1,
                "failed_count": 0,
            }
        return {
            "refreshed": True,
            "stale_count": 1,
            "job": job,
            "status_path": f"/v1/embedding/jobs/{job.get('id', 'job-001')}",
        }

    def active_embedding_status(
        self, *, memory_space_key: str | None = None
    ) -> dict[str, Any]:
        return {
            "embedding_profile": {
                "provider": "fake",
                "model": "fake-model",
                "profile": "fake-profile",
                "dimensions": 8,
            },
            "provider_status": "configured",
            "model_status": "managed_externally",
            "model_cache_path": None,
            "runtime": None,
            "startup_reembedding_job_id": None,
            "startup_reembedding_status_path": None,
            "embedding_jobs_status_path": "/v1/embedding/jobs",
            "recent_embedding_jobs": self.list_embedding_jobs(limit=5),
            "memory_space_key": memory_space_key
            or self.config.default_memory_space_key,
            "memory_space_db_path": str(self.config.resolved_database_path),
        }

    def _ensure_model_ready(self, *, suppress_provider_output: bool = False) -> None:
        self.model_ready_calls.append(
            {"suppress_provider_output": suppress_provider_output}
        )

    def database_status(
        self,
        *,
        memory_space_key: str | None = None,
    ) -> dict[str, object]:
        return {
            "status": "ok",
            "memory_space_key": memory_space_key
            or self.config.default_memory_space_key,
            "memory_space_db_path": str(self.config.resolved_database_path),
            "memory_space_is_default": True,
        }

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


def _make_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    raw_config: dict[str, Any] | None = None,
) -> RecollectiumConfig:
    for name in (
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_CACHE_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
    ):
        monkeypatch.setenv(name, str(tmp_path / name.lower()))
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(raw_config or {}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
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


def _assert_pattern(text: str, pattern: str) -> None:
    assert re.search(pattern, text, re.S), pattern


def test_webui_static_assets_expose_control_plane_contract() -> None:
    static_dir = (
        Path(__file__).resolve().parents[1] / "src" / "recollectium" / "webui_static"
    )
    assert (static_dir / "index.html").exists()
    assert (static_dir / "app.js").exists()
    assert (static_dir / "styles.css").exists()

    index_html = (static_dir / "index.html").read_text(encoding="utf-8")
    app_js = (static_dir / "app.js").read_text(encoding="utf-8")
    styles_css = (static_dir / "styles.css").read_text(encoding="utf-8")

    for tab_id, button_id in {
        "tab-memories": "tab-button-memories",
        "tab-spaces-config": "tab-button-spaces-config",
        "tab-workspaces": "tab-button-workspaces",
        "tab-services": "tab-button-services",
        "tab-embeddings": "tab-button-embeddings",
        "tab-dev-tools": "tab-button-dev-tools",
        "tab-graph": "tab-button-graph",
        "tab-diagnostics": "tab-button-diagnostics",
    }.items():
        _assert_pattern(
            index_html,
            rf'<button[^>]*id="{button_id}"[^>]*role="tab"[^>]*aria-controls="{tab_id}"',
        )
        _assert_pattern(
            index_html,
            rf'<section[^>]*id="{tab_id}"[^>]*role="tabpanel"[^>]*aria-labelledby="{button_id}"',
        )

    for pattern in [
        r'id="global-search-form"',
        r'placeholder="Search memories only"',
        r"Ctrl/⌘K · memories",
        r'id="memory-search-form"',
        r'id="config-key-form"',
        r'id="workspace-form"',
        r'id="service-form"',
        r'id="service-restart"',
        r'id="service-restart-note"',
        r'id="embedding-refresh-form"',
        r'id="run-embedding-maintenance"',
        r'id="clear-embedding-jobs"',
        r'<p[^>]*class="[^"]*risk-note[^"]*">\s*Clearing job history removes job records for the active memory space only\. Browser confirmation is required\.',
        r'id="dev-eval-form"',
        r'name="confirm"',
        r'id="threshold-form"',
        r'id="graph-form"',
        r'id="diagnostics"',
        r'id="log-tail-lines"',
        r'id="log-tail-filter"',
        r'id="log-tail-note"',
        r"Filter loaded log tail",
        r"Filters only the loaded log tail\.",
        r'id="copy-logs"',
        r'<button[^>]*data-action="archive"[^>]*class="[^"]*danger[^"]*"',
        r'<button[^>]*data-action="unset"[^>]*class="[^"]*danger[^"]*"',
        r'<button[^>]*data-action="remove-alias"[^>]*class="[^"]*danger[^"]*"',
        r'<button[^>]*id="reset-dev-seed"[^>]*class="[^"]*danger[^"]*"',
        r'<button[^>]*data-action="stop"[^>]*class="[^"]*danger[^"]*"',
        r'<p[^>]*class="[^"]*risk-note[^"]*"',
    ]:
        _assert_pattern(index_html, pattern)

    assert "Search memories" in index_html
    assert "workspaces, or services" not in index_html

    for pattern in [
        r"--bg-app: #0b0f14",
        r"--radius-shell: 12px",
        r"--radius-chip: 4px",
        r'--font-mono: "JetBrains Mono"',
        r"\.risk-note",
        r"\.tab-button\.active",
        r"\.list-item__meta",
        r"\.status-chip",
        r"\.micro-chip",
        r":focus-visible",
        r"prefers-reduced-motion",
    ]:
        _assert_pattern(styles_css, pattern)

    for pattern in [
        r"/v1/webui/memories",
        r"/v1/webui/workspaces",
        r"/v1/webui/config",
        r"/v1/webui/services",
        r"/v1/webui/embedding/status",
        r"/v1/webui/embedding/maintenance",
        r"/v1/webui/dev/optimize-threshold",
        r"/v1/webui/graph",
        r"/v1/webui/diagnostics",
        r"/v1/webui/logs",
        r"function selectTab\(name, \{ focusButton = false \} = \{\}\)",
        r"ArrowRight",
        r"ArrowLeft",
        r"Home",
        r"End",
        r"confirmDanger",
        r"escapeAttr",
        r"formatTimestamp",
        r"formatConfidence",
        r"updateServiceControls",
        r"wireGlobalSearch",
        r"syncCardSelection",
        r"service-restart-note",
        r"function normalizeMemoryEntry\(entry\)",
        r"renderEmbeddingStatus",
        r"renderGraph",
        r"renderDiagnosticsBundle",
        r"renderLogSummary",
        r"currentLogTailFilter",
        r"filterLoadedLogTailLines",
        r"logTailRawLines",
        r"logTailRenderedText",
        r"workspace\.alias_count",
        r"serviceDetails\.endpoint",
        r"serviceDetails\.port",
        r"job\.provider",
        r"job\.model",
        r"space\.source",
        r"lines\.join\('\\n'\)",
        r"log-tail-filter",
        r"copy-logs",
        r"confirmDanger\('Clear embedding job history'",
        r"confirmDanger\('Archive memory'",
        r"confirmDanger\('Unset config key'",
        r"confirmDanger\('Remove workspace alias'",
        r"confirmDanger\('Reset seeded dev database'",
        r"confirmDanger\('Stop service'",
    ]:
        _assert_pattern(app_js, pattern)

    for snippet in [
        "memory?.source",
        "memory?.confidence",
        "memory?.created_at",
        "memory?.updated_at",
    ]:
        assert snippet in app_js


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
    search_payload = search_response.json()
    assert search_payload["count"] == 1
    assert search_payload["results"][0]["memory"]["id"] == "mem-001"
    assert search_payload["results"][0]["score"] > 0.0

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


def test_webui_backend_supports_embeddings_dev_tools_graph_and_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    core = _make_core(tmp_path, monkeypatch)
    core.add_memory(
        space=SPACE_WORKSPACE,
        type="note",
        content="shared staging note with sensitive preview text",
        workspace_uid="project-alpha",
        metadata={"tags": ["alpha", "shared"]},
    )
    core.add_memory(
        space=SPACE_WORKSPACE,
        type="note",
        content="shared staging note with matching topic",
        workspace_uid="project-alpha",
        metadata={"tags": ["alpha", "shared"]},
    )

    monkeypatch.setattr(
        "recollectium.webui.RecollectiumCore", lambda *args, **kwargs: core
    )
    monkeypatch.setattr(
        "recollectium.webui.seeded_dev_database_is_initialized",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        "recollectium.webui.ensure_seeded_dev_database",
        lambda *_args, **_kwargs: {"status": "seeded"},
    )
    monkeypatch.setattr(
        "recollectium.webui.reset_seeded_dev_database",
        lambda *_args, **_kwargs: {"status": "reset"},
    )
    monkeypatch.setattr("recollectium.webui.asdict", lambda obj: dict(obj.__dict__))
    monkeypatch.setattr(
        "recollectium.webui.evaluate_exact_mrr_for_core",
        lambda _core: SimpleNamespace(
            value=0.42, targets=2, user_value=0.4, workspace_value=0.44
        ),
    )
    monkeypatch.setattr(
        "recollectium.webui.evaluate_semantic_mrr_for_core",
        lambda _core: SimpleNamespace(value=0.51, targets=2, queries=3),
    )
    monkeypatch.setattr(
        "recollectium.webui.evaluate_thematic_weighted_metrics_for_core",
        lambda _core: SimpleNamespace(
            weighted_precision=0.62, weighted_recall=0.58, weighted_f1=0.6
        ),
    )
    monkeypatch.setattr(
        "recollectium.webui.evaluate_ranked_set_ndcg_for_core",
        lambda _core: SimpleNamespace(value=0.71, cases=2),
    )

    class FakeThresholdReport:
        def to_dict(self) -> dict[str, object]:
            return {
                "recommended_threshold": 0.5,
                "tested_thresholds": 3,
                "rows": [{"threshold": 0.5, "recommended": True}],
            }

    monkeypatch.setattr(
        "recollectium.webui.build_threshold_search_bundles", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        "recollectium.webui.build_threshold_optimization_report",
        lambda **kwargs: FakeThresholdReport(),
    )
    monkeypatch.setattr(
        "recollectium.webui._log_summary_payload",
        lambda core, tail_lines=80: {
            "status": "ok",
            "log_dir": str(core.config.xdg_dirs["logs"]),
            "log_files": [
                {
                    "path": str(core.config.xdg_dirs["logs"] / "recollectium.log"),
                    "exists": False,
                    "lines": ["log line one", "log line two"],
                    "line_count": 2,
                    "truncated": False,
                }
            ],
            "recent": {
                "path": str(core.config.xdg_dirs["logs"] / "recollectium.log"),
                "exists": False,
                "lines": ["log line one", "log line two"],
                "line_count": 2,
                "truncated": False,
            },
        },
    )

    client = _client(core)

    embedding_status = client.get("/v1/webui/embedding/status")
    assert embedding_status.status_code == 200
    embedding_payload = embedding_status.json()
    assert embedding_payload["provider_status"] == "configured"
    assert "model_state" in embedding_payload

    embedding_jobs = client.get("/v1/webui/embedding/jobs")
    assert embedding_jobs.status_code == 200
    assert embedding_jobs.json()["count"] == 1

    embedding_job = client.get("/v1/webui/embedding/jobs/job-001")
    assert embedding_job.status_code == 200
    assert embedding_job.json()["job"]["id"] == "job-001"

    refresh_embeddings = client.post(
        "/v1/webui/embedding/refresh",
        json={"space": "user", "include_archived": False},
    )
    assert refresh_embeddings.status_code == 200
    assert refresh_embeddings.json()["result"]["refreshed"] is True

    clear_embedding_jobs = client.request(
        "DELETE",
        "/v1/webui/embedding/jobs",
        json={"states": ["completed"]},
    )
    assert clear_embedding_jobs.status_code == 200
    assert clear_embedding_jobs.json()["result"]["deleted_count"] == 1

    dev_status = client.get("/v1/webui/dev/status")
    assert dev_status.status_code == 200
    assert dev_status.json()["seeded_database"]["initialized"] is True

    dev_seed_init = client.post("/v1/webui/dev/seeding/init")
    assert dev_seed_init.status_code == 200
    assert dev_seed_init.json()["status"] in {"ok", "seeded"}

    dev_seed_reset = client.post("/v1/webui/dev/seeding/reset")
    assert dev_seed_reset.status_code == 200
    assert dev_seed_reset.json()["status"] == "reset"

    dev_eval_pending = client.post("/v1/webui/dev/eval", json={"confirm": False})
    assert dev_eval_pending.status_code == 200
    assert dev_eval_pending.json()["status"] == "confirmation_required"

    dev_eval = client.post("/v1/webui/dev/eval", json={"confirm": True})
    assert dev_eval.status_code == 200
    assert dev_eval.json()["reports"]["exact_mrr"]["value"] == 0.42

    threshold_pending = client.post(
        "/v1/webui/dev/optimize-threshold",
        json={
            "start": 0.0,
            "end": 1.0,
            "step": 0.5,
            "beta": 0.5,
            "output_format": "csv",
            "write_config": False,
            "confirm": False,
        },
    )
    assert threshold_pending.status_code == 200
    assert threshold_pending.json()["status"] == "confirmation_required"

    threshold = client.post(
        "/v1/webui/dev/optimize-threshold",
        json={
            "start": 0.0,
            "end": 1.0,
            "step": 0.5,
            "beta": 0.5,
            "output_format": "csv",
            "write_config": False,
            "confirm": True,
        },
    )
    assert threshold.status_code == 200
    assert threshold.json()["report"]["recommended_threshold"] == 0.5

    maintenance_pending = client.post(
        "/v1/webui/embedding/maintenance",
        json={"confirm": False},
    )
    assert maintenance_pending.status_code == 200
    assert maintenance_pending.json()["status"] == "confirmation_required"

    maintenance = client.post(
        "/v1/webui/embedding/maintenance",
        json={"confirm": True},
    )
    assert maintenance.status_code == 200
    assert maintenance.json()["status"] == "embedding_maintenance_completed"
    assert core.model_ready_calls

    graph = client.get("/v1/webui/graph?limit=10")
    assert graph.status_code == 200
    graph_payload = graph.json()
    assert graph_payload["summary"]["memory_count"] >= 2
    assert any(node["kind"] == "memory_space" for node in graph_payload["nodes"])
    assert any(node["kind"] == "memory" for node in graph_payload["nodes"])
    assert all("content_preview" not in node for node in graph_payload["nodes"])
    graph_text = json.dumps(graph_payload)
    assert "shared staging note with sensitive preview text" not in graph_text
    assert any(
        edge["kind"] == "memory_relationship"
        and edge["source"].startswith("mem-")
        and edge["target"].startswith("mem-")
        for edge in graph_payload["edges"]
    )

    diagnostics = client.get("/v1/webui/diagnostics")
    assert diagnostics.status_code == 200
    diagnostics_payload = diagnostics.json()
    assert diagnostics_payload["config_validation"]["valid"] is True
    assert diagnostics_payload["logs"]["recent"]["lines"][0] == "log line one"

    logs = client.get("/v1/webui/logs")
    assert logs.status_code == 200
    assert logs.json()["recent"]["line_count"] == 2


def test_webui_redacts_config_and_diagnostics_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_config = {
        "api": {
            "token": "super-secret-token",
            "endpoint": "http://localhost:9999",
        },
        "credentials": {
            "password": "hunter2",
            "nested": {"client_secret": "abc123"},
        },
        "service": {"endpoint": "http://localhost:8765"},
    }
    config = _make_config(tmp_path, monkeypatch, raw_config=raw_config)
    client = _client(FakeCore(config))

    config_response = client.get("/v1/webui/config")
    assert config_response.status_code == 200
    config_payload = config_response.json()
    config_text = config_response.text
    assert "super-secret-token" not in config_text
    assert "hunter2" not in config_text
    assert "abc123" not in config_text
    assert config_payload["config"]["api"]["token"] == "[redacted]"
    assert config_payload["config"]["credentials"] == "[redacted]"
    assert config_payload["config"]["service"]["endpoint"] == "http://localhost:8765"

    diagnostics_response = client.get("/v1/webui/diagnostics?tail_lines=10")
    assert diagnostics_response.status_code == 200
    diagnostics_payload = diagnostics_response.json()
    diagnostics_text = diagnostics_response.text
    assert "super-secret-token" not in diagnostics_text
    assert (
        diagnostics_payload["config_validation"]["config"]["api"]["token"]
        == "[redacted]"
    )
    assert (
        diagnostics_payload["config_validation"]["config"]["credentials"]
        == "[redacted]"
    )


def test_webui_logs_support_bounded_tail_depth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    core = _make_core(tmp_path, monkeypatch)
    log_dir = core.config.xdg_dirs["logs"]
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "recollectium.log"
    lines = [f"{index:04d} café {'x' * 180}" for index in range(1000)]
    log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    client = _client(core)

    logs = client.get("/v1/webui/logs?tail_lines=5")
    assert logs.status_code == 200
    logs_payload = logs.json()
    assert logs_payload["recent"]["lines"] == lines[-10:]
    assert logs_payload["recent"]["truncated"] is True

    diagnostics = client.get("/v1/webui/diagnostics?tail_lines=7")
    assert diagnostics.status_code == 200
    diagnostics_payload = diagnostics.json()
    assert diagnostics_payload["logs"]["recent"]["lines"] == lines[-10:]


def test_webui_root_serves_shell_and_bootstrap_endpoints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(_make_core(tmp_path, monkeypatch))

    root_response = client.get("/")
    assert root_response.status_code == 200
    assert "Recollectium WebUI" in root_response.text
    assert "cockpit-shell" in root_response.text
    assert 'id="global-search-form"' in root_response.text
    assert 'id="memory-search-form"' in root_response.text

    app_js = client.get("/assets/app.js")
    assert app_js.status_code == 200
    assert "/v1/webui/context" in app_js.text
    assert "/v1/webui/embedding/status" in app_js.text
    assert "/v1/webui/graph" in app_js.text
    assert "/v1/webui/diagnostics" in app_js.text
    assert "/v1/webui/dev/optimize-threshold" in app_js.text
