"""Deterministic semantic paraphrase fixtures for seeded dev eval."""

from __future__ import annotations

# This file stores explicit checked-in paraphrase data. Runtime semantic MRR
# eval imports these strings directly; it does not synthesize queries dynamically.
# Tests enforce three non-empty queries per target, unique natural-language
# queries, banned-template guards, keyword-bag artifact guards, and a maximum
# copied span below ten contiguous tokens from each source memory.

from typing import TypedDict


class SemanticMRRFixtureEntry(TypedDict):
    """Semantic MRR fixture row for one seeded memory."""

    scope: str
    workspace_uid: str | None
    queries: tuple[str, str, str]


SEMANTIC_MRR_FIXTURE: dict[str, SemanticMRRFixtureEntry] = {
    "dev-user-001": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How do they enjoy spending time thinking about train journeys along "
            "the coast?",
            "What should I recall about their fondness for make-believe seaside "
            "rail routes with artistic details?",
            "When planning a weekend escape story, what kind of transport "
            "fantasy do they mention — one involving colorful little stations "
            "along the shore?",
        ),
    },
    "dev-user-002": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What collection do they maintain that organizes scenic pictures by "
            "landscape type?",
            "Tell me about the imaginary album they keep where postcards are "
            "grouped into four nature categories.",
            "If I wanted to browse their pretend photo collection, how would the "
            "pictures be sorted — by terrain like peaks, islands, deserts, and "
            "woodlands?",
        ),
    },
    "dev-user-003": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What is their ideal short fictional getaway composed of — a calm "
            "museum and an early walk?",
            "When they dream up a two-day escape, which two gentle activities do "
            "they always include?",
            "Describe the kind of pretend weekend trip they favor: one cultural "
            "stop plus a peaceful morning stroll.",
        ),
    },
    "dev-user-004": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What habit do they have around designing artificial city layouts "
            "and noting the pastry district?",
            "Tell me about the game they play where they draw made-up urban maps "
            "and highlight where the best fictional bakeries are.",
            "When they sketch an invented city, what specific landmark do they "
            "always identify — the area with the finest imagined bread and "
            "sweets?",
        ),
    },
    "dev-user-005": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What do they like to create for imaginary cabin stays where the "
            "climate shifts every hour?",
            "Recall their interest in writing supply lists for storybook "
            "cottages with rapidly changing weather.",
            "When preparing for a whimsical lodge visit, what organizational "
            "task do they enjoy — making a packing checklist for a place where "
            "it might rain, snow, and shine all in one afternoon?",
        ),
    },
    "dev-user-006": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which would they pick: a quiet scenic rail ride through an invented "
            "gorge, or a loud fantasy celebration?",
            "What preference do they hold about preferring serene observation "
            "over crowded spectacle when traveling in stories?",
            "If offered a choice between a glass-ceiling train journey across a "
            "fictional ravine and a bustling mythical festival, which experience "
            "would appeal more — and why does it involve panoramic windows?",
        ),
    },
    "dev-user-007": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How do they catalog dream locations — by the hue of the street "
            "lighting in each place?",
            "What unusual detail do they record about fantasy destinations in a "
            "private notebook?",
            "When they jot down places they hope to visit someday, what visual "
            "feature do they use to characterize each town — the color of its "
            "evening lamps?",
        ),
    },
    "dev-user-008": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of fictional coastal inn do they picture — one that "
            "offers a warm pear drink before a lighthouse stroll?",
            "Describe the make-believe seaside lodging they enjoy: a place with "
            "a specific tea service and an evening walk to the beacon.",
            "What two details define their ideal imaginary shorefront guesthouse "
            "— a fruit infusion served to visitors and a nearby tower with a "
            "guiding light?",
        ),
    },
    "dev-user-009": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What sort of structures do they add to a wish list for calm autumn "
            "evening crossings?",
            "Tell me about the collection of fictitious bridges they dream of "
            "traversing during peaceful fall nights.",
            "What themed list do they keep — spanning desired walkways to "
            "experience when the air is crisp and the sun sets early?",
        ),
    },
    "dev-user-010": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does a perfect make-believe travel day look like to them — no "
            "schedules, a couple of unplanned turns, and time for drawing?",
            "How would they design a relaxed fictional travel itinerary: "
            "unstructured, with two detours, and space for sketching?",
            "If they described their ultimate unhurried journey, what three "
            "elements would appear — freedom from alarms, a pair of spontaneous "
            "route changes, and an opportunity to draw?",
        ),
    },
    "dev-user-011": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What small vehicle do they favor for running errands in their "
            "imagined town — a teal bike with a bell?",
            "Describe their preferred mode of getting around the fictional "
            "village square for quick tasks.",
            "When they need to pick up a few things in the storybook downtown, "
            "what color and style of bicycle do they reach for, and what small "
            "accessory does it have?",
        ),
    },
    "dev-user-012": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How do they name pretend transit lines to make them easier to "
            "recall — using star patterns?",
            "What system do they use for labeling invented bus services so the "
            "routes are memorable?",
            "Tell me about their trick for remembering which imaginary coach "
            "goes where: they assign each line the name of a constellation.",
        ),
    },
    "dev-user-013": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Why do they choose tram seats at the back — to better view made-up "
            "wall paintings?",
            "Where do they prefer to sit on a fictional streetcar and what do "
            "they hope to spot from that spot?",
            "When riding an imaginary tram, what seating area offers the best "
            "vantage for admiring the invented city artwork, according to "
            "them?",
        ),
    },
    "dev-user-014": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What do they keep tucked inside a notebook for planning imaginary "
            "boat journeys — a fabricated schedule?",
            "Tell me about the pretend nautical timetable they maintain for "
            "route-planning diversions.",
            "What reference document do they fold into their journal to help "
            "plot storybook ferry adventures?",
        ),
    },
    "dev-user-015": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which would they choose for crossing a tiny invented campus: a "
            "quiet electric scooter or a car?",
            "What stance do they take on moving around a small fictional "
            "academic setting — preferring a near-silent two-wheeler?",
            "If they had to get from one end of a miniature storybook college to "
            "the other, what vehicle feels right to them and why does the "
            "quietness matter?",
        ),
    },
    "dev-user-016": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How do they orient themselves at fantasy rail stations — by noting "
            "which snack stand is closest to the departure display?",
            "What is their landmark for finding the right platform in an "
            "imaginary train terminal?",
            "When navigating a made-up transit hub, what specific kiosk do they "
            "use as a reference point relative to the schedule board?",
        ),
    },
    "dev-user-017": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of paths do they favor when strolling between invented "
            "districts — ones with painted distance markers?",
            "Describe the walking routes they enjoy in storybook neighborhoods: "
            "marked trails with artistic mileposts.",
            "When designing a fictional pedestrian route, what decorative "
            "element do they include every so often to show how far they've "
            "come?",
        ),
    },
    "dev-user-018": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What imaginary transport do they enjoy — a hillside cable car that "
            "stops midway for a view of scarlet roofs?",
            "Tell me about the fantasy lift ride they like, where the journey "
            "pauses halfway up to admire the town below.",
            "What specific detail do they appreciate about make-believe aerial "
            "trams: a deliberate halt partway that reveals a panorama of "
            "red-tiled buildings?",
        ),
    },
    "dev-user-019": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What do they maintain for a mint-green cargo bike named Clover — a "
            "fictional upkeep list?",
            "Describe the pretend record they keep for servicing their invented "
            "freight bicycle.",
            "What color is the made-up delivery cycle they care for, what is its "
            "name, and what kind of document tracks its maintenance?",
        ),
    },
    "dev-user-020": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How do they pick transportation in narratives — whichever option "
            "preserves the most time for letting the mind wander?",
            "What principle guides their choice of travel methods in stories: "
            "maximizing daydreaming opportunities?",
            "When characters in a tale need to get somewhere, what criterion "
            "does this person apply — which mode of movement leaves the greatest "
            "space for idle thought?",
        ),
    },
    "dev-user-021": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What genre do they enjoy where the main storyline can be postponed "
            "while they rearrange garden plots?",
            "Tell me about their taste for gentle exploration titles that allow "
            "ignoring the primary quest to tend flower beds.",
            "When playing a calm sandbox game, what side activity do they "
            "prioritize — reorganizing planted areas — even if the central "
            "mission waits?",
        ),
    },
    "dev-user-022": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of pretend puzzle games appeal to them — ones with penned "
            "clue journals and zero rushing timers?",
            "Describe the logbook-and-no-pressure style of brain teasers they "
            "gravitate toward.",
            "In an ideal fictional riddle game, what two features must be "
            "present: handwritten hints and the absence of any countdown "
            "clock?",
        ),
    },
    "dev-user-023": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What naming convention do they use for game save slots — "
            "atmospheric terms like drizzle and ember?",
            "How do they label their progress files in video games, drawing from "
            "weather and light vocabulary?",
            "When they start a new playthrough, what kind of words inspire the "
            "names they type into the save screen — misty, glowing, dusky?",
        ),
    },
    "dev-user-024": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of character do they like to roleplay — someone who "
            "resolves conflict by bartering dishes instead of gathering weapons?",
            "Tell me about their preference for protagonists who trade culinary "
            "creations rather than collect arms.",
            "In their ideal RPG, how does the hero solve problems — by "
            "exchanging recipes, not by amassing a sword collection?",
        ),
    },
    "dev-user-025": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What digital keepsake do they hold on to — a fabricated arcade coin "
            "from a moth-themed library delivery game?",
            "Describe the pixel-art memento they treasure from a title about "
            "insects carrying books.",
            "What imaginary token do they own that commemorates a retro-style "
            "game where winged nocturnal creatures serve as postal workers for a "
            "reading room?",
        ),
    },
    "dev-user-026": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When do round-based fights feel most satisfying — when the win "
            "display features tiny festive animations?",
            "What heightens their enjoyment of tactical combat: celebratory "
            "miniature visuals after a successful match?",
            "In a turn-oriented battle system, what post-victory detail matters "
            "to them — small, charming motion graphics on the results screen?",
        ),
    },
    "dev-user-027": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What audio palette do they prefer in game backgrounds — gentle "
            "synth chimes, rainy loops, and soft interface sounds?",
            "Describe the soundtrack style they favor: delicate electronic "
            "bells, drizzle ambience, and quiet menu clicks.",
            "When evaluating a game's music, what three elements tend to win "
            "them over — mellow synthesized tones, precipitation loops, and "
            "subtle button sounds?",
        ),
    },
    "dev-user-028": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What self-imposed rule do they follow in creative builder titles — "
            "constructing mirrored farms even when lopsided would be quicker?",
            "Tell me about their aesthetic choice in sandbox games: always "
            "placing crops and structures in balanced, matching layouts.",
            "When speed isn't the goal, why do they spend extra minutes ensuring "
            "their agricultural plots are perfectly even on both sides?",
        ),
    },
    "dev-user-029": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What condition must a made-up horror title meet before they'll try "
            "it — courteous spirits and cozy illumination?",
            "Under what circumstances would they consider a spooky game: if the "
            "ghosts are friendly and the lighting stays gentle?",
            "They normally steer clear of frightening fiction, but what two "
            "traits might change their mind — well-mannered apparitions and a "
            "warm, inviting glow throughout?",
        ),
    },
    "dev-user-030": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What odd habit do they have around fictional game characters — "
            "recording their birth dates to send digital pastry gifts?",
            "Why do they track the birthdays of made-up NPCs — so nobody misses "
            "out on a virtual baked treat?",
            "What peculiar calendar do they maintain inside their game notebook, "
            "and what small present do they give on each listed date?",
        ),
    },
    "dev-user-031": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of novels draw them in — ones with illustrated "
            "cartography and headings that feel like hidden entrances?",
            "Tell me about the two book features they love: a drawn map and "
            "chapter names that whisper of secret passages.",
            "When browsing for a story, what combination signals a must-read — a "
            "visual guide to the world and titles that evoke mysterious "
            "doorways?",
        ),
    },
    "dev-user-032": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What do they keep stocked in their imaginary reading corner — "
            "citrus biscuits and a blue woolen throw?",
            "Describe the pretend nook where they curl up with a book: two "
            "specific comforts are always within reach.",
            "If you were to set up a cozy story-time spot for them, what edible "
            "and what blanket would you provide, and what color is the "
            "blanket?",
        ),
    },
    "dev-user-033": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What twist do they enjoy in library-centered whodunits — the lost "
            "item is a page-marker, not a gem?",
            "Tell me about their preferred mystery premise: a missing "
            "placeholder strip rather than a stolen treasure.",
            "In detective tales set among bookshelves, what humble object do "
            "they want to be the center of the puzzle instead of something "
            "precious?",
        ),
    },
    "dev-user-034": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How do they organize imagined library shelves — by feeling, mixing "
            "tempestuous journeys with gentle comedies?",
            "What unusual sorting method do they apply to their pretend book "
            "collection: grouping by emotional tone?",
            "Instead of author or genre, what criterion guides the arrangement "
            "of their fantasy bookcases — placing stormy tales next to calm, "
            "funny ones?",
        ),
    },
    "dev-user-035": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of anthology appeals to them — tales about kind "
            "automatons caring for greenery on building tops?",
            "Describe the subject of their favorite short story collections: "
            "softhearted machines maintaining elevated gardens.",
            "What niche theme do they seek in compilations — mechanical beings "
            "with gentle dispositions tending plants on high ledges?",
        ),
    },
    "dev-user-036": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What physical book style do they favor in tales about roaming "
            "mapmakers — softcovers with rough-cut page borders?",
            "Tell me about the paperback format they prefer for stories of "
            "wandering cartographers: uneven, feathery edges.",
            "When the protagonist is a traveling chart-drawer, what tactile "
            "quality of the volume itself do they appreciate?",
        ),
    },
    "dev-user-037": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What rule governs their make-believe reading circle — every pick "
            "must feature at least one creature that speaks?",
            "Describe the one requirement for books chosen in their fictional "
            "club: the presence of a conversational animal.",
            "What unifying element must appear in every selection on their "
            "imaginary book-group roster?",
        ),
    },
    "dev-user-038": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What small detail do they revisit in stories — footnotes that hide "
            "tiny jokes about made-up scholars?",
            "Tell me about the ancillary text they love rediscovering: marginal "
            "comments with quiet humor at the expense of fictitious academics.",
            "Where do they find hidden delight in certain novels — among the "
            "annotations that poke gentle fun at imaginary historians?",
        ),
    },
    "dev-user-039": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What impossible memorabilia do they gather — autographs from "
            "writers whose works exist only in daydreams?",
            "Describe the collection of signatures they've assembled from "
            "novelists who aren't real.",
            "What kind of inscription do they treasure — signed pages from books "
            "that were never actually published outside their imagination?",
        ),
    },
    "dev-user-040": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What three endings do they hope for in a story — characters "
            "launching a patisserie, reviving a garden, or welcoming a drowsy "
            "feline?",
            "Tell me about the conclusions that satisfy them most: opening a "
            "bake shop, restoring greenery, or giving a home to a sleepy cat.",
            "When they near the final chapter, which outcomes feel right — a new "
            "pastry business, a renewed flower bed, or adopting a tired kitty?",
        ),
    },
    "dev-user-041": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What fantasy breakfast do they enjoy making — star-shaped tropical "
            "fruit flapjacks with spiced sugary clouds?",
            "Describe their lazy weekend morning creation: a pancake involving "
            "exotic fruit and a topping reminiscent of cinnamon mist.",
            "What two unusual elements appear in their favorite make-believe "
            "griddle cakes served on a slow Sunday?",
        ),
    },
    "dev-user-042": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What storied seasoning do they keep — a container marked lunar "
            "pepper for adding to broths?",
            "Tell me about the imaginary spice jar they reach for when preparing "
            "fictional soups.",
            "What label is on the pretend condiment tin they use to season "
            "pottages in made-up recipes, and what celestial body does it "
            "reference?",
        ),
    },
    "dev-user-043": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Why do they dice produce into tiny cubes — because imagined stews "
            "simply look neater that way?",
            "What precision habit do they apply to vegetable preparation when "
            "cooking in fantasy?",
            "When chopping ingredients for a storybook pot, what size do they "
            "aim for and what aesthetic reasoning drives that choice?",
        ),
    },
    "dev-user-044": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What do they enjoy assembling — meadow concert picnic menus with "
            "stone-fruit pastries and citrus-basil refreshment?",
            "Describe their ideal outdoor feast plan for a musical gathering in "
            "a field.",
            "What two items always appear when they design a basket for an "
            "open-air performance: a dessert with plums and a drink blending "
            "lemon and an herb?",
        ),
    },
    "dev-user-045": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What imaginary kitchen policy do they follow — adding a small "
            "sketch next to every untried dish?",
            "Tell me about their rule for new recipes: each one earns a doodle "
            "in the margin.",
            "What visual tradition accompanies any first attempt at a meal in "
            "their pretend culinary world — a quick drawing beside the "
            "instructions?",
        ),
    },
    "dev-user-046": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What do they like to bake for storybook neighbors — spherical "
            "loaves with decorative botanical slashes?",
            "Describe the bread they prepare for the invented community: round, "
            "with leaf-shaped scoring on top.",
            "What shape and what surface pattern characterize the oven goods "
            "they gift to fictional folks next door?",
        ),
    },
    "dev-user-047": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How do they categorize imaginary noodle toppings — using "
            "time-of-year labels instead of component lists?",
            "Tell me about their naming system for made-up pasta dressing: "
            "spring, summer, autumn, winter designations.",
            "What unconventional taxonomy do they apply to the sauces in their "
            "pretend recipe notes — seasonal names rather than ingredient "
            "descriptions?",
        ),
    },
    "dev-user-048": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of culinary plot do they find amusing — a story whose "
            "central tension is whether the custard needs additional vanilla?",
            "Describe the stakes they enjoy in cooking fiction: a debate over "
            "the correct quantity of a floral extract.",
            "In a tale set in a kitchen, what disagreement feels perfectly "
            "scaled to them — an argument about an aromatic liquid's proportion "
            "in a creamy dessert?",
        ),
    },
    "dev-user-049": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What material and palette do they prefer for mixing bowls — "
            "ceramic, in invented shades like cloudberry and tidepool?",
            "Tell me about the vessel style they favor for blending: earthenware "
            "in fantasy hues.",
            "When choosing a bowl to combine ingredients, what three imaginary "
            "color names attract them?",
        ),
    },
    "dev-user-050": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What do they enjoy putting together — imaginary midday meal boxes "
            "with miniature waffles, cucumber crescents, and fruit-infused tea?",
            "Describe the pretend packed lunches they assemble for work or outings.",
            "What three items typically fill their fantasy lunch container — "
            "tiny grid-patterned pastries, cool moon-shaped slices, and a warm "
            "red beverage?",
        ),
    },
    "dev-user-051": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What morning routine do they picture — soft movements in a bright "
            "room dappled with fern silhouettes?",
            "Tell me about the gentle stretching session they imagine in a "
            "sun-filled studio with plant shadows.",
            "When they visualize an ideal start to the day, what activity and "
            "what kind of light and botanical backdrop are present?",
        ),
    },
    "dev-user-052": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How do they track their walking habit — by counting circuits around "
            "a small comma-shaped pond?",
            "Describe the metric they use for their stroll consistency: laps of "
            "a tiny curved lake.",
            "What landmark defines the walking route they measure their streak "
            "against, and what punctuation mark does its outline resemble?",
        ),
    },
    "dev-user-053": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What charming detail do they include in workout plans — recovery "
            "days named after cozy creatures like otter and dormouse?",
            "Tell me about how they label rest periods in their exercise "
            "schedule using animal monikers.",
            "Instead of calling them 'off days,' what cute naming approach do "
            "they take, pulling from the names of snuggly fauna?",
        ),
    },
    "dev-user-054": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What type of free weights do they picture for a compact flat gym — "
            "small ones tinted a soft purple?",
            "Describe the hand weights they'd choose for a modest apartment "
            "workout space, including the color.",
            "When outfitting a tiny home exercise corner, what shade and size of "
            "dumbbell feels right to them?",
        ),
    },
    "dev-user-055": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What sticker system do they use for fitness goals — cloud and green "
            "hill shapes moved on a chart after each session?",
            "Tell me about the visual reward method they employ to mark "
            "completed workouts.",
            "How do they tangibly track progress: by relocating adhesive "
            "pictures of sky formations and tiny mounds across a paper display "
            "after every finished routine?",
        ),
    },
    "dev-user-056": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of low-pressure movement do they enjoy — dance sessions "
            "synced to radio broadcasts from an airborne city?",
            "Describe their preferred cardio: relaxed choreography paired with "
            "transmissions from a floating metropolis.",
            "What audio source guides their gentle dance workouts, and what "
            "feeling do the opening tracks aim to evoke — the start of a new "
            "day?",
        ),
    },
    "dev-user-057": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Where do they like fictional hiking paths to conclude — at a tea "
            "stall, not a peak plaque?",
            "Tell me about their ideal trail ending in stories: a warm drink "
            "stand, with a flask of imaginary brew as incentive for the last "
            "curve.",
            "What destination and what carried reward define their perfect "
            "make-believe trek — a beverage cart at the terminus and a thermos "
            "treat for the final bend?",
        ),
    },
    "dev-user-058": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What indoor pool environment appeals to them — lanes marked by "
            "painted aquatic creatures and a cooldown of three unhurried "
            "backstroke lengths?",
            "Describe their swimming preference: a calm natatorium with tile "
            "fish art and a deliberate winding-down routine.",
            "How do they track laps in a serene pool, what decorates the lane "
            "lines, and how many slow back-crawl passes end the session?",
        ),
    },
    "dev-user-059": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What self-care checklist do they maintain during extended "
            "map-drawing sessions — shoulder rolls and wrist circles with "
            "leaf-mark rewards?",
            "Tell me about the posture-break system they follow when absorbed in "
            "long cartographic work.",
            "What gentle reminders do they set while making maps for hours, and "
            "what tiny symbol do they earn for each completed break?",
        ),
    },
    "dev-user-060": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How do they celebrate personal bests — with a sparkling fruit drink "
            "and a garden stroll, valuing steadiness over big leaps?",
            "What reward and what reflection matter after achieving a fitness "
            "milestone?",
            "When they hit a record, what treat do they give themselves and what "
            "philosophy do they hold — consistency trumps chasing flashy "
            "numbers?",
        ),
    },
    "dev-user-061": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What instrumental sound do they enjoy — harp, soft percussion, and "
            "remote rainfall ambience blended together?",
            "Describe the gentle acoustic mix they favor: plucked strings, light "
            "rhythm, and distant drizzle.",
            "What three components make up their ideal background listening — a "
            "classical string instrument, brushed drum hits, and the sound of "
            "faraway rain?",
        ),
    },
    "dev-user-062": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What impossible event stub do they possess — a concert pass from a "
            "group that only performs as the moon appears?",
            "Tell me about the cherished fictional ticket they own for a show "
            "that happens exclusively at a particular celestial moment.",
            "What imaginary admission slip do they treasure, and what "
            "astronomical timing governs the performance it grants entry to?",
        ),
    },
    "dev-user-063": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What lyrical themes and musical qualities appeal to them — cozy "
            "low-end melodies and verses mentioning vessels, reading halls, or "
            "warm-season storms?",
            "Describe the song ingredients they're drawn to: a full bass "
            "presence and words about maritime craft, book collections, or "
            "hot-weather tempests.",
            "When a track features a rich bottom register and storytelling about "
            "sailing, libraries, or seasonal squalls, how do they typically "
            "react?",
        ),
    },
    "dev-user-064": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "By what unusual criterion do they sequence imaginary compilation "
            "tapes — hue, not style or year?",
            "Tell me about their method for organizing pretend mixtapes: "
            "grouping tracks by shade.",
            "When building a fantasy playlist, what visual property do they use "
            "to order the songs instead of genre or chronological data?",
        ),
    },
    "dev-user-065": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What instrument do they imagine practicing — a tangerine-colored "
            "miniature guitar named Clementine?",
            "Describe the fantasy instrument they strum: a small, citrus-hued "
            "uke with a personal name.",
            "What color and what name belong to the make-believe four-stringed "
            "instrument they enjoy learning simple chords on?",
        ),
    },
    "dev-user-066": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What fictional venue do they like — cafés whose in-house ensemble "
            "performs soft dances during the reading period?",
            "Tell me about the dream coffeehouse where the resident musicians "
            "play gentle two-step tunes while patrons browse books.",
            "What two activities coexist in their ideal pretend café — a live "
            "band offering calm ballroom numbers and a designated quiet reading "
            "hour?",
        ),
    },
    "dev-user-067": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What creative naming do they engage in — dreaming up record titles "
            "such as Lantern Orchard and Velvet Comet?",
            "Describe the hobby of inventing album names from evocative word pairs.",
            "What are a couple of examples of the imagined LP labels they jot "
            "down, blending light sources with nature or soft fabric with "
            "celestial bodies?",
        ),
    },
    "dev-user-068": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What storybook object fascinates them — melodic boxes that shift "
            "their song whenever a concealed drawer slides open?",
            "Tell me about the whimsical music-playing trinket that changes its "
            "tune based on hidden compartment access.",
            "What property of certain narrative music boxes captures their "
            "imagination: the melody transforms each time a secret storage space "
            "is revealed?",
        ),
    },
    "dev-user-069": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Why do they hum while preparing food — because make-believe soups "
            "supposedly gain flavor from a small tune?",
            "What quirky belief do they hold about cooking: a little melody "
            "improves the taste of imaginary broths?",
            "When standing at the stove in a fantasy kitchen, what sound do they "
            "make and what superstitious benefit do they think it brings to the "
            "pot?",
        ),
    },
    "dev-user-070": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What pretend broadcast do they enjoy — stations that read weather "
            "bulletins for undiscovered landmasses?",
            "Describe the fictitious radio programming they tune into: forecasts "
            "for islands absent from any chart.",
            "What kind of imaginary channel captures their attention — one that "
            "announces climatic conditions for shores no explorer has "
            "documented?",
        ),
    },
    "dev-user-071": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What pet lives in their imagination — a black-and-white feline "
            "named Miso who absconds with plush page-markers?",
            "Tell me about the made-up cat they describe: a tuxedo-patterned "
            "companion with a habit of pilfering reading accessories.",
            "What is the name and coat pattern of their pretend kitty, and what "
            "item does it repeatedly steal from the armchair?",
        ),
    },
    "dev-user-072": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of make-believe canine jobs amuse them — official greeter "
            "at a beacon tower or supervisor of pastry shop crumbs?",
            "Describe the serious-sounding yet whimsical occupations they assign "
            "to fictional dogs.",
            "What two imaginary roles for pups do they find delightful — "
            "welcoming visitors at a coastal light and inspecting baking "
            "debris?",
        ),
    },
    "dev-user-073": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of tank do they envision — one with translucent swimmers "
            "that emit light whenever humor is present?",
            "Tell me about the fantasy fishbowl where the inhabitants glow in "
            "response to punchlines.",
            "What triggers the luminescence of the aquatic creatures in their "
            "imagined aquarium: the sound of someone telling a funny story?",
        ),
    },
    "dev-user-074": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What trait do they value in storybook birds — the ability to echo "
            "kind words rather than private information?",
            "Describe their preference for avian companions in tales: ones that "
            "repeat praise, not secrets.",
            "When a feathered friend appears in a narrative, what should its "
            "mimicry focus on — compliments, never confidential matters?",
        ),
    },
    "dev-user-075": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What bunny do they imagine — one called Pollen who dozes inside a "
            "container of freshly laundered cloths?",
            "Tell me about the rabbit they've dreamed up: its name and its "
            "favorite sleeping spot.",
            "What is the chosen napping location for their pretend long-eared "
            "pet, and what is the pet's nature-inspired name?",
        ),
    },
    "dev-user-076": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What do they enjoy creating — miniature fictional waterproof coats "
            "for short-legged dogs guarding fungus plots?",
            "Describe the tiny garments they design for corgis tasked with "
            "watching over mushroom beds.",
            "What breed of dog receives their invented rainwear, and what "
            "botanical responsibility does that dog hold in their imagination?",
        ),
    },
    "dev-user-077": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What care chart do they maintain for pretend animals — a schedule "
            "written with violet-colored ink listing treat times?",
            "Tell me about the husbandry record they keep: colored writing and "
            "snack-time entries.",
            "What hue is the pen they use for their imaginary pet timeline, and "
            "what information does the chart primarily track?",
        ),
    },
    "dev-user-078": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What role do they value for creature sidekicks in interactive "
            "entertainment — foraging for plants instead of engaging in combat?",
            "Describe their ideal animal ally in games: one that helps locate "
            "botanical items rather than fighting adversaries.",
            "In video games, how do they prefer their companion beasts to "
            "contribute — by seeking out greenery, not by battling beasts?",
        ),
    },
    "dev-user-079": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What leisurely reptile lives in their stories — a drowsy shelled "
            "creature named Button that can distinguish among evening meal "
            "signals?",
            "Tell me about the fictional tortoise they describe: its name, its "
            "general energy level, and its special auditory skill.",
            "How many different supper chimes can their imaginary slow-moving "
            "pet recognize, and what is its moniker?",
        ),
    },
    "dev-user-080": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What do they enjoy in animal adoption tales — each new companion "
            "receiving a handcrafted cover and a bright windowsill?",
            "Describe the ending they hope for in pet rescue stories: a woven "
            "wrap and a sunlit perch for every creature.",
            "What two comforting provisions do they want every adopted animal to "
            "receive in a heartwarming fiction — a knit throw and a spot bathed "
            "in daylight?",
        ),
    },
    "dev-user-081": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How do they enjoy studying invented writing systems — by "
            "transcribing pastry shop signage from imaginary coastal "
            "settlements?",
            "Tell me about their method for learning make-believe alphabets: "
            "copying bakery placards in fictional harbour villages.",
            "What real-world inspiration do they use to practice pretend scripts "
            "— the storefront lettering of dreamt-up seaside bakehouses?",
        ),
    },
    "dev-user-082": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of study tracker do they keep — one with golden adhesive "
            "stars for cartographic symbols, avian sounds, and broth "
            "terminology?",
            "Describe the reward chart they use for learning: shiny foil "
            "stickers earned across three diverse subjects.",
            "What three categories appear on their imaginary progress board, and "
            "what color are the markers of achievement?",
        ),
    },
    "dev-user-083": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What makes a tutorial appealing to them — including a miniature "
            "practice build and a lighthearted dictionary of errors?",
            "Tell me about the two features they value in instructional content: "
            "a small hands-on project and a cheerful typo reference.",
            "When evaluating a how-to guide, what complementary elements win "
            "their approval — a compact exercise and a whimsical listing of "
            "common mistakes?",
        ),
    },
    "dev-user-084": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What do they enjoy committing to memory — fabricated star groupings "
            "shaped like cups, animals, and wind-powered mills?",
            "Describe their mnemonic hobby: learning invented celestial patterns "
            "resembling crockery, wild creatures, and grain-grinding structures.",
            "What three everyday objects inspire the shapes of the imaginary "
            "constellations they memorize?",
        ),
    },
    "dev-user-085": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What two-column note format do they prefer — practical insights on "
            "the left and fanciful wonderings on the right?",
            "Tell me about their organized page layout: useful knowledge in one "
            "column, playful what-ifs in the other.",
            "When jotting ideas in a notebook, how do they spatially separate "
            "actionable content from curious musings?",
        ),
    },
    "dev-user-086": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How do they like study sessions to conclude — by sketching a small "
            "illustration of the concept they grasped?",
            "Describe their preferred wind-down after absorbing new material: a "
            "tiny drawing capturing the lesson.",
            "What creative ritual marks the end of a learning period for them — "
            "translating understanding into a simple visual?",
        ),
    },
    "dev-user-087": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What sort of review tool do they keep — a fictional deck about "
            "cloud varieties from a narrative meteorology school?",
            "Tell me about the pretend study cards they maintain: focused on "
            "atmospheric formations in a whimsical weather curriculum.",
            "What subject do their imaginary flashcards cover, and what "
            "fictional institution are they associated with?",
        ),
    },
    "dev-user-088": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What do they imagine happening after a fictional workshop — "
            "participants exchanging handcrafted reading accessories?",
            "Describe the closing ritual of their dream class: students swapping "
            "artisanal placeholders.",
            "At the conclusion of a made-up educational session, what item do "
            "attendees gift one another — and what is it used for?",
        ),
    },
    "dev-user-089": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of teachers do they admire in stories — those who clarify "
            "tough concepts through gardens, vessels, and cookware?",
            "Tell me about the three everyday metaphors they feel make the best "
            "narrative educators.",
            "When an instructor in a tale breaks down a difficult topic, what "
            "trio of familiar objects do they hope will appear in the "
            "explanation — patches of earth, watercraft, and cooking pots?",
        ),
    },
    "dev-user-090": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What pace do they prefer for acquiring abilities — mastering one "
            "micro-skill and naming each new stage after an amiable orbiter?",
            "Describe their incremental approach to growth: a single small "
            "competency at a time, with planet-themed milestone labels.",
            "How do they celebrate progress steps in their learning journey — by "
            "associating each achievement with a friendly celestial body?",
        ),
    },
    "dev-user-091": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What interior qualities do they favor — warm illumination, curved "
            "furnishings, and open shelves of vivid tableware?",
            "Tell me about the three elements that define their ideal room: "
            "gentle light sources, smooth-edged pieces, and displays of bright "
            "ceramics.",
            "When designing a living space, what combination feels right — cozy "
            "lamps, non-angular furniture, and visible stacks of colorful "
            "dishes?",
        ),
    },
    "dev-user-092": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What do they place near the front door — a receptacle for shore "
            "pebbles, backup keys, and borrowing slips?",
            "Describe the catch-all they maintain in a make-believe entrance for "
            "natural souvenirs, spare access, and reading records.",
            "What three categories of items gather in the fictional hallway "
            "basket they've imagined?",
        ),
    },
    "dev-user-093": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What fabric, color, and length do they prefer for window dressings "
            "in invented flats — flax-based, sage-toned, and slightly dragging?",
            "Tell me about their ideal drapery: a natural weave in a muted green "
            "that puddles a bit on the floor.",
            "When outfitting imaginary apartment windows, what material and "
            "shade do they select, and what deliberate sizing quirk do they "
            "include?",
        ),
    },
    "dev-user-094": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How do they arrange potted greenery — in clusters of three, five, "
            "or seven next to bright openings?",
            "Describe their plant placement rule: grouping indoor flora in odd "
            "quantities beside sunlit panes.",
            "What numeric pattern guides the positioning of their houseplants, "
            "and what environmental factor determines the location?",
        ),
    },
    "dev-user-095": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of armchair do they envision — one that rotates to face "
            "either a rainy window or a hearth?",
            "Tell me about the swiveling seat they dream of: it turns toward "
            "precipitation on one side and warm flames on the other.",
            "What dual-facing capability does their fantasy reading chair "
            "possess, and what two views does it offer?",
        ),
    },
    "dev-user-096": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What do they put on their workspace walls — boards covered in "
            "charts, meal instructions, and kind reminder slips?",
            "Describe the pinboard setup in their ideal study: a collage of "
            "cartography, dishes, and soft nudges.",
            "What three kinds of paper decor do they imagine above their desk — "
            "navigational drawings, culinary formulas, and gentle "
            "self-prompts?",
        ),
    },
    "dev-user-097": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What floor covering style attracts them — mats with subtle "
            "geometric motifs reminiscent of miniature garden walkways?",
            "Tell me about their rug preference: quiet angular designs that "
            "evoke small horticultural paths.",
            "What does the pattern on their ideal carpet suggest to them — tiny "
            "trails through a planted space?",
        ),
    },
    "dev-user-098": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How do they outfit a spare bedroom — with fluffy cloud-shaped "
            "cushions and a container of minty candy sticks?",
            "Describe the provisions they stock in a make-believe visitor's "
            "room: two specific comfort items.",
            "What pillow form and what edible treat await anyone staying in "
            "their imaginary guest quarters?",
        ),
    },
    "dev-user-099": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What organizing system do they picture in a fantasy cookspace — "
            "cups suspended by hue and stirring implements resting in a cobalt "
            "pot?",
            "Tell me about the color-coded hanging storage and the blue vessel "
            "for utensils in their dream kitchen.",
            "What two visual rules govern their imagined culinary workspace: a "
            "chromatic arrangement of drinkware and a navy container for mixing "
            "tools?",
        ),
    },
    "dev-user-100": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How would they describe their preferred tranquil decor — a blend of "
            "coastal beacon-keeper dwelling and gentle woodland studio?",
            "What two-part label captures their calm interior aesthetic: "
            "lighthouse cottage meets soft forest workshop?",
            "Tell me about the dual-inspired home vibe they gravitate toward — "
            "something maritime and guiding combined with a serene, tree-filled "
            "craft space.",
        ),
    },
    "dev-workspace-01-001": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "How should CedarLedger divide access between owners, report "
            "reviewers, and sales clerks?",
            "A clerk can see admin settings after entering daily sales; "
            "which permissions memory describes the intended role split?",
            "Remember that CedarLedger separates banking approval, "
            "reporting access, and counter-entry duties for small "
            "workshops.",
        ),
    },
    "dev-workspace-01-002": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Who is allowed to see payroll notes and owner withdrawal "
            "details in CedarLedger?",
            "If a regular teammate can browse compensation records while "
            "reviewing expenses, what privacy boundary was missed?",
            "Keep sensitive pay and owner-draw information limited to "
            "finance admins, not routine bookkeeping users.",
        ),
    },
    "dev-workspace-01-003": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What access level should a newly invited bookkeeper receive "
            "before the owner grants more rights?",
            "An invited bookkeeper starts editing entries on first login "
            "without approval; which onboarding rule should prevent "
            "that?",
            "New CedarLedger bookkeeping invitees begin as reviewers and "
            "need owner approval before editing.",
        ),
    },
    "dev-workspace-01-004": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Where must CedarLedger enforce protection for bills, file "
            "attachments, and month-end review actions?",
            "A hidden menu link is the only thing stopping attachment "
            "downloads; what security reminder applies?",
            "Use backend authorization checks for financial endpoints, "
            "not just UI navigation hiding.",
        ),
    },
    "dev-workspace-01-005": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What can cash-drawer clerks do, and which CedarLedger "
            "settings are off limits to them?",
            "A clerk entering supplier receipts can also edit payout "
            "accounts; which role restriction is being violated?",
            "Daily takings and vendor slips are clerk tasks, but tax, "
            "payout, and billing configuration stay protected.",
        ),
    },
    "dev-workspace-01-006": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What should happen to cached permissions when a user "
            "switches CedarLedger workshops?",
            "After changing workspaces, buttons from the previous "
            "account still look enabled; what bug fix is needed?",
            "Clear local capability grants whenever the workspace "
            "selector changes so the wrong account cannot borrow old "
            "rights.",
        ),
    },
    "dev-workspace-01-007": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What safeguards are required when CedarLedger ownership is transferred?",
            "An owner handoff proceeds without another login challenge "
            "or summary screen; which transfer requirement covers this?",
            "Ownership changes need fresh authentication, an audit "
            "record of both parties, and a clear irreversible-action "
            "confirmation.",
        ),
    },
    "dev-workspace-01-008": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What information may CedarLedger support staff inspect "
            "during troubleshooting?",
            "A help-desk view exposes transaction descriptions and "
            "balance details while diagnosing an issue; what privacy "
            "rule applies?",
            "Support can use diagnostic fields, but private transaction "
            "content, attachment previews, and balances must remain "
            "masked.",
        ),
    },
    "dev-workspace-01-009": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "How should permissions work for an archived CedarLedger workshop?",
            "Members can invite people and edit historical records in an "
            "archived workspace; which rule should stop that?",
            "Archived workshops are read-only for summaries, with only "
            "owners able to reopen or change ledger records.",
        ),
    },
    "dev-workspace-01-010": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What should CedarLedger do to active sessions after a "
            "password is changed?",
            "An old report tab exports a ledger package after the user "
            "changed their password; what regression case covers this?",
            "Password changes should kill other sessions, keep the "
            "refreshed current one, and force stale tabs to "
            "reauthorize.",
        ),
    },
    "dev-workspace-01-011": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Which export formats does CedarLedger offer for reviewing "
            "monthly workshop records?",
            "A workshop owner wants both spreadsheet-friendly totals and "
            "structured data; what export support should exist?",
            "CedarLedger monthly exports include CSV and JSON so owners "
            "can review income, expenses, and category totals "
            "elsewhere.",
        ),
    },
    "dev-workspace-01-012": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Why should CedarLedger put a generated time marker into "
            "monthly package names?",
            "Repeated report downloads for the same date span are hard "
            "to distinguish; which naming requirement solves that?",
            "Monthly report filenames need generation timestamps so "
            "identical ranges from different pulls remain separate.",
        ),
    },
    "dev-workspace-01-013": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What kind of sample accounting rows should CedarLedger "
            "development exports use?",
            "A dev export contains realistic personal vendors and "
            "precise amounts; what fixture guidance keeps them "
            "harmless?",
            "Use generic vendor examples, rounded values, and benign "
            "reference numbers in development accounting output.",
        ),
    },
    "dev-workspace-01-014": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What column ordering must CedarLedger spreadsheet exports keep stable?",
            "A migration moved the debit field ahead of description and "
            "reviewer macros broke; what test expectation applies?",
            "Spreadsheet columns for dates, IDs, accounts, categories, "
            "descriptions, debit and credit values, currency, and batch "
            "markers must stay predictable.",
        ),
    },
    "dev-workspace-01-015": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What should the planned restorable CedarLedger snapshot "
            "include and exclude?",
            "A restore bundle includes local file paths and applies "
            "without showing counts; which task note addresses that?",
            "The ledger snapshot should cover records and report "
            "metadata, omit secrets and paths, and preview record totals "
            "first.",
        ),
    },
    "dev-workspace-01-016": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What caused April workshop expenses to appear in the wrong "
            "order in CedarLedger exports?",
            "The monthly spreadsheet is alphabetized by memo text "
            "instead of transaction chronology; which bug does that "
            "match?",
            "April expense rows were sorted by description when they "
            "should have followed the transaction date.",
        ),
    },
    "dev-workspace-01-017": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What timezone should CedarLedger use for generated archive "
            "artifact timestamps?",
            "Archive names become ambiguous around daylight-saving "
            "changes while reports show local workspace time; what "
            "packaging default fixes this?",
            "Package filenames should use UTC generation times even if "
            "report contents display the workspace timezone.",
        ),
    },
    "dev-workspace-01-018": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What examples belong in CedarLedger archive bundles for "
            "screenshots and demos?",
            "A sample archive names real brands and personal payees; "
            "which content guideline should replace those descriptions?",
            "Archive bundles need plain generic ledger examples like "
            "workshop costs and refunds, avoiding real names or "
            "brands.",
        ),
    },
    "dev-workspace-01-019": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "How should CedarLedger explain the difference between "
            "restore bundles and spreadsheets?",
            "A reviewer cannot tell whether to download a state package "
            "or a totals spreadsheet; which helper-note requirement "
            "applies?",
            "State bundles restore the app, spreadsheets are for "
            "reviewing rows and totals, and both should share range "
            "cutoff rules.",
        ),
    },
    "dev-workspace-01-020": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What should the monthly archive workflow write to its "
            "manifest after packaging?",
            "A failed CedarLedger archive leaves partial files and no "
            "completion proof; which workflow rule handles this?",
            "Monthly packages need a checksum note, confirmation of "
            "completion, and cleanup of incomplete artifacts on "
            "failure.",
        ),
    },
    "dev-workspace-01-021": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "How does CedarLedger distinguish money received from "
            "amounts still owed at closeout?",
            "A closeout screen blends paid cash with "
            "billed-but-unsettled work; which totals rule should guide "
            "it?",
            "Collected revenue and outstanding balances should be "
            "calculated separately for workshop owner review.",
        ),
    },
    "dev-workspace-01-022": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What should CedarLedger compare during month-end expense review?",
            "Imported vendor charges lack receipts but are not flagged; "
            "which reconciliation memory is relevant?",
            "Month-end review should match expense proof against imports "
            "and call out vendor charges without support.",
        ),
    },
    "dev-workspace-01-023": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What must be present before a settled customer bill counts "
            "in closed monthly totals?",
            "A paid invoice appears in closeout without method, date, or "
            "ledger link; which validation rule applies?",
            "Settled bills need payment date, payment method, and a "
            "linked ledger transaction before closeout totals include "
            "them.",
        ),
    },
    "dev-workspace-01-024": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What signals should CedarLedger use when matching records together?",
            "A pairing algorithm only compares exact memo wording and "
            "misses likely matches; which matching guidance improves it?",
            "Record matching should weigh amounts, dates, counterparty "
            "names, and reference details rather than memo text alone.",
        ),
    },
    "dev-workspace-01-025": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What February closeout problem overstated CedarLedger's received revenue?",
            "Expense rows look fine, but two unpaid customer bills are "
            "still counted as settled cash; which bug note explains it?",
            "February review inflated revenue because open bills were "
            "included even though cash had not arrived.",
        ),
    },
    "dev-workspace-01-026": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "How should CedarLedger explain differences in month-end totals?",
            "A closeout mismatch appears with no reason shown; which "
            "guidance lists missing proof, open balances, duplicates, "
            "and pending items?",
            "Month-end variance messaging should name concrete causes "
            "such as unsupported expenses, unpaid customers, duplicate "
            "imports, or records awaiting review.",
        ),
    },
    "dev-workspace-01-027": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What filter is still needed before finalizing CedarLedger "
            "monthly reports?",
            "Users cannot isolate uncleared materials purchases during "
            "closeout; which backlog item should be remembered?",
            "Add a way to inspect workshop supply charges that have not "
            "yet been cleared before approval.",
        ),
    },
    "dev-workspace-01-028": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "How should partial customer payments be represented in "
            "CedarLedger revenue and status?",
            "A partially paid bill disappears from open records after "
            "the first payment; what closeout behavior is expected?",
            "Received portions can count as collected, but the bill "
            "remains open until the remaining amount is fully paid.",
        ),
    },
    "dev-workspace-01-029": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What bug involved deleting expense proof during CedarLedger "
            "closeout review?",
            "A transaction stays marked complete after its supporting "
            "receipt is removed; which validation defect matches this?",
            "Removing proof should reopen the related expense for "
            "monthly validation instead of leaving it complete.",
        ),
    },
    "dev-workspace-01-030": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What checklist must be complete before CedarLedger allows "
            "monthly approval?",
            "The approval button activates while imported records are "
            "neither cleared, excluded, nor deferred; what rule should "
            "disable it?",
            "Every import needs a cleared, reasoned exclusion, or "
            "carry-forward decision before month-end approval can "
            "proceed.",
        ),
    },
    "dev-workspace-02-001": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What field types can editors add from the Northstar Forms "
            "builder palette?",
            "An editor needs photos, signatures, locations, dates, and "
            "choice prompts in one form; which builder capability covers "
            "this?",
            "Northstar Forms pages can be composed from common text, "
            "numeric, media, location, signature, date, and "
            "single-choice inputs.",
        ),
    },
    "dev-workspace-02-002": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Why does the Northstar Forms schema keep field IDs immutable?",
            "A label rename breaks older submissions because the "
            "internal identifier changed; which schema rule prevents "
            "that?",
            "Keep stable hidden field IDs so saved responses survive "
            "editor-facing label changes.",
        ),
    },
    "dev-workspace-02-003": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Where should Northstar Forms show conditional display rules to editors?",
            "A branching rule is buried in global settings and the "
            "affected prompt is hard to find; what UI placement is "
            "preferred?",
            "Show visibility conditions next to the prompt they control "
            "rather than hiding them on a distant settings page.",
        ),
    },
    "dev-workspace-02-004": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What should be preserved when cloning an input in Northstar "
            "Forms template editing?",
            "A duplicated field loses its help text and visibility "
            "behavior; which cloning expectation was missed?",
            "Cloned inputs should carry their guidance copy, "
            "constraints, and display behavior with them.",
        ),
    },
    "dev-workspace-02-005": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "How should repeatable sections support equipment "
            "inspections in Northstar Forms?",
            "A crew records multiple assets in one visit but repeated "
            "items share one completion status; which repeat-section "
            "rule applies?",
            "Each repeated inspection item needs its own completion "
            "state and clear visual boundaries in preview.",
        ),
    },
    "dev-workspace-02-006": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What warning should authors see for a required item inside "
            "a conditional area?",
            "A mandatory field may never appear because of branching, "
            "yet the editor gets no warning; what authoring safeguard is "
            "needed?",
            "Warn in that item's settings when a must-fill prompt is "
            "controlled by a condition, with a jump to the controlling "
            "question.",
        ),
    },
    "dev-workspace-02-007": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What bug occurs when the controlling prompt for a Northstar "
            "Forms condition is removed?",
            "Deleting a parent question leaves a stale visibility rule "
            "and an empty card in preview; which cleanup is required?",
            "Before saving, remove orphaned conditional rules when their "
            "controlling question no longer exists.",
        ),
    },
    "dev-workspace-02-008": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "How should Northstar Forms handle editor changes when "
            "connectivity is poor?",
            "A designer changes layout offline and loses work before "
            "publishing; which local-save behavior should protect it?",
            "Authoring sessions should save on the device after each "
            "change and wait to publish until service is reliable.",
        ),
    },
    "dev-workspace-02-009": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What should the Northstar Forms technical preview show "
            "before a design ships?",
            "Developers need to compare branching order and nested "
            "repeat sections with the renderer; which preview feature "
            "supports this?",
            "The preview should expose repeat boundaries, nesting order, "
            "and branching paths to catch runtime ordering mistakes.",
        ),
    },
    "dev-workspace-02-010": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Which controls belong near numeric and photo field type "
            "selection in Northstar Forms?",
            "An editor cannot find decimal precision or image limit "
            "settings for a prompt; which configuration note applies?",
            "Number fields need min, max, units, and precision controls, "
            "while photo fields need limits and caption options "
            "nearby.",
        ),
    },
    "dev-workspace-02-011": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "How long should Northstar Forms keep offline drafts on a device?",
            "A tablet automatically deletes a field draft before the "
            "crew lead acts; which offline draft rule was violated?",
            "Offline drafts stay local until the lead intentionally "
            "submits them or removes them.",
        ),
    },
    "dev-workspace-02-012": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Which timestamp should order queued Northstar Forms "
            "submissions after sync?",
            "Receipts are sorted by upload time, hiding the actual field "
            "sequence; what chronology rule should be used?",
            "Preserve original completion time separately from server "
            "sync time, and order receipts by when crews finished the "
            "work.",
        ),
    },
    "dev-workspace-02-013": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What details should a Northstar Forms sync receipt include?",
            "A server acknowledgement lacks the draft identifier and "
            "form name; which receipt fields are expected?",
            "Receipts should show the form name, local draft ID, server "
            "submission ID, and acknowledgement time.",
        ),
    },
    "dev-workspace-02-014": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "How should Northstar Forms process saved work when the "
            "connection returns?",
            "One queued item has a rules conflict and blocks all later "
            "uploads; what backlog behavior is intended?",
            "Send the oldest saved submissions first and keep processing "
            "the queue even if one item needs conflict handling.",
        ),
    },
    "dev-workspace-02-015": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Why do Northstar Forms field crews need an emergency "
            "package for tablet-stored work?",
            "A damaged device still has unsynced entries before shift "
            "change; which handoff capability is needed?",
            "Provide an emergency export or transfer package so local "
            "tablet entries can move to the next crew.",
        ),
    },
    "dev-workspace-02-016": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What bug can happen if a locally stored form is edited "
            "after it joins the outbound queue?",
            "The payload waiting to upload changes after the user edits "
            "the local draft, and the confirmation names another "
            "version; which defect is this?",
            "Queued sync payloads must not be overwritten by later local "
            "edits that make the receipt describe the wrong version.",
        ),
    },
    "dev-workspace-02-017": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What autosave indicator should Northstar Forms show during "
            "long inspections?",
            "Signal drops between sections and the crew cannot tell "
            "whether the tablet saved the latest answers; what UI "
            "reminder applies?",
            "After every autosave, show a clear local-device saved state "
            "so offline inspectors trust their progress.",
        ),
    },
    "dev-workspace-02-018": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What different states should the Northstar Forms reconnect "
            "banner distinguish?",
            "A generic online banner treats no pending work, active "
            "uploads, completed confirmations, and conflicts the same; "
            "what should change?",
            "Reconnect messaging needs separate action text for empty "
            "queue, transmitting items, confirmed transfers, and "
            "conflicts needing attention.",
        ),
    },
    "dev-workspace-02-019": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "How do local draft retention and confirmation retention "
            "differ in Northstar Forms settings?",
            "The settings screen shows only one retention value, "
            "confusing workspace draft storage with submitted-form "
            "confirmations; which config note applies?",
            "Display workspace-specific local draft retention beside "
            "confirmation retention that follows the audit log policy.",
        ),
    },
    "dev-workspace-02-020": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What should the next Northstar Forms resilience test cover?",
            "QA needs an offline-to-online scenario with restart "
            "recovery, handoff, confirmations, and spreadsheet output "
            "for blocked work; which test plan matches?",
            "Test airplane-mode creation, restart recovery, service "
            "return handoff, confirmation display, blocked-item export, "
            "and only mark accepted items complete.",
        ),
    },
    "dev-workspace-02-021": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "When should Northstar Forms block final submission for "
            "missing required answers?",
            "A draft with blank mandatory fields is submitted because "
            "saving and approval were treated the same; what review "
            "banner rule applies?",
            "Incomplete drafts may be saved, but final submission must "
            "stop until missing required fields are marked and "
            "resolved.",
        ),
    },
    "dev-workspace-02-022": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What should the Northstar Forms completion error summary separate?",
            "The final screen mixes blank required answers with invalid "
            "formats in one message; which summary behavior is needed?",
            "Completion errors should distinguish missing mandatory "
            "responses from formatting problems.",
        ),
    },
    "dev-workspace-02-023": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What do supervisors require before marking a Northstar "
            "Forms submission complete?",
            "A form is completed even though a mandatory response is "
            "invalid and has no waiver note; which supervisor check "
            "applies?",
            "Every required answer must be valid, or have an approved "
            "waiver, before completion is allowed.",
        ),
    },
    "dev-workspace-02-024": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "How should Northstar Forms word validation messages for "
            "required responses?",
            "A required-field error says only a generic system code; "
            "which plain-language guidance should replace it?",
            "Use human wording that says the response is needed before "
            "signoff, not vague technical error text.",
        ),
    },
    "dev-workspace-02-025": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What offline draft bug affected required radio questions in "
            "Northstar Forms?",
            "After reopening a saved draft, a required choice appears "
            "selected even though the stored value is empty; which bug "
            "note covers it?",
            "Required radio prompts could look answered after reopen "
            "while actually blank, and review failed to catch the "
            "missing value.",
        ),
    },
    "dev-workspace-02-026": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What focus behavior is required after a failed Northstar "
            "Forms completion attempt?",
            "Keyboard users submit with blank fields and focus stays "
            "away from the problem summary; which accessibility note "
            "applies?",
            "Move keyboard focus to the error summary after failed "
            "completion, with links back to each blank question.",
        ),
    },
    "dev-workspace-02-027": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What separate counts should the Northstar Forms completion "
            "indicator show?",
            "A single incomplete badge hides whether problems are "
            "missing answers, rule failures, or supervisor blockers; "
            "what indicator detail is needed?",
            "Show distinct totals for missing mandatory items, failed "
            "checks, and signoff blockers instead of one broad "
            "incomplete status.",
        ),
    },
    "dev-workspace-02-028": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "When should conditional required questions appear in the "
            "final Northstar Forms checklist?",
            "A hidden required child question blocks signoff even though "
            "its parent condition is false; which checklist rule "
            "applies?",
            "Only active conditional must-fill prompts should block "
            "signoff, and skipped hidden questions need an "
            "explanation.",
        ),
    },
    "dev-workspace-02-029": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What screen reader issue was found on the Northstar Forms "
            "final check page?",
            "Inline validation text is announced twice after completion "
            "fails; what accessibility adjustment did the team plan?",
            "Keep the summary announcement but reduce repeated inline "
            "problem messages so assistive tech does not read them "
            "twice.",
        ),
    },
    "dev-workspace-02-030": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Why does Northstar Forms need a server-side final signoff guard?",
            "A crew collected responses offline, rules changed before "
            "upload, and the app accepted the form without rechecking; "
            "what guard is required?",
            "After field data reaches the server, rerun "
            "required-response checks and explain any changed rules that "
            "need another review.",
        ),
    },
    "dev-workspace-03-001": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "How should HarborPilot help dispatchers notice when crane, "
            "welding, and survey jobs collide at one pier?",
            "During schedule review, a dispatcher wants conflicts "
            "visible from the board without drilling into every repair "
            "card.",
            "Remember that repair work should appear in clear time "
            "blocks so same-pier overlaps stand out immediately.",
        ),
    },
    "dev-workspace-03-002": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Why does the crew coordination screen show arrival periods "
            "instead of precise appointment times?",
            "When tides or setup delays shift the day, dispatchers still "
            "need the planned sequence without rigid clocks.",
            "Keep in mind that arrival estimates are flexible ranges "
            "while the order of jobs remains meaningful.",
        ),
    },
    "dev-workspace-03-003": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What priority order should the dispatch board use for hull "
            "repairs, maintenance, and dock hardware?",
            "After cards reload, urgent patching must still appear ahead "
            "of routine service and minor dock fixes.",
            "The team should remember the stable sorting rule that keeps "
            "high-impact repairs above lower-priority work.",
        ),
    },
    "dev-workspace-03-004": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Which quick time filters should dispatchers have for "
            "upcoming HarborPilot work?",
            "A supervisor wants to narrow the board to jobs starting "
            "soon, the next morning, or the current shift block.",
            "Remember to support filtering by two-hour starts, tomorrow "
            "morning work, and the active crew period.",
        ),
    },
    "dev-workspace-03-005": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Why does HarborPilot need a separate lane for night-shift repair work?",
            "At morning handoff, supervisors must distinguish repairs "
            "carried over overnight from fresh assignments.",
            "The board should keep overnight crew items in their own "
            "swimlane for clearer turnover decisions.",
        ),
    },
    "dev-workspace-03-006": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What bug affected repair cards when dispatchers moved them "
            "between columns?",
            "If a card is dragged to another status, its crew should "
            "remain and its planned kickoff should not revert to dawn.",
            "Remember that column moves must preserve the expected start "
            "window unless someone intentionally changes it.",
        ),
    },
    "dev-workspace-03-007": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "How should HarborPilot configure normal crew periods for "
            "different harbor areas?",
            "Dry dock and pier repair schedules follow different "
            "rhythms, so each zone needs its own default work blocks.",
            "The configuration should let harbor zones define standard "
            "crew timing instead of sharing one global pattern.",
        ),
    },
    "dev-workspace-03-008": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "How should idle spaces on the repair timeline be shown to dispatchers?",
            "When there is a short opening between larger jobs, the "
            "board can suggest quick surveys or parts swaps without "
            "bumping bigger orders.",
            "Remember to mark gaps with their usable duration while "
            "preventing tiny filler work from taking priority over major "
            "jobs.",
        ),
    },
    "dev-workspace-03-009": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Where should warnings appear when back-to-back repairs in "
            "different zones require extra travel or staging?",
            "A supervisor reviewing consecutive work orders needs to "
            "know whether the second job is at risk because of movement "
            "time, setup, or both.",
            "Keep the crew assignment warning beside the later job and "
            "explain the exact cause of the scheduling issue.",
        ),
    },
    "dev-workspace-03-010": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What fields belong in HarborPilot dispatch exports, and "
            "what private details must be excluded?",
            "For demo screenshots, the export should be useful with job "
            "and gear context but leave out customer contact "
            "information.",
            "Remember that exported dispatch data includes operational "
            "columns and arrival ranges, not names, addresses, or phone "
            "numbers.",
        ),
    },
    "dev-workspace-03-011": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "How should HarborPilot handle the west yard hoist after "
            "overlapping haul-out attempts?",
            "If two pier crews try to schedule that shared lift for the "
            "same morning, the system should treat it as unavailable to "
            "one of them.",
            "Remember that the west yard hoist can serve only one booking at a time.",
        ),
    },
    "dev-workspace-03-012": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "When should HarborPilot avoid recommending air-tool work "
            "because the pneumatic trailer is unavailable?",
            "On Friday afternoons, filter service takes the air trailer "
            "out of circulation, so suggested jobs should not depend on "
            "it.",
            "The team should remember the weekly maintenance window for "
            "the pneumatic trailer when generating work suggestions.",
        ),
    },
    "dev-workspace-03-013": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What problem occurs when diagnostic handhelds stay checked "
            "out after vessel surveys?",
            "Before closing related notes, HarborPilot should ask for "
            "device return confirmation and identify the previous job "
            "using it.",
            "Remember to prevent stale handheld availability by warning "
            "about unreturned survey devices.",
        ),
    },
    "dev-workspace-03-014": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Should HarborPilot warn about unavailable tools before or "
            "after crew scheduling conflicts?",
            "When heavy gear or a diagnostic device is required, the "
            "board must explain that the job cannot start until the item "
            "is secured.",
            "Keep gear conflicts ahead of staffing issues because "
            "available crews do not matter when required equipment is "
            "missing.",
        ),
    },
    "dev-workspace-03-015": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "How should bookings for the north basin hoist account for "
            "setup and teardown time?",
            "A dispatcher should not be able to plan consecutive repair "
            "bay moves as though the hoist relocates instantly.",
            "Remember to show preparation and wrap-up buffers as "
            "occupied periods on the hoist calendar.",
        ),
    },
    "dev-workspace-03-016": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What calendar bug involved shortening an air trailer "
            "reservation that another crew still needed?",
            "If a crew reduces a pneumatic trailer booking, HarborPilot "
            "must protect dependent work that relies on the original "
            "slot.",
            "Remember the issue where one team's edit could undermine "
            "another team's air trailer schedule.",
        ),
    },
    "dev-workspace-03-017": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What reasons should dispatchers be able to choose when "
            "equipment cannot be assigned?",
            "In suggestions, a tool should explain whether it is down "
            "for service, being moved, under a safety hold, or charging.",
            "Remember that unavailable-item reasons need to be visible "
            "before the detail page, not hidden after selection.",
        ),
    },
    "dev-workspace-03-018": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "When should HarborPilot remind supervisors about diagnostic "
            "handheld field notes?",
            "Before a handheld returns to the shared pool, the "
            "supervisor must verify that its survey notes have "
            "transmitted.",
            "Remember that devices with unfinished record transfers "
            "should not be picked up by another crew without "
            "confirmation.",
        ),
    },
    "dev-workspace-03-019": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "How should portable air units be organized so crews can "
            "find compatible substitutes?",
            "For hull repair tasks, the picker should show any air unit "
            "that meets the output requirement rather than relying only "
            "on labels.",
            "Remember to group air equipment by pressure capacity "
            "because names can hide valid alternatives.",
        ),
    },
    "dev-workspace-03-020": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "How should HarborPilot reserve time when a hoist travels "
            "between the dry dock apron and inner harbor corridor?",
            "Dispatchers need the shared gear calendar to show "
            "relocation time as unavailable while heavy equipment is in "
            "transit.",
            "Remember that moving heavy gear consumes schedulable time, "
            "not just the repair tasks themselves.",
        ),
    },
    "dev-workspace-03-021": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What should the relief crew verify before assigning divers "
            "to the Pier 4 fender job?",
            "The evening note says that fender repair is blocked by a "
            "safety release, so the next crew must confirm the hold is "
            "gone.",
            "Remember that Pier 4 diver assignment waits until the "
            "safety hold has been lifted.",
        ),
    },
    "dev-workspace-03-022": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What statuses should handoff notes show so incoming "
            "coordinators avoid calling crews too early?",
            "At shift change, the coordinator needs to see whether each "
            "job is ready, blocked, or pending inspection before "
            "contacting workers.",
            "Remember that HarborPilot handoffs must make not-startable "
            "work obvious to the next coordinator.",
        ),
    },
    "dev-workspace-03-023": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What must be checked before dispatching the north basin "
            "bollard replacement?",
            "Coordinators should not clear that bollard job until the "
            "crane, tide status, and safety barriers are all confirmed.",
            "Remember the north basin checklist items required before "
            "the replacement can be released to crews.",
        ),
    },
    "dev-workspace-03-024": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "When do blocked jobs remain pinned above other handoff items?",
            "A work order with an unresolved blocker should stay "
            "prominent until someone records both the blocker type and "
            "accountable role.",
            "Remember that the handoff board keeps blocked work at the "
            "top until ownership and category are captured.",
        ),
    },
    "dev-workspace-03-025": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What three pending repair states did the outgoing lead "
            "report at crew turnover?",
            "During shift change, the summary should distinguish one "
            "dispatch-ready job, one materials delay, and one waiting "
            "for approval.",
            "Remember the turnover example with three repairs in "
            "different readiness conditions.",
        ),
    },
    "dev-workspace-03-026": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What turnover summary bug caused incoming coordinators to repeat checks?",
            "If completed checklist entries disappear from the handoff "
            "summary, the next coordinator may unnecessarily ask crews "
            "again.",
            "Remember to include finished checklist items reliably so "
            "shift handoff does not duplicate crew verification.",
        ),
    },
    "dev-workspace-03-027": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What is the status of the fuel dock ladder repair noted by "
            "the night crew?",
            "The ladder job may be prepared at the site, but work should "
            "not begin because the last safety hold remains active.",
            "Remember that staging is allowed for the fuel dock ladder, "
            "while starting the repair is still unsafe.",
        ),
    },
    "dev-workspace-03-028": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What information should coordinator summaries emphasize, "
            "and what should they hide by default?",
            "At handoff, coordinators need recent crew contact and open "
            "access problems without clutter from ordinary completed "
            "updates.",
            "Remember to surface latest contact times and unresolved "
            "access issues while collapsing routine done items.",
        ),
    },
    "dev-workspace-03-029": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "How should HarborPilot distinguish different reasons a job "
            "is not ready during handoff?",
            "Instead of a vague blocked state, the workflow should "
            "separate permit gaps, unfinished checklists, and inspection "
            "holds with ownership and next steps.",
            "Remember that every handoff blocker needs a specific "
            "category, an accountable owner, and a follow-up action.",
        ),
    },
    "dev-workspace-03-030": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What assignment problem happened to jobs cleared before the shift change?",
            "When work is approved before turnover, the morning view "
            "should keep the assigned crew instead of dropping it.",
            "Remember to preserve team assignments across crew change "
            "for jobs that were already cleared.",
        ),
    },
}
