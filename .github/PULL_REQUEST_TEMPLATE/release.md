## Release prep

Use this template for the release-prep PR only. Keep the regular PR template for normal work.

### Target version and tag

- Version:
- Tag:

### Release summary

- What is included in this release?
- What changed since the last release candidate or stable release?
- What is the release intent in one short paragraph?

### Release gate checklist

Fill every item below in the release-prep PR. Use the checkbox itself for status and add a short note inline if a gate is blocked, not applicable, or needs follow-up.

<details>
<summary>Gate A: Product and surface readiness</summary>

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

</details>

<details>
<summary>Gate B: Documentation readiness</summary>

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
- [ ] B13. Docs distinguish the tag-triggered GitHub Release path from any future package-published release path, and the post-release checks match the path actually in use.
- [ ] B14. User-facing examples are executable or clearly marked illustrative.
- [ ] B15. Docs links resolve.
- [ ] B16. Release notes call out operator actions, rollback guidance, known limitations, the support window, and the compatibility matrix.
- [ ] B17. Changelog and release notes describe the user-visible diff and omit internal noise.

</details>

<details>
<summary>Gate C: CLI and completion readiness</summary>

- [ ] C1. Every CLI command, subcommand, flag, and positional argument has help text.
- [ ] C2. Every CLI command supports both human-readable and JSON output shapes.
- [ ] C3. Argcomplete reaches every CLI command and flag.
- [ ] C4. `recollectium config get/set/unset <TAB>` completes config keys.
- [ ] C5. PowerShell dynamic completion works through `Register-ArgumentCompleter`.
- [ ] C6. PowerShell `recollectium config get/set/unset <TAB>` completes config keys.

</details>

<details>
<summary>Gate D: Install, upgrade, uninstall, and service readiness</summary>

- [ ] D1. Bootstrap install works on supported Linux and macOS paths.
- [ ] D2. Bootstrap install works on supported Windows paths.
- [ ] D3. `pip install` from the release candidate artifact works, if that artifact is available for install smoke testing.
- [ ] D4. `pipx install` from the release candidate artifact works, if that artifact is available for install smoke testing.
- [ ] D5. `uv tool install` from the release candidate artifact works, if that artifact is available for install smoke testing.
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

</details>

<details>
<summary>Gate E: Migration, embedding, and model readiness</summary>

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

</details>

<details>
<summary>Gate F: Quality readiness</summary>

Run the full quality gate in this release-prep PR before merge.

#### Quality commands

- [ ] `git diff --check`
- [ ] `uv run ruff format .` or `uv run ruff format --check .` as appropriate, with any formatter output committed
- [ ] `uv run ruff check .`
- [ ] `uv run pyright`
- [ ] `uv run pytest`
- [ ] `uv run pytest --cov=src/recollectium --cov-report=term-missing`
- [ ] CI passes, or is still pending with the current status recorded here:

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

</details>

<details>
<summary>Gate G: Post-release verification</summary>

- [ ] G1. A GitHub Release exists and includes the curated changelog.
- [ ] G2. Package install paths are verified only when a package-published release path is enabled for that release.
- [ ] G3. README and wiki links resolve after release.
- [ ] G4. Wiki content is current after release.
- [ ] G5. Version strings, dates, changelog, tag, package metadata, docs, and GitHub Release title all match.
- [ ] G6. The release workflow and tag trigger are verified.
- [ ] G7. Changelog extraction and generated release notes are verified.
- [ ] G8. GitHub Release publication is verified on the actual tag-triggered release path.
- [ ] G9. Failure recovery and rerun behavior are verified.
- [ ] G10. A clean canary on the GitHub Release tag or bootstrap release path works and uninstalls cleanly; package artifact canaries run only when package publication is enabled.

</details>

<details>
<summary>Gate H: Development tooling readiness</summary>

- [ ] H1. `recollectium dev eval` reports Exact MRR, Semantic MRR, Thematic Weighted Precision@10, Thematic Weighted Recall@10, and Ranked-set NDCG@5 according to the docs.
- [ ] H2. `recollectium dev eval` compact, verbose, JSON, and human-readable progress modes preserve their documented stdout and stderr contracts.
- [ ] H3. `recollectium dev optimize-threshold` documents and verifies its recommendation objective, F-beta precision and recall tradeoff, CSV output, PNG output, progress behavior, and `--write-config` behavior.
- [ ] H4. Seeded development fixtures remain public-safe, deterministic, isolated from real memory databases, and free of private memory contents.
- [ ] H5. Dev tooling cleans up generated artifacts, temp DBs, and reports after success or failure, or clearly documents where they are left.
- [ ] H6. Seeded and CI fixtures exercise realistic user, workspace, metadata, malformed, stale-embedding, and cross-surface cases.

</details>

### Version, changelog, and docs readiness

- [ ] Version bump complete.
- [ ] Changelog updated for the target release.
- [ ] Docs updated for any release gate gaps.
- [ ] Any intentional not applicable items are noted inline on the relevant checklist items.

### Post-merge and pre-tag checks

- [ ] Clean `main` checkout confirmed.
- [ ] Merge commit or branch SHA recorded.
- [ ] Tag ready to push.
- [ ] Release workflow watched on `main`.
- [ ] The final release-prep PR merge commit matches the reviewed branch state.

### Post-release checks

- [ ] GitHub Release published.
- [ ] Changelog and release notes match the tagged version.
- [ ] Published artifact checks passed.
- [ ] Follow-up validation complete.
- [ ] Release workflow completed successfully for the tagged commit.

### Risks, blockers, and follow-up

- Risks:
- Blockers:
- Follow-up:
