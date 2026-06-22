# Recollectium WebUI

Recollectium WebUI is the local browser control plane for Recollectium Core. It uses the same local service contract as the CLI, API, and managed services, so you can inspect and manage a running Core from your browser.

## Start, stop, restart, status

Use the dedicated WebUI service commands:

```bash
recollectium webui serve
recollectium webui start
recollectium webui stop
recollectium webui restart
recollectium webui status
```

### Command modes

- `recollectium webui serve` runs the WebUI in the foreground for local development.
- `recollectium webui start` starts the managed background WebUI service.
- `recollectium webui stop` stops the managed WebUI service.
- `recollectium webui restart` restarts the managed WebUI service.
- `recollectium webui status` reports whether the WebUI is running and shows the current endpoints.

## Default host and port

The default bind address is `127.0.0.1:8766`.

You can override the bind address with config or with `serve` flags:

```bash
recollectium webui serve --host 127.0.0.1 --port 8766
```

The managed `start`, `stop`, `restart`, and `status` commands read the configured WebUI host and port from the active Recollectium config.

## Local-first security warning

The WebUI is local-first, unauthenticated, and intended for localhost use.

- Default authentication: none.
- Default TLS: off.
- Recommended bind: `127.0.0.1`.

Do not bind the WebUI to a non-local interface unless you also add private-network controls and understand that anyone who can reach the interface can access your local memory and service operations.

## What the WebUI can do

The WebUI exposes the same major local control surfaces as Core:

- Memory CRUD, search, archive, and memory-space filtering.
- Workspace listing, aliasing, and resolution.
- Config get, set, unset, and validate.
- Service discovery plus API, MCP, and WebUI service controls.
- Embedding status, refresh, job list, and job cleanup.
- Dev tools, including seeded data reset, evaluation, and threshold optimization.
- Graph, diagnostics, and logs views.

The packaged front end lives in `src/recollectium/webui_static/` and is exercised by the test suite, so WebUI changes should keep the static shell and the API contract in sync.

## Related docs

- [README](../README.md)
- [Roadmap](../ROADMAP.md)
- [Contributing](../CONTRIBUTING.md)
- [Local service API](local-service-api.md)
