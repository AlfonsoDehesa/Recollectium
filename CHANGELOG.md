# Changelog

Recollectium v1.0 is here! 🎉

This release provides working embedding-powered semantic memory for agents, exposed through a pretty CLI, JSON CLI, MCP stdio, MCP HTTP, and an HTTP API. It gives agents a local place to remember useful context across sessions, search it semantically, and keep workspace knowledge separate from user-level memory.

## Unreleased

### ✨ Features

- **NEW DEFAULT MODEL:** switched the built-in FastEmbed default to `BAAI/bge-base-en-v1.5`, with a legacy profile still available for older installs.
- **MODEL PERFORMANCE EVALUATION:** added `recollectium dev eval` and `recollectium dev optimize-threshold` for seeded quality checks, threshold sweeps, and recommendation exports.
- **EMBEDDING MAINTENANCE:** expanded install, upgrade, search, refresh, and dev reset flows to prepare models, refresh stale embeddings, and clean up embedding jobs with visible progress.
- **RESPONSE VERBOSITY CONTROLS:** added compact defaults and verbose overrides across the CLI, HTTP API, and MCP surfaces for cleaner payloads.
- **MODEL CACHE AND UNINSTALL CLEANUP:** added a Recollectium-owned FastEmbed cache, upgrade tracking metadata, and uninstall handling for cached model artifacts while preserving user memories by default.
- **SAFER LOGGING:** added `logging.sensitivity` for redacted default logs with an opt-in full mode, plus workspace alias listing parity through the HTTP API.

### 🐛 Fixes

- **API, MCP, AND CLI PARITY:** tightened validation and error handling for invalid fields, enum values, protected thresholds, archive requests, and malformed JSON.
- **SCHEMA AND TOOL CONTRACTS:** fixed OpenAPI and schema coverage so validation errors, search overrides, embedding job filters, and MCP tool arguments are rejected and documented consistently.
- **CONSISTENT OUTPUT FORMATS:** improved compact and verbose output parity across workspace operations, lifecycle commands, config and version output, completion handling, and adapter responses.
- **QUIETER PROTOCOL OUTPUT:** fixed foreground serve and MCP startup logging so stderr follows the effective log level, hides routine FastMCP noise, and keeps memory-sensitive details redacted.
- **BETTER PROGRESS REPORTING:** fixed model readiness, init, and re-embedding flows so progress stays readable, stale cache state is handled correctly, and long refreshes complete inline.
- **INSTALL, UPGRADE, AND UNINSTALL CLEANUP:** fixed macOS state paths, shell PATH repair, `main` tracking, source install detection, and cleanup when metadata is missing.
- **HUMAN-FRIENDLY CLI OUTPUT:** kept eval, model prep, and memory result lists readable without breaking JSON, CSV, or protocol output.

### 🧹 Chores

- **SERVICE COMMANDS:** removed top-level `recollectium serve`; use `recollectium dev serve` for foreground development or `recollectium service start api` for managed startup.
- **RELEASE DOCS AND ADAPTER GUIDANCE:** refreshed docs for foreground serving, service discovery, API and MCP parity, the OpenCode adapter contract, and release notes guidance.
- **CI AND FIXTURE HARDENING:** hardened release automation, Node 24 GitHub Actions, installer smoke coverage, and test fixtures for installer selection and seeded evaluation data.
- **REPEATABLE DEV DATA:** refreshed seeded development memories and public-safe fixtures for local testing and retrieval experiments.

## v1.0.0

### ✨ Features

- Added the local-first Recollectium Core memory engine with SQLite-backed storage for private, durable memory on a user's own machine.
- Added user and workspace memory scopes with canonical memory buckets, type filters, metadata, and archive-aware retrieval.
- Added memory add, search, list, get, update, and archive operations across the CLI, Python API, local HTTP API, and MCP surfaces.
- Added FastEmbed semantic search with the `jinaai/jina-embeddings-v2-small-en` model, chunk-aware ranking, background re-embedding jobs, and embedding and job status reporting.
- Added SQLite migrations plus predictable config, data, cache, log, and runtime directories across supported platforms.
- Added a CLI with JSON output for automation and Rich-backed human-readable output for interactive terminals.
- Added a Python API, local FastAPI HTTP service, MCP stdio server, and managed MCP service for integrating local memory into tools.
- Added FastAPI endpoints for health, version, capabilities, memories, embeddings, workspaces, and service metadata.
- Added MCP tools for memory operations, workspace management, embedding status, embedding jobs, and service discovery.
- Added managed service lifecycle commands with start, stop, status, restart, discovery metadata, and local endpoint reporting.
- Added workspace UID normalization, listing, rename, resolve, and alias support for stable workspace identity across moved or renamed projects.
- Added an OpenCode adapter readiness contract with discovery, health, capability, workspace, remote Core, and split-machine deployment guidance.
- Added install-time initialization and model-readiness checks plus bootstrap installers for Linux, macOS, and Windows.
- Added upgrade checks, dry-run upgrade planning, and package upgrade flows that preserved running service state.
- Added one-command uninstall flows that stop managed services, clean managed completions, remove supported package installs, preserve user data by default, and require an explicit purge for data removal.
- Added shell completion generation for bash, zsh, fish, and PowerShell, including completion support for configuration keys.
- Added structured JSON logging with rotation plus lifecycle and failure events for install, service, CLI, API, MCP, embedding, and uninstall paths.
- Added an optional seeded development memory database with config toggles and `recollectium dev reset` for repeatable local testing.

### 🐛 Fixes

- Fixed validation for memory payloads, workspace identifiers, non-finite floats, bucket filters, and mixed workspace identity inputs.
- Fixed CLI stdout JSON contracts so automation output stayed clean while non-argparse failures emitted structured JSON on stderr.
- Hardened service lifecycle handling for stale or corrupt PID files, daemon cleanup, process ownership checks, crash detection, and discovery-file cleanup.
- Improved install and model-readiness failure handling with clearer offline, model download, and recovery guidance.
- Fixed MCP parity gaps for metadata, filters, embedding tools, workspace operations, and JSON metadata parsing failures.
- Fixed workspace alias handling and same-UID rename behavior so workspace identity updates were predictable and non-destructive.
- Fixed uninstall and completion cleanup behavior across supported shells and platforms.
- Clarified local service, API, security, and documentation wording where earlier guidance could imply unsupported authentication, exposure, or deployment guarantees.

### 🧹 Chores

- Adopted the AGPL-3.0-only license for the public release.
- Standardized the project on Python 3.12 or later with a uv-managed contributor and release workflow.
- Added contributor workflow documentation, issue templates, release checklist guidance, changelog conventions, and release automation.
- Added changelog validation and release workflow enforcement for curated release notes.
- Refreshed the README, SECURITY, ROADMAP, CONTRIBUTING, local service API docs, OpenAPI contract, OpenCode adapter contract, and GitHub Wiki documentation.
- Expanded CI and test coverage for core memory behavior, service lifecycle, MCP, install, uninstall, completion, and release-critical paths.
- Documented the v1 local-first unauthenticated security model with localhost defaults and private-network guidance.
- Retired repo-hosted wiki source pages in favor of the published GitHub Wiki as the canonical long-form documentation.
