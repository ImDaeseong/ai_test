"""
LilyPond (.ly) sheet music generator from parsed Suno prompt data.
Produces: melody stub, chord names, and lyrics for each section.

Melody patterns are derived dynamically from musical attributes
(BPM, key mode, instruments, mood, time signature, section role)
rather than fixed genre-name lookups — so any genre combination works.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

from config import CHORD_TO_LILYPOND, KEY_TO_LILYPOND, OUTPUT_DIR
from analyzer.suno_parser import SunoPromptData, LyricsSection


import re as _re

# Default minimum bars per section when syllable count is small.
_MAX_BARS = 8

# Root note → LilyPond pitch name
_NOTE_TO_LILY: dict[str, str] = {
    "C": "c",  "D": "d",  "E": "e",  "F": "f",
    "G": "g",  "A": "a",  "B": "b",
    "C#": "cis", "D#": "dis", "E#": "f",  "F#": "fis",
    "G#": "gis", "A#": "ais", "B#": "c",
    "Cb": "b",  "Db": "des", "Eb": "ees", "Fb": "e",
    "Gb": "ges", "Ab": "aes", "Bb": "bes",
}

# Quality tokens ordered longest → shortest to avoid partial matches
_CHORD_QUALITIES: list[tuple[str, str]] = [
    ("m7b5", "m7.5-"), ("m7-5", "m7.5-"),
    ("maj13", "maj13"), ("maj11", "maj11"), ("maj9", "maj9"), ("maj7", "maj7"),
    ("maj", "maj7"),
    ("m13", "m13"), ("m11", "m11"), ("m9", "m9"), ("m7", "m7"), ("m6", "m6"),
    ("m", "m"),
    ("dim7", "dim7"), ("dim", "dim"),
    ("aug7", "aug.7"), ("aug", "aug"),
    ("7sus4", "7sus4"), ("sus4", "sus4"), ("sus2", "sus2"),
    ("13", "13"), ("11", "11"), ("9", "9"), ("7", "7"), ("6", "6"), ("5", "5"),
]


def _chord_to_lily(chord: str) -> str:
    """Convert any chord symbol to LilyPond chordmode format.

    Examples: "Cmaj9" → "c1:maj9", "F#m7b5" → "fis1:m7.5-", "C/G" → "c1/g"
    Falls back to CHORD_TO_LILYPOND lookup first for speed.
    """
    if chord in CHORD_TO_LILYPOND:
        ly = CHORD_TO_LILYPOND[chord]
        if ":" in ly:
            root_part, mod = ly.split(":", 1)
            return f"{root_part}1:{mod}"
        return f"{ly}1"

    c = chord.strip()
    slash = ""
    if "/" in c:
        c, bass = c.rsplit("/", 1)
        bass = bass.strip()
        b_root = bass[:2] if len(bass) >= 2 and bass[1] in "#b" else bass[:1]
        slash = "/" + _NOTE_TO_LILY.get(b_root, b_root.lower())

    if len(c) >= 2 and c[1] in "#b":
        root, rest = c[:2], c[2:]
    elif c:
        root, rest = c[0], c[1:]
    else:
        return "c1"

    root_ly = _NOTE_TO_LILY.get(root, root.lower())

    quality = ""
    for token, lily_q in _CHORD_QUALITIES:
        if rest.startswith(token):
            quality = lily_q
            rest = rest[len(token):]
            break

    # Remaining alterations: b5 → .5-, #9 → .9+, add9 → .9
    rest = _re.sub(r"add(\d+)", r".\1", rest)
    rest = _re.sub(r"b(\d+)", r".\1-", rest)
    rest = _re.sub(r"#(\d+)", r".\1+", rest)

    modifier = quality + rest
    return f"{root_ly}1:{modifier}{slash}" if modifier else f"{root_ly}1{slash}"

# Beat value map: LilyPond duration string → quarter-note beats
_BEAT: dict[str, float] = {
    "1": 4.0, "2": 2.0, "4": 1.0, "8": 0.5, "16": 0.25, "32": 0.125,
    "2.": 3.0, "4.": 1.5, "8.": 0.75,
}


def _parse_time_signature(value: str) -> tuple[str, str, float]:
    m = _re.match(r"^\s*(\d{1,2})\s*/\s*(\d{1,2})\s*$", value or "")
    if not m:
        return "4/4", "4", 4.0
    numerator = int(m.group(1))
    denominator = int(m.group(2))
    if numerator < 1 or denominator not in {1, 2, 4, 8, 16, 32}:
        return "4/4", "4", 4.0
    # Convert to quarter-note-equivalent beats: 6/8 → 3.0, 4/4 → 4.0, 3/4 → 3.0
    beats = (numerator / denominator) * 4.0
    return f"{numerator}/{denominator}", str(denominator), beats


def _lily_string(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _lily_lyric_token(value: str) -> str:
    return f'"{_lily_string(value)}"'

# ─────────────────────────────────────────────────────────────────────────────
#  Music profile — derived at runtime from parsed song data
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class _MusicProfile:
    """All musical attributes needed to build a melody pattern."""
    rhythm: str          # "trap" | "syncopated" | "driving" | "swing" | "flowing" | "straight"
    is_minor: bool
    bpm: int
    beats_per_bar: float


def _derive_profile(data: SunoPromptData) -> _MusicProfile:
    """
    Infer rhythm style and key mode from the song's actual metadata.

    No genre-name lookup table — works by reading the instruments,
    mood, vocal style, and BPM that are already parsed from the prompt.
    New or hybrid genres (K-Trap R&B, Melodic Drill, Future Bass …) are
    handled automatically because the decision is based on descriptors,
    not the genre label itself.
    """
    # Build one normalised tag string from every descriptive field
    raw = " ".join(data.genre + data.instruments + data.mood + data.vocal_style)
    tags = _re.sub(r"[^a-z0-9 ]", " ", raw.lower())

    def has(*kws: str) -> bool:
        return any(kw in tags for kw in kws)

    # Rhythm style — evaluated in priority order (most specific first)
    if has("trap", "drill", "808", "glitch"):
        rhythm = "trap"
    elif has("hip hop", "hiphop", "rap", "boom bap", "boombap", "grime"):
        rhythm = "syncopated"
    elif has("edm", "electronic", "techno", "house", "dance", "dubstep", "rave", "trance"):
        rhythm = "driving"
    elif has("jazz", "swing", "blues", "bossa", "soul", "funk"):
        rhythm = "swing"
    elif has("ballad", "acoustic", "slow", "gentle", "lo-fi", "lofi", "ambient", "chill"):
        rhythm = "flowing"
    elif data.bpm <= 80:
        rhythm = "flowing"
    elif data.bpm >= 140:
        rhythm = "driving"
    else:
        rhythm = "straight"

    _, key_mode = KEY_TO_LILYPOND.get(data.key, ("c", "\\major"))
    is_minor = "\\minor" in key_mode

    _, _, beats_per_bar = _parse_time_signature(data.time_signature)

    return _MusicProfile(
        rhythm=rhythm,
        is_minor=is_minor,
        bpm=data.bpm,
        beats_per_bar=beats_per_bar,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Bar pattern builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_bar_pattern(profile: _MusicProfile, section_name: str) -> list[tuple[str, str]]:
    """
    Return one bar of (note, duration) pairs for the given profile and section.

    Scale degrees are written relative to \\relative c' so that
    \\transpose in _section_block moves everything to the actual key.

    Minor key uses A-natural-minor scale degrees (a,=A4, c=C5 …).
    Major key uses C-major scale degrees (c=C5, e=E5 …).

    Beat totals are verified to equal profile.beats_per_bar exactly.
    """
    b = profile.beats_per_bar
    bpm = profile.bpm
    sec = section_name.lower()

    # ── Scale degree note names in \\relative c' ──────────────────────────
    if profile.is_minor:
        # A natural minor degrees 1–5 (a,=A4 … e=E5 in \relative c')
        d1, d2, d3, d4, d5 = "a,", "b,", "c", "d", "e"
    else:
        # C major degrees 1–5 (c=C5 … g=G5 in \relative c')
        d1, d2, d3, d4, d5 = "c", "d", "e", "f", "g"

    # ── Melodic contour per section role ─────────────────────────────────
    def is_sec(*keys): return any(k in sec for k in keys)

    # Longer / more-specific names checked before their substrings.
    # "pre-chorus" before "chorus"; "post-chorus" before "chorus";
    # "breakdown" before "down"; "verse rap" before "verse"/"rap".
    if is_sec("pre-chorus", "prechorus", "pre chorus", "pre chor", "lift"):
        # Ascending build toward 5th
        m = [d3, d4, d5, d5]
    elif is_sec("post-chorus", "postchorus", "post chorus"):
        # After peak — settling: 5th→3rd→root
        m = [d5, d3, d1, d3]
    elif is_sec("chorus", "hook", "refrain"):
        # Peak: 5th–3rd–root–2nd
        m = [d5, d3, d1, d2]
    elif is_sec("drop"):
        # EDM drop — root punch then climb
        m = [d1, d1, d3, d5]
    elif is_sec("build"):
        # Gradual ascent
        m = [d1, d2, d4, d5]
    elif is_sec("breakdown", "interlude"):
        # Sparse / contrast — low movement
        m = [d1, d3, d2, d1]
    elif is_sec("bridge"):
        # Contrast: descend from 4th
        m = [d4, d3, d2, d1]
    elif is_sec("outro", "coda", "fade"):
        # Resolution to root
        m = [d3, d2, d1, d1]
    elif is_sec("intro"):
        # Open: root–5th oscillation
        m = [d1, d5, d1, d5]
    elif is_sec("rap", "spoken", "verse rap", "skit"):
        # Tight range around root
        m = [d1, d2, d3, d1]
    else:
        # Verse / default: root–3rd–5th–3rd
        m = [d1, d3, d5, d3]

    r = profile.rhythm

    # ── 3/4 time (3 beats per bar) ────────────────────────────────────────
    if b < 3.5:
        if r == "trap":
            # 0.5+0.25+0.25+0.5+0.5+1 = 3.0
            return [(m[0], "8"), ("r", "16"), (m[1], "16"),
                    (m[2], "8"), ("r", "8"), (m[3], "4")]
        if r == "syncopated":
            # 1+0.5+0.5+1 = 3.0
            return [(m[0], "4"), (m[1], "8"), ("r", "8"), (m[2], "4")]
        if r == "driving":
            # 0.5+0.5+0.5+0.5+1 = 3.0
            return [(m[0], "8"), (m[1], "8"), (m[2], "8"), (m[1], "8"), (m[0], "4")]
        if r == "swing":
            # 1.5+1+0.5 = 3.0
            return [(m[0], "4."), (m[1], "4"), (m[2], "8")]
        if r == "flowing":
            # 2+1 = 3.0
            return [(m[0], "2"), (m[1], "4")]
        # straight: 1+1+1 = 3.0
        return [(m[0], "4"), (m[1], "4"), (m[2], "4")]

    # ── 4/4 time (4 beats per bar, default) ──────────────────────────────
    if r == "trap":
        # 0.5+0.25+0.25+0.5+0.5+1+1 = 4.0
        return [(m[0], "8"), ("r", "16"), (m[1], "16"),
                (m[2], "8"), ("r", "8"), (m[3], "4"), ("r", "4")]
    if r == "syncopated":
        # 0.5+0.5+0.5+0.5+1+1 = 4.0
        return [(m[0], "8"), ("r", "8"),
                (m[1], "8"), ("r", "8"),
                (m[2], "4"), ("r", "4")]
    if r == "driving":
        # 0.5+0.5+1+0.5+0.5+1 = 4.0
        return [(m[0], "8"), (m[0], "8"),
                (m[1], "4"),
                (m[2], "8"), (m[1], "8"),
                (m[0], "4")]
    if r == "swing":
        # 1.5+0.5+1+1 = 4.0
        return [(m[0], "4."), (m[1], "8"),
                (m[2], "4"), (m[3], "4")]
    if r == "flowing":
        if bpm < 70:
            # 2+2 = 4.0
            return [(m[0], "2"), (m[2], "2")]
        # 2+1+1 = 4.0
        return [(m[0], "2"), (m[1], "4"), (m[2], "4")]
    # straight: 1+1+1+1 = 4.0
    return [(m[0], "4"), (m[1], "4"), (m[2], "4"), (m[1], "4")]


# ─────────────────────────────────────────────────────────────────────────────
#  Melody / lyrics / chord helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pattern_beats(pattern: list[tuple[str, str]]) -> float:
    total = 0.0
    for _, dur in pattern:
        d = dur.rstrip("~")
        total += _BEAT.get(d, 1.0)
    return total


def _melody_for_section(
    section: LyricsSection,
    profile: _MusicProfile,
) -> tuple[str, int, int]:
    """
    Build a melody stub with enough bars to cover all section syllables
    Returns (lilypond_note_string, note_count, bars_used).
    """
    pattern = _build_bar_pattern(profile, section.name)
    pb = _pattern_beats(pattern)

    # Pitch notes (non-rest) per bar — used to estimate needed bar count
    notes_per_bar = max(sum(1 for pitch, _ in pattern if pitch != "r"), 1)
    total_sylls = len(section.syllables)

    if total_sylls > _MAX_BARS * notes_per_bar:
        max_bars = (total_sylls + notes_per_bar - 1) // notes_per_bar
    else:
        max_bars = _MAX_BARS

    beats_needed = max_bars * profile.beats_per_bar
    reps = max(1, int(beats_needed / max(pb, 0.01)) + 1)

    note_stream = [f"{pitch}{dur}" for pitch, dur in pattern * reps]

    bar_lines: list[str] = []
    current: list[str] = []
    accum = 0.0
    note_count = 0

    for note in note_stream:
        if len(bar_lines) >= max_bars:
            break
        m = _re.search(r"(\d+\.?)", note)
        d = m.group(1) if m else "4"
        beats = _BEAT.get(d, 1.0)
        current.append(note)
        if note[0] != "r":
            note_count += 1
        accum += beats
        if accum >= profile.beats_per_bar - 0.01:
            bar_lines.append(" ".join(current))
            current = []
            accum = 0.0

    # Close partial bar with a rest if needed
    if current and len(bar_lines) < max_bars:
        rest_beats = profile.beats_per_bar - accum
        if rest_beats > 0.1:
            rd = {4.0: "1", 3.0: "2.", 2.0: "2", 1.5: "4.", 1.0: "4", 0.5: "8"}.get(rest_beats, "4")
            current.append(f"r{rd}")
        bar_lines.append(" ".join(current))

    # 16-space indent aligns with _section_block template for textwrap.dedent
    ly = " |\n                ".join(bar_lines) + " |"

    return ly, note_count, len(bar_lines)


def _lyrics_block(section: LyricsSection, max_notes: int) -> str:
    sylls = section.syllables[:max_notes]
    if not sylls:
        return "\\skip 1"
    return " ".join(_lily_lyric_token(s) for s in sylls)


def _chordnames_block(chords: list[str], bars: int = 4) -> str:
    if not chords:
        return "c1"
    ly_chords = [_chord_to_lily(c) for c in chords]
    result = (ly_chords * ((bars // len(ly_chords)) + 1))[:bars]
    return " | ".join(result) + " |"


# ─────────────────────────────────────────────────────────────────────────────
#  LilyPond file generator
# ─────────────────────────────────────────────────────────────────────────────

class LilyPondGenerator:
    def generate(self, data: SunoPromptData, out_dir: Path = OUTPUT_DIR) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        ly_code = self._build(data)
        out_path = out_dir / f"{self._safe_name(data.title)}.ly"
        out_path.write_text(ly_code, encoding="utf-8")
        return out_path

    def _build(self, data: SunoPromptData) -> str:
        key_root, key_mode = KEY_TO_LILYPOND.get(data.key, ("c", "\\major"))
        bpm = data.bpm
        time_sig, denom, _ = _parse_time_signature(data.time_signature)

        profile = _derive_profile(data)
        section_vars = self._assign_var_names(data)

        section_blocks: list[str] = []
        for s, var in section_vars:
            block, _ = self._section_block(s, data, profile, var)
            section_blocks.append(block)

        if not section_blocks:
            section_blocks = [self._empty_section_block(data, profile)]

        sections_ly = "\n\n".join(section_blocks)

        return "\n".join([
            '\\version "2.24.0"',
            '',
            '\\header {',
            f'  title = "{_lily_string(data.title)}"',
            f'  composer = "{_lily_string(data.artist)}"',
            f'  subtitle = "{_lily_string(", ".join(data.genre))}"',
            '  tagline = "Generated by AI Music Analyzer"',
            '}',
            '',
            '% ── Global settings ──────────────────────────────────────────',
            'globalSettings = {',
            f'  \\key {key_root} {key_mode}',
            f'  \\time {time_sig}',
            f'  \\tempo {denom} = {bpm}',
            '}',
            '',
            '% ══════════════════════════════════════════════════════════════',
            '%  Sections',
            '% ══════════════════════════════════════════════════════════════',
            '',
            sections_ly,
            '',
            self._score_staves(section_vars),
        ])

    @staticmethod
    def _assign_var_names(data: SunoPromptData) -> list[tuple[LyricsSection, str]]:
        sections_with_lyrics = [s for s in data.sections if s.lyrics]

        base_count: dict[str, int] = {}
        for s in sections_with_lyrics:
            b = LilyPondGenerator._safe_var(s.name)
            base_count[b] = base_count.get(b, 0) + 1

        seen: dict[str, int] = {}
        result: list[tuple[LyricsSection, str]] = []
        for s in sections_with_lyrics:
            b = LilyPondGenerator._safe_var(s.name)
            if base_count[b] > 1:
                n = seen.get(b, 0) + 1
                seen[b] = n
                if n == 1:
                    var = b
                elif b[-1].isdigit():
                    var = b + chr(ord('b') + n - 2)
                else:
                    var = f"{b}{n}"
            else:
                var = b
            result.append((s, var))
        return result

    def _section_block(
        self,
        section: LyricsSection,
        data: SunoPromptData,
        profile: _MusicProfile,
        var: str,
    ) -> tuple[str, int]:
        key_root, _ = KEY_TO_LILYPOND.get(data.key, ("c", "\\major"))
        melody, note_count, bars_used = _melody_for_section(section, profile)
        lyrics = _lyrics_block(section, note_count)
        section_chords = section.chords or data.chord_progression
        chords_ly = _chordnames_block(section_chords, bars=bars_used)

        block = dedent(f"""\
            % ── {section.name} ────────────────────────────────────────────
            {var}Melody = {{
              \\globalSettings
              \\transpose c {key_root} \\relative c' {{
                {melody}
              }}
            }}

            {var}Chords = \\chordmode {{
              {chords_ly}
            }}

            {var}Lyrics = \\lyricmode {{
              {lyrics}
            }}
        """)
        return block, bars_used

    def _empty_section_block(self, data: SunoPromptData, profile: _MusicProfile) -> str:
        pattern = _build_bar_pattern(profile, "verse")
        notes = " ".join(f"{p}{d}" for p, d in pattern) + " |"
        key_root, key_mode = KEY_TO_LILYPOND.get(data.key, ("c", "\\major"))
        time_sig, denom, _ = _parse_time_signature(data.time_signature)
        return dedent(f"""\
            % ── Melody stub (no lyrics found) ────────────────────────────
            mainMelody = {{
              \\key {key_root} {key_mode}
              \\time {time_sig}
              \\tempo {denom} = {data.bpm}
              \\transpose c {key_root} \\relative c' {{
                {notes}
              }}
            }}
        """)

    def _score_staves(self, section_vars: list[tuple[LyricsSection, str]]) -> str:
        """Generate one score block per section, each with its own chord names."""
        if not section_vars:
            return dedent("""\
                \\score {
                  \\new Staff { \\mainMelody }
                  \\layout { }
                  \\midi { }
                }""")
        scores = []
        for s, var in section_vars:
            name = _lily_string(s.name)
            scores.append(dedent(f"""\
                % ── Score: {s.name} ─────────────────────────────────────────
                \\score {{
                  <<
                    \\new ChordNames {{ \\{var}Chords }}
                    \\new Staff \\with {{ instrumentName = "{name}" }} {{
                      \\new Voice = "{var}" {{ \\{var}Melody }}
                    }}
                    \\new Lyrics \\lyricsto "{var}" {{
                      \\{var}Lyrics
                    }}
                  >>
                  \\header {{ piece = "{name}" }}
                  \\layout {{ }}
                  \\midi {{ }}
                }}"""))
        return "\n\n".join(scores)

    @staticmethod
    def _safe_name(title: str) -> str:
        ascii_only = _re.sub(r"[^\x00-\x7F]", "", title)
        cleaned = _re.sub(r"[^\w\-]", "_", ascii_only).strip("_")
        return cleaned or "untitled"

    @staticmethod
    def _safe_var(name: str) -> str:
        cleaned = _re.sub(r"[^a-zA-Z0-9]", "", name)
        if not cleaned:
            return "section"
        if cleaned[0].isdigit():
            cleaned = "s" + cleaned
        return cleaned[0].lower() + cleaned[1:]
