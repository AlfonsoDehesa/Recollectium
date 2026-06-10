# Output surface audit follow-ups

This document tracks the red and yellow findings from the CLI/API/MCP compact/verbose and human-readable/JSON audit.

## Legend

- 🔴 Audit found an inconsistency to fix.
- 🟡 Alfonso made a product decision to implement.
- ✅ Fixed in this PR.

## Scope

Implement all red findings and all yellow decisions Alfonso accepted, while keeping C6 unchanged: `config --defaults` compact mode still shows the full config defaults.

## Items

| ID | Status | Surface | Item | Decision |
|---|---:|---|---|---|
| S1 / C38 / A18 / M10 | ✅ | CLI/API/MCP | `workspace list --include-aliases` verbose output is less informative than compact. | Make verbose preserve compact essentials and include full alias records/timestamps. |
| S2 / C46 / A13 / A14 / M17 / M18 | 🔴 | CLI/API/MCP | Compact embedding job rows omit failure reason. | Map failed job `error_message` to compact `reason`. |
| S3 / A5 / A6 | 🔴 | API docs | Search docs say default `limit=10`, implementation uses `20`. | Align docs with implementation default `20`. |
| C6 | 🟡 | CLI | `config --defaults` compact/verbose are the same. | Keep compact showing full config defaults. No change. |
| C15 | 🟡 | CLI | `config reset` verbose could include what changed. | Add verbose changed/reset detail. |
| C31 | 🟡 | CLI | `db-status` verbose could include migration internals. | Add verbose migration/internal detail. |
| C32 | 🟡 | CLI | `dev true` verbose could include seeded DB counts/details. | Add verbose seeded DB counts/details. |
| C33 | 🟡 | CLI | `dev false` verbose could include seeded DB state/context. | Add verbose seeded DB state/context. |
| C34 | 🟡 | CLI | `dev reset` verbose could include reset/seed counts/details. | Add verbose reset/seed counts/details. |
| C39 / A19 / M11 | ✅ | CLI/API/MCP | Compact workspace resolve includes input/normalized context. | Remove extra `input_uid` / `normalized_uid` from compact resolve. |
| C48 / A16 / M20 | 🟡 | CLI/API/MCP | Verbose embedding job clear could include deleted job IDs. | Add deleted job IDs in verbose clear output. |
| C50 | 🟡 | CLI | `--json completion` raw behavior could error instead of being ignored. | Make `--json completion` without `--install` fail with selected-format error. |

## Verification plan

- Add focused unit/CLI/API/MCP tests for each changed output contract.
- Run `uv run ruff format --check .`, `uv run ruff check .`, `uv run pyright`, focused tests, and full coverage before PR readiness.
