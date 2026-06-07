from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

from common import PROJECT_ROOT, ensure_directories, load_config, read_json, write_text
from policy_safety import safety_normalize_prompt

_platforms_raw = load_config("platforms").get("platforms", [])
if not _platforms_raw:
    raise RuntimeError("configs/platforms.json must define platforms.")
_PLATFORMS: list[dict] = _platforms_raw
_NEG_COMMON = "blurry, distorted faces, flickering, extra limbs, watermark, low quality"

# Generic camera words that appear in almost every shot description and cause false matches.
# "shot" matches "static shot" against any direction containing "shot" (nearly all of them).
# "angle" matches "low angle" against any direction containing "angle" (upward, dutch, etc.).
_CAMERA_STOPWORDS = frozenset({"shot", "angle"})
_CLIP_TARGET_SECONDS = 6.0
_CLIP_MAX_SECONDS = 8.0


def _slug_section(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "scene"


def _scene_duration(scene: dict) -> float | None:
    start = scene.get("start_time")
    end = scene.get("end_time")
    if start is None or end is None:
        return None
    try:
        duration = float(end) - float(start)
    except (TypeError, ValueError):
        return None
    return duration if duration > 0 else None


def _clip_count(scene: dict) -> int:
    duration = _scene_duration(scene)
    if duration is None:
        return 4  # 타이밍 없는 경우: Wide→Action→Emotion→Detail 4샷 기본값
    return max(1, math.ceil(duration / _CLIP_MAX_SECONDS))


def _clip_time_range(scene: dict, clip_index: int, total_clips: int) -> tuple[float | None, float | None]:
    duration = _scene_duration(scene)
    if duration is None:
        return None, None
    start = float(scene["start_time"])
    clip_duration = duration / total_clips
    clip_start = start + (clip_index - 1) * clip_duration
    clip_end = start + clip_index * clip_duration
    return round(clip_start, 2), round(clip_end, 2)


def _clip_role(clip_index: int, total_clips: int) -> str:
    if total_clips == 1:
        return "single clip: cover the whole scene with one readable camera move and a clean end frame"
    if clip_index == 1:
        return "opening clip: establish the location, subject silhouette, palette, and motif"
    if clip_index == total_clips:
        return "transition clip: resolve the action and prepare a clean end frame for the next scene"
    if clip_index == 2:
        return "detail clip: move closer to the face, prop, gesture, or lyric symbol"
    return "development clip: vary the camera distance and let the action progress without redesigning the subject"


def _clip_reference_image_label(clip_index: int, total_clips: int) -> str:
    if total_clips == 4:
        return ["wide", "action", "emotion", "detail"][clip_index - 1]
    if clip_index == 1:
        return "wide"
    if clip_index == total_clips:
        return "detail"
    if clip_index == 2:
        return "action"
    return "emotion"


def _clip_camera(scene: dict, clip_index: int, total_clips: int) -> str:
    base = scene.get("camera_direction", "cinematic anime shot")
    if total_clips == 1:
        return base
    if total_clips == 4:
        # Wide → Action(original) → Emotion close-up → Detail insert
        variants = [
            f"wide establishing shot — pulls back to show full {scene.get('environment', 'environment')}",
            base,
            "close-up emotion frame — tight on face and expression",
            "extreme close-up insert — symbolic prop or motif detail",
        ]
        return variants[clip_index - 1]
    variants = [
        base,
        "medium detail frame preserving the same subject silhouette and prop",
        "close anime reaction frame focused on the face, hands, or motif glow",
        "wide transition frame preserving the environment and final pose",
    ]
    if clip_index == total_clips:
        return variants[-1]
    return variants[min(clip_index - 1, len(variants) - 2)]


def _clip_action(scene: dict, clip_index: int, total_clips: int) -> str:
    action = scene.get("scene_action", "continues the scene action")
    symbol = scene.get("symbolic_focus", "the song motif")
    if total_clips == 1:
        return action
    if total_clips == 4:
        prop = scene.get("protagonist_continuity", "character").split(",")[0]
        return [
            f"environment reveals context; {prop} silhouette appears at distance",
            action,
            f"{symbol} reflects the emotional state as {prop} expresses the lyric feeling",
            f"{symbol} fills the frame as a detail insert; holds clean transition pose",
        ][clip_index - 1]
    if clip_index == 1:
        return f"begins the scene action: {action}"
    if clip_index == total_clips:
        return f"lets {symbol} settle into the final pose, then holds a clean transition frame"
    if clip_index == 2:
        return f"continues through a readable gesture detail while {symbol} responds to the beat"
    return f"develops the motion phrase with subtle variation while {symbol} stays visually connected"


def _clip_base_prompt(scene: dict, clip_index: int, total_clips: int) -> str:
    base = safety_normalize_prompt(scene.get("video_prompt", ""))
    clip_start, clip_end = _clip_time_range(scene, clip_index, total_clips)
    reference_label = _clip_reference_image_label(clip_index, total_clips)
    if clip_start is None or clip_end is None:
        time_text = f"Clip {clip_index}/{total_clips}: untimed section, target {_CLIP_TARGET_SECONDS:.0f}s."
    else:
        clip_duration = max(0.1, clip_end - clip_start)
        time_text = (
            f"Clip {clip_index}/{total_clips}: timecode {clip_start:.2f}s-{clip_end:.2f}s "
            f"({clip_duration:.2f}s)."
        )
    return safety_normalize_prompt(
        f"{base} "
        f"{time_text} "
        f"Clip role: {_clip_role(clip_index, total_clips)}. "
        f"Primary reference image: use the matching scene_{reference_label} image for this clip when available. "
        f"Clip camera: {_clip_camera(scene, clip_index, total_clips)}. "
        f"Clip action: {_clip_action(scene, clip_index, total_clips)}. "
        "Use the approved scene image as the first frame when available; for later clips, use the previous clip end frame as continuity reference. "
        "Keep only one main camera move and one subject action in this clip."
    )


def _clip_scene(scene: dict, clip_index: int, total_clips: int) -> dict:
    clip = dict(scene)
    clip["camera_direction"] = _clip_camera(scene, clip_index, total_clips)
    clip["scene_action"] = _clip_action(scene, clip_index, total_clips)
    clip_start, clip_end = _clip_time_range(scene, clip_index, total_clips)
    if clip_start is not None and clip_end is not None:
        clip["start_time"] = clip_start
        clip["end_time"] = clip_end
        clip["video_rhythm"] = (
            f"{scene.get('video_rhythm', '')}; clip {clip_index}/{total_clips} covers "
            f"{clip_start:.2f}s-{clip_end:.2f}s"
        )
    else:
        clip["video_rhythm"] = f"{scene.get('video_rhythm', '')}; clip {clip_index}/{total_clips} target {_CLIP_TARGET_SECONDS:.0f}s"
    clip["video_prompt"] = _clip_base_prompt(scene, clip_index, total_clips)
    return clip


def _match_camera_keyword(camera: str, kw_list: list[str]) -> str:
    """Return the best-matching keyword from the platform's camera_keywords list.
    Only matches on meaningful words (length > 3, not in _CAMERA_STOPWORDS) to avoid
    false positives from generic words like 'shot' or 'angle' that appear in many
    camera descriptions and cause wrong mappings (e.g. 'drone shot' matching on 'shot').
    """
    if not camera:
        return "tracking shot"
    cam_lower = camera.lower()
    for kw in kw_list:
        meaningful = [p for p in kw.lower().split() if len(p) > 3 and p not in _CAMERA_STOPWORDS]
        if meaningful and any(part in cam_lower for part in meaningful):
            return kw
    return "tracking shot"


def remotion_prompt(scene: dict, note: str) -> str:
    """Write a structured Remotion implementation brief instead of a prose video-model prompt."""
    section = scene.get("music_section", "Scene")
    scene_no = int(scene.get("scene_number", 0) or 0)
    component_name = f"Scene{scene_no:02d}{section.replace('-', '').replace(' ', '')}"
    subject = scene.get("protagonist_continuity", "primary visual subject")
    lyric = scene.get("lyric_visual_idea", "").replace("lyric cue: ", "").replace("music cue: ", "")
    lyric = lyric.replace("futuristic", "song-specific cinematic").replace("Futuristic", "Song-specific cinematic")

    # Song-specific fields
    story_stage = scene.get("story_stage", "")
    story_beat = scene.get("story_beat_en", "")
    cinematic_style = scene.get("cinematic_style", "")
    symbolism = scene.get("symbolism", [])
    motif_items = ", ".join(symbolism[:3]) if symbolism else scene.get("symbolic_focus", "song motif elements")

    # BPM-aware frame timing derived from video_rhythm field
    rhythm_raw = scene.get("video_rhythm", "")
    bpm_hint = ""
    if rhythm_raw and "BPM" in rhythm_raw:
        try:
            bpm_val = int(rhythm_raw.split("BPM")[0].strip().split()[-1])
            beat_ms = round(60000 / bpm_val)
            beat_frames_30 = round(1800 / bpm_val)  # frames per beat at 30fps = 1800/bpm
            bpm_hint = f"At {bpm_val} BPM: 1 beat = {beat_ms}ms = ~{beat_frames_30}f at 30fps. Sync cuts and light pulses to beat multiples."
        except (ValueError, IndexError):
            pass

    # Intensity-aware easing hint
    intensity = scene.get("intensity", "medium")
    easing_hint = {
        "low":           "Use slow ease-in-out (spring or bezier). Prioritize atmosphere over motion.",
        "medium":        "Mix gentle eases with occasional beat-synced accent pulses.",
        "medium-high":   "Lean into forward momentum. Use ease-out on beat hits with brief holds between phrases.",
        "high":          "Use sharp ease-out on beat hits. Keep momentum — avoid lingering holds.",
        "emotional peak": "Slow the motion dramatically — let the emotion breathe. One precise accent at the peak frame.",
        "falling":       "Ease-in for a sense of weight and descent. Gentle deceleration toward stillness.",
    }.get(intensity, "Use easing matched to the section's emotional intensity.")

    lines = [
        f"Composition: `{component_name}`",
        f"Purpose: Build this as a Remotion scene component for Scene {scene_no:02d} - {section}.",
        "",
        "Scene Data:",
        f"- Primary subject: {subject}",
        f"- Environment: {scene.get('environment', '')}",
        f"- Cinematic style: {cinematic_style}",
        f"- Story stage: {story_stage}" + (f" — {story_beat}" if story_beat else ""),
        f"- Emotion/intensity: {scene.get('emotion', '')} / {intensity}",
        f"- Lyric cue: {lyric}",
        f"- Action: {scene.get('scene_action', '')}",
        f"- Symbolic focus: {scene.get('symbolic_focus', '')}",
        f"- Symbolism: {', '.join(symbolism) if symbolism else '—'}",
        f"- Camera: {scene.get('camera_direction', '')}",
        f"- Motion: {scene.get('movement', '')}",
        f"- Rhythm: {rhythm_raw}",
        f"- Lighting/style: {scene.get('lighting', '')}",
        "",
        "Layer Plan:",
        f"- Background: {scene.get('environment', 'environment')} with palette-matched gradients and parallax depth. Base colors from cinematic style palette.",
        "- Primary subject layer: use the approved scene image or subject reference sheet. Preserve character identity across all sections.",
        f"- Motif/symbol layer: animate {motif_items}. Style particles and glows to match the scene lighting and palette.",
        f"- Foreground accent layer: beat-synced light streaks or depth elements at {intensity} intensity.",
        "- Optional transition layer: wipe, dissolve, or symbol-led cut prepared at the final 20% of the composition duration.",
        "",
        "Animation Plan:",
        "- Use `useCurrentFrame()` and `interpolate()` for camera push/pull, opacity, blur, scale, and parallax.",
        f"- {bpm_hint}" if bpm_hint else "- Sync motion timing to the section's BPM rhythm.",
        f"- {easing_hint}",
        "- Map: first 30% → establishing motion / entering camera; middle 50% → main action and lyric expression; final 20% → transition preparation.",
        "- Keep subject identity stable. Animate transforms, light, and atmosphere — not facial or costume redesign.",
        "",
        "Implementation Notes:",
        "- Build with React components, absolute-positioned layers, CSS transforms, `Img`, and optional SVG/CSS masks.",
        f"- Style palette and visual identity are derived from: {cinematic_style}. Apply these as CSS color variables.",
        "- Avoid generating readable text inside the frame unless the lyric cue explicitly requires it.",
        "- Keep colors, subject silhouette, and camera intent faithful to the matching image prompt for this scene.",
        f"- {note}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Per-platform prompt handlers (Strategy pattern)
# 새 플랫폼 추가: 함수 작성 후 _PLATFORM_HANDLERS 에 등록
# ---------------------------------------------------------------------------

def _prompt_runway(scene: dict, platform: dict, base: str, camera: str, lighting: str, action: str) -> str:
    note = platform.get("note", "")
    lead = camera if camera else "cinematic tracking shot"
    return safety_normalize_prompt(f"[{lead}]: {base}\n\n> {note}")


def _prompt_kling(scene: dict, platform: dict, base: str, camera: str, lighting: str, action: str) -> str:
    note = platform.get("note", "")
    subject = scene.get("protagonist_continuity", "").split(",")[0].strip()
    _cam_phrase = (camera.split(",")[0].strip() if camera else "").split()
    _cam_phrase = _cam_phrase[:min(3, len(_cam_phrase))]
    _trailing_preps = {"from", "into", "with", "toward", "to", "at", "of", "and", "the"}
    while _cam_phrase and _cam_phrase[-1].lower() in _trailing_preps:
        _cam_phrase.pop()
    cam_type = " ".join(_cam_phrase) if _cam_phrase else "medium shot"
    kling_body = (
        f"{cam_type.capitalize()}: {subject} in {scene.get('environment', 'open cinematic space')}, "
        f"{action}. {lighting}."
    )
    conclusion_triggers = ("settles", "stillness", "returns to", "fades", "comes to rest")
    conclusion = " The movement settles back into stillness."
    has_conclusion = any(t in kling_body.lower() for t in conclusion_triggers)
    max_body = 59 if not has_conclusion else 65
    words = kling_body.split()
    if len(words) > max_body:
        kling_body = " ".join(words[:max_body])
        last_period = kling_body.rfind(".")
        if last_period > 20:
            kling_body = kling_body[:last_period + 1]
    if not has_conclusion:
        kling_body += conclusion
    return safety_normalize_prompt(f"{kling_body}\n\n> {note}")


def _prompt_pika(scene: dict, platform: dict, base: str, camera: str, lighting: str, action: str) -> str:
    note = platform.get("note", "")
    cam_flag = _match_camera_keyword(camera, platform.get("camera_keywords", []))
    flags = f"-camera {cam_flag} -motion 2 -fps 24 -neg '{_NEG_COMMON}'"
    return safety_normalize_prompt(f"{base}\n\n**Pika flags:** `{flags}`\n\n> {note}")


def _prompt_pixverse(scene: dict, platform: dict, base: str, camera: str, lighting: str, action: str) -> str:
    note = platform.get("note", "")
    return safety_normalize_prompt(
        f"{base}\n\n**Style preset:** `anime` | **Negative prompt:** `{_NEG_COMMON}`\n\n> {note}"
    )


def _prompt_sora(scene: dict, platform: dict, base: str, camera: str, lighting: str, action: str) -> str:
    note = platform.get("note", "")
    style = "anime cel-shaded 2D animation, palette faithful to the matching image prompt"
    rhythm = scene.get("video_rhythm", "")
    lyric_cue = scene.get("lyric_visual_idea", "").replace("lyric cue: ", "").replace("music cue: ", "")
    lyric_cue = lyric_cue.replace("futuristic", "song-specific cinematic").replace("Futuristic", "Song-specific cinematic")
    sound = f"{rhythm}. {lyric_cue}" if lyric_cue else rhythm
    return safety_normalize_prompt(
        f"**Scene:** {base}\n"
        f"**Cinematography:** {camera}. {lighting}.\n"
        f"**Actions:** {action}\n"
        f"**Style:** {style}\n"
        f"**Sound:** {sound}\n\n"
        f"> {note}"
    )


def _prompt_hailuo(scene: dict, platform: dict, base: str, camera: str, lighting: str, action: str) -> str:
    note = platform.get("note", "")
    subject = scene.get("protagonist_continuity", "").split(",")[0].strip()
    env = scene.get("environment", "")
    movement = scene.get("movement", "")
    cam_phrase = camera.split(",")[0].strip() if camera else "medium shot"
    lyric_idea = scene.get("lyric_visual_idea", "").replace("lyric cue: ", "").replace("music cue: ", "")
    lyric_idea = lyric_idea.replace("futuristic", "song-specific cinematic").replace("Futuristic", "Song-specific cinematic")
    narrative = f"{cam_phrase}. {subject} {action} in {env}. {movement}. {lighting}."
    if lyric_idea:
        narrative += f" {lyric_idea}."
    narrative += " Song-specific cinematic atmosphere."
    return safety_normalize_prompt(f"{narrative}\n\n> {note}")


def _prompt_veo_flow(scene: dict, platform: dict, base: str, camera: str, lighting: str, action: str) -> str:
    note = platform.get("note", "")
    return safety_normalize_prompt(f"{camera}: {base}\n\n> {note}" if camera else f"{base}\n\n> {note}")


def _prompt_luma(scene: dict, platform: dict, base: str, camera: str, lighting: str, action: str) -> str:
    note = platform.get("note", "")
    luma_cam = _match_camera_keyword(camera, platform.get("camera_keywords", []))
    env = scene.get("environment", "")
    movement = scene.get("movement", "")
    lyric_idea = scene.get("lyric_visual_idea", "").replace("lyric cue: ", "").replace("music cue: ", "")
    lyric_idea = lyric_idea.replace("futuristic", "song-specific cinematic").replace("Futuristic", "Song-specific cinematic")[:120]
    return safety_normalize_prompt(
        f"{base}\n\n"
        f"**Luma camera:** `{luma_cam}` — camera path with parallax depth and environmental atmosphere.\n"
        f"**Environment:** {env}. **Movement:** {movement}.\n"
        + (f"**Lyric cue:** {lyric_idea}\n\n" if lyric_idea else "\n")
        + f"> {note}"
    )


def _prompt_wan(scene: dict, platform: dict, base: str, camera: str, lighting: str, action: str) -> str:
    note = platform.get("note", "")
    cam_kw = _match_camera_keyword(camera, platform.get("camera_keywords", []))
    neg = "low quality, worst quality, blurry, distorted, watermark, text, extra limbs, bad anatomy"
    return safety_normalize_prompt(
        f"{cam_kw.capitalize() if cam_kw else 'Cinematic shot'}. {base}\n"
        f"Camera: {cam_kw}.\n\n"
        f"**Negative prompt:** `{neg}`\n\n"
        f"> {note}"
    )


def _prompt_default(scene: dict, platform: dict, base: str, camera: str, lighting: str, action: str) -> str:
    return safety_normalize_prompt(f"{base}\n\n> {platform.get('note', '')}")


# 플랫폼 ID → 핸들러 함수 테이블
# 새 플랫폼 추가 시: 함수 작성 후 여기에 등록
_PLATFORM_HANDLERS = {
    "runway":   _prompt_runway,
    "kling":    _prompt_kling,
    "pika":     _prompt_pika,
    "pixverse": _prompt_pixverse,
    "sora":     _prompt_sora,
    "hailuo":   _prompt_hailuo,
    "veo":      _prompt_veo_flow,
    "flow":     _prompt_veo_flow,
    "luma":     _prompt_luma,
    "wan":      _prompt_wan,
}


def _build_platform_prompt(scene: dict, platform: dict) -> str:
    """Format scene video prompt according to each platform's official guidelines."""
    pid = platform.get("id", "")
    if pid == "remotion":
        return remotion_prompt(scene, platform.get("note", ""))

    base     = safety_normalize_prompt(scene.get("video_prompt", ""))
    camera   = safety_normalize_prompt(scene.get("camera_direction", "").strip())
    lighting = safety_normalize_prompt(scene.get("lighting", ""))
    action   = safety_normalize_prompt(scene.get("scene_action", ""))

    handler = _PLATFORM_HANDLERS.get(pid, _prompt_default)
    return handler(scene, platform, base, camera, lighting, action)


def run(scene_list_path: Path | None = None) -> None:
    ensure_directories()
    path = scene_list_path or (PROJECT_ROOT / "storyboard" / "scene_list.json")
    scene_list = read_json(path)
    out_dir = PROJECT_ROOT / "prompts" / "video_prompts"
    clip_dir = PROJECT_ROOT / "prompts" / "video_clip_prompts"
    for old_file in out_dir.glob("scene_*.md"):
        old_file.unlink()
    for old_file in clip_dir.glob("scene_*.md"):
        old_file.unlink()
    timeline_rows = [
        "# Video Clip Timeline Plan",
        "",
        "Use `video_prompts` for section-level direction and these clip prompts for actual 5-8 second generation batches.",
        "",
        "| Scene | Clip | Timecode | Role | Reference flow |",
        "|---|---:|---|---|---|",
    ]
    total_clips = 0
    for scene in scene_list["scenes"]:
        content = [f"# Scene {scene['scene_number']:02d} - {scene['music_section']}\n"]
        for platform in _PLATFORMS:
            content.append(f"## {platform['display_name']}")
            content.append(f"{_build_platform_prompt(scene, platform)}\n")
        filename = out_dir / f"scene_{scene['scene_number']:02d}_{_slug_section(scene['music_section'])}.md"
        write_text(filename, safety_normalize_prompt("\n".join(content)))

        scene_clip_count = _clip_count(scene)
        total_clips += scene_clip_count
        for clip_index in range(1, scene_clip_count + 1):
            clip = _clip_scene(scene, clip_index, scene_clip_count)
            reference_label = _clip_reference_image_label(clip_index, scene_clip_count)
            clip_content = [
                f"# Scene {scene['scene_number']:02d} - {scene['music_section']} - Clip {clip_index:02d}/{scene_clip_count:02d}\n",
                f"Reference flow: use the matching `{reference_label}` scene image as the first clip reference; use the previous clip end frame for later clips when available.\n",
            ]
            for platform in _PLATFORMS:
                clip_content.append(f"## {platform['display_name']}")
                clip_content.append(f"{_build_platform_prompt(clip, platform)}\n")
            clip_filename = (
                clip_dir
                / f"scene_{scene['scene_number']:02d}_{_slug_section(scene['music_section'])}_clip_{clip_index:02d}.md"
            )
            write_text(clip_filename, safety_normalize_prompt("\n".join(clip_content)))

            clip_start, clip_end = _clip_time_range(scene, clip_index, scene_clip_count)
            if clip_start is None or clip_end is None:
                timecode = f"target {_CLIP_TARGET_SECONDS:.0f}s"
            else:
                timecode = f"{clip_start:.2f}s-{clip_end:.2f}s"
            timeline_rows.append(
                f"| {scene['scene_number']:02d} {scene['music_section']} | {clip_index}/{scene_clip_count} | "
                f"{timecode} | {_clip_role(clip_index, scene_clip_count)} | {reference_label} image -> previous end frame |"
            )
    write_text(clip_dir / "timeline_plan.md", "\n".join(timeline_rows) + "\n")
    print(f"Wrote {len(scene_list['scenes'])} video prompt files")
    print(f"Wrote {total_clips} video clip prompt files")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write per-scene video prompts for major AI video platforms.")
    parser.add_argument("--scene-list", default=str(PROJECT_ROOT / "storyboard" / "scene_list.json"))
    args = parser.parse_args()
    run(scene_list_path=Path(args.scene_list))


if __name__ == "__main__":
    main()
