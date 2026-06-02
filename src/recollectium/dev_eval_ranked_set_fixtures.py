"""Deterministic ranked-set NDCG@5 fixtures for seeded dev eval."""

from __future__ import annotations

from typing import TypedDict

from recollectium.models import SPACE_USER, SPACE_WORKSPACE

RANKED_SET_NDCG_CUTOFF = 5


class RankedSetRelevanceFixtureEntry(TypedDict):
    """Graded relevance judgment for one seeded memory in a ranked-set case."""

    grade: int
    rationale: str


class RankedSetNDCGFixtureEntry(TypedDict):
    """Ranked-set NDCG@5 fixture row for one curated query."""

    id: str
    scope: str
    workspace_uid: str | None
    query: str
    relevance: dict[str, RankedSetRelevanceFixtureEntry]


RANKED_SET_NDCG_FIXTURE: tuple[RankedSetNDCGFixtureEntry, ...] = (
    {
        "id": "user-travel-flexible-day-planning",
        "scope": SPACE_USER,
        "workspace_uid": None,
        "query": "plan a flexible city trip day with one main activity and backup ideas",
        "relevance": {
            "dev-user-008": {
                "grade": 3,
                "rationale": "Directly states the user wants one anchor activity per travel day with flexible time around it.",
            },
            "dev-user-010": {
                "grade": 3,
                "rationale": "Directly covers saved backup lists for indoor activities, parks, and restaurants when plans change.",
            },
            "dev-user-001": {
                "grade": 2,
                "rationale": "Strong supporting context because the user prefers wandering time instead of reservation-packed trips.",
            },
            "dev-user-007": {
                "grade": 2,
                "rationale": "Relevant support because advance-ticket and rainy-day advice shapes practical flexible itinerary planning.",
            },
            "dev-user-005": {
                "grade": 1,
                "rationale": "Adjacent travel context about early market visits, but not about day structure or fallback planning.",
            },
        },
    },
    {
        "id": "user-transport-reliable-route-tradeoffs",
        "scope": SPACE_USER,
        "workspace_uid": None,
        "query": "choose a reliable route with fewer stressful transfers even if it costs more",
        "relevance": {
            "dev-user-017": {
                "grade": 3,
                "rationale": "Directly says reliable transportation matters more than the cheapest option.",
            },
            "dev-user-012": {
                "grade": 3,
                "rationale": "Directly says the user prefers fewer transfers even when a route is slightly slower.",
            },
            "dev-user-015": {
                "grade": 2,
                "rationale": "Clearly supports route choice by comparing time, cost, and hassle across modes.",
            },
            "dev-user-020": {
                "grade": 2,
                "rationale": "Relevant context about arriving early to avoid rushed transportation timing.",
            },
            "dev-user-018": {
                "grade": 1,
                "rationale": "Adjacent because rideshare is a backup for bad weather or late nights, not the core reliability tradeoff.",
            },
        },
    },
    {
        "id": "user-games-low-pressure-session-fit",
        "scope": SPACE_USER,
        "workspace_uid": None,
        "query": "recommend a relaxing game with gentle goals and clear save behavior for short sessions",
        "relevance": {
            "dev-user-027": {
                "grade": 3,
                "rationale": "Directly describes cozy low-pressure games with gentle goals for unwinding.",
            },
            "dev-user-028": {
                "grade": 3,
                "rationale": "Directly covers clear save systems and avoiding lost progress during longer or paused sessions.",
            },
            "dev-user-024": {
                "grade": 2,
                "rationale": "Clearly relevant because playtime and short-session fit are part of the query.",
            },
            "dev-user-022": {
                "grade": 2,
                "rationale": "Relevant support because flexible difficulty helps tune challenge to mood.",
            },
            "dev-user-030": {
                "grade": 1,
                "rationale": "Adjacent platform comfort and readable UI context, but not specifically relaxation or saves.",
            },
        },
    },
    {
        "id": "user-cooking-weeknight-leftover-dinner",
        "scope": SPACE_USER,
        "workspace_uid": None,
        "query": "make an easy weeknight dinner using pantry staples and leftover vegetables",
        "relevance": {
            "dev-user-041": {
                "grade": 3,
                "rationale": "Directly states the user prefers 30-minute weeknight dinners with minimal cleanup.",
            },
            "dev-user-043": {
                "grade": 3,
                "rationale": "Directly lists pantry staples the user keeps available for meals.",
            },
            "dev-user-050": {
                "grade": 3,
                "rationale": "Directly covers planning meals around leftover herbs, vegetables, and grains.",
            },
            "dev-user-045": {
                "grade": 2,
                "rationale": "Relevant support because clear recipes with substitutions help use available ingredients.",
            },
            "dev-user-049": {
                "grade": 1,
                "rationale": "Adjacent because balanced dinner preferences help, but it is less about quick pantry or leftover use.",
            },
        },
    },
    {
        "id": "user-learning-practical-small-projects",
        "scope": SPACE_USER,
        "workspace_uid": None,
        "query": "learn a skill through small practical projects with checkpoints and concise examples",
        "relevance": {
            "dev-user-086": {
                "grade": 3,
                "rationale": "Directly says the user enjoys learning through small projects that produce something useful.",
            },
            "dev-user-083": {
                "grade": 3,
                "rationale": "Directly describes checkpoints and visible progress for keeping learning momentum.",
            },
            "dev-user-089": {
                "grade": 2,
                "rationale": "Clearly supports the query with concise explanations and examples in different contexts.",
            },
            "dev-user-081": {
                "grade": 2,
                "rationale": "Relevant because the user prefers skill plans broken into small concrete steps.",
            },
            "dev-user-085": {
                "grade": 1,
                "rationale": "Adjacent note-taking habit, but less central than projects, checkpoints, and examples.",
            },
        },
    },
    {
        "id": "user-home-cozy-practical-room",
        "scope": SPACE_USER,
        "workspace_uid": None,
        "query": "set up a cozy practical room with warm lighting, tidy storage, plants, and a reading spot",
        "relevance": {
            "dev-user-091": {
                "grade": 3,
                "rationale": "Directly describes warm lighting, natural textures, and lived-in rooms.",
            },
            "dev-user-095": {
                "grade": 3,
                "rationale": "Directly covers the comfortable reading spot, lamp, side table, and blanket.",
            },
            "dev-user-092": {
                "grade": 2,
                "rationale": "Covers the requested tidy storage, but only for entryway containment rather than the broader cozy room setup.",
            },
            "dev-user-094": {
                "grade": 2,
                "rationale": "Covers the requested plants, but only as window plant clusters rather than the room's lighting, storage, and reading needs.",
            },
            "dev-user-096": {
                "grade": 1,
                "rationale": "Adjacent tidy office context, but not the main cozy room setup requested.",
            },
        },
    },
    {
        "id": "user-pets-calm-durable-home-care",
        "scope": SPACE_USER,
        "workspace_uid": None,
        "query": "calm pet care setup with durable washable gear, enrichment, and safe household choices",
        "relevance": {
            "dev-user-071": {
                "grade": 3,
                "rationale": "Directly states calm, predictable pet care routines.",
            },
            "dev-user-072": {
                "grade": 3,
                "rationale": "Directly covers durable, washable, low-noise pet product recommendations.",
            },
            "dev-user-076": {
                "grade": 2,
                "rationale": "Covers the requested enrichment ideas, but not the calmer routine, durable gear, or household safety choices needed for grade 3.",
            },
            "dev-user-079": {
                "grade": 2,
                "rationale": "Covers requested household safety choices, but not the pet-care routine, washable gear, or enrichment pieces needed for grade 3.",
            },
            "dev-user-073": {
                "grade": 1,
                "rationale": "Adjacent home organization for pet supplies, but less central than care, gear, enrichment, and safety.",
            },
        },
    },
    {
        "id": "cedarledger-permission-boundaries",
        "scope": SPACE_WORKSPACE,
        "workspace_uid": "proj-fic-cedarledger-01",
        "query": "financial app permissions separating owners, clerks, support, and read-only reviewers",
        "relevance": {
            "dev-workspace-01-001": {
                "grade": 3,
                "rationale": "Directly defines tiered permissions for owners, managers, and clerks.",
            },
            "dev-workspace-01-003": {
                "grade": 3,
                "rationale": "Directly covers read-only reviewer invitations until owner confirmation.",
            },
            "dev-workspace-01-008": {
                "grade": 3,
                "rationale": "Directly describes support staff diagnostic access boundaries.",
            },
            "dev-workspace-01-005": {
                "grade": 2,
                "rationale": "Relevant supporting clerk restriction on tax, payout, and billing settings.",
            },
            "dev-workspace-01-006": {
                "grade": 1,
                "rationale": "Adjacent cached-capabilities bug involving wrong-account controls, but less central than role policy.",
            },
        },
    },
    {
        "id": "cedarledger-month-end-closeout-review",
        "scope": SPACE_WORKSPACE,
        "workspace_uid": "proj-fic-cedarledger-01",
        "query": "I need the month-end closeout notes that explain why approval is still blocked and what proof, bills, or duplicate imports are holding it up",
        "relevance": {
            "dev-workspace-01-022": {
                "grade": 3,
                "rationale": "Directly describes comparing expense proof with imported records.",
            },
            "dev-workspace-01-026": {
                "grade": 3,
                "rationale": "Directly names missing proof, open balances, duplicate imports, and pending records as differences.",
            },
            "dev-workspace-01-030": {
                "grade": 3,
                "rationale": "Directly states approval remains disabled until every imported record is resolved.",
            },
            "dev-workspace-01-025": {
                "grade": 2,
                "rationale": "Relevant because open customer bills inflated settled revenue during review.",
            },
            "dev-workspace-01-027": {
                "grade": 1,
                "rationale": "Adjacent uncleared supply charge filtering, but narrower than the overall closeout review query.",
            },
        },
    },
    {
        "id": "northstar-offline-sync-recovery",
        "scope": SPACE_WORKSPACE,
        "workspace_uid": "proj-fic-northstar-forms-01",
        "query": "offline form drafts queue, sync receipts, recovery after restart, and conflict handling",
        "relevance": {
            "dev-workspace-02-011": {
                "grade": 3,
                "rationale": "Directly says offline drafts stay on the device until submitted or deleted.",
            },
            "dev-workspace-02-012": {
                "grade": 3,
                "rationale": "Directly describes queued submissions preserving completion time and receiving synced-at timestamps.",
            },
            "dev-workspace-02-020": {
                "grade": 3,
                "rationale": "Directly calls for airplane-mode creation, restart recovery, handoff, and blocked item output testing.",
            },
            "dev-workspace-02-014": {
                "grade": 2,
                "rationale": "Relevant support because backlog processing continues even when one item hits a conflict.",
            },
            "dev-workspace-02-013": {
                "grade": 1,
                "rationale": "Adjacent receipt detail, but less broad than offline queue and recovery behavior.",
            },
        },
    },
    {
        "id": "northstar-final-review-required-fields",
        "scope": SPACE_WORKSPACE,
        "workspace_uid": "proj-fic-northstar-forms-01",
        "query": "final form review blocking missing required answers with summaries, focus, and conditional rules",
        "relevance": {
            "dev-workspace-02-021": {
                "grade": 3,
                "rationale": "Directly states final submission is blocked when a required answer is missing.",
            },
            "dev-workspace-02-026": {
                "grade": 3,
                "rationale": "Directly covers keyboard focus on the problem summary and links to blank questions.",
            },
            "dev-workspace-02-028": {
                "grade": 3,
                "rationale": "Directly explains conditional must-fill questions only block when active.",
            },
            "dev-workspace-02-022": {
                "grade": 2,
                "rationale": "Relevant support because error summaries separate blank mandatory responses from format problems.",
            },
            "dev-workspace-02-025": {
                "grade": 1,
                "rationale": "Adjacent bug about reopened offline drafts, but less central than the intended review behavior.",
            },
        },
    },
    {
        "id": "harborpilot-shared-gear-blockers",
        "scope": SPACE_WORKSPACE,
        "workspace_uid": "proj-fic-harborpilot-01",
        "query": "shared gear availability blocking pier repair work",
        "relevance": {
            "dev-workspace-03-011": {
                "grade": 3,
                "rationale": "Directly describes the west yard shared hoist as a single-capacity constraint.",
            },
            "dev-workspace-03-014": {
                "grade": 3,
                "rationale": "Directly describes tool conflicts preventing work from beginning.",
            },
            "dev-workspace-03-020": {
                "grade": 3,
                "rationale": "Directly describes shared heavy gear blocking calendar availability during transit.",
            },
            "dev-workspace-03-012": {
                "grade": 2,
                "rationale": "Relevant because pneumatic trailer maintenance affects tool availability.",
            },
            "dev-workspace-03-017": {
                "grade": 2,
                "rationale": "Relevant supporting context about reasons a tool cannot be assigned.",
            },
            "dev-workspace-03-010": {
                "grade": 1,
                "rationale": "Adjacent because dispatch output mentions required gear, but it is not about availability blocking work.",
            },
        },
    },
    {
        "id": "harborpilot-dispatch-scheduling-clashes",
        "scope": SPACE_WORKSPACE,
        "workspace_uid": "proj-fic-harborpilot-01",
        "query": "Help me find the dispatch scheduling notes about fitting repair crews into available windows without missing urgent jobs or wasting idle gaps",
        "relevance": {
            "dev-workspace-03-001": {
                "grade": 3,
                "rationale": "Directly covers visible repair time blocks and schedule clashes on the same pier.",
            },
            "dev-workspace-03-003": {
                "grade": 3,
                "rationale": "Directly covers dispatch board ordering for urgent, routine, and low-priority repairs.",
            },
            "dev-workspace-03-008": {
                "grade": 3,
                "rationale": "Directly describes idle gaps between jobs and how to fit small tasks without displacing larger work.",
            },
            "dev-workspace-03-002": {
                "grade": 2,
                "rationale": "Covers requested crew arrival windows, but not repair block clashes, urgent ordering, or idle-gap fitting needed for grade 3.",
            },
            "dev-workspace-03-004": {
                "grade": 1,
                "rationale": "Adjacent time-window filter behavior, but narrower than the full scheduling question.",
            },
        },
    },
    {
        "id": "harborpilot-shift-handoff-blockers",
        "scope": SPACE_WORKSPACE,
        "workspace_uid": "proj-fic-harborpilot-01",
        "query": "shift handoff showing blocked or ready jobs, safety holds, permits, and unresolved access issues",
        "relevance": {
            "dev-workspace-03-022": {
                "grade": 3,
                "rationale": "Directly says handoff notes show ready, blocked, or inspection-waiting job states.",
            },
            "dev-workspace-03-028": {
                "grade": 3,
                "rationale": "Directly separates missing permits, incomplete checklists, and inspection holds with owners and next actions.",
            },
            "dev-workspace-03-027": {
                "grade": 2,
                "rationale": "Relevant support because coordinator summaries include unresolved access issues.",
            },
            "dev-workspace-03-021": {
                "grade": 2,
                "rationale": "Relevant safety-hold handoff detail about Pier 4 fender repair.",
            },
            "dev-workspace-03-024": {
                "grade": 1,
                "rationale": "Adjacent turnover summary context, but less specifically about blocker categories and access issues.",
            },
        },
    },
    {
        "id": "northstar-form-builder-conditional-authoring",
        "scope": SPACE_WORKSPACE,
        "workspace_uid": "proj-fic-northstar-forms-01",
        "query": "I'm looking for form-builder guidance on authoring conditional sections safely, including repeatable areas, stable field IDs, and warnings before designers publish",
        "relevance": {
            "dev-workspace-02-003": {
                "grade": 3,
                "rationale": "Directly says conditional display rules should appear beside the affected prompt.",
            },
            "dev-workspace-02-006": {
                "grade": 3,
                "rationale": "Directly covers warnings for mandatory items inside conditional areas.",
            },
            "dev-workspace-02-005": {
                "grade": 2,
                "rationale": "Relevant support about repeatable sections and preview boundaries.",
            },
            "dev-workspace-02-002": {
                "grade": 2,
                "rationale": "Relevant support because immutable field IDs protect saved submissions after label changes.",
            },
            "dev-workspace-02-007": {
                "grade": 1,
                "rationale": "Adjacent orphan-rule bug after removing a controlling question, but less central than authoring design behavior.",
            },
        },
    },
)
