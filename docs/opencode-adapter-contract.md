# OpenCode adapter contract for Recallium

This document describes the contract between Recallium Core and a future
OpenCode adapter or plugin.

Recallium Core already exposes the local service, workspace memory operations,
and workspace UID normalization contract that an adapter needs. The adapter's
job is to bridge OpenCode's workspace context and agent tool surface to
Recallium's local service, not to reimplement memory logic inside OpenCode.

## What the adapter must do

A Recallium adapter should:

- Discover the running local Recallium service automatically where practical.
- Allow explicit host, IP, port, or base-URL overrides for deployments where
  the adapter and Recallium are not on the same machine.
- Validate that the discovered service is healthy and compatible before use.
- Resolve the workspace from the actual working directory the host app scoped
  the agent to, not from model guesswork.
- If that directory is inside a git-managed tree, use the git repository root
  as the canonical workspace boundary. Nested subfolders inherit the same
  workspace UID.
- If there is no git-managed tree, use the current workspace directory or its
  containing workspace folder as the canonical boundary.
- Normalize the resulting UID with Core's workspace UID rules before passing it
  into Recallium workspace memory operations.
- Expose user-memory and workspace-memory operations as separate tools.
- Treat Recallium Core as the source of truth for memory storage and search.

## Service discovery contract

Use the machine-readable discovery command rather than hardcoding host, port,
or service paths:

```bash
recallium service discover
```

Discovery is the first step for any adapter workflow.

For same-machine installs, discovery should be automatic and the adapter should
not require the user to enter host, port, PID file, runtime path, or service
type manually. For deployments where the adapter is talking to Recallium on a
different machine, keep a host, IP, or base-URL setting available as a fallback
and still prefer discovery when it is reachable.

Discovery returns JSON that includes:

- service type
- process ID
- endpoint
- API prefix
- health URL
- version URL
- capabilities URL
- Recallium version
- service API version
- config path
- runtime directory
- PID file path
- discovery file path

Adapter behavior:

- If discovery reports a running service, use the returned URLs directly.
- If discovery reports `not_running`, guide the user to start the API service.
- If discovery reports invalid or stale metadata, treat that as a local recovery
  problem and surface the error clearly.

## Validation contract

Before enabling Recallium-backed tools, the adapter should validate the service
in this order:

1. Call `health_url` and require an ok response.
2. Call `version_url` and verify the service API version is compatible.
3. Call `capabilities_url` and verify the capabilities needed by the adapter
   are present.

The current service contract exposes these core capabilities:

- `health.read`
- `version.read`
- `capabilities.read`
- `memories.search_user`
- `memories.search_workspace`
- `memories.add`
- `memories.update`
- `memories.archive`
- `memories.list`
- `memories.get`
- `embedding.status`
- `embedding.jobs.list`
- `embedding.jobs.get`
- `workspaces.list`
- `workspaces.rename`

The adapter should treat capability names as the compatibility check, not the
transport details.

## Workspace UID contract

Workspace memories are keyed by a stable workspace UID. The adapter must not
use a filesystem path as the canonical key or invent a separate workspace
registry.

Recommended adapter behavior:

- Determine the current workspace from the host application's active project,
  current directory, or other workspace context.
- Use the git repository root as the workspace boundary when the active path is
  inside a git-managed tree. Subfolders under the same repo do not get separate
  workspace UIDs.
- When there is no git repo, use the actual current workspace directory or its
  containing workspace folder as the boundary.
- Derive the workspace UID from that boundary, then normalize it using Core's
  `workspace.uid_normalization` rules.
- Pass that normalized UID into Recallium workspace memory operations.

If the adapter maintains workspace metadata in a repo-local file, that file is
an adapter concern, not a Core requirement. Recallium Core does not require any
specific file format, registry, or git-based identity. The only contract is
that the adapter resolves the UID for the actual directory before calling Core.

The adapter should preserve the distinction between:

- workspace identity, which is a stable UID
- workspace location hints, which may be useful metadata but are not the key
- transport settings such as host, IP, or base URL, which are separate from the
  workspace identity and only matter for remote deployments

## Memory operation contract

Expose separate tools or actions for:

- user memory search
- workspace memory search
- add memory
- update memory
- archive memory
- list memories
- get memory by ID
- list workspace UIDs
- rename workspace UID

Workspace operations should require a workspace UID when the underlying Core
operation does.

User memory operations must remain scope-separated from workspace memory
operations.

## Error handling contract

The adapter should surface service problems clearly:

- service not running
- incompatible service API version
- missing capability
- missing or invalid workspace UID
- stale discovery metadata

When the service is unavailable, the adapter should fail with a message that
helps the user start or rediscover the service instead of silently falling back
or inventing a workspace identity.

## Recommended workflow

1. Install Recallium Core.
2. Start the local service.
3. Run `recallium service discover`.
4. Validate health, version, and capabilities.
5. Resolve the active workspace UID from the actual workspace boundary the
   host app scoped the agent to. If that path is inside a git-managed tree, use
   the git repository root; otherwise use the current workspace directory or
   containing workspace folder. Normalize it using Core's rules.
6. Call the memory endpoints needed for the user task.

## Documentation expectations

When this contract changes, update the corresponding Core docs in the same PR:

- `README.md`
- `docs/local-service-api.md`
- `ROADMAP.md`
- `CONTRIBUTING.md` if the maintenance gate changes

This document should stay aligned with the live Core service contract and the
roadmap item's completion status.
