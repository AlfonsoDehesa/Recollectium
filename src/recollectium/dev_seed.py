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
DEV_SEED_PROJECT_THEMES_BY_UID: dict[str, tuple[str, ...]] = {
    "proj-fic-cedarledger-01": ("permissions", "exports", "reconciliation"),
    "proj-fic-northstar-forms-01": ("form-builder", "offline-sync", "review"),
    "proj-fic-harborpilot-01": ("scheduling", "equipment", "handoff"),
}
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
        "CedarLedger uses role-based access so shop owners can approve account connections, managers can review reports, and clerks can enter receipts without changing settings.",
        "A decision keeps payroll notes and owner draws visible only to users with the finance admin role, even when a workspace member can view ordinary expense categories.",
        "When inviting a new bookkeeper, CedarLedger should default to the least-privileged reviewer role until the workshop owner explicitly grants edit access.",
        "Access control checks must happen on the server for every invoice, receipt, and reconciliation endpoint, not only through hidden menu items in the interface.",
        "The session timeout should be shorter for users with permission to export ledgers. Exports can include sensitive supplier payment history and should not stay open on shared computers.",
        "A bug was found where switching between two workshop workspaces kept the previous workspace's permissions cached until refresh. Disabled buttons could briefly appear active for the wrong account.",
        "The owner role can transfer ownership only after re-authentication. The audit log should record the previous owner, new owner role, and timestamp without exposing secret values.",
        "A support user may view diagnostic metadata for a CedarLedger workspace but must not open transaction descriptions, attachment previews, or connected account balances. This keeps troubleshooting separate from financial content. The support view should explain which fields are intentionally hidden.",
        "The permissions matrix needs a specific rule for archived workshops. Members may read historical ledger summaries, but only an owner can reactivate or modify records. The archived state should also hide invite actions.",
        "Password changes should invalidate other active sessions while preserving the current re-authenticated session. CedarLedger needs regression coverage for open report tabs after that change. Export buttons should require a fresh permission check before downloading files.",
        "CedarLedger exports include both CSV and JSON formats so workshop owners can review monthly income, expenses, and category totals in whichever tool they prefer.",
        "The monthly report export uses a generated timestamp in the filename to make repeated downloads easy to distinguish.",
        "Safe placeholder accounting records for exports use generic vendors with rounded amounts and non-sensitive invoice references.",
        "CSV exports should preserve stable column order for date, entry ID, account, category, description, debit, credit, currency, and export batch. Tests should fail if a column moves without an intentional migration note.",
        "A task remains to add a JSON backup export that includes accounts, categories, ledger entries, reconciliation notes, and report metadata. The backup must not include credentials or local file paths.",
        "A bug was found where monthly CSV reports sorted entries alphabetically by description instead of transaction date. April workshop expenses appeared out of sequence in the exported file.",
        "The export settings panel should default to UTC timestamps for generated files. Report contents can still show the workspace display timezone selected in CedarLedger.",
        "CedarLedger backup files should use safe placeholder ledger data during development setup. Example rows can include tool purchases, workshop rental income, and materials refunds. The records must stay generic enough for screenshots.",
        "JSON exports are better for restoring CedarLedger state, while CSV exports are better for reviewers who only need monthly totals and transaction rows. The export screen should explain that difference in one short helper note. Both formats should share the same selected date range.",
        "The monthly exports workflow should include a checksum note in the export manifest. Users can verify that backup files were generated completely before archiving them. Failed exports should remove partial files before showing the error.",
        "CedarLedger calculates paid and outstanding invoice totals separately during reconciliation. Workshop owners can see cash collected versus work billed but not yet settled. The two totals should never be collapsed into one summary number.",
        "The monthly reconciliation review compares expense receipts against imported records and flags any vendor charge that lacks a matching receipt entry.",
        "An invoice marked paid must include a payment date, payment method, and matched ledger transaction before it appears in closed monthly totals.",
        "Record matching works best when CedarLedger compares amount, date window, vendor or client name, and reference notes rather than relying on exact memo text alone.",
        "During report review, February showed expenses matched correctly but two outstanding invoices were still included in the paid total. The revenue summary looked higher than the settled cash amount.",
        "The reconciliation screen should show a short explanation when totals differ. The message should say whether the gap comes from unmatched expenses, unpaid invoices, duplicate imports, or pending records.",
        "A task remains to add a filter for unmatched workshop supply expenses. Users need to review materials purchases before finalizing the monthly report.",
        "Partial invoice payments remain open records until the remaining balance reaches zero. The paid portion still contributes to collected revenue. The outstanding amount should stay visible beside the invoice status.",
        "A bug was found where deleting a matched expense receipt did not reopen the related transaction for reconciliation. The monthly validation state stayed incorrectly marked complete. Regression coverage belongs with receipt deletion tests.",
        "For monthly report approval, CedarLedger should require all imported records to be matched, excluded with a reason, or carried forward as pending review. The approval button should stay disabled until that checklist is complete. Reviewers need a summary of any carried-forward records.",
    ),
    "proj-fic-northstar-forms-01": (
        "Northstar Forms lets template editors add short text, long text, number, date, photo, signature, location, and single-choice fields from the builder palette.",
        "The form schema uses stable field IDs so saved offline submissions can still sync correctly after a template label is renamed, while the builder shows labels as editable text and keeps IDs hidden from normal editors.",
        "Conditional logic rules stay visible beside each field instead of hiding in a separate settings page.",
        "Template editing supports duplicating an existing field with its help text, validation rules, and conditional visibility settings intact.",
        "Repeatable groups are used for equipment inspections where a crew may record multiple assets under one site visit. Each repeated item should preserve its own validation state.",
        "The builder UI needs a clear warning when a required field is placed inside a conditional section that may never become visible. The warning belongs in the field settings panel.",
        "A bug was found where deleting the controlling question for a conditional field left an orphaned rule in the schema. The preview panel then rendered a blank card.",
        "Northstar Forms stores builder drafts locally first, so template edits made in low-connectivity areas remain available before workspace sync completes. The editor should show a local saved state after each change. Publishing can wait until the connection returns.",
        "The schema preview should show repeatable group boundaries, nested field order, and conditional branches. Developers can compare the builder output with the runtime form renderer. This helps catch mismatched field order before a template ships.",
        "Number fields need minimum, maximum, unit label, and decimal precision options. Photo fields need maximum image count and required caption settings. The builder should keep these controls near the field type selector.",
        "Northstar Forms keeps offline drafts on the device until the crew lead explicitly submits or deletes them.",
        "Queued submissions preserve their original completion timestamp and add a separate synced-at value once the server accepts them after reconnect. Receipt sorting should use completion time, not upload time.",
        "A sync receipt includes the form name, local draft ID, submission ID, and the time the server acknowledged the upload.",
        "When connectivity returns, the app processes queued submissions oldest first and continues syncing the remaining queue even if one entry fails validation.",
        "Field crews need an export option for unsynced drafts and queued submissions. This lets a crew hand off work from a damaged tablet before the next shift starts.",
        "A bug was found where editing an offline draft after it entered the submission queue could overwrite the queued payload. The receipt then described a different version than the one sent.",
        "Northstar Forms should show a clear local saved indicator after every offline autosave. This matters most on long forms where crews may lose signal between sections.",
        "The reconnect banner should distinguish between no drafts to sync, syncing queued submissions, sync completed with receipts, and sync blocked by conflicts. Each state needs different action text. Crews should never have to guess whether work is still local only.",
        "Configuration notes say offline draft retention is set per workspace, while sync receipt retention follows the audit log policy for submitted forms. The settings screen should show both values together. Retention changes should not delete existing drafts without confirmation.",
        "The next sync test should cover airplane mode form creation, local save recovery after app restart, queued submission after reconnect, receipt display, and CSV export of any item that still cannot upload. The test should also verify that failed uploads remain in the queue. Receipts should appear only for accepted submissions.",
        "Northstar Forms blocks final submission when a required answer is missing. Drafts may stay incomplete if the missing fields are clearly marked before approval. The review banner should explain that saving and submitting are separate actions.",
        "The review screen needs an error summary that groups required-answer failures separately from format validation issues.",
        "Approval checks expect every required answer to have either a valid response or an approved waiver note before a supervisor can mark the form complete.",
        "Validation messages should use plain language such as answer required before approval instead of generic system text.",
        "A bug was found where required radio questions appeared answered after reopening an offline draft. The stored value was blank, and the review step did not catch it.",
        "Accessibility review notes say the error summary must receive keyboard focus after a failed completion attempt. Each message should link back to the exact unanswered question.",
        "The draft completion indicator should show separate counts for unanswered required questions, failed validation rules, and pending approval checks. A single incomplete badge hides too much information.",
        "Conditional required questions should appear in the required-answer review list only when their parent condition is active in the current draft. Hidden questions should not block approval. The review screen should mention why a conditional question is skipped.",
        "Screen reader testing found that inline validation messages were announced twice on the review page. The team planned to keep the summary announcement and make repeated inline text less noisy. Keyboard focus should still move to the first problem field on request.",
        "Northstar Forms needs a final approval guard that re-runs required-answer checks after offline sync. Validation rules can change while a crew is collecting responses in the field. If a rule changed, the approval screen should explain what needs another review.",
    ),
    "proj-fic-harborpilot-01": (
        "HarborPilot shows repair job schedules as grouped time blocks so dispatchers can spot overlapping crane, welding, and inspection work on the same pier.",
        "The crew coordination view shows planned start windows as ranges instead of exact timestamps.",
        "Lane ordering in the dispatch board prioritizes urgent hull patch jobs first, then scheduled maintenance, then low-priority dock hardware repairs.",
        "The planned start window filter supports jobs beginning within the next two hours, tomorrow morning, or the current shift block.",
        "Night shift crews need a separate lane so supervisors can distinguish carryover work from newly assigned morning jobs. That lane should stay visible during morning handoff.",
        "A bug was found where dragging a repair card between dispatch lanes preserved the crew assignment but reset the planned start window. The card jumped back to the beginning of the day.",
        "HarborPilot configuration allows each harbor zone to define its own standard shift blocks. The dry dock team and pier repair team do not follow the same daily schedule.",
        "The schedule timeline should highlight idle gaps between repair jobs. Dispatchers can insert quick inspections or small parts replacement tasks without disrupting larger work orders. The gap indicator should show the available duration.",
        "The shift planning screen warns when a crew is assigned to back-to-back repair jobs in different harbor zones. It should account for travel and setup time between blocks. The warning belongs near the second job assignment.",
        "Schedule exports include job code, lane, required equipment, crew label, and planned start window. They should not include customer names, addresses, or phone numbers. The export remains useful for local testing and screenshots.",
        "HarborPilot reserves the west yard shared lift as a single-capacity resource because two pier repair crews tried to book it for overlapping morning haul-outs.",
        "The compressor trailer is unavailable every Friday afternoon for filter checks, so scheduling suggestions need to avoid assigning pneumatic tool work during that window.",
        "Diagnostic tablets often stay checked out after vessel-side inspections, creating stale availability data for the next repair shift. HarborPilot should prompt for tablet return before marking related inspection notes complete.",
        "HarborPilot shows equipment conflicts before crew conflicts when a job requires a shared lift, compressor, or diagnostic tablet. The board should explain that the job cannot start until the resource is reserved.",
        "The north basin lift reservation includes a setup and teardown buffer. Back-to-back assignments should not assume instant movement between repair bays.",
        "A bug was found where the equipment calendar allowed a compressor reservation to be shortened by one crew while another crew still depended on the original time range.",
        "An equipment-unavailable reason field should support maintenance, relocation, safety hold, and battery charging. Dispatchers need to understand why a tool cannot be assigned.",
        "HarborPilot needs a reminder when diagnostic tablets have not synced inspection notes before being returned to the shared equipment pool. The reminder should appear before the tablet is marked available. Supervisors can dismiss it only after confirming sync status.",
        "Portable compressors should be grouped by pressure rating, not only by name. Some hull repair tasks can use any unit above the required output. The resource picker should surface compatible alternatives.",
        "Resource reservations should flag travel time when a shared lift must move from the dry dock apron to the inner harbor service lane. The move should reserve the lift during transit. Dispatchers need to see that blocked interval on the equipment calendar.",
        "The evening dispatcher marked Pier 4 fender repair as blocked. The inspection hold is still active. Next shift should verify the hold release before assigning a dive crew.",
        "HarborPilot handoff notes show whether each job is ready, blocked, or waiting on inspection so incoming coordinators avoid calling crews for work that cannot start.",
        "The north basin bollard replacement checklist requires crane availability, tide window confirmation, and safety barrier placement before the job can move to ready status.",
        "Blocked jobs remain visible at the top of the handoff board until the blocker type and responsible role are recorded.",
        "During shift change, the outgoing lead summarized three pending repairs. One was cleared for crew dispatch, one was waiting on materials, and one was paused until inspection signoff.",
        "A bug was found where completed crew checklist items did not always appear in the next-shift summary. The incoming coordinator repeated readiness checks unnecessarily.",
        "The night crew left a note that the fuel dock ladder repair is safe to stage but not safe to begin. The final inspection hold has not been removed.",
        "Next-shift summaries include the last crew contact time and any unresolved access issues. Coordinators can quickly decide whether to roll a repair team. The summary should hide completed routine updates by default.",
        "The handoff workflow treats missing permits, incomplete checklists, and inspection holds as separate blockers instead of combining them into a generic not-ready status. Each blocker needs an owner and next action. This makes morning triage less ambiguous.",
        "A coordinator noticed that jobs marked ready before shift end sometimes lost their assigned crew in the morning view. The assignment should persist across handoff. Dispatchers should check this before relying on HarborPilot for planning.",
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
    theme_index = memory_index // 10
    theme = DEV_SEED_PROJECT_THEMES_BY_UID[workspace_uid][theme_index]
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
            "dev_theme": theme,
            "dev_theme_index": theme_index,
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
    expected_workspace_theme_counts = {
        uid: Counter({theme: 10 for theme in themes})
        for uid, themes in DEV_SEED_PROJECT_THEMES_BY_UID.items()
    }
    actual_workspace_theme_counts = {
        project["uid"]: Counter(
            memory.metadata.get("dev_theme")
            for memory in workspace_memories
            if memory.workspace_uid == project["uid"]
        )
        for project in DEV_SEED_PROJECTS
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
        and actual_workspace_theme_counts == expected_workspace_theme_counts
        and all(
            memory.workspace_uid is not None
            and memory.metadata.get("dev_project_name")
            == expected_project_names[memory.workspace_uid]
            and memory.metadata.get("dev_project_uid") == memory.workspace_uid
            and memory.metadata.get("dev_theme")
            in DEV_SEED_PROJECT_THEMES_BY_UID[memory.workspace_uid]
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
