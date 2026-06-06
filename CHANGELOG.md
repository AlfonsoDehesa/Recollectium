# Changelog

Recollectium v1.0 is here! 🎉

This release provides working embedding-powered semantic memory for agents, exposed through a pretty CLI, JSON CLI, MCP stdio, MCP HTTP, and an HTTP API. It gives agents a local place to remember useful context across sessions, search it semantically, and keep workspace knowledge separate from user-level memory.

## Unreleased

### ✨ Features

- Changed the default built-in FastEmbed model to `BAAI/bge-base-en-v1.5`.
  - Default profile: `builtin-fastembed-bge-base-en-v1-5-v1`, 768 dimensions, 512 max tokens, 384 chunk tokens, 64 overlap tokens.
  - Legacy supported profile: `jinaai/jina-embeddings-v2-small-en`, `builtin-fastembed-jina-v2-small-en-v1`, 512 dimensions, 8192 max tokens, 6144 chunk tokens, 512 overlap tokens.
- Added `recollectium dev eval`, a seeded retrieval-quality evaluator that reports Exact MRR, Semantic MRR, Thematic Weighted Precision@10, Thematic Weighted Recall@10, and Ranked-set NDCG@5 separately without a combined score; it now uses live progress indicators for preparation and counted phases, and concise mode is much shorter while verbose mode preserves the detailed seeded-db/diagnostics view.
- Added `recollectium dev optimize-threshold`, a seeded threshold optimizer that writes CSV or PNG sweep reports, marks a recommended `retrieval.match_threshold`, supports configurable F-beta precision/recall tradeoffs, shows human-readable progress with scoring ETA, and can optionally persist the recommendation with `--write-config`.
- Added explicit stale-embedding refresh and embedding job cleanup controls across CLI, HTTP API, and MCP.
- Added human-readable CLI re-embedding progress on search and embedding refresh commands while preserving JSON stdout contracts.
- Added install and upgrade embedding maintenance so bootstrap installs and successful package upgrades prepare the configured model and refresh stale or missing embeddings inline when needed.
- Added upgrade target tracking in install metadata. Bootstrap installs now default to the latest release, explicit upgrades can track latest, a pinned release, or `main`, and `--check`/`--dry-run` remain non-mutating.
- Added product-wide response verbosity controls. CLI, API, and MCP now default to compact payloads for token efficiency, with `response_verbosity`, `--compact`/`--verbose`, API query/header controls, and MCP `verbosity` tool parameters for full-detail inspection when needed.
- Added a Recollectium-owned FastEmbed model cache under `directories.cache` so heavy model artifacts can be reported and removed on uninstall while preserving memories by default.

### 🐛 Fixes

- Re-embedding now runs inline for the triggering CLI command, API request, or MCP tool call so large refreshes finish durably instead of being stranded in a process-local background daemon queue.
- Fixed bootstrap install metadata on macOS so `recollectium upgrade` reads installs from the same state directory the installer writes.
- Fixed `main`-tracking upgrades to compare installed and remote commit SHAs so `--check`, `--dry-run`, and plain upgrades skip work when already current unless `--force` is used.
- Fixed uninstall planning for direct pip, pipx, and uv tool installs when install metadata is missing.
- Fixed source upgrade detection so package installs launched from a Recollectium checkout are not misclassified as source checkouts.
- Fixed bootstrap installs for macOS zsh users so the Recollectium CLI path is added to zsh startup files.
- Fixed bootstrap PATH repair so malformed or empty managed path blocks are rewritten with the current uv tool bin export.
- Suppressed uv bootstrap PATH warnings while keeping durable shell PATH edits based on the user's original terminal environment.
- Clarified bootstrap installer PATH guidance when the current shell cannot see the installed command yet.
- Fixed model cache status and uninstall cleanup reporting for custom embedding providers and Recollectium-owned FastEmbed cache paths.
- Fixed `recollectium dev eval` human-readable TTY progress so it updates one pretty stderr line and clears before the final summary instead of printing a line per progress update.
- Fixed human-readable CLI output framing so final output and argparse help start with a blank line and end with a trailing blank line while JSON, CSV, completion, and protocol output stay byte-clean.
- Fixed human-readable memory result lists so the result count and each memory entry are separated by a blank line.

### 🧹 Chores

- Added installer selector metadata test coverage and CI install-smoke metadata assertions.
- Added stable seeded-memory `eval_key` metadata and a checked-in thematic query-memory label dataset for future retrieval-quality scoring work.
- Updated seeded development memory fixtures with unique fictional user and project memories safe for public repositories, without visible deterministic label prefixes in stored content.
- Refreshed workspace seeded development memories so each dummy workspace has three 10-memory themes for retrieval efficacy testing.

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
