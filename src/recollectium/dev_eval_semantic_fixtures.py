"""Deterministic semantic paraphrase fixtures for seeded dev eval."""

from __future__ import annotations

# This file is generated from the checked-in seeded development fixture and
# intentionally stores explicit paraphrase data. Runtime semantic MRR eval
# imports these strings; it does not synthesize queries dynamically.

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
            "Which travel preference says they prefer trips that leave room for wandering through neighborhoods instead of filling every day with reservations?",
            "Find the user memory about trips that leave room for wandering through neighborhoods instead of filling every day with reservations.",
            "What should recommendations remember about trips that leave room for wandering through neighborhoods instead of filling every day with reservations for this person's travel choices?",
        ),
    },
    "dev-user-002": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which travel preference says they like choosing hotels or rentals near reliable transit, casual restaurants, and a grocery stop for simple supplies?",
            "Find the user memory about choosing hotels or rentals near reliable transit, casual restaurants, and a grocery stop for simple supplies.",
            "What should recommendations remember about choosing hotels or rentals near reliable transit, casual restaurants, and a grocery stop for simple supplies for this person's travel choices?",
        ),
    },
    "dev-user-003": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which travel preference says they usually compare train routes, airport transfers, and walking distances before deciding where to stay?",
            "Find the user memory about train routes, airport transfers, and walking distances before deciding where to stay.",
            "What should recommendations remember about train routes, airport transfers, and walking distances before deciding where to stay for this person's travel choices?",
        ),
    },
    "dev-user-004": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which travel preference says they enjoy travel days more when there is enough buffer time to get coffee, find the platform, and avoid rushing?",
            "Find the user memory about travel days more when there is enough buffer time to get coffee, find the platform, and avoid rushing.",
            "What should recommendations remember about travel days more when there is enough buffer time to get coffee, find the platform, and avoid rushing for this person's travel choices?",
        ),
    },
    "dev-user-005": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which travel preference says they like visiting local markets early in a trip; they use them to get a feel for the neighborhood and pick up snacks for later?",
            "Find the user memory about visiting local markets early in a trip; they use them to get a feel for the neighborhood and pick up snacks for later.",
            "What should recommendations remember about visiting local markets early in a trip for this person's travel choices?",
        ),
    },
    "dev-user-006": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which travel preference says they prefer packing a small capsule wardrobe for city trips; they would rather do a quick laundry load than check a large bag?",
            "Find the user memory about packing a small capsule wardrobe for city trips; they would rather do a quick laundry load than check a large bag.",
            "What should recommendations remember about packing a small capsule wardrobe for city trips for this person's travel choices?",
        ),
    },
    "dev-user-007": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which travel preference says they appreciate destination advice that mentions when attractions need advance tickets; they also like knowing which sights are better saved for a rainy day?",
            "Find the user memory about destination advice that mentions when attractions need advance tickets; they also like knowing which sights are better saved for a rainy day.",
            "What should recommendations remember about destination advice that mentions when attractions need advance tickets for this person's travel choices?",
        ),
    },
    "dev-user-008": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which travel preference says they tend to plan one anchor activity per travel day and keep the rest flexible; a museum, hike, or food tour is enough structure; they do not like feeling locked into a minute-by-minute itinerary?",
            "Find the user memory about plan one anchor activity per travel day and keep the rest flexible; a museum, hike, or food tour is enough structure; they do not like feeling locked into a minute-by-minute itinerary.",
            "What should recommendations remember about plan one anchor activity per travel day and keep the rest flexible for this person's travel choices?",
        ),
    },
    "dev-user-009": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which travel preference says they like trying regional breakfasts and simple neighborhood cafes while traveling; they often save fancier meals for lunch instead of dinner; this helps keep evenings relaxed after a full day out?",
            "Find the user memory about trying regional breakfasts and simple neighborhood cafes while traveling; they often save fancier meals for lunch instead of dinner; this helps keep evenings relaxed after a full day out.",
            "What should recommendations remember about trying regional breakfasts and simple neighborhood cafes while traveling for this person's travel choices?",
        ),
    },
    "dev-user-010": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which travel preference says they keep a short backup list of indoor activities, quiet parks, and casual restaurants for each trip; they find it easier to change plans when options are already saved; practical recommendations with transit time, approximate cost, and reservation details are most useful?",
            "Find the user memory about a short backup list of indoor activities, quiet parks, and casual restaurants for each trip; they find it easier to change plans when options are already saved; practical recommendations with transit time, approximate cost, and reservation details are most useful.",
            "What should recommendations remember about a short backup list of indoor activities, quiet parks, and casual restaurants for each trip for this person's travel choices?",
        ),
    },
    "dev-user-011": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which transportation preference says they prefer taking trains over short flights when the total travel time is comparable?",
            "Find the user memory about taking trains over short flights when the total travel time is comparable.",
            "What should recommendations remember about taking trains over short flights when the total travel time is comparable for this person's transportation choices?",
        ),
    },
    "dev-user-012": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which transportation preference says they generally choose routes with fewer transfers, even when a simpler route takes a few extra minutes?",
            "Find the user memory about routes with fewer transfers, even when a simpler route takes a few extra minutes.",
            "What should recommendations remember about routes with fewer transfers, even when a simpler route takes a few extra minutes for this person's transportation choices?",
        ),
    },
    "dev-user-013": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which transportation preference says they tend to check traffic before leaving for appointments, station pickups, and airport trips?",
            "Find the user memory about check traffic before leaving for appointments, station pickups, and airport trips.",
            "What should recommendations remember about check traffic before leaving for appointments, station pickups, and airport trips for this person's transportation choices?",
        ),
    },
    "dev-user-014": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which transportation preference says they like bike-share or scooter options for short city trips when protected lanes and clear parking rules are available?",
            "Find the user memory about bike-share or scooter options for short city trips when protected lanes and clear parking rules are available.",
            "What should recommendations remember about bike-share or scooter options for short city trips when protected lanes and clear parking rules are available for this person's transportation choices?",
        ),
    },
    "dev-user-015": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which transportation preference says they like route suggestions that compare driving, transit, and walking when those options are practical; they appreciate knowing the tradeoff in time, cost, and hassle?",
            "Find the user memory about route suggestions that compare driving, transit, and walking when those options are practical; they appreciate knowing the tradeoff in time, cost, and hassle.",
            "What should recommendations remember about route suggestions that compare driving, transit, and walking when those options are practical for this person's transportation choices?",
        ),
    },
    "dev-user-016": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which transportation preference says they like to check parking availability and likely cost before driving into a busy neighborhood; they would rather know about garages, meters, or permit zones ahead of time?",
            "Find the user memory about to check parking availability and likely cost before driving into a busy neighborhood; they would rather know about garages, meters, or permit zones ahead of time.",
            "What should recommendations remember about to check parking availability and likely cost before driving into a busy neighborhood for this person's transportation choices?",
        ),
    },
    "dev-user-017": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which transportation preference says they value reliable transportation plans over the absolute cheapest option; they are willing to pay a little more to avoid missed connections or stressful timing?",
            "Find the user memory about reliable transportation plans over the absolute cheapest option; they are willing to pay a little more to avoid missed connections or stressful timing.",
            "What should recommendations remember about reliable transportation plans over the absolute cheapest option for this person's transportation choices?",
        ),
    },
    "dev-user-018": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which transportation preference says they is comfortable using rideshare services as a backup plan, especially late at night or in bad weather; they still prefer not to make rideshare the default for every trip; if transit is reliable, they would rather use it?",
            "Find the user memory about they is comfortable using rideshare services as a backup plan, especially late at night or in bad weather; they still prefer not to make rideshare the default for every trip; if transit is reliable, they would rather use it.",
            "What should recommendations remember about they is comfortable using rideshare services as a backup plan, especially late at night or in bad weather for this person's transportation choices?",
        ),
    },
    "dev-user-019": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which transportation preference says they prefer walking for short city trips when sidewalks feel safe and the weather is reasonable; they enjoy routes that pass parks, cafes, or interesting storefronts; they dislike walking plans that require crossing confusing highways or poorly lit areas?",
            "Find the user memory about walking for short city trips when sidewalks feel safe and the weather is reasonable; they enjoy routes that pass parks, cafes, or interesting storefronts; they dislike walking plans that require crossing confusing highways or poorly lit areas.",
            "What should recommendations remember about walking for short city trips when sidewalks feel safe and the weather is reasonable for this person's transportation choices?",
        ),
    },
    "dev-user-020": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which transportation preference says they prefer arriving early for trains, buses, and flights so they do not feel rushed; they like having a small buffer for ticket machines, platform changes, or security lines; for important trips, they would rather wait calmly than cut it close?",
            "Find the user memory about arriving early for trains, buses, and flights so they do not feel rushed; they like having a small buffer for ticket machines, platform changes, or security lines; for important trips, they would rather wait calmly than cut it close.",
            "What should recommendations remember about arriving early for trains, buses, and flights so they do not feel rushed for this person's transportation choices?",
        ),
    },
    "dev-user-021": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which videogames preference says they enjoy story-driven games with strong atmosphere and memorable characters?",
            "Find the user memory about story-driven games with strong atmosphere and memorable characters.",
            "What should recommendations remember about story-driven games with strong atmosphere and memorable characters for this person's videogames choices?",
        ),
    },
    "dev-user-022": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which videogames preference says they prefer flexible difficulty settings because they like adjusting the challenge to fit their mood?",
            "Find the user memory about flexible difficulty settings because they like adjusting the challenge to fit their mood.",
            "What should recommendations remember about flexible difficulty settings because they like adjusting the challenge to fit their mood for this person's videogames choices?",
        ),
    },
    "dev-user-023": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which videogames preference says they enjoy puzzle mechanics when they are integrated naturally into the game world?",
            "Find the user memory about puzzle mechanics when they are integrated naturally into the game world.",
            "What should recommendations remember about puzzle mechanics when they are integrated naturally into the game world for this person's videogames choices?",
        ),
    },
    "dev-user-024": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which videogames preference says they like recommendations that mention approximate playtime and whether a game is better in short sessions or long sessions?",
            "Find the user memory about recommendations that mention approximate playtime and whether a game is better in short sessions or long sessions.",
            "What should recommendations remember about recommendations that mention approximate playtime and whether a game is better in short sessions or long sessions for this person's videogames choices?",
        ),
    },
    "dev-user-025": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which videogames preference says they like open-world games when exploration feels rewarding instead of checklist-driven; they usually appreciate maps that leave room for curiosity and discovery?",
            "Find the user memory about open-world games when exploration feels rewarding instead of checklist-driven; they usually appreciate maps that leave room for curiosity and discovery.",
            "What should recommendations remember about open-world games when exploration feels rewarding instead of checklist-driven for this person's videogames choices?",
        ),
    },
    "dev-user-026": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which videogames preference says they tend to avoid multiplayer games that require frequent voice chat with strangers; they are more comfortable with cooperative modes that can be played quietly or with simple pings?",
            "Find the user memory about avoid multiplayer games that require frequent voice chat with strangers; they are more comfortable with cooperative modes that can be played quietly or with simple pings.",
            "What should recommendations remember about avoid multiplayer games that require frequent voice chat with strangers for this person's videogames choices?",
        ),
    },
    "dev-user-027": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which videogames preference says they enjoy cozy or low-pressure games as a way to unwind after work; they prefer gentle goals, pleasant music, and systems that do not punish taking a break?",
            "Find the user memory about cozy or low-pressure games as a way to unwind after work; they prefer gentle goals, pleasant music, and systems that do not punish taking a break.",
            "What should recommendations remember about cozy or low-pressure games as a way to unwind after work for this person's videogames choices?",
        ),
    },
    "dev-user-028": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which videogames preference says they prefer games with clear save systems and dislikes losing progress because of unclear checkpoints; they often check save behavior before starting a long session; autosaves are helpful, but manual save options are still preferred when possible?",
            "Find the user memory about games with clear save systems and dislikes losing progress because of unclear checkpoints; they often check save behavior before starting a long session; autosaves are helpful, but manual save options are still preferred when possible.",
            "What should recommendations remember about games with clear save systems and dislikes losing progress because of unclear checkpoints for this person's videogames choices?",
        ),
    },
    "dev-user-029": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which videogames preference says they are interested in indie games with distinctive art direction or unusual mechanics; they are willing to try a rough edge or two if the central idea feels fresh; they especially appreciate games that do one focused thing well?",
            "Find the user memory about indie games with distinctive art direction or unusual mechanics; they are willing to try a rough edge or two if the central idea feels fresh; they especially appreciate games that do one focused thing well.",
            "What should recommendations remember about indie games with distinctive art direction or unusual mechanics for this person's videogames choices?",
        ),
    },
    "dev-user-030": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which videogames preference says they prefer controller-friendly games when playing on a couch or TV setup; they also like readable UI text, adjustable subtitles, and menus that work cleanly without a mouse; if a game is awkward on a controller, they usually save it for the desk setup?",
            "Find the user memory about controller-friendly games when playing on a couch or TV setup; they also like readable UI text, adjustable subtitles, and menus that work cleanly without a mouse; if a game is awkward on a controller, they usually save it for the desk setup.",
            "What should recommendations remember about controller-friendly games when playing on a couch or TV setup for this person's videogames choices?",
        ),
    },
    "dev-user-031": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which books preference says they enjoy novels with thoughtful character development and a strong sense of place?",
            "Find the user memory about novels with thoughtful character development and a strong sense of place.",
            "What should recommendations remember about novels with thoughtful character development and a strong sense of place for this person's books choices?",
        ),
    },
    "dev-user-032": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which books preference says they prefer book recommendations that include a brief spoiler-free reason why each title fits their interests?",
            "Find the user memory about book recommendations that include a brief spoiler-free reason why each title fits their interests.",
            "What should recommendations remember about book recommendations that include a brief spoiler-free reason why each title fits their interests for this person's books choices?",
        ),
    },
    "dev-user-033": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which books preference says they like nonfiction that explains complex topics clearly without sounding like a textbook?",
            "Find the user memory about nonfiction that explains complex topics clearly without sounding like a textbook.",
            "What should recommendations remember about nonfiction that explains complex topics clearly without sounding like a textbook for this person's books choices?",
        ),
    },
    "dev-user-034": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which books preference says they appreciate concise chapters because they make it easier to read during short breaks?",
            "Find the user memory about concise chapters because they make it easier to read during short breaks.",
            "What should recommendations remember about concise chapters because they make it easier to read during short breaks for this person's books choices?",
        ),
    },
    "dev-user-035": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which books preference says they often alternate between lighter reads and more demanding books to avoid burnout; they like having one comforting option available after finishing something dense?",
            "Find the user memory about between lighter reads and more demanding books to avoid burnout; they like having one comforting option available after finishing something dense.",
            "What should recommendations remember about between lighter reads and more demanding books to avoid burnout for this person's books choices?",
        ),
    },
    "dev-user-036": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which books preference says they enjoy science fiction when it focuses on human consequences instead of only technology; they prefer speculative ideas that still leave room for believable emotions and relationships?",
            "Find the user memory about science fiction when it focuses on human consequences instead of only technology; they prefer speculative ideas that still leave room for believable emotions and relationships.",
            "What should recommendations remember about science fiction when it focuses on human consequences instead of only technology for this person's books choices?",
        ),
    },
    "dev-user-037": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which books preference says they appreciate mysteries that play fair with the reader and avoid overly convenient twists; they like clues to feel visible in hindsight rather than hidden by the author?",
            "Find the user memory about mysteries that play fair with the reader and avoid overly convenient twists; they like clues to feel visible in hindsight rather than hidden by the author.",
            "What should recommendations remember about mysteries that play fair with the reader and avoid overly convenient twists for this person's books choices?",
        ),
    },
    "dev-user-038": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which books preference says they keep a small to-read list and prefers three to five strong options over long catalogs; they are more likely to start a book when the recommendation includes tone, pacing, and approximate length; if a series is suggested, they want to know whether the first book stands on its own?",
            "Find the user memory about a small to-read list and prefers three to five strong options over long catalogs; they are more likely to start a book when the recommendation includes tone, pacing, and approximate length; if a series is suggested, they want to know whether the first book stands on its own.",
            "What should recommendations remember about a small to-read list and prefers three to five strong options over long catalogs for this person's books choices?",
        ),
    },
    "dev-user-039": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which books preference says they are interested in memoirs when they connect personal stories to broader cultural or historical context; they prefer reflective writing over celebrity gossip or shock value; a grounded narrative voice matters more to them than dramatic events?",
            "Find the user memory about memoirs when they connect personal stories to broader cultural or historical context; they prefer reflective writing over celebrity gossip or shock value; a grounded narrative voice matters more to them than dramatic events.",
            "What should recommendations remember about memoirs when they connect personal stories to broader cultural or historical context for this person's books choices?",
        ),
    },
    "dev-user-040": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which books preference says they like reading before bed but avoids books that are too tense late at night; they usually save thrillers, heavy nonfiction, and emotionally intense novels for weekends or earlier in the day; calmer literary fiction, essays, or cozy mysteries work better for evening reading?",
            "Find the user memory about reading before bed but avoids books that are too tense late at night; they usually save thrillers, heavy nonfiction, and emotionally intense novels for weekends or earlier in the day; calmer literary fiction, essays, or cozy mysteries work better for evening reading.",
            "What should recommendations remember about reading before bed but avoids books that are too tense late at night for this person's books choices?",
        ),
    },
    "dev-user-041": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which cooking preference says they prefer weeknight dinners that can be made in about 30 minutes with minimal cleanup?",
            "Find the user memory about weeknight dinners that can be made in about 30 minutes with minimal cleanup.",
            "What should recommendations remember about weeknight dinners that can be made in about 30 minutes with minimal cleanup for this person's cooking choices?",
        ),
    },
    "dev-user-042": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which cooking preference says they like Mediterranean-inspired meals with vegetables, grains, olive oil, and simple proteins?",
            "Find the user memory about Mediterranean-inspired meals with vegetables, grains, olive oil, and simple proteins.",
            "What should recommendations remember about Mediterranean-inspired meals with vegetables, grains, olive oil, and simple proteins for this person's cooking choices?",
        ),
    },
    "dev-user-043": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which cooking preference says they usually keeps pantry staples like pasta, rice, beans, canned tomatoes, and basic spices on hand?",
            "Find the user memory about they usually keeps pantry staples like pasta, rice, beans, canned tomatoes, and basic spices on hand.",
            "What should recommendations remember about they usually keeps pantry staples like pasta, rice, beans, canned tomatoes, and basic spices on hand for this person's cooking choices?",
        ),
    },
    "dev-user-044": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which cooking preference says they prefer savory breakfasts over sweet breakfasts when they have time to cook?",
            "Find the user memory about savory breakfasts over sweet breakfasts when they have time to cook.",
            "What should recommendations remember about savory breakfasts over sweet breakfasts when they have time to cook for this person's cooking choices?",
        ),
    },
    "dev-user-045": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which cooking preference says they enjoy cooking at home and appreciates recipes with clear steps; they like when substitutions are offered for common ingredients they may already have?",
            "Find the user memory about cooking at home and appreciates recipes with clear steps; they like when substitutions are offered for common ingredients they may already have.",
            "What should recommendations remember about cooking at home and appreciates recipes with clear steps for this person's cooking choices?",
        ),
    },
    "dev-user-046": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which cooking preference says they like batch-cooking soups, stews, or grain bowls for easy lunches during the week; meals that reheat well are especially useful for their routine?",
            "Find the user memory about batch-cooking soups, stews, or grain bowls for easy lunches during the week; meals that reheat well are especially useful for their routine.",
            "What should recommendations remember about batch-cooking soups, stews, or grain bowls for easy lunches during the week for this person's cooking choices?",
        ),
    },
    "dev-user-047": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which cooking preference says they enjoy trying new recipes but does not want overly complicated techniques on busy days; they are more likely to attempt a project recipe on a quiet weekend?",
            "Find the user memory about trying new recipes but does not want overly complicated techniques on busy days; they are more likely to attempt a project recipe on a quiet weekend.",
            "What should recommendations remember about trying new recipes but does not want overly complicated techniques on busy days for this person's cooking choices?",
        ),
    },
    "dev-user-048": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which cooking preference says they are interested in improving knife skills and becoming faster at prep work; they would like practical guidance on safe hand position, even cuts, and efficient cleanup; short practice drills are more appealing than formal culinary lessons?",
            "Find the user memory about improving knife skills and becoming faster at prep work; they would like practical guidance on safe hand position, even cuts, and efficient cleanup; short practice drills are more appealing than formal culinary lessons.",
            "What should recommendations remember about improving knife skills and becoming faster at prep work for this person's cooking choices?",
        ),
    },
    "dev-user-049": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which cooking preference says they like balanced meals that include protein, vegetables, and a satisfying carbohydrate; they prefer recipes that feel filling without requiring heavy sauces or a long ingredient list; a simple side salad or roasted vegetable is usually enough to round out dinner?",
            "Find the user memory about balanced meals that include protein, vegetables, and a satisfying carbohydrate; they prefer recipes that feel filling without requiring heavy sauces or a long ingredient list; a simple side salad or roasted vegetable is usually enough to round out dinner.",
            "What should recommendations remember about balanced meals that include protein, vegetables, and a satisfying carbohydrate for this person's cooking choices?",
        ),
    },
    "dev-user-050": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which cooking preference says they often plans meals around what needs to be used up in the refrigerator; they appreciate suggestions that combine leftover herbs, half-used vegetables, or cooked grains into something intentional; they dislike wasting food but do not want every meal to feel like a compromise?",
            "Find the user memory about they often plans meals around what needs to be used up in the refrigerator; they appreciate suggestions that combine leftover herbs, half-used vegetables, or cooked grains into something intentional; they dislike wasting food but do not want every meal to feel like a compromise.",
            "What should recommendations remember about they often plans meals around what needs to be used up in the refrigerator for this person's cooking choices?",
        ),
    },
    "dev-user-051": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which fitness preference says they prefer a practical fitness routine that fits into a normal workweek?",
            "Find the user memory about a practical fitness routine that fits into a normal workweek.",
            "What should recommendations remember about a practical fitness routine that fits into a normal workweek for this person's fitness choices?",
        ),
    },
    "dev-user-052": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which fitness preference says they like strength training plans that explain the purpose of each movement?",
            "Find the user memory about strength training plans that explain the purpose of each movement.",
            "What should recommendations remember about strength training plans that explain the purpose of each movement for this person's fitness choices?",
        ),
    },
    "dev-user-053": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which fitness preference says they enjoy walks as a low-pressure way to stay active and clear their head?",
            "Find the user memory about walks as a low-pressure way to stay active and clear their head.",
            "What should recommendations remember about walks as a low-pressure way to stay active and clear their head for this person's fitness choices?",
        ),
    },
    "dev-user-054": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which fitness preference says they prefer progress tracking that focuses on consistency rather than perfection?",
            "Find the user memory about progress tracking that focuses on consistency rather than perfection.",
            "What should recommendations remember about progress tracking that focuses on consistency rather than perfection for this person's fitness choices?",
        ),
    },
    "dev-user-055": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which fitness preference says they like workouts that include warmup guidance; they are more likely to follow a plan when the first few minutes feel approachable?",
            "Find the user memory about workouts that include warmup guidance; they are more likely to follow a plan when the first few minutes feel approachable.",
            "What should recommendations remember about workouts that include warmup guidance for this person's fitness choices?",
        ),
    },
    "dev-user-056": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which fitness preference says they prefer simple equipment options such as dumbbells, bands, or bodyweight movements; they do not want a routine that depends on a crowded gym?",
            "Find the user memory about simple equipment options such as dumbbells, bands, or bodyweight movements; they do not want a routine that depends on a crowded gym.",
            "What should recommendations remember about simple equipment options such as dumbbells, bands, or bodyweight movements for this person's fitness choices?",
        ),
    },
    "dev-user-057": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which fitness preference says they appreciate mobility exercises for shoulders, hips, and back comfort; short routines are easier for them to keep up with than long stretching sessions?",
            "Find the user memory about mobility exercises for shoulders, hips, and back comfort; short routines are easier for them to keep up with than long stretching sessions.",
            "What should recommendations remember about mobility exercises for shoulders, hips, and back comfort for this person's fitness choices?",
        ),
    },
    "dev-user-058": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which fitness preference says they prefer fitness advice that respects rest days; they want to avoid turning every missed workout into a failure; a sustainable plan matters more than a perfect streak?",
            "Find the user memory about fitness advice that respects rest days; they want to avoid turning every missed workout into a failure; a sustainable plan matters more than a perfect streak.",
            "What should recommendations remember about fitness advice that respects rest days for this person's fitness choices?",
        ),
    },
    "dev-user-059": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which fitness preference says they like cardio options that can be adjusted for energy level; a brisk walk, easy bike ride, or short interval session can all fit depending on the day; clear intensity cues help them choose the right version?",
            "Find the user memory about cardio options that can be adjusted for energy level; a brisk walk, easy bike ride, or short interval session can all fit depending on the day; clear intensity cues help them choose the right version.",
            "What should recommendations remember about cardio options that can be adjusted for energy level for this person's fitness choices?",
        ),
    },
    "dev-user-060": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which fitness preference says they are interested in building strength without chasing extreme goals; they prefer steady improvements, good form, and fewer aches; plans with realistic recovery time feel more trustworthy?",
            "Find the user memory about building strength without chasing extreme goals; they prefer steady improvements, good form, and fewer aches; plans with realistic recovery time feel more trustworthy.",
            "What should recommendations remember about building strength without chasing extreme goals for this person's fitness choices?",
        ),
    },
    "dev-user-061": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which music preference says they like having different playlists for focus, errands, workouts, and relaxing at home?",
            "Find the user memory about having different playlists for focus, errands, workouts, and relaxing at home.",
            "What should recommendations remember about having different playlists for focus, errands, workouts, and relaxing at home for this person's music choices?",
        ),
    },
    "dev-user-062": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which music preference says they enjoy discovering new artists through recommendations based on songs they already like?",
            "Find the user memory about discovering new artists through recommendations based on songs they already like.",
            "What should recommendations remember about discovering new artists through recommendations based on songs they already like for this person's music choices?",
        ),
    },
    "dev-user-063": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which music preference says they often listen to instrumental or low-vocal music while doing focused work?",
            "Find the user memory about to instrumental or low-vocal music while doing focused work.",
            "What should recommendations remember about to instrumental or low-vocal music while doing focused work for this person's music choices?",
        ),
    },
    "dev-user-064": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which music preference says they like upbeat music for cleaning, cooking, and other household tasks?",
            "Find the user memory about upbeat music for cleaning, cooking, and other household tasks.",
            "What should recommendations remember about upbeat music for cleaning, cooking, and other household tasks for this person's music choices?",
        ),
    },
    "dev-user-065": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which music preference says they prefer music suggestions that include a short explanation of why they might fit the mood; they are more likely to try a track when the recommendation mentions tempo, vocals, and overall energy?",
            "Find the user memory about music suggestions that include a short explanation of why they might fit the mood; they are more likely to try a track when the recommendation mentions tempo, vocals, and overall energy.",
            "What should recommendations remember about music suggestions that include a short explanation of why they might fit the mood for this person's music choices?",
        ),
    },
    "dev-user-066": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which music preference says they appreciate both older classics and newer releases when exploring a genre; they like hearing how newer songs connect to earlier influences without getting a lecture?",
            "Find the user memory about both older classics and newer releases when exploring a genre; they like hearing how newer songs connect to earlier influences without getting a lecture.",
            "What should recommendations remember about both older classics and newer releases when exploring a genre for this person's music choices?",
        ),
    },
    "dev-user-067": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which music preference says they prefer playlists that have a consistent mood rather than jumping sharply between styles; smooth transitions matter more to them than strict genre purity?",
            "Find the user memory about playlists that have a consistent mood rather than jumping sharply between styles; smooth transitions matter more to them than strict genre purity.",
            "What should recommendations remember about playlists that have a consistent mood rather than jumping sharply between styles for this person's music choices?",
        ),
    },
    "dev-user-068": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which music preference says they like acoustic or mellow music in the evening; they usually avoid aggressive drums or very bright production late at night; calm vocals, soft guitar, or gentle piano fit that part of the day best?",
            "Find the user memory about acoustic or mellow music in the evening; they usually avoid aggressive drums or very bright production late at night; calm vocals, soft guitar, or gentle piano fit that part of the day best.",
            "What should recommendations remember about acoustic or mellow music in the evening for this person's music choices?",
        ),
    },
    "dev-user-069": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which music preference says they is open to music from different countries and languages when the vibe matches the request; they do not need to understand every lyric to enjoy a song; a brief note about the style or region helps them decide what to play next?",
            "Find the user memory about they is open to music from different countries and languages when the vibe matches the request; they do not need to understand every lyric to enjoy a song; a brief note about the style or region helps them decide what to play next.",
            "What should recommendations remember about they is open to music from different countries and languages when the vibe matches the request for this person's music choices?",
        ),
    },
    "dev-user-070": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which music preference says they enjoy learning small bits of context about an album, artist, or genre; they prefer a few memorable details over a long history lesson; release era, standout instruments, and listening mood are the most useful context for them?",
            "Find the user memory about learning small bits of context about an album, artist, or genre; they prefer a few memorable details over a long history lesson; release era, standout instruments, and listening mood are the most useful context for them.",
            "What should recommendations remember about learning small bits of context about an album, artist, or genre for this person's music choices?",
        ),
    },
    "dev-user-071": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which pets preference says they like pet care routines that are calm, predictable, and easy to maintain?",
            "Find the user memory about pet care routines that are calm, predictable, and easy to maintain.",
            "What should recommendations remember about pet care routines that are calm, predictable, and easy to maintain for this person's pets choices?",
        ),
    },
    "dev-user-072": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which pets preference says they prefer pet product recommendations that mention durability, washability, and noise level?",
            "Find the user memory about pet product recommendations that mention durability, washability, and noise level.",
            "What should recommendations remember about pet product recommendations that mention durability, washability, and noise level for this person's pets choices?",
        ),
    },
    "dev-user-073": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which pets preference says they enjoy homes with practical spaces for leashes, brushes, treats, and cleanup supplies?",
            "Find the user memory about homes with practical spaces for leashes, brushes, treats, and cleanup supplies.",
            "What should recommendations remember about homes with practical spaces for leashes, brushes, treats, and cleanup supplies for this person's pets choices?",
        ),
    },
    "dev-user-074": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which pets preference says they like pet advice that balances comfort, enrichment, and safety without being overly fussy?",
            "Find the user memory about pet advice that balances comfort, enrichment, and safety without being overly fussy.",
            "What should recommendations remember about pet advice that balances comfort, enrichment, and safety without being overly fussy for this person's pets choices?",
        ),
    },
    "dev-user-075": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which pets preference says they prefer feeding reminders that are simple and consistent; they are easier to follow when they include morning and evening checkpoints?",
            "Find the user memory about feeding reminders that are simple and consistent; they are easier to follow when they include morning and evening checkpoints.",
            "What should recommendations remember about feeding reminders that are simple and consistent for this person's pets choices?",
        ),
    },
    "dev-user-076": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which pets preference says they like enrichment ideas such as puzzle feeders, rotating toys, and short training games; they prefer activities that can fit into a normal day?",
            "Find the user memory about enrichment ideas such as puzzle feeders, rotating toys, and short training games; they prefer activities that can fit into a normal day.",
            "What should recommendations remember about enrichment ideas such as puzzle feeders, rotating toys, and short training games for this person's pets choices?",
        ),
    },
    "dev-user-077": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which pets preference says they appreciate pet-friendly travel tips that mention lodging rules, quiet walking routes, and nearby green space; they dislike advice that assumes every pet is comfortable in crowded places?",
            "Find the user memory about pet-friendly travel tips that mention lodging rules, quiet walking routes, and nearby green space; they dislike advice that assumes every pet is comfortable in crowded places.",
            "What should recommendations remember about pet-friendly travel tips that mention lodging rules, quiet walking routes, and nearby green space for this person's pets choices?",
        ),
    },
    "dev-user-078": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which pets preference says they prefer pet areas that are tidy but not sterile; a washable blanket, a toy basket, and easy access to water make the space feel intentional; they like setups that work for both daily life and guests?",
            "Find the user memory about pet areas that are tidy but not sterile; a washable blanket, a toy basket, and easy access to water make the space feel intentional; they like setups that work for both daily life and guests.",
            "What should recommendations remember about pet areas that are tidy but not sterile for this person's pets choices?",
        ),
    },
    "dev-user-079": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which pets preference says they is careful about plants, cleaners, and small objects around pets; new items should be checked before they are left within reach; safety matters more than matching the room perfectly?",
            "Find the user memory about they is careful about plants, cleaners, and small objects around pets; new items should be checked before they are left within reach; safety matters more than matching the room perfectly.",
            "What should recommendations remember about they is careful about plants, cleaners, and small objects around pets for this person's pets choices?",
        ),
    },
    "dev-user-080": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which pets preference says they like training approaches based on patience and short practice sessions; clear cues, small rewards, and breaks help keep the routine positive; they avoid methods that make a pet seem scared or confused?",
            "Find the user memory about training approaches based on patience and short practice sessions; clear cues, small rewards, and breaks help keep the routine positive; they avoid methods that make a pet seem scared or confused.",
            "What should recommendations remember about training approaches based on patience and short practice sessions for this person's pets choices?",
        ),
    },
    "dev-user-081": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which learning preference says they prefer learning plans that break a skill into small, concrete steps?",
            "Find the user memory about learning plans that break a skill into small, concrete steps.",
            "What should recommendations remember about learning plans that break a skill into small, concrete steps for this person's learning choices?",
        ),
    },
    "dev-user-082": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which learning preference says they like tutorials that include one practical exercise after each concept?",
            "Find the user memory about tutorials that include one practical exercise after each concept.",
            "What should recommendations remember about tutorials that include one practical exercise after each concept for this person's learning choices?",
        ),
    },
    "dev-user-083": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which learning preference says they keep better momentum when lessons have clear checkpoints and visible progress?",
            "Find the user memory about better momentum when lessons have clear checkpoints and visible progress.",
            "What should recommendations remember about better momentum when lessons have clear checkpoints and visible progress for this person's learning choices?",
        ),
    },
    "dev-user-084": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which learning preference says they prefer explanations that start with an example before introducing formal terminology?",
            "Find the user memory about explanations that start with an example before introducing formal terminology.",
            "What should recommendations remember about explanations that start with an example before introducing formal terminology for this person's learning choices?",
        ),
    },
    "dev-user-085": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which learning preference says they like taking notes in their own words after finishing a lesson; this helps them notice what they actually understood?",
            "Find the user memory about taking notes in their own words after finishing a lesson; this helps them notice what they actually understood.",
            "What should recommendations remember about taking notes in their own words after finishing a lesson for this person's learning choices?",
        ),
    },
    "dev-user-086": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which learning preference says they enjoy learning through small projects that produce something useful; they find abstract drills easier to tolerate when there is a visible outcome?",
            "Find the user memory about learning through small projects that produce something useful; they find abstract drills easier to tolerate when there is a visible outcome.",
            "What should recommendations remember about learning through small projects that produce something useful for this person's learning choices?",
        ),
    },
    "dev-user-087": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which learning preference says they prefer review sessions that revisit earlier material without feeling punitive; gentle repetition helps them retain details over time?",
            "Find the user memory about review sessions that revisit earlier material without feeling punitive; gentle repetition helps them retain details over time.",
            "What should recommendations remember about review sessions that revisit earlier material without feeling punitive for this person's learning choices?",
        ),
    },
    "dev-user-088": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which learning preference says they get discouraged by courses that skip setup details; they appreciate instructions that mention prerequisites, common mistakes, and how to verify the result; a clear first success makes the next step easier?",
            "Find the user memory about courses that skip setup details; they appreciate instructions that mention prerequisites, common mistakes, and how to verify the result; a clear first success makes the next step easier.",
            "What should recommendations remember about courses that skip setup details for this person's learning choices?",
        ),
    },
    "dev-user-089": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which learning preference says they like comparing two or three examples when learning a new pattern; seeing the same idea in different contexts helps them generalize it; they prefer concise explanations over long theoretical detours?",
            "Find the user memory about comparing two or three examples when learning a new pattern; seeing the same idea in different contexts helps them generalize it; they prefer concise explanations over long theoretical detours.",
            "What should recommendations remember about comparing two or three examples when learning a new pattern for this person's learning choices?",
        ),
    },
    "dev-user-090": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which learning preference says they is more likely to finish a learning plan when the workload is realistic; short sessions, spaced practice, and small milestones fit better than weekend marathons; they want enough structure to continue without feeling boxed in?",
            "Find the user memory about they is more likely to finish a learning plan when the workload is realistic; short sessions, spaced practice, and small milestones fit better than weekend marathons; they want enough structure to continue without feeling boxed in.",
            "What should recommendations remember about they is more likely to finish a learning plan when the workload is realistic for this person's learning choices?",
        ),
    },
    "dev-user-091": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which home style preference says they prefer warm lighting, natural textures, and rooms that feel lived-in rather than staged?",
            "Find the user memory about warm lighting, natural textures, and rooms that feel lived-in rather than staged.",
            "What should recommendations remember about warm lighting, natural textures, and rooms that feel lived-in rather than staged for this person's home style choices?",
        ),
    },
    "dev-user-092": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which home style preference says they like entryway storage that keeps shoes, bags, keys, and mail from spreading through the house?",
            "Find the user memory about entryway storage that keeps shoes, bags, keys, and mail from spreading through the house.",
            "What should recommendations remember about entryway storage that keeps shoes, bags, keys, and mail from spreading through the house for this person's home style choices?",
        ),
    },
    "dev-user-093": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which home style preference says they prefer linen curtains, simple rugs, and muted colors with a few warmer accents?",
            "Find the user memory about linen curtains, simple rugs, and muted colors with a few warmer accents.",
            "What should recommendations remember about linen curtains, simple rugs, and muted colors with a few warmer accents for this person's home style choices?",
        ),
    },
    "dev-user-094": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which home style preference says they like arranging houseplants in small clusters near windows where they are easy to water?",
            "Find the user memory about arranging houseplants in small clusters near windows where they are easy to water.",
            "What should recommendations remember about arranging houseplants in small clusters near windows where they are easy to water for this person's home style choices?",
        ),
    },
    "dev-user-095": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which home style preference says they prefer rooms with one comfortable reading spot; a good lamp, side table, and soft blanket matter more than decorative extras?",
            "Find the user memory about rooms with one comfortable reading spot; a good lamp, side table, and soft blanket matter more than decorative extras.",
            "What should recommendations remember about rooms with one comfortable reading spot for this person's home style choices?",
        ),
    },
    "dev-user-096": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which home style preference says they like home offices with a clear desk surface and a visible place for notes; clutter feels less stressful when there is a specific tray or board for it?",
            "Find the user memory about home offices with a clear desk surface and a visible place for notes; clutter feels less stressful when there is a specific tray or board for it.",
            "What should recommendations remember about home offices with a clear desk surface and a visible place for notes for this person's home style choices?",
        ),
    },
    "dev-user-097": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which home style preference says they prefer kitchens with open counter space and practical storage; a few attractive everyday items can stay out, but crowded displays are frustrating?",
            "Find the user memory about kitchens with open counter space and practical storage; a few attractive everyday items can stay out, but crowded displays are frustrating.",
            "What should recommendations remember about kitchens with open counter space and practical storage for this person's home style choices?",
        ),
    },
    "dev-user-098": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which home style preference says they like guest rooms that feel calm and useful without being formal; a small lamp, clear surface, spare blanket, and place for a suitcase are enough; the room should be easy to reset after visitors leave?",
            "Find the user memory about guest rooms that feel calm and useful without being formal; a small lamp, clear surface, spare blanket, and place for a suitcase are enough; the room should be easy to reset after visitors leave.",
            "What should recommendations remember about guest rooms that feel calm and useful without being formal for this person's home style choices?",
        ),
    },
    "dev-user-099": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which home style preference says they prefer a cozy style that mixes pale wood, warm brass, soft greens, and clay-colored accents; they like handmade details when they are subtle; the overall goal is tidy, comfortable, and personal?",
            "Find the user memory about a cozy style that mixes pale wood, warm brass, soft greens, and clay-colored accents; they like handmade details when they are subtle; the overall goal is tidy, comfortable, and personal.",
            "What should recommendations remember about a cozy style that mixes pale wood, warm brass, soft greens, and clay-colored accents for this person's home style choices?",
        ),
    },
    "dev-user-100": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which home style preference says they like seasonal decor in small doses; a wreath, candle, or bowl of fruit feels better than changing the whole room; they prefer decorations that are easy to store and reuse?",
            "Find the user memory about seasonal decor in small doses; a wreath, candle, or bowl of fruit feels better than changing the whole room; they prefer decorations that are easy to store and reuse.",
            "What should recommendations remember about seasonal decor in small doses for this person's home style choices?",
        ),
    },
    "dev-workspace-01-001": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which permissions memory covers the product uses tiered permissions so shop owners approve bank connections, managers inspect reports, and clerks record daily sales without reaching administrative settings; the setup mirrors how small workshops separate counter work from financial oversight?",
            "Find the CedarLedger note about uses tiered permissions so shop owners approve bank connections, managers inspect reports, and clerks record daily sales without reaching administrative settings; the setup mirrors how small workshops separate counter work from financial oversight.",
            "What should the CedarLedger team remember about uses tiered permissions so shop owners approve bank connections, managers inspect reports, and clerks record daily sales without reaching administrative settings in the permissions area?",
        ),
    },
    "dev-workspace-01-002": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which permissions memory covers Payroll notes and owner draws stay visible only to finance administrators, even when a workspace teammate can browse ordinary expense categories. That boundary keeps sensitive compensation details away from routine bookkeeping chores?",
            "Find the CedarLedger note about Payroll notes and owner draws stay visible only to finance administrators, even when a workspace teammate can browse ordinary expense categories. That boundary keeps sensitive compensation details away from routine bookkeeping chores.",
            "What should the CedarLedger team remember about Payroll notes and owner draws stay visible only to finance administrators, even when a workspace teammate can browse ordinary expense categories in the permissions area?",
        ),
    },
    "dev-workspace-01-003": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which permissions memory covers New bookkeeper invitations should land in a read-only reviewer seat until the workshop owner deliberately grants editing rights; the first visit should explain that extra capabilities require owner confirmation?",
            "Find the CedarLedger note about New bookkeeper invitations should land in a read-only reviewer seat until the workshop owner deliberately grants editing rights; the first visit should explain that extra capabilities require owner confirmation.",
            "What should the CedarLedger team remember about New bookkeeper invitations should land in a read-only reviewer seat until the workshop owner deliberately grants editing rights in the permissions area?",
        ),
    },
    "dev-workspace-01-004": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which permissions memory covers Server-side guards must protect every bill, attachment, and month-end review endpoint rather than relying on hidden navigation items?",
            "Find the CedarLedger note about Server-side guards must protect every bill, attachment, and month-end review endpoint rather than relying on hidden navigation items.",
            "What should the CedarLedger team remember about Server-side guards must protect every bill, attachment, and month-end review endpoint rather than relying on hidden navigation items in the permissions area?",
        ),
    },
    "dev-workspace-01-005": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which permissions memory covers Cash-drawer clerks can enter daily takings and supplier slips, but they should not change tax settings, payout accounts, or workspace billing details?",
            "Find the CedarLedger note about Cash-drawer clerks can enter daily takings and supplier slips, but they should not change tax settings, payout accounts, or workspace billing details.",
            "What should the CedarLedger team remember about Cash-drawer clerks can enter daily takings and supplier slips, but they should not change tax settings, payout accounts, or workspace billing details in the permissions area?",
        ),
    },
    "dev-workspace-01-006": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which permissions memory covers a bug where switching between two workshops reused the earlier workspace's cached capabilities until refresh. Disabled controls briefly looked usable for the wrong account; the fix should clear local grants whenever the workspace selector changes?",
            "Find the CedarLedger note about bug where switching between two workshops reused the earlier workspace's cached capabilities until refresh. Disabled controls briefly looked usable for the wrong account; the fix should clear local grants whenever the workspace selector changes.",
            "What should the CedarLedger team remember about bug where switching between two workshops reused the earlier workspace's cached capabilities until refresh in the permissions area?",
        ),
    },
    "dev-workspace-01-007": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which permissions memory covers the owner seat may transfer ownership only after re-authentication; the audit trail records the former owner, the incoming owner, and the timestamp without exposing secrets. A confirmation screen should summarize the irreversible parts of the change?",
            "Find the CedarLedger note about owner seat may transfer ownership only after re-authentication; the audit trail records the former owner, the incoming owner, and the timestamp without exposing secrets. A confirmation screen should summarize the irreversible parts of the change.",
            "What should the CedarLedger team remember about owner seat may transfer ownership only after re-authentication in the permissions area?",
        ),
    },
    "dev-workspace-01-008": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which permissions memory covers Support staff may inspect CedarLedger diagnostic metadata but must not open transaction descriptions, attachment previews, or connected balance details; the troubleshooting screen should explain which fields are intentionally masked; this keeps help-desk work separate from private financial content?",
            "Find the CedarLedger note about Support staff may inspect CedarLedger diagnostic metadata but must not open transaction descriptions, attachment previews, or connected balance details; the troubleshooting screen should explain which fields are intentionally masked; this keeps help-desk work separate from private financial content.",
            "What should the CedarLedger team remember about Support staff may inspect CedarLedger diagnostic metadata but must not open transaction descriptions, attachment previews, or connected balance details in the permissions area?",
        ),
    },
    "dev-workspace-01-009": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which permissions memory covers Archived workshops need a separate matrix rule: members may read historical ledger summaries, while only an owner can reactivate or alter records. Invite actions should disappear while the workspace is archived; the read-only banner should mention who can reopen the workspace?",
            "Find the CedarLedger note about Archived workshops need a separate matrix rule: members may read historical ledger summaries, while only an owner can reactivate or alter records. Invite actions should disappear while the workspace is archived; the read-only banner should mention who can reopen the workspace.",
            "What should the CedarLedger team remember about Archived workshops need a separate matrix rule: members may read historical ledger summaries, while only an owner can reactivate or alter records in the permissions area?",
        ),
    },
    "dev-workspace-01-010": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which permissions memory covers After a password change, other active sessions should be invalidated while the current re-authenticated session survives. CedarLedger needs regression coverage for open report tabs and a fresh authorization check before any ledger package leaves the app. Stale tabs should show a prompt instead of silently continuing?",
            "Find the CedarLedger note about After a password change, other active sessions should be invalidated while the current re-authenticated session survives. CedarLedger needs regression coverage for open report tabs and a fresh authorization check before any ledger package leaves the app. Stale tabs should show a prompt instead of silently continuing.",
            "What should the CedarLedger team remember about After a password change, other active sessions should be invalidated while the current re-authenticated session survives in the permissions area?",
        ),
    },
    "dev-workspace-01-011": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which exports memory covers the product provides CSV and JSON exports so workshop owners can inspect monthly income, expenses, and category totals in the tool that suits their review process?",
            "Find the CedarLedger note about provides CSV and JSON exports so workshop owners can inspect monthly income, expenses, and category totals in the tool that suits their review process.",
            "What should the CedarLedger team remember about provides CSV and JSON exports so workshop owners can inspect monthly income, expenses, and category totals in the tool that suits their review process in the exports area?",
        ),
    },
    "dev-workspace-01-012": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which exports memory covers Monthly report packages should include a generated timestamp in the name so repeated pulls from the same date range remain easy to tell apart?",
            "Find the CedarLedger note about Monthly report packages should include a generated timestamp in the name so repeated pulls from the same date range remain easy to tell apart.",
            "What should the CedarLedger team remember about Monthly report packages should include a generated timestamp in the name so repeated pulls from the same date range remain easy to tell apart in the exports area?",
        ),
    },
    "dev-workspace-01-013": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which exports memory covers Sample accounting rows used for development output rely on generic vendors, rounded amounts, and harmless reference numbers?",
            "Find the CedarLedger note about Sample accounting rows used for development output rely on generic vendors, rounded amounts, and harmless reference numbers.",
            "What should the CedarLedger team remember about Sample accounting rows used for development output rely on generic vendors, rounded amounts, and harmless reference numbers in the exports area?",
        ),
    },
    "dev-workspace-01-014": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which exports memory covers Spreadsheet output needs a stable column order for date, entry ID, account, category, description, debit, credit, currency, and batch marker. Tests should fail when a column moves without a migration note. Reviewer macros depend on those positions staying predictable?",
            "Find the CedarLedger note about Spreadsheet output needs a stable column order for date, entry ID, account, category, description, debit, credit, currency, and batch marker. Tests should fail when a column moves without a migration note. Reviewer macros depend on those positions staying predictable.",
            "What should the CedarLedger team remember about Spreadsheet output needs a stable column order for date, entry ID, account, category, description, debit, credit, currency, and batch marker in the exports area?",
        ),
    },
    "dev-workspace-01-015": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which exports memory covers A task remains to add a restorable ledger snapshot covering accounts, categories, entries, month-end notes, and report metadata; it must omit credentials and local paths; the restore preview should list record counts before applying changes?",
            "Find the CedarLedger note about A task remains to add a restorable ledger snapshot covering accounts, categories, entries, month-end notes, and report metadata; it must omit credentials and local paths; the restore preview should list record counts before applying changes.",
            "What should the CedarLedger team remember about A task remains to add a restorable ledger snapshot covering accounts, categories, entries, month-end notes, and report metadata in the exports area?",
        ),
    },
    "dev-workspace-01-016": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which exports memory covers A bug sorted April workshop expenses by description instead of transaction date, which made the monthly spreadsheet appear out of sequence?",
            "Find the CedarLedger note about A bug sorted April workshop expenses by description instead of transaction date, which made the monthly spreadsheet appear out of sequence.",
            "What should the CedarLedger team remember about A bug sorted April workshop expenses by description instead of transaction date, which made the monthly spreadsheet appear out of sequence in the exports area?",
        ),
    },
    "dev-workspace-01-017": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which exports memory covers the packaging settings panel should default generated artifact timestamps to UTC. Report contents may still display the CedarLedger workspace timezone; this avoids ambiguous archive names across daylight-saving changes?",
            "Find the CedarLedger note about packaging settings panel should default generated artifact timestamps to UTC. Report contents may still display the CedarLedger workspace timezone; this avoids ambiguous archive names across daylight-saving changes.",
            "What should the CedarLedger team remember about packaging settings panel should default generated artifact timestamps to UTC in the exports area?",
        ),
    },
    "dev-workspace-01-018": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which exports memory covers the product archive bundles should contain generic ledger examples such as tool purchases, workshop rent income, and materials refunds; the values need to be plain enough for screenshots. Example descriptions should avoid brand names and personal names?",
            "Find the CedarLedger note about archive bundles should contain generic ledger examples such as tool purchases, workshop rent income, and materials refunds; the values need to be plain enough for screenshots. Example descriptions should avoid brand names and personal names.",
            "What should the CedarLedger team remember about archive bundles should contain generic ledger examples such as tool purchases, workshop rent income, and materials refunds in the exports area?",
        ),
    },
    "dev-workspace-01-019": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which exports memory covers Structured state bundles are best for restoring CedarLedger, while spreadsheets suit reviewers who only need totals and transaction rows; the screen should explain the difference in one short helper note, with both formats sharing the selected date range. Both outputs should use the same cutoff rules?",
            "Find the CedarLedger note about Structured state bundles are best for restoring CedarLedger, while spreadsheets suit reviewers who only need totals and transaction rows; the screen should explain the difference in one short helper note, with both formats sharing the selected date range. Both outputs should use the same cutoff rules.",
            "What should the CedarLedger team remember about Structured state bundles are best for restoring CedarLedger, while spreadsheets suit reviewers who only need totals and transaction rows in the exports area?",
        ),
    },
    "dev-workspace-01-020": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which exports memory covers the monthly archive workflow should write a checksum note into the manifest; users can confirm the package completed before storing it, and failed runs should discard partial artifacts before showing an error?",
            "Find the CedarLedger note about monthly archive workflow should write a checksum note into the manifest; users can confirm the package completed before storing it, and failed runs should discard partial artifacts before showing an error.",
            "What should the CedarLedger team remember about monthly archive workflow should write a checksum note into the manifest in the exports area?",
        ),
    },
    "dev-workspace-01-021": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which reconciliation memory covers the product calculates collected and outstanding totals separately during closeout. Workshop owners can compare cash received with work billed but not yet settled?",
            "Find the CedarLedger note about calculates collected and outstanding totals separately during closeout. Workshop owners can compare cash received with work billed but not yet settled.",
            "What should the CedarLedger team remember about calculates collected and outstanding totals separately during closeout in the reconciliation area?",
        ),
    },
    "dev-workspace-01-022": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which reconciliation memory covers the month-end review compares proof of expenses with imported records and flags vendor charges that have no supporting entry?",
            "Find the CedarLedger note about month-end review compares proof of expenses with imported records and flags vendor charges that have no supporting entry.",
            "What should the CedarLedger team remember about month-end review compares proof of expenses with imported records and flags vendor charges that have no supporting entry in the reconciliation area?",
        ),
    },
    "dev-workspace-01-023": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which reconciliation memory covers a customer bill marked settled must include a payment date, payment method, and linked ledger transaction before it appears in closed monthly totals?",
            "Find the CedarLedger note about customer bill marked settled must include a payment date, payment method, and linked ledger transaction before it appears in closed monthly totals.",
            "What should the CedarLedger team remember about customer bill marked settled must include a payment date, payment method, and linked ledger transaction before it appears in closed monthly totals in the reconciliation area?",
        ),
    },
    "dev-workspace-01-024": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which reconciliation memory covers Record pairing works best when CedarLedger weighs amount, date window, vendor or client name, and reference notes instead of exact memo text alone?",
            "Find the CedarLedger note about Record pairing works best when CedarLedger weighs amount, date window, vendor or client name, and reference notes instead of exact memo text alone.",
            "What should the CedarLedger team remember about Record pairing works best when CedarLedger weighs amount, date window, vendor or client name, and reference notes instead of exact memo text alone in the reconciliation area?",
        ),
    },
    "dev-workspace-01-025": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which reconciliation memory covers During February review, expense lines looked correct but two open customer bills still inflated the settled revenue total; the summary overstated cash actually received?",
            "Find the CedarLedger note about During February review, expense lines looked correct but two open customer bills still inflated the settled revenue total; the summary overstated cash actually received.",
            "What should the CedarLedger team remember about During February review, expense lines looked correct but two open customer bills still inflated the settled revenue total in the reconciliation area?",
        ),
    },
    "dev-workspace-01-026": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which reconciliation memory covers the product should explain why month-end totals differ, naming gaps from missing expense proof, open customer balances, duplicate imports, or pending records?",
            "Find the CedarLedger note about should explain why month-end totals differ, naming gaps from missing expense proof, open customer balances, duplicate imports, or pending records.",
            "What should the CedarLedger team remember about should explain why month-end totals differ, naming gaps from missing expense proof, open customer balances, duplicate imports, or pending records in the reconciliation area?",
        ),
    },
    "dev-workspace-01-027": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which reconciliation memory covers A filter is still needed for workshop supply charges that have not been cleared; users need to inspect materials purchases before finalizing the monthly report?",
            "Find the CedarLedger note about A filter is still needed for workshop supply charges that have not been cleared; users need to inspect materials purchases before finalizing the monthly report.",
            "What should the CedarLedger team remember about A filter is still needed for workshop supply charges that have not been cleared in the reconciliation area?",
        ),
    },
    "dev-workspace-01-028": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which reconciliation memory covers Partial customer payments remain open records until the remaining balance reaches zero; the received portion still contributes to collected revenue, while the outstanding amount stays visible beside the status?",
            "Find the CedarLedger note about Partial customer payments remain open records until the remaining balance reaches zero; the received portion still contributes to collected revenue, while the outstanding amount stays visible beside the status.",
            "What should the CedarLedger team remember about Partial customer payments remain open records until the remaining balance reaches zero in the reconciliation area?",
        ),
    },
    "dev-workspace-01-029": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which reconciliation memory covers a bug where deleting supporting proof for an expense did not reopen the related transaction for closeout review; the monthly validation state stayed incorrectly marked complete?",
            "Find the CedarLedger note about bug where deleting supporting proof for an expense did not reopen the related transaction for closeout review; the monthly validation state stayed incorrectly marked complete.",
            "What should the CedarLedger team remember about bug where deleting supporting proof for an expense did not reopen the related transaction for closeout review in the reconciliation area?",
        ),
    },
    "dev-workspace-01-030": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "In CedarLedger, which reconciliation memory covers Before monthly approval, every imported record should be cleared, excluded with a reason, or carried forward for later review; the approval button remains disabled until that checklist is complete?",
            "Find the CedarLedger note about Before monthly approval, every imported record should be cleared, excluded with a reason, or carried forward for later review; the approval button remains disabled until that checklist is complete.",
            "What should the CedarLedger team remember about Before monthly approval, every imported record should be cleared, excluded with a reason, or carried forward for later review in the reconciliation area?",
        ),
    },
    "dev-workspace-02-001": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which form-builder memory covers the product lets editors compose pages with short text, paragraphs, numbers, dates, photos, signatures, locations, and single-choice prompts from the builder palette?",
            "Find the Northstar Forms note about lets editors compose pages with short text, paragraphs, numbers, dates, photos, signatures, locations, and single-choice prompts from the builder palette.",
            "What should the Northstar Forms team remember about lets editors compose pages with short text, paragraphs, numbers, dates, photos, signatures, locations, and single-choice prompts from the builder palette in the form-builder area?",
        ),
    },
    "dev-workspace-02-002": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which form-builder memory covers the form schema keeps immutable field IDs so saved submissions survive label changes; editors see friendly labels while internal identifiers remain hidden?",
            "Find the Northstar Forms note about form schema keeps immutable field IDs so saved submissions survive label changes; editors see friendly labels while internal identifiers remain hidden.",
            "What should the Northstar Forms team remember about form schema keeps immutable field IDs so saved submissions survive label changes; editors see friendly labels while internal identifiers remain hidden in the form-builder area?",
        ),
    },
    "dev-workspace-02-003": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which form-builder memory covers Conditional display rules should appear beside the prompt they affect instead of being buried on a separate settings page?",
            "Find the Northstar Forms note about Conditional display rules should appear beside the prompt they affect instead of being buried on a separate settings page.",
            "What should the Northstar Forms team remember about Conditional display rules should appear beside the prompt they affect instead of being buried on a separate settings page in the form-builder area?",
        ),
    },
    "dev-workspace-02-004": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which form-builder memory covers Template editing supports cloning an input with its help copy, constraints, and visibility behavior intact?",
            "Find the Northstar Forms note about Template editing supports cloning an input with its help copy, constraints, and visibility behavior intact.",
            "What should the Northstar Forms team remember about Template editing supports cloning an input with its help copy, constraints, and visibility behavior intact in the form-builder area?",
        ),
    },
    "dev-workspace-02-005": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which form-builder memory covers Repeatable sections support equipment inspections where a crew records several assets during one site visit; each repeated item keeps its own completion state; the preview should make repeated boundaries visually obvious?",
            "Find the Northstar Forms note about Repeatable sections support equipment inspections where a crew records several assets during one site visit; each repeated item keeps its own completion state; the preview should make repeated boundaries visually obvious.",
            "What should the Northstar Forms team remember about Repeatable sections support equipment inspections where a crew records several assets during one site visit in the form-builder area?",
        ),
    },
    "dev-workspace-02-006": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which form-builder memory covers the authoring UI needs a warning when a mandatory item sits inside a conditional area that might never appear. Place the warning in the settings panel for that item. Editors should be able to jump from the warning to the controlling prompt?",
            "Find the Northstar Forms note about authoring UI needs a warning when a mandatory item sits inside a conditional area that might never appear. Place the warning in the settings panel for that item. Editors should be able to jump from the warning to the controlling prompt.",
            "What should the Northstar Forms team remember about authoring UI needs a warning when a mandatory item sits inside a conditional area that might never appear in the form-builder area?",
        ),
    },
    "dev-workspace-02-007": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which form-builder memory covers a bug where removing the controlling question for conditional display left an orphan rule in the internal definition; the preview then rendered an empty card. Cleanup should run before the updated design is saved?",
            "Find the Northstar Forms note about bug where removing the controlling question for conditional display left an orphan rule in the internal definition; the preview then rendered an empty card. Cleanup should run before the updated design is saved.",
            "What should the Northstar Forms team remember about bug where removing the controlling question for conditional display left an orphan rule in the internal definition in the form-builder area?",
        ),
    },
    "dev-workspace-02-008": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which form-builder memory covers the product saves editing sessions on the device first, so layout changes made in poor connectivity remain available before publishing; the editor should show a local-saved state after every change. Publishing can wait until the connection is stable?",
            "Find the Northstar Forms note about saves editing sessions on the device first, so layout changes made in poor connectivity remain available before publishing; the editor should show a local-saved state after every change. Publishing can wait until the connection is stable.",
            "What should the Northstar Forms team remember about saves editing sessions on the device first, so layout changes made in poor connectivity remain available before publishing in the form-builder area?",
        ),
    },
    "dev-workspace-02-009": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which form-builder memory covers the technical preview should display repeatable section boundaries, nested order, and branching paths. Developers can compare the generated structure with the runtime renderer before a design ships; this catches ordering mismatches before crews use the page?",
            "Find the Northstar Forms note about technical preview should display repeatable section boundaries, nested order, and branching paths. Developers can compare the generated structure with the runtime renderer before a design ships; this catches ordering mismatches before crews use the page.",
            "What should the Northstar Forms team remember about technical preview should display repeatable section boundaries, nested order, and branching paths in the form-builder area?",
        ),
    },
    "dev-workspace-02-010": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which form-builder memory covers Numeric entries need minimum, maximum, unit label, and decimal precision controls. Photo prompts need image-count limits and caption settings. Keep those options close to the type selector?",
            "Find the Northstar Forms note about Numeric entries need minimum, maximum, unit label, and decimal precision controls. Photo prompts need image-count limits and caption settings. Keep those options close to the type selector.",
            "What should the Northstar Forms team remember about Numeric entries need minimum, maximum, unit label, and decimal precision controls in the form-builder area?",
        ),
    },
    "dev-workspace-02-011": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which offline-sync memory covers the product keeps offline drafts on the device until the crew lead explicitly submits or deletes them?",
            "Find the Northstar Forms note about keeps offline drafts on the device until the crew lead explicitly submits or deletes them.",
            "What should the Northstar Forms team remember about keeps offline drafts on the device until the crew lead explicitly submits or deletes them in the offline-sync area?",
        ),
    },
    "dev-workspace-02-012": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which offline-sync memory covers Queued submissions preserve their original completion time and receive a separate synced-at timestamp after server acceptance. Receipt ordering should use completion time rather than upload time. Supervisors need the field chronology, not the network chronology?",
            "Find the Northstar Forms note about Queued submissions preserve their original completion time and receive a separate synced-at timestamp after server acceptance. Receipt ordering should use completion time rather than upload time. Supervisors need the field chronology, not the network chronology.",
            "What should the Northstar Forms team remember about Queued submissions preserve their original completion time and receive a separate synced-at timestamp after server acceptance in the offline-sync area?",
        ),
    },
    "dev-workspace-02-013": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which offline-sync memory covers A sync receipt includes the form name, local draft ID, submission ID, and the time the server acknowledged the upload?",
            "Find the Northstar Forms note about A sync receipt includes the form name, local draft ID, submission ID, and the time the server acknowledged the upload.",
            "What should the Northstar Forms team remember about A sync receipt includes the form name, local draft ID, submission ID, and the time the server acknowledged the upload in the offline-sync area?",
        ),
    },
    "dev-workspace-02-014": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which offline-sync memory covers When connection returns, the app sends saved work oldest first and keeps moving through the backlog even if one item hits a rule conflict?",
            "Find the Northstar Forms note about When connection returns, the app sends saved work oldest first and keeps moving through the backlog even if one item hits a rule conflict.",
            "What should the Northstar Forms team remember about When connection returns, the app sends saved work oldest first and keeps moving through the backlog even if one item hits a rule conflict in the offline-sync area?",
        ),
    },
    "dev-workspace-02-015": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which offline-sync memory covers Field crews need an emergency package for work still stored on a tablet; this lets a damaged device hand off entries before the next shift starts?",
            "Find the Northstar Forms note about Field crews need an emergency package for work still stored on a tablet; this lets a damaged device hand off entries before the next shift starts.",
            "What should the Northstar Forms team remember about Field crews need an emergency package for work still stored on a tablet in the offline-sync area?",
        ),
    },
    "dev-workspace-02-016": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which offline-sync memory covers a bug where editing a locally stored form after it entered the outbound line could overwrite the payload waiting to sync; the confirmation then described a different version than the one sent?",
            "Find the Northstar Forms note about bug where editing a locally stored form after it entered the outbound line could overwrite the payload waiting to sync; the confirmation then described a different version than the one sent.",
            "What should the Northstar Forms team remember about bug where editing a locally stored form after it entered the outbound line could overwrite the payload waiting to sync in the offline-sync area?",
        ),
    },
    "dev-workspace-02-017": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which offline-sync memory covers the product should show a clear saved-on-this-device indicator after every autosave. That matters most on long inspections where signal may drop between sections?",
            "Find the Northstar Forms note about should show a clear saved-on-this-device indicator after every autosave. That matters most on long inspections where signal may drop between sections.",
            "What should the Northstar Forms team remember about should show a clear saved-on-this-device indicator after every autosave in the offline-sync area?",
        ),
    },
    "dev-workspace-02-018": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which offline-sync memory covers the reconnect banner should distinguish between nothing pending, items being transmitted, completed transfer with confirmations, and conflicts needing attention; each state needs different action text?",
            "Find the Northstar Forms note about reconnect banner should distinguish between nothing pending, items being transmitted, completed transfer with confirmations, and conflicts needing attention; each state needs different action text.",
            "What should the Northstar Forms team remember about reconnect banner should distinguish between nothing pending, items being transmitted, completed transfer with confirmations, and conflicts needing attention in the offline-sync area?",
        ),
    },
    "dev-workspace-02-019": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which offline-sync memory covers Configuration notes say local draft retention is set per workspace, while confirmation retention follows the audit log policy for submitted forms; the settings screen should show both values together?",
            "Find the Northstar Forms note about Configuration notes say local draft retention is set per workspace, while confirmation retention follows the audit log policy for submitted forms; the settings screen should show both values together.",
            "What should the Northstar Forms team remember about Configuration notes say local draft retention is set per workspace, while confirmation retention follows the audit log policy for submitted forms in the offline-sync area?",
        ),
    },
    "dev-workspace-02-020": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which offline-sync memory covers the next resilience test should cover airplane-mode creation, recovery after app restart, handoff when service returns, confirmation display, and spreadsheet output for any item still blocked. Accepted items should be the only ones marked complete?",
            "Find the Northstar Forms note about next resilience test should cover airplane-mode creation, recovery after app restart, handoff when service returns, confirmation display, and spreadsheet output for any item still blocked. Accepted items should be the only ones marked complete.",
            "What should the Northstar Forms team remember about next resilience test should cover airplane-mode creation, recovery after app restart, handoff when service returns, confirmation display, and spreadsheet output for any item still blocked in the offline-sync area?",
        ),
    },
    "dev-workspace-02-021": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which review memory covers the product blocks final submission when a required answer is missing. Drafts may stay incomplete if the missing fields are clearly marked before approval; the review banner should explain that saving and submitting are separate actions?",
            "Find the Northstar Forms note about blocks final submission when a required answer is missing. Drafts may stay incomplete if the missing fields are clearly marked before approval; the review banner should explain that saving and submitting are separate actions.",
            "What should the Northstar Forms team remember about blocks final submission when a required answer is missing in the review area?",
        ),
    },
    "dev-workspace-02-022": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which review memory covers the completion screen needs an error summary that separates blank mandatory responses from format problems?",
            "Find the Northstar Forms note about completion screen needs an error summary that separates blank mandatory responses from format problems.",
            "What should the Northstar Forms team remember about completion screen needs an error summary that separates blank mandatory responses from format problems in the review area?",
        ),
    },
    "dev-workspace-02-023": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which review memory covers Supervisor checks expect every mandatory response to be valid or have an approved waiver note before the form can be marked complete?",
            "Find the Northstar Forms note about Supervisor checks expect every mandatory response to be valid or have an approved waiver note before the form can be marked complete.",
            "What should the Northstar Forms team remember about Supervisor checks expect every mandatory response to be valid or have an approved waiver note before the form can be marked complete in the review area?",
        ),
    },
    "dev-workspace-02-024": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which review memory covers Validation messages should use plain language such as this response is needed before signoff instead of generic system text?",
            "Find the Northstar Forms note about Validation messages should use plain language such as this response is needed before signoff instead of generic system text.",
            "What should the Northstar Forms team remember about Validation messages should use plain language such as this response is needed before signoff instead of generic system text in the review area?",
        ),
    },
    "dev-workspace-02-025": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which review memory covers a bug where required radio questions appeared answered after reopening an offline draft; the stored value was blank, and the review step did not catch it?",
            "Find the Northstar Forms note about bug where required radio questions appeared answered after reopening an offline draft; the stored value was blank, and the review step did not catch it.",
            "What should the Northstar Forms team remember about bug where required radio questions appeared answered after reopening an offline draft in the review area?",
        ),
    },
    "dev-workspace-02-026": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which review memory covers Accessibility notes say the problem summary must receive keyboard focus after a failed completion attempt; each message should link back to the exact blank question?",
            "Find the Northstar Forms note about Accessibility notes say the problem summary must receive keyboard focus after a failed completion attempt; each message should link back to the exact blank question.",
            "What should the Northstar Forms team remember about Accessibility notes say the problem summary must receive keyboard focus after a failed completion attempt in the review area?",
        ),
    },
    "dev-workspace-02-027": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which review memory covers the completion indicator should show separate counts for missing mandatory items, failed rule checks, and supervisor signoff blockers. A single incomplete badge hides too much information?",
            "Find the Northstar Forms note about completion indicator should show separate counts for missing mandatory items, failed rule checks, and supervisor signoff blockers. A single incomplete badge hides too much information.",
            "What should the Northstar Forms team remember about completion indicator should show separate counts for missing mandatory items, failed rule checks, and supervisor signoff blockers in the review area?",
        ),
    },
    "dev-workspace-02-028": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which review memory covers Conditional must-fill questions should appear in the final check list only when their parent condition is active in the current draft. Hidden questions should not block signoff; the screen should mention why a conditional question is skipped?",
            "Find the Northstar Forms note about Conditional must-fill questions should appear in the final check list only when their parent condition is active in the current draft. Hidden questions should not block signoff; the screen should mention why a conditional question is skipped.",
            "What should the Northstar Forms team remember about Conditional must-fill questions should appear in the final check list only when their parent condition is active in the current draft in the review area?",
        ),
    },
    "dev-workspace-02-029": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which review memory covers Screen reader testing found that inline problem messages were announced twice on the final check page; the team planned to keep the summary announcement and reduce repeated inline text?",
            "Find the Northstar Forms note about Screen reader testing found that inline problem messages were announced twice on the final check page; the team planned to keep the summary announcement and reduce repeated inline text.",
            "What should the Northstar Forms team remember about Screen reader testing found that inline problem messages were announced twice on the final check page in the review area?",
        ),
    },
    "dev-workspace-02-030": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "In Northstar Forms, which review memory covers the product needs a final signoff guard that re-runs mandatory-response checks after field data reaches the server. Rules can change while a crew is collecting responses away from service. If a rule changed, the screen should explain what needs another pass?",
            "Find the Northstar Forms note about needs a final signoff guard that re-runs mandatory-response checks after field data reaches the server. Rules can change while a crew is collecting responses away from service. If a rule changed, the screen should explain what needs another pass.",
            "What should the Northstar Forms team remember about needs a final signoff guard that re-runs mandatory-response checks after field data reaches the server in the review area?",
        ),
    },
    "dev-workspace-03-001": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which scheduling memory covers the product groups repair work into visible time blocks so dispatchers can catch crane, welding, and survey overlap on the same pier; the board should make clashes obvious without opening each card?",
            "Find the HarborPilot note about groups repair work into visible time blocks so dispatchers can catch crane, welding, and survey overlap on the same pier; the board should make clashes obvious without opening each card.",
            "What should the HarborPilot team remember about groups repair work into visible time blocks so dispatchers can catch crane, welding, and survey overlap on the same pier in the scheduling area?",
        ),
    },
    "dev-workspace-03-002": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which scheduling memory covers the crew coordination view presents arrival windows as ranges rather than exact clock times, leaving room for tide changes and setup delays. Dispatchers need flexibility without losing the intended order of work?",
            "Find the HarborPilot note about crew coordination view presents arrival windows as ranges rather than exact clock times, leaving room for tide changes and setup delays. Dispatchers need flexibility without losing the intended order of work.",
            "What should the HarborPilot team remember about crew coordination view presents arrival windows as ranges rather than exact clock times, leaving room for tide changes and setup delays in the scheduling area?",
        ),
    },
    "dev-workspace-03-003": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which scheduling memory covers Dispatch board ordering puts urgent hull patches first, routine maintenance second, and low-priority dock hardware fixes after the higher-impact work; the sort rule should remain stable when cards refresh?",
            "Find the HarborPilot note about Dispatch board ordering puts urgent hull patches first, routine maintenance second, and low-priority dock hardware fixes after the higher-impact work; the sort rule should remain stable when cards refresh.",
            "What should the HarborPilot team remember about Dispatch board ordering puts urgent hull patches first, routine maintenance second, and low-priority dock hardware fixes after the higher-impact work in the scheduling area?",
        ),
    },
    "dev-workspace-03-004": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which scheduling memory covers the time-window filter should support work beginning within two hours, tomorrow morning, or the active crew block?",
            "Find the HarborPilot note about time-window filter should support work beginning within two hours, tomorrow morning, or the active crew block.",
            "What should the HarborPilot team remember about time-window filter should support work beginning within two hours, tomorrow morning, or the active crew block in the scheduling area?",
        ),
    },
    "dev-workspace-03-005": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which scheduling memory covers Overnight crews need a distinct swimlane so supervisors can separate carryover repairs from new morning assignments during turnover?",
            "Find the HarborPilot note about Overnight crews need a distinct swimlane so supervisors can separate carryover repairs from new morning assignments during turnover.",
            "What should the HarborPilot team remember about Overnight crews need a distinct swimlane so supervisors can separate carryover repairs from new morning assignments during turnover in the scheduling area?",
        ),
    },
    "dev-workspace-03-006": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which scheduling memory covers a bug where moving a repair card across dispatch columns kept the crew assignment but reset the expected kickoff window; the card jumped back to daybreak; the move action should preserve timing unless the dispatcher edits it directly?",
            "Find the HarborPilot note about bug where moving a repair card across dispatch columns kept the crew assignment but reset the expected kickoff window; the card jumped back to daybreak; the move action should preserve timing unless the dispatcher edits it directly.",
            "What should the HarborPilot team remember about bug where moving a repair card across dispatch columns kept the crew assignment but reset the expected kickoff window in the scheduling area?",
        ),
    },
    "dev-workspace-03-007": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which scheduling memory covers the product configuration lets each harbor zone define standard crew blocks because dry dock work and pier repair work follow different daily rhythms?",
            "Find the HarborPilot note about configuration lets each harbor zone define standard crew blocks because dry dock work and pier repair work follow different daily rhythms.",
            "What should the HarborPilot team remember about configuration lets each harbor zone define standard crew blocks because dry dock work and pier repair work follow different daily rhythms in the scheduling area?",
        ),
    },
    "dev-workspace-03-008": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which scheduling memory covers the timeline should highlight idle gaps between repair jobs so dispatchers can fit in quick surveys or small parts replacement tasks; the gap marker should show available duration. Tiny filler tasks should never displace larger work orders?",
            "Find the HarborPilot note about timeline should highlight idle gaps between repair jobs so dispatchers can fit in quick surveys or small parts replacement tasks; the gap marker should show available duration. Tiny filler tasks should never displace larger work orders.",
            "What should the HarborPilot team remember about timeline should highlight idle gaps between repair jobs so dispatchers can fit in quick surveys or small parts replacement tasks in the scheduling area?",
        ),
    },
    "dev-workspace-03-009": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which scheduling memory covers Crew assignment warnings should account for travel and setup when consecutive repairs happen in different harbor zones; the warning belongs beside the second work order. Supervisors should see whether the problem is travel, staging, or both?",
            "Find the HarborPilot note about Crew assignment warnings should account for travel and setup when consecutive repairs happen in different harbor zones; the warning belongs beside the second work order. Supervisors should see whether the problem is travel, staging, or both.",
            "What should the HarborPilot team remember about Crew assignment warnings should account for travel and setup when consecutive repairs happen in different harbor zones in the scheduling area?",
        ),
    },
    "dev-workspace-03-010": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which scheduling memory covers Exports for HarborPilot dispatch views include job code, board column, required gear, crew label, and target arrival window. They must omit customer names, addresses, and phone numbers; the output stays useful for local testing and screenshots?",
            "Find the HarborPilot note about Exports for HarborPilot dispatch views include job code, board column, required gear, crew label, and target arrival window. They must omit customer names, addresses, and phone numbers; the output stays useful for local testing and screenshots.",
            "What should the HarborPilot team remember about Exports for HarborPilot dispatch views include job code, board column, required gear, crew label, and target arrival window in the scheduling area?",
        ),
    },
    "dev-workspace-03-011": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which equipment memory covers the product treats the west yard shared hoist as single-capacity after two pier crews attempted overlapping morning haul-outs?",
            "Find the HarborPilot note about treats the west yard shared hoist as single-capacity after two pier crews attempted overlapping morning haul-outs.",
            "What should the HarborPilot team remember about treats the west yard shared hoist as single-capacity after two pier crews attempted overlapping morning haul-outs in the equipment area?",
        ),
    },
    "dev-workspace-03-012": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which equipment memory covers the pneumatic trailer is offline every Friday afternoon for filter checks, so work suggestions should avoid air-tool jobs during that maintenance window?",
            "Find the HarborPilot note about pneumatic trailer is offline every Friday afternoon for filter checks, so work suggestions should avoid air-tool jobs during that maintenance window.",
            "What should the HarborPilot team remember about pneumatic trailer is offline every Friday afternoon for filter checks, so work suggestions should avoid air-tool jobs during that maintenance window in the equipment area?",
        ),
    },
    "dev-workspace-03-013": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which equipment memory covers Diagnostic handhelds often remain checked out after vessel-side surveys, leaving stale availability for the next repair crew. HarborPilot should request return confirmation before related notes are closed; the warning should name the last job that used the device?",
            "Find the HarborPilot note about Diagnostic handhelds often remain checked out after vessel-side surveys, leaving stale availability for the next repair crew. HarborPilot should request return confirmation before related notes are closed; the warning should name the last job that used the device.",
            "What should the HarborPilot team remember about Diagnostic handhelds often remain checked out after vessel-side surveys, leaving stale availability for the next repair crew in the equipment area?",
        ),
    },
    "dev-workspace-03-014": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which equipment memory covers the product surfaces tool conflicts before crew conflicts when a job depends on shared heavy gear or diagnostic devices; the board should explain that work cannot begin until the needed item is secured. Crew availability is secondary when the gear is unavailable?",
            "Find the HarborPilot note about surfaces tool conflicts before crew conflicts when a job depends on shared heavy gear or diagnostic devices; the board should explain that work cannot begin until the needed item is secured. Crew availability is secondary when the gear is unavailable.",
            "What should the HarborPilot team remember about surfaces tool conflicts before crew conflicts when a job depends on shared heavy gear or diagnostic devices in the equipment area?",
        ),
    },
    "dev-workspace-03-015": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which equipment memory covers the north basin hoist booking includes setup and teardown buffers. Back-to-back assignments should not assume instant movement between repair bays; the calendar should display those buffers as occupied time?",
            "Find the HarborPilot note about north basin hoist booking includes setup and teardown buffers. Back-to-back assignments should not assume instant movement between repair bays; the calendar should display those buffers as occupied time.",
            "What should the HarborPilot team remember about north basin hoist booking includes setup and teardown buffers in the equipment area?",
        ),
    },
    "dev-workspace-03-016": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which equipment memory covers a bug where the air trailer calendar let one crew shorten a booking while another crew still depended on the original time range?",
            "Find the HarborPilot note about bug where the air trailer calendar let one crew shorten a booking while another crew still depended on the original time range.",
            "What should the HarborPilot team remember about bug where the air trailer calendar let one crew shorten a booking while another crew still depended on the original time range in the equipment area?",
        ),
    },
    "dev-workspace-03-017": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which equipment memory covers An unavailable-item reason field should include maintenance, relocation, safety hold, and battery charging. Dispatchers need to know why a tool cannot be assigned; the reason should appear in suggestions, not just on the detail page?",
            "Find the HarborPilot note about An unavailable-item reason field should include maintenance, relocation, safety hold, and battery charging. Dispatchers need to know why a tool cannot be assigned; the reason should appear in suggestions, not just on the detail page.",
            "What should the HarborPilot team remember about An unavailable-item reason field should include maintenance, relocation, safety hold, and battery charging in the equipment area?",
        ),
    },
    "dev-workspace-03-018": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which equipment memory covers the product needs a reminder when diagnostic handhelds have not transmitted field notes before returning to the shared pool. Supervisors can dismiss it only after confirming transfer status; this prevents another crew from taking a device with unfinished records?",
            "Find the HarborPilot note about needs a reminder when diagnostic handhelds have not transmitted field notes before returning to the shared pool. Supervisors can dismiss it only after confirming transfer status; this prevents another crew from taking a device with unfinished records.",
            "What should the HarborPilot team remember about needs a reminder when diagnostic handhelds have not transmitted field notes before returning to the shared pool in the equipment area?",
        ),
    },
    "dev-workspace-03-019": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which equipment memory covers Portable air units should be grouped by pressure rating rather than name alone. Some hull repair tasks can use any unit above the required output, so the picker should show compatible alternatives. Names alone hide workable substitutes?",
            "Find the HarborPilot note about Portable air units should be grouped by pressure rating rather than name alone. Some hull repair tasks can use any unit above the required output, so the picker should show compatible alternatives. Names alone hide workable substitutes.",
            "What should the HarborPilot team remember about Portable air units should be grouped by pressure rating rather than name alone in the equipment area?",
        ),
    },
    "dev-workspace-03-020": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which equipment memory covers Bookings for shared heavy gear should reserve transit time when a hoist moves from the dry dock apron to the inner harbor service corridor. Dispatchers need that unavailable interval visible on the gear calendar?",
            "Find the HarborPilot note about Bookings for shared heavy gear should reserve transit time when a hoist moves from the dry dock apron to the inner harbor service corridor. Dispatchers need that unavailable interval visible on the gear calendar.",
            "What should the HarborPilot team remember about Bookings for shared heavy gear should reserve transit time when a hoist moves from the dry dock apron to the inner harbor service corridor in the equipment area?",
        ),
    },
    "dev-workspace-03-021": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which handoff memory covers the evening dispatcher marked Pier 4 fender repair as waiting on a safety release; the relief crew should confirm the hold is lifted before assigning divers?",
            "Find the HarborPilot note about evening dispatcher marked Pier 4 fender repair as waiting on a safety release; the relief crew should confirm the hold is lifted before assigning divers.",
            "What should the HarborPilot team remember about evening dispatcher marked Pier 4 fender repair as waiting on a safety release in the handoff area?",
        ),
    },
    "dev-workspace-03-022": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which handoff memory covers the product handoff notes show whether each job is ready, blocked, or waiting on inspection so incoming coordinators avoid calling crews for work that cannot start?",
            "Find the HarborPilot note about handoff notes show whether each job is ready, blocked, or waiting on inspection so incoming coordinators avoid calling crews for work that cannot start.",
            "What should the HarborPilot team remember about handoff notes show whether each job is ready, blocked, or waiting on inspection so incoming coordinators avoid calling crews for work that cannot start in the handoff area?",
        ),
    },
    "dev-workspace-03-023": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which handoff memory covers the north basin bollard replacement checklist requires crane availability, tide confirmation, and safety barrier placement before coordinators can clear the job for dispatch?",
            "Find the HarborPilot note about north basin bollard replacement checklist requires crane availability, tide confirmation, and safety barrier placement before coordinators can clear the job for dispatch.",
            "What should the HarborPilot team remember about north basin bollard replacement checklist requires crane availability, tide confirmation, and safety barrier placement before coordinators can clear the job for dispatch in the handoff area?",
        ),
    },
    "dev-workspace-03-024": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which handoff memory covers Blocked jobs stay at the top of the handoff board until the blocker category and responsible role are recorded?",
            "Find the HarborPilot note about Blocked jobs stay at the top of the handoff board until the blocker category and responsible role are recorded.",
            "What should the HarborPilot team remember about Blocked jobs stay at the top of the handoff board until the blocker category and responsible role are recorded in the handoff area?",
        ),
    },
    "dev-workspace-03-025": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which handoff memory covers At crew turnover, the outgoing lead summarized three pending repairs: one cleared for dispatch, one waiting on materials, and one paused for signoff?",
            "Find the HarborPilot note about At crew turnover, the outgoing lead summarized three pending repairs: one cleared for dispatch, one waiting on materials, and one paused for signoff.",
            "What should the HarborPilot team remember about At crew turnover, the outgoing lead summarized three pending repairs: one cleared for dispatch, one waiting on materials, and one paused for signoff in the handoff area?",
        ),
    },
    "dev-workspace-03-026": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which handoff memory covers a bug where completed checklist items did not always appear in the turnover summary; the incoming coordinator repeated crew checks unnecessarily?",
            "Find the HarborPilot note about bug where completed checklist items did not always appear in the turnover summary; the incoming coordinator repeated crew checks unnecessarily.",
            "What should the HarborPilot team remember about bug where completed checklist items did not always appear in the turnover summary in the handoff area?",
        ),
    },
    "dev-workspace-03-027": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which handoff memory covers the night crew noted that the fuel dock ladder repair is safe to stage but not safe to begin; the final safety hold has not been removed?",
            "Find the HarborPilot note about night crew noted that the fuel dock ladder repair is safe to stage but not safe to begin; the final safety hold has not been removed.",
            "What should the HarborPilot team remember about night crew noted that the fuel dock ladder repair is safe to stage but not safe to begin in the handoff area?",
        ),
    },
    "dev-workspace-03-028": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which handoff memory covers Coordinator summaries include the most recent crew contact time and unresolved access issues. Routine completed updates should stay hidden by default?",
            "Find the HarborPilot note about Coordinator summaries include the most recent crew contact time and unresolved access issues. Routine completed updates should stay hidden by default.",
            "What should the HarborPilot team remember about Coordinator summaries include the most recent crew contact time and unresolved access issues in the handoff area?",
        ),
    },
    "dev-workspace-03-029": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which handoff memory covers the handoff workflow separates missing permits, incomplete checklists, and inspection holds instead of collapsing them into a generic not-ready state; each blocker needs an owner and next action?",
            "Find the HarborPilot note about handoff workflow separates missing permits, incomplete checklists, and inspection holds instead of collapsing them into a generic not-ready state; each blocker needs an owner and next action.",
            "What should the HarborPilot team remember about handoff workflow separates missing permits, incomplete checklists, and inspection holds instead of collapsing them into a generic not-ready state in the handoff area?",
        ),
    },
    "dev-workspace-03-030": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "In HarborPilot, which handoff memory covers A coordinator noticed that jobs cleared before the crew change sometimes lost their assigned team in the morning view. HarborPilot should preserve that assignment across turnover?",
            "Find the HarborPilot note about A coordinator noticed that jobs cleared before the crew change sometimes lost their assigned team in the morning view. HarborPilot should preserve that assignment across turnover.",
            "What should the HarborPilot team remember about A coordinator noticed that jobs cleared before the crew change sometimes lost their assigned team in the morning view in the handoff area?",
        ),
    },
}
