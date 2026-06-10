# Recollectium Core Local Service API

This document describes the currently implemented FastAPI local HTTP JSON service in `src/recollectium/service.py`.

## Local access and security assumptions

See [`../SECURITY.md`](../SECURITY.md) for the full v1 security model.

- This service is local-first and intended for single-machine use.
- Default bind is `127.0.0.1` on port `8765`.
- API and MCP services are unauthenticated in v1 and are not public internet APIs.
- The SQLite memory database is not encrypted by Recollectium.
- If you bind a service to a non-local interface, memory contents and memory-changing operations may be exposed to anyone who can reach that interface.
- Any user, process, or network client with sufficient access to the Recollectium data directory, database file, or unauthenticated service endpoint can read, modify, or delete memories. Because memories influence what agents recall, unauthorized memory changes can also influence agent behavior.
- If an agent must connect from another machine, use private networking with external access controls. For most users, Tailscale is the recommended split-machine path; WireGuard, SSH tunneling, firewall allowlists, or equivalent VPN/overlay networking can also work.

For the managed service path used by adapters, start the API service with:

```bash
recollectium service start api
```

For foreground development or debugging, run the same API server directly:

```bash
recollectium serve
```

Or run the foreground server with explicit host/port/database path:

```bash
recollectium --db /path/to/recollectium.db serve --host 127.0.0.1 --port 8765
```

## Base URL and versioning

- Default base URL: `http://127.0.0.1:8765`
- API prefix: `/v1`
- Service API version value: `1`

## Adapter discovery workflow

Adapters and plugins should discover the local service with:

```bash
recollectium service discover
```

The command exits `0` when a managed service is running, exits `1` when no service is running, and exits `2` when config or discovery metadata is invalid. It prints human-readable output on stdout by default and does not create a config file just to inspect discovery state. Use `recollectium service discover --json` in adapters and scripts.

Running response shape:

```json
{
  "status": "running",
  "service": {
    "type": "api",
    "pid": 12345,
    "process_start_time": 123456789,
    "endpoint": "http://127.0.0.1:8765",
    "api_prefix": "/v1",
    "health_url": "http://127.0.0.1:8765/v1/health",
    "version_url": "http://127.0.0.1:8765/v1/version",
    "capabilities_url": "http://127.0.0.1:8765/v1/capabilities"
  },
  "versions": {
    "service_api_version": "1",
    "recollectium_version": "1.0.0"
  },
  "paths": {
    "config": "/home/user/.config/recollectium/config.json",
    "runtime_dir": "/run/user/1000/recollectium",
    "pid_file": "/run/user/1000/recollectium/service.pid",
    "discovery_file": "/run/user/1000/recollectium/service-discovery.json"
  }
}
```

Not-running response shape:

```json
{
  "status": "not_running",
  "service": null,
  "versions": {
    "service_api_version": "1",
    "recollectium_version": "1.0.0"
  },
  "paths": {
    "config": "/home/user/.config/recollectium/config.json",
    "runtime_dir": "/run/user/1000/recollectium",
    "pid_file": "/run/user/1000/recollectium/service.pid",
    "discovery_file": "/run/user/1000/recollectium/service-discovery.json"
  },
  "next_step": "Run `recollectium service start api` to start the local API service."
}
```

`recollectium service start api` and `recollectium service start mcp` write the running response to `{runtime_dir}/service-discovery.json` after process ownership is verified. `recollectium service stop`, `recollectium service status`, and `recollectium service discover` remove stale Recollectium-owned PID and discovery files when they prove the managed process is gone.

Adapters should validate the target service before enabling Recollectium-backed tools. This validation confirms compatibility, not authentication or authorization:

1. For local discovery, use the returned `health_url`, `version_url`, and
   `capabilities_url`. For remote Core config, derive `/v1/health`,
   `/v1/version`, and `/v1/capabilities` from the configured base URL.
2. Call the health endpoint and require an ok response.
3. Call the version endpoint and verify compatible `service_api_version`.
4. Call the capabilities endpoint and verify every required capability is
   present.

Adapters should autodiscover Recollectium after the host application loads the
plugin when the adapter and Core run on the same machine. Users should not need
to manually configure host, port, PID file, runtime path, or service type for
that local path. If local autodiscovery reports `not_running`, the plugin should
attempt `recollectium service start api` and then rerun discovery before guiding
the user. Private-network split-machine Core instances are different: the user points the
plugin at the Core base URL in plugin config, and the adapter validates that
configured endpoint by calling `/v1/health`, `/v1/version`, and
`/v1/capabilities`. Host-level plugin registration remains outside Recollectium
Core. See `docs/opencode-adapter-contract.md` for the adapter contract and
workspace UID rules.

The v1.0.0 API is local-first and unauthenticated. Binding to a non-local interface can expose memory contents and memory-changing operations. Remote or split-machine access should use private networking with external access controls; see [`../SECURITY.md`](../SECURITY.md).

## Envelope shapes

Successful responses use:

```json
{
  "data": {}
}
```

Error responses use:

```json
{
  "error": {
    "code": "validation_error",
    "message": "workspace_uid is required for workspace search",
    "details": {}
  }
}
```

`details` is currently always an object and defaults to `{}`.

## Response verbosity

All implemented API endpoints accept an optional `verbosity` query parameter or `X-Recollectium-Verbosity` header. Supported values are `compact` and `verbose`.

The same response projection is used by the CLI and MCP surfaces. CLI callers use `--compact` or `--verbose`; MCP callers pass the optional `verbosity` tool argument. The config key for the default is `response_verbosity`.

Precedence is:

1. `?verbosity=...` query parameter
2. `X-Recollectium-Verbosity` header
3. configured `response_verbosity`
4. built-in default `compact`

`compact` is the default response shape. It is optimized for adapters and common UI use. `verbose` returns the full stored objects and operational details. Empty or unknown verbosity values are invalid and return `validation_error`. If the query parameter is present, it wins over the header even when invalid.

Compact projections by operation:

- Memory list and get: `{id, content, type, space}` plus `workspace_uid` when present.
- Memory search: `{id, content, match}` where `match` is the search score.
- Memory add, update, and archive: `{id, status}` with status values `saved`, `updated`, or `archived`.
- Embedding status: `provider_status`, `embedding_profile`, `model_status`, `model_cache_path`, and `embedding_jobs_status_path`.
- Embedding job list and get: `id`, `state`, `reason`, `total_count`, `succeeded_count`, and `failed_count` when present.
- Embedding refresh: `refreshed`, `stale_count`, `status_path`, and `job_id` when a job exists.
- Embedding job clear: `deleted_count` and `states`.
- Workspace list: UID strings when `include_aliases=false`; when `include_aliases=true`, `{workspace_uid, aliases, alias_count}` where `aliases` contains alias UID strings.
- Workspace resolve: `{canonical_uid, resolved_by_alias}` plus `input_uid` and `normalized_uid` only when alias resolution or UID normalization changed the input.
- Workspace alias list: `{alias_uid, canonical_uid}`.
- Workspace alias add: `{canonical_uid, alias_uid, status, migrated_memories}` with `status` set to `added`.
- Workspace alias remove: `{alias_uid, canonical_uid, status}` with `status` set to `removed`.
- Workspace rename: `{old_uid, new_uid, memories_updated, aliases_updated, status}` with `status` set to `renamed`.

Health and version responses have the same shape for compact and verbose. Capabilities are already mostly compact; verbose adds response verbosity metadata.

Request verbose data with a query parameter:

```bash
curl -sS 'http://127.0.0.1:8765/v1/memories?verbosity=verbose'
```

Or with a header:

```bash
curl -sS http://127.0.0.1:8765/v1/memories \
  -H 'X-Recollectium-Verbosity: verbose'
```

## Version and capability discovery

### `GET /v1/health`

Purpose: service liveness check.

Optional response controls: `verbosity` query parameter or `X-Recollectium-Verbosity` header (`compact` or `verbose`). The response shape is unchanged.

Response example:

```json
{
  "data": {
    "status": "ok"
  }
}
```

### `GET /v1/version`

Purpose: report service API and package version.

Optional response controls: `verbosity` query parameter or `X-Recollectium-Verbosity` header (`compact` or `verbose`). The response shape is unchanged.

Response example:

```json
{
  "data": {
    "service_api_version": "1",
    "recollectium_version": "1.0.0"
  }
}
```

### `GET /v1/capabilities`

Purpose: list implemented operation capabilities.

Optional response controls: `verbosity` query parameter or `X-Recollectium-Verbosity` header (`compact` or `verbose`). Verbose responses include response verbosity metadata.

Response example:

```json
{
  "data": {
    "service_api_version": "1",
    "capabilities": [
      "health.read",
      "version.read",
      "capabilities.read",
      "memories.search_user",
      "memories.search_workspace",
      "memories.add",
      "memories.update",
      "memories.archive",
      "memories.list",
      "memories.get",
      "embedding.status",
      "embedding.jobs.list",
      "embedding.jobs.get",
      "embedding.refresh",
      "embedding.jobs.clear",
      "workspaces.list",
      "workspaces.rename",
      "workspaces.resolve",
      "workspaces.aliases.list",
      "workspaces.aliases.add",
      "workspaces.aliases.remove"
    ],
    "memory_types": {
      "user": [
        "fact",
        "preference",
        "personal_fact",
        "social_context",
        "goal",
        "communication_style",
        "note"
      ],
      "workspace": [
        "fact",
        "decision",
        "task_context",
        "configuration",
        "bug_finding",
        "note"
      ],
      "all": [
        "fact",
        "preference",
        "personal_fact",
        "social_context",
        "goal",
        "communication_style",
        "note",
        "decision",
        "task_context",
        "configuration",
        "bug_finding"
      ]
    }
  }
}
```

## Workspace UID requirements

- Workspace search requires `workspace_uid`.
- Adding workspace memories requires `space="workspace"` and `workspace_uid`.
- Adding user memories requires `space="user"` and must not include `workspace_uid`.
- Workspace filters on list are optional.

Violations return `validation_error`.

## Endpoints

All request bodies below are JSON objects.
All successful endpoint responses currently return HTTP `200` with a `{"data": ...}` payload.

### 1) Search user memories

- Method and path: `POST /v1/memories/search_user`
- Purpose: semantic search in user-space memories only.
- Required inputs:
  - `query` (string, non-empty)
- Optional inputs:
  - `type` (string bucket filter; optional)
  - `limit` (positive integer, default `10`)
  - `include_archived` (boolean, default `false`)
- Side effects: none.
- Successful response: HTTP `200` with compact `data` list of search results (`id`, `content`, `match`) by default. Use `?verbosity=verbose` or the verbosity header for full search result objects (`memory`, `score`, `rank`, `matched_text`, `snippet`, `chunk_index`).

Example request: compact default

```bash
curl -sS http://127.0.0.1:8765/v1/memories/search_user \
  -H 'Content-Type: application/json' \
  -d '{"query":"likes tea","type":"fact","limit":5}'
```

Example response: compact default

```json
{
  "data": [
    {"id": "8f6d...", "content": "Alfonso likes tea", "match": 0.91}
  ]
}
```

Example request: verbose

```bash
curl -sS 'http://127.0.0.1:8765/v1/memories/search_user?verbosity=verbose' \
  -H 'Content-Type: application/json' \
  -d '{"query":"likes tea","type":"fact","limit":5}'
```

Verbose response includes full search result fields:

```json
{
  "data": [
    {
      "memory": {
        "id": "8f6d...",
        "space": "user",
        "workspace_uid": null,
        "type": "fact",
        "content": "Alfonso likes tea",
        "metadata": {},
        "status": "active",
        "source": null,
        "confidence": null,
        "sensitivity": null,
        "created_at": "2026-05-18T12:34:56+00:00",
        "updated_at": "2026-05-18T12:34:56+00:00",
        "last_accessed_at": null
      },
      "score": 0.91,
      "rank": 1,
      "matched_text": "Alfonso likes tea",
      "snippet": "Alfonso likes tea",
      "chunk_index": 0
    }
  ]
}
```

### 2) Search workspace memories

- Method and path: `POST /v1/memories/search_workspace`
- Purpose: semantic search in one workspace UID only.
- Required inputs:
  - `query` (string, non-empty)
  - `workspace_uid` (string, non-empty)
- Optional inputs:
  - `type` (string bucket filter; optional)
  - `limit` (positive integer, default `10`)
  - `include_archived` (boolean, default `false`)
- Side effects: none.
- Successful response: HTTP `200` with compact `data` list of search results (`id`, `content`, `match`) by default. Use `?verbosity=verbose` or the verbosity header for full search result objects.

Example request: compact default

```bash
curl -sS http://127.0.0.1:8765/v1/memories/search_workspace \
  -H 'Content-Type: application/json' \
  -d '{"query":"sqlite","workspace_uid":"ws-1","type":"decision"}'
```

Example response: compact default

```json
{
  "data": [
    {"id": "d22a...", "content": "Use sqlite for local db", "match": 0.88}
  ]
}
```

Verbose requests use `POST /v1/memories/search_workspace?verbosity=verbose` or `X-Recollectium-Verbosity: verbose` and return the same full search result shape shown in the user search verbose example.

### 3) Add memory

- Method and path: `POST /v1/memories`
- Purpose: create one memory.
- Required inputs:
  - `space` (`"user"` or `"workspace"`)
  - `type` (string, non-empty)
  - `content` (string, non-empty)
- Conditionally required:
  - `workspace_uid` required when `space="workspace"`
  - `workspace_uid` forbidden when `space="user"`
- Optional inputs:
  - `metadata` (JSON object, default `{}`)
  - `source` (string)
  - `confidence` (number in range `0` to `1`)
  - `sensitivity` (string)
- Side effects:
  - Inserts memory into SQLite store.
  - Generates and stores embedding for `content`.
- Successful response: HTTP `200` with compact mutation data (`id`, `status`) by default, where `status` is `saved`. Use `?verbosity=verbose` or the verbosity header for the created memory object.

Example request: compact default

```bash
curl -sS http://127.0.0.1:8765/v1/memories \
  -H 'Content-Type: application/json' \
  -d '{"space":"workspace","type":"decision","content":"Use sqlite","workspace_uid":"ws-1"}'
```

Example response: compact default

```json
{
  "data": {"id": "d22a...", "status": "saved"}
}
```

Example request: verbose

```bash
curl -sS 'http://127.0.0.1:8765/v1/memories?verbosity=verbose' \
  -H 'Content-Type: application/json' \
  -d '{"space":"workspace","type":"decision","content":"Use sqlite","workspace_uid":"ws-1"}'
```

Verbose response contains the full created memory object.

### 4) Update memory

- Method and path: `PATCH /v1/memories/{memory_id}`
- Purpose: update one existing memory.
- Path params:
  - `memory_id` (string)
- Optional inputs (at least one required):
  - `type` (string)
  - `content` (string)
  - `metadata` (JSON object)
  - `source` (string)
  - `confidence` (number in range `0` to `1`)
  - `sensitivity` (string)
- Side effects:
  - Updates memory fields.
  - If `content` changes, embedding is regenerated.
- Successful response: HTTP `200` with compact mutation data (`id`, `status`) by default, where `status` is `updated`. Use `?verbosity=verbose` or the verbosity header for the updated memory object.

Example request: compact default

```bash
curl -sS -X PATCH http://127.0.0.1:8765/v1/memories/8f6d... \
  -H 'Content-Type: application/json' \
  -d '{"content":"Alfonso likes green tea"}'
```

Example response: compact default

```json
{
  "data": {"id": "8f6d...", "status": "updated"}
}
```

Example request: verbose `PATCH /v1/memories/8f6d...?verbosity=verbose`. Verbose response contains the full updated memory object.

### 5) Archive memory

- Method and path: `POST /v1/memories/{memory_id}/archive`
- Purpose: mark a memory archived.
- Path params:
  - `memory_id` (string)
- Side effects:
  - Sets memory status to archived.
  - Archived memories are excluded from default search and list results.
- Successful response: HTTP `200` with compact mutation data (`id`, `status`) by default, where `status` is `archived`. Use `?verbosity=verbose` or the verbosity header for the archived memory object.

Example request: compact default

```bash
curl -sS -X POST http://127.0.0.1:8765/v1/memories/8f6d.../archive
```

Example response: compact default

```json
{
  "data": {"id": "8f6d...", "status": "archived"}
}
```

Example request: verbose `POST /v1/memories/8f6d.../archive?verbosity=verbose`. Verbose response contains the full archived memory object.

### 6) List memories

- Method and path: `GET /v1/memories`
- Purpose: list memories with optional filters.
- Query params (all optional):
  - `space` (string)
  - `type` (string)
  - `status` (string)
  - `workspace_uid` (string)
  - `include_archived` (`true` or `false`, default `false`)
  - `limit` (positive integer)
- Side effects: none.
- Successful response: HTTP `200` with compact memory objects by default (`id`, `content`, `type`, `space`, and `workspace_uid` when present). Use `?verbosity=verbose` or the verbosity header for full memory objects.

Archived behavior:

- By default (`include_archived` omitted), archived memories are excluded.
- Set `include_archived=true` to include archived memories.

Example request: compact default

```bash
curl -sS 'http://127.0.0.1:8765/v1/memories?space=workspace&workspace_uid=ws-1&include_archived=true&limit=20'
```

Example response: compact default

```json
{
  "data": [
    {
      "id": "d22a...",
      "space": "workspace",
      "workspace_uid": "ws-1",
      "type": "decision",
      "content": "Use sqlite"
    }
  ]
}
```

Example request: verbose `GET /v1/memories?space=workspace&workspace_uid=ws-1&verbosity=verbose`. Verbose response contains full memory objects.

### 7) Get memory by ID

- Method and path: `GET /v1/memories/{memory_id}`
- Purpose: fetch one memory by ID.
- Path params:
  - `memory_id` (string)
- Side effects:
  - Updates `last_accessed_at` when possible.
- Successful response: HTTP `200` with a compact memory object by default (`id`, `content`, `type`, `space`, and `workspace_uid` when present). Use `?verbosity=verbose` or the verbosity header for the full memory object.

Example request: compact default

```bash
curl -sS http://127.0.0.1:8765/v1/memories/8f6d...
```

Example response: compact default

```json
{
  "data": {
    "id": "8f6d...",
    "space": "user",
    "type": "fact",
    "content": "Alfonso likes tea"
  }
}
```

Example request: verbose `GET /v1/memories/8f6d...?verbosity=verbose`. Verbose response contains the full memory object including metadata, timestamps, and status.

## Memory object shape

Verbose memory responses use this JSON object shape:

```json
{
  "id": "string",
  "space": "user|workspace",
  "workspace_uid": "string|null",
  "type": "string",
  "content": "string",
  "metadata": {},
  "status": "active|archived",
  "source": "string|null",
  "confidence": 0.0,
  "sensitivity": "string|null",
  "created_at": "ISO-8601 string",
  "updated_at": "ISO-8601 string",
  "last_accessed_at": "ISO-8601 string|null"
}
```

Verbose search responses return a list of search-result objects. The inner `memory` field holds the full memory object. Compact search responses return only `id`, `content`, and `match`.

### 8) Embedding status

Supported built-in FastEmbed profiles:

| Model | Role | Profile | Dimensions | Max tokens | Chunk tokens | Overlap tokens |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `BAAI/bge-base-en-v1.5` | default | `builtin-fastembed-bge-base-en-v1-5-v1` | 768 | 512 | 384 | 64 |
| `jinaai/jina-embeddings-v2-small-en` | legacy supported | `builtin-fastembed-jina-v2-small-en-v1` | 512 | 8192 | 6144 | 512 |

Switching embedding model or profile can require existing memories to be refreshed through the readiness and re-embedding job path. Refresh jobs run inline in the command, API request, or MCP tool call that triggers them, so callers get a completed or failed job result before the operation returns.

- Method and path: `GET /v1/embedding/status`
- Purpose: return the active local embedding profile, built-in FastEmbed model cache path when Recollectium manages it, runtime posture, startup re-embedding job reference, status paths, and recent embedding jobs.
- Side effects: none.
- Successful response: HTTP `200` with compact embedding status by default. Use `?verbosity=verbose` or the verbosity header for runtime details, startup job fields, and recent jobs. Custom or injected embedding providers report `model_status: "managed_externally"` and do not include a Recollectium model cache path or FastEmbed runtime.

Example request: compact default

```bash
curl -sS http://127.0.0.1:8765/v1/embedding/status
```

Example response: compact default

```json
{
  "data": {
    "embedding_profile": {
      "provider": "builtin-fastembed",
      "model": "BAAI/bge-base-en-v1.5",
      "dimensions": 768,
      "version": "1",
      "profile": "builtin-fastembed-bge-base-en-v1-5-v1",
      "max_tokens": 512,
      "chunk_tokens": 384,
      "chunk_overlap_tokens": 64,
      "query_prompt_policy": "raw"
    },
    "provider_status": "configured",
    "model_status": "managed_by_recollectium_cache",
    "model_cache_path": "/home/alice/.cache/recollectium/models",
    "embedding_jobs_status_path": "/v1/embedding/jobs"
  }
}
```

Example request: verbose

```bash
curl -sS 'http://127.0.0.1:8765/v1/embedding/status?verbosity=verbose'
```

Verbose response includes runtime fields, startup re-embedding paths, the same model cache path for the built-in provider, and recent embedding jobs. The built-in FastEmbed cache at `${directories.cache}/models` is Recollectium-owned derived data and can be removed by plain uninstall even when `directories.cache` is customized.

### 9) List embedding jobs

- Method and path: `GET /v1/embedding/jobs`
- Purpose: list embedding jobs for model readiness or stale-profile re-embedding.
- Optional query params:
  - `state` (string, commonly `pending`, `in_progress`, `completed`, or `failed`)
  - `limit` (positive integer)
- Side effects: none.
- Successful response: HTTP `200` with a compact `data` list ordered by most recent first. Use `?verbosity=verbose` or the verbosity header for full job objects.

Example request: verbose

```bash
curl -sS "http://127.0.0.1:8765/v1/embedding/jobs?state=failed&limit=5&verbosity=verbose"
```

Example response: verbose

```json
{
  "data": [
    {
      "id": "job-123",
      "state": "failed",
      "total_count": 3,
      "processed_count": 1,
      "succeeded_count": 0,
      "failed_count": 1,
      "provider": "builtin-fastembed",
      "model": "BAAI/bge-base-en-v1.5",
      "embedding_profile": {
        "provider": "builtin-fastembed",
        "model": "BAAI/bge-base-en-v1.5",
        "dimensions": 768,
        "version": "1",
        "profile": "builtin-fastembed-bge-base-en-v1-5-v1",
        "max_tokens": 512,
        "chunk_tokens": 384,
        "chunk_overlap_tokens": 64,
        "query_prompt_policy": "raw"
      },
      "error_message": "runtime re-embedding failed",
      "created_at": "2026-05-19T10:09:55+00:00",
      "updated_at": "2026-05-19T10:10:05+00:00",
      "started_at": "2026-05-19T10:10:00+00:00",
      "completed_at": "2026-05-19T10:10:05+00:00"
    }
  ]
}
```

### 10) Force embedding refresh

- Method and path: `POST /v1/embedding/refresh`
- Purpose: force stale memories to be re-embedded for the active profile. The request processes the job inline and returns after the job completes or fails.
- Side effects: may create an embedding job and update memory embedding fields and chunks. It does not change memory content.
- Request body: optional JSON object. Omit the body, or send `{}`, to refresh all stale embeddings.
- Optional request fields:
  - `space` (`user` or `workspace`)
  - `workspace_uid` (string, implies workspace scope)
  - `include_archived` (boolean, default `false`)
- Successful response: HTTP `200` with compact refresh status by default. Use `?verbosity=verbose` or the verbosity header for the full completed job object.

Example request: verbose

```bash
curl -sS -X POST 'http://127.0.0.1:8765/v1/embedding/refresh?verbosity=verbose' \
  -H 'Content-Type: application/json' \
  -d '{"space":"workspace","workspace_uid":"recollectium"}'
```

Example response: verbose

```json
{
  "data": {
    "refreshed": true,
    "stale_count": 12,
    "job": {
      "id": "job-123",
      "state": "completed",
      "total_count": 12,
      "processed_count": 12,
      "succeeded_count": 12,
      "failed_count": 0,
      "provider": "builtin-fastembed",
      "model": "BAAI/bge-base-en-v1.5",
      "embedding_profile": {
        "provider": "builtin-fastembed",
        "model": "BAAI/bge-base-en-v1.5",
        "dimensions": 768,
        "version": "1",
        "profile": "builtin-fastembed-bge-base-en-v1-5-v1",
        "max_tokens": 512,
        "chunk_tokens": 384,
        "chunk_overlap_tokens": 64,
        "query_prompt_policy": "raw"
      },
      "error_message": null,
      "created_at": "2026-05-19T10:09:55+00:00",
      "updated_at": "2026-05-19T10:10:05+00:00",
      "started_at": "2026-05-19T10:10:00+00:00",
      "completed_at": "2026-05-19T10:10:05+00:00"
    },
    "status_path": "/v1/embedding/jobs/job-123"
  }
}
```

Compact default response omits the nested job object and returns `job_id` when a job exists:

```json
{
  "data": {
    "refreshed": true,
    "stale_count": 12,
    "status_path": "/v1/embedding/jobs/job-123",
    "job_id": "job-123"
  }
}
```

If no stale memories match the request, `refreshed` is `false`, `stale_count` is `0`, and no `job_id` is returned.

### 11) Clear embedding job records

- Method and path: `DELETE /v1/embedding/jobs`
- Purpose: delete embedding job audit records without deleting memories or embeddings.
- Side effects: removes matching rows from the embedding job history.
- Optional request fields:
  - `states` (array of states to delete). If omitted, Recollectium deletes `completed`, `failed`, and `pending` job records.
- Successful response: HTTP `200` with deleted count and selected states. This shape is the same for compact and verbose.

Example request:

```bash
curl -sS -X DELETE http://127.0.0.1:8765/v1/embedding/jobs \
  -H 'Content-Type: application/json' \
  -d '{"states":["completed","failed","pending"]}'
```

Example response:

```json
{
  "data": {
    "deleted_count": 3,
    "states": ["completed", "failed", "pending"]
  }
}
```

### 12) Get embedding job

- Method and path: `GET /v1/embedding/jobs/{job_id}`
- Purpose: fetch one embedding job by ID.
- Job states: inline refresh work may appear as `in_progress` while memories are being refreshed, `completed` when all stale memories succeeded, or `failed` when one or more memories could not be re-embedded. Historical `pending` records may also exist before they are cleared.
- Path params:
  - `job_id` (string)
- Side effects: none.
- Successful response: HTTP `200` with one compact job object in `data` by default. Use `?verbosity=verbose` or the verbosity header for the full job object.

Example request: verbose `GET /v1/embedding/jobs/job-123?verbosity=verbose`.

Example response: verbose

```json
{
  "data": {
    "id": "job-123",
    "state": "in_progress",
    "total_count": 12,
    "processed_count": 4,
    "succeeded_count": 4,
    "failed_count": 0,
    "provider": "builtin-fastembed",
    "model": "BAAI/bge-base-en-v1.5",
    "embedding_profile": {
      "provider": "builtin-fastembed",
      "model": "BAAI/bge-base-en-v1.5",
      "dimensions": 768,
      "version": "1",
      "profile": "builtin-fastembed-bge-base-en-v1-5-v1",
      "max_tokens": 512,
      "chunk_tokens": 384,
      "chunk_overlap_tokens": 64,
      "query_prompt_policy": "raw"
    },
    "error_message": "triggered by search",
    "created_at": "2026-05-19T10:09:55+00:00",
    "updated_at": "2026-05-19T10:10:00+00:00",
    "started_at": "2026-05-19T10:10:00+00:00",
    "completed_at": null
  }
}
```

## Error codes and common failures

Implemented error codes:

- `validation_error` (`400`)
  - Examples: missing required fields, invalid `space`, bad `limit`, missing `workspace_uid` for workspace search, empty JSON body.
- `not_found` (`404`)
  - Example: `GET /v1/memories/{memory_id}` for missing ID.
- `unsupported_operation` (`404`)
  - Example: unknown path or unsupported method on a known path.
- `invalid_json` (`400`)
  - Example: malformed JSON request body.
- `embedding_provider_unavailable` (`503`)
  - Example: built-in provider runtime could not initialize.
- `embedding_model_unavailable` (`503`)
  - Example: FastEmbed model cache missing or load failed.
- `embedding_generation_failed` (`500`)
  - Example: provider failed during embedding generation.
- `embedding_profile_mismatch` (`500`)
  - Example: returned embedding dimension does not match active profile.
- `embedding_readiness_timeout` (`503`)
  - Example: provider readiness check exceeded timeout.
- `reembedding_in_progress` (`409`)
  - Includes `details.job_id` and `details.status_path`.
- `reembedding_failed` (`503`)
  - Includes `details.job_id` and `details.status_path`.
- `internal_error` (`500`)
  - Unexpected server-side exception at request boundary.

Common failure examples:

Invalid JSON:

```json
{
  "error": {
    "code": "invalid_json",
    "message": "invalid JSON: Expecting property name enclosed in double quotes",
    "details": {}
  }
}
```

Missing workspace UID for workspace search:

```json
{
  "error": {
    "code": "validation_error",
    "message": "workspace_uid is required for workspace search",
    "details": {}
  }
}
```

Unsupported route/method:

```json
{
  "error": {
    "code": "unsupported_operation",
    "message": "unsupported operation",
    "details": {}
  }
}
```

## Workspace operations

### `GET /v1/workspaces`

Purpose: list distinct workspace UIDs visible through the API. With `include_aliases=true`, return workspace objects with alias UID arrays in compact mode.

**Query parameters**

| Param | Type | Default | Description |
|---|---|---|---|
| `include_archived` | bool | `false` | Include UIDs that appear only on archived memories. |
| `include_aliases` | bool | `false` | Return objects shaped as `{workspace_uid, aliases, alias_count}` instead of UID strings in compact mode. Verbose mode includes full alias records. |

Compact is the default. Use `?verbosity=verbose` or the verbosity header with `include_aliases=true` for full alias records with timestamps.

**Response 200**

```json
{
  "data": ["generalist-ai", "recollectium"]
}
```

**Response 200 with aliases, compact default**

```json
{
  "data": [
    {"workspace_uid": "recollectium", "aliases": ["recollectium-core"], "alias_count": 1},
    {"workspace_uid": "generalist-ai", "aliases": [], "alias_count": 0}
  ]
}
```

### `GET /v1/workspaces/resolve`

Purpose: normalize a workspace UID candidate and resolve it to the canonical UID if it is an alias.

Compact is the default and returns `{canonical_uid, resolved_by_alias}`. It also includes `input_uid` and `normalized_uid` when alias resolution happened or normalization changed the input. Verbose mode returns the full resolution payload.

Example request:

```bash
curl -sS 'http://127.0.0.1:8765/v1/workspaces/resolve?uid=Recollectium%20Core'
```

Example response: compact default

```json
{
  "data": {
    "canonical_uid": "recollectium",
    "resolved_by_alias": true,
    "input_uid": "Recollectium Core",
    "normalized_uid": "recollectium-core"
  }
}
```

### `GET /v1/workspaces/{uid}/aliases`

Purpose: list aliases for a canonical workspace UID. The `uid` path value is normalized and resolved before filtering.

Compact is the default and returns each alias as `{alias_uid, canonical_uid}`. Use `?verbosity=verbose` or the verbosity header for timestamps.

Example request:

```bash
curl -sS http://127.0.0.1:8765/v1/workspaces/recollectium/aliases
```

Example response: compact default

```json
{
  "data": [
    {
      "alias_uid": "recollectium-core",
      "canonical_uid": "recollectium"
    }
  ]
}
```

### `POST /v1/workspaces/{uid}/aliases`

Purpose: add an alias for a canonical workspace UID. Use `migrate_existing=true` to move existing alias-owned memories into the canonical workspace in the same transaction.

Compact is the default and returns `{canonical_uid, alias_uid, status, migrated_memories}` with `status: "added"`. Use `?verbosity=verbose` or the verbosity header for the nested alias record with timestamps.

Example request:

```bash
curl -sS http://127.0.0.1:8765/v1/workspaces/recollectium/aliases \
  -H 'Content-Type: application/json' \
  -d '{"alias_uid":"recollectium-core","migrate_existing":false}'
```

Example response: compact default

```json
{
  "data": {
    "canonical_uid": "recollectium",
    "alias_uid": "recollectium-core",
    "status": "added",
    "migrated_memories": 0
  }
}
```

**Error 400 (existing memories under alias UID)**

```json
{
  "error": {
    "code": "validation_error",
    "message": "workspace alias conflicts with existing workspace memories: recollectium-core. Use --migrate-existing to move those memories to recollectium and keep recollectium-core as an alias.",
    "details": {}
  }
}
```

### `DELETE /v1/workspaces/aliases/{alias_uid}`

Purpose: remove an alias mapping by alias UID.

Compact is the default and returns `{alias_uid, canonical_uid, status}` with `status: "removed"`. Use `?verbosity=verbose` or the verbosity header for timestamps.

Example request:

```bash
curl -sS -X DELETE http://127.0.0.1:8765/v1/workspaces/aliases/recollectium-core
```

Example response: compact default

```json
{
  "data": {
    "alias_uid": "recollectium-core",
    "canonical_uid": "recollectium",
    "status": "removed"
  }
}
```

### `POST /v1/workspaces/{uid}/rename`

Purpose: rename a workspace by migrating all workspace memories (including archived) from
the old UID to a new UID. Both UIDs are normalized according to the
`workspace.uid_normalization` config setting before the operation.

Compact is the default and returns `{old_uid, new_uid, memories_updated, aliases_updated, status}` with `status: "renamed"`. Verbose mode returns the same counts without the compact status field.

Example request:

```bash
curl -sS -X POST http://127.0.0.1:8765/v1/workspaces/recollectium-core/rename \
  -H 'Content-Type: application/json' \
  -d '{"new_uid":"recollectium"}'
```

Request body:

```json
{
  "new_uid": "recollectium"
}
```

Example response: compact default

```json
{
  "data": {
    "old_uid": "recollectium-core",
    "new_uid": "recollectium",
    "memories_updated": 42,
    "aliases_updated": 3,
    "status": "renamed"
  }
}
```

**Error 404 (workspace not found)**

```json
{
  "error": {
    "code": "not_found",
    "message": "no workspace memories found for uid: nonexistent",
    "details": {}
  }
}
```

**Error 400 (empty new_uid after normalization)**

```json
{
  "error": {
    "code": "validation_error",
    "message": "workspace UID normalizes to an empty string: '!!!'",
    "details": {}
  }
}
```

## Notes

- Only documented fields are supported.
- JSON body is required for `POST` and `PATCH` endpoints that accept request-body inputs (`POST /v1/memories/search_user`, `POST /v1/memories/search_workspace`, `POST /v1/memories`, and `PATCH /v1/memories/{memory_id}`).
- `POST /v1/memories/{memory_id}/archive` is body-less.
- This document is tied to the current implementation and should be updated with service contract changes.
