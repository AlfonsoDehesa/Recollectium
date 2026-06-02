from pathlib import Path
import json
import re
from typing import Any

from fastapi.testclient import TestClient
import pytest

from recollectium.core import RecollectiumCore
from recollectium.models import (
    ALL_MEMORY_TYPES,
    USER_MEMORY_TYPES,
    WORKSPACE_MEMORY_TYPES,
)
from recollectium.errors import ValidationError
from recollectium.service import (
    _map_boundary_error,
    _parse_optional_bool,
    _parse_optional_positive_int,
    create_app,
    create_mcp_app,
    run_service,
)
from recollectium.service_contract import (
    OPERATION_EMBEDDING_JOBS_GET,
    OPERATION_EMBEDDING_REFRESH,
    OPERATION_EMBEDDING_JOBS_CLEAR,
    OPERATION_EMBEDDING_JOBS_LIST,
    OPERATION_EMBEDDING_STATUS,
    OPERATION_CAPABILITIES_READ,
    OPERATION_HEALTH_READ,
    OPERATION_MEMORIES_ADD,
    OPERATION_MEMORIES_ARCHIVE,
    OPERATION_MEMORIES_GET,
    OPERATION_MEMORIES_LIST,
    OPERATION_MEMORIES_SEARCH_USER,
    OPERATION_MEMORIES_SEARCH_WORKSPACE,
    OPERATION_MEMORIES_UPDATE,
    OPERATION_VERSION_READ,
    OPERATION_WORKSPACES_LIST,
    OPERATION_WORKSPACES_RENAME,
    OPERATION_WORKSPACES_RESOLVE,
    OPERATION_WORKSPACES_ALIASES_LIST,
    OPERATION_WORKSPACES_ALIASES_ADD,
    OPERATION_WORKSPACES_ALIASES_REMOVE,
    SERVICE_API_VERSION,
    SERVICE_CAPABILITIES,
    capabilities_payload,
    error_payload,
    health_payload,
    serialize_embedding_job,
    serialize_embedding_jobs,
    serialize_embedding_operation_result,
    serialize_embedding_status,
    serialize_memories,
    serialize_memory,
    serialize_search_result,
    serialize_search_results,
    success_payload,
    version_payload,
)


def test_service_capabilities_cover_required_operations() -> None:
    assert SERVICE_CAPABILITIES == (
        OPERATION_HEALTH_READ,
        OPERATION_VERSION_READ,
        OPERATION_CAPABILITIES_READ,
        OPERATION_MEMORIES_SEARCH_USER,
        OPERATION_MEMORIES_SEARCH_WORKSPACE,
        OPERATION_MEMORIES_ADD,
        OPERATION_MEMORIES_UPDATE,
        OPERATION_MEMORIES_ARCHIVE,
        OPERATION_MEMORIES_LIST,
        OPERATION_MEMORIES_GET,
        OPERATION_EMBEDDING_STATUS,
        OPERATION_EMBEDDING_JOBS_LIST,
        OPERATION_EMBEDDING_JOBS_GET,
        OPERATION_EMBEDDING_REFRESH,
        OPERATION_EMBEDDING_JOBS_CLEAR,
        OPERATION_WORKSPACES_LIST,
        OPERATION_WORKSPACES_RENAME,
        OPERATION_WORKSPACES_RESOLVE,
        OPERATION_WORKSPACES_ALIASES_LIST,
        OPERATION_WORKSPACES_ALIASES_ADD,
        OPERATION_WORKSPACES_ALIASES_REMOVE,
    )


def test_metadata_payload_helpers_are_stable() -> None:
    assert health_payload() == {"data": {"status": "ok"}}

    version = version_payload()
    assert version["data"]["service_api_version"] == SERVICE_API_VERSION
    assert isinstance(version["data"]["recollectium_version"], str)

    capabilities = capabilities_payload()
    assert capabilities["data"] == {
        "service_api_version": SERVICE_API_VERSION,
        "capabilities": list(SERVICE_CAPABILITIES),
        "memory_types": {
            "user": list(USER_MEMORY_TYPES),
            "workspace": list(WORKSPACE_MEMORY_TYPES),
            "all": list(ALL_MEMORY_TYPES),
        },
    }


def test_error_payload_shape_is_stable() -> None:
    assert error_payload("validation_error", "bad request") == {
        "error": {
            "code": "validation_error",
            "message": "bad request",
            "details": {},
        }
    }
    assert error_payload(
        "validation_error",
        "bad request",
        details={"field": "workspace_uid"},
    ) == {
        "error": {
            "code": "validation_error",
            "message": "bad request",
            "details": {"field": "workspace_uid"},
        }
    }


def test_serializers_use_existing_models(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-contract.db")
    memory = core.add_memory(
        space="user",
        type="fact",
        content="Kaylee likes tea",
        metadata={"source": "chat"},
    )
    results = core.search_user_memories("likes tea")

    serialized_memory = serialize_memory(memory)
    assert serialized_memory["id"] == memory.id
    assert serialized_memory["metadata"] == {"source": "chat"}

    serialized_memories = serialize_memories([memory])
    assert serialized_memories == [memory.to_dict()]

    serialized_result = serialize_search_result(results[0])
    assert serialized_result["memory"]["id"] == memory.id
    assert serialized_result["rank"] == 1

    serialized_results = serialize_search_results(results)
    assert serialized_results == [result.to_dict() for result in results]

    compact_results = serialize_search_results(results, verbosity="compact")
    assert compact_results == [
        {"id": memory.id, "content": "Kaylee likes tea", "match": results[0].score}
    ]
    assert isinstance(compact_results[0]["match"], float)

    status = {"provider_status": "configured"}
    assert serialize_embedding_status(status) is status
    assert serialize_embedding_operation_result(status) is status

    job = {"id": "job-1"}
    assert serialize_embedding_job(job) is job
    assert serialize_embedding_jobs([job]) == [job]


def test_embedding_serializers_project_with_operation_and_verbosity() -> None:
    status = {
        "provider_status": "configured",
        "embedding_profile": {"provider": "fake", "model": "fake-model"},
        "model_status": {"ready": True},
        "embedding_jobs_status_path": "/tmp/jobs.json",
        "extra_detail": "verbose-only",
    }

    compact_status = serialize_embedding_status(
        status, operation=OPERATION_EMBEDDING_STATUS
    )
    assert compact_status == {
        "provider_status": "configured",
        "embedding_profile": {"provider": "fake", "model": "fake-model"},
        "model_status": {"ready": True},
        "embedding_jobs_status_path": "/tmp/jobs.json",
    }
    assert serialize_embedding_status(
        status,
        verbosity="verbose",
        operation=OPERATION_EMBEDDING_STATUS,
    ) is status

    job = {
        "id": "job-1",
        "state": "completed",
        "reason": "test",
        "total": 2,
        "succeeded": 2,
        "failed": 0,
        "started_at": "verbose-only",
    }
    compact_job = {
        "id": "job-1",
        "state": "completed",
        "reason": "test",
        "total": 2,
        "succeeded": 2,
        "failed": 0,
    }
    assert serialize_embedding_job(
        job, operation=OPERATION_EMBEDDING_JOBS_GET
    ) == compact_job
    assert serialize_embedding_jobs(
        [job], operation=OPERATION_EMBEDDING_JOBS_LIST
    ) == [compact_job]


def test_success_payload_wraps_data_without_mutation() -> None:
    data = [{"id": "m-1"}, {"id": "m-2"}]
    assert success_payload(data) == {"data": data}


def test_local_service_docs_cover_request_and_response_behavior_for_all_routes() -> (
    None
):
    docs_path = Path(__file__).resolve().parents[1] / "docs" / "local-service-api.md"
    assert docs_path.exists()

    docs_text = docs_path.read_text(encoding="utf-8")
    routes = {
        "GET /v1/health": {"require_request": False},
        "GET /v1/version": {"require_request": False},
        "GET /v1/capabilities": {"require_request": False},
        "POST /v1/memories/search_user": {"require_request": True},
        "POST /v1/memories/search_workspace": {"require_request": True},
        "POST /v1/memories": {"require_request": True},
        "PATCH /v1/memories/{memory_id}": {"require_request": True},
        "POST /v1/memories/{memory_id}/archive": {"require_request": True},
        "GET /v1/memories": {"require_request": True},
        "GET /v1/memories/{memory_id}": {"require_request": True},
        "GET /v1/embedding/status": {"require_request": False},
        "GET /v1/embedding/jobs": {"require_request": False},
        "POST /v1/embedding/refresh": {"require_request": True},
        "DELETE /v1/embedding/jobs": {"require_request": True},
        "GET /v1/embedding/jobs/{job_id}": {"require_request": False},
    }

    for route, constraints in routes.items():
        assert route in docs_text
        section = _service_docs_section_for_route(docs_text, route)
        assert "Purpose:" in section
        if constraints["require_request"]:
            assert "Example request:" in section
            assert "curl" in section
        assert "Example response:" in section or "Response example:" in section
        assert '"data":' in section

    for error_code in (
        "embedding_provider_unavailable",
        "embedding_model_unavailable",
        "embedding_generation_failed",
        "embedding_profile_mismatch",
        "embedding_readiness_timeout",
        "reembedding_in_progress",
        "reembedding_failed",
    ):
        assert error_code in docs_text

    assert "POST /v1/memories/{memory_id}/archive` is body-less." in docs_text


def test_local_service_openapi_contract_is_valid_and_covers_routes(
    tmp_path: Path,
) -> None:
    openapi_path = (
        Path(__file__).resolve().parents[1] / "docs" / "local-service-openapi.json"
    )
    assert openapi_path.exists()

    contract = json.loads(openapi_path.read_text(encoding="utf-8"))
    app = create_app(RecollectiumCore(db_path=tmp_path / "openapi.db"))
    assert contract == app.openapi()
    assert contract["openapi"] == "3.1.0"

    info_description = contract["info"]["description"].lower()
    assert "localhost" in info_description or "local" in info_description
    assert "no authentication" in info_description or "no auth" in info_description

    paths = contract["paths"]
    required_paths = {
        "/v1/health": ["get"],
        "/v1/version": ["get"],
        "/v1/capabilities": ["get"],
        "/v1/memories/search_user": ["post"],
        "/v1/memories/search_workspace": ["post"],
        "/v1/memories": ["post", "get"],
        "/v1/memories/{memory_id}": ["patch", "get"],
        "/v1/memories/{memory_id}/archive": ["post"],
        "/v1/embedding/status": ["get"],
        "/v1/embedding/jobs": ["get"],
        "/v1/embedding/jobs/{job_id}": ["get"],
        "/v1/workspaces": ["get"],
        "/v1/workspaces/resolve": ["get"],
        "/v1/workspaces/{uid}/aliases": ["get", "post"],
        "/v1/workspaces/aliases/{alias_uid}": ["delete"],
        "/v1/workspaces/{uid}/rename": ["post"],
    }
    for path, methods in required_paths.items():
        assert path in paths
        for method in methods:
            assert method in paths[path]

    archive_operation = paths["/v1/memories/{memory_id}/archive"]["post"]
    assert "requestBody" not in archive_operation

    for metadata_path in ("/v1/health", "/v1/version"):
        parameter_names = {
            parameter["name"] for parameter in paths[metadata_path]["get"]["parameters"]
        }
        assert {"verbosity", "X-Recollectium-Verbosity"} <= parameter_names

    schemas = contract["components"]["schemas"]
    for schema_name in (
        "AddMemoryRequest",
        "SearchUserRequest",
        "SearchWorkspaceRequest",
        "UpdateMemoryRequest",
        "RenameWorkspaceRequest",
        "AddWorkspaceAliasRequest",
    ):
        assert schema_name in schemas


def _service_docs_section_for_route(docs_text: str, route: str) -> str:
    route_index = docs_text.index(route)
    next_heading_match = re.search(r"\n### ", docs_text[route_index + 1 :])
    if next_heading_match is None:
        return docs_text[route_index:]

    next_heading_index = route_index + 1 + next_heading_match.start()
    return docs_text[route_index:next_heading_index]


def _client(core: RecollectiumCore) -> TestClient:
    return TestClient(create_app(core), raise_server_exceptions=False)


def _request_json(
    client: TestClient,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    response = client.request(method, path, json=body)
    return response.status_code, response.json()


def _request_raw(
    client: TestClient,
    method: str,
    path: str,
    body: bytes,
) -> tuple[int, dict[str, Any]]:
    response = client.request(
        method,
        path,
        content=body,
        headers={"Content-Type": "application/json"},
    )
    return response.status_code, response.json()


def test_http_metadata_routes_return_json(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-metadata.db")
    client = _client(core)

    status, payload = _request_json(client, "GET", "/v1/health")
    assert status == 200
    assert payload == {"data": {"status": "ok"}}

    status, payload = _request_json(client, "GET", "/v1/version")
    assert status == 200
    assert payload["data"]["service_api_version"] == "1"

    status, payload = _request_json(client, "GET", "/v1/capabilities")
    assert status == 200
    assert payload["data"]["capabilities"] == list(SERVICE_CAPABILITIES)


def test_http_local_service_smoke_end_to_end(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-smoke.db")
    client = _client(core)

    status, health = _request_json(client, "GET", "/v1/health")
    assert status == 200
    assert health == {"data": {"status": "ok"}}

    # add_memory now defaults to compact mutation projection
    status, added = _request_json(
        client,
        "POST",
        "/v1/memories",
        {
            "space": "user",
            "type": "fact",
            "content": "smoke test memory",
        },
    )
    assert status == 200
    data = added["data"]
    assert data["status"] == "saved"
    assert isinstance(data["id"], str)

    # retrieve in verbose to verify content
    mem_id = data["id"]
    status, got = _request_json(
        client, "GET", f"/v1/memories/{mem_id}?verbosity=verbose"
    )
    assert status == 200
    assert got["data"]["content"] == "smoke test memory"
    assert got["data"]["space"] == "user"


def test_http_memory_routes_delegate_to_core(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-memory-routes.db")
    client = _client(core)

    status, added_user = _request_json(
        client,
        "POST",
        "/v1/memories",
        {"space": "user", "type": "fact", "content": "Alfonso likes tea"},
    )
    assert status == 200
    user_id = str(added_user["data"]["id"])

    status, added_workspace = _request_json(
        client,
        "POST",
        "/v1/memories",
        {
            "space": "workspace",
            "type": "decision",
            "content": "Use sqlite for local db",
            "workspace_uid": "ws-1",
        },
    )
    assert status == 200
    workspace_id = str(added_workspace["data"]["id"])

    status, list_payload = _request_json(client, "GET", "/v1/memories")
    assert status == 200
    assert {item["id"] for item in list_payload["data"]} == {user_id, workspace_id}

    status, search_user = _request_json(
        client,
        "POST",
        "/v1/memories/search_user",
        {"query": "likes tea", "type": "fact"},
    )
    assert status == 200
    # compact search result: {id, content, match}
    assert search_user["data"][0]["id"] == user_id

    status, search_workspace = _request_json(
        client,
        "POST",
        "/v1/memories/search_workspace",
        {"query": "sqlite", "workspace_uid": "ws-1", "type": "decision"},
    )
    assert status == 200
    assert search_workspace["data"][0]["id"] == workspace_id

    # get_memory returns compact by default
    status, got_memory = _request_json(client, "GET", f"/v1/memories/{user_id}")
    assert status == 200
    assert got_memory["data"]["id"] == user_id

    # update_memory returns compact by default; verify content via verbose get
    status, updated = _request_json(
        client,
        "PATCH",
        f"/v1/memories/{user_id}",
        {"content": "Alfonso likes green tea"},
    )
    assert status == 200
    assert updated["data"]["status"] == "updated"
    assert updated["data"]["id"] == user_id

    # verbose get to verify content change
    status, verbose_get = _request_json(
        client, "GET", f"/v1/memories/{user_id}?verbosity=verbose"
    )
    assert status == 200
    assert verbose_get["data"]["content"] == "Alfonso likes green tea"

    status, archived = _request_json(
        client,
        "POST",
        f"/v1/memories/{user_id}/archive",
    )
    assert status == 200
    assert archived["data"]["status"] == "archived"

    status, list_default = _request_json(client, "GET", "/v1/memories")
    assert status == 200
    listed_ids_default = {item["id"] for item in list_default["data"]}
    assert user_id not in listed_ids_default
    assert workspace_id in listed_ids_default

    status, list_with_archived = _request_json(
        client,
        "GET",
        "/v1/memories?include_archived=true",
    )
    assert status == 200
    listed_ids_all = {item["id"] for item in list_with_archived["data"]}
    assert user_id in listed_ids_all
    assert workspace_id in listed_ids_all

    # embedding status is compact by default; use verbose for full check
    status, embedding_status = _request_json(
        client, "GET", "/v1/embedding/status?verbosity=verbose"
    )
    assert status == 200
    assert (
        embedding_status["data"]["embedding_profile"]["provider"] == "builtin-fastembed"
    )
    assert embedding_status["data"]["provider_status"] == "configured"
    assert embedding_status["data"]["model_status"] == "managed_by_fastembed_cache"
    assert embedding_status["data"]["runtime"] == {
        "name": "fastembed",
        "threads": 1,
        "parallel": None,
    }

    status, jobs_payload = _request_json(client, "GET", "/v1/embedding/jobs")
    assert status == 200
    jobs = jobs_payload["data"]
    assert isinstance(jobs, list)
    if jobs:
        job_id = jobs[0]["id"]
        status, one_job = _request_json(client, "GET", f"/v1/embedding/jobs/{job_id}")
        assert status == 200
        assert one_job["data"]["id"] == job_id

    status, limited_jobs = _request_json(client, "GET", "/v1/embedding/jobs?limit=1")
    assert status == 200
    assert len(limited_jobs["data"]) <= 1


def test_http_query_parsers_accept_valid_values_and_reject_bad_values() -> None:
    assert _parse_optional_bool(None, field_name="include_archived") is None
    assert _parse_optional_bool(" TRUE ", field_name="include_archived") is True
    assert _parse_optional_bool("false", field_name="include_archived") is False

    with pytest.raises(ValidationError, match="include_archived"):
        _parse_optional_bool("yes", field_name="include_archived")

    assert _parse_optional_positive_int(None, field_name="limit") is None
    assert _parse_optional_positive_int("3", field_name="limit") == 3

    with pytest.raises(ValidationError, match="positive integer"):
        _parse_optional_positive_int("nope", field_name="limit")

    with pytest.raises(ValidationError, match="positive integer"):
        _parse_optional_positive_int("0", field_name="limit")


def test_http_invalid_query_params_return_validation_errors(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-query-validation.db")
    client = _client(core)

    status, payload = _request_json(client, "GET", "/v1/memories?include_archived=yes")
    assert status == 400
    assert payload["error"]["code"] == "validation_error"

    status, payload = _request_json(client, "GET", "/v1/embedding/jobs?limit=0")
    assert status == 400
    assert payload["error"]["code"] == "validation_error"


def test_http_workspace_search_requires_workspace_uid(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-workspace-validation.db")
    client = _client(core)

    status, payload = _request_json(
        client,
        "POST",
        "/v1/memories/search_workspace",
        {"query": "hello"},
    )
    assert status == 400
    assert payload["error"]["code"] == "validation_error"


def test_http_unknown_route_returns_unsupported_operation(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-unknown-route.db")
    client = _client(core)

    status, payload = _request_json(client, "GET", "/v1/nope")
    assert status == 404
    assert payload["error"]["code"] == "unsupported_operation"


def test_http_exception_handler_preserves_other_http_errors(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-http-error.db")
    app = create_app(core)

    from fastapi import HTTPException

    @app.get("/boom")
    def boom() -> None:
        raise HTTPException(status_code=418, detail="short and stout")

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/boom")
    assert response.status_code == 418
    assert response.json()["error"] == {
        "code": "http_error",
        "message": "short and stout",
        "details": {},
    }


def test_http_get_missing_memory_returns_not_found(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-missing-memory.db")
    client = _client(core)

    status, payload = _request_json(client, "GET", "/v1/memories/missing-id")
    assert status == 404
    assert payload["error"]["code"] == "not_found"


def test_http_get_missing_embedding_job_returns_not_found(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-missing-job.db")
    client = _client(core)

    status, payload = _request_json(client, "GET", "/v1/embedding/jobs/missing-job")

    assert status == 404
    assert payload["error"]["code"] == "not_found"


def test_http_get_embedding_job_returns_existing_job(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-existing-job.db")
    job = core.store.create_embedding_job(
        job_id="job-1",
        state="completed",
        total_count=1,
        processed_count=1,
        succeeded_count=1,
        failed_count=0,
        provider="test",
        model="fake",
        embedding_profile={"provider": "test", "model": "fake", "dimensions": 3},
    )
    client = _client(core)

    status, payload = _request_json(client, "GET", f"/v1/embedding/jobs/{job['id']}")

    assert status == 200
    assert payload["data"]["id"] == "job-1"


def test_embedding_refresh_and_clear_jobs_endpoints(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-refresh.db")
    client = _client(core)

    status, refresh_payload = _request_json(client, "POST", "/v1/embedding/refresh")
    assert status == 200
    # compact projection: refreshed, stale_count, status_path (job omitted when None)
    assert refresh_payload["data"] == {
        "refreshed": False,
        "stale_count": 0,
        "status_path": "/v1/embedding/jobs",
    }

    status, refresh_payload = _request_json(
        client,
        "POST",
        "/v1/embedding/refresh",
        body={"space": "user", "include_archived": False},
    )
    assert status == 200
    assert refresh_payload["data"] == {
        "refreshed": False,
        "stale_count": 0,
        "status_path": "/v1/embedding/jobs",
    }

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
    status, clear_payload = _request_json(
        client,
        "DELETE",
        "/v1/embedding/jobs",
        body={"states": ["pending"]},
    )
    assert status == 200
    assert clear_payload["data"] == {"deleted_count": 1, "states": ["pending"]}


def test_http_invalid_json_returns_invalid_json_error(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-invalid-json.db")
    client = _client(core)

    status, payload = _request_raw(
        client,
        "POST",
        "/v1/memories",
        b'{"space": "user",',
    )
    assert status == 400
    assert payload["error"]["code"] == "invalid_json"


def test_http_unsupported_method_returns_unsupported_operation(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-unsupported-method.db")
    client = _client(core)

    status, payload = _request_json(client, "POST", "/v1/health")
    assert status == 404
    assert payload["error"]["code"] == "unsupported_operation"


def test_http_internal_error_is_mapped_without_traceback(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-internal-error.db")
    client = _client(core)
    original = core.list_memories

    def boom(*args: Any, **kwargs: Any) -> list[Any]:
        raise RuntimeError("db blew up with private details")

    core.list_memories = boom
    try:
        status, payload = _request_json(client, "GET", "/v1/memories")
        assert status == 500
        assert payload["error"]["code"] == "internal_error"
        assert payload["error"]["message"] == "internal server error"
    finally:
        core.list_memories = original


def test_http_embedding_errors_map_to_stable_boundary_codes(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-embedding-errors.db")
    client = _client(core)
    original = core.search_user_memories

    from recollectium.errors import (
        EmbeddingDimensionMismatchError,
        EmbeddingGenerationError,
        EmbeddingModelUnavailableError,
        EmbeddingProviderUnavailableError,
        EmbeddingReadinessTimeoutError,
        ReembeddingFailedError,
        ReembeddingInProgressError,
    )

    error_cases = [
        (
            EmbeddingReadinessTimeoutError("FastEmbed provider startup timed out"),
            503,
            "embedding_readiness_timeout",
        ),
        (
            EmbeddingProviderUnavailableError("FastEmbed is unavailable"),
            503,
            "embedding_provider_unavailable",
        ),
        (
            EmbeddingModelUnavailableError("failed to load embedding model"),
            503,
            "embedding_model_unavailable",
        ),
        (
            EmbeddingDimensionMismatchError("unexpected embedding dimension"),
            500,
            "embedding_profile_mismatch",
        ),
        (
            EmbeddingGenerationError("failed to generate embedding"),
            500,
            "embedding_generation_failed",
        ),
        (
            ReembeddingFailedError(
                "runtime re-embedding failed",
                job_id="job-failed",
                status_path="/v1/embedding/jobs/job-failed",
            ),
            503,
            "reembedding_failed",
        ),
    ]

    def reembedding_in_progress(*args: Any, **kwargs: Any) -> list[Any]:
        raise ReembeddingInProgressError(
            "re-embedding is in progress for the active profile",
            job_id="job-123",
            status_path="/v1/embedding/jobs/job-123",
        )

    core.search_user_memories = reembedding_in_progress
    try:
        status, payload = _request_json(
            client,
            "POST",
            "/v1/memories/search_user",
            {"query": "test"},
        )
        assert status == 409
        assert payload["error"]["code"] == "reembedding_in_progress"
        assert payload["error"]["details"] == {
            "job_id": "job-123",
            "status_path": "/v1/embedding/jobs/job-123",
        }

        for error, expected_status, expected_code in error_cases:

            def raise_error(*args: Any, **kwargs: Any) -> list[Any]:
                raise error

            core.search_user_memories = raise_error
            status, payload = _request_json(
                client,
                "POST",
                "/v1/memories/search_user",
                {"query": "test"},
            )
            assert status == expected_status
            assert payload["error"]["code"] == expected_code

            if expected_code == "reembedding_failed":
                assert payload["error"]["details"] == {
                    "job_id": "job-failed",
                    "status_path": "/v1/embedding/jobs/job-failed",
                }
    finally:
        core.search_user_memories = original


def test_boundary_error_maps_json_decode_error_message() -> None:
    error = json.JSONDecodeError("missing value", "{", 1)

    status, payload = _map_boundary_error(error)

    assert status == 400
    assert payload["error"]["code"] == "invalid_json"
    assert payload["error"]["message"] == "invalid JSON: missing value"


def test_run_service_builds_core_and_starts_uvicorn(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeCore:
        def __init__(
            self,
            *,
            db_path: str | None,
            config_path: str | None = None,
            log_level: str | None = None,
        ) -> None:
            calls["db_path"] = db_path
            self.config = type(
                "FakeConfig",
                (),
                {"effective_config": {"logging": {"level": "debug"}}},
            )()

        def _ensure_model_ready(self) -> None:
            pass

    def fake_create_app(core: object) -> str:
        calls["core"] = core
        return "fake-app"

    def fake_run(
        app: object,
        *,
        host: str,
        port: int,
        log_level: str,
        log_config: dict[str, object] | None,
    ) -> None:
        calls["app"] = app
        calls["host"] = host
        calls["port"] = port
        calls["log_level"] = log_level
        calls["log_config"] = log_config

    monkeypatch.setattr("recollectium.service.RecollectiumCore", FakeCore)
    monkeypatch.setattr("recollectium.service.create_app", fake_create_app)

    import uvicorn

    monkeypatch.setattr(uvicorn, "run", fake_run)

    run_service(host="127.0.0.2", port=9002, db_path="service.db")

    assert calls["db_path"] == "service.db"
    assert calls["app"] == "fake-app"
    assert calls["host"] == "127.0.0.2"
    assert calls["port"] == 9002
    assert calls["log_level"] == "debug"
    assert calls["log_config"] is None


def test_create_mcp_app_instantiates_fastapi_with_sse_mount(
    tmp_path: Path,
) -> None:
    db_path = str(tmp_path / "mcp-app.db")
    core = RecollectiumCore(db_path=db_path)
    app = create_mcp_app(core)

    from fastapi import FastAPI

    assert isinstance(app, FastAPI)
    assert app.title == "Recollectium MCP Server"


def test_run_service_mcp_uses_create_mcp_app(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeCore:
        def __init__(
            self,
            *,
            db_path: str | None,
            config_path: str | None = None,
            log_level: str | None = None,
        ) -> None:
            self.config = type(
                "FakeConfig",
                (),
                {"effective_config": {"logging": {"level": "info"}}},
            )()

        def _ensure_model_ready(self) -> None:
            pass

    def fake_create_mcp_app(core: object) -> str:
        calls["mcp_core"] = core
        return "fake-mcp-app"

    def fake_run(
        app: object,
        *,
        host: str,
        port: int,
        log_level: str,
        log_config: dict[str, object] | None,
    ) -> None:
        calls["app"] = app
        calls["host"] = host
        calls["log_config"] = log_config

    monkeypatch.setattr("recollectium.service.RecollectiumCore", FakeCore)
    monkeypatch.setattr("recollectium.service.create_mcp_app", fake_create_mcp_app)

    import uvicorn

    monkeypatch.setattr(uvicorn, "run", fake_run)

    run_service(
        host="127.0.0.1",
        port=8900,
        db_path="mcp.db",
        service_type="mcp",
    )

    assert calls["app"] == "fake-mcp-app"
    assert calls["log_config"] is None


def test_run_service_exits_cleanly_on_readiness_failure(monkeypatch) -> None:
    class FailingCore:
        def __init__(self, *, db_path=None, config_path=None, log_level=None):
            self.config = type(
                "FakeConfig",
                (),
                {"effective_config": {"logging": {"level": "info"}}},
            )()

        def _ensure_model_ready(self) -> None:
            raise Exception("model download failed")

    monkeypatch.setattr("recollectium.service.RecollectiumCore", FailingCore)

    with pytest.raises(SystemExit) as exc_info:
        run_service(host="127.0.0.1", port=8901, db_path="fail.db")
    assert exc_info.value.code == 1


# -- workspace API tests --------------------------------------------------


def test_get_workspaces_returns_empty_list(tmp_path: Path) -> None:
    """GET /v1/workspaces on empty database returns empty array."""
    core = RecollectiumCore(db_path=tmp_path / "ws.db")
    client = _client(core)

    status, payload = _request_json(client, "GET", "/v1/workspaces")
    assert status == 200
    assert payload["data"] == []


def test_get_workspaces_returns_sorted_uids(tmp_path: Path) -> None:
    """GET /v1/workspaces returns distinct workspace UIDs sorted."""
    core = RecollectiumCore(db_path=tmp_path / "ws.db")
    core.add_memory(
        space="workspace", type="fact", content="a", workspace_uid="project-b"
    )
    core.add_memory(
        space="workspace", type="fact", content="b", workspace_uid="project-a"
    )

    client = _client(core)
    status, payload = _request_json(client, "GET", "/v1/workspaces")
    assert status == 200
    assert payload["data"] == ["project-a", "project-b"]


def test_get_workspaces_include_archived(tmp_path: Path) -> None:
    """GET /v1/workspaces?include_archived=true includes archived-only UIDs."""
    core = RecollectiumCore(db_path=tmp_path / "ws.db")
    core.add_memory(
        space="workspace", type="fact", content="a", workspace_uid="active-ws"
    )
    core.add_memory(
        space="workspace", type="fact", content="b", workspace_uid="archived-ws"
    )
    # Archive the second memory
    memories = core.list_memories(space="workspace", workspace_uid="archived-ws")
    core.archive_memory(memories[0].id)

    client = _client(core)
    status, payload = _request_json(
        client, "GET", "/v1/workspaces?include_archived=true"
    )
    assert status == 200
    assert "archived-ws" in payload["data"]


def test_rename_workspace_success(tmp_path: Path) -> None:
    """POST /v1/workspaces/{uid}/rename migrates memories."""
    core = RecollectiumCore(db_path=tmp_path / "ws.db")
    core.add_memory(space="workspace", type="fact", content="a", workspace_uid="old-ws")

    client = _client(core)
    status, payload = _request_json(
        client,
        "POST",
        "/v1/workspaces/old-ws/rename",
        body={"new_uid": "new-ws"},
    )
    assert status == 200
    assert payload["data"]["old_uid"] == "old-ws"
    assert payload["data"]["new_uid"] == "new-ws"
    assert payload["data"]["memories_updated"] == 1


def test_rename_workspace_not_found(tmp_path: Path) -> None:
    """POST /v1/workspaces/{uid}/rename returns 404 for nonexistent UID."""
    core = RecollectiumCore(db_path=tmp_path / "ws.db")
    client = _client(core)

    status, payload = _request_json(
        client,
        "POST",
        "/v1/workspaces/nonexistent/rename",
        body={"new_uid": "new-ws"},
    )
    assert status == 404
    assert payload["error"]["code"] == "not_found"


def test_rename_workspace_validation_error(tmp_path: Path) -> None:
    """POST /v1/workspaces/{uid}/rename returns 400 for empty new_uid."""
    core = RecollectiumCore(db_path=tmp_path / "ws.db")
    core.add_memory(space="workspace", type="fact", content="a", workspace_uid="ws")

    client = _client(core)
    status, payload = _request_json(
        client,
        "POST",
        "/v1/workspaces/ws/rename",
        body={"new_uid": "!!!"},
    )
    assert status == 400


def test_http_workspace_alias_routes_resolve_add_list_remove(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-aliases.db")
    core.add_memory(
        space="workspace", type="fact", content="a", workspace_uid="Canonical"
    )
    client = _client(core)

    status, added = _request_json(
        client,
        "POST",
        "/v1/workspaces/Canonical/aliases",
        {"alias_uid": "Legacy", "migrate_existing": False},
    )
    assert status == 200
    assert added["data"]["alias"]["alias_uid"] == "legacy"

    status, resolved = _request_json(client, "GET", "/v1/workspaces/resolve?uid=Legacy")
    assert status == 200
    assert resolved["data"]["canonical_uid"] == "canonical"
    assert resolved["data"]["resolved_by_alias"] is True

    status, aliases = _request_json(client, "GET", "/v1/workspaces/Canonical/aliases")
    assert status == 200
    assert aliases["data"][0]["alias_uid"] == "legacy"

    status, workspaces = _request_json(
        client, "GET", "/v1/workspaces?include_aliases=true"
    )
    assert status == 200
    assert workspaces["data"] == [{"workspace_uid": "canonical", "aliases": ["legacy"]}]

    status, removed = _request_json(client, "DELETE", "/v1/workspaces/aliases/Legacy")
    assert status == 200
    assert removed["data"]["alias_uid"] == "legacy"


def test_http_workspace_alias_conflict_returns_400(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "service-alias-conflict.db")
    core.add_memory(space="workspace", type="fact", content="a", workspace_uid="legacy")
    client = _client(core)

    status, payload = _request_json(
        client,
        "POST",
        "/v1/workspaces/canonical/aliases",
        {"alias_uid": "legacy"},
    )
    assert status == 400
    assert payload["error"]["code"] == "validation_error"
    assert "Use --migrate-existing" in payload["error"]["message"]


def test_run_service_raises_embedding_error_for_structured_cli_failures(
    monkeypatch,
) -> None:
    from recollectium.errors import EmbeddingGenerationError

    class FailingCore:
        def __init__(self, *, db_path=None, config_path=None, log_level=None):
            self.config = type(
                "FakeConfig",
                (),
                {"effective_config": {"logging": {"level": "info"}}},
            )()

        def _ensure_model_ready(self) -> None:
            raise Exception("model download failed")

    monkeypatch.setattr("recollectium.service.RecollectiumCore", FailingCore)

    with pytest.raises(EmbeddingGenerationError) as exc_info:
        run_service(
            host="127.0.0.1",
            port=8902,
            db_path="fail.db",
            cli_structured_errors=True,
        )

    assert "model readiness failed: model download failed" in str(exc_info.value)


# -- verbosity override tests ----------------------------------------------


def _request_verbosity(
    client: TestClient,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    query_verbosity: str | None = None,
    header_verbosity: str | None = None,
) -> tuple[int, dict[str, Any]]:
    """Make a request with optional verbosity query param and header."""
    if query_verbosity is not None:
        path = f"{path}?verbosity={query_verbosity}" if "?" not in path else f"{path}&verbosity={query_verbosity}"
    headers: dict[str, str] = {}
    if header_verbosity is not None:
        headers["X-Recollectium-Verbosity"] = header_verbosity
    response = client.request(method, path, json=body, headers=headers)
    return response.status_code, response.json()


class TestVerbosityOverride:
    """Grouped verbosity override tests for discoverability."""

    def test_invalid_verbosity_returns_validation_error(
        self, tmp_path: Path
    ) -> None:
        """Invalid verbosity values return validation_error JSON."""
        core = RecollectiumCore(db_path=tmp_path / "verbosity-invalid.db")
        client = _client(core)

        # Invalid query param
        status, payload = _request_verbosity(
            client, "GET", "/v1/memories", query_verbosity="invalid"
        )
        assert status == 400
        assert payload["error"]["code"] == "validation_error"
        assert "verbosity must be one of" in payload["error"]["message"]

        # Invalid header
        status, payload = _request_verbosity(
            client, "GET", "/v1/embedding/status", header_verbosity="WRONG"
        )
        assert status == 400
        assert payload["error"]["code"] == "validation_error"

        # Metadata endpoints accept and validate verbosity even though response shape is unchanged
        for path in ("/v1/health", "/v1/version"):
            status, payload = _request_verbosity(
                client, "GET", path, query_verbosity="invalid"
            )
            assert status == 400
            assert payload["error"]["code"] == "validation_error"

            status, payload = _request_verbosity(
                client, "GET", path, query_verbosity="verbose"
            )
            assert status == 200
            assert "data" in payload

    def test_compact_default_for_memory_endpoints(self, tmp_path: Path) -> None:
        """Without verbosity override, memory endpoints return compact payloads."""
        core = RecollectiumCore(db_path=tmp_path / "verbosity-default.db")
        core.add_memory(
            space="user", type="fact", content="Default verbosity test",
            metadata={"source": "test"}, confidence=0.95,
        )
        client = _client(core)

        # List memories defaults to compact
        status, payload = _request_verbosity(
            client, "GET", "/v1/memories"
        )
        assert status == 200
        mem = payload["data"][0]
        assert set(mem.keys()) == {"id", "content", "type", "space"}

        # Get single memory defaults to compact
        mem_id = mem["id"]
        status, payload = _request_verbosity(
            client, "GET", f"/v1/memories/{mem_id}"
        )
        assert status == 200
        assert set(payload["data"].keys()) == {"id", "content", "type", "space"}

        # Search defaults to compact
        status, payload = _request_verbosity(
            client, "POST", "/v1/memories/search_user",
            body={"query": "Default verbosity test"}
        )
        assert status == 200
        sr = payload["data"][0]
        assert set(sr.keys()) == {"id", "content", "match"}

    def test_verbose_query_param_produces_full_payload(self, tmp_path: Path) -> None:
        """Verbose query param returns full memory and search payloads."""
        core = RecollectiumCore(db_path=tmp_path / "verbosity-verbose.db")
        core.add_memory(
            space="user", type="fact", content="Full payload test",
            metadata={"source": "verbose-test"}, confidence=0.85,
        )
        client = _client(core)

        # List memories with verbose query
        status, payload = _request_verbosity(
            client, "GET", "/v1/memories", query_verbosity="verbose"
        )
        assert status == 200
        mem = payload["data"][0]
        assert "metadata" in mem
        assert mem["metadata"] == {"source": "verbose-test"}
        assert "confidence" in mem
        assert mem["content"] == "Full payload test"

        # Get single memory verbose
        mem_id = mem["id"]
        status, payload = _request_verbosity(
            client, "GET", f"/v1/memories/{mem_id}", query_verbosity="verbose"
        )
        assert status == 200
        assert "confidence" in payload["data"]
        assert payload["data"]["confidence"] == 0.85

        # Search verbose
        status, payload = _request_verbosity(
            client, "POST", "/v1/memories/search_user",
            body={"query": "Full payload test"}, query_verbosity="verbose"
        )
        assert status == 200
        sr = payload["data"][0]
        assert "memory" in sr
        assert sr["memory"]["content"] == "Full payload test"
        assert "rank" in sr

    def test_header_verbosity_override(self, tmp_path: Path) -> None:
        """Header X-Recollectium-Verbosity overrides config default."""
        core = RecollectiumCore(db_path=tmp_path / "verbosity-header.db")
        core.add_memory(
            space="user", type="fact", content="Header override test"
        )
        client = _client(core)

        # Header verbose
        status, payload = _request_verbosity(
            client, "GET", "/v1/memories", header_verbosity="verbose"
        )
        assert status == 200
        mem = payload["data"][0]
        assert "metadata" in mem
        assert "confidence" in mem

        # Header compact
        status, payload = _request_verbosity(
            client, "GET", "/v1/memories", header_verbosity="compact"
        )
        assert status == 200
        mem = payload["data"][0]
        assert set(mem.keys()) == {"id", "content", "type", "space"}

    def test_query_overrides_header(self, tmp_path: Path) -> None:
        """Query verbosity takes precedence over header."""
        core = RecollectiumCore(db_path=tmp_path / "verbosity-precedence.db")
        core.add_memory(
            space="user", type="fact", content="Precedence test",
            metadata={"key": "val"},
        )
        client = _client(core)

        # Query says verbose, header says compact → verbose wins
        status, payload = _request_verbosity(
            client, "GET", "/v1/memories",
            query_verbosity="verbose", header_verbosity="compact"
        )
        assert status == 200
        mem = payload["data"][0]
        assert "metadata" in mem

        # Query says compact, header says verbose → compact wins
        status, payload = _request_verbosity(
            client, "GET", "/v1/memories",
            query_verbosity="compact", header_verbosity="verbose"
        )
        assert status == 200
        mem = payload["data"][0]
        assert set(mem.keys()) == {"id", "content", "type", "space"}

    def test_embedding_status_compact_and_verbose(self, tmp_path: Path) -> None:
        """Embedding status endpoint respects verbosity."""
        core = RecollectiumCore(db_path=tmp_path / "verbosity-emb-status.db")
        client = _client(core)

        # Default compact
        status, payload = _request_verbosity(
            client, "GET", "/v1/embedding/status"
        )
        assert status == 200
        data = payload["data"]
        assert set(data.keys()) == {
            "provider_status", "embedding_profile",
            "model_status", "embedding_jobs_status_path",
        }

        # Verbose
        status, payload = _request_verbosity(
            client, "GET", "/v1/embedding/status", query_verbosity="verbose"
        )
        assert status == 200
        data = payload["data"]
        assert "runtime" in data
        assert "provider_status" in data

    def test_workspace_endpoints_with_verbosity(self, tmp_path: Path) -> None:
        """Workspace endpoints accept verbosity override."""
        core = RecollectiumCore(db_path=tmp_path / "verbosity-ws.db")
        core.add_memory(
            space="workspace", type="fact", content="ws-test",
            workspace_uid="project-z"
        )
        client = _client(core)

        # List workspaces - compact (default)
        status, payload = _request_verbosity(
            client, "GET", "/v1/workspaces"
        )
        assert status == 200
        assert payload["data"] == ["project-z"]

        # List workspaces - verbose
        status, payload = _request_verbosity(
            client, "GET", "/v1/workspaces", query_verbosity="verbose"
        )
        assert status == 200
        assert payload["data"] == ["project-z"]

        # Resolve workspace - verbose
        status, payload = _request_verbosity(
            client, "GET", "/v1/workspaces/resolve?uid=project-z",
            query_verbosity="verbose"
        )
        assert status == 200
        assert payload["data"]["canonical_uid"] == "project-z"

    def test_capabilities_verbose_includes_verbosity_metadata(
        self, tmp_path: Path
    ) -> None:
        """Capabilities endpoint in verbose mode includes response_verbosity."""
        core = RecollectiumCore(db_path=tmp_path / "verbosity-caps.db")
        client = _client(core)

        # Default (compact) does not include verbosity metadata
        status, payload = _request_verbosity(
            client, "GET", "/v1/capabilities"
        )
        assert status == 200
        assert "response_verbosity" not in payload["data"]

        # Verbose includes the metadata
        status, payload = _request_verbosity(
            client, "GET", "/v1/capabilities", query_verbosity="verbose"
        )
        assert status == 200
        assert payload["data"]["response_verbosity"] == "verbose"

    def test_add_memory_compact_mutation_projection(self, tmp_path: Path) -> None:
        """Add memory returns compact mutation shape by default."""
        core = RecollectiumCore(db_path=tmp_path / "verbosity-add.db")
        client = _client(core)

        # Default compact mutation
        status, payload = _request_verbosity(
            client, "POST", "/v1/memories",
            body={"space": "user", "type": "fact", "content": "Mutation test"}
        )
        assert status == 200
        data = payload["data"]
        assert set(data.keys()) == {"id", "status"}
        assert data["status"] == "saved"

        # Verbose mutation
        status, payload = _request_verbosity(
            client, "POST", "/v1/memories",
            body={"space": "user", "type": "fact", "content": "Mutation verbose"},
            query_verbosity="verbose"
        )
        assert status == 200
        data = payload["data"]
        assert data["content"] == "Mutation verbose"
        assert "metadata" in data

    def test_archive_memory_compact_projection(self, tmp_path: Path) -> None:
        """Archive memory returns compact mutation shape by default."""
        core = RecollectiumCore(db_path=tmp_path / "verbosity-archive.db")
        mem = core.add_memory(
            space="user", type="fact", content="Archive me"
        )
        client = _client(core)

        status, payload = _request_verbosity(
            client, "POST", f"/v1/memories/{mem.id}/archive"
        )
        assert status == 200
        data = payload["data"]
        assert set(data.keys()) == {"id", "status"}
        assert data["status"] == "archived"
