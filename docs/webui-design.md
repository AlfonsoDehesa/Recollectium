# Recollectium WebUI Design

## Architecture Decision

**Decision: keep the current packaged FastAPI static shell for this PR, and make it Reflex-ready rather than migrating it to Reflex now.**

Why:

- The current WebUI is already shipped as packaged static assets under `src/recollectium/webui_static/{index.html,styles.css,app.js}` and the test suite asserts that contract directly.
- `pyproject.toml` currently packages only `*.html`, `*.js`, and `*.css` for `recollectium.webui_static`, and Reflex is not a runtime dependency.
- Moving the PR to Reflex now would force a packaging/runtime shift and likely expand the test surface far beyond the design-step scope, while the current backend/service contract is already stable and green.

What this means for future work:

- Keep the FastAPI/static delivery path for now.
- Design components and tokens so they map cleanly to Reflex later: shell, status pills, chips, inspector panes, log streams, service cards, graph canvas, and confirmation dialogs.
- Preserve the existing control-plane endpoints and smoke coverage so any future migration stays behaviorally safe.

## Product Feel

Recollectium WebUI is a **retro pixel memory operations cockpit**: dark, dense, technical, and polished. It should feel like a local control room for memory state, service health, and configuration, with a tasteful retro game UI influence used as material language rather than cosplay.

The approved visual calibration is preserved in [`webui-inspo.md`](webui-inspo.md): v10 defines the pixel-art material style and v11 maps that style onto concrete Recollectium screens. Treat these as the reference direction for future WebUI work.

The experience should communicate:

- calm control over memory data and service actions,
- dense but readable diagnostics,
- local-first trust and provenance,
- operational seriousness for risky actions,
- visible system health at a glance.

## Palette

Use semantic tokens, not ad hoc colors.

| Token | Hex | Use |
| --- | --- | --- |
| `bg.app` | `#0B0F14` | App background |
| `bg.shell` | `#101722` | Persistent app chrome |
| `bg.panel` | `#151E2B` | Cards, panels, modals |
| `bg.panelRaised` | `#1B2636` | Selected rows, active panels |
| `border.subtle` | `#263244` | Default borders |
| `border.strong` | `#3A4A61` | Active borders, focus emphasis |
| `text.primary` | `#F3F6F8` | Primary text |
| `text.secondary` | `#B8C3CF` | Labels and metadata |
| `text.muted` | `#7F8B99` | Hints, timestamps, disabled text |
| `accent.memory` | `#6EE7B7` | Healthy state, active space |
| `accent.search` | `#8AB4FF` | Search, semantic ranking |
| `accent.graph` | `#A78BFA` | Graph relationships |
| `state.warning` | `#FBBF24` | Risk, stale config, attention |
| `state.danger` | `#FB7185` | Destructive or failed state |
| `state.info` | `#38BDF8` | Informational diagnostics |
| `shadow.glow` | `rgba(110, 231, 183, 0.18)` | Rare active-space glow |

Rules:

- Keep most surfaces neutral.
- Spend accent color on state and orientation, not decoration.
- Use danger only for destructive or failed states.
- Use warning for risky config, missing services, and deferred operations.

## Typography

- Prefer a clean sans family for UI text: Inter, Geist, Satoshi, or a comparable system fallback.
- Use a mono face for IDs, paths, timestamps, ports, counts, and diagnostic readouts: JetBrains Mono, IBM Plex Mono, or system monospace.
- Use tabular numerals where available for counts, scores, timestamps, ports, and confidence values.
- Keep headings compact and direct. This is an operational surface, not a marketing page.
- Memory content must stay readable before it becomes decorative.

## Layout and Density

- Use a persistent app shell with a clear active space indicator, global search, and service health in the top bar.
- Keep the sidebar compact and labeled. Avoid icon-only navigation until the product proves it needs it.
- Primary workspace should change by task: memories, spaces/config, workspaces, services, embeddings, dev tools, graph, diagnostics/logs.
- Use split-pane layouts for inspection workflows: list/table on the left, selected record or detail pane on the right.
- Reserve modals for confirmation and focused forms, not for basic reading.
- Desktop is the primary layout. On smaller screens, collapse the inspector below the main content and preserve active space/service visibility.

## Component Rules

### Memories

- Memory lists should read like a list/table hybrid: summary first, metadata second.
- Every memory should expose provenance, space, workspace, type, confidence, sensitivity, timestamps, and safe actions.
- Selected memory details belong in a stable inspector pane.
- Archive/delete actions need confirmation and clear scope language.

### Spaces

- Memory spaces are boundaries, not just filters.
- The active space must remain visible in the shell.
- Cross-space operations need explicit language and a visible scope indicator.

### Services

- Service cards should show running state, endpoint, health, version, port, and next action.
- Start/stop/restart controls need loading, disabled, and failure states.
- Self-stop or localhost changes should read as risky actions, not routine buttons.

### Config

- Read-only config should be easy to inspect.
- Editable config should separate safe fields from risky fields.
- Keep validation and unset actions visibly different from ordinary changes.

### Dev tools

- Treat evaluation, threshold tuning, seeding, and maintenance as a contained lab bench.
- Show progress and results in a log-like panel with copyable output.
- Make destructive dev actions explicit about their blast radius.

### Graph

- Graph views should explain relationships, not decorate the page.
- Start from a selected memory, search result, space, or workspace.
- Include filters, node-type meaning, and a way to reduce complexity.
- Avoid an unfiltered full-database graph as the default.

### Logs and diagnostics

- Logs must be searchable, copyable, and easy to scan.
- Diagnostics should summarize health first, then reveal details.
- Copy/download paths should be obvious and deliberate.

## Interaction, Motion, and Accessibility

- Motion should communicate state change, not novelty. Keep it short and subtle.
- Respect reduced-motion preferences.
- Keep visible focus on every interactive control.
- Maintain WCAG AA contrast for text and essential UI affordances.
- Every icon-only action needs an accessible label.
- Use toasts for completed actions, inline errors for forms, and persistent banners for service-level problems.
- Empty states should name the active space or scope and explain the next safe action.

## Inspiration and Anti-Patterns

### Inspiration

- Linear for disciplined density and calm hierarchy.
- Raycast for keyboard-friendly search and crisp command surfaces.
- Grafana and Datadog for health, logs, and operations structure.
- Obsidian graph view for local knowledge mapping, but heavily constrained.
- TablePlus or DataGrip for technical object browsing.
- The approved v10/v11 Recollectium inspo set in [`webui-inspo.md`](webui-inspo.md): modern dashboard composition with actual pixel-art UI construction.
- OpenGameArt Golden UI-style material language: brass/gold bevel frames, dark inset wells, inventory-slot cards, gem/status controls, and warm pixel-art edge highlights.
- Minimal fantasy / pixel RPG UI references for parchment wells, teal title bars/actions, hard-edged sprite icons, slot grids, side tabs, hotbars, and 9-slice-like frames.
- Retro keygen/cracktro interfaces for pixel tactility, stepped borders, and chunky status lights.

### Anti-patterns

- Generic SaaS dashboard styling.
- Bright gradients or AI-product gloss.
- Cutesy memory metaphors.
- Full-screen decorative graph hairballs.
- Flat tables with no hierarchy.
- Dangerous actions styled like normal actions.
- Overusing accent colors until state meaning disappears.

## WebUI Feature Coverage Rule

Any new user-facing Recollectium feature or operation should gain matching WebUI support in the same release unless the PR explicitly documents the deferment.

That includes support for:

- memories,
- memory spaces,
- workspaces,
- services,
- config,
- embeddings,
- dev tools,
- graph,
- diagnostics,
- logs.

If a future feature has no WebUI representation, the PR should say why and when the WebUI follow-up will happen.
