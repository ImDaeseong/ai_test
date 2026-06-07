from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from common import PROJECT_ROOT, load_config


HISTORY_FILE  = PROJECT_ROOT / "data" / "suno_history.jsonl"
GENRES_FILE   = PROJECT_ROOT / "configs" / "genres.json"
ATMOS_FILE    = PROJECT_ROOT / "configs" / "atmosphere_rules.json"
BACKUP_DIR    = PROJECT_ROOT / "data" / "config_backups"
PROFILE_CANDIDATES_FILE = PROJECT_ROOT / "data" / "new_profile_candidates.json"
_LEARNING_CONFIG = load_config("learning_rules")
DEFAULT_MIN_FREQ = int(_LEARNING_CONFIG.get("default_min_freq", 2))

# Connector words that appear as tag prefixes after comma-splitting
_STRIP_PREFIX = re.compile(
    _LEARNING_CONFIG.get("strip_prefix_pattern", r"^(and|plus|or|with|a|an|the)\s+"),
    re.I,
)
# Tags that are recording/production specs rather than genre/style identifiers
_PRODUCTION_RE = re.compile(
    _LEARNING_CONFIG.get("production_tag_pattern", r"\b(bpm|production|vocal|voice)\b"),
    re.I,
)
_NON_LEARNABLE_TAGS = {
    str(tag).lower()
    for tag in _LEARNING_CONFIG.get("non_learnable_tags", [])
}
_MAX_PROFILE_CANDIDATES = int(_LEARNING_CONFIG.get("max_profile_candidates", 15))
_CANDIDATE_CO_TAGS = int(_LEARNING_CONFIG.get("candidate_co_tags", 8))
_NEW_PROFILE_ACTION = _LEARNING_CONFIG.get(
    "new_profile_candidate_action",
    "review as a possible new genre profile",
)


# ---------------------------------------------------------------------------
# History I/O
# ---------------------------------------------------------------------------

def load_history() -> list[dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []
    entries: list[dict[str, Any]] = []
    with open(HISTORY_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def content_fingerprint(entry: dict[str, Any]) -> str:
    """Stable content-based key: SHA256(title + raw_tags[:200]).
    Used when neither URL nor audio_hash is available (e.g. generate_storyboard entries).
    """
    title = (entry.get("title") or "").strip().lower()
    tags  = (entry.get("raw_tags") or entry.get("tags") or "").strip().lower()
    raw   = f"{title}|{tags[:200]}"
    return "fp:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def composite_key(entry: dict[str, Any]) -> str:
    """3-tier unique key:
    1. url        — Suno-generated URL (strongest identity)
    2. audio_hash — SHA256 of uploaded audio bytes (local MP3/WAV)
    3. content_fp — title + tags fingerprint (fallback)
    """
    url = (entry.get("url") or "").strip()
    if url:
        return url
    audio_hash = (entry.get("audio_hash") or "").strip()
    if audio_hash:
        return "audio:" + audio_hash
    return content_fingerprint(entry)


def dedupe_composite(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate entries using composite_key; keep the most-recent per key."""
    seen: dict[str, dict[str, Any]] = {}
    for entry in entries:
        key = composite_key(entry)
        if key not in seen or entry.get("timestamp", "") > seen[key].get("timestamp", ""):
            seen[key] = entry
    return list(seen.values())


# kept for backward compatibility — callers inside this module now use dedupe_composite
def dedupe_by_url(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return dedupe_composite(entries)


# ---------------------------------------------------------------------------
# Tag extraction
# ---------------------------------------------------------------------------

def is_genre_tag(tag: str) -> bool:
    """True if the tag looks like a genre/style keyword, not a production spec."""
    tag = tag.strip()
    normalized = re.sub(r"\s+", " ", tag.lower())
    if len(tag) < 2:
        return False
    if len(tag.split()) > 4:
        return False
    if re.match(r"^\d+(\.\d+)?$", tag):
        return False
    if normalized in _NON_LEARNABLE_TAGS:
        return False
    if _PRODUCTION_RE.search(tag):
        return False
    return True


def tags_from_entry(entry: dict[str, Any]) -> list[str]:
    """Extract valid genre/style tags from one history entry.

    Supports both history formats:
      - new: cleaned_tags (list) + raw_tags (str)
      - legacy: tags (str) + lyrics (str)
    """
    raw_list = entry.get("cleaned_tags")
    if isinstance(raw_list, list) and raw_list:
        return [t.lower() for t in raw_list if is_genre_tag(t)]
    # Fall back to raw_tags → tags (either format)
    raw = entry.get("raw_tags") or entry.get("tags", "")
    if not raw:
        return []
    parts = [_STRIP_PREFIX.sub("", p.strip().lower()) for p in re.split(r"[,;]", raw) if p.strip()]
    return [t.rstrip(".,!?").strip() for t in parts if is_genre_tag(_STRIP_PREFIX.sub("", t))]


# ---------------------------------------------------------------------------
# Genre learning
# ---------------------------------------------------------------------------

def all_existing_keys(profiles: list[dict[str, Any]]) -> set[str]:
    return {k.lower() for p in profiles for k in p.get("keys", [])}


def tag_entry_freq(entries: list[dict[str, Any]]) -> Counter:
    """Count how many *unique* entries each tag appears in."""
    freq: Counter = Counter()
    for entry in entries:
        for tag in set(tags_from_entry(entry)):
            freq[tag] += 1
    return freq


def _key_in_text(key: str, text: str) -> bool:
    """Word-boundary check: is `key` a whole-word substring of `text`?"""
    try:
        return bool(_WB.sub("", text) != text if False else
                    re.search(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])", text))
    except re.error:
        return key in text


def _direct_score(tag: str, profile: dict[str, Any]) -> int:
    """Count how many of the profile's keys appear (word-boundary) inside `tag`."""
    return sum(1 for k in profile.get("keys", []) if _key_in_text(k.lower(), tag))


def _cooccurrence_score(
    tag: str,
    entries: list[dict[str, Any]],
    profile: dict[str, Any],
) -> int:
    """For entries that contain `tag`, count co-occurring tags that overlap with profile keys."""
    pkeys = {k.lower() for k in profile.get("keys", [])}
    score = 0
    for entry in entries:
        entry_tags = set(tags_from_entry(entry))
        if tag in entry_tags:
            for et in entry_tags:
                if et != tag and any(_key_in_text(pk, et) for pk in pkeys):
                    score += 1
    return score


def best_profile_for_tag(
    tag: str,
    entries: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Two-stage assignment:
    1. Direct: profile keys that appear word-boundary inside the candidate tag.
    2. Co-occurrence: tags that appear alongside candidate share profile keys.
    """
    # Stage 1 — direct key-in-tag
    best_direct, best_direct_score = None, 0
    for profile in profiles:
        s = _direct_score(tag, profile)
        if s > best_direct_score:
            best_direct_score, best_direct = s, profile
    if best_direct:
        return best_direct

    # Stage 2 — co-occurrence with substring-aware matching
    best_cooc, best_cooc_score = None, 0
    for profile in profiles:
        s = _cooccurrence_score(tag, entries, profile)
        if s > best_cooc_score:
            best_cooc_score, best_cooc = s, profile
    return best_cooc if best_cooc_score > 0 else None


def compute_genre_updates(
    entries: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
    min_freq: int,
) -> dict[str, list[str]]:
    """
    Returns {profile_name: [new keys to add]}.
    Only tags that are absent from all profiles AND appear >= min_freq times.
    """
    existing = all_existing_keys(profiles)
    freq = tag_entry_freq(entries)
    updates: dict[str, list[str]] = defaultdict(list)

    for tag, count in sorted(freq.items(), key=lambda x: -x[1]):
        if count < min_freq:
            continue
        if tag in existing:
            continue
        profile = best_profile_for_tag(tag, entries, profiles)
        if profile:
            updates[profile["name"]].append(tag)

    return dict(updates)


def compute_new_profile_candidates(
    entries: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
    min_freq: int,
) -> list[dict[str, Any]]:
    """Report frequent learnable tags that do not clearly belong to an existing profile."""
    existing = all_existing_keys(profiles)
    freq = tag_entry_freq(entries)
    candidates: list[dict[str, Any]] = []
    for tag, count in sorted(freq.items(), key=lambda x: (-x[1], x[0])):
        if count < min_freq or tag in existing:
            continue
        if best_profile_for_tag(tag, entries, profiles):
            continue
        co_tags: Counter = Counter()
        for entry in entries:
            entry_tags = set(tags_from_entry(entry))
            if tag in entry_tags:
                co_tags.update(t for t in entry_tags if t != tag and t not in existing)
        candidates.append(
            {
                "tag": tag,
                "count": count,
                "co_tags": [t for t, _ in co_tags.most_common(_CANDIDATE_CO_TAGS)],
                "suggested_action": _NEW_PROFILE_ACTION,
            }
        )
    return candidates


# ---------------------------------------------------------------------------
# BPM statistics
# ---------------------------------------------------------------------------

def extract_bpms(entries: list[dict[str, Any]]) -> list[int]:
    bpms = []
    for entry in entries:
        text = entry.get("raw_tags") or entry.get("tags", "")
        m = re.search(r"(\d{2,3})\s*BPM", text, re.I)
        if m:
            b = int(m.group(1))
            if 40 <= b <= 220:
                bpms.append(b)
    return sorted(bpms)


def bpm_stats(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    bpms = extract_bpms(entries)
    if not bpms:
        return None
    n = len(bpms)
    return {
        "count": n,
        "min": bpms[0],
        "max": bpms[-1],
        "median": bpms[n // 2],
        "mean": round(sum(bpms) / n, 1),
        "slow_le80":    sum(1 for b in bpms if b <= 80),
        "medium_81_119": sum(1 for b in bpms if 81 <= b <= 119),
        "fast_ge120":   sum(1 for b in bpms if b >= 120),
    }


# ---------------------------------------------------------------------------
# Atmosphere learning
# ---------------------------------------------------------------------------

def compute_atmosphere_updates(
    entries: list[dict[str, Any]],
    atmosphere: dict[str, Any],
    min_freq: int,
) -> dict[str, list[str]]:
    """
    Suggests new urban_keywords and season_keywords from history lyrics/tags.
    Returns {"urban_keywords": [...new...], "season_hints": [...new...]}
    """
    existing_urban = {k.lower() for k in atmosphere.get("urban_keywords", [])}
    season_candidate_map = {
        "summer": "summer nostalgia",
        "spring": "spring awakening",
        "winter": "winter stillness",
        "autumn": "autumn melancholy",
        "fall": "autumn melancholy",
        "rain": "rainy late spring night",
        "snow": "winter stillness",
    }
    existing_season_keys: set[str] = set()
    for rule in atmosphere.get("season_rules", []):
        existing_season_keys.update(k.lower() for k in rule.get("keys", []))

    urban_counter: Counter = Counter()
    season_counter: Counter = Counter()

    urban_candidates = [
        "downtown", "metro", "alley", "highway", "bridge", "station",
        "boulevard", "overpass", "crosswalk", "sidewalk", "corridor",
        "apartment", "skyscraper", "underpass",
    ]

    for entry in entries:
        combined = " ".join([
            entry.get("raw_tags") or entry.get("tags", ""),
            entry.get("lyrics_preview") or entry.get("lyrics", "")[:200],
        ]).lower()
        for word in urban_candidates:
            if word in combined and word not in existing_urban:
                urban_counter[word] += 1
        for word in season_candidate_map:
            if word in combined and word not in existing_season_keys:
                season_counter[word] += 1

    new_urban = [w for w, c in urban_counter.items() if c >= min_freq]
    new_season = {
        season_candidate_map[w]: [w]
        for w, c in season_counter.items()
        if c >= min_freq
    }

    result: dict[str, Any] = {}
    if new_urban:
        result["urban_keywords"] = new_urban
    if new_season:
        result["season_rules"] = new_season
    return result


# ---------------------------------------------------------------------------
# Apply updates + backup
# ---------------------------------------------------------------------------

_MAX_BACKUPS = 10


def _prune_old_backups() -> None:
    if not BACKUP_DIR.exists():
        return
    dirs = sorted((d for d in BACKUP_DIR.iterdir() if d.is_dir()), key=lambda p: p.name)
    for old in dirs[:-_MAX_BACKUPS]:
        shutil.rmtree(old, ignore_errors=True)


def backup_configs() -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUP_DIR / ts
    backup_path.mkdir(parents=True, exist_ok=True)
    for src in [GENRES_FILE, ATMOS_FILE]:
        if src.exists():
            shutil.copy2(src, backup_path / src.name)
    _prune_old_backups()
    return str(backup_path)


def apply_genre_updates(
    genre_updates: dict[str, list[str]],
    profiles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    updated = []
    for profile in profiles:
        new_keys = genre_updates.get(profile["name"], [])
        if new_keys:
            p = dict(profile)
            p["keys"] = list(profile["keys"]) + new_keys
            updated.append(p)
        else:
            updated.append(profile)
    return updated


def apply_atmosphere_updates(
    atmos_updates: dict[str, Any],
    atmosphere: dict[str, Any],
) -> dict[str, Any]:
    updated = dict(atmosphere)
    if "urban_keywords" in atmos_updates:
        updated["urban_keywords"] = list(
            dict.fromkeys(
                atmosphere.get("urban_keywords", []) + atmos_updates["urban_keywords"]
            )
        )
    if "season_rules" in atmos_updates:
        existing_rules = list(updated.get("season_rules", []))
        existing_season_keys = {k for r in existing_rules for k in r.get("keys", [])}
        for season_label, keys in atmos_updates["season_rules"].items():
            new_keys = [k for k in keys if k not in existing_season_keys]
            if new_keys:
                existing_rules.append({"keys": new_keys, "season": season_label})
        updated["season_rules"] = existing_rules
    return updated


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def write_profile_candidates(candidates: list[dict[str, Any]]) -> None:
    PROFILE_CANDIDATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_CANDIDATES_FILE.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run(
    min_freq: int = DEFAULT_MIN_FREQ,
    dry_run: bool = False,
    write_candidates: bool = False,
) -> dict[str, Any]:
    """
    Analyze suno_history.jsonl and optionally update configs.

    Returns a report dict with:
      - entries_analyzed
      - genre_updates:    {profile_name: [new keys]}
      - atmosphere_updates
      - bpm_stats
      - configs_changed
      - backup_path (if applied)
    """
    entries = load_history()
    if not entries:
        return {
            "status": "skipped",
            "reason": "data/suno_history.jsonl이 비어 있거나 존재하지 않습니다.",
            "entries_analyzed": 0,
        }

    entries = dedupe_composite(entries)
    profiles: list[dict[str, Any]] = json.loads(GENRES_FILE.read_text(encoding="utf-8"))
    atmosphere: dict[str, Any] = json.loads(ATMOS_FILE.read_text(encoding="utf-8"))

    genre_updates = compute_genre_updates(entries, profiles, min_freq)
    new_profile_candidates = compute_new_profile_candidates(entries, profiles, min_freq)
    atmos_updates = compute_atmosphere_updates(entries, atmosphere, min_freq)
    bstats = bpm_stats(entries)

    tag_freq = tag_entry_freq(entries)
    existing = all_existing_keys(profiles)
    top_new_tags = [
        {"tag": t, "count": c}
        for t, c in tag_freq.most_common(30)
        if t not in existing
    ]

    report: dict[str, Any] = {
        "status": "dry_run" if dry_run else "applied",
        "entries_analyzed": len(entries),
        "genre_updates": genre_updates,
        "new_profile_candidates": new_profile_candidates[:_MAX_PROFILE_CANDIDATES],
        "atmosphere_updates": atmos_updates,
        "bpm_stats": bstats,
        "top_new_tags": top_new_tags[:15],
        "configs_changed": [],
    }

    if not dry_run and (genre_updates or atmos_updates):
        backup_path = backup_configs()
        report["backup_path"] = backup_path

        if genre_updates:
            updated_profiles = apply_genre_updates(genre_updates, profiles)
            GENRES_FILE.write_text(
                json.dumps(updated_profiles, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            report["configs_changed"].append("configs/genres.json")

        if atmos_updates:
            updated_atmos = apply_atmosphere_updates(atmos_updates, atmosphere)
            ATMOS_FILE.write_text(
                json.dumps(updated_atmos, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            report["configs_changed"].append("configs/atmosphere_rules.json")

    if write_candidates:
        candidates_to_write = new_profile_candidates[:_MAX_PROFILE_CANDIDATES]
        write_profile_candidates(candidates_to_write)
        report["candidate_report_path"] = str(PROFILE_CANDIDATES_FILE)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Suno 이력을 분석하여 configs를 자동으로 업데이트합니다."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="분석만 하고 파일은 수정하지 않습니다.",
    )
    parser.add_argument(
        "--min-freq", type=int, default=DEFAULT_MIN_FREQ,
        help=f"config에 추가할 최소 등장 횟수 (기본값: {DEFAULT_MIN_FREQ})",
    )
    parser.add_argument(
        "--write-candidates", action="store_true",
        help="새 장르 프로필 후보를 data/new_profile_candidates.json에 기록합니다.",
    )
    args = parser.parse_args()
    report = run(
        min_freq=args.min_freq,
        dry_run=args.dry_run,
        write_candidates=args.write_candidates,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
