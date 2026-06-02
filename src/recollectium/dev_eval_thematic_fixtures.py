"""Deterministic thematic Precision@10 fixtures for seeded dev eval."""

from __future__ import annotations

from typing import TypedDict

from recollectium.models import SPACE_USER, SPACE_WORKSPACE

THEMATIC_PRECISION_QUERIES_PER_GROUP = 3


class ThematicPrecisionFixtureEntry(TypedDict):
    """Thematic Precision@10 fixture row for one seeded topic or theme group."""

    scope: str
    group: str
    workspace_uid: str | None
    queries: tuple[str, str, str]


THEMATIC_PRECISION_FIXTURE: tuple[ThematicPrecisionFixtureEntry, ...] = (
    {
        "scope": SPACE_USER,
        "group": "travel",
        "workspace_uid": None,
        "queries": (
            "flexible vacation days with neighborhoods, markets, and backup options",
            "trip planning preferences around lodging, tickets, meals, and pacing",
            "city break advice with transit access, local food, and room to wander",
        ),
    },
    {
        "scope": SPACE_USER,
        "group": "transportation",
        "workspace_uid": None,
        "queries": (
            "getting around with reliable routes, buffers, and fewer stressful transfers",
            "comparing trains, driving, walking, transit, parking, and backup rides",
            "arrival planning for stations, airports, appointments, and city errands",
        ),
    },
    {
        "scope": SPACE_USER,
        "group": "videogames",
        "workspace_uid": None,
        "queries": (
            "game recommendations with story, atmosphere, controls, saves, and session length",
            "low-pressure play preferences for exploration, puzzles, cozy goals, and flexible challenge",
            "choosing games by mood, art direction, multiplayer comfort, and couch setup",
        ),
    },
    {
        "scope": SPACE_USER,
        "group": "books",
        "workspace_uid": None,
        "queries": (
            "reading suggestions with character depth, tone, pacing, and spoiler-free fit",
            "book habits around concise chapters, calmer evenings, and rotating difficult reads",
            "fiction, nonfiction, mysteries, memoirs, and speculative stories that match reading mood",
        ),
    },
    {
        "scope": SPACE_USER,
        "group": "cooking",
        "workspace_uid": None,
        "queries": (
            "simple home meals using pantry staples, vegetables, grains, and easy cleanup",
            "recipe preferences for weeknights, leftovers, substitutions, and practical prep",
            "cooking advice with balanced dinners, savory breakfasts, batch lunches, and knife skills",
        ),
    },
    {
        "scope": SPACE_USER,
        "group": "fitness",
        "workspace_uid": None,
        "queries": (
            "sustainable exercise plans with strength work, walking, mobility, and rest days",
            "workout guidance that fits a normal week with simple equipment and warmups",
            "training advice focused on consistency, recovery, form, and adjustable intensity",
        ),
    },
    {
        "scope": SPACE_USER,
        "group": "music",
        "workspace_uid": None,
        "queries": (
            "playlist and song suggestions for focus, errands, workouts, cleaning, and relaxing",
            "music discovery based on mood, tempo, vocals, instruments, and steady transitions",
            "album or artist context with genre influences, listening vibe, and concise background",
        ),
    },
    {
        "scope": SPACE_USER,
        "group": "pets",
        "workspace_uid": None,
        "queries": (
            "calm animal care routines with feeding, enrichment, safety, and training cues",
            "pet-friendly home and travel advice with durable gear, cleanup, and quiet spaces",
            "keeping companion areas practical, safe, washable, predictable, and comfortable",
        ),
    },
    {
        "scope": SPACE_USER,
        "group": "learning",
        "workspace_uid": None,
        "queries": (
            "skill-building plans with small steps, exercises, checkpoints, and realistic sessions",
            "tutorial preferences around examples first, setup details, projects, and review",
            "study guidance that supports momentum, note taking, spaced practice, and visible progress",
        ),
    },
    {
        "scope": SPACE_USER,
        "group": "home style",
        "workspace_uid": None,
        "queries": (
            "cozy rooms with warm lighting, natural textures, muted colors, and personal details",
            "practical household layout for entryways, kitchens, offices, plants, and guest rooms",
            "decor choices with tidy storage, reading spots, soft materials, and reusable seasonal accents",
        ),
    },
    {
        "scope": SPACE_WORKSPACE,
        "group": "permissions",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "who should be allowed to change financial settings",
            "role boundaries for clerks, owners, reviewers, and support staff",
            "access control bugs when switching between workshop accounts",
        ),
    },
    {
        "scope": SPACE_WORKSPACE,
        "group": "exports",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "month-end report downloads for accounting review",
            "spreadsheet and archive packages with stable metadata",
            "safe export bundles that avoid credentials and private paths",
        ),
    },
    {
        "scope": SPACE_WORKSPACE,
        "group": "reconciliation",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "month-end closeout checks for expenses, bills, and payment status",
            "matching imported records with proof, amounts, dates, and references",
            "review blockers from open balances, duplicate imports, and uncleared purchases",
        ),
    },
    {
        "scope": SPACE_WORKSPACE,
        "group": "form-builder",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "designing field forms with prompts, conditions, repeatable sections, and previews",
            "editor tools for labels, internal IDs, constraints, branching, and saved templates",
            "authoring warnings when required items or conditional rules make layouts confusing",
        ),
    },
    {
        "scope": SPACE_WORKSPACE,
        "group": "offline-sync",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "saving inspection drafts on a device until network service returns",
            "queued submissions, receipts, conflicts, retention, and recovery after app restart",
            "offline work handoff with local autosave indicators and reconnect status banners",
        ),
    },
    {
        "scope": SPACE_WORKSPACE,
        "group": "review",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "final signoff checks for blank mandatory responses and rule failures",
            "supervisor completion review with waivers, error summaries, and accessibility focus",
            "validation messages for missing answers, conditional requirements, and changed rules",
        ),
    },
    {
        "scope": SPACE_WORKSPACE,
        "group": "scheduling",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "dispatch board timing for repair blocks, crew windows, and pier work clashes",
            "harbor job ordering around urgent repairs, crew blocks, filters, and idle gaps",
            "dispatch scheduling changes that preserve timing, filters, and crew readiness",
        ),
    },
    {
        "scope": SPACE_WORKSPACE,
        "group": "equipment",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "shared gear availability blocking repair work",
            "hoist, trailer, or tool conflicts across pier jobs",
            "equipment maintenance affecting dispatch assignments",
        ),
    },
    {
        "scope": SPACE_WORKSPACE,
        "group": "handoff",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "crew turnover notes for blocked, ready, or inspection-waiting harbor jobs",
            "handoff summaries with safety holds, permits, unresolved access, and next actions",
            "incoming coordinators preserving assignments and checklist status across shift changes",
        ),
    },
)
