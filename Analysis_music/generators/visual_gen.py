"""
Visual prompt generator: album art, per-section video scenes, and style guide.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from config import OUTPUT_DIR, VISUAL_THEME_MAP
from analyzer.suno_parser import SunoPromptData

# Ordered rules: first matching cluster (by score) wins the fallback theme.
# Each entry is (frozenset_of_tags, theme_name). Tags are matched against
# the joined genre+mood+instruments+vocal_style string.
_TAG_THEME_RULES: list[tuple[frozenset, str]] = [
    (frozenset({"edm", "rave", "drop", "club", "dance", "house", "techno", "trance", "dubstep", "dnb"}), "Cyberpunk Neon"),
    (frozenset({"k-pop", "kpop", "idol", "choreo", "group"}), "Cyberpunk Neon"),
    (frozenset({"neon", "cyber", "glitch", "digital", "synth", "electro"}), "Cyberpunk Neon"),
    (frozenset({"dark", "underground", "808", "trap", "drill", "gangsta", "gritty"}), "Cyberpunk Dark"),
    (frozenset({"hip-hop", "hiphop", "rap", "urban", "street", "graffiti", "mc", "freestyle"}), "Urban Cinematic"),
    (frozenset({"pop", "bright", "colorful", "upbeat", "bubbly", "cheerful", "fun"}), "Vibrant Pop"),
    (frozenset({"r&b", "rnb", "neo soul", "smooth", "sensual", "groove", "soulful"}), "Emotional Cinematic"),
    (frozenset({"ballad", "sad", "cry", "heartbreak", "longing", "tender", "emotional", "piano", "strings"}), "Emotional Cinematic"),
    (frozenset({"love", "romantic", "sweet", "soft", "gentle", "warm"}), "Romantic Soft"),
    (frozenset({"jazz", "blues", "noir", "swing", "smoke", "lounge", "bebop", "bossa"}), "Melancholic Noir"),
    (frozenset({"lonely", "alone", "melancholy", "nostalgia", "winter", "cold"}), "Melancholic Noir"),
    (frozenset({"lo-fi", "lofi", "chill", "mellow", "cozy", "bedroom", "rain", "study"}), "Atmospheric Moody"),
    (frozenset({"ambient", "meditation", "peaceful", "calm", "atmospheric", "drone"}), "Atmospheric Moody"),
    (frozenset({"metal", "rock", "punk", "hardcore", "grunge", "distortion", "guitar", "headbang"}), "High Energy Dynamic"),
    (frozenset({"fire", "energy", "explosive", "intense", "power", "aggressive", "heavy"}), "High Energy Dynamic"),
    (frozenset({"night", "midnight", "late", "insomnia", "city lights", "nocturnal"}), "Nocturnal Urban"),
    (frozenset({"classical", "orchestra", "baroque", "violin", "cello", "choir", "operatic"}), "Romantic Soft"),
    (frozenset({"folk", "country", "acoustic", "roots", "western", "bluegrass", "campfire"}), "Natural Organic"),
    (frozenset({"reggae", "caribbean", "tropical", "beach", "summer", "sun", "island"}), "Natural Organic"),
    (frozenset({"nature", "organic", "earth", "forest", "green", "outdoor"}), "Natural Organic"),
    (frozenset({"future", "sci-fi", "space", "galaxy", "cosmic", "futuristic", "cybernetic"}), "Futuristic Sci-Fi"),
    (frozenset({"retro", "vintage", "80s", "70s", "nostalgic", "throwback", "vhs", "analog"}), "Retro Vintage"),
    (frozenset({"dream", "surreal", "psychedelic", "abstract", "ethereal", "trippy"}), "Dreamlike Surreal"),
    (frozenset({"minimal", "minimalist", "clean", "simple", "pure", "sparse"}), "Minimalist"),
]


@dataclass
class VisualOutput:
    theme: str
    color_palette: list[str]
    album_art_prompt: str
    video_scenes: list[dict]         # [{section, prompt, camera, color}]
    style_guide: dict                # {filters, fonts, transitions, aspect_ratio}
    keyword_map: dict[str, str]      # {keyword: visual_element}

    def to_markdown(self) -> str:
        lines = [
            "## 8. Visual Content Guide\n",
            f"### Visual Theme: **{self.theme}**\n",
            f"**Color Palette:** {' · '.join(self.color_palette)}\n",
            "---",
            "### Album Art Prompt (for Midjourney / DALL·E / Stable Diffusion)\n",
            f"```\n{self.album_art_prompt}\n```\n",
            "---",
            "### Video Scene Prompts (Runway / Kling / Pika)\n",
        ]
        for scene in self.video_scenes:
            lines.append(f"**[{scene['section']}]**")
            lines.append(f"- *Prompt:* {scene['prompt']}")
            if scene.get("camera"):
                lines.append(f"- *Camera:* {scene['camera']}")
            if scene.get("color"):
                lines.append(f"- *Color Grade:* {scene['color']}")
            lines.append("")
        lines += [
            "---",
            "### Style Guide (Reels / Shorts)\n",
            f"- **Filters:** {self.style_guide.get('filters', 'N/A')}",
            f"- **Font Style:** {self.style_guide.get('fonts', 'N/A')}",
            f"- **Transitions:** {self.style_guide.get('transitions', 'N/A')}",
            f"- **Aspect Ratio:** {self.style_guide.get('aspect_ratio', '9:16')}",
            f"- **Overlay FX:** {self.style_guide.get('overlay', 'N/A')}",
            "",
            "---",
            "### Keyword → Visual Theme Mapping\n",
            "| Keyword | Visual Element |",
            "|---------|----------------|",
        ]
        for kw, ve in self.keyword_map.items():
            lines.append(f"| `{kw}` | {ve} |")
        return "\n".join(lines)


class VisualGenerator:
    def generate(
        self,
        data: SunoPromptData,
        out_dir: Path = OUTPUT_DIR,
    ) -> tuple[VisualOutput, Path]:
        out_dir.mkdir(parents=True, exist_ok=True)

        keywords = self._extract_visual_keywords(data)
        theme = self._determine_theme(keywords, data)
        visual = self._generate_rule_based(data, keywords, theme)

        # Append visual section to existing report
        report_path = out_dir / "report.md"
        if report_path.exists():
            existing = report_path.read_text(encoding="utf-8")
            report_path.write_text(
                existing + "\n---\n\n" + visual.to_markdown(),
                encoding="utf-8",
            )

        # Also save standalone visual_prompts.md
        vp_path = out_dir / "visual_prompts.md"
        vp_path.write_text(
            f"# Visual Content Prompts\n\n*Title: {data.title}*\n\n" + visual.to_markdown(),
            encoding="utf-8",
        )
        return visual, vp_path

    # ------------------------------------------------------------------ #
    #  Rule-based generation
    # ------------------------------------------------------------------ #

    def _generate_rule_based(
        self,
        data: SunoPromptData,
        keywords: list[str],
        theme: str,
    ) -> VisualOutput:
        palette = self._palette_for_theme(theme)
        album_art = self._album_art_prompt(data, theme, keywords, palette)
        scenes = self._video_scenes(data, theme)
        style_guide = self._style_guide(theme, data)
        kw_map = self._keyword_visual_map(keywords, theme)

        return VisualOutput(
            theme=theme,
            color_palette=palette,
            album_art_prompt=album_art,
            video_scenes=scenes,
            style_guide=style_guide,
            keyword_map=kw_map,
        )

    # ------------------------------------------------------------------ #
    #  Prompt builders
    # ------------------------------------------------------------------ #

    def _album_art_prompt(
        self,
        data: SunoPromptData,
        theme: str,
        keywords: list[str],
        palette: list[str],
    ) -> str:
        genre_str = ", ".join(data.genre)
        mood_str = ", ".join(data.mood) if data.mood else "emotional"
        kw_str = ", ".join(keywords[:6])
        colors = ", ".join(palette[:3])

        theme_descs = {
            "Cyberpunk Dark":
                "dark cyberpunk cityscape, neon holographic glitch effects, ultra-detailed dystopian aesthetic",
            "Cyberpunk Neon":
                "neon-soaked cyberpunk city, vibrant electric colors, futuristic hologram overlays, lens flare",
            "Emotional Cinematic":
                "cinematic emotional scene, soft bokeh background, dramatic lighting, single subject focus",
            "Romantic Soft":
                "soft pastel romantic scene, warm golden hour light, delicate floral elements, dreamy atmosphere",
            "Melancholic Noir":
                "noir aesthetic, rain-soaked streets at night, monochromatic blue tones, lone figure silhouette",
            "Urban Cinematic":
                "urban rooftop at golden hour, city skyline bokeh, cinematic wide shot, street art elements",
            "Minimalist":
                "ultra-clean minimalist composition, single bold color accent, negative space, geometric shapes",
            "Vibrant Pop":
                "vibrant bold pop art aesthetic, saturated colors, dynamic composition, energetic visual rhythm",
            "Color-Saturated Artistic":
                "hyper-saturated color explosion, abstract paint splashes, artistic chaos, vivid pigment",
            "High Energy Dynamic":
                "explosive high-energy performance, dynamic light show, stage fog, crowd energy, peak moment freeze frame",
            "Atmospheric Moody":
                "atmospheric rain scene, moody blue-grey tones, reflections on wet pavement, cinematic wide angle",
            "Nocturnal Urban":
                "urban nightscape, city lights reflection, lone figure in darkness, high contrast dramatic lighting",
            "Dreamlike Surreal":
                "surreal dream sequence, double exposure, ethereal glow, floating elements, soft prismatic light",
            "Natural Organic":
                "organic natural setting, golden sunlight through trees, raw earth textures, authentic outdoor atmosphere",
            "Futuristic Sci-Fi":
                "futuristic sci-fi aesthetic, holographic interfaces, space-age technology, ultra-clean lines, zero gravity",
            "Retro Vintage":
                "retro vintage aesthetic, film grain, warm analog tones, nostalgic photography style, 70s-80s palette",
        }
        desc = theme_descs.get(theme, "moody cinematic album cover, professional photography")

        return (
            f"Album cover art, {genre_str} music, {mood_str} mood. "
            f"{desc}. "
            f"Color palette: {colors}. "
            f"Visual elements inspired by: {kw_str}. "
            f"Korean artist aesthetic, high-end music production, "
            f"square format (1:1), 4K resolution, ultra-detailed, "
            f"professional album cover photography, cinematic lighting. "
            f"--ar 1:1 --q 2 --style raw"
        )

    def _video_scenes(
        self,
        data: SunoPromptData,
        theme: str,
    ) -> list[dict]:
        scenes = []
        color_grade = self._color_grade(theme)

        section_templates = {
            # Longer / more-specific keys BEFORE their substrings so that
            # next(k for k in section_templates if k in name.lower()) matches correctly.
            "intro": {
                "camera": "Slow aerial drone pull-back, establishing shot",
                "desc": "Establishing wide shot. {theme} cityscape at night, "
                        "camera slowly pulling back from a single glowing light source, "
                        "revealing the urban landscape. Atmospheric haze, depth of field.",
            },
            "pre-chorus": {
                "camera": "Slow push-in, building tension",
                "desc": "Tension building sequence. Camera slowly pushing in on subject. "
                        "{theme} lighting intensifying, color grade shifting warmer. "
                        "Environment: {bg}, slight motion blur.",
            },
            "post-chorus": {
                "camera": "Slow pull-back, energy settling",
                "desc": "After the peak, atmosphere settling. Wide shot slowly pulling back. "
                        "{theme} lighting softening, energy dissipating. "
                        "Environment: {bg}, contemplative mood.",
            },
            "chorus": {
                "camera": "Dynamic 360° orbit, high energy",
                "desc": "High-energy dynamic shot. Artist at center, "
                        "dramatic {theme} lighting explosion, "
                        "particle effects and light streaks radiating outward. "
                        "Fast-paced cuts synchronized to beat. "
                        "Environment: {bg}, cinematic color grade.",
            },
            "hook": {
                "camera": "Dynamic 360° orbit, peak impact",
                "desc": "Peak-energy hook moment. Artist commanding frame, "
                        "{theme} light burst synchronized to hook rhythm. "
                        "Ultra-fast cuts, audience reaction shots intercut. "
                        "Environment: {bg}.",
            },
            "refrain": {
                "camera": "Wide shot to close-up, emotional pull",
                "desc": "Recurring emotional anchor. Wide pull to intimate close-up. "
                        "{theme} warm color grade, familiar visual motifs returning. "
                        "Background: {bg}, sense of emotional recognition.",
            },
            "breakdown": {
                "camera": "Extreme close-up details, fragmented cuts",
                "desc": "Stripped-down breakdown. Fragmented close-ups — hands, textures, details. "
                        "{theme} minimal elements, slow motion, high contrast. "
                        "Background: {bg}, sparse and atmospheric.",
            },
            "bridge": {
                "camera": "Overhead bird's eye, slow rotation",
                "desc": "Artistic transition sequence. Overhead perspective, "
                        "slow rotation. Abstract {theme} visual metaphor. "
                        "Color contrast shift, dreamlike quality, "
                        "layered visual elements, surreal environment.",
            },
            "build": {
                "camera": "Accelerating push-in, mounting tension",
                "desc": "Energy building toward the peak. Camera accelerating toward subject. "
                        "{theme} atmosphere charging, filters intensifying. "
                        "Background: {bg}, motion blur increasing with momentum. "
                        "Crowd/environment responding to the rising tension.",
            },
            "drop": {
                "camera": "Low-angle wide shot, explosive impact",
                "desc": "Peak energy drop moment. Ultra-low angle, wide frame exploding with "
                        "{theme} light and motion. Bass-impact visual shockwave radiating outward. "
                        "Ultra-fast beat-synced cuts, pyrotechnic or particle burst. "
                        "Environment: {bg}, visceral and overwhelming.",
            },
            "interlude": {
                "camera": "Static wide shot, contemplative stillness",
                "desc": "Meditative interlude. Static or very slow camera movement. "
                        "{theme} abstract visual elements, minimal motion. "
                        "Color palette shifting to cooler, introspective tones. "
                        "Background: {bg}, peaceful pause in the narrative.",
            },
            "verse": {
                "camera": "Handheld tracking shot, intimate close-up",
                "desc": "Intimate close-up of artist, {theme} aesthetic. "
                        "Soft rim lighting, shallow depth of field. "
                        "Background: blurred {bg}. "
                        "Emotional expression, micro-expressions visible.",
            },
            "rap": {
                "camera": "Low-angle handheld, energetic movement",
                "desc": "Urban energy sequence. Low-angle shot, "
                        "artist in {theme} street environment. "
                        "Fast cuts, urban textures, graffiti elements, "
                        "dynamic camera movement, high contrast.",
            },
            "spoken": {
                "camera": "Static medium shot, documentary style",
                "desc": "Intimate spoken word sequence. Static medium shot, natural lighting. "
                        "{theme} minimal environment, directional light on face. "
                        "Focus on authenticity and emotional truth. Background: {bg}.",
            },
            "skit": {
                "camera": "Handheld casual, candid documentary",
                "desc": "Candid skit sequence. Handheld camera, natural lighting. "
                        "{theme} casual environment, relaxed energy. "
                        "Authentic documentary-style, unstaged feel. Background: {bg}.",
            },
            "coda": {
                "camera": "Extreme long shot, slow fade to silence",
                "desc": "Final resolution. Extreme wide shot, figure receding into distance. "
                        "{theme} sky slowly darkening or brightening. "
                        "Very slow fade, poetic visual closure. Mirrors the intro composition.",
            },
            "outro": {
                "camera": "Long slow pull-back to wide shot, fade",
                "desc": "Emotional closing shot. Wide landscape, "
                        "single figure silhouette against {theme} sky. "
                        "Camera slowly pulling back, golden/twilight color grade. "
                        "Visual echo of opening scene, narrative closure.",
            },
        }

        bg_map = {
            "Cyberpunk Dark": "neon-lit underground club",
            "Cyberpunk Neon": "holographic billboard street",
            "Emotional Cinematic": "rain-soaked window interior",
            "Romantic Soft": "blooming flower garden at sunset",
            "Melancholic Noir": "empty rain-soaked rooftop",
            "Urban Cinematic": "city rooftop skyline",
            "Minimalist": "stark white studio with single light source",
            "Color-Saturated Artistic": "abstract painted backdrop",
            "Vibrant Pop": "bright neon dance studio",
            "High Energy Dynamic": "massive concert stage with pyrotechnics",
            "Atmospheric Moody": "rain-soaked empty street at night",
            "Nocturnal Urban": "empty city street at 3am",
            "Dreamlike Surreal": "floating dreamscape environment",
            "Natural Organic": "serene forest clearing at golden hour",
            "Futuristic Sci-Fi": "sleek futuristic space station interior",
            "Retro Vintage": "retro-styled room with vintage props",
        }
        bg = bg_map.get(theme, "atmospheric urban environment")

        for s in data.sections:
            section_key = next(
                (k for k in section_templates if k in s.name.lower()),
                "verse",
            )
            tmpl = section_templates[section_key]
            desc = tmpl["desc"].format(theme=theme, bg=bg)

            # Extract lyric keywords for this section
            section_kws = [w for w in s.all_words if len(w) > 2][:3]
            if section_kws:
                desc += f" Visual motifs: {', '.join(section_kws)}."

            scenes.append({
                "section": s.name,
                "prompt": desc,
                "camera": tmpl["camera"],
                "color": color_grade,
            })

        return scenes

    def _style_guide(self, theme: str, data: SunoPromptData) -> dict:
        guides = {
            "Cyberpunk Dark": {
                "filters": "Cyberpunk preset, Teal+Orange split tone, Heavy vignette, Grain +30",
                "fonts": "Bebas Neue / Rajdhani Bold — white with cyan glow, glitch animation",
                "transitions": "Glitch cut, RGB split, Digital dissolve",
                "overlay": "Scan lines, particle rain, holographic flicker",
            },
            "Cyberpunk Neon": {
                "filters": "Neon Punch preset, Vibrance +50, Hue shift -15, High contrast",
                "fonts": "Orbitron / Space Grotesk — neon purple with bloom effect",
                "transitions": "Flash cut, Electric wipe, Chromatic aberration",
                "overlay": "Neon particles, lens flare burst, electric sparks",
            },
            "Emotional Cinematic": {
                "filters": "Cinematic Teal preset, Fade highlights, Crush blacks, Film grain",
                "fonts": "Garamond / Cormorant Garamond Italic — off-white, fade-in animation",
                "transitions": "Cross-dissolve, Slow fade, Dreamy blur transition",
                "overlay": "Light leak, soft bokeh overlay, subtle vignette",
            },
            "Romantic Soft": {
                "filters": "Golden Hour preset, Warm tones +30, Soft glow, Reduce contrast",
                "fonts": "Playfair Display / Dancing Script — rose gold, elegant fade",
                "transitions": "Petal wipe, Soft dissolve, Bloom fade",
                "overlay": "Bokeh circles, golden dust particles, light flare",
            },
            "Melancholic Noir": {
                "filters": "Film Noir B&W, Crushed blacks, Silver tones, Heavy grain",
                "fonts": "Neue Haas Grotesk / Times New Roman — white on black, typewriter effect",
                "transitions": "Hard cut, Venetian blind, Film reel burn",
                "overlay": "Rain drops, static noise, vintage film scratches",
            },
            "Urban Cinematic": {
                "filters": "Urban preset, Warm shadows, Lifted blacks, Cinematic crop",
                "fonts": "Montserrat ExtraBold / Futura — white with drop shadow, slide-in",
                "transitions": "J-cut, Match cut on movement, Whip pan",
                "overlay": "City light bokeh, dust motes, heat shimmer",
            },
            "High Energy Dynamic": {
                "filters": "Vivid preset, High contrast, Warm tones, Motion blur, Saturation +30",
                "fonts": "Impact / Anton — yellow or white, bold shake animation",
                "transitions": "Flash cut, Hard cut on beat, Strobe effect",
                "overlay": "Fire particles, lens flare burst, crowd confetti",
            },
            "Atmospheric Moody": {
                "filters": "Moody Blue preset, Desaturate +20, Lift shadows, Heavy vignette",
                "fonts": "Georgia / Lora Italic — pale blue, slow fade-in",
                "transitions": "Rain wipe, Slow cross-dissolve, Fog transition",
                "overlay": "Rain drops on lens, mist overlay, water ripple",
            },
            "Nocturnal Urban": {
                "filters": "Nightlife preset, Crushed blacks, Neon glow, High contrast",
                "fonts": "Neue Haas / Helvetica Bold — white with neon glow",
                "transitions": "Hard cut, Neon flicker, Traffic light wipe",
                "overlay": "City bokeh, light streaks, dust in air",
            },
            "Dreamlike Surreal": {
                "filters": "Dreamy preset, Soft glow, Purple tint, Blur edges",
                "fonts": "Didot / Cormorant — lavender, float animation",
                "transitions": "Dream dissolve, Prism split, Morphing blend",
                "overlay": "Lens flare, soap bubble overlay, star sparkle",
            },
            "Natural Organic": {
                "filters": "Natural preset, Warm tones, Lifted shadows, Slight haze",
                "fonts": "Lato / Merriweather — earth brown, nature fade-in",
                "transitions": "Leaf wipe, Gentle dissolve, Sunbeam reveal",
                "overlay": "Bokeh leaves, golden dust, nature particles",
            },
            "Futuristic Sci-Fi": {
                "filters": "Cold Blue preset, High clarity, Desaturate warm tones, Glow",
                "fonts": "Rajdhani / Exo 2 — cyan with scanline flicker",
                "transitions": "Hologram glitch, Data stream wipe, Teleport flash",
                "overlay": "Holographic grid, data particles, scanline effect",
            },
            "Retro Vintage": {
                "filters": "Vintage Film preset, Warm tones, Heavy grain, Vignette",
                "fonts": "Courier New / Special Elite — aged sepia, typewriter reveal",
                "transitions": "Film burn, VHS rewind, Analogue scan",
                "overlay": "Film grain, light leaks, VHS tracking lines",
            },
        }
        default = {
            "filters": "Cinematic color grade, Vignette, Film grain",
            "fonts": "Clean sans-serif, Bold weight, Fade-in animation",
            "transitions": "Smooth cross-dissolve, Beat-synced cuts",
            "overlay": "Atmospheric particles, subtle light effects",
        }
        guide = guides.get(theme, default)
        guide["aspect_ratio"] = "9:16 (Reels/Shorts) / 16:9 (YouTube)"
        guide["bpm_sync"] = f"Cut on beat: every {int(60000/data.bpm)}ms ({data.bpm} BPM)"
        return guide

    # ------------------------------------------------------------------ #
    #  Utility
    # ------------------------------------------------------------------ #

    def _extract_visual_keywords(self, data: SunoPromptData) -> list[str]:
        stopwords = {
            "이", "가", "을", "를", "은", "는", "의", "에", "로", "으로",
            "와", "과", "도", "만", "에서", "나", "너", "그", "저",
            "a", "an", "the", "and", "or", "in", "on", "at", "to", "of",
            "is", "are", "was", "i", "you", "me", "my",
        }
        freq: dict[str, int] = {}
        for s in data.sections:
            for word in s.all_words:
                w = word.strip(".,!?\"'").lower()
                if w and w not in stopwords and len(w) >= 2:
                    freq[w] = freq.get(w, 0) + 1
        # Add mood/instrument keywords
        for m in data.mood:
            freq[m.lower()] = freq.get(m.lower(), 0) + 2
        for inst in data.instruments:
            freq[inst.lower()] = freq.get(inst.lower(), 0) + 1
        return sorted(freq, key=lambda k: freq[k], reverse=True)

    @staticmethod
    def _determine_theme(keywords: list[str], data: SunoPromptData) -> str:
        all_text = " ".join(
            keywords + data.mood + data.genre + data.instruments + data.vocal_style
        ).lower()
        scores: dict[str, int] = {}
        for kw, theme in VISUAL_THEME_MAP.items():
            if kw in all_text:
                scores[theme] = scores.get(theme, 0) + 1
        if scores:
            return max(scores, key=lambda k: scores[k])
        # Descriptor-tag fallback — scan tag clusters, pick highest-scoring theme
        for tag_set, theme in _TAG_THEME_RULES:
            for tag in tag_set:
                if tag in all_text:
                    scores[theme] = scores.get(theme, 0) + 1
        if scores:
            return max(scores, key=lambda k: scores[k])
        return "Urban Cinematic"

    @staticmethod
    def _palette_for_theme(theme: str) -> list[str]:
        palettes = {
            "Cyberpunk Dark": ["#0d0d1a", "#00f5ff", "#ff00aa", "#1a0533"],
            "Cyberpunk Neon": ["#0a0015", "#b300ff", "#00ffcc", "#ff6600"],
            "Emotional Cinematic": ["#1c1c2e", "#4a90d9", "#c8a96e", "#f5f0e8"],
            "Romantic Soft": ["#fff0f3", "#ffb3c1", "#c9ada7", "#f2e9e4"],
            "Melancholic Noir": ["#0a0a0a", "#2c2c2c", "#8a8a8a", "#d4d4d4"],
            "Urban Cinematic": ["#1a1a2e", "#e94560", "#f5a623", "#ffffff"],
            "Minimalist": ["#ffffff", "#f0f0f0", "#333333", "#000000"],
            "Vibrant Pop": ["#ff006e", "#fb5607", "#ffbe0b", "#8338ec"],
            "Color-Saturated Artistic": ["#ff4136", "#0074d9", "#2ecc40", "#ffdc00"],
            "High Energy Dynamic":      ["#ff4500", "#ff6600", "#ffcc00", "#1a0000"],
            "Atmospheric Moody":        ["#0d1b2a", "#1b4965", "#5fa8d3", "#bee9e8"],
            "Nocturnal Urban":          ["#0a0a0a", "#1a1a2e", "#e94560", "#f5a623"],
            "Dreamlike Surreal":        ["#e8d5f5", "#c3b1e1", "#9b72cf", "#6b4c93"],
            "Natural Organic":          ["#2d6a4f", "#52b788", "#d8f3dc", "#b7e4c7"],
            "Futuristic Sci-Fi":        ["#03045e", "#0077b6", "#00b4d8", "#90e0ef"],
            "Retro Vintage":            ["#b5838d", "#e5989b", "#ffb4a2", "#ffcdb2"],
        }
        return palettes.get(theme, ["#1a1a2e", "#e94560", "#f5a623", "#ffffff"])

    @staticmethod
    def _color_grade(theme: str) -> str:
        grades = {
            "Cyberpunk Dark": "Teal shadows, Magenta highlights, High contrast",
            "Cyberpunk Neon": "Purple-cyan split toning, Crushed blacks, Bloom highlights",
            "Emotional Cinematic": "Teal-orange grade, Lifted blacks, Film grain",
            "Romantic Soft": "Warm golden, Soft whites, Rose tint in shadows",
            "Melancholic Noir": "Desaturated, Blue-black shadows, Silver highlights",
            "Urban Cinematic":      "Orange-teal, Warm golden hour, High detail",
            "High Energy Dynamic":  "Warm reds, Fiery orange midtones, High contrast",
            "Atmospheric Moody":    "Cool blue shadows, Desaturated mids, Silver highlights",
            "Nocturnal Urban":      "Deep shadows, Neon accent lights, High contrast noir",
            "Dreamlike Surreal":    "Soft purple tones, Dreamy haze, Ethereal highlight bloom",
            "Natural Organic":      "Warm earth tones, Natural greens, Golden hour glow",
            "Futuristic Sci-Fi":    "Cold blue-white, Holographic shimmer, Deep space blacks",
            "Retro Vintage":        "Warm analog, Faded highlights, Nostalgic grain",
            "Minimalist":           "Clean whites, Neutral greys, Crisp blacks, No grade",
            "Vibrant Pop":          "Saturated primaries, Lifted shadows, High vibrance, Clean",
            "Color-Saturated Artistic": "Hyper-saturated hues, No crush, Maximum vibrance, Painterly",
        }
        return grades.get(theme, "Cinematic color grade, Subtle vignette")

    @staticmethod
    def _keyword_visual_map(keywords: list[str], theme: str) -> dict[str, str]:
        korean_visuals = {
            "색": "Color explosion / chromatic burst effect",
            "빛": "Light ray / God ray / lens flare",
            "밤": "Nighttime cityscape / neon reflection on wet pavement",
            "눈물": "Slow-motion tear drop / water splash macro",
            "불꽃": "Fire particles / ember floating upward",
            "꿈": "Dreamy double exposure / soft-focus ethereal glow",
            "비": "Rain on glass / slow-mo rain curtain",
            "별": "Star field / bokeh stars / galaxy background",
            "바람": "Flowing fabric / hair in wind / particle drift",
            "808": "Bass waveform visualization / subwoofer ripple effect",
            "bass": "Sound wave explosion / low-frequency pulse ring",
            "neon": "Neon sign flicker / electric glow / tube light",
        }
        result = {}
        for kw in keywords[:10]:
            if kw in korean_visuals:
                result[kw] = korean_visuals[kw]
            else:
                result[kw] = f"{kw.capitalize()} — {theme} visual motif"
        return result
