# Changelog

Recollectium gives AI tools a local memory they can search across sessions. It keeps useful context on your machine, separates personal memory from workspace memory, and exposes the same memory system through the CLI, API, and MCP integrations.

## Unreleased

### ✨ Features

- **BETTER DEFAULT SEARCH MODEL:** the built-in default is now `BAAI/bge-base-en-v1.5`, which gives better search results while keeping memory lookups fast and inexpensive. If you prefer speed over accuracy, you can still choose the lighter older model in your settings.
- **TOOLS FOR TESTING SEARCH QUALITY:** added `recollectium dev eval` and `recollectium dev optimize-threshold` to compare search models and tune the cutoff for what counts as a match. These are the tools used before adding model support, and users can run them too when they want to test their own data.
- **SEARCH THRESHOLD CUTOFF:** added a match cutoff for search results, so Recollectium can favor either more recall or fewer false matches. Advanced users can set a number, turn the cutoff off with `null`, or let Recollectium follow the recommended default for the selected model when one is provided.
- **SAFE MODEL SWITCHING:** if your memories were embedded with one model and you switch to another later, Recollectium keeps the memories and re-embeds them on the next search, so you can change models without losing anything.
- **CLEARER OUTPUT OPTIONS:** compact output is now the default, with verbose output still available when you want more detail in the CLI, API, or MCP tools.
- **MODEL DOWNLOADS AND CLEANUP:** Recollectium now manages its own FastEmbed cache, keeps track of upgrades, and cleans up cached model files during uninstall without removing your memories.
- **SAFER LOGGING:** added `logging.sensitivity` so normal logs stay redacted by default, with a full-detail option when you need it. Workspace alias listing now matches across the HTTP API too.

### 🐛 Fixes

- **MORE CONSISTENT INPUT CHECKS:** tightened validation and error handling for bad field names, invalid option values, protected thresholds, archive requests, and malformed JSON.
- **MATCHES ARE EASIER TO READ:** improved search, model setup, and re-embedding progress so long-running work is easier to follow and stale cache state is handled correctly.
- **MATCHING OUTPUT ACROSS INTERFACES:** kept CLI, API, and MCP responses aligned for workspace operations, service commands, config and version output, completions, and adapters.
- **LESS NOISE IN LOGS:** foreground service and MCP startup logs now follow the active log level, hide routine FastMCP noise, and keep sensitive memory details redacted.
- **BETTER FAILURE MESSAGES:** improved install and model readiness errors so offline setups, model downloads, and recovery steps are easier to understand.
- **CLEANER CLI LISTS:** eval results, model prep output, and memory lists stay readable without breaking JSON, CSV, or protocol output.

### 🧹 Chores

- **SERVICE COMMANDS:** removed top-level `recollectium serve`; use `recollectium dev serve` for local development or `recollectium service start api` for managed startup.
- **DOCS AND RELEASE NOTES:** refreshed the docs for foreground serving, service discovery, API and MCP parity, the OpenCode adapter contract, and release notes guidance.
- **TESTS AND RELEASE SUPPORT:** strengthened release automation, Node 24 GitHub Actions, installer smoke tests, and fixtures for installer selection and seeded evaluation data.
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
