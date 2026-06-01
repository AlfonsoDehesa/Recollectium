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
    {"uid": "fictional-ember-garden", "name": "Ember Garden"},
    {"uid": "fictional-lunar-ledger", "name": "Lunar Ledger"},
    {"uid": "fictional-river-bakery", "name": "River Bakery"},
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
        "likes planning imaginary rail trips through coastal towns with painted station signs",
        "keeps a fictional postcard album sorted by mountain, island, desert, and forest scenes",
        "prefers make-believe weekend escapes that include one quiet museum and one sunrise walk",
        "collects invented city maps and marks the best pretend bakery district in each one",
        "enjoys creating packing lists for storybook cabins where the weather changes every hour",
        "would choose a glass-roof train through a fictional canyon over a crowded fantasy festival",
        "notes dream destinations by the color of their street lanterns in a private travel notebook",
        "likes pretend seaside inns that serve pear tea before guests walk to the lighthouse",
        "keeps a bucket list of imaginary bridges to cross during calm autumn evenings",
        "prefers fictional travel days with no alarms, two scenic detours, and room for sketching",
    ),
    (
        "prefers a small teal bicycle with a brass bell for errands in the fictional town square",
        "names imaginary bus routes after constellations so they are easier to remember",
        "likes tram seats near the rear window because pretend city murals are easier to spot",
        "keeps a made-up ferry timetable folded inside a notebook for route-planning games",
        "would rather ride a quiet electric scooter than drive across a tiny fictional campus",
        "tracks fantasy train platforms by the snack kiosk nearest the departure board",
        "prefers walking paths with painted mile stones when moving between invented neighborhoods",
        "likes fictional cable cars that pause halfway up the hill for a view of red rooftops",
        "keeps a pretend maintenance checklist for a mint-green cargo bike named Clover",
        "chooses transportation in stories based on which option leaves the most time for daydreaming",
    ),
    (
        "enjoys cozy exploration games where the main quest can wait while gardens are rearranged",
        "prefers fictional puzzle games with handwritten clue journals and no countdown timers",
        "usually names game save files after weather words like drizzle, ember, and twilight",
        "likes roleplaying characters who solve problems by trading recipes instead of collecting swords",
        "keeps a pretend arcade token from a pixel game about moths delivering library books",
        "enjoys turn-based battles most when the victory screen includes tiny celebratory animations",
        "prefers game soundtracks with soft synth bells, rain loops, and gentle menu clicks",
        "likes building symmetrical farms in sandbox games even when asymmetry would be faster",
        "avoids fictional horror games unless the ghosts are polite and the lighting is warm",
        "keeps notes about imaginary game NPC birthdays so no one misses a digital muffin gift",
    ),
    (
        "prefers novels with annotated maps and chapter titles that sound like secret doorways",
        "keeps a fictional reading nook stocked with lemon biscuits and a blue wool blanket",
        "likes library mysteries where the missing object is a bookmark rather than a jewel",
        "sorts imaginary bookshelves by mood, placing stormy adventures beside quiet comedies",
        "enjoys short story collections about gentle robots tending rooftop gardens",
        "prefers paperbacks with deckled edges in stories about wandering cartographers",
        "keeps a pretend book club list where every selection includes at least one talking animal",
        "likes rereading fictional footnotes that reveal tiny jokes about invented historians",
        "collects made-up author signatures from novels that only exist inside daydreams",
        "prefers endings where characters open a bakery, restore a garden, or adopt a sleepy cat",
    ),
    (
        "likes making fictional starfruit pancakes with cinnamon clouds on quiet Sunday mornings",
        "keeps a pretend spice tin labeled moon pepper for soups in story recipes",
        "prefers chopping vegetables into tiny cubes because imaginary stews look tidier that way",
        "enjoys inventing picnic menus for meadow concerts with plum tarts and basil lemonade",
        "likes a fictional kitchen rule that every new recipe gets a doodle in the margin",
        "prefers baking round loaves scored with leaf patterns for make-believe neighbors",
        "keeps notes on imaginary noodle sauces named after seasons rather than ingredients",
        "likes cooking stories where the main conflict is whether the custard needs more vanilla",
        "prefers ceramic mixing bowls in invented colors like cloudberry, tidepool, and lantern yellow",
        "enjoys packing fictional lunch boxes with tiny waffles, cucumber moons, and cherry tea",
    ),
    (
        "prefers gentle morning stretches while imagining a sunlit studio with fern shadows",
        "keeps a fictional walking streak measured in laps around a tiny lake shaped like a comma",
        "likes exercise plans with rest days named after comfortable animals such as otter and dormouse",
        "prefers light dumbbells painted lavender in a pretend apartment gym",
        "tracks imaginary fitness goals using stickers shaped like clouds and little green hills",
        "enjoys low-pressure dance workouts to fictional radio shows from a floating city",
        "likes hiking routes in stories that end at a tea stand instead of a summit marker",
        "prefers swimming in calm indoor pools with painted tile fish along the lane markers",
        "keeps a pretend checklist for posture breaks during long mapmaking sessions",
        "celebrates fictional personal records with pear soda and a walk through a lantern garden",
    ),
    (
        "likes mellow instrumental playlists with harp, brushed drums, and distant rain sounds",
        "keeps a fictional concert ticket from a band that performs only at moonrise",
        "prefers songs with warm bass lines and lyrics about boats, libraries, or summer storms",
        "enjoys arranging imaginary mixtapes by color rather than genre or release year",
        "likes practicing three easy chords on a pretend orange ukulele named Clementine",
        "prefers fictional cafés where the house band plays quiet waltzes for reading hour",
        "keeps a notebook of invented album names such as Lantern Orchard and Velvet Comet",
        "likes music boxes in stories that play a different tune whenever a secret drawer opens",
        "prefers humming while cooking because imaginary soups taste better with a small melody",
        "enjoys make-believe radio stations that announce weather for islands no map has found",
    ),
    (
        "has an imaginary tuxedo cat named Miso who steals soft bookmarks from the reading chair",
        "likes fictional dogs with serious jobs such as lighthouse greeter or bakery crumb inspector",
        "keeps a pretend aquarium stocked with glassy fish that glow whenever someone tells a joke",
        "prefers pet birds in stories that repeat compliments instead of secrets",
        "imagines a rabbit named Pollen who naps in a basket of clean dish towels",
        "likes designing tiny fictional raincoats for corgis who patrol mushroom gardens",
        "keeps a make-believe pet care chart with snack times written in purple ink",
        "prefers animal companions in games that help find herbs rather than fight monsters",
        "imagines a sleepy tortoise named Button who recognizes three different dinner bells",
        "likes fictional adoption stories where every pet receives a knitted blanket and a sunny window",
    ),
    (
        "likes learning imaginary alphabets by copying bakery signs from invented seaside towns",
        "keeps a fictional study plan with gold stars for map symbols, bird calls, and soup terms",
        "prefers tutorials that include a tiny practice project and a cheerful mistake glossary",
        "enjoys memorizing pretend constellations shaped like teacups, foxes, and windmills",
        "likes taking notes in two columns: useful ideas on the left and whimsical questions on the right",
        "prefers learning sessions that end with a small drawing of what was understood",
        "keeps a pretend flashcard deck about cloud types in a storybook weather academy",
        "likes fictional workshops where students trade handmade bookmarks after the final lesson",
        "prefers teachers in stories who explain hard topics using gardens, boats, and soup pots",
        "enjoys learning one tiny skill at a time and naming each milestone after a friendly planet",
    ),
    (
        "prefers home rooms with warm lamps, rounded furniture, and shelves of colorful bowls",
        "keeps a fictional entryway basket for beach stones, spare keys, and library receipts",
        "likes curtains in invented apartments to be linen, moss green, and slightly too long",
        "prefers arranging houseplants in odd-numbered clusters beside sunny windows",
        "imagines a reading chair that swivels toward either the rain or the fireplace",
        "likes home offices with cork boards full of maps, recipes, and gentle reminder notes",
        "prefers rugs with quiet geometric patterns that look like tiny garden paths",
        "keeps a pretend guest room stocked with cloud pillows and a jar of peppermint sticks",
        "likes fictional kitchens where mugs hang by color and mixing spoons live in a blue crock",
        "prefers a calm home style described as lighthouse cottage meets soft forest workshop",
    ),
)

PROJECT_MEMORIES_BY_UID: dict[str, tuple[str, ...]] = {
    "fictional-ember-garden": (
        "The project tracks pretend greenhouse beds with soft red, amber, and violet status labels.",
        "The team decided that plant records use invented cultivar names rather than real botanical data.",
        "The demo dashboard opens on the weekly watering lane because it has the clearest sample flow.",
        "Seed packet images are represented by generated color tiles so no licensed assets are needed.",
        "A bug was found where moonlight reminders sorted before sunrise reminders on the same date.",
        "The fixture includes three greenhouse zones named Atrium, Lantern Row, and Moss Nook.",
        "The project uses a fake caretaker persona called Rowan Field to narrate onboarding hints.",
        "Decision notes say humidity values should be playful bands such as misty, crisp, and balmy.",
        "The backlog keeps a task to add a printable fantasy planting calendar for the sample garden.",
        "Configuration defaults choose Celsius-looking labels but avoid claiming any real sensor readings.",
        "The color palette intentionally uses warm clay backgrounds with pale sprout highlights.",
        "The mock importer accepts comma-separated seed names but never reaches an external service.",
        "A known test case covers duplicate bed nicknames by appending a tiny lantern glyph in the UI copy.",
        "The project glossary defines a glow day as any fictional day with two completed care tasks.",
        "The sample export contains only fabricated bed names and deterministic timestamp strings.",
        "A task remains to add keyboard shortcuts for moving between greenhouse zones in the prototype.",
        "The acceptance notes require every empty state to suggest one whimsical next action.",
        "The local settings file stores the selected greenhouse theme and no personal profile fields.",
        "The mock alert queue includes overdue misting, compost turn, and label repaint reminders.",
        "A bug note says archived plants briefly appeared in the active shelf count after a filter reset.",
        "The project decided not to model pests because the sample should stay calm and low-stakes.",
        "The prototype treats every sample plant as fictional and safe to publish in screenshots.",
        "The nightly demo reset restores exactly twelve beds across the three imaginary zones.",
        "A design note prefers rounded cards because sharp table grids made the garden feel too clinical.",
        "The fixture includes a fake seed supplier named Cloudroot Cooperative for scenario testing.",
        "The project records decisions in dated notes but keeps dates fixed for deterministic tests.",
        "A task asks for a gentle success sound placeholder named chime-soft-one in the asset manifest.",
        "The sample search query herb spiral should return the Moss Nook planning note first.",
        "The read-only tour mode hides edit controls while preserving all sample greenhouse content.",
        "A release checklist item verifies that no real plant inventory or user names appear in the seed data.",
    ),
    "fictional-lunar-ledger": (
        "The project models an imaginary moon market with shells, lanterns, and stamps as pretend units.",
        "The team decided balances should be obviously fictional and never resemble real financial data.",
        "The overview page groups sample entries by moon phase rather than calendar month.",
        "A bug was found where crescent credits displayed with the full-moon icon after sorting.",
        "The dummy workspace has account names like Observatory Jar, Kite Fund, and Biscuit Reserve.",
        "Configuration fixtures disable network sync and keep every ledger entry local to the sample file.",
        "The importer accepts fantasy receipt rows with columns for stall, charm, amount, and note.",
        "The project uses a fake reviewer persona called Mina Vale for comment examples.",
        "Decision notes say negative balances should be called cloudy totals in user-facing copy.",
        "A task remains to add chart legends for lantern income and stardust expenses.",
        "The fixture includes deterministic entries for tea stalls, paper kites, and telescope polish.",
        "A known issue says the printed summary wraps long market stall names one line too early.",
        "The color palette uses midnight blue, parchment cream, and a small amount of comet orange.",
        "The sample data intentionally avoids bank names, card numbers, addresses, and real currencies.",
        "The project glossary defines a pocket moon as a decorative grouping label with no real value.",
        "The dashboard empty state suggests adding a pretend receipt from the North Pier market.",
        "A task asks for a reversible demo reset button that restores the original thirty entries.",
        "The workspace notes require totals to show the word fictional in developer screenshots.",
        "A bug note says deleting the last Kite Fund entry left its category chip visible until refresh.",
        "The mock audit log stores action labels but omits IP addresses, device names, and actor emails.",
        "The project decided that recurring entries should repeat every third moonbeam for whimsy.",
        "The prototype search query telescope should rank maintenance receipts before snack receipts.",
        "The local fixture has three report templates named Market Drift, Harbor Glow, and Quiet Orbit.",
        "The accessibility note requires icons to have text labels because phase shapes can be ambiguous.",
        "The scenario tests include a fabricated refund from the cloud umbrella stall.",
        "The project stores export filenames with fixed slugs so snapshot tests stay deterministic.",
        "A task remains to add a small warning when a pretend receipt has an empty charm field.",
        "The sample ledger is licensed as generated placeholder content safe for public repositories.",
        "Decision notes say the app should explain that all demo arithmetic is illustrative play data.",
        "A release checklist item verifies no real merchants or personal purchases are seeded.",
    ),
    "fictional-river-bakery": (
        "The project simulates a cozy riverside bakery that sells invented pastries to story characters.",
        "The team decided menu items use fantasy names like pebble buns and willow twists.",
        "The sample order board groups work by oven, cooling rack, display case, and delivery basket.",
        "A bug was found where the frosting queue counted archived tasting notes as active orders.",
        "The dummy workspace includes stations named Dock Window, Blue Oven, and Picnic Counter.",
        "Configuration fixtures set the opening hour label to dawn-ish so it is clearly not operational.",
        "The project uses a fake baker persona called Juniper Loaf for tutorial snippets.",
        "Decision notes say recipes should list whimsical measures such as spoonful, pinch, and cloud.",
        "A task remains to add drag-and-drop sorting for the fictional pastry display case.",
        "The fixture includes deterministic sample orders for reed rolls, plum boats, and button cakes.",
        "A known issue says long pastry names overflow the tiny receipt preview on narrow screens.",
        "The color palette uses flour white, river blue, copper pan, and jam red accents.",
        "The mock inventory includes made-up ingredients and never records real supplier details.",
        "The project glossary defines a warm shelf as a sample-only status for pastries awaiting pickup.",
        "The empty state invites adding a pretend morning special with one short flavor note.",
        "A task asks for printable fictional recipe cards with generated border art.",
        "The workspace notes require every customer name to be invented and obviously non-identifying.",
        "A bug note says changing the oven filter reset the selected pastry type to the first option.",
        "The mock activity log stores station changes but no staff schedules or contact information.",
        "The project decided that delivery routes follow river landmarks rather than real streets.",
        "The prototype search query plum should rank the plum boat recipe above order cleanup notes.",
        "The local fixture has three menus named Rainy Morning, Festival Noon, and Lantern Supper.",
        "The accessibility note requires pastry color labels because frosting swatches alone are unclear.",
        "The scenario tests include a fabricated catering box for the paper dragon picnic.",
        "The project stores generated recipe IDs with fixed prefixes for stable snapshot tests.",
        "A task remains to warn when an invented recipe has no cooling time note.",
        "The sample bakery data is generated placeholder content safe for public repositories.",
        "Decision notes say totals are story counts and must never imply real sales reporting.",
        "The demo reset restores exactly ten pastries, eight orders, and twelve station notes.",
        "A release checklist item verifies no real restaurants, customers, or private recipes are seeded.",
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
        content=f"The user {fact}.",
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
    """Create the seeded development database when it is missing or incomplete."""
    if seeded_dev_database_is_initialized(db_path):
        return None
    return reset_seeded_dev_database(db_path, embedding_provider)
