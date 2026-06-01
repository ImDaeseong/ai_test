"""
Suno AI prompt parser.
Handles both tag-based ([Genre: K-Pop]) and free-text formats.
"""
import re
from dataclasses import dataclass, field
from typing import Optional
from config import GENRE_TEMPO_MAP


@dataclass
class LyricsSection:
    name: str
    lyrics: list[str] = field(default_factory=list)
    chords: list[str] = field(default_factory=list)
    duration_hint: Optional[float] = None

    @property
    def text(self) -> str:
        return "\n".join(self.lyrics)

    @property
    def all_words(self) -> list[str]:
        words = []
        for line in self.lyrics:
            words.extend(line.split())
        return words

    # English words that are Suno style tags, not lyrics.
    # Skipped when a line also contains Korean content.
    _STYLE_WORDS: frozenset[str] = frozenset({
        "bpm", "bass", "drum", "beat", "kick", "snare", "hihat", "trap",
        "boombap", "boomba", "punchy", "gritty", "rawness", "subbass",
        "hiphop", "hip", "hop", "techno", "electronic", "acoustic",
        "male", "female", "vocal", "delivery", "heavyweight", "sincerity",
        "weirdness", "rhythmic", "buildup", "aggressive", "resonance",
        "artwork", "cover", "style", "influence", "authentic", "organic",
        "shaker", "heavy", "light", "fast", "slow", "hard", "soft",
        "dnb", "metal", "synth", "distortion", "reverb",
        # Instruments and production/gear terms embedded in Korean lines
        "guitar", "solo", "riff", "riffing", "strum", "strumming", "picking",
        "stroke", "downstroke", "upstroke",
        "gain", "tube", "amp", "mic", "feedback", "signal",
        "thumping", "visceral", "drummer", "drums", "drumming",
        "counts", "count", "counting",
        # Vocal/performance direction words embedded in Korean lines
        "breathy", "breathe", "breathing", "hushed", "whisper", "whispered", "airy",
        "falsetto", "vibrato", "melisma", "spoken", "adlib",
        "emotional", "swell", "intake", "texture", "intensity",
        "climax", "echo", "harmony", "harmonize", "unison",
        # Section/production end markers
        "end", "fade", "outro", "coda", "finale", "finish",
        "begin", "start", "intro", "buildup", "breakdown",
        # English stopwords: filtered in Korean-dominant lines (not standalone syllables)
        "a", "an", "the", "of", "in", "on", "at", "to", "by", "or",
        "and", "with", "for", "from", "as", "its",
    })

    @property
    def syllables(self) -> list[str]:
        """
        Split text into lyric units for LilyPond.
        Korean: each syllable block = one unit.
        English: each whole word = one unit.
        Style-descriptor lines and style-tag words are skipped.
        """
        sylls = []
        for line in self.lyrics:
            if SunoParser._is_style_descriptor(line):
                continue
            # Lines mixing Korean + English style tags: skip the English style words
            has_korean = sum(1 for c in line if "가" <= c <= "힣") >= 2
            i = 0
            while i < len(line):
                ch = line[i]
                if "가" <= ch <= "힣":
                    sylls.append(ch)
                    i += 1
                elif ch.isalpha():
                    word = ""
                    while i < len(line) and line[i].isalpha():
                        word += line[i]
                        i += 1
                    if word and (not has_korean or word.lower() not in LyricsSection._STYLE_WORDS):
                        sylls.append(word.lower())
                else:
                    i += 1
        return sylls


@dataclass
class SunoPromptData:
    title: str = "Untitled"
    artist: str = "Unknown Artist"
    genre: list[str] = field(default_factory=list)
    bpm: int = 0  # 0 = not yet set; _infer_missing fills from genre map
    key: str = "C"
    mood: list[str] = field(default_factory=list)
    instruments: list[str] = field(default_factory=list)
    vocal_style: list[str] = field(default_factory=list)
    sections: list[LyricsSection] = field(default_factory=list)
    chord_progression: list[str] = field(default_factory=list)
    raw_prompt: str = ""
    time_signature: str = "4/4"
    language: str = "Korean"

    @property
    def primary_genre(self) -> str:
        return self.genre[0].lower() if self.genre else "pop"

    @property
    def has_lyrics(self) -> bool:
        return any(s.lyrics for s in self.sections)

    @property
    def total_lines(self) -> int:
        return sum(len(s.lyrics) for s in self.sections)

    @property
    def all_lyrics_text(self) -> str:
        parts = []
        for s in self.sections:
            if s.lyrics:
                parts.append(f"[{s.name}]\n{s.text}")
        return "\n\n".join(parts)

    def section_by_name(self, name: str) -> Optional[LyricsSection]:
        name_lower = name.lower()
        for s in self.sections:
            if s.name.lower() == name_lower:
                return s
        return None


_SEC_NAMES = (
    # Longer / more-specific names BEFORE their substrings
    r"Intro|Outro|"
    r"Build(?:[\s\-]?[Uu]p)?|"
    r"Verse(?:\s*(?:\d+|Rap))?|"
    r"Pre[-\s]?Chorus|"
    r"Post[-\s]?Chorus|"
    r"Chorus|Hook|Refrain|"
    r"Drop|Breakdown|Bridge|"
    r"Interlude|"
    r"Rap(?:\s*\d*)?|Spoken(?:\s*Word)?|Skit(?:\s*\d*)?|"
    r"Coda|Fade(?:\s*Out)?"
)


class SunoParser:
    _METADATA_PATTERN = re.compile(
        r"\[(?P<key>[A-Za-z\s]+):\s*(?P<value>[^\]]+)\]",
        re.IGNORECASE,
    )
    # [Verse 1]  or  [Verse 1: style description...]
    _SECTION_PATTERN = re.compile(
        r"\[(?P<name>" + _SEC_NAMES + r")(?:[:\s][^\]]*)?\]",
        re.IGNORECASE,
    )
    # (Verse 1)  or  (Chorus)
    _SECTION_PAREN = re.compile(
        r"\((?P<name>" + _SEC_NAMES + r")(?:[:\s][^)]*)?\)",
        re.IGNORECASE,
    )
    # Bare line: just  "Verse 1"  or  "Pre-Chorus"  (nothing else on the line)
    _SECTION_BARE = re.compile(
        r"^(?P<name>" + _SEC_NAMES + r")(?:\s*[:\-][^\n]*)?$",
        re.IGNORECASE,
    )
    _CQ = (
        r"(?:m7b5|m7-5|maj13|maj11|maj9|maj7|maj"
        r"|m13|m11|m9|m7|m6|m"
        r"|dim7|dim|aug7|aug"
        r"|7sus4|sus4|sus2"
        r"|add9|add11"
        r"|13|11|9|7|6|5)?"
    )
    _CN = r"[A-G][b#]?"
    _CHORD_INLINE = re.compile(
        r"\((" + _CN + _CQ + r"(?:/" + _CN + r")?)\)"
    )
    _CHORD_PROGRESSION = re.compile(
        r"(" + _CN + _CQ + r")"
        r"(?:\s*[-–]\s*" + _CN + _CQ + r"){2,}"
    )

    def parse(self, prompt_text: str) -> SunoPromptData:
        data = SunoPromptData(raw_prompt=prompt_text)
        lines = prompt_text.strip().splitlines()

        metadata_lines, body_lines = self._split_metadata_body(lines)
        self._parse_metadata(metadata_lines, data)
        self._parse_sections(body_lines, data)
        self._infer_missing(data)
        self._detect_language(data)
        return data

    def parse_file(self, path: str) -> SunoPromptData:
        with open(path, "r", encoding="utf-8") as f:
            return self.parse(f.read())

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _match_section(self, stripped: str) -> Optional[re.Match]:
        """Try all three section marker formats and return the first match."""
        return (
            self._SECTION_PATTERN.match(stripped)
            or self._SECTION_PAREN.match(stripped)
            or self._SECTION_BARE.match(stripped)
        )

    def _split_metadata_body(self, lines: list[str]):
        metadata, body, in_body = [], [], False
        for line in lines:
            if self._match_section(line.strip()):
                in_body = True
            if not in_body and self._METADATA_PATTERN.match(line.strip()):
                metadata.append(line)
            else:
                body.append(line)
        if not body:
            return metadata, lines
        return metadata, body

    def _parse_metadata(self, lines: list[str], data: SunoPromptData):
        for line in lines:
            m = self._METADATA_PATTERN.match(line.strip())
            if not m:
                continue
            key = m.group("key").strip().lower()
            value = m.group("value").strip()

            if key in ("genre", "style"):
                data.genre = [g.strip() for g in re.split(r"[,/]", value)]
            elif key == "bpm":
                try:
                    data.bpm = int(re.search(r"\d+", value).group())
                except (AttributeError, ValueError):
                    pass
            elif key == "key":
                data.key = self._normalize_key(value)
            elif key == "mood":
                data.mood = [tok.strip() for tok in re.split(r"[,/]", value)]
            elif key in ("instruments", "instrument"):
                data.instruments = [i.strip() for i in re.split(r"[,/]", value)]
            elif key in ("vocal", "vocal style", "vocals"):
                data.vocal_style = [v.strip() for v in re.split(r"[,/]", value)]
            elif key == "title":
                data.title = value
            elif key == "artist":
                data.artist = value
            elif key in ("chord", "chords", "chord progression"):
                data.chord_progression = self._extract_chord_list(value)
            elif key in ("time", "time signature"):
                data.time_signature = self._normalize_time_signature(value)

        # Also scan free-text for BPM / key / genre hints
        full_text = " ".join(lines)
        if not data.bpm:
            bm = re.search(r"(\d{2,3})\s*(?:bpm|BPM)", full_text)
            if bm:
                data.bpm = int(bm.group(1))

        if not data.genre:
            for genre in GENRE_TEMPO_MAP:
                if genre in full_text.lower():
                    data.genre.append(genre)
                    break

    def _parse_sections(self, lines: list[str], data: SunoPromptData):
        current_section: Optional[LyricsSection] = None
        found_any_section = False
        pre_section: Optional[LyricsSection] = None  # fallback before first marker

        for line in lines:
            stripped = line.strip()
            sm = self._match_section(stripped)
            if sm:
                if current_section is not None:
                    data.sections.append(current_section)
                current_section = LyricsSection(name=sm.group("name").title())
                found_any_section = True
                continue

            if current_section is not None and stripped:
                # Skip Suno style descriptor lines (e.g. "K-Hip Hop, Heavy Drums, Male Vocal...")
                if self._is_style_descriptor(stripped):
                    continue
                # Extract inline chords e.g. "(Am) 가사 (F) 가사"
                chords = self._CHORD_INLINE.findall(stripped)
                if chords:
                    current_section.chords.extend(chords)
                lyric_line = self._CHORD_INLINE.sub("", stripped).strip()
                if lyric_line:
                    current_section.lyrics.append(lyric_line)
            elif not found_any_section and stripped:
                # No section markers yet — collect into a fallback verse
                if current_section is None:
                    current_section = LyricsSection(name="Verse 1")
                    pre_section = current_section
                cp = self._CHORD_PROGRESSION.search(stripped)
                if cp:
                    data.chord_progression.extend(
                        self._extract_chord_list(stripped)
                    )
                elif stripped:
                    current_section.lyrics.append(stripped)

        if current_section is not None:
            data.sections.append(current_section)

        # Drop the pre-section fallback when a real section with the same name exists.
        # The fallback is created from content before the first [SectionName] marker
        # and often contains only style descriptors, not actual lyrics.
        if pre_section is not None and pre_section in data.sections:
            proper = [s for s in data.sections if s is not pre_section]
            if any(s.name == pre_section.name for s in proper):
                data.sections.remove(pre_section)

        # Pull global chord progression from any section if still empty
        if not data.chord_progression:
            for s in data.sections:
                if s.chords:
                    data.chord_progression.extend(s.chords)
                    break

    def _infer_missing(self, data: SunoPromptData):
        if not data.genre:
            data.genre = ["Pop"]
        if not data.bpm:
            genre_lower = data.primary_genre
            data.bpm = GENRE_TEMPO_MAP.get(genre_lower, 120)
        if not data.key:
            data.key = "C"
        if not data.chord_progression:
            genre_tags = " ".join(data.genre + data.mood + data.instruments).lower()
            data.chord_progression = self._default_progression(data.key, genre_tags)
        if not data.sections:
            data.sections = [LyricsSection(name="Verse 1")]
        # Estimate section durations (heuristic: 4 bars each at given BPM)
        beats_per_bar, _ = self._parse_time_signature(data.time_signature)
        for s in data.sections:
            bars = max(4, len(s.lyrics) * 2)
            seconds_per_bar = (60.0 / max(data.bpm, 1)) * beats_per_bar
            s.duration_hint = bars * seconds_per_bar

    def _detect_language(self, data: SunoPromptData):
        all_text = " ".join(
            word for s in data.sections for word in s.all_words
        )
        korean_chars = sum(1 for c in all_text if "가" <= c <= "힣")
        ascii_chars = sum(1 for c in all_text if c.isascii() and c.isalpha())
        if korean_chars > ascii_chars:
            data.language = "Korean"
        elif korean_chars > 0:
            data.language = "Mixed (Korean/English)"
        else:
            data.language = "English"

    @staticmethod
    def _normalize_key(raw: str) -> str:
        raw = raw.strip()
        m = re.match(r"([A-Gb#]+)\s*(minor|major|min|maj|m\b)?", raw, re.IGNORECASE)
        if not m:
            return "C"
        root = m.group(1).capitalize()
        quality = (m.group(2) or "").lower()
        if quality in ("minor", "min", "m"):
            return root + "m"
        return root

    @staticmethod
    def _extract_chord_list(text: str) -> list[str]:
        return re.findall(
            r"[A-G][b#]?(?:m7b5|m7-5|maj13|maj11|maj9|maj7|maj"
            r"|m13|m11|m9|m7|m6|m|dim7|dim|aug7|aug"
            r"|7sus4|sus4|sus2|add9|add11|13|11|9|7|6|5)?",
            text,
        )

    @staticmethod
    def _parse_time_signature(value: str) -> tuple[int, int]:
        m = re.match(r"^\s*(\d{1,2})\s*/\s*(\d{1,2})\s*$", value or "")
        if not m:
            return 4, 4
        numerator = int(m.group(1))
        denominator = int(m.group(2))
        if numerator < 1 or denominator not in {1, 2, 4, 8, 16, 32}:
            return 4, 4
        return numerator, denominator

    @classmethod
    def _normalize_time_signature(cls, value: str) -> str:
        numerator, denominator = cls._parse_time_signature(value)
        return f"{numerator}/{denominator}"

    @staticmethod
    def _default_progression(key: str, genre_tags: str = "") -> list[str]:
        """Return a genre-appropriate 4-chord progression for the given key."""
        # Diatonic I-vi-IV-V (major) / i-VI-III-VII (minor) per key
        _base: dict[str, list[str]] = {
            "C":   ["C",   "Am",  "F",   "G"],
            "Db":  ["Db",  "Bbm", "Gb",  "Ab"],
            "C#":  ["C#",  "A#m", "F#",  "G#"],
            "D":   ["D",   "Bm",  "G",   "A"],
            "Eb":  ["Eb",  "Cm",  "Ab",  "Bb"],
            "D#":  ["D#",  "Cm",  "G#",  "A#"],
            "E":   ["E",   "C#m", "A",   "B"],
            "F":   ["F",   "Dm",  "Bb",  "C"],
            "F#":  ["F#",  "D#m", "B",   "C#"],
            "Gb":  ["Gb",  "Ebm", "B",   "Db"],
            "G":   ["G",   "Em",  "C",   "D"],
            "Ab":  ["Ab",  "Fm",  "Db",  "Eb"],
            "G#":  ["G#",  "Fm",  "C#",  "D#"],
            "A":   ["A",   "F#m", "D",   "E"],
            "Bb":  ["Bb",  "Gm",  "Eb",  "F"],
            "A#":  ["A#",  "Gm",  "D#",  "F"],
            "B":   ["B",   "G#m", "E",   "F#"],
            "Cm":  ["Cm",  "Ab",  "Eb",  "Bb"],
            "C#m": ["C#m", "A",   "E",   "B"],
            "Dbm": ["Dbm", "A",   "E",   "B"],
            "Dm":  ["Dm",  "Bb",  "F",   "C"],
            "D#m": ["D#m", "B",   "F#",  "C#"],
            "Ebm": ["Ebm", "B",   "Gb",  "Db"],
            "Em":  ["Em",  "C",   "G",   "D"],
            "Fm":  ["Fm",  "Db",  "Ab",  "Eb"],
            "F#m": ["F#m", "D",   "A",   "E"],
            "Gbm": ["Gbm", "D",   "A",   "E"],
            "Gm":  ["Gm",  "Eb",  "Bb",  "F"],
            "G#m": ["G#m", "E",   "B",   "F#"],
            "Abm": ["Abm", "E",   "B",   "F#"],
            "Am":  ["Am",  "F",   "C",   "G"],
            "A#m": ["A#m", "F#",  "C#",  "G#"],
            "Bbm": ["Bbm", "Gb",  "Db",  "Ab"],
            "Bm":  ["Bm",  "G",   "D",   "A"],
        }
        base = _base.get(key, ["C", "Am", "F", "G"])
        I, vi, IV, V = base[0], base[1], base[2], base[3]

        t = genre_tags.lower()
        def has(*kws: str) -> bool:
            return any(k in t for k in kws)

        if has("blues"):
            # I7 - IV7 - V7 - IV7 (blues turnaround)
            return [I + "7", IV + "7", V + "7", IV + "7"]

        if has("jazz", "bebop", "bossa", "swing", "cool jazz"):
            # vi7 - V7 - Imaj7 - IVmaj7 (ii-V-I feel)
            return [vi + "7", V + "7", I + "maj7", IV + "maj7"]

        if has("r&b", "rnb", "neo soul", "soul", "funk"):
            # Imaj7 - vi7 - IVmaj7 - V7
            return [I + "maj7", vi + "7", IV + "maj7", V + "7"]

        if has("trap", "drill", "phonk", "dark trap"):
            # i - VI - III - VII (minor-key trap feel)
            return [I, vi, IV, vi]

        if has("pop", "edm", "dance", "kpop", "k-pop", "k pop",
               "synthwave", "retrowave", "hyperpop", "future bass"):
            # I - V - vi - IV  (Axis / four-chord pop)
            return [I, V, vi, IV]

        if has("rock", "punk", "metal", "grunge", "hardcore"):
            # I - IV - V - I
            return [I, IV, V, I]

        if has("reggae", "dancehall", "dub"):
            # I - IV - I - V
            return [I, IV, I, V]

        if has("folk", "country", "bluegrass", "acoustic", "singer-songwriter"):
            # I - IV - V - IV
            return [I, IV, V, IV]

        if has("classical", "orchestral", "baroque", "cinematic"):
            # I - V - IV - V
            return [I, V, IV, V]

        # Default: I - vi - IV - V
        return base

    @staticmethod
    def _is_style_descriptor(line: str) -> bool:
        """
        Return True if line is a Suno sound/style descriptor, NOT actual lyrics.

        Suno prompts often embed style tags inside sections, e.g.:
          [Verse 1]
          K-Hip Hop, Hard hitting, Boomba p, Heavy Drums, Male Deep Voice...  ← descriptor
          오늘도 알람은 눈치 없이 울려 대고                                    ← lyrics
        """
        stripped = line.strip()
        if not stripped or len(stripped) < 4:
            return False

        # Any significant Korean content → lyrics, not descriptor
        korean = sum(1 for c in stripped if "가" <= c <= "힣")
        if korean >= 2:
            return False

        ascii_alpha = sum(1 for c in stripped if c.isascii() and c.isalpha())
        total = max(len(stripped), 1)

        # ≥3 comma-separated items that are mostly ASCII → style descriptor
        if stripped.count(",") >= 2:
            parts = [p.strip() for p in stripped.split(",")]
            ascii_parts = sum(
                1 for p in parts if sum(1 for c in p if c.isascii() and c.isalpha()) > 0
            )
            if ascii_parts / max(len(parts), 1) >= 0.7:
                return True

        # Known Suno style keywords — if ≥2 appear, treat as descriptor
        _STYLE_KW = {
            "bpm", "bass", "drum", "beat", "kick", "snare", "hihat", "hi-hat",
            "hip hop", "hiphop", "trap", "boombap", "boomba", "punchy", "gritty",
            "rawness", "subbass", "sub bass", "high fidelity", "style influence",
            "male", "female", "vocal", "vocals", "delivery", "heavyweight", "sincerity",
            "dnb", "techno", "electronic", "metal", "acoustic", "shaker",
            "weirdness", "rhythmic", "buildup", "aggressive", "resonance",
            "fast tempo", "slow tempo", "light pop", "dark mood",
            "artwork", "cover art", "style guide", "authentic", "organic",
            "distortion", "reverb", "ambient", "atmospheric", "cinematic",
            "instrumental", "lo-fi", "lofi", "hifi", "hi-fi",
            # Guitar / instrument production terms
            "guitar", "riffing", "strumming", "picking",
            "gain", "tube amp", "feedback", "mic",
            "thumping", "drummer", "drumming",
            "visceral", "stroke", "downstroke",
            "counts", "counting",
            # Transition / effect / structure direction words
            "glitch", "transition", "subtle", "fill",
            "energy", "postlude", "percussive", "outro",
        }
        lower = stripped.lower()
        matches = sum(1 for kw in _STYLE_KW if kw in lower)
        if matches >= 2:
            return True

        # Line is >70% ASCII alpha and longer than 40 chars with no sentence punctuation → descriptor
        if ascii_alpha / total > 0.7 and len(stripped) > 40 and "." not in stripped:
            return True

        # Short pure-English vocal/performance direction lines with no Korean
        # e.g. "breathy", "emotional swell", "guitar solo", "breath intake"
        if korean == 0:
            _VOCAL_DIR = {
                "breathy", "breathe", "breath", "breathing", "intake", "airy",
                "whisper", "whispered", "hushed",
                "emotional", "emotion", "swell", "peak", "climax",
                "dynamic", "power", "texture",
                "falsetto", "vibrato", "melisma", "spoken", "adlib",
                "intensity", "build", "drop", "lift", "fade",
                "echo", "harmony", "harmonize", "unison",
                "end", "fade", "outro", "coda", "finale", "finish",
                "begin", "start", "intro", "buildup", "breakdown",
                "interlude", "solo", "instrumental",
                # Instrument / gear direction
                "guitar", "riff", "riffing", "strum", "strumming",
                "lead", "rhythm", "chord", "melody",
                "improv", "improvise",
                "loud", "gain", "amp", "mic", "feedback",
                "aggressive", "visceral", "thumping",
                # Transition / effect / structure direction words
                "glitch", "transition", "subtle", "fill",
                "energy", "postlude", "percussive",
                "clean", "short", "sudden", "vocals",
            }
            words = re.findall(r"[a-zA-Z]+", stripped.lower())
            if 1 <= len(words) <= 4 and all(w in _VOCAL_DIR for w in words):
                return True

            # Pure-English lines where ≥60% of words are production/style vocabulary
            _PROD_VOCAB = _VOCAL_DIR | {
                "soft", "heavy", "light", "fast", "slow",
                "tube", "signal",
                "bass", "drum", "drums", "drummer", "cymbal", "kick", "snare",
                "stroke", "downstroke", "upstroke", "picking",
                "counts", "count", "counting",
                "one", "two", "three", "four", "five", "six", "seven", "eight",
                "pounding", "driving", "grinding",
                "cut", "off",
            }
            if len(words) >= 3:
                prod_count = sum(1 for w in words if w in _PROD_VOCAB)
                if prod_count / len(words) >= 0.6:
                    return True

        return False
