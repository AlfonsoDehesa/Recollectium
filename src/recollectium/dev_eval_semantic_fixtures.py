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
            "What travel preference says they like unscheduled time for exploring neighborhoods?",
            "Ask for the user's tendency to avoid overbooking vacations with reservations.",
            "Ask about their preference for city trip days with room to wander locally.",
        ),
    },
    "dev-user-002": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of lodging location does the user look for when traveling?",
            "Find their preference for staying near transit, casual food, and basic groceries.",
            "How does the user choose hotels or rentals based on nearby everyday conveniences?",
        ),
    },
    "dev-user-003": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the user compare before picking a place to stay on a trip?",
            "Retrieve the travel planning habit about trains, airport access, and walkability.",
            "Show their habit of evaluating transport links and walkability before booking lodging.",
        ),
    },
    "dev-user-004": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How does the user prefer travel days to be paced around departures?",
            "Find the preference for having time to buy coffee and locate the right platform.",
            "What memory says rushed connections make travel days less enjoyable for them?",
        ),
    },
    "dev-user-005": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the user like doing at local markets near the start of a trip?",
            "Look up their habit of using markets to understand a neighborhood and stock snacks.",
            "Show their interest in early market stops for local atmosphere and snacks.",
        ),
    },
    "dev-user-006": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What packing style does the user prefer for urban vacations?",
            "Ask how they pack lightly for city travel while relying on quick laundry.",
            "How does the user balance packing light with washing clothes during city travel?",
        ),
    },
    "dev-user-007": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What destination advice helps the user handle ticketed attractions and bad weather?",
            "Retrieve their preference for knowing which sights require booking ahead.",
            "Show the travel advice they value about rainy-day options and tickets to reserve ahead.",
        ),
    },
    "dev-user-008": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How much structure does the user like for each vacation day?",
            "Find their preference for one main museum, hike, or food activity with flexible time around it.",
            "What travel memory says detailed minute-by-minute schedules feel too restrictive?",
        ),
    },
    "dev-user-009": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What dining rhythm does the user enjoy when traveling?",
            "Look up their preference for regional morning meals, casual cafes, and calmer evenings.",
            "Show their habit of choosing the nicer meal at lunch so travel evenings stay easy.",
        ),
    },
    "dev-user-010": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of backup options does the user save before a trip?",
            "Ask how they prepare flexible fallback plans with indoor stops, quiet parks, and casual food.",
            "How do transit time, price, and reservation notes make travel recommendations more useful to them?",
        ),
    },
    "dev-user-011": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When does the user prefer trains instead of flying?",
            "Retrieve the transportation preference for rail when door-to-door time is similar to an air trip.",
            "Show their rail preference when flying would not save much total time.",
        ),
    },
    "dev-user-012": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How does the user feel about transfers when choosing a route?",
            "Find the preference for a more direct trip even if it is slightly slower.",
            "What transportation memory says fewer connections can matter more than saving a few minutes?",
        ),
    },
    "dev-user-013": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the user check before leaving for time-sensitive travel or appointments?",
            "Look up the habit of reviewing traffic ahead of airport runs and station pickups.",
            "Show their routine of checking traffic before leaving for scheduled travel.",
        ),
    },
    "dev-user-014": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When is the user open to bike-share or scooters for short trips?",
            "Ask when scooters or shared bikes feel acceptable for short city transportation.",
            "What transportation preference mentions bikes or scooters for brief city errands when infrastructure feels safe?",
        ),
    },
    "dev-user-015": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What route information does the user appreciate when multiple transportation modes are realistic?",
            "Retrieve the preference for comparing car, transit, and walking by time, cost, and inconvenience.",
            "Show their interest in route advice that weighs practical tradeoffs among travel modes.",
        ),
    },
    "dev-user-016": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What parking details does the user want before driving to a busy area?",
            "Find their habit of checking garages, meters, permit zones, and likely prices in advance.",
            "Show their preference for knowing parking options before driving somewhere busy.",
        ),
    },
    "dev-user-017": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How does the user weigh reliability against the lowest transportation cost?",
            "Look up their willingness to spend a bit more to avoid stressful connections.",
            "What memory says dependable travel plans matter more than the cheapest option?",
        ),
    },
    "dev-user-018": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How does the user use rideshare in their transportation planning?",
            "Find the preference for treating ride-hailing as a backup at night or in bad weather rather than the default.",
            "Show their view that ride-hailing is a fallback while dependable public transit is preferred.",
        ),
    },
    "dev-user-019": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When does the user like walking for short urban trips?",
            "Retrieve their walking preference for safe sidewalks, decent weather, and pleasant street scenery.",
            "What preference warns against walking plans through confusing highways or dark areas?",
        ),
    },
    "dev-user-020": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How early does the user like to arrive for buses, trains, or flights?",
            "Ask how much extra time they want before departures for tickets, gates, or screening.",
            "What preference says waiting calmly is better than cutting an important trip close?",
        ),
    },
    "dev-user-021": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of games does the user enjoy for narrative and mood?",
            "Retrieve the gaming preference for atmospheric stories and characters that stick with them.",
            "Show their interest in narrative games with atmosphere and characters they remember.",
        ),
    },
    "dev-user-022": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Why does the user value adjustable difficulty in games?",
            "Find the preference for changing challenge level depending on how they feel.",
            "What gaming memory says flexible settings help match the user's mood?",
        ),
    },
    "dev-user-023": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What makes puzzle mechanics appealing to the user in games?",
            "Look up their preference for puzzles that feel like part of the world rather than detached obstacles.",
            "Show their preference for puzzle design that feels embedded in the game world.",
        ),
    },
    "dev-user-024": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What practical details does the user want in game recommendations?",
            "Ask what session-length information makes game suggestions more useful to them.",
            "Show the gaming recommendation detail about playtime and session length.",
        ),
    },
    "dev-user-025": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When does the user enjoy open-world games?",
            "Retrieve the preference for exploration that rewards curiosity instead of feeling like errands on a list.",
            "What memory says maps should invite discovery rather than just completion chores?",
        ),
    },
    "dev-user-026": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What multiplayer setup does the user tend to avoid?",
            "Ask why online games with constant stranger voice chat are not a good fit for them.",
            "Show their comfort with cooperative play that can stay quiet or use basic pings.",
        ),
    },
    "dev-user-027": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kinds of games help the user relax after work?",
            "Look up their preference for cozy games with gentle objectives, pleasant soundtracks, and forgiving systems.",
            "Show their preference for low-stress games that are forgiving when they pause or leave.",
        ),
    },
    "dev-user-028": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What save system qualities does the user care about in games?",
            "Ask why clear checkpoints matter before the user starts a longer game session.",
            "Show their view that autosave is useful but a manual save option is ideal.",
        ),
    },
    "dev-user-029": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What draws the user to indie games?",
            "Retrieve the preference for unusual mechanics or distinctive visuals despite minor rough edges.",
            "Show their openness to rough indie games when the central concept feels original.",
        ),
    },
    "dev-user-030": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What makes a game suitable for the user's couch or TV setup?",
            "Find the preference for controller support, readable interface text, adjustable captions, and mouse-free menus.",
            "Show their tendency to reserve controller-awkward games for a desk setup.",
        ),
    },
    "dev-user-031": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What qualities does the user enjoy in novels?",
            "Retrieve the reading preference for nuanced character arcs and a vivid setting.",
            "Show their taste for fiction where characters deepen and the setting feels vivid.",
        ),
    },
    "dev-user-032": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How should book recommendations explain why a title fits the user?",
            "Find the preference for brief reasons without revealing plot spoilers.",
            "What reading memory says suggested books should include a short spoiler-safe fit explanation?",
        ),
    },
    "dev-user-033": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What nonfiction style does the user prefer?",
            "Look up their interest in clear nonfiction that avoids a textbook tone.",
            "Show their nonfiction preference for clarity without a dry classroom feel.",
        ),
    },
    "dev-user-034": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Why does the user appreciate shorter chapters?",
            "Ask why concise book sections are helpful for their reading routine.",
            "Show why short chapters help them read during small pockets of time.",
        ),
    },
    "dev-user-035": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How does the user avoid reading burnout?",
            "Retrieve the habit of alternating demanding books with easier, comforting reads.",
            "What memory says they like a lighter option ready after finishing something dense?",
        ),
    },
    "dev-user-036": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of science fiction appeals to the user?",
            "Find the preference for speculative stories centered on human effects and believable relationships.",
            "Show their sci-fi taste for emotional consequences rather than technology alone.",
        ),
    },
    "dev-user-037": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the user like in mystery novels?",
            "Look up the preference for fair clues and twists that do not feel overly convenient.",
            "Show their mystery preference for clues that feel fair once the solution is known.",
        ),
    },
    "dev-user-038": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How many book suggestions does the user prefer at once?",
            "Ask how they prefer a concise to-read list to describe tone, pacing, length, and series commitment.",
            "What reading preference says three to five strong options beat a huge catalog?",
        ),
    },
    "dev-user-039": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of memoirs interest the user?",
            "Retrieve the preference for personal narratives connected to cultural or historical context.",
            "Show their preference for grounded reflective memoirs over gossip or sensationalism.",
        ),
    },
    "dev-user-040": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the user avoid reading late at night?",
            "Ask what kinds of intense books they avoid close to bedtime.",
            "Show the calmer genres they prefer for bedtime reading.",
        ),
    },
    "dev-user-041": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the user want from weeknight dinner recipes?",
            "Retrieve the cooking preference for meals around half an hour with little cleanup.",
            "Show their preference for fast dinners with minimal cleanup on work nights.",
        ),
    },
    "dev-user-042": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What style of meals does the user enjoy with vegetables, grains, and olive oil?",
            "Ask about their taste for Mediterranean-leaning meals built around simple proteins.",
            "Show their interest in Mediterranean-style grain and vegetable meals.",
        ),
    },
    "dev-user-043": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What pantry staples does the user tend to keep available?",
            "Look up their habit of stocking pasta, rice, beans, canned tomatoes, and everyday spices.",
            "Show the pantry basics they usually keep ready for cooking.",
        ),
    },
    "dev-user-044": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What breakfast flavor profile does the user prefer when cooking?",
            "Ask whether they lean savory or sweet for breakfast when they can cook.",
            "Show their preference for savory breakfasts when they have time to cook.",
        ),
    },
    "dev-user-045": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What recipe format does the user appreciate for home cooking?",
            "Retrieve the preference for clear instructions and substitutions for ingredients they may already have.",
            "Show their interest in recipes with clear steps and practical ingredient swaps.",
        ),
    },
    "dev-user-046": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kinds of make-ahead lunches does the user like preparing?",
            "Ask what batch-cooked meals they like for easy lunches during the week.",
            "Show their reliance on reheatable batch-cooked meals for weekday lunches.",
        ),
    },
    "dev-user-047": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When is the user more willing to try complicated recipe projects?",
            "Look up the preference for new recipes without difficult techniques on busy days.",
            "Show their tendency to save more ambitious recipe projects for calm weekends.",
        ),
    },
    "dev-user-048": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What cooking skill does the user want to improve?",
            "Ask what practical knife-prep guidance would help them cook faster and more safely.",
            "Show their interest in brief practical knife-skill practice rather than formal lessons.",
        ),
    },
    "dev-user-049": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What balance does the user want in dinner recipes?",
            "Retrieve their preference for protein, vegetables, and satisfying carbs without heavy sauces or too many ingredients.",
            "Show how a simple salad or roasted vegetable fits their idea of a balanced dinner.",
        ),
    },
    "dev-user-050": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "How does the user use refrigerator leftovers when planning meals?",
            "Ask how they prefer to turn extra herbs, partial vegetables, or cooked grains into planned meals.",
            "Show their desire to use leftovers creatively without making dinner feel second-rate.",
        ),
    },
    "dev-user-051": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Help me design exercise habits that fit around regular office hours.",
            "I need a workout schedule that feels realistic during a busy week.",
            "Look up my preference for fitness routines that are easy to maintain with work.",
        ),
    },
    "dev-user-052": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Show me strength workouts that say what each lift is meant to accomplish.",
            "I want resistance training advice with the reasoning behind the movements.",
            "Find my preference for weight training plans that explain why exercises are included.",
        ),
    },
    "dev-user-053": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Remind me how walking fits into my approach to staying active.",
            "What low-key activity do I use for both movement and mental reset?",
            "Pull up my note about using strolls to decompress while keeping fit.",
        ),
    },
    "dev-user-054": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "I need habit tracking that rewards showing up, not flawless performance.",
            "Find my fitness tracking preference about steady consistency over perfect streaks.",
            "What kind of progress log keeps me motivated without all-or-nothing pressure?",
        ),
    },
    "dev-user-055": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Show me workouts that ease in with a manageable warmup at the beginning.",
            "I am more likely to exercise if the opening minutes do not feel intimidating.",
            "Find my preference for plans that include simple warmup instructions.",
        ),
    },
    "dev-user-056": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "I want exercise options using bands, dumbbells, or just my own body.",
            "Find routines that do not require fighting for equipment at a busy fitness center.",
            "What is my preference about simple gear for workouts at home or anywhere?",
        ),
    },
    "dev-user-057": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Show me quick mobility work for my hips, shoulders, and back.",
            "I need short stretching-style routines I can actually keep doing.",
            "Find my note about joint comfort exercises being easier when they are brief.",
        ),
    },
    "dev-user-058": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "I need fitness guidance that treats recovery as part of the plan.",
            "Find my preference for sustainable exercise without guilt after skipping a day.",
            "What workout advice helps me avoid turning missed sessions into failure?",
        ),
    },
    "dev-user-059": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Give me cardio ideas I can scale based on how energetic I feel.",
            "Find my preference for walks, biking, or intervals with clear effort levels.",
            "What aerobic options let me choose an easier or harder version for the day?",
        ),
    },
    "dev-user-060": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "I want strength plans focused on gradual gains and solid technique.",
            "Find my preference for getting stronger without chasing extreme outcomes.",
            "What fitness approach feels trustworthy because it includes realistic recovery?",
        ),
    },
    "dev-user-061": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Remind me how I organize playlists for different parts of my day.",
            "I want music separated for concentration, chores, exercise, and unwinding.",
            "Find my note about keeping distinct mixes for work focus and home relaxation.",
        ),
    },
    "dev-user-062": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Suggest new musicians by starting from tracks I already enjoy.",
            "Find my preference for discovering artists through similar song recommendations.",
            "How do I like to branch out musically from favorites I know?",
        ),
    },
    "dev-user-063": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What kind of music do I put on when I need to concentrate?",
            "Find my preference for mostly non-lyrical background audio during deep work.",
            "I need focus music with few vocals or an instrumental feel.",
        ),
    },
    "dev-user-064": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Give me energetic songs for tidying up or making dinner.",
            "Find my preference for lively music during cooking and chores.",
            "What soundtrack do I like for household tasks that need momentum?",
        ),
    },
    "dev-user-065": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Recommend music with a quick note about pace, singing, and energy.",
            "Find my preference for song suggestions that explain why they match the mood.",
            "I am more likely to try a track if the recommendation describes its feel.",
        ),
    },
    "dev-user-066": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When exploring a style, I like both classics and current songs.",
            "Find my music preference about connecting newer releases to older influences.",
            "I want genre recommendations with history lightly explained, not a lecture.",
        ),
    },
    "dev-user-067": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Build me a playlist that keeps the vibe steady from song to song.",
            "Find my preference for smooth mood transitions over strict genre boundaries.",
            "What playlist style do I dislike when it jumps abruptly between sounds?",
        ),
    },
    "dev-user-068": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What music suits me at night when I want something gentle?",
            "Find my preference for soft evening songs with mellow vocals or quiet instruments.",
            "I want calm late-day music and usually avoid harsh percussion then.",
        ),
    },
    "dev-user-069": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Recommend international songs where the overall feel matters more than lyrics.",
            "Find my openness to music in other languages when the mood fits.",
            "I like a brief style or region note before trying global music.",
        ),
    },
    "dev-user-070": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Tell me a few memorable facts about an artist or record before I listen.",
            "Find my preference for concise music context instead of a long history lesson.",
            "I like album notes that mention era, instruments, and the best listening mood.",
        ),
    },
    "dev-user-071": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "I need pet routines that feel peaceful, regular, and not hard to sustain.",
            "Find my preference for animal care habits that are predictable and calm.",
            "What kind of daily pet schedule is easiest for me to maintain?",
        ),
    },
    "dev-user-072": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When recommending pet gear, mention whether it lasts, washes easily, and is quiet.",
            "Find my criteria for choosing animal products based on sturdiness and noise.",
            "I want pet item suggestions that cover cleaning ease and durability.",
        ),
    },
    "dev-user-073": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Help me set up a home drop zone for pet supplies and cleanup items.",
            "Find my preference for practical places to store leashes, treats, and brushes.",
            "I like houses organized so animal-care gear has an obvious spot.",
        ),
    },
    "dev-user-074": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Give me pet advice that is safe and enriching without being precious.",
            "Find my preference for animal guidance that balances wellbeing with practicality.",
            "I want comfort and safety for pets, but not fussy overcomplication.",
        ),
    },
    "dev-user-075": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Set up straightforward pet feeding prompts for morning and night.",
            "Find my preference for consistent mealtime reminders for an animal.",
            "I follow pet feeding routines best when the checkpoints are simple.",
        ),
    },
    "dev-user-076": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Give me easy enrichment ideas like toy rotation and quick training games.",
            "Find my pet preference for puzzle feeders and activities that fit a normal day.",
            "I want animal stimulation options that do not require a big production.",
        ),
    },
    "dev-user-077": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When traveling with a pet, I need lodging rules and calm walking options.",
            "Find my preference for animal-friendly trip advice that considers green space and crowds.",
            "I dislike pet travel tips that assume every animal enjoys busy places.",
        ),
    },
    "dev-user-078": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Help me make a pet corner tidy, washable, and welcoming to guests.",
            "Find my preference for animal areas with water access, toy storage, and a blanket.",
            "I want pet spaces that feel intentional without looking overly sterile.",
        ),
    },
    "dev-user-079": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Before bringing things home, remind me to check if they are safe for pets.",
            "Find my caution about plants, cleaners, and little objects around animals.",
            "I care more about pet safety than perfect room styling when placing new items.",
        ),
    },
    "dev-user-080": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "I prefer pet training with brief practices, rewards, and patient cues.",
            "Find my approach to animal training that avoids fear or confusion.",
            "What training style keeps pets positive with breaks and small incentives?",
        ),
    },
    "dev-user-081": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Break a new skill into tiny actionable steps for me.",
            "Find my preference for learning plans made from concrete bite-size tasks.",
            "I learn better when a skill is divided into manageable pieces.",
        ),
    },
    "dev-user-082": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Give me a lesson format with a hands-on task after each idea.",
            "Find my preference for tutorials that pair concepts with immediate practice.",
            "I want every new learning point followed by one practical exercise.",
        ),
    },
    "dev-user-083": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "I stay motivated when lessons show milestones and clear progress markers.",
            "Find my learning preference for checkpoints that make advancement visible.",
            "What course structure helps me keep momentum through obvious next goals?",
        ),
    },
    "dev-user-084": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Explain new material with an example first, then give me the terminology.",
            "Find my preference for learning that begins concretely before naming concepts.",
            "I understand formal terms better after seeing them used in a sample.",
        ),
    },
    "dev-user-085": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "After a lesson, I like summarizing the idea in my own phrasing.",
            "Find my note-taking habit that helps reveal what I actually understood.",
            "What learning practice do I use after finishing a lesson to check comprehension?",
        ),
    },
    "dev-user-086": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "I learn well through small projects that make something useful.",
            "Find my preference for visible outcomes instead of only abstract drills.",
            "Give me practice tasks with a practical product at the end.",
        ),
    },
    "dev-user-087": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "I need review sessions that revisit old material without feeling like punishment.",
            "Find my preference for gentle repetition to help information stick.",
            "What study approach helps me retain details by calmly returning to earlier topics?",
        ),
    },
    "dev-user-088": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "I get frustrated when courses gloss over installation or setup steps.",
            "Find my preference for instructions that include prerequisites, mistakes, and verification.",
            "A learning guide should help me confirm the first result before moving on.",
        ),
    },
    "dev-user-089": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Show me two or three examples so I can learn a new pattern.",
            "Find my preference for comparing the same idea across different situations.",
            "I prefer concise explanations over heavy theory when generalizing a concept.",
        ),
    },
    "dev-user-090": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Make my learning plan realistic with short sessions and spaced practice.",
            "Find my preference for small milestones instead of marathon weekend studying.",
            "I finish courses more often when the workload has structure but is not rigid.",
        ),
    },
    "dev-user-091": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Describe my decorating taste for cozy rooms with warm light and natural materials.",
            "Find my home style preference for lived-in spaces rather than showroom staging.",
            "I like interiors that feel comfortable, textured, and not overly polished.",
        ),
    },
    "dev-user-092": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Help me organize an entryway so keys, bags, footwear, and mail stay contained.",
            "Find my preference for mudroom-style storage near the door.",
            "I want a landing area that stops everyday items from drifting through the house.",
        ),
    },
    "dev-user-093": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What curtains, rugs, and color palette match my home taste?",
            "Find my preference for muted interiors with linen, simple floor coverings, and warm accents.",
            "I like soft colors and uncomplicated textiles with a little warmth added.",
        ),
    },
    "dev-user-094": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Arrange my houseplants in little window groups that are easy to water.",
            "Find my preference for clustering plants near natural light.",
            "I like plant displays that look nice but still make watering convenient.",
        ),
    },
    "dev-user-095": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Set up one inviting reading nook with a lamp, table, and blanket.",
            "Find my preference for a comfortable reading spot over extra decor.",
            "What elements matter most to me for a cozy place to read?",
        ),
    },
    "dev-user-096": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Design a home office with an uncluttered desk and a place to collect notes.",
            "Find my preference for workspaces where papers have a tray or visible board.",
            "I feel less stressed by office clutter when there is a designated spot for it.",
        ),
    },
    "dev-user-097": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "I want my kitchen counters mostly open with useful storage nearby.",
            "Find my preference for practical kitchens without crowded displays.",
            "A few everyday objects can stay out, but too many items on counters annoy me.",
        ),
    },
    "dev-user-098": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Make a guest room calm, useful, and easy to reset after visitors.",
            "Find my preference for spare rooms with a lamp, surface, blanket, and suitcase space.",
            "I do not need a formal guest bedroom, just a simple comfortable setup.",
        ),
    },
    "dev-user-099": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Describe my cozy palette with pale wood, brass, greens, and clay tones.",
            "Find my home style preference for subtle handmade touches and personal warmth.",
            "I like rooms that are tidy and comfortable with soft green and earthy accents.",
        ),
    },
    "dev-user-100": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "I prefer seasonal decorating with just a wreath, candle, or fruit bowl.",
            "Find my preference for holiday touches that are easy to store and reuse.",
            "I like small seasonal accents better than redecorating an entire room.",
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
