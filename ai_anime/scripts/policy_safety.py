from __future__ import annotations

import re


POLICY_SAFE_NOTE = (
    "Safe animated music-video performance scene with concert-only props, "
    "decorative costume details, non-violent staging, and no realistic harm imagery."
)

_SAFETY_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("human remains", "empty traces of absence"),
    ("body remains", "empty traces of absence"),
    ("corpse", "abandoned silhouette motif"),
    ("dead body", "fallen shadow motif"),
    ("blood", "red stage light"),
    ("bloody", "red-lit"),
    ("gore", "graphic intensity"),
    ("gory", "graphic-looking"),
    ("violence", "dramatic tension"),
    ("violent", "high-contrast"),
    ("weapon", "stage prop"),
    ("weapons", "stage props"),
    ("knife", "reflective stage prop"),
    ("knives", "reflective stage props"),
    ("gun", "spotlight rig"),
    ("guns", "spotlight rigs"),
    ("dangerous", "high-tension"),
    ("restraint", "controlled musical poise"),
    ("restrained", "controlled"),
    ("emotionally restrained", "emotionally controlled"),
    ("tied to the vocal phrase", "synced to the vocal phrase"),
    ("tied to", "synced to"),
    ("tied around", "worn as a decorative cord around"),
    ("bound", "framed by stage light"),
    ("tied up", "visually gathered"),
    ("chain", "decorative metallic strap"),
    ("chains", "decorative metallic straps"),
    ("spike", "rounded metallic accent"),
    ("spikes", "rounded metallic accents"),
    ("rib cage", "chest area"),
    ("skeletal hand", "stylized hand"),
    ("skeletal fingers", "stylized fingers"),
    ("skeletal wrist", "stylized wrist"),
    ("screams aggressively", "sings with high-energy rock intensity"),
    ("screaming into", "singing into"),
    ("headbanging", "rhythmic concert movement"),
)

POLICY_RISK_TERMS: tuple[str, ...] = (
    "human remains",
    "body remains",
    "corpse",
    "dead body",
    "blood",
    "bloody",
    "gore",
    "gory",
    "violence",
    "violent",
    "weapon",
    "weapons",
    "knife",
    "knives",
    "gun",
    "guns",
    "dangerous",
    "restraint",
    "restrained",
    "emotionally restrained",
    "tied to",
    "tied around",
    "tied up",
    "bound",
    "chain",
    "chains",
    "spike",
    "spikes",
    "rib cage",
    "skeletal hand",
    "skeletal fingers",
    "skeletal wrist",
    "screams aggressively",
    "screaming into",
    "headbanging",
)


def safety_normalize_prompt(text: str) -> str:
    """Normalize policy-sensitive wording while preserving the anime MV intent."""
    if not text:
        return text
    result = text
    for source, target in _SAFETY_REPLACEMENTS:
        pattern = r"(?<![a-z0-9-])" + re.escape(source) + r"(?![a-z0-9-])"
        result = re.sub(pattern, target, result, flags=re.IGNORECASE)
    # Preserve markdown structure; only compact horizontal whitespace.
    result = re.sub(r"[ \t]+", " ", result)
    result = re.sub(r" *\n *", "\n", result)
    return result.strip()


def policy_risk_hits(text: str) -> list[str]:
    hits: list[str] = []
    for term in POLICY_RISK_TERMS:
        pattern = r"(?<![a-z0-9-])" + re.escape(term) + r"(?![a-z0-9-])"
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(term)
    return hits


def append_policy_safe_note(text: str) -> str:
    normalized = safety_normalize_prompt(text)
    if POLICY_SAFE_NOTE.casefold() in normalized.casefold():
        return normalized
    return f"{normalized} {POLICY_SAFE_NOTE}"


def safety_normalize_data(value):
    """Recursively normalize strings in generated JSON-like prompt payloads."""
    if isinstance(value, str):
        return safety_normalize_prompt(value)
    if isinstance(value, list):
        return [safety_normalize_data(item) for item in value]
    if isinstance(value, dict):
        return {key: safety_normalize_data(item) for key, item in value.items()}
    return value
