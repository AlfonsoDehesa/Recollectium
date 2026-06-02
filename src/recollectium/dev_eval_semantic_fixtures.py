"""Deterministic semantic paraphrase fixtures for seeded dev eval."""

from __future__ import annotations

# This file stores explicit checked-in paraphrase data. Runtime semantic MRR
# eval imports these strings directly; it does not synthesize queries dynamically.
# Tests enforce three non-empty queries per target plus a maximum copied span
# below ten contiguous tokens from each source memory.

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
            "When giving travel planning advice, what profile note mentions trips, leave, room, wandering, local areas, filling, and bookings?",
            "What does the profile say to prioritize around room, wandering, local areas, filling, and bookings?",
            "What preference connects travel planning with trips, room, local areas, and bookings?",
        ),
    },
    "dev-user-002": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which saved preference would guide a request about choosing, lodging, stays, near, reliable, public transport, and casual?",
            "When tailoring travel planning, what detail matters for stays, near, reliable, public transport, casual, places to eat, and basic supplies?",
            "For a recommendation request, what saved detail covers choosing, stays, reliable, casual, basic supplies, and supplies?",
        ),
    },
    "dev-user-003": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the profile say to prioritize around compares, rail, route options, flight hub, transfers, walkable, and distances?",
            "What preference connects travel planning with route options, flight hub, transfers, walkable, distances, deciding, and stay?",
            "When giving travel planning advice, what profile note mentions compares, route options, transfers, distances, and stay?",
        ),
    },
    "dev-user-004": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When tailoring travel planning, what detail matters for travel, buffer, time, cafe stop, boarding area, avoid, and rushing?",
            "For a recommendation request, what saved detail covers time, cafe stop, boarding area, avoid, and rushing?",
            "Which saved preference would guide a request about travel, time, boarding area, and rushing?",
        ),
    },
    "dev-user-005": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What preference connects travel planning with visiting, market stops, early, trip, feel, neighborhood, and pick?",
            "When giving travel planning advice, what profile note mentions early, trip, feel, neighborhood, pick, snacks, and later?",
            "What does the profile say to prioritize around visiting, early, feel, pick, and later?",
        ),
    },
    "dev-user-006": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "For a recommendation request, what saved detail covers packing, minimal, packing list, city, trips, quick, and washing?",
            "Which saved preference would guide a request about packing list, city, trips, quick, washing, load, and check?",
            "When tailoring travel planning, what detail matters for packing, packing list, trips, washing, check, and bag?",
        ),
    },
    "dev-user-007": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When giving travel planning advice, what profile note mentions destination, attractions, advance, passes, knowing, sights, and wet-weather?",
            "What does the profile say to prioritize around advance, passes, knowing, sights, and wet-weather?",
            "What preference connects travel planning with destination, advance, knowing, and wet-weather?",
        ),
    },
    "dev-user-008": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which saved preference would guide a request about plan, anchor, main plan, travel, rest, flexible, and museum?",
            "When tailoring travel planning, what detail matters for main plan, travel, rest, flexible, museum, hike, and food?",
            "For a recommendation request, what saved detail covers plan, main plan, rest, museum, food, and structure?",
        ),
    },
    "dev-user-009": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the profile say to prioritize around trying, regional, morning meals, neighborhood, cafe choices, traveling, and save?",
            "What preference connects travel planning with morning meals, neighborhood, cafe choices, traveling, save, fancier, and meals?",
            "When giving travel planning advice, what profile note mentions trying, morning meals, cafe choices, save, meals, and dinner?",
        ),
    },
    "dev-user-010": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When tailoring travel planning, what detail matters for fallback, list, indoor, activities, quiet, parks, and casual?",
            "For a recommendation request, what saved detail covers indoor, activities, quiet, parks, casual, places to eat, and trip?",
            "Which saved preference would guide a request about fallback, indoor, quiet, casual, trip, and change?",
        ),
    },
    "dev-user-011": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "For a recommendation request, what saved detail covers taking, trains, flights, total, travel, time, and comparable?",
            "Which saved preference would guide a request about flights, total, travel, time, and comparable?",
            "When tailoring getting around, what detail matters for taking, flights, travel, and comparable?",
        ),
    },
    "dev-user-012": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When giving getting around advice, what profile note mentions generally, chooses, route options, fewer, transfers, even, and simpler?",
            "What does the profile say to prioritize around route options, fewer, transfers, even, simpler, route, and takes?",
            "What preference connects getting around with generally, route options, transfers, simpler, takes, and minutes?",
        ),
    },
    "dev-user-013": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which saved preference would guide a request about check, traffic, leaving, appointments, station, pickups, and flight hub?",
            "When tailoring getting around, what detail matters for leaving, appointments, station, pickups, flight hub, and trips?",
            "For a recommendation request, what saved detail covers check, leaving, station, and flight hub?",
        ),
    },
    "dev-user-014": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the profile say to prioritize around bike-share, scooter, options, city, trips, protected, and lanes?",
            "What preference connects getting around with options, city, trips, protected, lanes, car storage, and rules?",
            "When giving getting around advice, what profile note mentions bike-share, options, trips, lanes, and rules?",
        ),
    },
    "dev-user-015": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When tailoring getting around, what detail matters for route, suggestions, compare, driving, public transport, walkable, and those?",
            "For a recommendation request, what saved detail covers compare, driving, public transport, walkable, those, options, and appreciate?",
            "Which saved preference would guide a request about route, compare, public transport, those, appreciate, and tradeoff?",
        ),
    },
    "dev-user-016": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What preference connects getting around with check, car storage, availability, cost, driving, busy, and neighborhood?",
            "When giving getting around advice, what profile note mentions availability, cost, driving, busy, neighborhood, know, and garages?",
            "What does the profile say to prioritize around check, availability, driving, neighborhood, garages, and permit?",
        ),
    },
    "dev-user-017": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "For a recommendation request, what saved detail covers reliable, transportation, plans, absolute, cheapest, option, and willing?",
            "Which saved preference would guide a request about plans, absolute, cheapest, option, willing, pay, and little?",
            "When tailoring getting around, what detail matters for reliable, plans, cheapest, willing, little, and missed?",
        ),
    },
    "dev-user-018": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When giving getting around advice, what profile note mentions ride hail, services, fallback, plan, especially, late, and night?",
            "What does the profile say to prioritize around fallback, plan, especially, late, night, weather, and not?",
            "What preference connects getting around with ride hail, fallback, especially, night, not, and trip?",
        ),
    },
    "dev-user-019": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which saved preference would guide a request about walkable, city, trips, sidewalks, feel, safe, and weather?",
            "When tailoring getting around, what detail matters for trips, sidewalks, feel, safe, weather, reasonable, and enjoy?",
            "For a recommendation request, what saved detail covers walkable, trips, feel, weather, enjoy, and pass?",
        ),
    },
    "dev-user-020": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the profile say to prioritize around arriving, early, trains, buses, flights, not, and feel?",
            "What preference connects getting around with trains, buses, flights, not, feel, rushed, and having?",
            "When giving getting around advice, what profile note mentions arriving, trains, flights, feel, having, and ticket?",
        ),
    },
    "dev-user-021": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What preference connects game recommendations with story-driven, games, strong, atmosphere, memorable, and characters?",
            "When giving game recommendations advice, what profile note mentions strong, atmosphere, memorable, and characters?",
            "What does the profile say to prioritize around story-driven, strong, and memorable?",
        ),
    },
    "dev-user-022": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "For a recommendation request, what saved detail covers flexible, difficulty, settings, adjusting, challenge, fit, and mood?",
            "Which saved preference would guide a request about settings, adjusting, challenge, fit, and mood?",
            "When tailoring game recommendations, what detail matters for flexible, settings, challenge, and mood?",
        ),
    },
    "dev-user-023": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When giving game recommendations advice, what profile note mentions puzzle, mechanics, integrated, naturally, game, and world?",
            "What does the profile say to prioritize around integrated, naturally, game, and world?",
            "What preference connects game recommendations with puzzle, integrated, and game?",
        ),
    },
    "dev-user-024": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which saved preference would guide a request about mention, approximate, playtime, whether, game, and sessions?",
            "When tailoring game recommendations, what detail matters for playtime, whether, game, and sessions?",
            "For a recommendation request, what saved detail covers mention, playtime, and game?",
        ),
    },
    "dev-user-025": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the profile say to prioritize around open-world, games, exploration, feels, rewarding, checklist-driven, and appreciate?",
            "What preference connects game recommendations with exploration, feels, rewarding, checklist-driven, appreciate, maps, and leave?",
            "When giving game recommendations advice, what profile note mentions open-world, exploration, rewarding, appreciate, leave, and curiosity?",
        ),
    },
    "dev-user-026": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When tailoring game recommendations, what detail matters for avoid, online play, games, require, frequent, microphone, and chat?",
            "For a recommendation request, what saved detail covers games, require, frequent, microphone, chat, strangers, and cooperative?",
            "Which saved preference would guide a request about avoid, games, frequent, chat, cooperative, and played?",
        ),
    },
    "dev-user-027": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What preference connects game recommendations with cozy, low-pressure, games, way, unwind, work, and gentle?",
            "When giving game recommendations advice, what profile note mentions games, way, unwind, work, gentle, goals, and pleasant?",
            "What does the profile say to prioritize around cozy, games, unwind, gentle, pleasant, and systems?",
        ),
    },
    "dev-user-028": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "For a recommendation request, what saved detail covers games, save, systems, dislikes, losing, progress, and unclear?",
            "Which saved preference would guide a request about systems, dislikes, losing, progress, unclear, save points, and check?",
            "When tailoring game recommendations, what detail matters for games, systems, losing, unclear, check, and starting?",
        ),
    },
    "dev-user-029": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When giving game recommendations advice, what profile note mentions indie, games, distinctive, art, direction, unusual, and mechanics?",
            "What does the profile say to prioritize around distinctive, art, direction, unusual, mechanics, willing, and try?",
            "What preference connects game recommendations with indie, distinctive, direction, mechanics, try, and edge?",
        ),
    },
    "dev-user-030": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which saved preference would guide a request about controller-friendly, games, playing, couch, setup, readable, and text?",
            "When tailoring game recommendations, what detail matters for playing, couch, setup, readable, text, adjustable, and subtitles?",
            "For a recommendation request, what saved detail covers controller-friendly, playing, setup, text, subtitles, and work?",
        ),
    },
    "dev-user-031": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When tailoring reading suggestions, what detail matters for novels, thoughtful, character, development, strong, sense, and place?",
            "For a recommendation request, what saved detail covers character, development, strong, sense, and place?",
            "Which saved preference would guide a request about novels, character, strong, and place?",
        ),
    },
    "dev-user-032": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What preference connects reading suggestions with book, brief, spoiler-free, reason, why, title, and fits?",
            "When giving reading suggestions advice, what profile note mentions spoiler-free, reason, why, title, fits, and interests?",
            "What does the profile say to prioritize around book, spoiler-free, why, and fits?",
        ),
    },
    "dev-user-033": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "For a recommendation request, what saved detail covers nonfiction, explains, complex, topics, clearly, sounding, and textbook?",
            "Which saved preference would guide a request about complex, topics, clearly, sounding, and textbook?",
            "When tailoring reading suggestions, what detail matters for nonfiction, complex, clearly, and textbook?",
        ),
    },
    "dev-user-034": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When giving reading suggestions advice, what profile note mentions concise, chapters, easier, read, and breaks?",
            "What does the profile say to prioritize around easier, read, and breaks?",
            "What preference connects reading suggestions with concise, easier, and breaks?",
        ),
    },
    "dev-user-035": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which saved preference would guide a request about alternates, between, lighter, reads, demanding, books, and avoid?",
            "When tailoring reading suggestions, what detail matters for lighter, reads, demanding, books, avoid, burnout, and having?",
            "For a recommendation request, what saved detail covers alternates, lighter, demanding, avoid, having, and option?",
        ),
    },
    "dev-user-036": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the profile say to prioritize around science, fiction, focuses, human, consequences, technology, and speculative?",
            "What preference connects reading suggestions with focuses, human, consequences, technology, speculative, ideas, and leave?",
            "When giving reading suggestions advice, what profile note mentions science, focuses, consequences, speculative, leave, and believable?",
        ),
    },
    "dev-user-037": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When tailoring reading suggestions, what detail matters for mysteries, play, fair, reader, avoid, overly, and convenient?",
            "For a recommendation request, what saved detail covers fair, reader, avoid, overly, convenient, twists, and clues?",
            "Which saved preference would guide a request about mysteries, fair, avoid, convenient, clues, and visible?",
        ),
    },
    "dev-user-038": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What preference connects reading suggestions with to-read, list, three, five, strong, options, and catalogs?",
            "When giving reading suggestions advice, what profile note mentions three, five, strong, options, catalogs, start, and book?",
            "What does the profile say to prioritize around to-read, three, strong, catalogs, book, and pacing?",
        ),
    },
    "dev-user-039": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "For a recommendation request, what saved detail covers life stories, connect, personal, stories, broader, cultural, and historical?",
            "Which saved preference would guide a request about personal, stories, broader, cultural, historical, context, and reflective?",
            "When tailoring reading suggestions, what detail matters for life stories, personal, broader, historical, reflective, and celebrity?",
        ),
    },
    "dev-user-040": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When giving reading suggestions advice, what profile note mentions reading, bed, avoids, books, too, tense, and late?",
            "What does the profile say to prioritize around avoids, books, too, tense, late, night, and save?",
            "What preference connects reading suggestions with reading, avoids, too, late, save, and heavy?",
        ),
    },
    "dev-user-041": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the profile say to prioritize around weeknight, dinners, minutes, minimal, and cleanup?",
            "What preference connects home cooking with minutes, minimal, and cleanup?",
            "When giving home cooking advice, what profile note mentions weeknight, minutes, and cleanup?",
        ),
    },
    "dev-user-042": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When tailoring home cooking, what detail matters for mediterranean-inspired, meals, vegetables, grains, olive, oil, and proteins?",
            "For a recommendation request, what saved detail covers vegetables, grains, olive, oil, and proteins?",
            "Which saved preference would guide a request about mediterranean-inspired, vegetables, olive, and proteins?",
        ),
    },
    "dev-user-043": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What preference connects home cooking with pantry, staples, pasta, rice, beans, canned, and tomatoes?",
            "When giving home cooking advice, what profile note mentions pasta, rice, beans, canned, tomatoes, basic, and spices?",
            "What does the profile say to prioritize around pantry, pasta, beans, tomatoes, and spices?",
        ),
    },
    "dev-user-044": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "For a recommendation request, what saved detail covers savory, morning meals, sweet, time, and cook?",
            "Which saved preference would guide a request about sweet, time, and cook?",
            "When tailoring home cooking, what detail matters for savory, sweet, and cook?",
        ),
    },
    "dev-user-045": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When giving home cooking advice, what profile note mentions cooking, home, meal instructions, steps, substitutions, offered, and common?",
            "What does the profile say to prioritize around meal instructions, steps, substitutions, offered, common, ingredients, and already?",
            "What preference connects home cooking with cooking, meal instructions, substitutions, common, and already?",
        ),
    },
    "dev-user-046": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which saved preference would guide a request about batch-cooking, soups, stews, grain, bowls, easy, and lunches?",
            "When tailoring home cooking, what detail matters for stews, grain, bowls, easy, lunches, week, and meals?",
            "For a recommendation request, what saved detail covers batch-cooking, stews, bowls, lunches, meals, and well?",
        ),
    },
    "dev-user-047": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the profile say to prioritize around trying, meal instructions, does, not, overly, complicated, and techniques?",
            "What preference connects home cooking with does, not, overly, complicated, techniques, busy, and attempt?",
            "When giving home cooking advice, what profile note mentions trying, does, overly, techniques, attempt, and recipe?",
        ),
    },
    "dev-user-048": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When tailoring home cooking, what detail matters for improving, prep knife, skills, becoming, faster, prep, and work?",
            "For a recommendation request, what saved detail covers skills, becoming, faster, prep, work, guidance, and safe?",
            "Which saved preference would guide a request about improving, skills, faster, work, safe, and position?",
        ),
    },
    "dev-user-049": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What preference connects home cooking with balanced, meals, protein, vegetables, satisfying, carbohydrate, and meal instructions?",
            "When giving home cooking advice, what profile note mentions protein, vegetables, satisfying, carbohydrate, meal instructions, feel, and filling?",
            "What does the profile say to prioritize around balanced, protein, satisfying, meal instructions, filling, and heavy?",
        ),
    },
    "dev-user-050": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "For a recommendation request, what saved detail covers plans, meals, around, what, refrigerator, appreciate, and suggestions?",
            "Which saved preference would guide a request about around, what, refrigerator, appreciate, suggestions, combine, and leftover?",
            "When tailoring home cooking, what detail matters for plans, around, refrigerator, suggestions, leftover, and half-used?",
        ),
    },
    "dev-user-051": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which saved preference would guide a request about fitness, routine, fits, and workweek?",
            "When tailoring fitness planning, what detail matters for fits and workweek?",
            "For a recommendation request, what saved detail covers fitness and fits?",
        ),
    },
    "dev-user-052": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the profile say to prioritize around strength, training, plans, explain, purpose, and movement?",
            "What preference connects fitness planning with plans, explain, purpose, and movement?",
            "When giving fitness planning advice, what profile note mentions strength, plans, and purpose?",
        ),
    },
    "dev-user-053": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When tailoring fitness planning, what detail matters for walks, low-pressure, way, stay, active, and head?",
            "For a recommendation request, what saved detail covers way, stay, active, and head?",
            "Which saved preference would guide a request about walks, way, and active?",
        ),
    },
    "dev-user-054": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What preference connects fitness planning with progress, tracking, focuses, consistency, and perfection?",
            "When giving fitness planning advice, what profile note mentions focuses, consistency, and perfection?",
            "What does the profile say to prioritize around progress, focuses, and perfection?",
        ),
    },
    "dev-user-055": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "For a recommendation request, what saved detail covers workouts, warmup, guidance, follow, plan, few, and minutes?",
            "Which saved preference would guide a request about guidance, follow, plan, few, minutes, feel, and approachable?",
            "When tailoring fitness planning, what detail matters for workouts, guidance, plan, minutes, and approachable?",
        ),
    },
    "dev-user-056": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When giving fitness planning advice, what profile note mentions equipment, options, dumbbells, bands, bodyweight, movements, and not?",
            "What does the profile say to prioritize around dumbbells, bands, bodyweight, movements, not, routine, and depends?",
            "What preference connects fitness planning with equipment, dumbbells, bodyweight, not, depends, and gym?",
        ),
    },
    "dev-user-057": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which saved preference would guide a request about mobility, exercises, shoulders, hips, back, comfort, and routines?",
            "When tailoring fitness planning, what detail matters for shoulders, hips, back, comfort, routines, easier, and stretching?",
            "For a recommendation request, what saved detail covers mobility, shoulders, back, routines, and stretching?",
        ),
    },
    "dev-user-058": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the profile say to prioritize around fitness, respects, rest, avoid, turning, missed, and workout?",
            "What preference connects fitness planning with rest, avoid, turning, missed, workout, failure, and sustainable?",
            "When giving fitness planning advice, what profile note mentions fitness, rest, turning, workout, sustainable, and matters?",
        ),
    },
    "dev-user-059": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When tailoring fitness planning, what detail matters for cardio, options, adjusted, energy, level, brisk, and walk?",
            "For a recommendation request, what saved detail covers adjusted, energy, level, brisk, walk, easy, and bike?",
            "Which saved preference would guide a request about cardio, adjusted, level, walk, bike, and interval?",
        ),
    },
    "dev-user-060": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What preference connects fitness planning with building, strength, chasing, extreme, goals, steady, and improvements?",
            "When giving fitness planning advice, what profile note mentions chasing, extreme, goals, steady, improvements, form, and fewer?",
            "What does the profile say to prioritize around building, chasing, goals, improvements, fewer, and plans?",
        ),
    },
    "dev-user-061": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When giving music discovery advice, what profile note mentions having, different, music queues, focus, errands, workouts, and relaxing?",
            "What does the profile say to prioritize around music queues, focus, errands, workouts, relaxing, and home?",
            "What preference connects music discovery with having, music queues, errands, and relaxing?",
        ),
    },
    "dev-user-062": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which saved preference would guide a request about discovering, artists, based, songs, and already?",
            "When tailoring music discovery, what detail matters for based, songs, and already?",
            "For a recommendation request, what saved detail covers discovering, based, and already?",
        ),
    },
    "dev-user-063": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the profile say to prioritize around listens, low-vocal, music, doing, focused, and work?",
            "What preference connects music discovery with music, doing, focused, and work?",
            "When giving music discovery advice, what profile note mentions listens, music, and focused?",
        ),
    },
    "dev-user-064": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When tailoring music discovery, what detail matters for upbeat, music, cleaning, cooking, other, household, and tasks?",
            "For a recommendation request, what saved detail covers cleaning, cooking, other, household, and tasks?",
            "Which saved preference would guide a request about upbeat, cleaning, other, and tasks?",
        ),
    },
    "dev-user-065": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What preference connects music discovery with music, suggestions, explanation, why, might, fit, and mood?",
            "When giving music discovery advice, what profile note mentions explanation, why, might, fit, mood, try, and track?",
            "What does the profile say to prioritize around music, explanation, might, mood, track, and vocals?",
        ),
    },
    "dev-user-066": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "For a recommendation request, what saved detail covers both, older, classics, newer, releases, exploring, and genre?",
            "Which saved preference would guide a request about classics, newer, releases, exploring, genre, hearing, and how?",
            "When tailoring music discovery, what detail matters for both, classics, releases, genre, how, and connect?",
        ),
    },
    "dev-user-067": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When giving music discovery advice, what profile note mentions music queues, consistent, mood, jumping, sharply, between, and styles?",
            "What does the profile say to prioritize around mood, jumping, sharply, between, styles, smooth, and transitions?",
            "What preference connects music discovery with music queues, mood, sharply, styles, transitions, and strict?",
        ),
    },
    "dev-user-068": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which saved preference would guide a request about acoustic, mellow, music, evening, avoid, aggressive, and drums?",
            "When tailoring music discovery, what detail matters for music, evening, avoid, aggressive, drums, very, and bright?",
            "For a recommendation request, what saved detail covers acoustic, music, avoid, drums, bright, and late?",
        ),
    },
    "dev-user-069": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the profile say to prioritize around music, different, countries, languages, vibe, matches, and not?",
            "What preference connects music discovery with countries, languages, vibe, matches, not, understand, and lyric?",
            "When giving music discovery advice, what profile note mentions music, countries, vibe, not, lyric, and song?",
        ),
    },
    "dev-user-070": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When tailoring music discovery, what detail matters for learning, bits, context, album, artist, genre, and few?",
            "For a recommendation request, what saved detail covers context, album, artist, genre, few, memorable, and history?",
            "Which saved preference would guide a request about learning, context, artist, few, history, and release?",
        ),
    },
    "dev-user-071": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "For a recommendation request, what saved detail covers pet, care, routines, calm, predictable, easy, and maintain?",
            "Which saved preference would guide a request about routines, calm, predictable, easy, and maintain?",
            "When tailoring pet care, what detail matters for pet, routines, predictable, and maintain?",
        ),
    },
    "dev-user-072": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When giving pet care advice, what profile note mentions pet, product, mention, durability, washability, noise, and level?",
            "What does the profile say to prioritize around mention, durability, washability, noise, and level?",
            "What preference connects pet care with pet, mention, washability, and level?",
        ),
    },
    "dev-user-073": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which saved preference would guide a request about homes, spaces, leashes, brushes, treats, cleanup, and supplies?",
            "When tailoring pet care, what detail matters for leashes, brushes, treats, cleanup, and supplies?",
            "For a recommendation request, what saved detail covers homes, leashes, treats, and supplies?",
        ),
    },
    "dev-user-074": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the profile say to prioritize around pet, balances, comfort, activity, safety, being, and overly?",
            "What preference connects pet care with comfort, activity, safety, being, overly, and fussy?",
            "When giving pet care advice, what profile note mentions pet, comfort, safety, and overly?",
        ),
    },
    "dev-user-075": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When tailoring pet care, what detail matters for feeding, reminders, consistent, easier, follow, morning, and evening?",
            "For a recommendation request, what saved detail covers consistent, easier, follow, morning, evening, and save points?",
            "Which saved preference would guide a request about feeding, consistent, follow, and evening?",
        ),
    },
    "dev-user-076": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What preference connects pet care with activity, ideas, puzzle, feeders, rotating, toys, and training?",
            "When giving pet care advice, what profile note mentions puzzle, feeders, rotating, toys, training, games, and activities?",
            "What does the profile say to prioritize around activity, puzzle, rotating, training, and activities?",
        ),
    },
    "dev-user-077": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "For a recommendation request, what saved detail covers pet-friendly, travel, tips, mention, lodging, rules, and quiet?",
            "Which saved preference would guide a request about tips, mention, lodging, rules, quiet, walkable, and route options?",
            "When tailoring pet care, what detail matters for pet-friendly, tips, lodging, quiet, route options, and green?",
        ),
    },
    "dev-user-078": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When giving pet care advice, what profile note mentions pet, areas, tidy, not, sterile, washable, and blanket?",
            "What does the profile say to prioritize around tidy, not, sterile, washable, blanket, toy, and basket?",
            "What preference connects pet care with pet, tidy, sterile, blanket, basket, and access?",
        ),
    },
    "dev-user-079": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which saved preference would guide a request about plants, cleaners, objects, around, pets, items, and checked?",
            "When tailoring pet care, what detail matters for objects, around, pets, items, checked, left, and within?",
            "For a recommendation request, what saved detail covers plants, objects, pets, checked, within, and safety?",
        ),
    },
    "dev-user-080": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the profile say to prioritize around training, approaches, based, patience, practice, sessions, and cues?",
            "What preference connects pet care with based, patience, practice, sessions, cues, rewards, and breaks?",
            "When giving pet care advice, what profile note mentions training, based, practice, cues, breaks, and positive?",
        ),
    },
    "dev-user-081": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What preference connects skill learning with learning, plans, break, skill, concrete, and steps?",
            "When giving skill learning advice, what profile note mentions break, skill, concrete, and steps?",
            "What does the profile say to prioritize around learning, break, and concrete?",
        ),
    },
    "dev-user-082": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "For a recommendation request, what saved detail covers lessons, exercise, and concept?",
            "Which saved preference would guide a request about concept?",
            "When tailoring skill learning, what detail matters for lessons and concept?",
        ),
    },
    "dev-user-083": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When giving skill learning advice, what profile note mentions momentum, lessons, save points, visible, and progress?",
            "What does the profile say to prioritize around save points, visible, and progress?",
            "What preference connects skill learning with momentum, save points, and progress?",
        ),
    },
    "dev-user-084": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which saved preference would guide a request about explanations, start, example, introducing, formal, and terminology?",
            "When tailoring skill learning, what detail matters for example, introducing, formal, and terminology?",
            "For a recommendation request, what saved detail covers explanations, example, and formal?",
        ),
    },
    "dev-user-085": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the profile say to prioritize around taking, words, finishing, lesson, notice, what, and actually?",
            "What preference connects skill learning with finishing, lesson, notice, what, actually, and understood?",
            "When giving skill learning advice, what profile note mentions taking, finishing, notice, and actually?",
        ),
    },
    "dev-user-086": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When tailoring skill learning, what detail matters for learning, projects, produce, something, useful, abstract, and drills?",
            "For a recommendation request, what saved detail covers produce, something, useful, abstract, drills, easier, and tolerate?",
            "Which saved preference would guide a request about learning, produce, useful, drills, tolerate, and outcome?",
        ),
    },
    "dev-user-087": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What preference connects skill learning with review, sessions, revisit, earlier, material, feeling, and punitive?",
            "When giving skill learning advice, what profile note mentions revisit, earlier, material, feeling, punitive, gentle, and repetition?",
            "What does the profile say to prioritize around review, revisit, material, punitive, repetition, and time?",
        ),
    },
    "dev-user-088": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "For a recommendation request, what saved detail covers discouraged, courses, skip, setup, appreciate, instructions, and mention?",
            "Which saved preference would guide a request about skip, setup, appreciate, instructions, mention, prerequisites, and common?",
            "When tailoring skill learning, what detail matters for discouraged, skip, appreciate, mention, common, and how?",
        ),
    },
    "dev-user-089": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When giving skill learning advice, what profile note mentions comparing, two, three, samples, learning, pattern, and seeing?",
            "What does the profile say to prioritize around three, samples, learning, pattern, seeing, idea, and different?",
            "What preference connects skill learning with comparing, three, learning, seeing, different, and generalize?",
        ),
    },
    "dev-user-090": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which saved preference would guide a request about finish, learning, plan, workload, realistic, sessions, and spaced?",
            "When tailoring skill learning, what detail matters for plan, workload, realistic, sessions, spaced, practice, and milestones?",
            "For a recommendation request, what saved detail covers finish, plan, realistic, spaced, milestones, and weekend?",
        ),
    },
    "dev-user-091": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When tailoring home setup, what detail matters for warm, lighting, natural, textures, rooms, feel, and lived-in?",
            "For a recommendation request, what saved detail covers natural, textures, rooms, feel, lived-in, and staged?",
            "Which saved preference would guide a request about warm, natural, rooms, and lived-in?",
        ),
    },
    "dev-user-092": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What preference connects home setup with entryway, storage, shoes, bags, keys, mail, and spreading?",
            "When giving home setup advice, what profile note mentions shoes, bags, keys, mail, spreading, and house?",
            "What does the profile say to prioritize around entryway, shoes, keys, and spreading?",
        ),
    },
    "dev-user-093": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "For a recommendation request, what saved detail covers linen, window fabric, floor textiles, muted, colors, few, and warmer?",
            "Which saved preference would guide a request about floor textiles, muted, colors, few, warmer, and accents?",
            "When tailoring home setup, what detail matters for linen, floor textiles, colors, and warmer?",
        ),
    },
    "dev-user-094": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When giving home setup advice, what profile note mentions arranging, plants, clusters, near, windows, easy, and water?",
            "What does the profile say to prioritize around clusters, near, windows, easy, and water?",
            "What preference connects home setup with arranging, clusters, windows, and water?",
        ),
    },
    "dev-user-095": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "Which saved preference would guide a request about rooms, reading, spot, lamp, side, table, and soft?",
            "When tailoring home setup, what detail matters for spot, lamp, side, table, soft, blanket, and matter?",
            "For a recommendation request, what saved detail covers rooms, spot, side, soft, matter, and extras?",
        ),
    },
    "dev-user-096": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What does the profile say to prioritize around home, offices, desk, surface, visible, place, and clutter?",
            "What preference connects home setup with desk, surface, visible, place, clutter, feels, and stressful?",
            "When giving home setup advice, what profile note mentions home, desk, visible, clutter, stressful, and tray?",
        ),
    },
    "dev-user-097": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When tailoring home setup, what detail matters for kitchens, counter, space, storage, few, attractive, and everyday?",
            "For a recommendation request, what saved detail covers space, storage, few, attractive, everyday, items, and stay?",
            "Which saved preference would guide a request about kitchens, space, few, everyday, stay, and crowded?",
        ),
    },
    "dev-user-098": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "What preference connects home setup with guest, rooms, feel, calm, useful, being, and formal?",
            "When giving home setup advice, what profile note mentions feel, calm, useful, being, formal, lamp, and surface?",
            "What does the profile say to prioritize around guest, feel, useful, formal, surface, and blanket?",
        ),
    },
    "dev-user-099": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "For a recommendation request, what saved detail covers cozy, style, mixes, pale, wood, warm, and brass?",
            "Which saved preference would guide a request about mixes, pale, wood, warm, brass, soft, and greens?",
            "When tailoring home setup, what detail matters for cozy, mixes, wood, brass, greens, and accents?",
        ),
    },
    "dev-user-100": {
        "scope": "user",
        "workspace_uid": None,
        "queries": (
            "When giving home setup advice, what profile note mentions seasonal, decor, doses, wreath, candle, bowl, and fruit?",
            "What does the profile say to prioritize around doses, wreath, candle, bowl, fruit, feels, and changing?",
            "What preference connects home setup with seasonal, doses, candle, fruit, changing, and room?",
        ),
    },
    "dev-workspace-01-001": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Which project note would answer a question about CedarLedger, tiered, permissions, shop, owners, approve, and bank?",
            "For the permissions area, what note mentions permissions, shop, owners, approve, bank, connections, and managers?",
            "Which workspace decision is relevant to CedarLedger, permissions, owners, bank, managers, and reports?",
        ),
    },
    "dev-workspace-01-002": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "When updating CedarLedger, what should engineers remember about payroll, owner, draws, stay, visible, finance, and administrators?",
            "Which technical reminder points to draws, stay, visible, finance, administrators, even, and teammate?",
            "What CedarLedger requirement should guide work on payroll, draws, visible, administrators, teammate, and ordinary?",
        ),
    },
    "dev-workspace-01-003": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Which permissions item tracks bookkeeper, invitations, land, read-only, reviewer, seat, and owner?",
            "What product context should be used for land, read-only, reviewer, seat, owner, deliberately, and grants?",
            "Which project note would answer a question about bookkeeper, land, reviewer, owner, grants, and rights?",
        ),
    },
    "dev-workspace-01-004": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What saved workspace context describes server-side, guards, protect, bill, attachment, month-end, and review?",
            "Which CedarLedger permissions note covers protect, bill, attachment, month-end, review, endpoint, and relying?",
            "When updating CedarLedger, what should engineers remember about server-side, protect, attachment, review, relying, and navigation?",
        ),
    },
    "dev-workspace-01-005": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Which CedarLedger memory helps with cash-drawer, clerks, enter, daily, takings, supplier, and slips?",
            "For CedarLedger, what implementation detail involves enter, daily, takings, supplier, slips, not, and change?",
            "Which permissions item tracks cash-drawer, enter, takings, slips, change, and settings?",
        ),
    },
    "dev-workspace-01-006": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "For the permissions area, what note mentions bug, showed, switching, between, two, workshops, and reused?",
            "Which workspace decision is relevant to switching, between, two, workshops, reused, earlier, and workspace's?",
            "What saved workspace context describes bug, switching, two, reused, workspace's, and capabilities?",
        ),
    },
    "dev-workspace-01-007": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Which technical reminder points to owner, seat, transfer, ownership, re-authentication, audit, and trail?",
            "What CedarLedger requirement should guide work on transfer, ownership, re-authentication, audit, trail, records, and former?",
            "Which CedarLedger memory helps with owner, transfer, re-authentication, trail, former, and timestamp?",
        ),
    },
    "dev-workspace-01-008": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What product context should be used for support, staff, inspect, CedarLedger, diagnostic, metadata, and not?",
            "Which project note would answer a question about inspect, CedarLedger, diagnostic, metadata, not, transaction, and descriptions?",
            "For the permissions area, what note mentions support, inspect, diagnostic, not, descriptions, and previews?",
        ),
    },
    "dev-workspace-01-009": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Which CedarLedger permissions note covers archived, workshops, separate, matrix, rule, members, and read?",
            "When updating CedarLedger, what should engineers remember about separate, matrix, rule, members, read, historical, and ledger?",
            "Which technical reminder points to archived, separate, rule, read, ledger, and owner?",
        ),
    },
    "dev-workspace-01-010": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "For CedarLedger, what implementation detail involves password, change, other, active, sessions, invalidated, and current?",
            "Which permissions item tracks other, active, sessions, invalidated, current, re-authenticated, and session?",
            "What product context should be used for password, other, sessions, current, session, and CedarLedger?",
        ),
    },
    "dev-workspace-01-011": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Which workspace decision is relevant to CedarLedger, provides, csv, json, exports, owners, and inspect?",
            "What saved workspace context describes csv, json, exports, owners, inspect, monthly, and income?",
            "Which CedarLedger exports note covers CedarLedger, csv, exports, inspect, income, and category?",
        ),
    },
    "dev-workspace-01-012": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What CedarLedger requirement should guide work on monthly, report, packages, generated, timestamp, name, and repeated?",
            "Which CedarLedger memory helps with packages, generated, timestamp, name, repeated, pulls, and date?",
            "For CedarLedger, what implementation detail involves monthly, packages, timestamp, repeated, date, and remain?",
        ),
    },
    "dev-workspace-01-013": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Which project note would answer a question about sample, accounting, rows, development, output, rely, and generic?",
            "For the exports area, what note mentions rows, development, output, rely, generic, vendors, and rounded?",
            "Which workspace decision is relevant to sample, rows, output, generic, rounded, and harmless?",
        ),
    },
    "dev-workspace-01-014": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "When updating CedarLedger, what should engineers remember about spreadsheet, output, stable, column, order, date, and entry?",
            "Which technical reminder points to stable, column, order, date, entry, account, and category?",
            "What CedarLedger requirement should guide work on spreadsheet, stable, order, entry, category, and debit?",
        ),
    },
    "dev-workspace-01-015": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Which exports item tracks task, remains, add, restorable, ledger, snapshot, and covering?",
            "What product context should be used for add, restorable, ledger, snapshot, covering, accounts, and categories?",
            "Which project note would answer a question about task, add, ledger, covering, categories, and month-end?",
        ),
    },
    "dev-workspace-01-016": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What saved workspace context describes bug, sorted, april, expenses, description, transaction, and date?",
            "Which CedarLedger exports note covers april, expenses, description, transaction, date, monthly, and spreadsheet?",
            "When updating CedarLedger, what should engineers remember about bug, april, description, date, spreadsheet, and out?",
        ),
    },
    "dev-workspace-01-017": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Which CedarLedger memory helps with packaging, settings, panel, default, generated, artifact, and timestamps?",
            "For CedarLedger, what implementation detail involves panel, default, generated, artifact, timestamps, utc, and report?",
            "Which exports item tracks packaging, panel, generated, timestamps, report, and display?",
        ),
    },
    "dev-workspace-01-018": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "For the exports area, what note mentions CedarLedger, archive, bundles, contain, generic, ledger, and samples?",
            "Which workspace decision is relevant to bundles, contain, generic, ledger, samples, tool, and purchases?",
            "What saved workspace context describes CedarLedger, bundles, generic, samples, purchases, and income?",
        ),
    },
    "dev-workspace-01-019": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Which technical reminder points to structured, state, bundles, restoring, CedarLedger, spreadsheets, and suit?",
            "What CedarLedger requirement should guide work on bundles, restoring, CedarLedger, spreadsheets, suit, reviewers, and who?",
            "Which CedarLedger memory helps with structured, bundles, CedarLedger, suit, who, and transaction?",
        ),
    },
    "dev-workspace-01-020": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What product context should be used for monthly, archive, workflow, write, checksum, manifest, and confirm?",
            "Which project note would answer a question about workflow, write, checksum, manifest, confirm, package, and completed?",
            "For the exports area, what note mentions monthly, workflow, checksum, confirm, completed, and failed?",
        ),
    },
    "dev-workspace-01-021": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Which CedarLedger reconciliation note covers CedarLedger, calculates, collected, outstanding, totals, separately, and closeout?",
            "When updating CedarLedger, what should engineers remember about collected, outstanding, totals, separately, closeout, owners, and compare?",
            "Which technical reminder points to CedarLedger, collected, totals, closeout, compare, and received?",
        ),
    },
    "dev-workspace-01-022": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "For CedarLedger, what implementation detail involves month-end, review, compares, proof, expenses, imported, and records?",
            "Which reconciliation item tracks compares, proof, expenses, imported, records, flags, and vendor?",
            "What product context should be used for month-end, compares, expenses, records, vendor, and supporting?",
        ),
    },
    "dev-workspace-01-023": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Which workspace decision is relevant to customer, bill, marked, settled, payment, date, and method?",
            "What saved workspace context describes marked, settled, payment, date, method, linked, and ledger?",
            "Which CedarLedger reconciliation note covers customer, marked, payment, method, ledger, and appears?",
        ),
    },
    "dev-workspace-01-024": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What CedarLedger requirement should guide work on record, pairing, works, CedarLedger, weighs, amount, and date?",
            "Which CedarLedger memory helps with works, CedarLedger, weighs, amount, date, window, and vendor?",
            "For CedarLedger, what implementation detail involves record, works, weighs, date, vendor, and name?",
        ),
    },
    "dev-workspace-01-025": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Which project note would answer a question about february, review, expense, lines, looked, correct, and two?",
            "For the reconciliation area, what note mentions expense, lines, looked, correct, two, customer, and bills?",
            "Which workspace decision is relevant to february, expense, looked, two, bills, and settled?",
        ),
    },
    "dev-workspace-01-026": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "When updating CedarLedger, what should engineers remember about CedarLedger, explain, why, month-end, totals, differ, and naming?",
            "Which technical reminder points to why, month-end, totals, differ, naming, gaps, and missing?",
            "What CedarLedger requirement should guide work on CedarLedger, why, totals, naming, missing, and proof?",
        ),
    },
    "dev-workspace-01-027": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Which reconciliation item tracks filter, needed, supply, charges, not, been, and cleared?",
            "What product context should be used for supply, charges, not, been, cleared, inspect, and materials?",
            "Which project note would answer a question about filter, supply, not, cleared, materials, and finalizing?",
        ),
    },
    "dev-workspace-01-028": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "What saved workspace context describes partial, customer, payments, remain, records, remaining, and balance?",
            "Which CedarLedger reconciliation note covers payments, remain, records, remaining, balance, reaches, and zero?",
            "When updating CedarLedger, what should engineers remember about partial, payments, records, balance, zero, and portion?",
        ),
    },
    "dev-workspace-01-029": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "Which CedarLedger memory helps with bug, was, found, deleting, supporting, proof, and expense?",
            "For CedarLedger, what implementation detail involves found, deleting, supporting, proof, expense, did, and not?",
            "Which reconciliation item tracks bug, found, supporting, expense, not, and related?",
        ),
    },
    "dev-workspace-01-030": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-cedarledger-01",
        "queries": (
            "For the reconciliation area, what note mentions monthly, approval, imported, record, cleared, excluded, and reason?",
            "Which workspace decision is relevant to imported, record, cleared, excluded, reason, carried, and forward?",
            "What saved workspace context describes monthly, imported, cleared, reason, forward, and review?",
        ),
    },
    "dev-workspace-02-001": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What saved workspace context describes Northstar Forms, forms, lets, editors, compose, pages, and text?",
            "Which Northstar Forms form-builder note covers lets, editors, compose, pages, text, paragraphs, and numbers?",
            "When updating Northstar Forms, what should engineers remember about Northstar Forms, lets, compose, text, numbers, and photos?",
        ),
    },
    "dev-workspace-02-002": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Which Northstar Forms memory helps with form, schema, immutable, field, ids, submissions, and survive?",
            "For Northstar Forms, what implementation detail involves immutable, field, ids, submissions, survive, label, and changes?",
            "Which form-builder item tracks form, immutable, ids, survive, changes, and see?",
        ),
    },
    "dev-workspace-02-003": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "For the form-builder area, what note mentions conditional, display, rules, appear, beside, prompt, and affect?",
            "Which workspace decision is relevant to rules, appear, beside, prompt, affect, being, and buried?",
            "What saved workspace context describes conditional, rules, beside, affect, buried, and settings?",
        ),
    },
    "dev-workspace-02-004": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Which technical reminder points to template, editing, supports, cloning, input, copy, and constraints?",
            "What Northstar Forms requirement should guide work on supports, cloning, input, copy, constraints, visibility, and behavior?",
            "Which Northstar Forms memory helps with template, supports, input, constraints, and behavior?",
        ),
    },
    "dev-workspace-02-005": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What product context should be used for repeatable, sections, support, equipment, inspections, crew, and records?",
            "Which project note would answer a question about support, equipment, inspections, crew, records, several, and assets?",
            "For the form-builder area, what note mentions repeatable, support, inspections, records, assets, and visit?",
        ),
    },
    "dev-workspace-02-006": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Which Northstar Forms form-builder note covers authoring, warning, mandatory, item, sits, inside, and conditional?",
            "When updating Northstar Forms, what should engineers remember about mandatory, item, sits, inside, conditional, area, and might?",
            "Which technical reminder points to authoring, mandatory, sits, conditional, might, and appear?",
        ),
    },
    "dev-workspace-02-007": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "For Northstar Forms, what implementation detail involves bug, was, found, removing, controlling, question, and conditional?",
            "Which form-builder item tracks found, removing, controlling, question, conditional, display, and left?",
            "What product context should be used for bug, found, controlling, conditional, left, and rule?",
        ),
    },
    "dev-workspace-02-008": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Which workspace decision is relevant to Northstar Forms, forms, saves, editing, sessions, device, and layout?",
            "What saved workspace context describes saves, editing, sessions, device, layout, changes, and poor?",
            "Which Northstar Forms form-builder note covers Northstar Forms, saves, sessions, layout, poor, and remain?",
        ),
    },
    "dev-workspace-02-009": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What Northstar Forms requirement should guide work on technical, preview, display, repeatable, section, boundaries, and nested?",
            "Which Northstar Forms memory helps with display, repeatable, section, boundaries, nested, order, and branching?",
            "For Northstar Forms, what implementation detail involves technical, display, section, nested, branching, and developers?",
        ),
    },
    "dev-workspace-02-010": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Which project note would answer a question about numeric, entries, minimum, maximum, unit, label, and decimal?",
            "For the form-builder area, what note mentions minimum, maximum, unit, label, decimal, precision, and controls?",
            "Which workspace decision is relevant to numeric, minimum, unit, decimal, controls, and prompts?",
        ),
    },
    "dev-workspace-02-011": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "When updating Northstar Forms, what should engineers remember about Northstar Forms, forms, offline, drafts, device, crew, and lead?",
            "Which technical reminder points to offline, drafts, device, crew, lead, explicitly, and submits?",
            "What Northstar Forms requirement should guide work on Northstar Forms, offline, device, lead, and submits?",
        ),
    },
    "dev-workspace-02-012": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Which offline-sync item tracks queued, submissions, preserve, original, completion, time, and receive?",
            "What product context should be used for preserve, original, completion, time, receive, separate, and synced-at?",
            "Which project note would answer a question about queued, preserve, completion, receive, synced-at, and server?",
        ),
    },
    "dev-workspace-02-013": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What saved workspace context describes sync, receipt, form, name, draft, submission, and time?",
            "Which Northstar Forms offline-sync note covers form, name, draft, submission, time, server, and acknowledged?",
            "When updating Northstar Forms, what should engineers remember about sync, form, draft, time, and acknowledged?",
        ),
    },
    "dev-workspace-02-014": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Which Northstar Forms memory helps with connection, returns, sends, work, oldest, moving, and backlog?",
            "For Northstar Forms, what implementation detail involves sends, work, oldest, moving, backlog, even, and item?",
            "Which offline-sync item tracks connection, sends, oldest, backlog, item, and rule?",
        ),
    },
    "dev-workspace-02-015": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "For the offline-sync area, what note mentions field, crews, emergency, package, work, stored, and tablet?",
            "Which workspace decision is relevant to emergency, package, work, stored, tablet, lets, and damaged?",
            "What saved workspace context describes field, emergency, work, tablet, damaged, and hand?",
        ),
    },
    "dev-workspace-02-016": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Which technical reminder points to bug, was, found, editing, locally, stored, and form?",
            "What Northstar Forms requirement should guide work on found, editing, locally, stored, form, entered, and outbound?",
            "Which Northstar Forms memory helps with bug, found, locally, form, outbound, and overwrite?",
        ),
    },
    "dev-workspace-02-017": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What product context should be used for Northstar Forms, forms, saved-on-this-device, indicator, autosave, matters, and inspections?",
            "Which project note would answer a question about saved-on-this-device, indicator, autosave, matters, inspections, signal, and drop?",
            "For the offline-sync area, what note mentions Northstar Forms, saved-on-this-device, autosave, inspections, drop, and sections?",
        ),
    },
    "dev-workspace-02-018": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Which Northstar Forms offline-sync note covers reconnect, banner, distinguish, between, nothing, pending, and items?",
            "When updating Northstar Forms, what should engineers remember about distinguish, between, nothing, pending, items, being, and transmitted?",
            "Which technical reminder points to reconnect, distinguish, nothing, items, transmitted, and transfer?",
        ),
    },
    "dev-workspace-02-019": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "For Northstar Forms, what implementation detail involves configuration, say, draft, retention, set, confirmation, and follows?",
            "Which offline-sync item tracks draft, retention, set, confirmation, follows, audit, and log?",
            "What product context should be used for configuration, draft, set, follows, log, and submitted?",
        ),
    },
    "dev-workspace-02-020": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Which workspace decision is relevant to resilience, test, cover, airplane-mode, creation, recovery, and restart?",
            "What saved workspace context describes cover, airplane-mode, creation, recovery, restart, handoff, and service?",
            "Which Northstar Forms offline-sync note covers resilience, cover, creation, restart, service, and confirmation?",
        ),
    },
    "dev-workspace-02-021": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What Northstar Forms requirement should guide work on Northstar Forms, forms, blocks, final, submission, required, and answer?",
            "Which Northstar Forms memory helps with blocks, final, submission, required, answer, missing, and drafts?",
            "For Northstar Forms, what implementation detail involves Northstar Forms, blocks, submission, answer, drafts, and incomplete?",
        ),
    },
    "dev-workspace-02-022": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Which project note would answer a question about completion, error, summary, separates, blank, mandatory, and responses?",
            "For the review area, what note mentions summary, separates, blank, mandatory, responses, format, and problems?",
            "Which workspace decision is relevant to completion, summary, blank, responses, and problems?",
        ),
    },
    "dev-workspace-02-023": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "When updating Northstar Forms, what should engineers remember about supervisor, checks, expect, mandatory, response, valid, and approved?",
            "Which technical reminder points to expect, mandatory, response, valid, approved, waiver, and form?",
            "What Northstar Forms requirement should guide work on supervisor, expect, response, approved, form, and complete?",
        ),
    },
    "dev-workspace-02-024": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Which review item tracks validation, messages, plain, language, response, needed, and signoff?",
            "What product context should be used for plain, language, response, needed, signoff, generic, and system?",
            "Which project note would answer a question about validation, plain, response, signoff, and system?",
        ),
    },
    "dev-workspace-02-025": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What saved workspace context describes bug, was, found, required, radio, questions, and appeared?",
            "Which Northstar Forms review note covers found, required, radio, questions, appeared, answered, and reopening?",
            "When updating Northstar Forms, what should engineers remember about bug, found, radio, appeared, reopening, and draft?",
        ),
    },
    "dev-workspace-02-026": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Which Northstar Forms memory helps with accessibility, say, problem, summary, receive, keyboard, and focus?",
            "For Northstar Forms, what implementation detail involves problem, summary, receive, keyboard, focus, failed, and completion?",
            "Which review item tracks accessibility, problem, receive, focus, completion, and message?",
        ),
    },
    "dev-workspace-02-027": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "For the review area, what note mentions completion, indicator, separate, counts, missing, mandatory, and items?",
            "Which workspace decision is relevant to separate, counts, missing, mandatory, items, failed, and rule?",
            "What saved workspace context describes completion, separate, missing, items, rule, and supervisor?",
        ),
    },
    "dev-workspace-02-028": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Which technical reminder points to conditional, must-fill, questions, appear, final, check, and list?",
            "What Northstar Forms requirement should guide work on questions, appear, final, check, list, parent, and condition?",
            "Which Northstar Forms memory helps with conditional, questions, final, list, condition, and current?",
        ),
    },
    "dev-workspace-02-029": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "What product context should be used for reader, testing, found, inline, problem, messages, and were?",
            "Which project note would answer a question about found, inline, problem, messages, were, announced, and twice?",
            "For the review area, what note mentions reader, found, problem, were, twice, and check?",
        ),
    },
    "dev-workspace-02-030": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-northstar-forms-01",
        "queries": (
            "Which Northstar Forms review note covers Northstar Forms, forms, final, signoff, guard, re-runs, and mandatory-response?",
            "When updating Northstar Forms, what should engineers remember about final, signoff, guard, re-runs, mandatory-response, checks, and field?",
            "Which technical reminder points to Northstar Forms, final, guard, mandatory-response, field, and reaches?",
        ),
    },
    "dev-workspace-03-001": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Which technical reminder points to HarborPilot, groups, repair, work, visible, time, and blocks?",
            "What HarborPilot requirement should guide work on repair, work, visible, time, blocks, dispatchers, and catch?",
            "Which HarborPilot memory helps with HarborPilot, repair, visible, blocks, catch, and welding?",
        ),
    },
    "dev-workspace-03-002": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What product context should be used for crew, coordination, view, presents, arrival, windows, and ranges?",
            "Which project note would answer a question about view, presents, arrival, windows, ranges, exact, and clock?",
            "For the scheduling area, what note mentions crew, view, arrival, ranges, clock, and leaving?",
        ),
    },
    "dev-workspace-03-003": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Which HarborPilot scheduling note covers dispatch, board, ordering, puts, urgent, hull, and patches?",
            "When updating HarborPilot, what should engineers remember about ordering, puts, urgent, hull, patches, routine, and maintenance?",
            "Which technical reminder points to dispatch, ordering, urgent, patches, maintenance, and low-priority?",
        ),
    },
    "dev-workspace-03-004": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "For HarborPilot, what implementation detail involves time-window, filter, support, work, beginning, within, and two?",
            "Which scheduling item tracks support, work, beginning, within, two, hours, and tomorrow?",
            "What product context should be used for time-window, support, beginning, two, tomorrow, and active?",
        ),
    },
    "dev-workspace-03-005": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Which workspace decision is relevant to overnight, crews, distinct, swimlane, supervisors, separate, and carryover?",
            "What saved workspace context describes distinct, swimlane, supervisors, separate, carryover, repairs, and morning?",
            "Which HarborPilot scheduling note covers overnight, distinct, supervisors, carryover, morning, and turnover?",
        ),
    },
    "dev-workspace-03-006": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What HarborPilot requirement should guide work on bug, was, found, moving, repair, card, and across?",
            "Which HarborPilot memory helps with found, moving, repair, card, across, dispatch, and columns?",
            "For HarborPilot, what implementation detail involves bug, found, repair, across, columns, and crew?",
        ),
    },
    "dev-workspace-03-007": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Which project note would answer a question about HarborPilot, configuration, lets, harbor, zone, define, and standard?",
            "For the scheduling area, what note mentions lets, harbor, zone, define, standard, crew, and blocks?",
            "Which workspace decision is relevant to HarborPilot, lets, zone, standard, blocks, and dock?",
        ),
    },
    "dev-workspace-03-008": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "When updating HarborPilot, what should engineers remember about timeline, highlight, idle, gaps, between, repair, and jobs?",
            "Which technical reminder points to idle, gaps, between, repair, jobs, dispatchers, and fit?",
            "What HarborPilot requirement should guide work on timeline, idle, between, jobs, fit, and surveys?",
        ),
    },
    "dev-workspace-03-009": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Which scheduling item tracks crew, assignment, warnings, account, travel, setup, and consecutive?",
            "What product context should be used for warnings, account, travel, setup, consecutive, repairs, and happen?",
            "Which project note would answer a question about crew, warnings, travel, consecutive, happen, and harbor?",
        ),
    },
    "dev-workspace-03-010": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What saved workspace context describes exports, HarborPilot, dispatch, views, job, code, and board?",
            "Which HarborPilot scheduling note covers dispatch, views, job, code, board, column, and required?",
            "When updating HarborPilot, what should engineers remember about exports, dispatch, job, board, required, and crew?",
        ),
    },
    "dev-workspace-03-011": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Which HarborPilot memory helps with HarborPilot, treats, west, yard, shared, hoist, and single-capacity?",
            "For HarborPilot, what implementation detail involves west, yard, shared, hoist, single-capacity, two, and pier?",
            "Which equipment item tracks HarborPilot, west, shared, single-capacity, pier, and attempted?",
        ),
    },
    "dev-workspace-03-012": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "For the equipment area, what note mentions pneumatic, trailer, offline, friday, afternoon, filter, and checks?",
            "Which workspace decision is relevant to offline, friday, afternoon, filter, checks, work, and suggestions?",
            "What saved workspace context describes pneumatic, offline, afternoon, checks, suggestions, and air-tool?",
        ),
    },
    "dev-workspace-03-013": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Which technical reminder points to diagnostic, handhelds, remain, checked, out, vessel-side, and surveys?",
            "What HarborPilot requirement should guide work on remain, checked, out, vessel-side, surveys, leaving, and stale?",
            "Which HarborPilot memory helps with diagnostic, remain, out, surveys, stale, and repair?",
        ),
    },
    "dev-workspace-03-014": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What product context should be used for HarborPilot, surfaces, tool, conflicts, crew, job, and depends?",
            "Which project note would answer a question about tool, conflicts, crew, job, depends, shared, and heavy?",
            "For the equipment area, what note mentions HarborPilot, tool, crew, depends, heavy, and diagnostic?",
        ),
    },
    "dev-workspace-03-015": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Which HarborPilot equipment note covers north, basin, hoist, booking, setup, teardown, and buffers?",
            "When updating HarborPilot, what should engineers remember about hoist, booking, setup, teardown, buffers, back-to-back, and assignments?",
            "Which technical reminder points to north, hoist, setup, buffers, assignments, and assume?",
        ),
    },
    "dev-workspace-03-016": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "For HarborPilot, what implementation detail involves bug, was, found, air, trailer, calendar, and let?",
            "Which equipment item tracks found, air, trailer, calendar, let, crew, and shorten?",
            "What product context should be used for bug, found, trailer, let, shorten, and another?",
        ),
    },
    "dev-workspace-03-017": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Which workspace decision is relevant to unavailable-item, reason, field, maintenance, relocation, safety, and hold?",
            "What saved workspace context describes field, maintenance, relocation, safety, hold, battery, and charging?",
            "Which HarborPilot equipment note covers unavailable-item, field, relocation, hold, charging, and know?",
        ),
    },
    "dev-workspace-03-018": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What HarborPilot requirement should guide work on HarborPilot, reminder, diagnostic, handhelds, not, transmitted, and field?",
            "Which HarborPilot memory helps with diagnostic, handhelds, not, transmitted, field, returning, and shared?",
            "For HarborPilot, what implementation detail involves HarborPilot, diagnostic, not, field, shared, and supervisors?",
        ),
    },
    "dev-workspace-03-019": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Which project note would answer a question about portable, air, units, grouped, pressure, rating, and name?",
            "For the equipment area, what note mentions units, grouped, pressure, rating, name, alone, and some?",
            "Which workspace decision is relevant to portable, units, pressure, name, some, and repair?",
        ),
    },
    "dev-workspace-03-020": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "When updating HarborPilot, what should engineers remember about bookings, shared, heavy, gear, reserve, public transport, and time?",
            "Which technical reminder points to heavy, gear, reserve, public transport, time, hoist, and moves?",
            "What HarborPilot requirement should guide work on bookings, heavy, reserve, time, moves, and dock?",
        ),
    },
    "dev-workspace-03-021": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Which handoff item tracks evening, dispatcher, marked, pier, fender, repair, and waiting?",
            "What product context should be used for marked, pier, fender, repair, waiting, safety, and release?",
            "Which project note would answer a question about evening, marked, fender, waiting, release, and crew?",
        ),
    },
    "dev-workspace-03-022": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What saved workspace context describes HarborPilot, handoff, whether, job, ready, blocked, and waiting?",
            "Which HarborPilot handoff note covers whether, job, ready, blocked, waiting, inspection, and incoming?",
            "When updating HarborPilot, what should engineers remember about HarborPilot, whether, ready, waiting, incoming, and avoid?",
        ),
    },
    "dev-workspace-03-023": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Which HarborPilot memory helps with north, basin, bollard, replacement, checklist, requires, and crane?",
            "For HarborPilot, what implementation detail involves bollard, replacement, checklist, requires, crane, availability, and tide?",
            "Which handoff item tracks north, bollard, checklist, crane, tide, and safety?",
        ),
    },
    "dev-workspace-03-024": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "For the handoff area, what note mentions blocked, jobs, stay, top, handoff, board, and blocker?",
            "Which workspace decision is relevant to stay, top, handoff, board, blocker, category, and responsible?",
            "What saved workspace context describes blocked, stay, handoff, blocker, responsible, and recorded?",
        ),
    },
    "dev-workspace-03-025": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Which technical reminder points to crew, turnover, outgoing, lead, summarized, three, and pending?",
            "What HarborPilot requirement should guide work on outgoing, lead, summarized, three, pending, repairs, and cleared?",
            "Which HarborPilot memory helps with crew, outgoing, summarized, pending, cleared, and waiting?",
        ),
    },
    "dev-workspace-03-026": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What product context should be used for bug, was, found, completed, checklist, items, and did?",
            "Which project note would answer a question about found, completed, checklist, items, did, not, and always?",
            "For the handoff area, what note mentions bug, found, checklist, did, always, and turnover?",
        ),
    },
    "dev-workspace-03-027": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Which HarborPilot handoff note covers night, crew, noted, fuel, dock, ladder, and repair?",
            "When updating HarborPilot, what should engineers remember about noted, fuel, dock, ladder, repair, safe, and stage?",
            "Which technical reminder points to night, noted, dock, repair, stage, and begin?",
        ),
    },
    "dev-workspace-03-028": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "For HarborPilot, what implementation detail involves coordinator, summaries, recent, crew, contact, time, and unresolved?",
            "Which handoff item tracks recent, crew, contact, time, unresolved, access, and issues?",
            "What product context should be used for coordinator, recent, contact, unresolved, issues, and completed?",
        ),
    },
    "dev-workspace-03-029": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "Which workspace decision is relevant to handoff, workflow, separates, missing, permits, incomplete, and checklists?",
            "What saved workspace context describes separates, missing, permits, incomplete, checklists, inspection, and holds?",
            "Which HarborPilot handoff note covers handoff, separates, permits, checklists, holds, and generic?",
        ),
    },
    "dev-workspace-03-030": {
        "scope": "workspace",
        "workspace_uid": "proj-fic-harborpilot-01",
        "queries": (
            "What HarborPilot requirement should guide work on coordinator, noticed, jobs, cleared, crew, change, and sometimes?",
            "Which HarborPilot memory helps with jobs, cleared, crew, change, sometimes, lost, and assigned?",
            "For HarborPilot, what implementation detail involves coordinator, jobs, crew, sometimes, assigned, and morning?",
        ),
    },
}
