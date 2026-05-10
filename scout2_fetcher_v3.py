#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║        Scout-2 RSS Fetcher — Investing with SPACE System             ║
║                       Version 4.0                                    ║
║                                                                      ║
║  NEW IN v4.0:                                                        ║
║  • scout2_alerts.json     — high-signal items only                   ║
║  • scout2_dump_latest.json — copy of latest run for dashboard        ║
║  • archive/scout2_dump_YYYYMMDD_HHMM.json — timestamped archive      ║
║  • scout2_run_history.json — log of every run                        ║
║  • urgency classification: immediate / same_day / watch              ║
╚══════════════════════════════════════════════════════════════════════╝

Usage:
    python scout2_fetcher_v3.py                     # live fetch, 72h window
    python scout2_fetcher_v3.py --days 1            # last 24 hours only
    python scout2_fetcher_v3.py --days 7            # last 7 days
    python scout2_fetcher_v3.py --max 40            # max items per feed
    python scout2_fetcher_v3.py --no-filter         # disable keyword filter
    python scout2_fetcher_v3.py --out morning_run   # custom output base name
    python scout2_fetcher_v3.py --save-xml          # save raw XML per feed
    python scout2_fetcher_v3.py --quiet             # suppress progress output
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# ── Dependency check ───────────────────────────────────────────────────────────
try:
    import feedparser
except ImportError:
    sys.exit("\n[ERROR] pip install feedparser\n")

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    sys.exit("\n[ERROR] pip install requests\n")


# ══════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════

VERSION      = "4.0"
SYSTEM_NAME  = "Scout-2 / Investing with SPACE"

QR_NO_DATE        = "no_publish_date"
QR_FUTURE_DATE    = "future_date"
QR_STALE          = "stale_beyond_window"
QR_KEYWORD_MISS   = "keyword_filter_miss"
QR_EMPTY_TITLE    = "empty_title"
QR_DUPLICATE      = "duplicate"

# Alert event keywords — triggers alert classification
ALERT_KEYWORDS = {
    "contract": [
        "contract", "award", "awarded", "task order", "idiq",
        "firm fixed price", "ffp", "indefinite delivery", "ota",
        "other transaction", "procurement", "sole source"
    ],
    "earnings": [
        "earnings", "revenue", "quarterly", "q1", "q2", "q3", "q4",
        "annual report", "guidance", "backlog", "beat", "miss",
        "profit", "loss", "ebitda", "margin"
    ],
    "funding": [
        "funding", "raises", "raised", "series a", "series b", "series c",
        "seed round", "investment", "venture", "million", "billion",
        "valuation", "unicorn", "capital"
    ],
    "ipo": [
        "ipo", "initial public offering", "spac", "goes public",
        "public markets", "s-1", "listing", "nasdaq", "nyse", "stock"
    ],
    "acquisition": [
        "acquires", "acquisition", "merger", "acquired", "takeover",
        "buys", "purchase", "deal", "m&a"
    ],
    "defense_award": [
        "space force", "ussf", "darpa", "pentagon", "dod", "nro",
        "missile defense", "golden dome", "sda", "space domain",
        "classified contract", "defense contract", "military contract"
    ]
}

# Urgency scoring weights
URGENCY_WEIGHTS = {
    "contract":      3,
    "earnings":      3,
    "ipo":           3,
    "acquisition":   3,
    "defense_award": 3,
    "funding":       2,
}


# ══════════════════════════════════════════════════════════════════════
#  FEED LIST
# ══════════════════════════════════════════════════════════════════════

FEEDS = [
    # ── Core Space Industry ───────────────────────────────────────
    {"url": "https://spacenews.com/feed/",
     "label": "SpaceNews",              "category": "Space Industry"},

    {"url": "https://payloadspace.com/feed/",
     "label": "Payload Space",          "category": "Space Industry"},

    {"url": "https://www.space.com/feeds/all",
     "label": "Space.com",              "category": "Space Industry"},

    # ── Defense / SDA ─────────────────────────────────────────────
    {"url": "https://www.defensenews.com/arc/outboundfeeds/rss/",
     "label": "Defense News",           "category": "Defense/SDA"},

    {"url": "https://www.airandspaceforces.com/feed/",
     "label": "Air & Space Forces",     "category": "Defense/SDA"},

    {"url": "https://breakingdefense.com/feed/",
     "label": "Breaking Defense",       "category": "Defense/SDA"},

    # ── NASA / Government ─────────────────────────────────────────
    {"url": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
     "label": "NASA Breaking News",     "category": "NASA/Gov"},

    {"url": "https://www.nasa.gov/blogs/artemis/feed/",
     "label": "NASA Artemis Blog",      "category": "NASA/Gov"},

    {"url": "https://www.nasa.gov/blogs/commercialcrew/feed/",
     "label": "NASA Commercial Crew",   "category": "NASA/Gov"},

    # ── Satellite / Communications ────────────────────────────────
    {"url": "https://www.satellitetoday.com/feed/",
     "label": "Satellite Today",        "category": "Satellite/Comms"},

    {"url": "https://spacenews.com/tag/business/feed/",
     "label": "SpaceNews Business",     "category": "Satellite/Comms"},

    # ── Business / Markets ────────────────────────────────────────
    {"url": "https://www.defenseone.com/rss/all/",
     "label": "Defense One",            "category": "Business/Markets"},

    {"url": "https://finance.yahoo.com/news/rssindex",
     "label": "Yahoo Finance",          "category": "Business/Markets"},

    # ── Aerospace / Industrial Suppliers ──────────────────────────
    {"url": "https://www.aerospacetestinginternational.com/feed",
     "label": "Aerospace Testing Intl", "category": "Aerospace/Suppliers"},

    {"url": "https://theaviationist.com/feed",
     "label": "The Aviationist",        "category": "Aerospace/Suppliers"},

    # ── Technology / AI / Data Center ─────────────────────────────
    {"url": "https://www.datacenterdynamics.com/en/rss/",
     "label": "Data Center Dynamics",   "category": "Tech/AI/Compute"},

    {"url": "https://www.semianalysis.com/feed",
     "label": "SemiAnalysis",           "category": "Tech/AI/Compute"},
]


# ══════════════════════════════════════════════════════════════════════
#  KEYWORD FILTER
# ══════════════════════════════════════════════════════════════════════

KEYWORDS = {
    "launch", "rocket", "liftoff", "reusability", "reusable",
    "falcon 9", "falcon heavy", "starship", "vulcan", "atlas v",
    "new glenn", "new shepard", "electron", "neutron", "ariane",
    "vega", "soyuz", "antares", "terran", "firefly alpha",
    "satellite", "constellation", "spacecraft", "payload",
    "bus", "propulsion", "thruster", "smallsat", "cubesat",
    "geostationary", "leo", "meo", "heo",
    "manufacturing", "assembly", "integration",
    "space domain awareness", "sda", "space force", "ussf",
    "space command", "spacecom", "smdc", "darpa", "nro", "nga",
    "missile", "hypersonic", "hypersonics", "directed energy",
    "electronic warfare", "gps", "sbirs", "opir", "dod",
    "pentagon", "classified", "disa", "mda", "missile defense",
    "space fence", "geoint", "sigint", "isr",
    "nasa", "artemis", "lunar gateway", "orion", "sls",
    "space launch system", "commercial crew", "cots", "crs",
    "clps", "hls", "human landing system",
    "starlink", "direct-to-device", "d2d", "satcom",
    "leo broadband", "telesat", "ses ", "intelsat", "viasat",
    "globalstar", "iridium", "oneweb", "hughesnet", "echostar",
    "earth observation", "geospatial", "synthetic aperture",
    "hyperspectral", "remote sensing", "imagery", "planet labs",
    "maxar", "black sky", "umbra", "capella space", "iceye",
    "spire global",
    "artificial intelligence", "machine learning", "autonomy",
    "gpu", "compute", "inference", "semiconductor", "nvidia",
    "data center", "edge computing", "fpga", "asic",
    "rf testing", "anechoic", "electromagnetic", "emi", "emc",
    "vibration test", "thermal vacuum", "tvac", "qualification",
    "simulation", "digital twin", "ground test",
    "ground station", "earth station", "teleport",
    "in-orbit servicing", "refueling", "debris removal",
    "iss ", "cargo resupply", "space station", "orbital transfer",
    "nuclear", "fission", "kilopower", "solar array",
    "power system", "rare earth", "lithium", "tantalum",
    "quantum", "quantum communication", "quantum key",
    "quantum sensor", "quantum computing",
    "lunar", "cislunar", "mars", "deep space",
    "interplanetary", "heliocentric",
    "ipo", "spac", "funding round", "series a", "series b",
    "series c", "contract award", "task order", "indefinite delivery",
    "idiq", "firm fixed price", "other transaction authority",
    "ota contract", "earnings", "revenue guidance", "backlog",
    "merger", "acquisition",
    "spacex", "boeing", "lockheed martin", "northrop grumman",
    "raytheon", "l3harris", "aerojet rocketdyne", "aerojet",
    "rocket lab", "rocketlab", "relativity space",
    "intuitive machines", "redwire", "terran orbital",
    "momentus", "ast spacemobile", "axiom space",
    "sierra space", "blue origin", "virgin galactic", "spire",
    "voyager space", "leidos", "bae systems", "airbus defence",
    "thales alenia", "safran", "avio", "isro", "esa ",
}


# ══════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════

NOW_UTC = datetime.now(timezone.utc)


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    for ent, rep in [("&amp;","&"),("&lt;","<"),("&gt;",">"),
                     ("&quot;",'"'),("&apos;","'"),("&#39;","'")]:
        text = text.replace(ent, rep)
    text = re.sub(r"&#\d+;", "", text)
    return re.sub(r"\s+", " ", text).strip()


def make_fingerprint(title: str, url: str) -> str:
    key = f"{title.lower().strip()}|{url.strip()}"
    return hashlib.md5(key.encode()).hexdigest()


def parse_date(entry) -> Optional[datetime]:
    for attr in ("published_parsed", "updated_parsed"):
        tup = getattr(entry, attr, None)
        if tup:
            try:
                return datetime(*tup[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            for fmt in (
                "%a, %d %b %Y %H:%M:%S %z",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
            ):
                try:
                    dt = datetime.strptime(raw.strip(), fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    pass
    return None


def get_guid(entry) -> Optional[str]:
    for attr in ("id", "guid", "eid"):
        val = getattr(entry, attr, None)
        if val and isinstance(val, str):
            return val.strip()
    return None


def is_relevant(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in KEYWORDS)


def validate_date(pub_dt: Optional[datetime], window_hours: int) -> tuple:
    if pub_dt is None:
        return False, QR_NO_DATE
    age = NOW_UTC - pub_dt
    if age.total_seconds() < 0:
        return False, QR_FUTURE_DATE
    if age > timedelta(hours=window_hours):
        return False, QR_STALE
    return True, None


def make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://",  adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": (
            "Scout2-RSS-Fetcher/4.0 (Investing with SPACE; "
            "non-commercial research aggregator)"
        ),
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    })
    return session


# ══════════════════════════════════════════════════════════════════════
#  ALERT CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════

def classify_alert(item: dict) -> Optional[dict]:
    """
    Check if item qualifies as a high-signal alert.
    Returns alert dict if it qualifies, None otherwise.
    """
    combined = f"{item['title']} {item['summary']}".lower()
    matched_types = []
    score = 0

    for event_type, keywords in ALERT_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            matched_types.append(event_type)
            score += URGENCY_WEIGHTS.get(event_type, 1)

    if not matched_types:
        return None

    # Determine urgency based on score and age
    age_hours = item.get("age_hours") or 999
    if score >= 6 or (score >= 3 and age_hours <= 6):
        urgency = "immediate"
    elif score >= 3 or age_hours <= 24:
        urgency = "same_day"
    else:
        urgency = "watch"

    alert = dict(item)
    alert["alert_types"]  = matched_types
    alert["alert_score"]  = score
    alert["urgency"]      = urgency
    return alert


# ══════════════════════════════════════════════════════════════════════
#  FEED FETCHER
# ══════════════════════════════════════════════════════════════════════

def fetch_feed(
    feed_cfg:       dict,
    session:        requests.Session,
    max_items:      int,
    window_hours:   int,
    keyword_filter: bool,
    save_xml_dir:   Optional[Path],
    quiet:          bool,
) -> tuple:
    url      = feed_cfg["url"]
    label    = feed_cfg["label"]
    category = feed_cfg["category"]
    retrieved_at = NOW_UTC.strftime("%Y-%m-%dT%H:%M:%SZ")

    live_items   = []
    quarantined  = []
    http_status  = None
    fetch_mode   = "live"
    error_msg    = None
    raw_bytes    = b""

    try:
        resp        = session.get(url, timeout=15)
        http_status = resp.status_code
        resp.raise_for_status()
        raw_bytes   = resp.content

        if save_xml_dir:
            save_xml_dir.mkdir(parents=True, exist_ok=True)
            safe_name = re.sub(r"[^\w\-]", "_", label) + ".xml"
            (save_xml_dir / safe_name).write_bytes(raw_bytes)

        parsed  = feedparser.parse(raw_bytes)
        entries = parsed.entries[:max_items] if max_items else parsed.entries

        if parsed.bozo and not entries:
            raise ValueError(f"Feed parse error: {parsed.bozo_exception}")

    except requests.exceptions.Timeout:
        error_msg   = "Timeout (15s)"
        http_status = http_status or 0
    except requests.exceptions.ConnectionError as e:
        error_msg   = f"Connection error: {str(e)[:120]}"
        http_status = 0
    except requests.exceptions.HTTPError as e:
        error_msg   = f"HTTP {e.response.status_code}"
        http_status = e.response.status_code
    except Exception as e:
        error_msg   = str(e)[:200]
        http_status = http_status or 0

    feed_log = {
        "feed_label":        label,
        "category":          category,
        "url":               url,
        "fetch_mode":        fetch_mode,
        "http_status":       http_status,
        "retrieved_at_utc":  retrieved_at,
        "items_parsed":      0,
        "items_live":        0,
        "items_quarantined": 0,
        "error":             error_msg,
        "xml_saved":         str(save_xml_dir / (re.sub(r"[^\w\-]","_",label)+".xml"))
                             if save_xml_dir and not error_msg else None,
    }

    if error_msg:
        if not quiet:
            print(f"  ✗ [{category}] {label:<30} {error_msg}", file=sys.stderr)
        return [], [], feed_log

    for entry in entries:
        title   = strip_html(entry.get("title",   "")).strip()
        link    = entry.get("link",    "").strip()
        raw_sum = entry.get("summary", entry.get("description", ""))
        summary = strip_html(raw_sum)[:700]
        guid    = get_guid(entry)
        pub_dt  = parse_date(entry)

        passes, q_reason = validate_date(pub_dt, window_hours)

        pub_utc_str = pub_dt.strftime("%Y-%m-%dT%H:%M:%SZ") if pub_dt else None
        age_hours   = round((NOW_UTC - pub_dt).total_seconds() / 3600, 1) if pub_dt else None

        date_warning = None
        if pub_dt:
            if (pub_dt - NOW_UTC).total_seconds() > 0:
                date_warning = f"FUTURE_DATE: published {pub_utc_str}"
            elif age_hours and age_hours > (window_hours * 2):
                date_warning = f"VERY_STALE: {age_hours}h old"

        if not title:
            q_reason = QR_EMPTY_TITLE
            passes   = False

        combined = f"{title} {summary}"
        if passes and keyword_filter and not is_relevant(combined):
            q_reason = QR_KEYWORD_MISS
            passes   = False

        item = {
            "fetch_mode":       fetch_mode,
            "http_status":      http_status,
            "retrieved_at_utc": retrieved_at,
            "raw_feed_guid":    guid,
            "feed_label":       label,
            "category":         category,
            "source_url":       url,
            "title":            title,
            "link":             link,
            "summary":          summary,
            "published_utc":    pub_utc_str,
            "published_display":pub_dt.strftime("%Y-%m-%d %H:%M UTC") if pub_dt else "UNKNOWN",
            "age_hours":        age_hours,
            "date_warning":     date_warning,
            "_fingerprint":     make_fingerprint(title, link),
        }

        if passes:
            live_items.append(item)
        else:
            item["quarantine_reason"] = q_reason
            quarantined.append(item)

    feed_log["items_parsed"]      = len(entries)
    feed_log["items_live"]        = len(live_items)
    feed_log["items_quarantined"] = len(quarantined)

    if not quiet:
        status = (f"✓ {len(live_items)} live  "
                  f"| {len(quarantined)} quarantined  "
                  f"| HTTP {http_status}")
        print(f"  [{category}] {label:<30} {status}", file=sys.stderr)

    return live_items, quarantined, feed_log


# ══════════════════════════════════════════════════════════════════════
#  DEDUPLICATION
# ══════════════════════════════════════════════════════════════════════

def deduplicate(items: list, quarantine: list) -> tuple:
    seen   = set()
    unique = []
    dupes  = 0
    for item in items:
        fp = item["_fingerprint"]
        if fp not in seen:
            seen.add(fp)
            unique.append(item)
        else:
            item["quarantine_reason"] = QR_DUPLICATE
            quarantine.append(item)
            dupes += 1
    return unique, quarantine, dupes


# ══════════════════════════════════════════════════════════════════════
#  CLEAN FOR EXPORT
# ══════════════════════════════════════════════════════════════════════

INTERNAL_FIELDS = {"_fingerprint"}

def clean(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in INTERNAL_FIELDS}


# ══════════════════════════════════════════════════════════════════════
#  RUN HISTORY
# ══════════════════════════════════════════════════════════════════════

def update_run_history(history_path: Path, run_entry: dict, max_entries: int = 30):
    """Append this run to the run history file, keep last max_entries."""
    history = []
    if history_path.exists():
        try:
            existing = json.loads(history_path.read_text(encoding="utf-8"))
            history  = existing.get("runs", [])
        except Exception:
            history = []

    history.append(run_entry)
    history = history[-max_entries:]  # keep last 30 runs

    history_path.write_text(
        json.dumps({"runs": history}, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


# ══════════════════════════════════════════════════════════════════════
#  TEXT BLOCK FORMATTER
# ══════════════════════════════════════════════════════════════════════

def format_text_block(live_items, quarantine, run_ts, stats, window_hours):
    lines = []
    SEP   = "═" * 74
    DIV   = "─" * 74

    lines += [
        SEP,
        "  SCOUT-2 LIVE FEED DUMP  |  Investing with SPACE System  v4.0",
        f"  Run timestamp  : {run_ts}",
        f"  Freshness window : last {window_hours}h",
        f"  Feeds attempted : {stats['feeds_attempted']}  (failed: {stats['feeds_failed']})",
        f"  LIVE items      : {stats['items_final']}",
        f"  ALERTS          : {stats['alerts_count']}",
        f"  QUARANTINED     : {stats['items_quarantined']}",
        SEP,
        "",
        "PASTE EVERYTHING BELOW THIS LINE INTO SCOUT-2",
        "",
    ]

    for i, item in enumerate(live_items, 1):
        warn = f"  ⚠ {item['date_warning']}" if item.get("date_warning") else ""
        lines += [
            f"[{i:03d}] ── {item['category']} ── {item['published_display']}"
            f"  (age: {item['age_hours']}h){warn}",
            f"HEADLINE : {item['title']}",
            f"SOURCE   : {item['feed_label']}",
            f"LINK     : {item['link']}",
        ]
        if item["summary"]:
            lines.append(textwrap.fill(
                item["summary"], width=78,
                initial_indent="SUMMARY  : ",
                subsequent_indent="           ",
            ))
        lines.append(DIV)

    lines.append(f"\n[END OF LIVE DUMP — {len(live_items)} items]")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
#  JSON OUTPUT BUILDERS
# ══════════════════════════════════════════════════════════════════════

def build_main_json(live_items, quarantined, feed_logs, run_ts, stats, window_hours, args_dict):
    return {
        "meta": {
            "system":                 SYSTEM_NAME,
            "version":                VERSION,
            "run_timestamp_utc":      run_ts,
            "freshness_window_hours": window_hours,
            "cutoff_utc":             (NOW_UTC - timedelta(hours=window_hours)
                                      ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fetch_mode_global":      "live",
            "keyword_filter":         args_dict.get("keyword_filter", True),
            "max_per_feed":           args_dict.get("max_per_feed", 30),
            "feeds_attempted":        stats["feeds_attempted"],
            "feeds_failed":           stats["feeds_failed"],
            "items_raw_parsed":       stats["items_raw"],
            "items_live":             stats["items_live"],
            "items_after_dedup":      stats["items_final"],
            "items_quarantined":      stats["items_quarantined"],
            "alerts_count":           stats["alerts_count"],
        },
        "feed_log":         feed_logs,
        "items":            [clean(i) for i in live_items],
        "quarantine_items": [clean(q) for q in quarantined],
    }


def build_alerts_json(alerts, run_ts):
    """Build the high-signal alerts output file."""
    immediate = [a for a in alerts if a["urgency"] == "immediate"]
    same_day  = [a for a in alerts if a["urgency"] == "same_day"]
    watch     = [a for a in alerts if a["urgency"] == "watch"]

    return {
        "meta": {
            "system":            SYSTEM_NAME,
            "version":           VERSION,
            "run_timestamp_utc": run_ts,
            "total_alerts":      len(alerts),
            "immediate_count":   len(immediate),
            "same_day_count":    len(same_day),
            "watch_count":       len(watch),
            "description":       (
                "High-signal items only: contracts, earnings, funding, "
                "IPO signals, defense awards, acquisitions. "
                "urgency: immediate=act now, same_day=review today, watch=monitor"
            ),
        },
        "immediate": [clean(a) for a in immediate],
        "same_day":  [clean(a) for a in same_day],
        "watch":     [clean(a) for a in watch],
    }


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(
        description="Scout-2 RSS Fetcher v4.0 — Investing with SPACE System",
    )
    ap.add_argument("--out",       default="scout2_dump",
        help="Output filename base (default: scout2_dump)")
    ap.add_argument("--days",      type=int, default=3,
        help="Freshness window in days (default: 3 = 72h)")
    ap.add_argument("--max",       type=int, default=30,
        help="Max items to parse per feed (default: 30)")
    ap.add_argument("--no-filter", action="store_true",
        help="Disable keyword filter")
    ap.add_argument("--save-xml",  action="store_true",
        help="Save raw RSS XML per feed into ./xml_audit/")
    ap.add_argument("--quiet",     action="store_true",
        help="Suppress per-feed progress output")
    args = ap.parse_args()

    window_hours   = args.days * 24
    keyword_filter = not args.no_filter
    run_ts         = NOW_UTC.strftime("%Y-%m-%dT%H:%M:%SZ")
    run_ts_file    = NOW_UTC.strftime("%Y%m%d_%H%M")
    xml_audit_dir  = Path("xml_audit") if args.save_xml else None

    # ── Output paths ──────────────────────────────────────────────
    data_dir    = Path("data")
    archive_dir = Path("archive")
    data_dir.mkdir(exist_ok=True)
    archive_dir.mkdir(exist_ok=True)

    if not args.quiet:
        print("\n╔════════════════════════════════════════════════════╗", file=sys.stderr)
        print("║  Scout-2 RSS Fetcher v4.0  |  Investing with SPACE  ║", file=sys.stderr)
        print("╚════════════════════════════════════════════════════╝", file=sys.stderr)
        print(f"  Run timestamp  : {run_ts}", file=sys.stderr)
        print(f"  Freshness      : last {window_hours}h  (--days {args.days})", file=sys.stderr)
        print(f"  Feeds          : {len(FEEDS)}", file=sys.stderr)
        print(f"  Keyword filter : {'ON' if keyword_filter else 'OFF'}", file=sys.stderr)
        print("", file=sys.stderr)

    # ── Fetch all feeds ───────────────────────────────────────────
    session         = make_session()
    all_live        = []
    all_quarantined = []
    feed_logs       = []

    for feed_cfg in FEEDS:
        live, quar, log = fetch_feed(
            feed_cfg, session, args.max,
            window_hours, keyword_filter, xml_audit_dir, args.quiet
        )
        all_live.extend(live)
        all_quarantined.extend(quar)
        feed_logs.append(log)

    # ── Deduplicate ───────────────────────────────────────────────
    unique_live, all_quarantined, n_dupes = deduplicate(all_live, all_quarantined)

    # ── Sort newest first ─────────────────────────────────────────
    unique_live.sort(
        key=lambda x: x.get("published_utc") or "0000",
        reverse=True,
    )

    # ── Classify alerts ───────────────────────────────────────────
    alerts = []
    for item in unique_live:
        alert = classify_alert(item)
        if alert:
            alerts.append(alert)

    # Sort alerts: immediate first, then by score desc
    urgency_order = {"immediate": 0, "same_day": 1, "watch": 2}
    alerts.sort(key=lambda a: (urgency_order.get(a["urgency"], 9), -a.get("alert_score", 0)))

    stats = {
        "feeds_attempted":  len(FEEDS),
        "feeds_failed":     sum(1 for l in feed_logs if l["error"]),
        "items_raw":        sum(l["items_parsed"] for l in feed_logs),
        "items_live":       len(all_live),
        "items_final":      len(unique_live),
        "items_quarantined":len(all_quarantined),
        "alerts_count":     len(alerts),
    }

    # ── Build JSON structures ─────────────────────────────────────
    main_json   = build_main_json(
        unique_live, all_quarantined, feed_logs,
        run_ts, stats, window_hours,
        {"keyword_filter": keyword_filter, "max_per_feed": args.max},
    )
    alerts_json = build_alerts_json(alerts, run_ts)
    txt_data    = format_text_block(unique_live, all_quarantined, run_ts, stats, window_hours)

    json_str    = json.dumps(main_json,   indent=2, ensure_ascii=False)
    alerts_str  = json.dumps(alerts_json, indent=2, ensure_ascii=False)

    # ── Write root-level files (for backward compat) ──────────────
    Path(f"{args.out}.json").write_text(json_str,   encoding="utf-8")
    # txt write skipped - data folder used instead

    # ── Write data/ folder files (for dashboard) ──────────────────
    (data_dir / "scout2_dump_latest.json").write_text(json_str,   encoding="utf-8")
    (data_dir / "scout2_alerts.json").write_text(alerts_str,      encoding="utf-8")

    # ── Write archive/ timestamped file ───────────────────────────
    archive_path = archive_dir / f"scout2_dump_{run_ts_file}.json"
    archive_path.write_text(json_str, encoding="utf-8")

    # ── Update run history ────────────────────────────────────────
    history_path = data_dir / "scout2_run_history.json"
    run_entry = {
        "run_timestamp_utc": run_ts,
        "feeds_attempted":   stats["feeds_attempted"],
        "feeds_failed":      stats["feeds_failed"],
        "items_live":        stats["items_final"],
        "alerts_count":      stats["alerts_count"],
        "items_quarantined": stats["items_quarantined"],
        "archive_file":      f"archive/scout2_dump_{run_ts_file}.json",
    }
    update_run_history(history_path, run_entry)

    # ── Summary ───────────────────────────────────────────────────
    if not args.quiet:
        print(f"\n{'─'*56}", file=sys.stderr)
        print(f"  Feeds attempted  : {stats['feeds_attempted']}", file=sys.stderr)
        print(f"  Feeds failed     : {stats['feeds_failed']}", file=sys.stderr)
        print(f"  Raw items parsed : {stats['items_raw']}", file=sys.stderr)
        print(f"  ✅ LIVE items    : {stats['items_final']}", file=sys.stderr)
        print(f"  🚨 ALERTS        : {stats['alerts_count']}", file=sys.stderr)
        print(f"  🔒 Quarantined   : {stats['items_quarantined']}", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"  ✓ scout2_dump.json", file=sys.stderr)
        print(f"  ✓ scout2_dump.txt", file=sys.stderr)
        print(f"  ✓ data/scout2_dump_latest.json", file=sys.stderr)
        print(f"  ✓ data/scout2_alerts.json", file=sys.stderr)
        print(f"  ✓ data/scout2_run_history.json", file=sys.stderr)
        print(f"  ✓ archive/scout2_dump_{run_ts_file}.json", file=sys.stderr)
        print(f"{'─'*56}\n", file=sys.stderr)


if __name__ == "__main__":
    main()
