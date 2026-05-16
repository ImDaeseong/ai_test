from __future__ import annotations

import argparse
from pathlib import Path

from common import PROJECT_ROOT, ensure_directories, load_config, read_json, write_text

_platforms_raw = load_config("platforms").get("platforms", [])
_PLATFORMS: list[dict] = _platforms_raw if _platforms_raw else [
    {"id": "runway",   "display_name": "Runway Gen-3 Alpha", "note": "Use image-to-video if available. Lead with camera type."},
    {"id": "kling",    "display_name": "Kling AI",           "note": "40-60 words. End with motion conclusion state."},
    {"id": "pika",     "display_name": "Pika 2.2",           "note": "Use -camera, -motion 2, -neg flags."},
    {"id": "luma",     "display_name": "Luma Dream Machine", "note": "Emphasize camera path and parallax."},
    {"id": "sora",     "display_name": "Sora (OpenAI)",      "note": "5-section: scene / cinematography / actions / style / sound."},
    {"id": "hailuo",   "display_name": "Hailuo AI (MiniMax)","note": "Narrative prose. Strong action verbs. Anchor character traits."},
    {"id": "pixverse", "display_name": "PixVerse",           "note": "Use anime style preset. Include negative prompt."},
    {"id": "veo",      "display_name": "Veo 2/3 (Google)",   "note": "Lead with cinematography. Specify visual medium."},
    {"id": "flow",     "display_name": "Google Flow",        "note": "Scene-building on Veo. Preserve character continuity."},
    {"id": "wan",      "display_name": "Wan 2.1 (Alibaba)",  "note": "T2V: [shot] + [scene] + [motion] + [camera] + [2D anime style]. Always include negative prompt."},
    {"id": "remotion", "display_name": "Remotion",           "note": "React/Remotion composition spec. Not a generative prompt."},
]

_NEG_COMMON = "blurry, distorted faces, flickering, extra limbs, watermark, low quality"


def _match_camera_keyword(camera: str, kw_list: list[str]) -> str:
    """Return the best-matching keyword from the platform's camera_keywords list."""
    if not camera:
        return "tracking shot"
    cam_lower = camera.lower()
    for kw in kw_list:
        if any(part in cam_lower for part in kw.lower().split()):
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
    return "\n".join(
        [
            f"Composition: `{component_name}`",
            f"Purpose: Build this as a Remotion scene component for Scene {scene_no:02d} - {section}.",
            "",
            "Scene Data:",
            f"- Primary subject: {subject}",
            f"- Environment: {scene.get('environment', '')}",
            f"- Emotion/intensity: {scene.get('emotion', '')} / {scene.get('intensity', '')}",
            f"- Lyric cue: {lyric}",
            f"- Action: {scene.get('scene_action', '')}",
            f"- Symbolic focus: {scene.get('symbolic_focus', '')}",
            f"- Camera: {scene.get('camera_direction', '')}",
            f"- Motion: {scene.get('movement', '')}",
            f"- Rhythm: {scene.get('video_rhythm', '')}",
            f"- Lighting/style: {scene.get('lighting', '')}",
            "",
            "Layer Plan:",
            "- Background environment layer with palette-matched gradients, texture, and parallax.",
            "- Primary subject/reference image layer. Use the approved scene image or subject sheet as source.",
            "- Motif layer for symbolic particles, reflections, scent trails, waveform lights, or memory fragments.",
            "- Foreground light/streak layer for depth and beat accents.",
            "- Optional mask layer for wipes, reflection reveals, or object-led transitions.",
            "",
            "Animation Plan:",
            "- Use `useCurrentFrame()` and `interpolate()` for camera push/pull, opacity, blur, scale, and parallax.",
            "- Map the first third to establishing motion, the middle third to the main action, and the final third to transition preparation.",
            "- Keep subject identity stable. Animate transforms, light, and atmosphere more than facial or body redesign.",
            "- Use easing for slow sections; use short accent pulses for beat peaks.",
            "",
            "Implementation Notes:",
            "- Build with React components, absolute-positioned layers, CSS transforms, `Img`, and optional SVG/CSS masks.",
            "- Avoid generating readable text inside the frame unless manually required.",
            "- Keep colors, subject, and camera intent faithful to the matching image prompt.",
            f"- {note}",
        ]
    )


def _build_platform_prompt(scene: dict, platform: dict) -> str:
    """Format scene video prompt according to each platform's official guidelines."""
    pid = platform.get("id", "")
    note = platform.get("note", "")

    if pid == "remotion":
        return remotion_prompt(scene, note)

    base = scene.get("video_prompt", "")
    camera = scene.get("camera_direction", "").strip()
    lighting = scene.get("lighting", "")
    action = scene.get("scene_action", "")
    cam_kws = platform.get("camera_keywords", [])

    if pid == "runway":
        # Official guide: lead with "[camera_type]:" before any other description
        lead = camera if camera else "cinematic tracking shot"
        return f"{lead}: {base}\n\n> {note}"

    if pid == "kling":
        # Official guide: 40-60 words (Kling 2.5 Turbo Pro), always end with motion conclusion
        # Build a concise 4-part body from scene fields rather than hard-cutting the long base prompt
        subject = scene.get("protagonist_continuity", "").split(",")[0].strip()
        kling_body = (
            f"Medium shot of {subject} in {scene.get('environment', 'urban night scene')}, "
            f"{action}. "
            f"{lighting}. Anime cinematic style."
        )
        words = kling_body.split()
        if len(words) > 60:
            kling_body = " ".join(words[:60])
            # Trim to last complete sentence to avoid mid-sentence cut
            last_period = kling_body.rfind(".")
            if last_period > 20:
                kling_body = kling_body[:last_period + 1]
        conclusion_triggers = ("settles", "stillness", "returns to", "fades", "comes to rest")
        if not any(t in kling_body.lower() for t in conclusion_triggers):
            kling_body += " The movement settles back into stillness."
        return f"{kling_body}\n\n> {note}"

    if pid == "pika":
        # Official guide: -camera flag, -motion, -fps, -neg parameter syntax
        cam_flag = _match_camera_keyword(camera, cam_kws)
        flags = f"-camera {cam_flag} -motion 2 -fps 24 -neg '{_NEG_COMMON}'"
        return f"{base}\n\n**Pika flags:** `{flags}`\n\n> {note}"

    if pid == "pixverse":
        # Official guide: anime style preset + negative prompt
        return (
            f"{base}\n\n"
            f"**Style preset:** `anime` | "
            f"**Negative prompt:** `{_NEG_COMMON}`\n\n"
            f"> {note}"
        )

    if pid == "sora":
        # Official guide: 5-section structure (scene/cinematography/actions/style/sound)
        style = "anime cel-shaded 2D animation, palette faithful to the matching image prompt"
        rhythm = scene.get("video_rhythm", "")
        lyric_cue = scene.get("lyric_visual_idea", "").replace("lyric cue: ", "").replace("music cue: ", "")
        lyric_cue = lyric_cue.replace("futuristic", "song-specific cinematic").replace("Futuristic", "Song-specific cinematic")
        sound = f"{rhythm}. {lyric_cue}" if lyric_cue else rhythm
        return (
            f"**Scene:** {base}\n"
            f"**Cinematography:** {camera}. {lighting}.\n"
            f"**Actions:** {action}\n"
            f"**Style:** {style}\n"
            f"**Sound:** {sound}\n\n"
            f"> {note}"
        )

    if pid == "hailuo":
        # Official guide: narrative prose, strong verbs — base prompt already formatted
        return f"{base}\n\n> {note}"

    if pid == "veo" or pid == "flow":
        # Official guide: lead with cinematography
        return f"{camera}: {base}\n\n> {note}" if camera else f"{base}\n\n> {note}"

    if pid == "luma":
        return f"{base}\n\n> {note}"

    if pid == "wan":
        # Official guide: structured formula — shot/camera/motion/style sections
        cam_kw = _match_camera_keyword(camera, cam_kws)
        neg = "low quality, worst quality, blurry, distorted, watermark, text, extra limbs, bad anatomy"
        return (
            f"Medium close-up shot. {base}\n"
            f"Camera: {cam_kw}.\n\n"
            f"**Negative prompt:** `{neg}`\n\n"
            f"> {note}"
        )

    return f"{base}\n\n> {note}"


def run(scene_list_path: Path | None = None) -> None:
    ensure_directories()
    path = scene_list_path or (PROJECT_ROOT / "storyboard" / "scene_list.json")
    scene_list = read_json(path)
    out_dir = PROJECT_ROOT / "prompts" / "video_prompts"
    for old_file in out_dir.glob("scene_*.md"):
        old_file.unlink()
    for scene in scene_list["scenes"]:
        content = [f"# Scene {scene['scene_number']:02d} - {scene['music_section']}\n"]
        for platform in _PLATFORMS:
            content.append(f"## {platform['display_name']}")
            content.append(f"{_build_platform_prompt(scene, platform)}\n")
        filename = out_dir / f"scene_{scene['scene_number']:02d}_{scene['music_section'].lower().replace('-', '_')}.md"
        write_text(filename, "\n".join(content))
    print(f"Wrote {len(scene_list['scenes'])} video prompt files")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write per-scene video prompts for major AI video platforms.")
    parser.add_argument("--scene-list", default=str(PROJECT_ROOT / "storyboard" / "scene_list.json"))
    args = parser.parse_args()
    run(scene_list_path=Path(args.scene_list))


if __name__ == "__main__":
    main()
