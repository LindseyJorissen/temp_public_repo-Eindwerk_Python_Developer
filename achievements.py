"""
achievements.py – Achievement definitions for Mittens: The Mischievous Cafe Destroyer.

Each entry has:
  name   – display name
  desc   – short description shown in achievements screen
  coins  – reward awarded on first unlock
  stat   – (optional) cumulative stat key for progress display
  target – (optional) target value for progress-based achievements
"""

ACHIEVEMENTS = {
    # ── Beginner hooks ──────────────────────────────────────────────
    "first_round": {
        "name": "First Round's On Me",
        "desc": "Catch 10 beers in a single game",
        "coins": 50,
    },
    "on_the_clock": {
        "name": "On The Clock",
        "desc": "Play against all 4 opponents",
        "coins": 100,
    },
    "disco_fever": {
        "name": "Disco Fever",
        "desc": "Reach 50 points in a single game",
        "coins": 75,
    },

    # ── Skill milestones ────────────────────────────────────────────
    "drunk_on_the_job": {
        "name": "Drunk On The Job",
        "desc": "Reach 80 points and survive Reverse Mode",
        "coins": 150,
    },
    "no_spills": {
        "name": "No Spills",
        "desc": "Catch 20 cups in a row without dropping one",
        "coins": 100,
    },
    "pest_control": {
        "name": "Pest Control",
        "desc": "Finish a game without being hit by any mouse",
        "coins": 150,
    },
    "shaky_hands": {
        "name": "Shaky Hands",
        "desc": "Catch 100 beers in a single game",
        "coins": 200,
    },

    # ── Grind goals (cumulative) ────────────────────────────────────
    "rookie_waiter": {
        "name": "Rookie Waiter",
        "desc": "Catch 500 total beers",
        "coins": 150,
        "stat": "total_cups_caught",
        "target": 500,
    },
    "veteran_bartender": {
        "name": "Veteran Bartender",
        "desc": "Catch 5,000 total beers",
        "coins": 500,
        "stat": "total_cups_caught",
        "target": 5000,
    },
    "whole_damn_menu": {
        "name": "The Whole Damn Menu",
        "desc": "Catch 25,000 total beers",
        "coins": 2000,
        "stat": "total_cups_caught",
        "target": 25000,
    },

    # ── Opponent-specific challenges ────────────────────────────────
    "chili_survivor": {
        "name": "Chili Survivor",
        "desc": "Score 50 points against Chili",
        "coins": 300,
    },
    "hector_tamer": {
        "name": "Hector Tamer",
        "desc": "Score 75 points against Hector",
        "coins": 250,
    },

    # ── Bar Duty campaign ────────────────────────────────────────────────────────
    "bar_survivor": {
        "name": "Bar Survivor",
        "desc": "Complete all 10 Bar Duty levels",
        "coins": 500,
    },

    # ── Kitchen Duty: Endless ────────────────────────────────────────────────────
    "kitchen_mise_en_place": {
        "name": "Mise En Place",
        "desc": "Serve 10 orders in a single endless kitchen run",
        "coins": 75,
    },
    "kitchen_head_chef": {
        "name": "Head Chef",
        "desc": "Serve 25 orders in a single endless kitchen run",
        "coins": 150,
    },
    "kitchen_iron_chef": {
        "name": "Iron Chef",
        "desc": "Serve 50 orders in a single endless kitchen run",
        "coins": 300,
    },
    "kitchen_long_shift": {
        "name": "The Long Shift",
        "desc": "Survive 5 minutes in endless kitchen mode",
        "coins": 100,
    },
    "kitchen_closing_time": {
        "name": "Closing Time",
        "desc": "Survive 10 minutes in endless kitchen mode",
        "coins": 250,
    },
    "kitchen_mittens_buffet": {
        "name": "Mittens' Buffet",
        "desc": "Have Mittens steal ingredients 5 times in one endless run",
        "coins": 50,
    },

    # ── Misc ────────────────────────────────────────────────────────
    "glutton_for_punishment": {
        "name": "Glutton For Punishment",
        "desc": "Play 50 total games",
        "coins": 200,
        "stat": "total_games_played",
        "target": 50,
    },
    "catastrophic": {
        "name": "Catastrophic",
        "desc": "Get hit by 3 mice in a single game",
        "coins": 25,
    },
}

# Ordered list for display in achievements screen
ACHIEVEMENT_ORDER = [
    "first_round",
    "on_the_clock",
    "disco_fever",
    "drunk_on_the_job",
    "no_spills",
    "pest_control",
    "shaky_hands",
    "rookie_waiter",
    "veteran_bartender",
    "whole_damn_menu",
    "chili_survivor",
    "hector_tamer",
    "bar_survivor",
    "glutton_for_punishment",
    "catastrophic",
    "kitchen_mise_en_place",
    "kitchen_head_chef",
    "kitchen_iron_chef",
    "kitchen_long_shift",
    "kitchen_closing_time",
    "kitchen_mittens_buffet",
]
