from __future__ import annotations

from typing import Any

import palette_engine as _pe
from common import _key_matches, load_config
from genre_selector import choose_genre_profile
from _song_helpers import _profile_value, _stable_choice, _with_color, song_character_seed

_CHAR_CONFIG = load_config("character_defaults")


# ---------------------------------------------------------------------------
# Character trait generation
# ---------------------------------------------------------------------------

def song_unique_traits(song: dict[str, Any], main_color: str) -> dict[str, str]:
    seed = song_character_seed(song)
    variants = _CHAR_CONFIG.get("song_unique_variants", {})
    title = song.get("title", "").strip()

    def pick(key: str) -> str:
        value = _stable_choice(variants.get(key, []), seed, key)
        return value.format(main_color=main_color, title=title)

    return {
        "archetype": pick("archetypes"),
        "face_shape": pick("face_shapes"),
        "hair_base": pick("hair_bases"),
        "face": pick("face_marks"),
        "hair": pick("hair_variants"),
        "body": pick("body_silhouettes"),
        "outfit_base": pick("outfit_bases"),
        "outfit": pick("outfit_accents"),
        "accessory": pick("accessories"),
        "gesture": pick("gesture_signatures"),
        "identity_lock": pick("identity_locks"),
    }


def infer_subject_profile(song: dict[str, Any], main_color: str) -> dict[str, Any]:
    """Infer whether the MV should center a person, pair/group, object, or environment."""
    positive_tags = [t for t in song.get("style_tags", []) if not t.lstrip().startswith(("‑", "-"))]
    text = " ".join(
        [
            song.get("title", ""),
            song.get("genre", ""),
            " ".join(positive_tags),
            " ".join(song.get("mood", [])),
            " ".join(song.get("instruments", [])),
            song.get("atmosphere", ""),
            " ".join(song.get("visual_cues", [])),
        ]
    ).lower()
    subject_rules = _CHAR_CONFIG.get("subject_rules", {})
    gender_rules = _CHAR_CONFIG.get("gender_presentation_rules", {})

    def rule_matches(rule: dict[str, Any]) -> bool:
        return any(_key_matches(str(k).lower(), text) for k in rule.get("keys", []))

    subject_type = "human_solo"
    subject_rule: dict[str, Any] = {}
    for candidate in ["human_duo", "group", "object_symbol", "environment_only"]:
        rule = subject_rules.get(candidate, {})
        if rule and rule_matches(rule):
            subject_type = candidate
            subject_rule = rule
            break

    male = rule_matches(gender_rules.get("male", {}))
    female = rule_matches(gender_rules.get("female", {}))
    androgynous = rule_matches(gender_rules.get("androgynous", {}))
    has_lead_vocal = any(
        _key_matches(k, text)
        for k in [
            "vocal",
            "vocals",
            "voice",
            "singer",
            "male vocal",
            "male vocals",
            "female vocal",
            "female vocals",
            "dry male vocals",
            "upfront vocal presence",
            "lead vocal",
        ]
    )
    full_instrumental = any(
        phrase in text
        for phrase in [
            "instrumental only",
            "no vocals",
            "no lead vocal",
            "piano only",
            "strings only",
        ]
    ) or text.strip() == "instrumental"
    if subject_type == "environment_only" and has_lead_vocal and not full_instrumental:
        subject_type = "human_solo"
        subject_rule = {}
    if subject_type in ("environment_only", "object_symbol"):
        gender = "non-human / symbolic"
    elif male and female:
        gender = "mixed-gender"
    elif female:
        gender = gender_rules.get("female", {}).get("description", "female-presenting")
    elif male:
        gender = gender_rules.get("male", {}).get("description", "male-presenting")
    elif androgynous:
        gender = gender_rules.get("androgynous", {}).get("description", "androgynous")
    else:
        gender = "androgynous"

    subject_label = {
        "human_solo": "one human lead character",
        "human_duo": "two human lead characters",
        "group": "small human ensemble with a center lead",
        "environment_only": "environment-led music video",
        "object_symbol": "symbolic object-led music video",
    }.get(subject_type, "one human lead character")

    subject_prop = _with_color(subject_rule.get("prop", ""), main_color)
    if subject_type == "object_symbol":
        if any(_key_matches(k, text) for k in ["perfume", "scent", "향기", "향"]):
            subject_prop = f"translucent perfume-like memory vial releasing {main_color} light and scent trails"
        elif any(_key_matches(k, text) for k in ["letter", "편지"]):
            subject_prop = f"folded handwritten letter glowing with {main_color} edges"
        elif any(_key_matches(k, text) for k in ["photo", "사진"]):
            subject_prop = f"old photo fragment carrying a soft {main_color} reflection"
        elif any(_key_matches(k, text) for k in ["ring", "반지"]):
            subject_prop = f"small ring catching a precise {main_color} rim light"

    return {
        "subject_type": subject_type,
        "subject_label": subject_label,
        "gender_presentation": gender,
        "identity_prefix": subject_rule.get("identity_prefix", ""),
        "identity": _with_color(subject_rule.get("identity", ""), main_color),
        "silhouette": _with_color(subject_rule.get("silhouette", ""), main_color),
        "prop": subject_prop,
        "reference_views": subject_rule.get("reference_views", []),
        "reference_note": subject_rule.get("reference_note", ""),
    }


# ---------------------------------------------------------------------------
# Protagonist builder
# ---------------------------------------------------------------------------

def create_protagonist(song: dict[str, Any], world: dict[str, Any]) -> dict[str, Any]:
    profile = choose_genre_profile(song)
    main_color = _pe.BRAND_PALETTE.get("main_color", "neon magenta")
    mood_words = ", ".join(song.get("mood", ["melancholic"]))
    seed = song_character_seed(song)
    profile_prop = _profile_value(profile, "prop", seed, "prop")
    motif = world.get("song_motif", profile_prop)
    colored_prop = _pe.apply_full_palette(profile_prop)
    unique = song_unique_traits(song, main_color)
    subject = infer_subject_profile(song, main_color)
    reference_character = world.get("genre_reference", {}).get("character_direction", "")

    if subject["subject_type"] in ("environment_only", "object_symbol"):
        subject_prop = subject.get("prop") or colored_prop
        reference_views = subject.get("reference_views") or [
            "main subject front reference",
            "main subject side/detail reference",
            "main subject in environment",
            "lighting and motif close-up",
        ]
        return {
            "role": "unique primary visual subject for this song",
            "subject_type": subject["subject_type"],
            "subject_label": subject["subject_label"],
            "gender_presentation": subject["gender_presentation"],
            "identity": subject.get("identity") or f"{subject['subject_label']} shaped by {world['genre_profile']}",
            "age_style": "non-human or environment-led anime MV subject, stylized and non-photorealistic",
            "hair": "",
            "outfit": "",
            "silhouette": subject.get("silhouette") or "clear non-human focal silhouette",
            "emotional_state": mood_words,
            "signature_prop": subject_prop,
            "accent_detail": (
                f"{_pe.BRAND_PALETTE['main_color']} remains dominant. The main visual focus is {subject['subject_label']}, "
                f"not a reusable human protagonist. This subject system belongs only to '{song.get('title', 'this song')}'"
            ),
            "consistency_rules": [
                f"Primary subject type: {subject['subject_type']} ({subject['subject_label']}).",
                "Do not introduce a full-body recurring lead human unless the scene explicitly needs a partial silhouette.",
                "Keep the same object/environment motif, palette, and spatial identity within this song only.",
                "Do not reuse another song's character face, hairstyle, outfit, or body silhouette.",
                "Use anime cinematic styling, never live-action realism.",
                "First generate Step 00 as the subject reference sheet before creating any scene image.",
                "Attach that same subject reference sheet when generating every scene image for this song.",
            ],
            "reference_workflow": [
                "Generate a clean song-specific subject reference sheet before scene production.",
                "Use the same subject reference sheet as an input/reference for every scene image prompt in this song.",
                "After each scene image is approved, use that scene image as the primary image-to-video input for that scene.",
            ],
            "required_reference_views": reference_views,
            "genre_character_direction": reference_character,
        }

    unique_identity_parts = [
        unique.get("archetype", ""),
        f"{subject['gender_presentation']} {subject['subject_label']}",
        subject.get("identity_prefix", ""),
        _profile_value(profile, "identity", seed, "identity"),
        reference_character,
        f"face structure: {unique['face_shape']}" if unique.get("face_shape") else "",
        f"song-specific face detail: {unique['face']}" if unique.get("face") else "",
        f"signature gesture: {unique['gesture']}" if unique.get("gesture") else "",
    ]
    unique_hair = ", ".join(
        part for part in [
            _with_color(unique.get("hair_base", ""), main_color),
            _with_color(unique.get("hair", ""), main_color),
            f"single {main_color} identity accent only, placed exactly as described",
        ] if part
    )
    unique_outfit = ", ".join(
        part for part in [
            _with_color(unique.get("outfit_base", ""), main_color),
            _with_color(unique.get("outfit", ""), main_color),
            _with_color(unique.get("accessory", ""), main_color),
        ] if part
    )
    unique_silhouette = _with_color(unique.get("body", ""), main_color) or profile["silhouette"]
    identity_lock = unique.get("identity_lock", "Treat this as a completely new lead character for this song.")
    identity_lock_sentence = identity_lock.rstrip(".")
    return {
        "role": "unique protagonist for this song",
        "subject_type": subject["subject_type"],
        "subject_label": subject["subject_label"],
        "gender_presentation": subject["gender_presentation"],
        "identity": ", ".join(part for part in unique_identity_parts if part),
        "age_style": "anime character, stylized and non-photorealistic",
        "hair": unique_hair,
        "outfit": unique_outfit,
        "silhouette": unique_silhouette,
        "emotional_state": mood_words,
        "signature_prop": colored_prop,
        "accent_detail": (
            f"{_pe.BRAND_PALETTE['main_color']} remains dominant, but the prop and gestures follow this song motif: {motif}. "
            f"This exact face structure, body silhouette, hair shape, outfit category, accessory, and gesture set belong only to '{song.get('title', 'this song')}'. "
            f"{identity_lock_sentence}"
        ),
        "consistency_rules": [
            "Keep the same face, hairstyle, outfit, body proportions, and signature prop within this song only.",
            f"Primary subject type: {subject['subject_type']} ({subject['subject_label']}); gender presentation: {subject['gender_presentation']}.",
            "Do not reuse this character design for a different song unless the user explicitly requests a series identity.",
            identity_lock,
            "Do not average this character into a generic dark-haired anime protagonist; prioritize the face structure, body silhouette, hair base, and outfit base.",
            "Let pose, expression, setting, and action change per section according to lyrics, genre, intensity, and BPM.",
            "Use anime cinematic styling, never live-action realism.",
            "First generate Step 00 (character turnaround model sheet) before creating any scene image.",
            "Attach that same character model sheet when generating every scene image for this song.",
            "Attach the final scene image as the primary image-to-video reference when generating the video for that scene.",
        ],
        "reference_workflow": [
            "Generate a clean song-specific character turnaround model sheet before scene production.",
            "Use the same model sheet as an input/reference for every scene image prompt in this song.",
            "After each scene image is approved, use that scene image as the primary image-to-video input with the matching video prompt.",
            "When possible, include the model sheet as a secondary reference during video generation to protect character identity.",
        ],
        "required_reference_views": [
            "front full-body view",
            "left side full-body view",
            "right side full-body view",
            "back full-body view",
            "three-quarter full-body view",
            "face close-up",
            f"prop close-up of {colored_prop}",
            f"gender/subject check: {subject['gender_presentation']} {subject['subject_label']}",
        ],
        "genre_character_direction": reference_character,
    }


# ---------------------------------------------------------------------------
# Character sheet prompt writers
# ---------------------------------------------------------------------------

def character_prompt(protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    rules = "\n".join(f"- {rule}" for rule in protagonist["consistency_rules"])
    if protagonist.get("subject_type") in ("environment_only", "object_symbol"):
        subject_description = (
            f"{protagonist['identity']}, {protagonist['age_style']}, {protagonist['silhouette']}. "
            f"Primary recurring subject: {protagonist['signature_prop']}. "
        )
    else:
        subject_description = (
            f"{protagonist['identity']}, {protagonist['age_style']}, {protagonist['hair']}, "
            f"{protagonist['outfit']}, {protagonist['silhouette']}. Signature prop: {protagonist['signature_prop']}. "
        )
    return (
        "# Character Prompt\n\n"
        "Create a completely new primary visual subject for this song, not a reused design or costume variation.\n\n"
        f"{subject_description}"
        f"Accent detail: {protagonist['accent_detail']}. Visual world: {world['visual_identity']}.\n\n"
        "Consistency rules:\n"
        f"{rules}\n"
    )


def character_reference_prompt(protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    rules    = "\n".join(f"- {rule}" for rule in protagonist["consistency_rules"])
    workflow = "\n".join(f"- {step}" for step in protagonist.get("reference_workflow", []))
    views    = "\n".join(f"- {view}" for view in protagonist.get("required_reference_views", []))
    is_nonhuman = protagonist.get("subject_type") in ("environment_only", "object_symbol")
    title = "Primary Visual Subject Reference Sheet Prompt" if is_nonhuman else "Character Turnaround Model Sheet Prompt"
    purpose = (
        "Create the master primary-subject reference sheet for this song. This sheet will be attached as the visual identity reference for every later scene image.\n\n"
        if is_nonhuman else
        "Create the master character turnaround model sheet for this song. This model sheet will be attached as the identity reference for every later scene image, and optionally as a secondary reference for video generation.\n\n"
    )
    design = (
        f"Subject design: {protagonist['identity']}, {protagonist['age_style']}, {protagonist['silhouette']}. "
        f"Primary recurring subject: {protagonist['signature_prop']}. "
        if is_nonhuman else
        f"Character design: {protagonist['identity']}, {protagonist['age_style']}, {protagonist['hair']}, "
        f"{protagonist['outfit']}, {protagonist['silhouette']}. Signature prop: {protagonist['signature_prop']}. "
    )
    composition = (
        "Composition: clean anime subject reference sheet, neutral simple background where useful, clear scale references, "
        "wide environment/object views plus close-up details, no full-body human turnaround unless the subject type is human, "
        "no readable text, clear recurring motif, no dramatic camera angle for the reference sheet. "
        if is_nonhuman else
        "Composition: clean anime production model sheet, neutral simple background, aligned character views at the same scale, "
        "full body visible from head to toe in each turnaround pose, clear face close-up, clear hairstyle silhouette, "
        "clear outfit seams, clear signature prop, no dramatic camera angle, no cropped limbs, no environmental scene, no action pose. "
    )
    return (
        f"# {title}\n\n"
        f"{purpose}"
        "Identity requirement: create a visibly new primary subject for this song, not a reused design, not a costume variation, "
        "not the same face with different clothes. If the subject is not human, do not force a full-body human character; keep the object/environment as the main subject.\n\n"
        "Required views:\n"
        f"{views}\n\n"
        f"{design}"
        f"Accent detail: {protagonist['accent_detail']}. Visual world: {world['visual_identity']}.\n\n"
        f"{composition}"
        f"{_pe.BRAND_PALETTE['palette_rule']}. Non-photorealistic, no live action, no text, no watermark.\n\n"
        "Consistency rules:\n"
        f"{rules}\n\n"
        "Production workflow:\n"
        f"{workflow}\n"
    )
