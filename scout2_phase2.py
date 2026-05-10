#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║     Scout-2 Phase 2 Processor — Investing with SPACE System          ║
║                        Version 1.0                                   ║
║                                                                      ║
║  Reads output from scout2_fetcher_v3.py and generates:              ║
║  • scout2_alerts.json          (enhanced alerts)                     ║
║  • scout2_trends.json          (cross-run signal trends)             ║
║  • scout2_scores.json          (company scoring table)               ║
║  • scout2_universe.json        (locked master universe)              ║
║  • scout2_supply_chain.json    (supplier/dependency map)             ║
║  • scout2_run_history.json     (historical run log)                  ║
║  • scout2_recommendations.json (recommended actions only)            ║
║  • scout2_dashboard_summary.json (dashboard header data)             ║
║  • scout2_email_alert.txt      (email-ready alert summary)           ║
╚══════════════════════════════════════════════════════════════════════╝

Usage:
    python scout2_phase2.py
    python scout2_phase2.py --data-dir data
    python scout2_phase2.py --quiet
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# ══════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════

VERSION     = "1.1"
SYSTEM_NAME = "Scout-2 Phase 2 / Investing with SPACE"
NOW_UTC     = datetime.now(timezone.utc)
NOW_STR     = NOW_UTC.strftime("%Y-%m-%dT%H:%M:%SZ")


# ══════════════════════════════════════════════════════════════════════
#  MASTER UNIVERSE
#  Locked list — only remove if dissolved, acquired, leaves thesis,
#  or Cory approves. Companies persist even with no recent news.
# ══════════════════════════════════════════════════════════════════════

MASTER_UNIVERSE = [
    # ── Launch ────────────────────────────────────────────────────────
    {"company": "SpaceX",               "ticker": None,    "status": "private",   "ring": 1, "layers": ["Launch", "Infrastructure", "Communications"]},
    {"company": "Rocket Lab",           "ticker": "RKLB",  "status": "public",    "ring": 1, "layers": ["Launch", "Defense/SDA", "Logistics"]},
    {"company": "Blue Origin",          "ticker": None,    "status": "private",   "ring": 1, "layers": ["Launch", "Lunar/Deep Space"]},
    {"company": "United Launch Alliance","ticker": None,   "status": "private",   "ring": 2, "layers": ["Launch", "Defense/SDA"]},
    {"company": "Firefly Aerospace",    "ticker": None,    "status": "private",   "ring": 2, "layers": ["Launch"]},
    {"company": "Relativity Space",     "ticker": None,    "status": "private",   "ring": 2, "layers": ["Launch"]},
    {"company": "Skyroot Aerospace",    "ticker": None,    "status": "private",   "ring": 2, "layers": ["Launch"]},
    {"company": "Starfighters Space",   "ticker": None,    "status": "private",   "ring": 3, "layers": ["Launch", "Defense/SDA"]},

    # ── Infrastructure / Manufacturing ────────────────────────────────
    {"company": "Northrop Grumman",     "ticker": "NOC",   "status": "public",    "ring": 1, "layers": ["Defense/SDA", "Infrastructure", "Launch"]},
    {"company": "Lockheed Martin",      "ticker": "LMT",   "status": "public",    "ring": 1, "layers": ["Defense/SDA", "Infrastructure", "Launch"]},
    {"company": "Boeing",               "ticker": "BA",    "status": "public",    "ring": 1, "layers": ["Defense/SDA", "Infrastructure", "Launch"]},
    {"company": "Raytheon Technologies","ticker": "RTX",   "status": "public",    "ring": 1, "layers": ["Defense/SDA", "Infrastructure"]},
    {"company": "L3Harris",             "ticker": "LHX",   "status": "public",    "ring": 1, "layers": ["Defense/SDA", "Communications", "Ground Segment"]},
    {"company": "MDA Space",            "ticker": "MDA.TO","status": "public",    "ring": 2, "layers": ["Infrastructure", "Logistics", "Lunar/Deep Space"]},
    {"company": "Redwire",              "ticker": "RDW",   "status": "public",    "ring": 2, "layers": ["Infrastructure", "Lunar/Deep Space", "Energy/Materials"]},
    {"company": "Terran Orbital",       "ticker": "LLAP",  "status": "public",    "ring": 2, "layers": ["Infrastructure"]},
    {"company": "Aerojet Rocketdyne",   "ticker": "AJRD",  "status": "acquired",  "ring": 2, "layers": ["Launch", "Defense/SDA"]},
    {"company": "Sierra Space",         "ticker": None,    "status": "private",   "ring": 2, "layers": ["Infrastructure", "Launch"]},
    {"company": "Axiom Space",          "ticker": None,    "status": "private",   "ring": 2, "layers": ["Infrastructure", "Logistics"]},
    {"company": "Voyager Space",        "ticker": None,    "status": "private",   "ring": 2, "layers": ["Infrastructure"]},

    # ── Defense / SDA ─────────────────────────────────────────────────
    {"company": "Leidos",               "ticker": "LDOS",  "status": "public",    "ring": 1, "layers": ["Defense/SDA", "AI/Compute"]},
    {"company": "BAE Systems",          "ticker": "BAESY", "status": "public",    "ring": 2, "layers": ["Defense/SDA"]},
    {"company": "Anduril Industries",   "ticker": None,    "status": "private",   "ring": 2, "layers": ["Defense/SDA", "AI/Compute"]},
    {"company": "Shield AI",            "ticker": None,    "status": "private",   "ring": 2, "layers": ["Defense/SDA", "AI/Compute"]},
    {"company": "HawkEye 360",          "ticker": "HE360", "status": "public",    "ring": 1, "layers": ["Defense/SDA", "Data/EO"]},
    {"company": "Odin Space",           "ticker": None,    "status": "private",   "ring": 3, "layers": ["Defense/SDA", "Logistics"]},

    # ── Communications ────────────────────────────────────────────────
    {"company": "AST SpaceMobile",      "ticker": "ASTS",  "status": "public",    "ring": 1, "layers": ["Communications"]},
    {"company": "Viasat",               "ticker": "VSAT",  "status": "public",    "ring": 1, "layers": ["Communications", "Defense/SDA"]},
    {"company": "Iridium",              "ticker": "IRDM",  "status": "public",    "ring": 2, "layers": ["Communications"]},
    {"company": "Globalstar",           "ticker": "GSAT",  "status": "public",    "ring": 1, "layers": ["Communications"]},
    {"company": "Telesat",              "ticker": "TSAT",  "status": "public",    "ring": 2, "layers": ["Communications"]},
    {"company": "SES",                  "ticker": "SGBAF", "status": "public",    "ring": 2, "layers": ["Communications"]},
    {"company": "Intelsat",             "ticker": None,    "status": "private",   "ring": 2, "layers": ["Communications"]},
    {"company": "EchoStar",             "ticker": "SATS",  "status": "public",    "ring": 2, "layers": ["Communications"]},

    # ── Data / Earth Observation ──────────────────────────────────────
    {"company": "Planet Labs",          "ticker": "PL",    "status": "public",    "ring": 1, "layers": ["Data/EO"]},
    {"company": "Maxar Technologies",   "ticker": None,    "status": "acquired",  "ring": 1, "layers": ["Data/EO", "Infrastructure"]},
    {"company": "Spire Global",         "ticker": "SPIR",  "status": "public",    "ring": 2, "layers": ["Data/EO", "Infrastructure"]},
    {"company": "BlackSky",             "ticker": "BKSY",  "status": "public",    "ring": 2, "layers": ["Data/EO"]},
    {"company": "Capella Space",        "ticker": None,    "status": "private",   "ring": 2, "layers": ["Data/EO"]},
    {"company": "Umbra",                "ticker": None,    "status": "private",   "ring": 2, "layers": ["Data/EO"]},
    {"company": "ICEYE",                "ticker": None,    "status": "private",   "ring": 2, "layers": ["Data/EO"]},
    {"company": "SatVu",                "ticker": None,    "status": "private",   "ring": 3, "layers": ["Data/EO", "Energy/Materials"]},

    # ── AI / Compute ──────────────────────────────────────────────────
    {"company": "Nvidia",               "ticker": "NVDA",  "status": "public",    "ring": 1, "layers": ["AI/Compute"]},
    {"company": "Palantir",             "ticker": "PLTR",  "status": "public",    "ring": 1, "layers": ["AI/Compute", "Defense/SDA", "Data/EO"]},
    {"company": "Quantinuum",           "ticker": None,    "status": "IPO-watch", "ring": 2, "layers": ["AI/Compute"]},
    {"company": "Credo Technology",     "ticker": "CRDO",  "status": "public",    "ring": 2, "layers": ["AI/Compute"]},
    {"company": "IREN",                 "ticker": "IREN",  "status": "public",    "ring": 2, "layers": ["AI/Compute"]},

    # ── Energy / Materials ────────────────────────────────────────────
    {"company": "MP Materials",         "ticker": "MP",    "status": "public",    "ring": 1, "layers": ["Energy/Materials"]},

    # ── Lunar / Deep Space ────────────────────────────────────────────
    {"company": "Intuitive Machines",   "ticker": "LUNR",  "status": "public",    "ring": 1, "layers": ["Lunar/Deep Space", "Launch"]},
    {"company": "Lunar Outpost",        "ticker": None,    "status": "private",   "ring": 2, "layers": ["Lunar/Deep Space", "Logistics"]},
    {"company": "Astrobotic",           "ticker": None,    "status": "private",   "ring": 2, "layers": ["Lunar/Deep Space"]},

    # ── Logistics / Servicing ─────────────────────────────────────────
    {"company": "Momentus",             "ticker": "MNTS",  "status": "public",    "ring": 2, "layers": ["Logistics"]},

    # ── Testing / Validation ──────────────────────────────────────────
    {"company": "Otto Aerospace",       "ticker": None,    "status": "private",   "ring": 3, "layers": ["Testing/Validation"]},

    # ── Government / Agency (non-investable but tracked) ──────────────
    {"company": "NASA",                 "ticker": None,    "status": "watch",     "ring": 1, "layers": ["NASA/Gov"]},
    {"company": "USSF / Space Force",   "ticker": None,    "status": "watch",     "ring": 1, "layers": ["Defense/SDA"]},
    {"company": "DARPA",                "ticker": None,    "status": "watch",     "ring": 1, "layers": ["Defense/SDA"]},
    {"company": "NRO",                  "ticker": None,    "status": "watch",     "ring": 1, "layers": ["Defense/SDA"]},
    {"company": "NGA",                  "ticker": None,    "status": "watch",     "ring": 1, "layers": ["Defense/SDA", "Data/EO"]},
    {"company": "MDA (Missile Defense)","ticker": None,    "status": "watch",     "ring": 1, "layers": ["Defense/SDA"]},
]

# Build lookup by company name (lowercase)
UNIVERSE_MAP = {e["company"].lower(): e for e in MASTER_UNIVERSE}


# ══════════════════════════════════════════════════════════════════════
#  SUPPLY CHAIN MAP (static base — enriched by signals)
# ══════════════════════════════════════════════════════════════════════

SUPPLY_CHAIN_BASE = [
    {
        "core_company":    "SpaceX",
        "suppliers":       ["Aerojet Rocketdyne", "Northrop Grumman", "Nvidia"],
        "customers":       ["NASA", "USSF / Space Force", "Globalstar", "Anthropic"],
        "partners":        ["NASA", "Anduril Industries"],
        "dependency_type": "launch_provider",
        "layer":           "Launch",
        "confidence":      9,
    },
    {
        "core_company":    "Rocket Lab",
        "suppliers":       ["Motiv Space Systems"],
        "customers":       ["NASA", "USSF / Space Force", "Anduril Industries", "Raytheon Technologies"],
        "partners":        ["Raytheon Technologies", "Anduril Industries"],
        "dependency_type": "launch_and_defense",
        "layer":           "Launch",
        "confidence":      9,
    },
    {
        "core_company":    "MDA Space",
        "suppliers":       ["Surrey Satellite Technology"],
        "customers":       ["Telesat", "Globalstar", "NASA", "Canadian Space Agency"],
        "partners":        ["Canadian Space Agency"],
        "dependency_type": "satellite_manufacturer",
        "layer":           "Infrastructure",
        "confidence":      8,
    },
    {
        "core_company":    "Planet Labs",
        "suppliers":       ["SpaceX"],
        "customers":       ["NGA", "Greek Government", "Marshall Islands", "Commercial"],
        "partners":        ["NGA", "NASA"],
        "dependency_type": "eo_data_provider",
        "layer":           "Data/EO",
        "confidence":      8,
    },
    {
        "core_company":    "AST SpaceMobile",
        "suppliers":       ["SpaceX"],
        "customers":       ["Mobile Network Operators", "AT&T", "Vodafone"],
        "partners":        ["Verizon", "Rakuten"],
        "dependency_type": "d2d_communications",
        "layer":           "Communications",
        "confidence":      8,
    },
    {
        "core_company":    "Globalstar",
        "suppliers":       ["SpaceX", "MDA Space"],
        "customers":       ["Apple", "Amazon"],
        "partners":        ["Amazon"],
        "dependency_type": "satcom_acquisition_target",
        "layer":           "Communications",
        "confidence":      9,
    },
    {
        "core_company":    "HawkEye 360",
        "suppliers":       ["SpaceX"],
        "customers":       ["NRO", "NGA", "USSF / Space Force", "DoD"],
        "partners":        ["DoD"],
        "dependency_type": "sigint_eo_provider",
        "layer":           "Defense/SDA",
        "confidence":      8,
    },
    {
        "core_company":    "Viasat",
        "suppliers":       ["Boeing", "Lockheed Martin"],
        "customers":       ["U.S. Marine Corps", "DoD", "Commercial Airlines"],
        "partners":        ["U.S. Marine Corps"],
        "dependency_type": "satcom_defense",
        "layer":           "Communications",
        "confidence":      9,
    },
    {
        "core_company":    "Northrop Grumman",
        "suppliers":       ["Aerojet Rocketdyne", "L3Harris"],
        "customers":       ["USSF / Space Force", "NASA", "DoD"],
        "partners":        ["NASA", "USSF / Space Force"],
        "dependency_type": "prime_defense_contractor",
        "layer":           "Defense/SDA",
        "confidence":      9,
    },
    {
        "core_company":    "MP Materials",
        "suppliers":       [],
        "customers":       ["DoD", "GM", "Apple", "Raytheon Technologies"],
        "partners":        ["DoD"],
        "dependency_type": "rare_earth_supplier",
        "layer":           "Energy/Materials",
        "confidence":      8,
    },
]


# ══════════════════════════════════════════════════════════════════════
#  ALERT CLASSIFICATION ENGINE v2
#  Precision-first: evidence-based event detection, not keyword spray.
#  Each event type requires strong headline/summary evidence.
#  Immediate = confirmed action on a tracked company only.
# ══════════════════════════════════════════════════════════════════════

# ── DISQUALIFIER PATTERNS ─────────────────────────────────────────────
# Items matching these are capped at "watch" regardless of other signals.
DISQUALIFIERS = {
    "opinion":        ["opinion", "analysis", "commentary", "editorial", "podcast",
                       "interview", "episode", "newsletter", "roundup", "weekly",
                       "according to", "experts say", "i think", "we think",
                       "outlook", "perspective", "in our view"],
    "nasa_info":      ["nasa image", "photo of the day", "space photo", "astronaut photo",
                       "glowing views", "i am artemis", "meet the fleet",
                       "captures mars", "artemis 2 commander",
                       "artemis astronauts saw", "scientists found",
                       "how you'd really die", "may sky", "star-hops",
                       "black holes", "exoplanets", "neutron star",
                       "titan be humanity", "moon joy", "curiosity rover wheels"],
    "general_defense":["fitness test", "insider trading", "prediction markets",
                       "ukrainian ground robot", "iran exchange fire",
                       "b-52 study", "cruise missiles on cargo",
                       "us strikes iran", "iran campaign demonstrates",
                       "europe defense autonomy", "turkish air force",
                       "aselsan", "electromagnetic spectrum exercise",
                       "hegseth", "deal team six", "munitions at risk",
                       "air force fitness", "sof insider"],
    "macro_markets":  ["strawberry fields reit", "ppl corporation",
                       "creative media", "brookfield business",
                       "stocks finish higher", "dow jones", "s&p 500",
                       "nasdaq record", "eli lilly", "omada health",
                       "data center in cleveland", "data center in nepal",
                       "data center in melbourne", "data center in lagos",
                       "medallion sues", "zerra dc", "stockland",
                       "prime breaks ground", "accelerate infrastructure",
                       "algeria and oman", "duos edge"],
}

# ── STRONG EVIDENCE PATTERNS ──────────────────────────────────────────
# These require the pattern to appear in the HEADLINE specifically,
# not just the summary, to reduce false positives.

# Contract: must have dollar value or specific award language
CONTRACT_STRONG = [
    r"\$[\d,]+\s*(million|billion|m\b|b\b)",  # dollar amount
    r"wins?\s+\$",                             # wins $X
    r"awarded?\s+\$",                          # awarded $X
    r"award[s]?\s+contract",                   # awards contract
    r"contract\s+award",                       # contract award
    r"task\s+order",                           # task order
    r"idiq",                                   # IDIQ
    r"firm.fixed.price",                       # FFP
    r"indefinite.delivery",                    # IDIQ full
    r"other\s+transaction\s+authority",        # OTA
    r"mecs\d*",                                # MECS (Marine Corps contract)
    r"sole.source\s+contract",
]

# Earnings: must reference actual results, not just the word
EARNINGS_STRONG = [
    r"q[1-4]\s+202[0-9]\s+(earnings|results|revenue|takeaways)",
    r"(quarterly|annual)\s+(earnings|results|revenue)",
    r"(beats?|misses?)\s+(earnings|estimates|expectations)",
    r"record\s+(quarterly|annual)\s+revenue",
    r"revenue\s+(grows?|grew|jumps?|falls?|declined?)\s+\d+",
    r"(earnings|revenue)\s+call",
    r"(guidance|backlog)\s+(raised?|lowered?|updated?|increased?)",
    r"(q[1-4]|full.year)\s+(eps|revenue|profit)",
]

# IPO: must reference actual event, not just mention of public markets
IPO_STRONG = [
    r"raises?\s+\$[\d,]+\s*(million|billion).*ipo",
    r"ipo\b",
    r"initial\s+public\s+offering",
    r"prices?\s+(its\s+)?(shares?|ipo)",
    r"begins?\s+trading",
    r"lists?\s+on\s+(nasdaq|nyse|stock)",
    r"s.?1\s+(filing|filed)",
    r"going\s+public",
    r"spac\s+(merger|deal)",
]

# Acquisition: must reference definitive deal, not speculation
ACQUISITION_STRONG = [
    r"acquires?\s+\w",              # acquires X
    r"to\s+acquire\s+\w",          # to acquire X
    r"acquisition\s+of\s+\w",      # acquisition of X
    r"merger\s+(agreement|with)",  # merger agreement/with
    r"acquired\s+by\s+\w",         # acquired by X
    r"takeover\s+(bid|offer)",     # takeover bid/offer
    r"buyout\s+of\s+\w",           # buyout of X
    r"acquisition\s+process",      # in acquisition process
]

# Funding: must reference confirmed round, not just mention of money
FUNDING_STRONG = [
    r"raises?\s+\$[\d,]+\s*(million|billion)",  # raises $X
    r"closes?\s+\$[\d,]+",                      # closes $X
    r"series\s+[a-e]\s+(funding|round)",        # Series A/B/C round
    r"seed\s+(round|funding)",                  # seed round
    r"\$[\d,]+\s*(million|billion)\s+(in\s+)?(funding|round|investment)",
    r"unicorn",                                  # unicorn status
    r"valuation\s+of\s+(more\s+than\s+)?\$",   # valuation of $X
]

# Defense award: must confirm actual award to a tracked company
DEFENSE_AWARD_STRONG = [
    r"(space\s+force|ussf|darpa|nro|nga|pentagon|dod)\s+(awards?|contracts?)",
    r"awards?\s+\$[\d,]+.*?(space\s+force|ussf|darpa|nro|nga|dod|pentagon)",
    r"(golden\s+dome|sbi|space.based\s+interceptor)",
    r"classified\s+contract",
    r"military\s+contract\s+to\s+\w",
    r"defense\s+contract\s+award",
]

# Guidance/revenue update (subset of earnings, treated separately)
GUIDANCE_STRONG = [
    r"raises?\s+(guidance|outlook|forecast)",
    r"(raises?|increases?|updates?)\s+full.year",
    r"(record|all.time.high)\s+(revenue|backlog|orders)",
    r"backlog\s+(grows?|reaches?|hits?)\s+\$",
]


def match_patterns(text: str, patterns: list) -> bool:
    """Return True if any regex pattern matches the text."""
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def is_disqualified(title: str, summary: str) -> tuple:
    """
    Check if item should be capped at watch/same_day due to content type.
    Returns (is_disqualified: bool, reason: str)
    """
    combined = f"{title} {summary}".lower()
    for reason, patterns in DISQUALIFIERS.items():
        if any(p in combined for p in patterns):
            return True, reason
    return False, None


def classify_event_types_v2(title: str, summary: str) -> tuple:
    """
    Precision event type detection.
    Requires strong headline evidence for high-confidence types.
    Returns (event_types: list, confidence: str, false_positive_risk: str)
    """
    title_lower   = title.lower()
    combined      = f"{title} {summary}".lower()
    event_types   = []
    evidence_count = 0

    # Check each event type with strong pattern matching
    if match_patterns(title_lower, CONTRACT_STRONG):
        event_types.append("contract")
        evidence_count += 3
    elif match_patterns(combined, CONTRACT_STRONG[:4]):  # looser for summary
        event_types.append("contract")
        evidence_count += 1

    if match_patterns(title_lower, EARNINGS_STRONG) or match_patterns(combined, EARNINGS_STRONG):
        event_types.append("earnings")
        evidence_count += 3

    if match_patterns(title_lower, IPO_STRONG) or match_patterns(combined, IPO_STRONG):
        event_types.append("ipo")
        evidence_count += 3

    if match_patterns(title_lower, ACQUISITION_STRONG) or match_patterns(combined, ACQUISITION_STRONG):
        event_types.append("acquisition")
        evidence_count += 3

    if match_patterns(title_lower, FUNDING_STRONG) or match_patterns(combined, FUNDING_STRONG):
        event_types.append("funding")
        evidence_count += 2

    if match_patterns(title_lower, DEFENSE_AWARD_STRONG) or match_patterns(combined, DEFENSE_AWARD_STRONG):
        event_types.append("defense_award")
        evidence_count += 3

    if match_patterns(title_lower, GUIDANCE_STRONG) or match_patterns(combined, GUIDANCE_STRONG):
        if "earnings" not in event_types:
            event_types.append("guidance")
        evidence_count += 2

    # Softer signals — only add if no hard signals found
    if not event_types:
        if any(kw in combined for kw in ["partnership", "teaming agreement", "joint venture", "mou with"]):
            event_types.append("partnership")
            evidence_count += 1
        if any(kw in combined for kw in ["static fire", "test flight", "first flight", "maiden flight",
                                          "launch milestone", "successfully launched", "achieved orbit"]):
            event_types.append("product_launch")
            evidence_count += 1

    # Confidence and false positive risk
    if evidence_count >= 3:
        confidence         = "high"
        false_positive_risk = "low"
    elif evidence_count == 2:
        confidence         = "medium"
        false_positive_risk = "medium"
    else:
        confidence         = "low"
        false_positive_risk = "high"

    return event_types, confidence, false_positive_risk


def calc_urgency_v2(
    event_types:        list,
    tracked_companies:  list,
    confidence:         str,
    false_positive_risk:str,
    disqualified:       bool,
    age_hours:          float,
) -> tuple:
    """
    Precision urgency classification.
    Immediate ONLY when:
    - tracked company involved AND
    - hard event type (contract/earnings/ipo/acquisition/defense_award/guidance) AND
    - high or medium confidence AND
    - not disqualified AND
    - published within 24h

    Returns (urgency: str, requires_council_review: bool)
    """
    IMMEDIATE_TYPES = {"contract", "earnings", "ipo", "acquisition", "defense_award", "guidance"}
    SOFT_TYPES      = {"partnership", "product_launch", "funding"}

    has_tracked    = len(tracked_companies) > 0
    has_hard_event = bool(IMMEDIATE_TYPES & set(event_types))
    has_soft_only  = bool(event_types) and not has_hard_event
    is_fresh       = age_hours <= 24
    is_high_conf   = confidence in ("high", "medium")
    is_low_fp      = false_positive_risk in ("low", "medium")

    # Immediate: all gates must pass
    if (has_hard_event and has_tracked and is_high_conf
            and is_low_fp and not disqualified and is_fresh):
        requires_review = True
        return "immediate", requires_review

    # Same day: tracked company + hard event but older, or soft event + tracked + fresh
    if has_tracked and has_hard_event and not disqualified:
        return "same_day", True

    if has_tracked and has_soft_only and is_fresh and not disqualified:
        return "same_day", False

    if has_hard_event and not has_tracked and not disqualified and is_fresh:
        return "same_day", False

    # Watch: everything else that passed disqualification
    return "watch", False


URGENCY_WEIGHTS = {
    "contract": 3, "earnings": 3, "ipo": 3, "guidance": 3,
    "acquisition": 3, "defense_award": 3, "funding": 2,
    "partnership": 1, "product_launch": 1,
}

LAYER_KEYWORDS = {
    "Launch":           ["launch", "rocket", "liftoff", "starship", "electron",
                         "neutron", "falcon", "new glenn", "vulcan"],
    "Infrastructure":   ["satellite", "constellation", "spacecraft", "manufacturing",
                         "bus", "propulsion", "smallsat"],
    "Defense/SDA":      ["space domain", "sda", "space force", "ussf", "darpa",
                         "missile", "hypersonic", "golden dome", "nro", "nga",
                         "pentagon", "dod", "isr", "geoint"],
    "Communications":   ["satcom", "direct-to-device", "d2d", "starlink",
                         "broadband", "telesat", "globalstar", "iridium"],
    "Data/EO":          ["earth observation", "imagery", "geospatial", "sar",
                         "remote sensing", "hyperspectral", "planet labs", "maxar"],
    "AI/Compute":       ["artificial intelligence", "machine learning", "gpu",
                         "compute", "inference", "semiconductor", "data center"],
    "Testing/Validation":["rf testing", "anechoic", "vibration test", "tvac",
                          "qualification", "simulation", "digital twin"],
    "Ground Segment":   ["ground station", "antenna", "earth station", "teleport"],
    "Logistics":        ["in-orbit servicing", "refueling", "debris removal",
                         "cargo resupply", "orbital transfer"],
    "Energy/Materials": ["nuclear", "solar array", "power system", "rare earth",
                         "lithium", "tantalum", "kilopower"],
    "Lunar/Deep Space": ["lunar", "moon", "cislunar", "mars", "deep space",
                         "artemis", "gateway", "orion"],
    "Software/OS":      ["mission control", "software", "autonomy", "algorithm",
                         "operating system", "data pipeline"],
    "NASA/Gov":         ["nasa", "artemis", "clps", "crs", "hls", "cots"],
}


# ══════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════

def load_json(path: Path) -> Optional[dict]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  [WARN] Could not load {path}: {e}", file=sys.stderr)
    return None


def save_json(path: Path, data: dict, quiet: bool = False):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    if not quiet:
        print(f"  ✓ {path}", file=sys.stderr)


def detect_companies(text: str) -> list:
    """Find known universe companies mentioned in text."""
    found = []
    lower = text.lower()
    for entry in MASTER_UNIVERSE:
        name = entry["company"].lower()
        if name in lower and entry["company"] not in found:
            found.append(entry["company"])
        if entry["ticker"] and entry["ticker"].lower() in lower:
            if entry["company"] not in found:
                found.append(entry["company"])
    return found


def detect_layers(text: str) -> list:
    """Detect thesis layers from text."""
    found = []
    lower = text.lower()
    for layer, keywords in LAYER_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            if layer not in found:
                found.append(layer)
    return found[:3]  # max 3 layers


def detect_event_types(text: str) -> list:
    """Legacy wrapper — used by trends/scores. Uses v2 classifier internally."""
    title   = text[:120]  # treat first 120 chars as headline proxy
    summary = text[120:]
    types, _, _ = classify_event_types_v2(title, summary)
    return types


def calc_alert_score(event_types: list, age_hours: float) -> int:
    """Score 1-10 based on event types and freshness."""
    base      = sum(URGENCY_WEIGHTS.get(e, 1) for e in event_types)
    freshness = max(0, 3 - int(age_hours / 24))
    return min(10, max(1, base + freshness))


def calc_urgency(score: int, age_hours: float) -> str:
    """Legacy wrapper kept for compatibility."""
    if score >= 6 or (score >= 3 and age_hours <= 6):
        return "immediate"
    elif score >= 3 or age_hours <= 24:
        return "same_day"
    return "watch"


def recommended_action(event_types: list, urgency: str) -> str:
    if "ipo" in event_types:
        return "Review S-1 filing and valuation before IPO date"
    if "acquisition" in event_types:
        return "Assess impact on supply chain and competing positions"
    if "contract" in event_types or "defense_award" in event_types:
        return "Confirm contract size and duration; assess backlog impact"
    if "earnings" in event_types:
        return "Review guidance and revenue trend before next position decision"
    if "funding" in event_types:
        return "Monitor valuation and IPO timeline"
    if urgency == "immediate":
        return "Review immediately and assess thesis impact"
    return "Monitor and log for next council review"


def recommended_agent(event_types: list, layers: list) -> str:
    if "defense_award" in event_types or "Defense/SDA" in layers:
        return "Defense & SDA Agent"
    if "ipo" in event_types or "earnings" in event_types:
        return "Capital Markets Agent"
    if "acquisition" in event_types:
        return "M&A Monitoring Agent"
    if "funding" in event_types:
        return "Private Markets Agent"
    if "Data/EO" in layers or "AI/Compute" in layers:
        return "Data & AI Agent"
    if "Launch" in layers:
        return "Launch & Infrastructure Agent"
    return "General Scout Agent"


def why_it_matters(event_types: list, companies: list, layers: list) -> str:
    parts = []
    if "defense_award" in event_types:
        parts.append("Direct DoD/USSF contract signal — validates defense space spending thesis")
    if "ipo" in event_types:
        parts.append("IPO creates new publicly tradeable space thesis vehicle")
    if "acquisition" in event_types:
        parts.append("M&A reshapes competitive landscape and supply chain dependencies")
    if "contract" in event_types:
        parts.append("Contract award confirms revenue visibility and backlog growth")
    if "earnings" in event_types:
        parts.append("Earnings data validates or challenges current thesis assumptions")
    if "funding" in event_types:
        parts.append("Private funding round signals investor confidence in this thesis layer")
    if companies:
        parts.append(f"Directly involves tracked universe companies: {', '.join(companies[:3])}")
    if not parts:
        parts.append(f"Relevant signal in {', '.join(layers[:2])} thesis layer(s)")
    return " | ".join(parts)


# ══════════════════════════════════════════════════════════════════════
#  PHASE 2 PROCESSORS
# ══════════════════════════════════════════════════════════════════════

def build_enhanced_alerts(items: list) -> list:
    """
    Build enhanced alerts from live items — precision v2.
    Uses evidence-based classification, not keyword spray.
    Immediate only fires when all gates pass.
    """
    alerts  = []
    skipped = 0

    # Source weight map — higher weight = more reliable source
    HIGH_WEIGHT_SOURCES = {
        "spacenews.com", "breakingdefense.com", "payloadspace.com",
        "satellitetoday.com", "airandspaceforces.com", "defensenews.com",
        "defenseone.com",
    }

    for item in items:
        title     = item.get("title",   "")
        summary   = item.get("summary", "")
        combined  = f"{title} {summary}"
        age_hours = item.get("age_hours") or 72
        source    = item.get("source_url", "").lower()

        # ── Step 1: Disqualify opinion/info/macro items ───────────────
        disqualified, disq_reason = is_disqualified(title, summary)

        # ── Step 2: Precision event classification ────────────────────
        event_types, confidence, fp_risk = classify_event_types_v2(title, summary)

        # No event types at all → skip entirely (not even a watch alert)
        if not event_types:
            skipped += 1
            continue

        # ── Step 3: Company detection (tracked universe only) ─────────
        companies = detect_companies(combined)
        layers    = detect_layers(combined)

        # ── Step 4: Urgency with all gates ────────────────────────────
        urgency, requires_review = calc_urgency_v2(
            event_types, companies, confidence, fp_risk,
            disqualified, age_hours
        )

        # Disqualified items cap at watch
        if disqualified and urgency != "watch":
            urgency = "watch"
            requires_review = False

        # ── Step 5: Alert score ───────────────────────────────────────
        score = calc_alert_score(event_types, age_hours)
        # Penalty for disqualified or low confidence
        if disqualified:
            score = max(1, score - 3)
        if confidence == "low":
            score = max(1, score - 2)
        if fp_risk == "high":
            score = max(1, score - 1)

        # ── Step 6: Source weight ─────────────────────────────────────
        src_weight = 8 if any(s in source for s in HIGH_WEIGHT_SOURCES) else 5

        # ── Step 7: Ticker ────────────────────────────────────────────
        ticker = None
        for c in companies:
            entry = UNIVERSE_MAP.get(c.lower())
            if entry and entry.get("ticker"):
                ticker = entry["ticker"]
                break

        ring = min(
            [UNIVERSE_MAP.get(c.lower(), {}).get("ring", 3) for c in companies],
            default=3
        ) if companies else 3

        alerts.append({
            # ── Core urgency fields ───────────────────────────────────
            "urgency":              urgency,
            "alert_score":          score,
            "confidence":           confidence,
            "false_positive_risk":  fp_risk,
            "requires_council_review": requires_review,
            # ── Event classification ──────────────────────────────────
            "event_type":           event_types,
            "disqualified":         disqualified,
            "disqualify_reason":    disq_reason,
            # ── Source ───────────────────────────────────────────────
            "source_weight":        src_weight,
            "feed_label":           item.get("feed_label", ""),
            "source_url":           item.get("source_url", ""),
            # ── Company / thesis ──────────────────────────────────────
            "company":              companies[:3] if companies else [],
            "ticker":               ticker,
            "layer":                layers[:3] if layers else ["General"],
            "ring":                 ring,
            # ── Content ───────────────────────────────────────────────
            "headline":             title,
            "link":                 item.get("link", ""),
            "summary":              summary[:400],
            # ── Analysis ─────────────────────────────────────────────
            "why_it_matters":       why_it_matters(event_types, companies, layers),
            "recommended_action":   recommended_action(event_types, urgency),
            "recommended_agent":    recommended_agent(event_types, layers),
            # ── Timestamps ───────────────────────────────────────────
            "published_utc":        item.get("published_utc", ""),
            "age_hours":            age_hours,
            "created_at_utc":       NOW_STR,
        })

    # Sort: immediate first → score desc → age asc
    order = {"immediate": 0, "same_day": 1, "watch": 2}
    alerts.sort(key=lambda a: (order.get(a["urgency"], 9), -a["alert_score"], a["age_hours"]))

    # Log classification stats
    immediate_n = sum(1 for a in alerts if a["urgency"] == "immediate")
    same_day_n  = sum(1 for a in alerts if a["urgency"] == "same_day")
    watch_n     = sum(1 for a in alerts if a["urgency"] == "watch")
    print(f"  Alert classifier v2: {len(alerts)} alerts "
          f"({immediate_n} immediate / {same_day_n} same_day / {watch_n} watch) "
          f"| {skipped} items skipped (no evidence)", file=sys.stderr)

    return alerts


def build_trends(items: list, history_path: Path) -> dict:
    """Build cross-run signal trends."""
    # Count mentions in current run
    company_counts = {}
    layer_counts   = {}
    event_counts   = {}

    for item in items:
        combined = f"{item.get('title','')} {item.get('summary','')}".lower()
        for c in detect_companies(combined):
            company_counts[c] = company_counts.get(c, 0) + 1
        for l in detect_layers(combined):
            layer_counts[l] = layer_counts.get(l, 0) + 1
        for e in detect_event_types(combined):
            event_counts[e] = event_counts.get(e, 0) + 1

    # Load prior run data for trend comparison
    prior_company = {}
    prior_layer   = {}
    history = load_json(history_path)
    if history:
        runs = history.get("runs", [])
        if runs:
            last = runs[-1]
            prior_company = last.get("company_counts", {})
            prior_layer   = last.get("layer_counts", {})

    def trend_label(curr, prior):
        if prior == 0:
            return "new"
        delta = curr - prior
        if delta > 2:   return "rising"
        if delta < -2:  return "falling"
        return "stable"

    # Top companies with trends
    top_companies = []
    for company, count in sorted(company_counts.items(), key=lambda x: -x[1])[:20]:
        entry = UNIVERSE_MAP.get(company.lower(), {})
        top_companies.append({
            "company":  company,
            "ticker":   entry.get("ticker"),
            "count":    count,
            "prior":    prior_company.get(company, 0),
            "trend":    trend_label(count, prior_company.get(company, 0)),
            "layers":   entry.get("layers", []),
        })

    # Top layers with trends
    top_layers = []
    for layer, count in sorted(layer_counts.items(), key=lambda x: -x[1]):
        top_layers.append({
            "layer":  layer,
            "count":  count,
            "prior":  prior_layer.get(layer, 0),
            "trend":  trend_label(count, prior_layer.get(layer, 0)),
        })

    # Silent tracked companies (in universe but no mentions this run)
    silent = []
    for entry in MASTER_UNIVERSE:
        if entry["company"] not in company_counts and entry["status"] == "public":
            silent.append({
                "company": entry["company"],
                "ticker":  entry["ticker"],
                "layers":  entry["layers"],
                "note":    "No signal in current 72h window",
            })

    # Top emerging themes
    rising = [c["company"] for c in top_companies if c["trend"] == "rising"][:5]

    return {
        "meta": {
            "generated_at_utc": NOW_STR,
            "items_analyzed":   len(items),
            "window":           "72h",
        },
        "company_mentions":     top_companies,
        "layer_mentions":       top_layers,
        "event_type_counts":    event_counts,
        "rising_companies":     rising,
        "silent_tracked":       silent[:15],
        "top_emerging_themes":  [l["layer"] for l in top_layers if l["trend"] == "rising"][:5],
        "_raw_company_counts":  company_counts,
        "_raw_layer_counts":    layer_counts,
    }


def build_scores(items: list, data_dir: Path) -> list:
    """Build company scoring table."""
    # Load prior scores for delta tracking
    prior_path   = data_dir / "scout2_scores.json"
    prior_data   = load_json(prior_path)
    prior_scores = {}
    if prior_data:
        for entry in prior_data.get("scores", []):
            prior_scores[entry["company"]] = entry.get("score", 5)

    # Count signals per company from current items
    company_signals = {}
    for item in items:
        combined = f"{item.get('title','')} {item.get('summary','')}".lower()
        companies  = detect_companies(combined)
        event_types = detect_event_types(combined)
        age_hours  = item.get("age_hours") or 72
        for c in companies:
            if c not in company_signals:
                company_signals[c] = {"count": 0, "score_add": 0, "events": [], "age_min": age_hours}
            company_signals[c]["count"]     += 1
            company_signals[c]["score_add"] += calc_alert_score(event_types, age_hours)
            company_signals[c]["events"].extend(event_types)
            company_signals[c]["age_min"]   = min(company_signals[c]["age_min"], age_hours)

    scores = []
    for entry in MASTER_UNIVERSE:
        company = entry["company"]
        sig     = company_signals.get(company, {})
        count   = sig.get("count", 0)
        add     = sig.get("score_add", 0)
        events  = list(set(sig.get("events", [])))
        prior   = prior_scores.get(company, 5)

        # Score: base 5 + signal boost, capped 1-10
        raw_score    = min(10, max(1, 5 + min(add // 3, 4) + (1 if count > 2 else 0)))
        score_change = raw_score - prior

        # Signal status
        if count == 0:
            signal_status = "silent"
        elif count <= 2:
            signal_status = "active"
        else:
            signal_status = "active"

        # Capital priority
        if raw_score >= 8 and entry["status"] == "public":
            capital_priority = "high"
        elif raw_score >= 6 and entry["status"] in ("public", "IPO-watch"):
            capital_priority = "medium"
        elif entry["status"] in ("acquired", "watch"):
            capital_priority = "watch"
        else:
            capital_priority = "low"

        # Recommended action
        if entry["status"] not in ("public", "IPO-watch"):
            rec_action = "watch"
        elif score_change >= 2:
            rec_action = "review"
        elif raw_score >= 8:
            rec_action = "buy_on_pullback"
        elif raw_score >= 6:
            rec_action = "hold"
        elif raw_score <= 3:
            rec_action = "avoid"
        else:
            rec_action = "watch"

        # Score change reason
        if count == 0:
            reason = "No signals in current 72h window"
        elif "defense_award" in events:
            reason = "Defense contract or award signal detected"
        elif "ipo" in events:
            reason = "IPO signal detected"
        elif "earnings" in events:
            reason = "Earnings signal detected"
        elif "acquisition" in events:
            reason = "Acquisition signal detected"
        elif "contract" in events:
            reason = "Contract signal detected"
        elif "funding" in events:
            reason = "Funding round signal detected"
        else:
            reason = f"{count} mentions in current window"

        last_signal = None
        if count > 0:
            last_signal = NOW_STR

        scores.append({
            "company":             company,
            "ticker":              entry.get("ticker"),
            "status":              entry["status"],
            "ring":                entry["ring"],
            "layers":              entry["layers"],
            "score":               raw_score,
            "prior_score":         prior,
            "score_change":        score_change,
            "score_change_reason": reason,
            "signal_count":        count,
            "signal_status":       signal_status,
            "capital_priority":    capital_priority,
            "recommended_action":  rec_action,
            "last_signal_at_utc":  last_signal,
        })

    # Sort by score desc
    scores.sort(key=lambda x: (-x["score"], x["company"]))
    return scores


def build_universe(scores: list) -> dict:
    """Build locked master universe file."""
    universe_entries = []
    score_map = {s["company"]: s for s in scores}

    for entry in MASTER_UNIVERSE:
        sc = score_map.get(entry["company"], {})
        universe_entries.append({
            "company":         entry["company"],
            "ticker":          entry.get("ticker"),
            "status":          entry["status"],
            "ring":            entry["ring"],
            "layers":          entry["layers"],
            "locked":          True,
            "removal_rule":    "Only remove if dissolved, acquired, leaves thesis, or Cory approves",
            "score":           sc.get("score", 5),
            "signal_status":   sc.get("signal_status", "silent"),
            "capital_priority":sc.get("capital_priority", "watch"),
            "last_signal_at_utc": sc.get("last_signal_at_utc"),
        })

    return {
        "meta": {
            "generated_at_utc": NOW_STR,
            "total_companies":  len(universe_entries),
            "locked":           True,
            "removal_rule":     "Only remove if dissolved, acquired, leaves thesis, or Cory approves",
            "note":             "Companies persist in universe even with no recent news signals",
        },
        "universe": universe_entries,
    }


def build_supply_chain(items: list) -> dict:
    """Build enriched supply chain map."""
    enriched = []
    for base in SUPPLY_CHAIN_BASE:
        # Find recent articles mentioning this company
        company_lower = base["core_company"].lower()
        related = []
        for item in items:
            combined = f"{item.get('title','')} {item.get('summary','')}".lower()
            if company_lower in combined:
                related.append({
                    "headline": item.get("title","")[:120],
                    "link":     item.get("link",""),
                    "age_hours":item.get("age_hours"),
                })

        entry = dict(base)
        entry["last_signal"]      = NOW_STR if related else None
        entry["related_articles"] = related[:5]
        entry["generated_at_utc"] = NOW_STR
        enriched.append(entry)

    return {
        "meta": {
            "generated_at_utc": NOW_STR,
            "total_relationships": len(enriched),
            "note": "Static base map enriched with live article signals",
        },
        "supply_chain": enriched,
    }


def build_recommendations(alerts: list) -> dict:
    """Build recommendations-only file."""
    recs = []
    seen = set()
    for alert in alerts:
        companies = alert.get("company", [])
        for company in companies[:1]:  # primary company only
            key = f"{company}:{alert.get('event_type',[''])[0]}"
            if key in seen:
                continue
            seen.add(key)

            entry = UNIVERSE_MAP.get(company.lower(), {})
            if entry.get("status") not in ("public", "IPO-watch", "watch"):
                continue

            recs.append({
                "company":        company,
                "ticker":         alert.get("ticker"),
                "action_type":    alert.get("recommended_action","watch"),
                "urgency":        alert.get("urgency","watch"),
                "event_types":    alert.get("event_type",[]),
                "rationale":      alert.get("why_it_matters",""),
                "risk_note":      "This is a signal flag, not a trade recommendation. Verify before acting.",
                "council_agent":  alert.get("recommended_agent","General Scout Agent"),
                "headline":       alert.get("headline",""),
                "link":           alert.get("link",""),
                "created_at_utc": NOW_STR,
                "disclaimer":     "NO AUTOMATED TRADE EXECUTION. Human review required.",
            })

    return {
        "meta": {
            "generated_at_utc":  NOW_STR,
            "total_recommendations": len(recs),
            "disclaimer": (
                "These are signal-based flags for human review only. "
                "No automated trade execution. Always verify independently."
            ),
        },
        "recommendations": recs[:30],  # cap at 30
    }


def update_run_history(
    history_path: Path,
    stats: dict,
    alerts: list,
    scores: list,
    trends: dict,
) -> dict:
    """Update run history with this run's metadata."""
    history = load_json(history_path) or {"runs": []}
    runs    = history.get("runs", [])

    # Top score mover
    top_mover = max(scores, key=lambda x: abs(x["score_change"]), default={})

    # Top new company (rising trend)
    rising = trends.get("rising_companies", [])
    top_new = rising[0] if rising else None

    # Top layer mover
    layer_trends = trends.get("layer_mentions", [])
    top_layer = next((l["layer"] for l in layer_trends if l.get("trend") == "rising"), None)

    run_entry = {
        "run_timestamp_utc": NOW_STR,
        "items_live":        stats.get("items_live", 0),
        "alerts_count":      len(alerts),
        "immediate_count":   sum(1 for a in alerts if a["urgency"] == "immediate"),
        "same_day_count":    sum(1 for a in alerts if a["urgency"] == "same_day"),
        "watch_count":       sum(1 for a in alerts if a["urgency"] == "watch"),
        "top_score_mover":   top_mover.get("company"),
        "top_new_company":   top_new,
        "top_layer_mover":   top_layer,
        "company_counts":    trends.get("_raw_company_counts", {}),
        "layer_counts":      trends.get("_raw_layer_counts", {}),
        "notes":             "",
    }

    runs.append(run_entry)
    runs = runs[-60:]  # keep last 60 runs (~20 days at 3x/day)

    updated = {"runs": runs}
    save_json(history_path, updated, quiet=True)
    return run_entry


def build_dashboard_summary(
    stats: dict,
    alerts: list,
    scores: list,
    trends: dict,
    feed_logs: list,
) -> dict:
    """Build small summary file for dashboard header."""
    immediate = [a for a in alerts if a["urgency"] == "immediate"]
    same_day  = [a for a in alerts if a["urgency"] == "same_day"]
    watch     = [a for a in alerts if a["urgency"] == "watch"]

    top_alert = immediate[0]["headline"] if immediate else (
                same_day[0]["headline"] if same_day else "No immediate alerts")

    top_mover  = max(scores, key=lambda x: abs(x["score_change"]), default={})
    layer_list = trends.get("layer_mentions", [])
    top_layer  = layer_list[0]["layer"] if layer_list else "None"

    feeds_ok     = sum(1 for f in feed_logs if not f.get("error"))
    feeds_failed = sum(1 for f in feed_logs if f.get("error"))

    return {
        "last_updated_utc":    NOW_STR,
        "system_status":       "operational" if feeds_failed == 0 else "degraded",
        "feed_health":         f"{feeds_ok}/{feeds_ok + feeds_failed} feeds OK",
        "top_alert":           top_alert[:120],
        "top_layer":           top_layer,
        "top_score_mover":     top_mover.get("company","None"),
        "top_score_change":    top_mover.get("score_change", 0),
        "immediate_alert_count": len(immediate),
        "same_day_alert_count":  len(same_day),
        "watch_alert_count":     len(watch),
        "total_alerts":          len(alerts),
        "items_live":            stats.get("items_live", 0),
        "universe_size":         len(MASTER_UNIVERSE),
    }


def build_email_alert(alerts: list, summary: dict) -> str:
    """Build email-ready plain text alert summary."""
    lines = []
    lines.append("=" * 60)
    lines.append("SCOUT-2 INTELLIGENCE ALERT — Investing with SPACE")
    lines.append(f"Generated: {NOW_STR}")
    lines.append("=" * 60)
    lines.append("")

    immediate = [a for a in alerts if a["urgency"] == "immediate"]
    same_day  = [a for a in alerts if a["urgency"] == "same_day"]

    lines.append(f"SYSTEM STATUS : {summary['system_status'].upper()}")
    lines.append(f"FEED HEALTH   : {summary['feed_health']}")
    lines.append(f"LIVE ITEMS    : {summary['items_live']}")
    lines.append(f"TOTAL ALERTS  : {summary['total_alerts']}")
    lines.append("")

    if immediate:
        lines.append("🚨 IMMEDIATE ALERTS")
        lines.append("-" * 40)
        for a in immediate[:5]:
            lines.append(f"  [{', '.join(a['event_type']).upper()}]")
            lines.append(f"  {a['headline']}")
            lines.append(f"  Companies: {', '.join(a['company'][:3])}")
            lines.append(f"  Why: {a['why_it_matters'][:150]}")
            lines.append(f"  Action: {a['recommended_action']}")
            lines.append(f"  Link: {a['link']}")
            lines.append("")

    if same_day:
        lines.append("⚡ SAME DAY ALERTS")
        lines.append("-" * 40)
        for a in same_day[:5]:
            lines.append(f"  [{', '.join(a['event_type']).upper()}] {a['headline'][:80]}")
            lines.append(f"  Link: {a['link']}")
            lines.append("")

    lines.append("=" * 60)
    lines.append("Dashboard: https://stachehistory.github.io/scout2-data/")
    lines.append("NO AUTOMATED TRADE EXECUTION — Human review required.")
    lines.append("=" * 60)
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(
        description="Scout-2 Phase 2 Processor v1.0"
    )
    ap.add_argument("--data-dir", default="data",
        help="Data directory (default: data)")
    ap.add_argument("--quiet", action="store_true",
        help="Suppress output")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    data_dir.mkdir(exist_ok=True)

    if not args.quiet:
        print("\n╔════════════════════════════════════════════════════╗", file=sys.stderr)
        print("║  Scout-2 Phase 2 Processor  |  Investing with SPACE ║", file=sys.stderr)
        print("╚════════════════════════════════════════════════════╝", file=sys.stderr)
        print(f"  Processing at: {NOW_STR}\n", file=sys.stderr)

    # ── Load latest fetcher output ────────────────────────────────
    latest_path = data_dir / "scout2_dump_latest.json"
    if not latest_path.exists():
        sys.exit(f"[ERROR] {latest_path} not found. Run scout2_fetcher_v3.py first.")

    dump     = load_json(latest_path)
    items    = dump.get("items", [])
    feed_logs = dump.get("feed_log", [])
    meta     = dump.get("meta", {})
    stats    = {
        "items_live":       meta.get("items_after_dedup", len(items)),
        "feeds_attempted":  meta.get("feeds_attempted", 0),
        "feeds_failed":     meta.get("feeds_failed", 0),
    }

    if not args.quiet:
        print(f"  Loaded {len(items)} live items from fetcher output", file=sys.stderr)
        print(f"  Building Phase 2 intelligence files...\n", file=sys.stderr)

    # ── Build all Phase 2 outputs ─────────────────────────────────
    history_path = data_dir / "scout2_run_history.json"
    trends       = build_trends(items, history_path)
    alerts       = build_enhanced_alerts(items)
    scores       = build_scores(items, data_dir)
    universe     = build_universe(scores)
    supply_chain = build_supply_chain(items)
    recommendations = build_recommendations(alerts)
    run_entry    = update_run_history(history_path, stats, alerts, scores, trends)
    summary      = build_dashboard_summary(stats, alerts, scores, trends, feed_logs)
    email_text   = build_email_alert(alerts, summary)

    # ── Build final alerts JSON (compatible with v4.0 fetcher) ────
    immediate = [a for a in alerts if a["urgency"] == "immediate"]
    same_day  = [a for a in alerts if a["urgency"] == "same_day"]
    watch_    = [a for a in alerts if a["urgency"] == "watch"]

    alerts_out = {
        "meta": {
            "system":            SYSTEM_NAME,
            "version":           VERSION,
            "run_timestamp_utc": NOW_STR,
            "total_alerts":      len(alerts),
            "immediate_count":   len(immediate),
            "same_day_count":    len(same_day),
            "watch_count":       len(watch_),
        },
        "immediate": immediate,
        "same_day":  same_day,
        "watch":     watch_,
    }

    # Remove internal trend fields before saving
    trends_clean = {k: v for k, v in trends.items() if not k.startswith("_")}

    # ── Save all files ────────────────────────────────────────────
    save_json(data_dir / "scout2_alerts.json",           alerts_out,      args.quiet)
    save_json(data_dir / "scout2_trends.json",           trends_clean,    args.quiet)
    save_json(data_dir / "scout2_scores.json",
              {"meta": {"generated_at_utc": NOW_STR}, "scores": scores}, args.quiet)
    save_json(data_dir / "scout2_universe.json",         universe,        args.quiet)
    save_json(data_dir / "scout2_supply_chain.json",     supply_chain,    args.quiet)
    save_json(data_dir / "scout2_recommendations.json",  recommendations, args.quiet)
    save_json(data_dir / "scout2_dashboard_summary.json",summary,         args.quiet)

    # Email alert text
    email_path = data_dir / "scout2_email_alert.txt"
    email_path.write_text(email_text, encoding="utf-8")
    if not args.quiet:
        print(f"  ✓ {email_path}", file=sys.stderr)

    # ── Summary ───────────────────────────────────────────────────
    if not args.quiet:
        print(f"\n{'─'*50}", file=sys.stderr)
        print(f"  🚨 Immediate alerts : {len(immediate)}", file=sys.stderr)
        print(f"  ⚡ Same-day alerts  : {len(same_day)}", file=sys.stderr)
        print(f"  👁  Watch alerts    : {len(watch_)}", file=sys.stderr)
        print(f"  🏢 Universe tracked : {len(MASTER_UNIVERSE)}", file=sys.stderr)
        print(f"  📊 Companies scored : {len(scores)}", file=sys.stderr)
        print(f"{'─'*50}\n", file=sys.stderr)


if __name__ == "__main__":
    main()
