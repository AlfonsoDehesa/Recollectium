<p align="center">
  <img src="https://raw.githubusercontent.com/AlfonsoDehesa/Recollectium/main/docs/assets/recollectium-banner.png" alt="Recollectium" width="100%">
</p>

## About

Agents work better when they can remember what already happened.

Recollectium gives AI agents a local, inspectable memory layer. It keeps the context that usually evaporates between sessions: preferences, project decisions, setup notes, debugging context, working style, and the hard-earned details that make an agent more useful over time.

Core handles the durable parts: SQLite storage, local embeddings, semantic search, migrations, local service APIs, MCP tools, service lifecycle, structured logs, and adapter discovery. Adapters stay thin. They bring the current workspace context, then let Core handle memory the same way every time.

OpenCode is the first major adapter target, but Recollectium is built for a world with many agents, many models, and many interfaces sharing one memory store.

## Why another memory engine?

Because most agent memory is either missing, trapped in one client, mixed across contexts, or hard to inspect and move.

Recollectium is built around a few stubborn ideas:

- **Memory belongs to the user.** Your machine, your database, your runtime. Memory leaves only when you choose to send it somewhere else.
- **Recall should work by meaning.** Human memory does not depend on exact strings. Agent memory should not either. Recollectium uses local embeddings so agents can find what matters even when the words do not match.
- **Personal context matters.** Project facts are useful. Durable user memory is the multiplier: preferences, style, goals, habits, and the patterns that make an assistant feel like it has been paying attention.
- **Setup should stay boring.** Install it, initialize it, and keep moving, without signing up for a hosted memory provider or fighting a dependency maze.
- **Models should be replaceable.** Use the agents, providers, and clients you like. If you switch tools, your memory comes with you.
- **One Core, many surfaces.** CLI, Python, local HTTP API, MCP stdio, and managed MCP service mode all talk to the same memory engine.
- **The future needs a shared foundation.** Dreamer agents, context managers, summarizers, and richer adapter integrations should build on one memory layer instead of inventing a new store each time.
- **Open source means no mystery box.** Inspect it, run it, back it up, move it, fork it, improve it.

## Quick start

Linux and macOS:

```bash
curl -LsSf https://raw.githubusercontent.com/AlfonsoDehesa/recollectium/main/install.sh | sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/AlfonsoDehesa/recollectium/main/install.ps1 | iex"
```

The bootstrap installer tracks the latest release by default. It also prepares the configured embedding model and refreshes stale or missing local embeddings when needed. See [Installation](https://github.com/AlfonsoDehesa/Recollectium/wiki/Installation) for pinned versions, `main`, and upgrade targets.

For the full setup flow, including first memory, service startup, MCP, API, logs, and troubleshooting, see the [Quick Start](https://github.com/AlfonsoDehesa/Recollectium/wiki/Quick-Start) in the GitHub Wiki.

## Database upgrades and recovery

Recollectium applies SQLite schema migrations automatically when `init`, `upgrade`, or a service start opens the database. Pending migrations run in order and only once. There is no separate manual migrate command.

Upgrades are forward-only. If the database is newer than the installed Recollectium build, startup fails with a migration error. In that case, upgrade Recollectium to a build that understands the newer schema or restore a backup from before the newer schema was written. Downgrades are not supported.

If a migration fails or startup is interrupted while it is applying, the failed step is rolled back and the database stays on the last successful version. After you fix the underlying problem, rerun the same command. Recollectium resumes from the last applied migration.

Before upgrading in production, stop the service and make a manual backup of the Recollectium data directory or the SQLite database file. There is no dedicated backup command in v1. If the database becomes corrupted, restore that copy and start Recollectium again.

Common next steps:

- Install details: [Installation](https://github.com/AlfonsoDehesa/Recollectium/wiki/Installation)
- Learn the model: [Concepts](https://github.com/AlfonsoDehesa/Recollectium/wiki/Concepts)
- Configure Recollectium: [Configuration](https://github.com/AlfonsoDehesa/Recollectium/wiki/Configuration)
- Use a seeded development database: [Seeded development database](https://github.com/AlfonsoDehesa/Recollectium/wiki/Configuration#seeded-development-database)
- Use the CLI: [CLI Reference](https://github.com/AlfonsoDehesa/Recollectium/wiki/CLI-Reference)
- Start services: [Service Management](https://github.com/AlfonsoDehesa/Recollectium/wiki/Service-Management)
- Read logs: [Logs](https://github.com/AlfonsoDehesa/Recollectium/wiki/Logs)
- Connect through MCP: [MCP Server](https://github.com/AlfonsoDehesa/Recollectium/wiki/MCP-Server)
- Call the local API: [API Reference](https://github.com/AlfonsoDehesa/Recollectium/wiki/API-Reference)

## What Recollectium gives you

- Local SQLite memory storage.
- Explicit `user` and `workspace` memory scopes.
- Canonical memory buckets for preferences, facts, decisions, task context, configuration, bug findings, and notes.
- Logical memory-space keys that route CLI, API, and MCP memory/database operations without changing the default behavior.
- Create, search, list, get, update, and archive memory operations.
- Local FastEmbed embeddings. Default: `BAAI/bge-base-en-v1.5` with 768 dimensions, profile `builtin-fastembed-bge-base-en-v1-5-v1`, 512 max tokens, 384 chunk tokens, and 64 overlap tokens.
- Legacy FastEmbed support for `jinaai/jina-embeddings-v2-small-en` with 512 dimensions, profile `builtin-fastembed-jina-v2-small-en-v1`, 8192 max tokens, 6144 chunk tokens, and 512 overlap tokens.
- Inline re-embedding jobs, explicit refresh controls, embedding job audit-record cleanup, and embedding status inspection. Switching embedding model or profile refreshes stale memories in the command or request that triggered it instead of relying on a fragile background thread.
- CLI, Python API, local HTTP API, and MCP surfaces with consistent results.
- Configurable CLI output, with Rich-backed TTY color for human-readable text and JSON available for automation.
- Optional seeded development database for repeatable embedding, search, and memory-operation tests without touching your regular memory DB. Seeded memories include stable `metadata.eval_key` values and a checked-in thematic label dataset. `recollectium dev optimize-threshold` sweeps retrieval thresholds, writes a CSV or PNG report, and recommends a model-specific `retrieval.match_threshold` using a precision-biased F0.5 default unless you override `--beta`. `recollectium dev eval` shows live progress on stderr, keeps concise progress generic, and exposes fuller verbose diagnostics, including Thematic Weighted Precision@10 and Thematic Weighted Recall@10 backed by the checked-in labels.
- Managed API and MCP service lifecycle with discovery metadata for adapters.
- Structured JSON logging with rotation.
- Bootstrap install, package upgrade with embedding maintenance, safe uninstall that removes heavy derived model artifacts while preserving memories by default, and shell completion.
- The built-in FastEmbed cache at `${directories.cache}/models` is Recollectium-owned derived data. Plain uninstall preserves memories and config but removes that model cache, including when `directories.cache` points at a custom cache directory.

## Documentation

Start with the GitHub Wiki:

- [Wiki Home](https://github.com/AlfonsoDehesa/Recollectium/wiki)
- [Quick Start](https://github.com/AlfonsoDehesa/Recollectium/wiki/Quick-Start)
- [Installation](https://github.com/AlfonsoDehesa/Recollectium/wiki/Installation)
- [Concepts](https://github.com/AlfonsoDehesa/Recollectium/wiki/Concepts)
- [Configuration](https://github.com/AlfonsoDehesa/Recollectium/wiki/Configuration)
- [Features and Commands](https://github.com/AlfonsoDehesa/Recollectium/wiki/Features-and-Commands)
- [CLI Reference](https://github.com/AlfonsoDehesa/Recollectium/wiki/CLI-Reference)
- [Service Management](https://github.com/AlfonsoDehesa/Recollectium/wiki/Service-Management)
- [Logs](https://github.com/AlfonsoDehesa/Recollectium/wiki/Logs)
- [MCP Server](https://github.com/AlfonsoDehesa/Recollectium/wiki/MCP-Server)
- [API Reference](https://github.com/AlfonsoDehesa/Recollectium/wiki/API-Reference)
- [Adapter and Plugin Integration](https://github.com/AlfonsoDehesa/Recollectium/wiki/Adapter-and-Plugin-Integration)
- [Verified Supported Plugins](https://github.com/AlfonsoDehesa/Recollectium/wiki/Verified-Supported-Plugins)
- [Troubleshooting](https://github.com/AlfonsoDehesa/Recollectium/wiki/Troubleshooting)
- [FAQ](https://github.com/AlfonsoDehesa/Recollectium/wiki/FAQ)

Repo docs that act as canonical contracts:

- [Local service API](docs/local-service-api.md)
- [OpenAPI JSON](docs/local-service-openapi.json)
- [OpenCode adapter contract](docs/opencode-adapter-contract.md)
- [Security policy](SECURITY.md)
- [Contributing guide](CONTRIBUTING.md)
- [Roadmap](ROADMAP.md)

## Local-first security model

Recollectium v1 services are local-first and unauthenticated. The recommended deployment is to run Recollectium on the same machine as the agent or client and keep services bound to localhost, usually `127.0.0.1`.

Binding the API or MCP service to a non-local interface can expose memory operations to anyone who can reach that interface. If you need split-machine access, use private networking with external access controls. For most users, Tailscale is the friendliest path.

Read [SECURITY.md](SECURITY.md) before changing service host settings or exposing Recollectium outside the local machine.

## Project status

Recollectium Core v1.1.1 is the current release. Core includes the CLI, Python API, local HTTP API, MCP stdio, managed MCP service, local embeddings, service lifecycle, install, upgrade, uninstall, logging, and adapter discovery contract.

OpenCode plugin implementation remains a roadmap item.

See [ROADMAP.md](ROADMAP.md) for current and upcoming roadmap work.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow, quality gates, documentation rules, release checklist, and PR process.

Please do not publish sensitive vulnerability details in public issues. See [SECURITY.md](SECURITY.md) for security reporting guidance.

## License

Recollectium is licensed under the [GNU Affero General Public License v3.0](LICENSE).
