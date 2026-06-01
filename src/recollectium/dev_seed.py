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
        "CedarLedger uses tiered permissions so shop owners approve bank connections, managers inspect reports, and clerks record daily sales without reaching administrative settings. The setup mirrors how small workshops separate counter work from financial oversight.",
        "Payroll notes and owner draws stay visible only to finance administrators, even when a workspace teammate can browse ordinary expense categories. That boundary keeps sensitive compensation details away from routine bookkeeping chores.",
        "New bookkeeper invitations should land in a read-only reviewer seat until the workshop owner deliberately grants editing rights. The first visit should explain that extra capabilities require owner confirmation.",
        "Server-side guards must protect every bill, attachment, and month-end review endpoint rather than relying on hidden navigation items.",
        "Cash-drawer clerks can enter daily takings and supplier slips, but they should not change tax settings, payout accounts, or workspace billing details.",
        "A bug showed that switching between two workshops reused the earlier workspace's cached capabilities until refresh. Disabled controls briefly looked usable for the wrong account. The fix should clear local grants whenever the workspace selector changes.",
        "The owner seat may transfer ownership only after re-authentication. The audit trail records the former owner, the incoming owner, and the timestamp without exposing secrets. A confirmation screen should summarize the irreversible parts of the change.",
        "Support staff may inspect CedarLedger diagnostic metadata but must not open transaction descriptions, attachment previews, or connected balance details. The troubleshooting screen should explain which fields are intentionally masked. This keeps help-desk work separate from private financial content.",
        "Archived workshops need a separate matrix rule: members may read historical ledger summaries, while only an owner can reactivate or alter records. Invite actions should disappear while the workspace is archived. The read-only banner should mention who can reopen the workspace.",
        "After a password change, other active sessions should be invalidated while the current re-authenticated session survives. CedarLedger needs regression coverage for open report tabs and a fresh authorization check before any ledger package leaves the app. Stale tabs should show a prompt instead of silently continuing.",
        "CedarLedger provides CSV and JSON exports so workshop owners can inspect monthly income, expenses, and category totals in the tool that suits their review process.",
        "Monthly report packages should include a generated timestamp in the name so repeated pulls from the same date range remain easy to tell apart.",
        "Sample accounting rows used for development output rely on generic vendors, rounded amounts, and harmless reference numbers.",
        "Spreadsheet output needs a stable column order for date, entry ID, account, category, description, debit, credit, currency, and batch marker. Tests should fail when a column moves without a migration note. Reviewer macros depend on those positions staying predictable.",
        "A task remains to add a restorable ledger snapshot covering accounts, categories, entries, month-end notes, and report metadata. It must omit credentials and local paths. The restore preview should list record counts before applying changes.",
        "A bug sorted April workshop expenses by description instead of transaction date, which made the monthly spreadsheet appear out of sequence.",
        "The packaging settings panel should default generated artifact timestamps to UTC. Report contents may still display the CedarLedger workspace timezone. This avoids ambiguous archive names across daylight-saving changes.",
        "CedarLedger archive bundles should contain generic ledger examples such as tool purchases, workshop rent income, and materials refunds. The values need to be plain enough for screenshots. Example descriptions should avoid brand names and personal names.",
        "Structured state bundles are best for restoring CedarLedger, while spreadsheets suit reviewers who only need totals and transaction rows. The screen should explain the difference in one short helper note, with both formats sharing the selected date range. Both outputs should use the same cutoff rules.",
        "The monthly archive workflow should write a checksum note into the manifest. Users can confirm the package completed before storing it, and failed runs should discard partial artifacts before showing an error.",
        "CedarLedger calculates collected and outstanding totals separately during closeout. Workshop owners can compare cash received with work billed but not yet settled.",
        "The month-end review compares proof of expenses with imported records and flags vendor charges that have no supporting entry.",
        "A customer bill marked settled must include a payment date, payment method, and linked ledger transaction before it appears in closed monthly totals.",
        "Record pairing works best when CedarLedger weighs amount, date window, vendor or client name, and reference notes instead of exact memo text alone.",
        "During February review, expense lines looked correct but two open customer bills still inflated the settled revenue total. The summary overstated cash actually received.",
        "CedarLedger should explain why month-end totals differ, naming gaps from missing expense proof, open customer balances, duplicate imports, or pending records.",
        "A filter is still needed for workshop supply charges that have not been cleared. Users need to inspect materials purchases before finalizing the monthly report.",
        "Partial customer payments remain open records until the remaining balance reaches zero. The received portion still contributes to collected revenue, while the outstanding amount stays visible beside the status.",
        "A bug was found where deleting supporting proof for an expense did not reopen the related transaction for closeout review. The monthly validation state stayed incorrectly marked complete.",
        "Before monthly approval, every imported record should be cleared, excluded with a reason, or carried forward for later review. The approval button remains disabled until that checklist is complete.",
    ),
    "proj-fic-northstar-forms-01": (
        "Northstar Forms lets editors compose pages with short text, paragraphs, numbers, dates, photos, signatures, locations, and single-choice prompts from the builder palette.",
        "The form schema keeps immutable field IDs so saved submissions survive label changes; editors see friendly labels while internal identifiers remain hidden.",
        "Conditional display rules should appear beside the prompt they affect instead of being buried on a separate settings page.",
        "Template editing supports cloning an input with its help copy, constraints, and visibility behavior intact.",
        "Repeatable sections support equipment inspections where a crew records several assets during one site visit. Each repeated item keeps its own completion state. The preview should make repeated boundaries visually obvious.",
        "The authoring UI needs a warning when a mandatory item sits inside a conditional area that might never appear. Place the warning in the settings panel for that item. Editors should be able to jump from the warning to the controlling prompt.",
        "A bug was found where removing the controlling question for conditional display left an orphan rule in the internal definition. The preview then rendered an empty card. Cleanup should run before the updated design is saved.",
        "Northstar Forms saves editing sessions on the device first, so layout changes made in poor connectivity remain available before publishing. The editor should show a local-saved state after every change. Publishing can wait until the connection is stable.",
        "The technical preview should display repeatable section boundaries, nested order, and branching paths. Developers can compare the generated structure with the runtime renderer before a design ships. This catches ordering mismatches before crews use the page.",
        "Numeric entries need minimum, maximum, unit label, and decimal precision controls. Photo prompts need image-count limits and caption settings. Keep those options close to the type selector.",
        "Northstar Forms keeps offline drafts on the device until the crew lead explicitly submits or deletes them.",
        "Queued submissions preserve their original completion time and receive a separate synced-at timestamp after server acceptance. Receipt ordering should use completion time rather than upload time. Supervisors need the field chronology, not the network chronology.",
        "A sync receipt includes the form name, local draft ID, submission ID, and the time the server acknowledged the upload.",
        "When connection returns, the app sends saved work oldest first and keeps moving through the backlog even if one item hits a rule conflict.",
        "Field crews need an emergency package for work still stored on a tablet. This lets a damaged device hand off entries before the next shift starts.",
        "A bug was found where editing a locally stored form after it entered the outbound line could overwrite the payload waiting to sync. The confirmation then described a different version than the one sent.",
        "Northstar Forms should show a clear saved-on-this-device indicator after every autosave. That matters most on long inspections where signal may drop between sections.",
        "The reconnect banner should distinguish between nothing pending, items being transmitted, completed transfer with confirmations, and conflicts needing attention. Each state needs different action text.",
        "Configuration notes say local draft retention is set per workspace, while confirmation retention follows the audit log policy for submitted forms. The settings screen should show both values together.",
        "The next resilience test should cover airplane-mode creation, recovery after app restart, handoff when service returns, confirmation display, and spreadsheet output for any item still blocked. Accepted items should be the only ones marked complete.",
        "Northstar Forms blocks final submission when a required answer is missing. Drafts may stay incomplete if the missing fields are clearly marked before approval. The review banner should explain that saving and submitting are separate actions.",
        "The completion screen needs an error summary that separates blank mandatory responses from format problems.",
        "Supervisor checks expect every mandatory response to be valid or have an approved waiver note before the form can be marked complete.",
        "Validation messages should use plain language such as this response is needed before signoff instead of generic system text.",
        "A bug was found where required radio questions appeared answered after reopening an offline draft. The stored value was blank, and the review step did not catch it.",
        "Accessibility notes say the problem summary must receive keyboard focus after a failed completion attempt. Each message should link back to the exact blank question.",
        "The completion indicator should show separate counts for missing mandatory items, failed rule checks, and supervisor signoff blockers. A single incomplete badge hides too much information.",
        "Conditional must-fill questions should appear in the final check list only when their parent condition is active in the current draft. Hidden questions should not block signoff. The screen should mention why a conditional question is skipped.",
        "Screen reader testing found that inline problem messages were announced twice on the final check page. The team planned to keep the summary announcement and reduce repeated inline text.",
        "Northstar Forms needs a final signoff guard that re-runs mandatory-response checks after field data reaches the server. Rules can change while a crew is collecting responses away from service. If a rule changed, the screen should explain what needs another pass.",
    ),
    "proj-fic-harborpilot-01": (
        "HarborPilot groups repair work into visible time blocks so dispatchers can catch crane, welding, and survey overlap on the same pier. The board should make clashes obvious without opening each card.",
        "The crew coordination view presents arrival windows as ranges rather than exact clock times, leaving room for tide changes and setup delays. Dispatchers need flexibility without losing the intended order of work.",
        "Dispatch board ordering puts urgent hull patches first, routine maintenance second, and low-priority dock hardware fixes after the higher-impact work. The sort rule should remain stable when cards refresh.",
        "The time-window filter should support work beginning within two hours, tomorrow morning, or the active crew block.",
        "Overnight crews need a distinct swimlane so supervisors can separate carryover repairs from new morning assignments during turnover.",
        "A bug was found where moving a repair card across dispatch columns kept the crew assignment but reset the expected kickoff window. The card jumped back to daybreak. The move action should preserve timing unless the dispatcher edits it directly.",
        "HarborPilot configuration lets each harbor zone define standard crew blocks because dry dock work and pier repair work follow different daily rhythms.",
        "The timeline should highlight idle gaps between repair jobs so dispatchers can fit in quick surveys or small parts replacement tasks. The gap marker should show available duration. Tiny filler tasks should never displace larger work orders.",
        "Crew assignment warnings should account for travel and setup when consecutive repairs happen in different harbor zones. The warning belongs beside the second work order. Supervisors should see whether the problem is travel, staging, or both.",
        "Exports for HarborPilot dispatch views include job code, board column, required gear, crew label, and target arrival window. They must omit customer names, addresses, and phone numbers. The output stays useful for local testing and screenshots.",
        "HarborPilot treats the west yard shared hoist as single-capacity after two pier crews attempted overlapping morning haul-outs.",
        "The pneumatic trailer is offline every Friday afternoon for filter checks, so work suggestions should avoid air-tool jobs during that maintenance window.",
        "Diagnostic handhelds often remain checked out after vessel-side surveys, leaving stale availability for the next repair crew. HarborPilot should request return confirmation before related notes are closed. The warning should name the last job that used the device.",
        "HarborPilot surfaces tool conflicts before crew conflicts when a job depends on shared heavy gear or diagnostic devices. The board should explain that work cannot begin until the needed item is secured. Crew availability is secondary when the gear is unavailable.",
        "The north basin hoist booking includes setup and teardown buffers. Back-to-back assignments should not assume instant movement between repair bays. The calendar should display those buffers as occupied time.",
        "A bug was found where the air trailer calendar let one crew shorten a booking while another crew still depended on the original time range.",
        "An unavailable-item reason field should include maintenance, relocation, safety hold, and battery charging. Dispatchers need to know why a tool cannot be assigned. The reason should appear in suggestions, not just on the detail page.",
        "HarborPilot needs a reminder when diagnostic handhelds have not transmitted field notes before returning to the shared pool. Supervisors can dismiss it only after confirming transfer status. This prevents another crew from taking a device with unfinished records.",
        "Portable air units should be grouped by pressure rating rather than name alone. Some hull repair tasks can use any unit above the required output, so the picker should show compatible alternatives. Names alone hide workable substitutes.",
        "Bookings for shared heavy gear should reserve transit time when a hoist moves from the dry dock apron to the inner harbor service corridor. Dispatchers need that unavailable interval visible on the gear calendar.",
        "The evening dispatcher marked Pier 4 fender repair as waiting on a safety release. The relief crew should confirm the hold is lifted before assigning divers.",
        "HarborPilot handoff notes show whether each job is ready, blocked, or waiting on inspection so incoming coordinators avoid calling crews for work that cannot start.",
        "The north basin bollard replacement checklist requires crane availability, tide confirmation, and safety barrier placement before coordinators can clear the job for dispatch.",
        "Blocked jobs stay at the top of the handoff board until the blocker category and responsible role are recorded.",
        "At crew turnover, the outgoing lead summarized three pending repairs: one cleared for dispatch, one waiting on materials, and one paused for signoff.",
        "A bug was found where completed checklist items did not always appear in the turnover summary. The incoming coordinator repeated crew checks unnecessarily.",
        "The night crew noted that the fuel dock ladder repair is safe to stage but not safe to begin. The final safety hold has not been removed.",
        "Coordinator summaries include the most recent crew contact time and unresolved access issues. Routine completed updates should stay hidden by default.",
        "The handoff workflow separates missing permits, incomplete checklists, and inspection holds instead of collapsing them into a generic not-ready state. Each blocker needs an owner and next action.",
        "A coordinator noticed that jobs cleared before the crew change sometimes lost their assigned team in the morning view. HarborPilot should preserve that assignment across turnover.",
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
