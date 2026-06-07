"""Expand each scene into 4 sub-shots (wide → action → emotion → detail).

Shot types (camera distance progression):
  1. wide    — Wide establishing shot: environment + character silhouette
  2. action  — Medium shot: character action (same as original prompt_writer output)
  3. emotion — Close-up: face / expression / emotional state
  4. detail  — Extreme close-up insert: symbolic prop / motif detail
"""
from __future__ import annotations

from typing import Any

import palette_engine as _pe
from policy_safety import append_policy_safe_note
from prompt_writer import character_visual, compact_lyric_idea

SHOT_TYPES: list[dict[str, str]] = [
    {"index": "1", "label": "wide",    "display": "Wide Establishing"},
    {"index": "2", "label": "action",  "display": "Medium Action"},
    {"index": "3", "label": "emotion", "display": "Close-up Emotion"},
    {"index": "4", "label": "detail",  "display": "Insert Detail"},
]


def _identity_lock(protagonist: dict[str, Any]) -> str:
    accent = protagonist.get("accent_detail", "").strip()
    if accent:
        return f"Identity lock: {accent}."
    return "Identity lock: preserve this song-specific primary subject, palette, prop, and silhouette within this song only."


# ---------------------------------------------------------------------------
# Image prompts — one per shot type
# ---------------------------------------------------------------------------

def _image_wide(scene: dict[str, Any], protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    """Wide establishing shot: environment first, character silhouette in context."""
    env       = scene["environment"]
    lighting  = scene["lighting"]
    symbol    = scene["symbolic_focus"]
    style     = world["visual_identity"]
    palette   = _pe.BRAND_PALETTE["palette_rule"]
    style_pos = _pe.STYLE_POSITIVE
    style_neg = _pe.STYLE_NEGATIVE
    char_sil  = protagonist.get("silhouette", "character silhouette")
    lines = [
        f"Wide establishing shot of {env}.",
        f"{char_sil} visible at a distance, framed within the full environment.",
        _identity_lock(protagonist),
        f"{lighting}.",
        f"Recurring motif: {symbol} present in the scene.",
        f"{style} cinematic world.",
        f"{palette}.",
        f"{style_pos}.",
        f"{style_neg}.",
    ]
    return append_policy_safe_note(" ".join(l for l in lines if l.strip()))


def _image_action(scene: dict[str, Any], protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    """Medium action shot — identical to prompt_writer.image_prompt() output."""
    from prompt_writer import image_prompt
    return image_prompt(scene, protagonist, world)


def _image_emotion(scene: dict[str, Any], protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    """Close-up emotion shot: face and expression detail."""
    emotion   = scene["emotion"]
    lighting  = scene["lighting"]
    lyric     = compact_lyric_idea(scene)
    palette   = _pe.BRAND_PALETTE["palette_rule"]
    style_pos = _pe.STYLE_POSITIVE
    style_neg = _pe.STYLE_NEGATIVE
    char_id   = protagonist.get("identity", "protagonist").split(",")[0].strip()
    acc_det   = protagonist.get("accent_detail", "")
    _lbl = "Scene atmosphere" if scene.get("is_instrumental") else "Lyric mood"
    lines = [
        f"Close-up on {char_id}, face and emotional expression in focus.",
        _identity_lock(protagonist),
        f"{emotion} emotion — expression matches the section intensity.",
        f"{_lbl}: {lyric}.",
        f"{lighting} — close-up lighting emphasis.",
        f"{palette}.",
        f"{style_pos}.",
        f"{style_neg}.",
    ]
    return append_policy_safe_note(" ".join(l for l in lines if l.strip()))


def _image_detail(scene: dict[str, Any], protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    """Extreme close-up insert: symbolic focus and signature prop detail."""
    symbol    = scene["symbolic_focus"]
    prop      = protagonist.get("signature_prop", "")
    lighting  = scene["lighting"]
    motif     = world.get("song_motif", symbol)
    palette   = _pe.BRAND_PALETTE["palette_rule"]
    style_pos = _pe.STYLE_POSITIVE
    lines = [
        f"Extreme close-up insert shot of {symbol}.",
        f"Signature prop detail: {prop}." if prop and prop not in symbol else "",
        _identity_lock(protagonist),
        f"Song motif: {motif} — texture, glow, and material detail visible.",
        f"{lighting} — focused on object surface.",
        f"{palette}.",
        f"{style_pos}. No human figure required.",
    ]
    return append_policy_safe_note(" ".join(l for l in lines if l.strip()))


# ---------------------------------------------------------------------------
# Video prompts — one per shot type
# ---------------------------------------------------------------------------

def _video_wide(scene: dict[str, Any], protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    """Wide establishing: slow panoramic drift, environment reveal."""
    env      = scene["environment"]
    lighting = scene["lighting"]
    rhythm   = scene["video_rhythm"]
    symbol   = scene["symbolic_focus"]
    palette  = _pe.BRAND_PALETTE["palette_rule"]
    neg      = _pe.VIDEO_NEGATIVE
    char_sil = protagonist.get("silhouette", "character silhouette")
    lines = [
        "Image-to-video from the attached scene image.",
        f"Camera slowly pulls back and drifts to reveal the full extent of {env}.",
        f"{char_sil} visible as a small figure within the wide frame.",
        f"{symbol} present in the environment, lit by {lighting}.",
        f"Musical timing: {rhythm}.",
        f"Slow cinematic drift, no sudden cuts. {palette}.",
        f"Smooth coherent anime motion, clean motivated transition at the end. {neg}.",
    ]
    return append_policy_safe_note(" ".join(l for l in lines if l.strip()))


def _video_action(scene: dict[str, Any], protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    """Medium action shot — identical to prompt_writer.video_prompt() output."""
    from prompt_writer import video_prompt
    return video_prompt(scene, protagonist, world)


def _video_emotion(scene: dict[str, Any], protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    """Close-up emotion: tight face follow, micro-expression reveal."""
    emotion  = scene["emotion"]
    lighting = scene["lighting"]
    rhythm   = scene["video_rhythm"]
    lyric    = compact_lyric_idea(scene)
    prop     = protagonist.get("signature_prop", "")
    palette  = _pe.BRAND_PALETTE["palette_rule"]
    neg      = _pe.VIDEO_NEGATIVE
    acc_det  = protagonist.get("accent_detail", "")
    _lbl = "Scene atmosphere" if scene.get("is_instrumental") else "Lyric mood"
    preserve = f"Preserve character design: {acc_det}." if acc_det else ""
    lines = [
        "Image-to-video from the attached scene image.",
        preserve,
        f"Camera: slow push-in close-up tracking face and expression.",
        f"{emotion} emotion builds through micro-expression and subtle movement.",
        f"{_lbl}: {lyric}.",
        f"Signature prop {prop} barely visible at edge of frame." if prop else "",
        f"Musical timing: {rhythm}.",
        f"{lighting} — close-up lighting on face. {palette}.",
        f"Smooth coherent anime motion, clean motivated transition at the end. {neg}.",
    ]
    return append_policy_safe_note(" ".join(l for l in lines if l.strip()))


def _video_detail(scene: dict[str, Any], protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    """Insert/detail: focus pull on symbolic object, minimal camera movement."""
    symbol   = scene["symbolic_focus"]
    prop     = protagonist.get("signature_prop", "")
    rhythm   = scene["video_rhythm"]
    lighting = scene["lighting"]
    motif    = world.get("song_motif", symbol)
    palette  = _pe.BRAND_PALETTE["palette_rule"]
    neg      = _pe.VIDEO_NEGATIVE
    lines = [
        "Image-to-video from the attached scene image.",
        f"Camera: locked-off extreme close-up with subtle rack focus on {symbol}.",
        f"Signature prop {prop} — texture, glow, and material detail animated." if prop else f"{motif} detail animated.",
        f"Minimal camera movement — let the object's surface and light carry the motion.",
        f"Musical timing: {rhythm}.",
        f"{lighting} — object-focused. {palette}.",
        f"Smooth coherent anime motion, clean motivated transition at the end. {neg}.",
    ]
    return append_policy_safe_note(" ".join(l for l in lines if l.strip()))


# ---------------------------------------------------------------------------
# Shot expansion entry point
# ---------------------------------------------------------------------------

_IMAGE_FN = {
    "wide":    _image_wide,
    "action":  _image_action,
    "emotion": _image_emotion,
    "detail":  _image_detail,
}

_VIDEO_FN = {
    "wide":    _video_wide,
    "action":  _video_action,
    "emotion": _video_emotion,
    "detail":  _video_detail,
}


def expand_scene_to_shots(
    scene: dict[str, Any],
    protagonist: dict[str, Any],
    world: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return a list of 4 shot dicts for one scene.

    Each shot dict contains all original scene fields plus:
      shot_index, shot_label, shot_display, image_prompt, video_prompt
    """
    shots = []
    for shot in SHOT_TYPES:
        label = shot["label"]
        shot_dict = {
            **scene,
            "shot_index":   shot["index"],
            "shot_label":   label,
            "shot_display": shot["display"],
            "image_prompt": _IMAGE_FN[label](scene, protagonist, world),
            "video_prompt": _VIDEO_FN[label](scene, protagonist, world),
        }
        shots.append(shot_dict)
    return shots


def expand_all_scenes(
    scenes: list[dict[str, Any]],
    protagonist: dict[str, Any],
    world: dict[str, Any],
) -> list[dict[str, Any]]:
    """Expand all scenes to shots. Returns a flat list of N×4 shot dicts."""
    result = []
    for scene in scenes:
        result.extend(expand_scene_to_shots(scene, protagonist, world))
    return result
