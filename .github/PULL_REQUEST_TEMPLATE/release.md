## Release prep

Use this template for the release-prep PR only. Keep the regular PR template for normal work.

### Target version and tag

- Version:
- Tag:

### Release summary

- What is included in this release?
- What changed since the last release candidate or stable release?

### Gate status

| Gate | Status | Notes |
| --- | --- | --- |
| A | Pass / Fail / Blocked / N/A | |
| B | Pass / Fail / Blocked / N/A | |
| C | Pass / Fail / Blocked / N/A | |
| D | Pass / Fail / Blocked / N/A | |
| E | Pass / Fail / Blocked / N/A | |
| F | Pass / Fail / Blocked / N/A | |
| G | Pass / Fail / Blocked / N/A | |
| H | Pass / Fail / Blocked / N/A | |

### Version, changelog, and docs readiness

- Version bump complete:
- Changelog updated for the target release:
- Docs updated for any release gate gaps:
- Any intentional not applicable items:

### Quality checks

- `git diff --check`:
- `uv run ruff format .` or check as needed:
- `uv run ruff check .`:
- `uv run pyright`:
- `uv run pytest`:
- `uv run pytest --cov=src/recollectium --cov-report=term-missing`:

### Post-merge and pre-tag checks

- Clean `main` checkout confirmed:
- Merge commit or branch SHA:
- Tag ready to push:
- Release workflow watched on `main`:

### Post-release checks

- GitHub Release published:
- Changelog and release notes match the tagged version:
- Published artifact checks passed:
- Follow-up validation complete:

### Risks, blockers, and follow-up

- Risks:
- Blockers:
- Follow-up: