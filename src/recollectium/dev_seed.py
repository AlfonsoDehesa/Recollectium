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
    {"uid": "proj-fic-cedarledger-01", "name": "CedarLedger"},
    {"uid": "proj-fic-northstar-forms-01", "name": "Northstar Forms"},
    {"uid": "proj-fic-harborpilot-01", "name": "HarborPilot"},
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
        "The user prefers trips that leave room for wandering through neighborhoods instead of filling every day with reservations.",
        "The user likes choosing hotels or rentals near reliable transit, casual restaurants, and a grocery stop for simple supplies.",
        "The user usually compares train routes, airport transfers, and walking distances before deciding where to stay.",
        "The user enjoys travel days more when there is enough buffer time to get coffee, find the platform, and avoid rushing.",
        "The user likes visiting local markets early in a trip. They use them to get a feel for the neighborhood and pick up snacks for later.",
        "The user prefers packing a small capsule wardrobe for city trips. They would rather do a quick laundry load than check a large bag.",
        "The user appreciates destination advice that mentions when attractions need advance tickets. They also like knowing which sights are better saved for a rainy day.",
        "The user tends to plan one anchor activity per travel day and keep the rest flexible. A museum, hike, or food tour is enough structure. They do not like feeling locked into a minute-by-minute itinerary.",
        "The user likes trying regional breakfasts and simple neighborhood cafes while traveling. They often save fancier meals for lunch instead of dinner. This helps keep evenings relaxed after a full day out.",
        "The user keeps a short backup list of indoor activities, quiet parks, and casual restaurants for each trip. They find it easier to change plans when options are already saved. Practical recommendations with transit time, approximate cost, and reservation details are most useful.",
    ),
    (
        "The user prefers taking trains over short flights when the total travel time is comparable.",
        "The user generally chooses routes with fewer transfers, even when a simpler route takes a few extra minutes.",
        "The user tends to check traffic before leaving for appointments, station pickups, and airport trips.",
        "The user likes bike-share or scooter options for short city trips when protected lanes and clear parking rules are available.",
        "The user likes route suggestions that compare driving, transit, and walking when those options are practical. They appreciate knowing the tradeoff in time, cost, and hassle.",
        "The user likes to check parking availability and likely cost before driving into a busy neighborhood. They would rather know about garages, meters, or permit zones ahead of time.",
        "The user values reliable transportation plans over the absolute cheapest option. They are willing to pay a little more to avoid missed connections or stressful timing.",
        "The user is comfortable using rideshare services as a backup plan, especially late at night or in bad weather. They still prefer not to make rideshare the default for every trip. If transit is reliable, they would rather use it.",
        "The user prefers walking for short city trips when sidewalks feel safe and the weather is reasonable. They enjoy routes that pass parks, cafes, or interesting storefronts. They dislike walking plans that require crossing confusing highways or poorly lit areas.",
        "The user prefers arriving early for trains, buses, and flights so they do not feel rushed. They like having a small buffer for ticket machines, platform changes, or security lines. For important trips, they would rather wait calmly than cut it close.",
    ),
    (
        "The user enjoys story-driven games with strong atmosphere and memorable characters.",
        "The user prefers flexible difficulty settings because they like adjusting the challenge to fit their mood.",
        "The user enjoys puzzle mechanics when they are integrated naturally into the game world.",
        "The user likes recommendations that mention approximate playtime and whether a game is better in short sessions or long sessions.",
        "The user likes open-world games when exploration feels rewarding instead of checklist-driven. They usually appreciate maps that leave room for curiosity and discovery.",
        "The user tends to avoid multiplayer games that require frequent voice chat with strangers. They are more comfortable with cooperative modes that can be played quietly or with simple pings.",
        "The user enjoys cozy or low-pressure games as a way to unwind after work. They prefer gentle goals, pleasant music, and systems that do not punish taking a break.",
        "The user prefers games with clear save systems and dislikes losing progress because of unclear checkpoints. They often check save behavior before starting a long session. Autosaves are helpful, but manual save options are still preferred when possible.",
        "The user is interested in indie games with distinctive art direction or unusual mechanics. They are willing to try a rough edge or two if the central idea feels fresh. They especially appreciate games that do one focused thing well.",
        "The user prefers controller-friendly games when playing on a couch or TV setup. They also like readable UI text, adjustable subtitles, and menus that work cleanly without a mouse. If a game is awkward on a controller, they usually save it for the desk setup.",
    ),
    (
        "The user enjoys novels with thoughtful character development and a strong sense of place.",
        "The user prefers book recommendations that include a brief spoiler-free reason why each title fits their interests.",
        "The user likes nonfiction that explains complex topics clearly without sounding like a textbook.",
        "The user appreciates concise chapters because they make it easier to read during short breaks.",
        "The user often alternates between lighter reads and more demanding books to avoid burnout. They like having one comforting option available after finishing something dense.",
        "The user enjoys science fiction when it focuses on human consequences instead of only technology. They prefer speculative ideas that still leave room for believable emotions and relationships.",
        "The user appreciates mysteries that play fair with the reader and avoid overly convenient twists. They like clues to feel visible in hindsight rather than hidden by the author.",
        "The user keeps a small to-read list and prefers three to five strong options over long catalogs. They are more likely to start a book when the recommendation includes tone, pacing, and approximate length. If a series is suggested, they want to know whether the first book stands on its own.",
        "The user is interested in memoirs when they connect personal stories to broader cultural or historical context. They prefer reflective writing over celebrity gossip or shock value. A grounded narrative voice matters more to them than dramatic events.",
        "The user likes reading before bed but avoids books that are too tense late at night. They usually save thrillers, heavy nonfiction, and emotionally intense novels for weekends or earlier in the day. Calmer literary fiction, essays, or cozy mysteries work better for evening reading.",
    ),
    (
        "The user prefers weeknight dinners that can be made in about 30 minutes with minimal cleanup.",
        "The user likes Mediterranean-inspired meals with vegetables, grains, olive oil, and simple proteins.",
        "The user usually keeps pantry staples like pasta, rice, beans, canned tomatoes, and basic spices on hand.",
        "The user prefers savory breakfasts over sweet breakfasts when they have time to cook.",
        "The user enjoys cooking at home and appreciates recipes with clear steps. They like when substitutions are offered for common ingredients they may already have.",
        "The user likes batch-cooking soups, stews, or grain bowls for easy lunches during the week. Meals that reheat well are especially useful for their routine.",
        "The user enjoys trying new recipes but does not want overly complicated techniques on busy days. They are more likely to attempt a project recipe on a quiet weekend.",
        "The user is interested in improving knife skills and becoming faster at prep work. They would like practical guidance on safe hand position, even cuts, and efficient cleanup. Short practice drills are more appealing than formal culinary lessons.",
        "The user likes balanced meals that include protein, vegetables, and a satisfying carbohydrate. They prefer recipes that feel filling without requiring heavy sauces or a long ingredient list. A simple side salad or roasted vegetable is usually enough to round out dinner.",
        "The user often plans meals around what needs to be used up in the refrigerator. They appreciate suggestions that combine leftover herbs, half-used vegetables, or cooked grains into something intentional. They dislike wasting food but do not want every meal to feel like a compromise.",
    ),
    (
        "The user prefers a practical fitness routine that fits into a normal workweek.",
        "The user likes strength training plans that explain the purpose of each movement.",
        "The user enjoys walks as a low-pressure way to stay active and clear their head.",
        "The user prefers progress tracking that focuses on consistency rather than perfection.",
        "The user likes workouts that include warmup guidance. They are more likely to follow a plan when the first few minutes feel approachable.",
        "The user prefers simple equipment options such as dumbbells, bands, or bodyweight movements. They do not want a routine that depends on a crowded gym.",
        "The user appreciates mobility exercises for shoulders, hips, and back comfort. Short routines are easier for them to keep up with than long stretching sessions.",
        "The user prefers fitness advice that respects rest days. They want to avoid turning every missed workout into a failure. A sustainable plan matters more than a perfect streak.",
        "The user likes cardio options that can be adjusted for energy level. A brisk walk, easy bike ride, or short interval session can all fit depending on the day. Clear intensity cues help them choose the right version.",
        "The user is interested in building strength without chasing extreme goals. They prefer steady improvements, good form, and fewer aches. Plans with realistic recovery time feel more trustworthy.",
    ),
    (
        "The user likes having different playlists for focus, errands, workouts, and relaxing at home.",
        "The user enjoys discovering new artists through recommendations based on songs they already like.",
        "The user often listens to instrumental or low-vocal music while doing focused work.",
        "The user likes upbeat music for cleaning, cooking, and other household tasks.",
        "The user prefers music suggestions that include a short explanation of why they might fit the mood. They are more likely to try a track when the recommendation mentions tempo, vocals, and overall energy.",
        "The user appreciates both older classics and newer releases when exploring a genre. They like hearing how newer songs connect to earlier influences without getting a lecture.",
        "The user prefers playlists that have a consistent mood rather than jumping sharply between styles. Smooth transitions matter more to them than strict genre purity.",
        "The user likes acoustic or mellow music in the evening. They usually avoid aggressive drums or very bright production late at night. Calm vocals, soft guitar, or gentle piano fit that part of the day best.",
        "The user is open to music from different countries and languages when the vibe matches the request. They do not need to understand every lyric to enjoy a song. A brief note about the style or region helps them decide what to play next.",
        "The user enjoys learning small bits of context about an album, artist, or genre. They prefer a few memorable details over a long history lesson. Release era, standout instruments, and listening mood are the most useful context for them.",
    ),
    (
        "The user likes pet care routines that are calm, predictable, and easy to maintain.",
        "The user prefers pet product recommendations that mention durability, washability, and noise level.",
        "The user enjoys homes with practical spaces for leashes, brushes, treats, and cleanup supplies.",
        "The user likes pet advice that balances comfort, enrichment, and safety without being overly fussy.",
        "The user prefers feeding reminders that are simple and consistent. They are easier to follow when they include morning and evening checkpoints.",
        "The user likes enrichment ideas such as puzzle feeders, rotating toys, and short training games. They prefer activities that can fit into a normal day.",
        "The user appreciates pet-friendly travel tips that mention lodging rules, quiet walking routes, and nearby green space. They dislike advice that assumes every pet is comfortable in crowded places.",
        "The user prefers pet areas that are tidy but not sterile. A washable blanket, a toy basket, and easy access to water make the space feel intentional. They like setups that work for both daily life and guests.",
        "The user is careful about plants, cleaners, and small objects around pets. New items should be checked before they are left within reach. Safety matters more than matching the room perfectly.",
        "The user likes training approaches based on patience and short practice sessions. Clear cues, small rewards, and breaks help keep the routine positive. They avoid methods that make a pet seem scared or confused.",
    ),
    (
        "The user prefers learning plans that break a skill into small, concrete steps.",
        "The user likes tutorials that include one practical exercise after each concept.",
        "The user keeps better momentum when lessons have clear checkpoints and visible progress.",
        "The user prefers explanations that start with an example before introducing formal terminology.",
        "The user likes taking notes in their own words after finishing a lesson. This helps them notice what they actually understood.",
        "The user enjoys learning through small projects that produce something useful. They find abstract drills easier to tolerate when there is a visible outcome.",
        "The user prefers review sessions that revisit earlier material without feeling punitive. Gentle repetition helps them retain details over time.",
        "The user gets discouraged by courses that skip setup details. They appreciate instructions that mention prerequisites, common mistakes, and how to verify the result. A clear first success makes the next step easier.",
        "The user likes comparing two or three examples when learning a new pattern. Seeing the same idea in different contexts helps them generalize it. They prefer concise explanations over long theoretical detours.",
        "The user is more likely to finish a learning plan when the workload is realistic. Short sessions, spaced practice, and small milestones fit better than weekend marathons. They want enough structure to continue without feeling boxed in.",
    ),
    (
        "The user prefers warm lighting, natural textures, and rooms that feel lived-in rather than staged.",
        "The user likes entryway storage that keeps shoes, bags, keys, and mail from spreading through the house.",
        "The user prefers linen curtains, simple rugs, and muted colors with a few warmer accents.",
        "The user likes arranging houseplants in small clusters near windows where they are easy to water.",
        "The user prefers rooms with one comfortable reading spot. A good lamp, side table, and soft blanket matter more than decorative extras.",
        "The user likes home offices with a clear desk surface and a visible place for notes. Clutter feels less stressful when there is a specific tray or board for it.",
        "The user prefers kitchens with open counter space and practical storage. A few attractive everyday items can stay out, but crowded displays are frustrating.",
        "The user likes guest rooms that feel calm and useful without being formal. A small lamp, clear surface, spare blanket, and place for a suitcase are enough. The room should be easy to reset after visitors leave.",
        "The user prefers a cozy style that mixes pale wood, warm brass, soft greens, and clay-colored accents. They like handmade details when they are subtle. The overall goal is tidy, comfortable, and personal.",
        "The user likes seasonal decor in small doses. A wreath, candle, or bowl of fruit feels better than changing the whole room. They prefer decorations that are easy to store and reuse.",
    ),
)

PROJECT_MEMORIES_BY_UID: dict[str, tuple[str, ...]] = {
    "proj-fic-cedarledger-01": (
        "CedarLedger is a bookkeeping app for independent workshops that need simple job, invoice, and expense tracking.",
        "The project keeps business examples generic, with no bank details, tax IDs, or customer contact records.",
        "The dashboard groups open invoices, recent expenses, and unpaid workshop jobs into separate summary cards.",
        "The sample expense categories are materials, tools, utilities, rent, insurance, and training.",
        "A design note prefers clear tables with compact filters over decorative financial charts.",
        "The app should warn when an expense is missing a category before it appears in a monthly report.",
        "The export feature writes local JSON and CSV files with generated placeholder records only.",
        "The project glossary defines a job as a billable workshop activity tied to one or more invoice lines.",
        "Invoice status filters include draft, sent, overdue, paid, and archived.",
        "A release checklist item verifies that bookkeeping examples contain no sensitive business details.",
        "A decision note says currency values should use small round numbers. This keeps screenshots and test assertions easy to read.",
        "The workspace has three workshop profiles named North Bench, Pine Room, and Sawdust Studio. These names are stable for repeatable search and list tests.",
        "A known issue says the unpaid badge can overlap long workshop names on narrow screens. The fix should reserve space before the status chip renders.",
        "Recurring expenses are grouped by vendor nickname and category. The app does not need full vendor profiles for the first version.",
        "The monthly report should separate paid invoices from outstanding invoices. Workshop owners need both cash received and work still awaiting payment.",
        "Job estimates can be converted into invoices after the workshop marks the work complete. The converted invoice should keep the original job notes.",
        "The app stores attachment placeholders for receipts and invoice PDFs. Real file upload behavior is outside the seeded workspace scope.",
        "The settings page lets a workshop choose a default tax label. The label is text-only so regional examples do not imply legal advice.",
        "Search should find expenses by category, job name, and short note. It should not require users to remember exact invoice numbers.",
        "A task remains to add keyboard navigation to the invoice table. Row actions should be reachable without opening the detail page.",
        "CedarLedger treats a workshop as the top-level account boundary. Jobs, invoices, expenses, and reports all belong to one workshop profile. Cross-workshop reporting is intentionally left for later.",
        "The overview screen uses three calm states for money owed, money received, and expenses logged. Each card links to a filtered table. The goal is quick orientation, not full accounting analysis.",
        "The seeded workspace includes cabinet repair, frame assembly, and tool maintenance jobs. Each job uses neutral descriptions and rounded amounts. None of the records refer to real people or addresses.",
        "Validation should catch invoices without line items before they can be marked sent. The error belongs near the line item table. A summary message should also appear at the top of the form.",
        "The report exporter includes a generated timestamp and selected month. It should not include machine paths or local usernames. This keeps exported examples safe for screenshots and test logs.",
        "A bug note says the expense filter resets after deleting a draft invoice. The corrected behavior should keep the current report filters active. Regression coverage belongs with the table state tests.",
        "The onboarding checklist asks users to create a workshop profile, add one job, record one expense, and preview an invoice. The steps should work with placeholder values. The final step links to the monthly report.",
        "CedarLedger avoids terms that imply certified accounting guidance. The copy should say reports and records instead of tax preparation. Users can export data for a professional review if needed.",
        "The local backup command writes one archive with jobs, invoices, expenses, and settings. It should fail clearly if the destination folder is not writable. Partial archives should be removed after a failed backup.",
        "The reconciliation screen compares invoices paid this month with expenses logged this month. Differences are shown as plain totals, not as financial advice. The screen should stay useful for small workshops with only a few records.",
    ),
    "proj-fic-northstar-forms-01": (
        "Northstar Forms keeps every draft form usable without a network connection.",
        "Field note templates start with location, observer role, weather, and follow-up fields.",
        "A compact review screen helps crews check required answers before exporting notes.",
        "The design favors plain language labels over survey jargon for field crews.",
        "The default theme uses high-contrast ink, muted blue accents, and large tap targets.",
        "Schema versioning is intentionally visible in the form settings panel.",
        "The sample checklist includes trail condition, equipment status, and photo reference prompts.",
        "A task remains to add keyboard shortcuts for moving between repeated observation blocks.",
        "The export panel offers CSV and JSON because partner tools vary by crew.",
        "Import tests use small JSON bundles with neutral station names.",
        "The team decided that required questions should be marked in both the label and helper text. This keeps printed copies understandable when color is unavailable.",
        "Offline mode queues submissions in timestamp order. A small status badge shows whether each note is saved locally or ready to sync.",
        "A bug note says conditional sections reopened after a draft was duplicated. The fix should preserve the collapsed state from the source draft.",
        "The form builder supports text, number, date, select, checkbox, and repeatable group fields. Signature and payment fields are out of scope.",
        "Decision notes say each template should preview well on a tablet held in portrait orientation. Desktop polish is secondary to reliable field entry.",
        "Validation messages should explain what to fix, not just name the failing rule. The copy guide prefers plain phrases such as choose one condition.",
        "The local database keeps separate tables for templates, drafts, attachments, and sync receipts. Attachments use generated placeholders in examples.",
        "A known issue says long repeat-group labels wrap awkwardly in the sidebar. The proposed fix is to reserve two lines before truncating.",
        "The project glossary defines a field note as a structured observation captured during site work. Notes can include repeatable observations, checklist answers, and short comments.",
        "Configuration defaults keep sync disabled until a workspace chooses an endpoint. The local-only path remains the primary example experience.",
        "Northstar Forms treats a template as locked once a crew begins collecting notes from it. Editors can clone the template, revise the copy, and publish a new version. This avoids changing the meaning of earlier field observations.",
        "The onboarding flow starts with a sample wetland survey because it shows conditional fields clearly. Users can remove the sample after creating their first real workspace. The example data stays generic and location-neutral.",
        "A sync receipt records the local draft ID, export batch ID, and template version. It does not store operator names, device identifiers, or precise site locations. This keeps troubleshooting useful without collecting private details.",
        "The accessibility review asks for every field type to work with screen readers and hardware keyboards. Error summaries should link directly to the problem field. Required markers must have text equivalents.",
        "A release checklist item verifies that the app can create, edit, save, close, and reopen a draft while offline. The test also exports the draft after reconnecting to the local service. No network-only dependency should be required for the core flow.",
        "The builder sidebar groups fields into basics, choices, structure, and review helpers. Reordering uses move buttons first, with drag-and-drop treated as optional enhancement. This keeps the editor usable on rugged tablets.",
        "The workspace includes templates for site walk, equipment check, and incident follow-up. Each template uses generic site codes and crew roles. None of the examples contain real addresses, personal names, or phone numbers.",
        "A bug was found where a hidden required field still blocked draft completion. The rule should only evaluate required fields when their parent condition is active. Regression coverage belongs beside the conditional-logic tests.",
        "The attachment placeholder flow stores file name, media type, and local draft reference. It does not need binary upload support for this project slice. Preview cards should still show whether a photo is expected.",
        "Template search should rank title matches first, then field labels, then helper text. Crews often remember the section name rather than the exact form title. The search screen should show why each result matched.",
    ),
    "proj-fic-harborpilot-01": (
        "HarborPilot keeps the shared lift schedule visible beside the repair crew task board so blocked jobs are easy to spot.",
        "The crew board groups work into intake, waiting on equipment, in progress, inspection, and ready for pickup lanes.",
        "Shared compressors, diagnostic tablets, and bay lifts are modeled as assignable resources rather than owned team assets.",
        "The dispatch view highlights repair jobs that can start immediately when a reserved equipment slot opens.",
        "HarborPilot uses calm blue and safety orange accents to separate schedule warnings from routine task updates.",
        "The prototype search query lift should rank equipment bookings before general maintenance notes.",
        "Job cards show the needed tools, target bay, and crew size before anyone drags the task into active work.",
        "A known issue says the calendar chip can overlap long equipment names on narrow boards.",
        "The weekly schedule starts with a planning lane for jobs awaiting equipment confirmation.",
        "The board empty state suggests adding a repair job, reserving shared equipment, or reviewing the handoff queue.",
        "HarborPilot treats equipment conflicts as scheduling blockers, not as assignment failures. The board should explain which job currently holds the shared resource.",
        "Each repair task can reserve one primary asset and several optional support tools. Optional tools should never prevent a job from moving forward unless the crew marks them required.",
        "The lane summary counts crews separately from equipment reservations. This helps reviewers see whether a delay comes from staffing or from a shared asset bottleneck.",
        "Configuration examples disable live notifications and keep all scheduling changes local to the sample workspace. The activity feed still shows generated booking edits for realistic review.",
        "A task remains to add a split view for upcoming lift reservations and active repairs. The goal is to reduce double-booking during shift handoff.",
        "The mock importer accepts repair rows with columns for job code, equipment need, bay, estimate, and notes. It rejects rows that include phone numbers or customer contact fields.",
        "The accessibility note requires warning icons to include text because color alone cannot explain equipment conflicts. The same rule applies to overdue inspection badges.",
        "A bug note says completed jobs briefly remained attached to a compressor reservation after the board filter was cleared. The fix should release the resource as soon as the job enters inspection.",
        "The handoff checklist asks crews to confirm bay cleanup, tool return, and next job readiness. A job cannot be marked ready for pickup until required equipment reservations are closed.",
        "Release notes call out that all schedules, crews, repair tasks, and equipment names use generated content. Reviewers should still check new memories for accidental personal details before merging.",
        "The team decided that urgent work uses priority bands named harbor red, pier amber, and dock green. These labels keep the sample operational without resembling a real emergency code. The colors should be paired with text labels everywhere.",
        "The planning lane keeps uncertain tasks visible without blocking a bay. Estimates remain visible, but start times stay hidden until a resource is selected. This helps coordinators avoid false commitments.",
        "HarborPilot sample crews use neutral names like Crew A, Crew B, and Night Crew. These labels are stable for snapshot tests and avoid implying any real staff roster. Crew capacity is expressed as available slots rather than individual identities.",
        "The equipment registry includes two lifts, one alignment rack, a compressor, a diagnostic tablet, and a parts cart. Each resource has a maintenance window that can be reserved like any job. The task board should show these windows as unavailable blocks.",
        "Scenario tests include a dock gate repair that needs the alignment rack after the morning lift slot. The expected schedule keeps the job waiting until both the rack and a two-person crew are free. This verifies that resource and staffing constraints combine correctly.",
        "HarborPilot stores generated job IDs with the prefix HP-JOB for deterministic examples. Equipment IDs use HP-EQ so the records are easy to scan. No identifier should resemble a license plate, serial number, or private asset tag.",
        "A design note prefers timeline cards over dense tables for the first scheduling screen. Cards make equipment conflicts easier to read during a quick crew standup. The table view remains useful for bulk editing later.",
        "The prototype should warn when two active jobs request the same lift within the same time block. The warning links to the equipment calendar and offers to move the lower-priority job. If both jobs have the same priority, HarborPilot suggests the one with the shorter estimated duration.",
        "The shift handoff view lists blocked jobs before routine updates. Coordinators can see equipment conflicts, missing parts, and inspection holds in one pass. Completed jobs collapse into a short summary at the bottom.",
        "Schedule exports include job code, lane, required equipment, crew label, and planned start window. They do not include customer names, addresses, or phone numbers. The export should remain useful for local testing and screenshots.",
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


def _memory_matches_expected(actual: Memory, expected: Memory) -> bool:
    return (
        actual.id == expected.id
        and actual.space == expected.space
        and actual.type == expected.type
        and actual.content == expected.content
        and actual.status == expected.status
        and actual.workspace_uid == expected.workspace_uid
        and actual.metadata == expected.metadata
        and actual.source == expected.source
        and actual.confidence == expected.confidence
        and actual.sensitivity == expected.sensitivity
        and actual.created_at == expected.created_at
        and actual.updated_at == expected.updated_at
        and actual.last_accessed_at == expected.last_accessed_at
    )


def _has_acceptable_visible_content(content: str) -> bool:
    banned_labels = (
        "Fictional dev user",
        "fact 1:",
        "project memory",
        "seed data",
        "seeded demo",
        "seeded bookkeeping",
        "seeded scheduling",
        "public-safe",
        "safe for public screenshots",
        "fixture",
        "demo",
        "fabricated",
    )
    sentence_count = len([part for part in content.split(". ") if part])
    return 1 <= sentence_count <= 3 and not any(
        label.casefold() in content.casefold() for label in banned_labels
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
    expected_user_memories = {
        _user_seed_memory(index).id: _user_seed_memory(index)
        for index in range(DEV_SEED_USER_MEMORY_COUNT)
    }
    expected_workspace_memories = {
        _workspace_seed_memory(
            workspace_index, memory_index
        ).id: _workspace_seed_memory(workspace_index, memory_index)
        for workspace_index in range(DEV_SEED_WORKSPACE_COUNT)
        for memory_index in range(DEV_SEED_WORKSPACE_MEMORY_COUNT)
    }
    actual_user_memories = {memory.id: memory for memory in user_memories}
    actual_workspace_memories = {memory.id: memory for memory in workspace_memories}
    user_contents = [memory.content for memory in user_memories]
    workspace_contents = [memory.content for memory in workspace_memories]
    all_contents = user_contents + workspace_contents
    expected_workspace_uids = {project["uid"] for project in DEV_SEED_PROJECTS}
    expected_workspace_counts = {
        project["uid"]: DEV_SEED_WORKSPACE_MEMORY_COUNT for project in DEV_SEED_PROJECTS
    }
    expected_topic_counts = {topic: 10 for topic in DEV_SEED_USER_TOPICS}
    actual_topic_counts = Counter(
        memory.metadata.get("dev_topic") for memory in user_memories
    )
    expected_project_names = {
        project["uid"]: project["name"] for project in DEV_SEED_PROJECTS
    }

    return (
        len(user_memories) == DEV_SEED_USER_MEMORY_COUNT
        and len(workspace_memories) == DEV_SEED_TOTAL_WORKSPACE_MEMORIES
        and set(actual_user_memories) == set(expected_user_memories)
        and set(actual_workspace_memories) == set(expected_workspace_memories)
        and all(
            _memory_matches_expected(actual_user_memories[memory_id], expected)
            for memory_id, expected in expected_user_memories.items()
        )
        and all(
            _memory_matches_expected(actual_workspace_memories[memory_id], expected)
            for memory_id, expected in expected_workspace_memories.items()
        )
        and set(store.list_workspace_uids(include_archived=True))
        == expected_workspace_uids
        and Counter(memory.workspace_uid for memory in workspace_memories)
        == expected_workspace_counts
        and actual_topic_counts == expected_topic_counts
        and len(set(user_contents)) == DEV_SEED_USER_MEMORY_COUNT
        and len(set(workspace_contents)) == DEV_SEED_TOTAL_WORKSPACE_MEMORIES
        and len(set(all_contents))
        == DEV_SEED_USER_MEMORY_COUNT + DEV_SEED_TOTAL_WORKSPACE_MEMORIES
        and all(_has_acceptable_visible_content(content) for content in all_contents)
        and all(
            memory.workspace_uid is not None
            and memory.metadata.get("dev_project_name")
            == expected_project_names[memory.workspace_uid]
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
