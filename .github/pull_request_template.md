## Summary

<!-- What does this PR do? One or two sentences. -->

## Changes

<!-- What files changed and what was done to them. -->

## Documentation

- [ ] `README.md` updated, or not applicable because ...
- [ ] GitHub Wiki updated, or not applicable because ...
- [ ] `docs/local-service-api.md` updated, or not applicable because ...
- [ ] `docs/local-service-openapi.json` updated, or not applicable because ...
- [ ] `docs/opencode-adapter-contract.md` updated, or not applicable because ...
- [ ] `SECURITY.md` updated, or not applicable because ...
- [ ] `ROADMAP.md` updated, or not applicable because ...
- [ ] `CONTRIBUTING.md` updated, or not applicable because ...
- [ ] `CHANGELOG.md` updated under `✨ Features`, `🐛 Fixes`, or `🧹 Chores`, or not applicable because ...
- [ ] WebUI support was updated for any user-facing feature or operation, or not applicable because ...

## Database migrations

- [ ] This PR does not change the SQLite schema
- [ ] If it changes the SQLite schema, the PR includes the migration module, existing-row population/default/nullability plan, lazy-migration safety notes, any required background backfill or re-embedding plan, and upgrade tests from the previous schema version

## Quality gates

- [ ] `git diff --check` passes
- [ ] `uv run ruff format --check .` passes, or not applicable because ...
- [ ] `uv run ruff check .` passes
- [ ] `uv run pyright` passes
- [ ] `uv run pytest` passes, or not applicable because ...
- [ ] `uv run pytest --cov=src/recollectium --cov-report=term-missing` targets 100% on changed code, or accepted misses are documented
- [ ] CI passes, or is pending at ...

## Formatting notes

- [ ] Formatter output from `uv run ruff format .` is committed, or no formatter changes were needed
- [ ] Optional local hook considered: `git config core.hooksPath .githooks`

## Broad PR / CI iteration notes, if applicable

- Failing job and first relevant error:
- Root cause:
- Local reproduction or focused check:
- Strict fix applied without path filters, `continue-on-error`, matrix reductions, draft skips, warning suppression, or deleted tests:

## Risks and follow-up

<!-- Compatibility notes, known risks, deferred work, or manual release steps. -->
