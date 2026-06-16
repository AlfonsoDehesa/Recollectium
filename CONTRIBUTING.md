# Contributing to Recollectium

Thanks for helping improve Recollectium. This guide is the contributor contract for the repo: how to request features, report bugs, submit pull requests, and prepare releases.

Use the available GitHub templates. They keep review focused and make sure maintainers get the information they need in one place.

## 1. Submit a feature request

Use the Feature request issue template. Describe the problem you are trying to solve, not just the solution you want.

A short user story helps:

```text
I want to do X so that Y.
```

Include:

- The use case.
- The current workaround, if any.
- The surface you expect to use: CLI, Python API, local HTTP API, MCP, configuration, service lifecycle, logging, install, uninstall, adapter/plugin integration, or docs.
- Any compatibility constraints you already know about.

Feature requests do not need a full implementation design. They should make the user need clear enough that maintainers can decide whether it belongs in Core, an adapter, the wiki, or a later roadmap phase.

## 2. Submit a bug report

Use the Bug report issue template. Before opening a new issue, check open and closed issues to see whether the problem has already been reported.

A good bug report has three parts: what happened, what you expected, and how to reproduce it.

Include:

- The exact command you ran.
- The full error output. Do not summarize or trim it.
- Recollectium logs, if possible.
- The output of `recollectium --version`.
- Your OS and Python version, from `python --version`.
- The exact reproduction steps, in order.
- Any config, database path, or memory data involved, if it is safe to share.

Do not paste secrets, tokens, credentials, private memory contents, or sensitive local paths into public issues. If sensitive data is required to explain the problem, redact it or ask a maintainer how to share it safely.

## 3. Submit a PR

Pull requests should be scoped, verified, documented, and easy to review. Keep each PR focused on one feature, fix, or docs change.

Use the pull request template. Do not delete template sections just because the PR is small. If a section does not apply, mark it as not applicable and say why.

### Development setup

Requirements:

- Python 3.12 or later.
- `uv`.
- Git.

Everything else is managed by uv.

```bash
git clone https://github.com/AlfonsoDehesa/recollectium.git
cd recollectium
uv sync --group dev
```

This creates the project virtual environment, installs Recollectium in editable mode, and installs developer tools such as pytest, ruff, pyright, and coverage.

Verify the environment:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv run recollectium --help
```

Always run project commands through `uv run` while developing from a source checkout so tools use the managed environment instead of a global Python install.

Optional local push guardrail: install the repo-local pre-push hook to catch formatter and lint failures before CI:

```bash
git config core.hooksPath .githooks
```

The hook runs `uv run ruff format --check .` and `uv run ruff check .`. If formatting fails, it prints `uv run ruff format --diff .` plus fix guidance. CI still runs the same strict checks, so commit formatter output from `uv run ruff format .` before pushing.

### Branches and commits

All work starts from `main` on a feature branch. Never commit directly to `main` and never push directly to `main`.

```bash
git checkout main
git pull --ff-only origin main
git checkout -b docs/my-change
```

Use descriptive branch names:

- `docs/<topic>` for documentation.
- `fix/<topic>` for bug fixes.
- `feat/<topic>` for new features.
- `chore/<topic>` for maintenance.

Each commit should be one logical, verified change. Do not save all work for one large end-of-branch commit when the work can be split into clean slices.

Preferred commit messages use `type(scope): summary`.

- Use a short lowercase type such as `docs`, `fix`, `feat`, `test`, `chore`, or `refactor`.
- Keep the scope short, lowercase, and specific to the touched area, such as `release`, `logging`, `cli`, `api`, `mcp`, `install`, or `docs`.
- Write the summary in imperative or concise present tense. Make it human-readable and specific.

Good commit messages:

```text
docs(contributing): clarify commit message shape
docs(release): clarify release gate checklist
fix(logging): propagate log level to service restart
feat(mcp): expose workspace alias removal
```

Avoid vague messages such as `updates`, `fix stuff`, or `address feedback`.

### PR format

Open a PR when there is a concrete change to review. Draft PRs are fine for early feedback. Keep follow-up work on the same PR until review is done.

Every PR should answer:

- What changed?
- Why did it change?
- How was it verified?
- Which docs were updated?
- What is the status of every required quality gate?
- Are there any risks, compatibility notes, migration notes, or follow-up items?

Use this structure in the PR body or in a final PR comment before review:

```markdown
## Summary

One or two sentences describing the change.

## Changes

- Changed X to do Y.
- Updated docs for Z.

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

- Risk: ...
- Follow-up: ...
```

For docs-only PRs, still list the gates that apply as passed, skipped with a reason, or not applicable. Do not make the reviewer infer that a gate was skipped.

### Broad PR and red-to-green CI iteration

Prefer small PRs. When a broad PR is unavoidable, keep CI red-to-green work disciplined:

- Keep every required gate enabled. Do not add path filters, `continue-on-error`, matrix reductions, draft skips, warning suppression, or deleted tests to get a green check.
- Push focused commits that each address one root cause, then rerun the failed local gate before pushing again.
- Let superseded PR CI runs cancel; do not use cancellation to avoid investigating the newest failing run.
- Note which CI job failed, the first relevant error, the suspected root cause, and the local command that reproduced or ruled it out.
- If CI fails only on one OS or architecture, preserve the matrix and isolate the platform-specific assumption.

Common red-to-green root causes:

| Symptom | Likely root cause | Keep-strict fix |
| --- | --- | --- |
| `uv run ruff format --check .` fails | Formatter output was not committed | Run `uv run ruff format .`, review the diff, commit it, and rerun the check. |
| `uv run ruff check .` fails | New lint issue or unsafe auto-fix left unreviewed | Fix the reported rule, or run `uv run ruff check --fix .` and review the result. |
| `uv run pyright` fails | Type contract drift, missing narrowing, or stale test fixture typing | Fix the type surface or fixture annotations without weakening type checking. |
| `uv run pytest` fails | Behavior regression, missing fixture update, or order/platform assumption | Reproduce the focused test locally and fix the code or test expectation. |
| Install smoke fails on one matrix leg | Shell, PATH, platform, or architecture-specific install assumption | Keep the matrix intact and add a targeted cross-platform fix plus coverage. |
| Release workflow fails | Changelog/tag contract or release action input drift | Fix the release contract or workflow input while preserving release validation. |

### PR submittal gates

Before marking a PR ready for review, complete the gates that match the changed surface. Summarize the applicable gate status in the PR template.

#### Required for every PR

- The branch is based on current `main`.
- The PR is scoped to one feature, fix, or docs change.
- `git diff --check` passes.
- The PR template is complete.
- Docs are updated or marked not applicable with a reason for each canonical doc.
- `CHANGELOG.md` is updated for release-notable work, or the PR explains why no changelog entry is needed.
- CI is passing or the PR clearly states which check is still pending or failing.
- Secrets, tokens, credentials, private memory contents, and sensitive local paths are not included.

#### Required for code changes

Run the full gate before review unless the PR explains why a gate is not applicable:

```bash
uv run ruff format .
uv run ruff check .
uv run pyright
uv run pytest
uv run pytest --cov=src/recollectium --cov-report=term-missing
```

Coverage should stay at 100 percent for changed or added code. If 100 percent is not feasible, list the exact uncovered lines in the PR and explain why the gap is acceptable.

Do not suppress warnings, loosen rules, or delete tests to make checks pass.

#### Required for docs-only changes

Run at least:

```bash
git diff --check
uv run ruff format --check .
uv run ruff check .
uv run pyright
```

If the docs change wiki navigation or anchors, verify the wiki sidebar and links that changed.

#### Required for CLI, API, MCP, and service changes

Surface parity matters. If functionality is reachable through one primary surface, confirm whether it belongs in the others. Before release, every functionality reachable through the CLI must also be reachable through the API and the MCP server unless there is a documented reason not to expose it.

When adding, removing, or changing CLI commands or flags, update CLI help text and docs in the same PR. Every CLI command should have:

- A short top-level command description.
- Clear command-level `--help` output.
- Help text for every flag and positional argument.
- Any important constraints, defaults, formats, or side effects.

Useful help checks for the full command inventory:

```bash
uv run recollectium --help
uv run recollectium init --help
uv run recollectium add --help
uv run recollectium search-user --help
uv run recollectium search-workspace --help
uv run recollectium list --help
uv run recollectium get --help
uv run recollectium update --help
uv run recollectium archive --help
uv run recollectium workspace --help
uv run recollectium config --help
uv run recollectium service --help
uv run recollectium dev serve --help
uv run recollectium db-status --help
uv run recollectium dev --help
uv run recollectium embedding-status --help
uv run recollectium embedding-maintenance --help
uv run recollectium embedding-jobs --help
uv run recollectium embedding-refresh --help
uv run recollectium embedding-jobs-clear --help
uv run recollectium mcp-stdio --help
uv run recollectium completion --help
uv run recollectium upgrade --help
uv run recollectium uninstall --help
```

Seeded development eval fixtures include stable `metadata.eval_key` values and
checked-in thematic query-memory labels under `src/recollectium/`. The thematic
label dataset feeds `recollectium dev optimize-threshold` and the weighted
thematic portion of `recollectium dev eval`: keep validation tests current when
changing seeded thematic memories or queries.

If a PR changes local service API endpoints, request schemas, response schemas, error shapes, capability names, version behavior, workspace UID rules, or local access/security assumptions, update both `docs/local-service-api.md` and `docs/local-service-openapi.json`.

If a PR changes service discovery, remote Core addressing, health/version/capability validation, workspace UID selection, adapter-facing operations, local auto-start, or plugin error handling expectations, update `docs/opencode-adapter-contract.md` and the matching wiki page.

#### Required for logging changes

Structured logging is a release gate. Before marking a PR ready, confirm that changed major features, endpoints, and code paths are logged where useful. Changed failure paths should emit appropriate structured events.

Logs must:

- Preserve stdout JSON contracts.
- Avoid memory content, metadata payloads, credentials, tokens, secrets, and other sensitive data.
- Avoid noisy events that make logs harder to use.

If a PR changes logging config, log path behavior, service logs, CLI log-level handling, structured log events, or failure paths, update the Wiki Logs page in the same change.

### Documentation update rules

Docs are part of the product. If a PR changes user-facing behavior, update the matching docs in the same PR.

Canonical docs:

- `README.md`: public front door, install overview, status, quick start, local access/security summary, and links to deeper docs.
- GitHub Wiki: long-form user and integrator manual. Keep wiki changes aligned with the same PR whenever behavior, docs, configuration, CLI, API, MCP, service lifecycle, logs, install, uninstall, security guidance, or adapter contracts change.
- `docs/local-service-api.md`: human-readable local API reference.
- `docs/local-service-openapi.json`: machine-readable local API contract served by the service.
- `docs/opencode-adapter-contract.md`: canonical adapter/plugin contract for OpenCode and related integrations.
- `SECURITY.md`: supported versions, vulnerability reporting, local access assumptions, and security posture.
- `ROADMAP.md`: current progress, release blockers, completed work, and upcoming version targets.
- `CONTRIBUTING.md`: contributor, PR, quality gate, and release procedure contract.
- `CHANGELOG.md`: human-readable release notes for published versions. The release workflow uses this file as the curated part of the GitHub Release body.

### Changelog usage

Recollectium keeps a human-written `CHANGELOG.md` and uses GitHub's generated release notes as automation on top of that. GitHub can collect merged PRs automatically, but it cannot reliably decide which changes matter to users or how to phrase them. The changelog is the curated summary; generated release notes are supporting detail.

Use a changelog entry for release-notable work:

- New user-visible behavior, commands, endpoints, config, install behavior, docs surfaces, or integrations.
- Bug fixes that change behavior, remove user-visible failure modes, or clarify confusing docs.
- Release chores that matter to users or operators, such as CI coverage, packaging, release automation, dependency policy, or documentation structure.

Skip a changelog entry for changes that are not useful in release notes, such as typo-only fixes, internal test refactors, PR template cleanup, or follow-up edits that are already covered by a broader entry. If you skip it, write the reason in the PR's `CHANGELOG.md` checkbox.

Every release section must use this exact shape:

```markdown
## Unreleased

### ✨ Features

- Added ...

### 🐛 Fixes

- Fixed ...

### 🧹 Chores

- Updated ...
```

Use `## Unreleased` while work is accumulating. In the release-prep PR, rename or copy the unreleased notes to the target version heading, such as `## v1.0.0`, then restore a fresh empty `## Unreleased` section above it.

Keep entries short and user-facing. Start each bullet with a past-tense verb such as `Added`, `Fixed`, `Updated`, `Documented`, or `Removed`. Do not paste commit hashes, PR numbers, or internal implementation noise into the changelog unless they help users understand the release.

The changelog shape is enforced by `tests/test_changelog.py`, which requires every release section to contain exactly these subsections in order: `✨ Features`, `🐛 Fixes`, and `🧹 Chores`.

Update `ROADMAP.md` in the same PR when a change implements a release blocker or roadmap item. Move completed work into the `Completed` section, mark the item complete, and keep the remaining roadmap accurate. Do not leave completed work expanded under remaining blockers.

Recollectium v1 services are unauthenticated and localhost-first. If a PR changes service host or port behavior, API or MCP service exposure, remote Core deployment guidance, discovery wording, auth/TLS/API key posture, data paths, database access, or filesystem assumptions, update `SECURITY.md` and linked local-access warnings.

### Schema migrations

A SQLite schema change includes new tables, columns, indexes, constraints, or data-shape changes to existing rows.

Recollectium uses an internal migration runner under `src/recollectium/migrations/versions/`. Do not assume Alembic is required for current SQLite schema migrations.

If a PR changes the SQLite schema, include a migration plan in the PR. The plan must state:

- The migration module under `src/recollectium/migrations/versions/`.
- The exact schema change.
- How existing rows are populated, defaulted, nullable, or intentionally unknown.
- Whether any new field is semantically required and how legacy rows satisfy it.
- Whether backfill is synchronous in the migration or deferred to a background job.
- Whether the migration is safe to apply lazily on database open.
- Running-service compatibility expectations.
- Downgrade or forward-only behavior when a database is newer than the installed package.
- Tests proving upgrade behavior from the previous schema version.

Semantically required fields must not rely on application code silently inventing values for legacy rows unless that fallback is explicitly documented and tested.

Embedding migration is not the same as database migration. Provider, model, profile, or vector changes belong to the re-embedding path. Table, column, index, and data-shape changes belong to SQLite schema migrations.

### Review and follow-up commits

PRs are reviewed by a codebase administrator and merged to `main` once they pass. When you are ready for review, mark the PR ready or leave a comment asking for review.

Replies and follow-up commits happen on the same PR. Do not open a new PR for review fixes unless the maintainer asks for one.

When review feedback is in:

1. Read every comment before making changes.
2. Group related fixes into focused commits.
3. Update tests and docs with the fix, not afterward.
4. Run the right quality gate for the scope of the change.
5. Push the branch.
6. Reply to the review with what changed and which checks passed.

A review is not resolved just because a commit was pushed. The final PR state should make it easy for the reviewer to see that each requested change was handled.

A good final PR comment includes:

```markdown
Addressed review feedback in `<commit>`.

What changed:
- ...

Verification:
- `git diff --check`: passed
- `uv run ruff check .`: passed
- `uv run pyright`: passed
- `uv run pytest`: passed or not run because ...
- CI: passed or pending

Remaining:
- None, or the exact remaining blocker.
```

### AI-assisted development

AI-assisted development is allowed as long as it follows every convention in this document. The same quality gates, commit standards, docs requirements, and review process apply regardless of how the code was written.

Do not commit AI tooling configuration to the repo. The `.gitignore` excludes common editor and agent directories such as `.opencode/`, `.cursor/`, `.claude/`, and `.aider*`. If a tool writes project config, keep it local. The repo is for Recollectium, not for your development environment.

## 4. For admins

This section is for maintainers and release managers.

### Merge policy

Delete the feature branch after merge. The merge commit on `main` is the record.

Do not tag or release directly from a feature branch. Releases happen from `main` only.

Before merging a PR, confirm:

- The PR is reviewed and approved.
- Required CI checks are green.
- The PR template is complete.
- Required docs and release notes are updated or explicitly not applicable.
- Any release-blocker work is reflected in `ROADMAP.md`.

### CI ownership

CI runs on every push and PR. The matrix covers lint, type checking, tests, coverage, and cross-platform bootstrap install smoke tests on Linux, macOS, and Windows.

CI is defined in `.github/workflows/`. If a PR changes how Recollectium builds, installs, upgrades, uninstalls, runs services, validates completions, or publishes releases, update CI in the same PR.

Pull request workflow runs use concurrency cancellation for superseded PR commits only. Main branch and tag runs must not be canceled or skipped as a substitute for fixing failures.

### Release procedure

Releases are created automatically when a version tag is pushed. Maintainers should do the tag and release from a clean `main` checkout after the release-prep PR is merged.

The release-prep PR is the single PR for the release sweep. It is a normal PR with a release-specific scope and should use the release template, which already contains the full release gate checklist plus the quality checks, version, changelog, and post-release sections. Fill that template in one place instead of duplicating the gate elsewhere.

The release-prep PR should contain the Phase A audit, any fixes required by that audit, and the version and changelog preparation for the target release:

- Confirm every item in the release gate in the release template below or fix the gap in the release-prep PR.
- Bump `version` in `pyproject.toml`.
- Move the curated `CHANGELOG.md` entries into the target release section.
- Update docs for gaps found during the release gate.

Release steps:

1. Choose the target version and confirm the intended tag, such as `v1.0.0`.
2. Open the release-prep PR against `main` with the release template, for example with `?template=release.md`, and fill the full gate checklist, quality checks, version, changelog, and release sections in that template.
3. Complete the release gate below in the release-prep PR. Fix any release-blocking gaps in that same PR.
4. Bump the version and prepare the changelog in the release-prep PR after the audit scope is known.
5. Run the required quality gates in the release-prep PR before merge and record the results in the PR.
6. Wait for review and CI to pass on the release-prep PR.
7. Merge the release-prep PR.
8. Update local `main` and verify the checkout is clean:

   ```bash
   git checkout main
   git pull --ff-only origin main
   git status --short
   ```

9. Confirm CI is green on `main` for the merge commit before tagging. Do not tag if local `main` differs from the reviewed release-prep merge commit.
10. Tag and push the release:

   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

11. Wait for `.github/workflows/release.yml` to finish. The workflow publishes the matching `CHANGELOG.md` section as the curated release body and lets GitHub append generated release notes for merged PR detail.
12. Complete the post-release checks below.

### Release gate

Every item in this gate is checked against the version about to be released, not the currently published release or current `main`. All release docs updates, along with release-gate fixes, version bumps, and changelog edits, belong in the release-prep PR for the version about to be released.

Use the gate names below as addressable status labels when discussing release readiness. Mark the applicable items Pass, Fail, Blocked, or N/A in the release-prep PR, with a short reason for Blocked or N/A.

#### Gate A: Product and surface readiness

- [ ] A1. User-facing operations available through CLI, API, or MCP stay symmetric unless the release notes call out a documented exception.
- [ ] A2. Every operation that supports compact output also supports verbose output where applicable.
- [ ] A3. Compact responses include the information required for product correctness and useful returned info.
- [ ] A4. `config get`, `config set`, and `config unset` cover every supported config key.
- [ ] A5. CLI failures emit structured stderr JSON when that surface is documented, keep stdout clean, and avoid leaking sensitive logs.
- [ ] A6. Structured logging stays useful across the paths changed in the release.
- [ ] A7. Human-readable progress for long-running CLI work uses the existing progress primitives and clears before final output.
- [ ] A8. Human-facing progress and logs never pollute JSON, CSV, completion output, MCP stdio, or API responses.
- [ ] A9. Indeterminate work uses honest indeterminate progress instead of implying completion.
- [ ] A10. Final human-readable output starts and ends cleanly without prompt collisions, provider noise, or stray log output.
- [ ] A11. Unknown, malformed, conflicting, and out-of-range inputs are rejected consistently across surfaces with documented error envelopes.
- [ ] A12. Public contract changes across CLI help, OpenAPI, MCP schemas, config keys, and output shapes are intentional and backward-compatible or documented as breaking.
- [ ] A13. Version and capability discovery are explicit for the release, including the user-visible version string, supported commands, surfaced capabilities, and any changed defaults.
- [ ] A14. Deprecation and removal policy is documented for changed defaults, removed commands, renamed fields, config changes, and any behavior incompatibility.
- [ ] A15. Semver classification is explicit for changed defaults, removed commands, renamed fields, config changes, and any behavior incompatibility.
- [ ] A16. Config compatibility and precedence remain correct for supported config files, flags, environment variables, defaults, and API or MCP overrides.
- [ ] A17. Known client and adapter compatibility stays intact, including OpenCode and other supported MCP clients.
- [ ] A18. Stale supported clients either continue working or fail gracefully when new fields, capabilities, config, or model metadata are added.
- [ ] A19. First-run and empty-state workflows are correct and documented.
- [ ] A20. Workspace isolation works across aliases, UID changes, moved or renamed directories, and cross-workspace behavior.
- [ ] A21. Archive and delete semantics, Unicode and path weirdness, large output and limits, timeouts and cancellation, exit and status codes, noninteractive automation, and agent-facing compact responses behave correctly.

#### Gate B: Documentation readiness

- [ ] B1. README is current, welcoming, and brief.
- [ ] B2. Wiki pages cover every command, flag, and user workflow touched by the release.
- [ ] B3. Wiki content matches current behavior with no stale or contradictory instructions.
- [ ] B4. `docs/local-service-api.md` matches the service behavior shipped in the release.
- [ ] B5. `docs/local-service-openapi.json` matches the served API contract.
- [ ] B6. The OpenCode adapter contract is current.
- [ ] B7. `SECURITY.md` is current.
- [ ] B8. `ROADMAP.md` is current.
- [ ] B9. `CONTRIBUTING.md` is current.
- [ ] B10. The target release section in `CHANGELOG.md` has exactly `### ✨ Features`, `### 🐛 Fixes`, and `### 🧹 Chores` in that order.
- [ ] B11. Changelog bullets are thematic user-facing entries, not one line per commit or PR.
- [ ] B12. Install, upgrade, uninstall, model, cache, logging, and re-embedding docs distinguish automatic behavior from operator action.
- [ ] B13. Docs distinguish GitHub-tag-only releases from package-published releases, and the post-release checks match the actual publishing path.
- [ ] B14. User-facing examples are executable or clearly marked illustrative.
- [ ] B15. Docs links resolve.
- [ ] B16. Release notes call out operator actions, rollback guidance, known limitations, the support window, and the compatibility matrix.
- [ ] B17. Changelog and release notes describe the user-visible diff and omit internal noise.

#### Gate C: CLI and completion readiness

- [ ] C1. Every CLI command, subcommand, flag, and positional argument has help text.
- [ ] C2. Every CLI command supports both human-readable and JSON output shapes.
- [ ] C3. Argcomplete reaches every CLI command and flag.
- [ ] C4. `recollectium config get/set/unset <TAB>` completes config keys.
- [ ] C5. PowerShell dynamic completion works through `Register-ArgumentCompleter`.
- [ ] C6. PowerShell `recollectium config get/set/unset <TAB>` completes config keys.

#### Gate D: Install, upgrade, uninstall, and service readiness

- [ ] D1. Bootstrap install works on supported Linux and macOS paths.
- [ ] D2. Bootstrap install works on supported Windows paths.
- [ ] D3. `pip install` from the release candidate artifact works.
- [ ] D4. `pipx install` from the release candidate artifact works.
- [ ] D5. `uv tool install` from the release candidate artifact works.
- [ ] D6. `recollectium --version`, `init`, and minimal add, search, and list workflows work after each supported install path.
- [ ] D7. Upgrade from the previous supported release preserves memories, config, services, completions, metadata, and embeddings.
- [ ] D8. `upgrade --check` is non-mutating.
- [ ] D9. `upgrade --dry-run` shows the planned command and is non-mutating.
- [ ] D10. Upgrade selectors `latest`, pinned, and `main` are mutually exclusive.
- [ ] D11. A successful mutating upgrade persists the chosen future target for the next run.
- [ ] D12. `main` tracking compares installed and remote SHAs and no-ops unless forced.
- [ ] D13. Mutating upgrade works across bootstrap, `pip`, `pipx`, `uv tool`, and source installs.
- [ ] D14. Mutating upgrade preserves the running service state when applicable.
- [ ] D15. Failed install, upgrade, uninstall, model readiness, and re-embedding operations leave a recoverable state with clear guidance.
- [ ] D16. Install, upgrade, uninstall, service, completion, model readiness, and re-embedding operations are idempotent where expected.
- [ ] D17. Offline or degraded network behavior is correct for install, upgrade, model download, and version checks.
- [ ] D18. Destructive or data-removing operations require explicit intent, report what was removed, and preserve user memory by default.
- [ ] D19. Uninstall preserves data by default.
- [ ] D20. `uninstall --purge` is safe and removes only the intended managed data.
- [ ] D21. Purge and cache cleanup remove only managed files and keep foreign files safe.
- [ ] D22. Managed files are discoverable through the documented manifest or equivalent listing.
- [ ] D23. `service start`, health checks, and `service stop` work on Linux, macOS, and Windows.
- [ ] D24. Service lifecycle behavior is correct when active clients are connected or recently connected.
- [ ] D25. A fresh-machine or no-dev-state canary passes from the release artifact.
- [ ] D26. Cross-platform path, shell, and state behavior is correct, including bash, zsh, fish, and PowerShell where supported.

#### Gate E: Migration, embedding, and model readiness

- [ ] E1. Schema migration plans and tests exist for any schema change.
- [ ] E2. Downgrade and forward-only migration behavior are documented, including what happens when a database is newer than the installed package.
- [ ] E3. Migration recovery guidance covers failure during apply, interrupted upgrades, and how to restore or re-run safely after a failed migration.
- [ ] E4. Lazy migration is safe and documented for the operator.
- [ ] E5. Re-embedding is separate from SQLite migrations.
- [ ] E6. Re-embedding works for the previous supported model and the newly supported model.
- [ ] E7. Default model changes document model, profile, dimensions, max tokens, chunking, overlap, cache, and compatibility effects.
- [ ] E8. Stale, missing, or legacy embeddings refresh durably through CLI, API, and MCP.
- [ ] E9. Re-embedding preserves memory identity, metadata, workspace, timestamps, archive state, and queryability unless a documented exception applies.
- [ ] E10. Model cache behavior is documented and tested separately from memory preservation.
- [ ] E11. Backup, corruption, and newer-database posture includes recovery guidance.
- [ ] E12. Import, export, and backup features, if present, work with release data and operator recovery workflows.
- [ ] E13. Model provider availability, cache reuse, fallback behavior, and custom provider behavior work as documented.

#### Gate F: Quality readiness

Run the full PR code gate in the release-prep PR before merge:

```bash
uv run ruff format .
uv run ruff check .
uv run pyright
uv run pytest
uv run pytest --cov=src/recollectium --cov-report=term-missing
```

The remaining checks happen after merge and before tagging.

- [ ] F1. Formatting is clean.
- [ ] F2. Ruff check is clean.
- [ ] F3. Pyright reports zero errors and warnings.
- [ ] F4. Pytest passes.
- [ ] F5. Coverage is 100 percent or any accepted misses are documented.
- [ ] F6. CI is green on the release-prep PR.
- [ ] F7. After merge and before tagging, local `main` is clean.
- [ ] F8. After merge and before tagging, CI is green on `main`.
- [ ] F9. Post-merge verification comes from a clean checkout of the final branch or merge commit.
- [ ] F10. Post-merge verification uses fresh outputs: no stale background processes, old output, dirty worktrees, or uncommitted edits remain.
- [ ] F11. Contract artifacts are regenerated or verified unchanged.
- [ ] F12. Secrets, private memory, local path, and privacy leaks are scanned across artifacts, docs, fixtures, logs, and generated files.
- [ ] F13. Security and privacy behavior is correct for localhost defaults, unauthenticated service assumptions, redaction, private path handling, and docs warnings.
- [ ] F14. Dependency review covers direct, transitive, and dev dependencies plus any new pins or constraints.
- [ ] F15. GitHub Actions and release automation changes are reviewed for workflow, tag-trigger, or platform impact.
- [ ] F16. Installer and packaging changes are reviewed for build inputs, install paths, and release safety.
- [ ] F17. License review covers third-party license changes and bundled notices.
- [ ] F18. Platform support review covers supported OS, Python, and shell assumptions.
- [ ] F19. Reproducibility review covers pinned inputs and deterministic release behavior.
- [ ] F20. Wheel and sdist contents are inspected for missing, unintended, stale, or version-mismatched files.
- [ ] F21. Installers and release assets are inspected for missing, unintended, stale, or version-mismatched files.
- [ ] F22. Generated contracts and docs are inspected for stale or mismatched content.
- [ ] F23. Package metadata is correct, including entry points, dependency constraints, Python classifiers, license, project URLs, and package data.
- [ ] F24. Minimum and latest supported Python and OS boundaries are verified.
- [ ] F25. The release is reproducible from the tagged commit.
- [ ] F26. The changed areas are audited for performance.
- [ ] F27. The changed areas are audited for concurrency and interruption handling.
- [ ] F28. The changed areas are audited for atomicity and concurrent writer behavior.
- [ ] F29. The changed areas are audited for filesystem limits and clock or timestamp assumptions.
- [ ] F30. The changed areas are audited for log growth.
- [ ] F31. The changed areas are audited for test isolation and generated-doc determinism.
- [ ] F32. The changed areas are audited for cleanup after failed dev tooling, troubleshooting, and observability.

#### Gate G: Post-release verification

- [ ] G1. A GitHub Release exists and includes the curated changelog.
- [ ] G2. Published package install paths work from the released artifact when available.
- [ ] G3. README and wiki links resolve after release.
- [ ] G4. Wiki content is current after release.
- [ ] G5. Version strings, dates, changelog, tag, package metadata, docs, and GitHub Release title all match.
- [ ] G6. The release workflow and tag trigger are verified.
- [ ] G7. Changelog extraction and generated release notes are verified.
- [ ] G8. Artifact publishing is verified on the actual release path.
- [ ] G9. Failure recovery and rerun behavior are verified.
- [ ] G10. A clean canary on the published artifact works and uninstalls cleanly.

#### Gate H: Development tooling readiness

- [ ] H1. `recollectium dev eval` reports Exact MRR, Semantic MRR, Thematic Weighted Precision@10, Thematic Weighted Recall@10, and Ranked-set NDCG@5 according to the docs.
- [ ] H2. `recollectium dev eval` compact, verbose, JSON, and human-readable progress modes preserve their documented stdout and stderr contracts.
- [ ] H3. `recollectium dev optimize-threshold` documents and verifies its recommendation objective, F-beta precision and recall tradeoff, CSV output, PNG output, progress behavior, and `--write-config` behavior.
- [ ] H4. Seeded development fixtures remain public-safe, deterministic, isolated from real memory databases, and free of private memory contents.
- [ ] H5. Dev tooling cleans up generated artifacts, temp DBs, and reports after success or failure, or clearly documents where they are left.
- [ ] H6. Seeded and CI fixtures exercise realistic user, workspace, metadata, malformed, stale-embedding, and cross-surface cases.

For questions, open an issue using the available template. The repo docs and GitHub Wiki are the source of truth for public project docs.
