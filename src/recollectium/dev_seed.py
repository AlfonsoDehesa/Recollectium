"""Seed data helpers for the optional development memory database."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from recollectium.embeddings import EmbeddingProvider, chunk_text_for_profile
from recollectium.models import Memory, SPACE_USER, SPACE_WORKSPACE
from recollectium.storage import SQLiteMemoryStore

DEV_SEED_USER_MEMORY_COUNT = 100
DEV_SEED_WORKSPACE_COUNT = 3
DEV_SEED_WORKSPACE_MEMORY_COUNT = 30
DEV_SEED_TOPIC_COUNT = 10
DEV_SEED_TOTAL_WORKSPACE_MEMORIES = (
    DEV_SEED_WORKSPACE_COUNT * DEV_SEED_WORKSPACE_MEMORY_COUNT
)
DEV_SEED_TIMESTAMP = "2026-01-01T00:00:00Z"
DEV_SEED_USER_TOPICS: tuple[str, ...] = (
    "travel",
    "transportation",
    "videogames",
    "books",
    "cooking",
    "fitness",
    "music",
    "pets",
    "learning",
    "home style",
)
DEV_SEED_PROJECTS: tuple[dict[str, str], ...] = (
    {"uid": "proj_fic_cedarledger_01", "name": "CedarLedger"},
    {"uid": "proj_fic_northstar_forms_01", "name": "Northstar Forms"},
    {"uid": "proj_fic_harborpilot_01", "name": "HarborPilot"},
)
USER_MEMORY_TYPES: tuple[str, ...] = (
    "fact",
    "preference",
    "personal_fact",
    "social_context",
    "goal",
    "communication_style",
    "note",
)
WORKSPACE_MEMORY_TYPES: tuple[str, ...] = (
    "fact",
    "decision",
    "task_context",
    "configuration",
    "bug_finding",
    "note",
)

USER_FACTS_BY_TOPIC: tuple[tuple[str, ...], ...] = (
    (
        "The user prefers planning trips with a loose daily itinerary rather than a rigid hour-by-hour schedule.",
        "The user likes staying in walkable neighborhoods where restaurants, transit, and parks are nearby.",
        "The user usually checks local public transportation options before deciding whether to rent a car on a trip.",
        "The user enjoys visiting museums, bookstores, and historic districts when traveling to a new city.",
        "The user prefers direct flights when the price difference is reasonable, even if the departure time is less convenient.",
        "The user likes to keep one unscheduled afternoon during longer trips for rest or spontaneous exploring.",
        "The user tends to pack light and prefers carry-on luggage for trips under a week.",
        "The user likes trying local coffee shops and bakeries while traveling.",
        "The user prefers travel recommendations that include practical details like transit time, reservation needs, and expected cost.",
        "The user usually saves a short list of backup restaurants or activities in case the original plan falls through.",
    ),
    (
        "The user prefers taking trains over short flights when the total travel time is comparable.",
        "The user likes navigation advice that includes both driving and public transit options when available.",
        "The user is comfortable using rideshare services but prefers them as a backup rather than the default option.",
        "The user generally prefers routes with fewer transfers, even if they take a few extra minutes.",
        "The user likes to know parking availability and cost before driving to a busy area.",
        "The user prefers walking for short city trips when the route is safe and weather is reasonable.",
        "The user tends to check traffic before leaving for appointments or airport trips.",
        "The user values reliable transportation plans over the absolute cheapest option.",
        "The user prefers arriving early for trains, buses, and flights to avoid feeling rushed.",
        "The user likes bike-share or scooter options for short trips in cities with good protected lanes.",
    ),
    (
        "The user enjoys story-driven games with strong atmosphere and memorable characters.",
        "The user prefers games that allow flexible difficulty settings rather than forcing a single challenge level.",
        "The user likes open-world games when exploration feels rewarding instead of checklist-driven.",
        "The user tends to avoid multiplayer games that require frequent voice chat with strangers.",
        "The user enjoys puzzle mechanics when they are integrated naturally into the game world.",
        "The user prefers games with clear save systems and dislikes losing progress because of unclear checkpoints.",
        "The user likes recommendations that mention approximate playtime and whether a game is better in short sessions or long sessions.",
        "The user enjoys cozy or low-pressure games as a way to unwind after work.",
        "The user is interested in indie games with distinctive art direction or unusual mechanics.",
        "The user prefers controller-friendly games when playing on a couch or TV setup.",
    ),
    (
        "The user enjoys fiction with thoughtful character development and a strong sense of place.",
        "The user prefers book recommendations that include a brief reason why the book fits their interests.",
        "The user likes nonfiction that explains complex topics clearly without feeling like a textbook.",
        "The user often alternates between lighter reads and more demanding books to avoid burnout.",
        "The user enjoys science fiction when it focuses on human consequences rather than only technology.",
        "The user appreciates mysteries that play fair with the reader and avoid overly convenient twists.",
        "The user prefers practical reading lists with three to five strong options instead of long catalogs.",
        "The user likes books with concise chapters because they are easier to read in short sessions.",
        "The user is interested in memoirs when they connect personal stories to broader cultural or historical context.",
        "The user prefers spoiler-free summaries when deciding whether to read a novel.",
    ),
    (
        "The user prefers weeknight dinners that can be made in about 30 minutes with minimal cleanup.",
        "The user likes Mediterranean-inspired meals with vegetables, grains, olive oil, and simple proteins.",
        "The user usually keeps pantry staples like pasta, rice, beans, canned tomatoes, and basic spices on hand.",
        "The user enjoys cooking at home but appreciates recipes with clear steps and flexible ingredient substitutions.",
        "The user prefers savory breakfasts over sweet breakfasts when they have time to cook.",
        "The user likes batch-cooking soups, stews, or grain bowls for easy lunches during the week.",
        "The user is interested in improving knife skills and becoming faster at prep work.",
        "The user prefers meals that reheat well for leftovers.",
        "The user enjoys trying new recipes but does not want overly complicated techniques on busy days.",
        "The user likes balanced meals that include protein, vegetables, and a satisfying carbohydrate.",
    ),
    (
        "The user prefers a practical fitness routine that fits into a normal workweek.",
        "The user likes walking as a low-pressure way to stay active and clear their head.",
        "The user is more consistent with workouts when they are planned in advance.",
        "The user prefers strength training routines that use simple movements and clear progression.",
        "The user wants fitness suggestions that avoid extreme dieting or all-or-nothing goals.",
        "The user likes short mobility sessions for stretching tight shoulders, hips, and back.",
        "The user prefers workouts that can be done at home when they cannot get to a gym.",
        "The user tracks progress best through consistency, energy levels, and strength improvements rather than only weight.",
        "The user appreciates beginner-friendly explanations for new exercises and proper form.",
        "The user is interested in building sustainable habits instead of chasing quick results.",
    ),
    (
        "The user likes having different playlists for focus, errands, workouts, and relaxing at home.",
        "The user enjoys discovering new artists through recommendations based on songs they already like.",
        "The user prefers music suggestions that include a short explanation of why they might fit the mood.",
        "The user often listens to instrumental or low-vocal music while doing focused work.",
        "The user likes upbeat music for cleaning, cooking, and other household tasks.",
        "The user appreciates both older classics and newer releases when exploring a genre.",
        "The user prefers playlists that have a consistent mood rather than jumping sharply between styles.",
        "The user likes acoustic or mellow music in the evening.",
        "The user is open to music from different countries and languages when the vibe matches the request.",
        "The user enjoys learning small bits of context about an album, artist, or genre.",
    ),
    (
        "The user likes practical pet care advice that focuses on routines, safety, and comfort.",
        "The user prefers pet product recommendations that are durable, easy to clean, and not overly expensive.",
        "The user believes pets do best with predictable feeding, play, and rest routines.",
        "The user likes enrichment ideas that can be done at home without complicated supplies.",
        "The user prefers calm, positive training approaches for pets.",
        "The user appreciates reminders to check with a veterinarian for health symptoms or diet changes.",
        "The user likes keeping pet areas tidy with washable blankets, simple storage, and regular cleaning.",
        "The user is interested in ways to reduce pet boredom when the household is busy.",
        "The user prefers travel or boarding advice that prioritizes the pet's comfort and stress level.",
        "The user likes tips for making a home more pet-friendly without making it feel cluttered.",
    ),
    (
        "The user learns best when a topic is broken into small steps with examples.",
        "The user prefers explanations that start with the big picture before going into details.",
        "The user likes study plans that include short daily sessions rather than long occasional cramming.",
        "The user appreciates practice questions or exercises after learning a new concept.",
        "The user prefers honest feedback that points out mistakes clearly and suggests how to improve.",
        "The user likes comparing a new idea to something familiar when trying to understand it.",
        "The user is interested in building long-term learning habits instead of only preparing for one task.",
        "The user prefers concise summaries they can review later.",
        "The user likes recommendations for books, courses, or tutorials when they are matched to their current level.",
        "The user benefits from checklists and milestones when working through a complex subject.",
    ),
    (
        "The user prefers a clean, comfortable home style with warm lighting and uncluttered surfaces.",
        "The user likes neutral colors with a few accent pieces rather than very bold rooms.",
        "The user prefers furniture that is practical, comfortable, and easy to maintain.",
        "The user likes storage solutions that reduce visible clutter without making items hard to access.",
        "The user enjoys adding plants or natural textures to make a room feel more relaxed.",
        "The user prefers decorating ideas that can be done gradually instead of requiring a full room makeover.",
        "The user likes cozy details such as soft throws, rugs, and warm-toned lamps.",
        "The user prefers layouts that make everyday routines easier and keep walkways open.",
        "The user appreciates budget-friendly home style suggestions that still look intentional.",
        "The user likes rooms that feel lived-in and personal without being crowded.",
    ),
)

PROJECT_MEMORIES_BY_UID: dict[str, tuple[str, ...]] = {
    "proj_fic_cedarledger_01": (
        "CedarLedger is a bookkeeping app for independent workshops that need simple job, invoice, and expense tracking.",
        "The project keeps sample businesses generic, with no real company names, bank details, tax IDs, or customer contact records.",
        "The dashboard groups open invoices, recent expenses, and unpaid workshop jobs into separate summary cards.",
        "A decision note says sample currency values are small round numbers so screenshots are easy to read.",
        "The transaction importer only reads local CSV fixtures and does not connect to external financial services.",
        "A bug note says invoice totals were recalculated twice after editing a line item quantity.",
        "The settings fixture stores a demo tax label, default invoice terms, and a preferred date format.",
        "The project uses deterministic invoice IDs so snapshot tests remain stable across runs.",
        "A task remains to add a keyboard shortcut for marking a draft invoice ready to send.",
        "The sample expense categories are materials, tools, utilities, rent, insurance, and training.",
        "A design note prefers clear tables with compact filters over decorative financial charts.",
        "The app should warn when an expense is missing a category before it appears in a monthly report.",
        "The demo workspace has three workshop profiles named North Bench, Pine Room, and Sawdust Studio.",
        "A known issue says the unpaid badge can overlap long workshop names on narrow screens.",
        "The export feature writes local JSON and CSV files with generated placeholder records only.",
        "The project glossary defines a job as a billable workshop activity tied to one or more invoice lines.",
        "A scenario test covers splitting one materials receipt across two active jobs.",
        "The monthly report should separate reimbursable materials from normal operating expenses.",
        "The mock activity log stores action types and timestamps but no IP addresses or device identifiers.",
        "A task asks for an empty state that explains how to add the first invoice in plain language.",
        "The fixture includes overdue, paid, draft, and partially paid invoice examples for UI coverage.",
        "The project decided to avoid payroll, lending, or tax filing features in the seeded demo.",
        "The search query clamp should return the sample tools expense before unrelated invoice notes.",
        "The local preferences file tracks the selected report period and sidebar collapse state.",
        "The accessibility note requires status badges to include text, not color alone.",
        "A bug note says deleting a job left its invoice count cached until the list was refreshed.",
        "The sample onboarding checklist has steps for adding a job, recording an expense, and drafting an invoice.",
        "The report builder starts with a simple profit and loss view for the current demo month.",
        "The app should show a confirmation before archiving a workshop profile with open invoices.",
        "A release checklist item verifies that seeded bookkeeping records are fictional and public-safe.",
    ),
    "proj_fic_northstar_forms_01": (
        "Northstar Forms is an offline-friendly form builder for teams that collect structured field notes.",
        "The project stores all sample forms locally and avoids real survey responses, names, addresses, or contact details.",
        "The builder supports short text, long text, number, checkbox, select, date, and photo-placeholder fields.",
        "A decision note says drafts must autosave locally before any sync status appears in the interface.",
        "The demo includes three form templates for equipment checks, site observations, and intake notes.",
        "A bug note says duplicated sections kept the original section title in the navigation sidebar.",
        "The fixture uses generated response IDs and fixed timestamps for deterministic tests.",
        "The sync simulator can be toggled between offline, pending, and complete without calling a network service.",
        "A task remains to add drag handles for reordering fields inside a section.",
        "The preview screen should show validation errors without leaving the form builder.",
        "The project glossary defines a packet as a local bundle of completed forms waiting for review.",
        "A known issue says required field markers are too subtle in high contrast mode.",
        "The export workflow writes a local archive with form schemas, responses, and attachment placeholders.",
        "The app should reject duplicate field keys within the same form schema.",
        "The sample response set includes complete, incomplete, and review-needed states.",
        "A design note keeps the left sidebar stable so users do not lose their place during edits.",
        "The settings fixture stores the default language, autosave interval, and local retention period.",
        "A scenario test covers filling a form while offline and reviewing it after reconnect simulation.",
        "The form renderer should preserve field order exactly as defined by the schema.",
        "The project decided that photo fields use placeholder filenames instead of real image files.",
        "The search query generator should rank form titles above individual response notes.",
        "A task asks for a concise empty state that explains how to create the first form template.",
        "The review queue groups submissions by template, completion status, and last edited time.",
        "The mock activity log records schema edits and review state changes without user emails.",
        "A bug note says removing a select option did not update existing validation warnings until reload.",
        "The accessibility note requires clear labels for all inputs and keyboard support for field reordering.",
        "The local backup routine keeps the most recent demo archive and removes older generated archives.",
        "The app should display a clear warning before deleting a form template with saved responses.",
        "The fixture includes one intentionally incomplete response to exercise validation messaging.",
        "A release checklist item verifies that seeded form data contains no private field reports.",
    ),
    "proj_fic_harborpilot_01": (
        "HarborPilot is a scheduling and task board for repair crews coordinating jobs across shared equipment.",
        "The project uses fabricated crews, jobs, and assets with no real addresses, phone numbers, customers, or facility names.",
        "The board groups work into requested, scheduled, in progress, blocked, and completed columns.",
        "A decision note says crews should see the next two days by default instead of a full month calendar.",
        "The demo includes job types for inspection, repair, cleanup, parts pickup, and follow-up review.",
        "A bug note says dragging a blocked task briefly cleared its blocker reason before the save completed.",
        "The fixture uses generated crew initials and stable job numbers for repeatable tests.",
        "The scheduler warns when the same crew is assigned to overlapping jobs.",
        "A task remains to add a compact print view for the daily crew plan.",
        "The sample equipment list includes generic lifts, carts, tool kits, and diagnostic tablets.",
        "A design note prefers clear priority labels over dense color coding on the task cards.",
        "The app should keep unscheduled tasks visible until a coordinator assigns a date and crew.",
        "The demo workspace has three crews named Dockside, Ridgeline, and Maple Shift.",
        "A known issue says the completion filter resets when switching from board view to calendar view.",
        "The export feature writes local schedule snapshots with placeholder job and crew data only.",
        "The project glossary defines a hold as a task paused until parts, access, or review is available.",
        "A scenario test covers moving a repair job from blocked to scheduled after parts arrive.",
        "The daily summary should list high priority tasks before routine follow-up work.",
        "The mock activity log records card moves and status changes without location traces or staff contacts.",
        "A task asks for an empty state that helps coordinators create the first repair job.",
        "The fixture includes urgent, normal, waiting, and completed examples for each board column.",
        "The project decided not to model payroll, live vehicle tracking, or customer billing in the seed data.",
        "The search query lift should return the equipment availability note before unrelated task comments.",
        "The local preferences file tracks the selected board view and whether completed tasks are hidden.",
        "The accessibility note requires priority, status, and blocked labels to be readable without color.",
        "A bug note says archiving a crew did not remove its name from one stale assignment filter.",
        "The onboarding checklist has steps for adding a task, assigning a crew, and resolving a blocker.",
        "The schedule conflict panel starts with a simple list of overlapping crew assignments.",
        "The app should show a confirmation before deleting a task with activity history.",
        "A release checklist item verifies that seeded scheduling data is fictional and safe for public screenshots.",
    ),
}


def _unlink_sqlite_files(db_path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(f"{db_path}{suffix}")
        if candidate.exists():
            candidate.unlink()


def _insert_seed_memory(
    store: SQLiteMemoryStore,
    provider: EmbeddingProvider,
    memory: Memory,
) -> None:
    chunks = chunk_text_for_profile(memory.content, provider.embedding_profile)
    chunk_embeddings = [(chunk, provider.embed(chunk.text)) for chunk in chunks]
    store.insert_memory(
        memory,
        chunk_embeddings[0][1],
        provider.embedding_profile,
    )
    store.replace_memory_chunks(
        memory_id=memory.id,
        embedding_profile=provider.embedding_profile,
        chunk_embeddings=chunk_embeddings,
    )


def _user_seed_memory(index: int) -> Memory:
    topic_index = index // 10
    fact_index = index % 10
    topic = DEV_SEED_USER_TOPICS[topic_index]
    ordinal = index + 1
    fact = USER_FACTS_BY_TOPIC[topic_index][fact_index]
    return Memory(
        id=f"dev-user-{ordinal:03d}",
        space=SPACE_USER,
        type=USER_MEMORY_TYPES[index % len(USER_MEMORY_TYPES)],
        content=fact,
        metadata={
            "dev_seed": True,
            "fictional": True,
            "dev_topic": topic,
            "dev_topic_index": topic_index,
            "dev_ordinal": ordinal,
        },
        source="dev-seed",
        confidence=0.75,
        created_at=DEV_SEED_TIMESTAMP,
        updated_at=DEV_SEED_TIMESTAMP,
    )


def _workspace_seed_memory(workspace_index: int, memory_index: int) -> Memory:
    project = DEV_SEED_PROJECTS[workspace_index]
    workspace_uid = project["uid"]
    project_name = project["name"]
    ordinal = memory_index + 1
    content = PROJECT_MEMORIES_BY_UID[workspace_uid][memory_index]
    return Memory(
        id=f"dev-workspace-{workspace_index + 1:02d}-{ordinal:03d}",
        space=SPACE_WORKSPACE,
        workspace_uid=workspace_uid,
        type=WORKSPACE_MEMORY_TYPES[memory_index % len(WORKSPACE_MEMORY_TYPES)],
        content=content,
        metadata={
            "dev_seed": True,
            "fictional": True,
            "dev_project": project_name,
            "dev_project_name": project_name,
            "dev_project_uid": workspace_uid,
            "dev_workspace_index": workspace_index,
            "dev_ordinal": ordinal,
        },
        source="dev-seed",
        confidence=0.75,
        created_at=DEV_SEED_TIMESTAMP,
        updated_at=DEV_SEED_TIMESTAMP,
    )


def seeded_dev_database_is_initialized(db_path: Path | str) -> bool:
    """Return True when *db_path* already has the complete seeded dev fixture."""
    db_path = Path(db_path)
    if not db_path.exists():
        return False
    store = SQLiteMemoryStore(db_path)
    user_memories = store.list_memories(space=SPACE_USER, include_archived=True)
    workspace_memories = store.list_memories(
        space=SPACE_WORKSPACE, include_archived=True
    )
    topics = {
        memory.metadata.get("dev_topic")
        for memory in user_memories
        if memory.metadata.get("dev_seed") is True
    }
    expected_workspace_uids = {project["uid"] for project in DEV_SEED_PROJECTS}
    workspace_uids = set(store.list_workspace_uids(include_archived=True))
    workspace_counts = Counter(memory.workspace_uid for memory in workspace_memories)
    expected_workspace_counts = {
        project["uid"]: DEV_SEED_WORKSPACE_MEMORY_COUNT for project in DEV_SEED_PROJECTS
    }
    user_contents = [memory.content for memory in user_memories]
    workspace_contents = [memory.content for memory in workspace_memories]
    all_contents = user_contents + workspace_contents
    return (
        len(user_memories) == DEV_SEED_USER_MEMORY_COUNT
        and len(workspace_memories) == DEV_SEED_TOTAL_WORKSPACE_MEMORIES
        and workspace_uids == expected_workspace_uids
        and workspace_counts == expected_workspace_counts
        and len(topics) == DEV_SEED_TOPIC_COUNT
        and len(set(user_contents)) == DEV_SEED_USER_MEMORY_COUNT
        and len(set(workspace_contents)) == DEV_SEED_TOTAL_WORKSPACE_MEMORIES
        and len(set(all_contents))
        == DEV_SEED_USER_MEMORY_COUNT + DEV_SEED_TOTAL_WORKSPACE_MEMORIES
        and all(
            not content.startswith("Fictional dev user") for content in user_contents
        )
        and all(" fact 1:" not in content for content in user_contents)
        and all(
            "fictional project memory" not in content for content in workspace_contents
        )
        and all(memory.metadata.get("dev_seed") is True for memory in user_memories)
        and all(memory.metadata.get("fictional") is True for memory in user_memories)
        and all(
            memory.metadata.get("dev_seed") is True for memory in workspace_memories
        )
        and all(
            memory.metadata.get("fictional") is True for memory in workspace_memories
        )
        and all(
            memory.metadata.get("dev_project_name")
            and memory.metadata.get("dev_project_uid") == memory.workspace_uid
            for memory in workspace_memories
        )
    )


def reset_seeded_dev_database(
    db_path: Path | str,
    embedding_provider: EmbeddingProvider,
) -> dict[str, object]:
    """Replace *db_path* with the canonical seeded development database."""
    resolved_db_path = Path(db_path).expanduser()
    resolved_db_path.parent.mkdir(parents=True, exist_ok=True)
    _unlink_sqlite_files(resolved_db_path)
    store = SQLiteMemoryStore(resolved_db_path)

    for index in range(DEV_SEED_USER_MEMORY_COUNT):
        _insert_seed_memory(store, embedding_provider, _user_seed_memory(index))

    for workspace_index in range(DEV_SEED_WORKSPACE_COUNT):
        for memory_index in range(DEV_SEED_WORKSPACE_MEMORY_COUNT):
            _insert_seed_memory(
                store,
                embedding_provider,
                _workspace_seed_memory(workspace_index, memory_index),
            )

    return {
        "status": "reset",
        "database": str(resolved_db_path),
        "user_memories": DEV_SEED_USER_MEMORY_COUNT,
        "workspace_memories": DEV_SEED_TOTAL_WORKSPACE_MEMORIES,
        "workspaces": DEV_SEED_WORKSPACE_COUNT,
        "topics": DEV_SEED_TOPIC_COUNT,
    }


def ensure_seeded_dev_database(
    db_path: Path | str,
    embedding_provider: EmbeddingProvider,
) -> dict[str, object] | None:
    """Create or refresh the seeded development database when it is missing/stale."""
    resolved_db_path = Path(db_path).expanduser()
    if seeded_dev_database_is_initialized(resolved_db_path):
        return None
    return reset_seeded_dev_database(resolved_db_path, embedding_provider)
