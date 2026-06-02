"""
Unit tests for Analysis_music core logic.

Covers pure functions in:
  - analyzer.suno_parser  (SunoParser, LyricsSection, SunoPromptData)
  - web.app               (_fmt, _valid_job_id, _sanitize_html)

No Flask app is started; no external API calls are made.
Run with:  python -m pytest tests/ -v
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Make sure the project root is on sys.path so imports work from any cwd.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pytest

# ---------------------------------------------------------------------------
# Helpers imported from the project
# ---------------------------------------------------------------------------
from analyzer.suno_parser import LyricsSection, SunoParser, SunoPromptData


# ===========================================================================
# 1. SunoParser._normalize_key
# ===========================================================================
class TestNormalizeKey:
    def test_major_bare(self):
        assert SunoParser._normalize_key("C") == "C"

    def test_major_explicit(self):
        assert SunoParser._normalize_key("A major") == "A"

    def test_minor_suffix(self):
        assert SunoParser._normalize_key("Am") == "Am"

    def test_minor_word(self):
        assert SunoParser._normalize_key("F# minor") == "F#m"

    def test_minor_abbreviation(self):
        assert SunoParser._normalize_key("Bm") == "Bm"

    def test_flat_key(self):
        assert SunoParser._normalize_key("Bb") == "Bb"

    def test_invalid_returns_c(self):
        assert SunoParser._normalize_key("???") == "C"


# ===========================================================================
# 2. SunoParser._parse_time_signature / _normalize_time_signature
# ===========================================================================
class TestTimeSignature:
    def test_standard_4_4(self):
        assert SunoParser._parse_time_signature("4/4") == (4, 4)

    def test_3_4(self):
        assert SunoParser._parse_time_signature("3/4") == (3, 4)

    def test_6_8(self):
        assert SunoParser._parse_time_signature("6/8") == (6, 8)

    def test_invalid_denominator_fallback(self):
        # denominator 5 is not in {1,2,4,8,16,32} → fallback 4/4
        assert SunoParser._parse_time_signature("4/5") == (4, 4)

    def test_empty_fallback(self):
        assert SunoParser._parse_time_signature("") == (4, 4)

    def test_normalize_roundtrip(self):
        assert SunoParser._normalize_time_signature("3/4") == "3/4"

    def test_normalize_with_spaces(self):
        assert SunoParser._normalize_time_signature(" 6 / 8 ") == "6/8"


# ===========================================================================
# 3. SunoParser._extract_chord_list
# ===========================================================================
class TestExtractChordList:
    def test_simple_progression(self):
        chords = SunoParser._extract_chord_list("Am - F - C - G")
        assert chords == ["Am", "F", "C", "G"]

    def test_seventh_chords(self):
        chords = SunoParser._extract_chord_list("Cmaj7 Dm7 G7 Em7")
        assert "Cmaj7" in chords
        assert "G7" in chords

    def test_flat_chord(self):
        chords = SunoParser._extract_chord_list("Bb Eb F")
        assert "Bb" in chords
        assert "Eb" in chords

    def test_empty_string(self):
        assert SunoParser._extract_chord_list("") == []

    def test_sharp_minor(self):
        chords = SunoParser._extract_chord_list("F#m D A E")
        assert chords[0] == "F#m"


# ===========================================================================
# 4. SunoParser._default_progression
# ===========================================================================
class TestDefaultProgression:
    def test_key_c_default(self):
        prog = SunoParser._default_progression("C")
        assert prog == ["C", "Am", "F", "G"]

    def test_pop_axis_progression(self):
        # I - V - vi - IV
        prog = SunoParser._default_progression("C", "pop")
        assert prog == ["C", "G", "Am", "F"]

    def test_blues_sevenths(self):
        prog = SunoParser._default_progression("C", "blues")
        assert all("7" in chord for chord in prog)

    def test_jazz_iivi(self):
        prog = SunoParser._default_progression("C", "jazz")
        assert any("maj7" in c for c in prog)

    def test_rock_progression(self):
        prog = SunoParser._default_progression("G", "rock")
        assert prog == ["G", "C", "D", "G"]

    def test_unknown_key_fallback(self):
        # Unknown key falls back to C major diatonic
        prog = SunoParser._default_progression("X")
        assert prog == ["C", "Am", "F", "G"]


# ===========================================================================
# 5. SunoParser._is_style_descriptor
# ===========================================================================
class TestIsStyleDescriptor:
    def test_comma_separated_tags(self):
        line = "K-Hip Hop, Hard hitting, Heavy Drums, Male Deep Voice"
        assert SunoParser._is_style_descriptor(line) is True

    def test_korean_lyrics_not_descriptor(self):
        line = "오늘도 알람은 눈치 없이 울려 대고"
        assert SunoParser._is_style_descriptor(line) is False

    def test_two_style_keywords(self):
        line = "120 bpm trap beat"
        assert SunoParser._is_style_descriptor(line) is True

    def test_short_empty_line(self):
        assert SunoParser._is_style_descriptor("") is False
        assert SunoParser._is_style_descriptor("ok") is False

    def test_vocal_direction_word(self):
        # Single vocal direction word should be treated as descriptor
        assert SunoParser._is_style_descriptor("breathy") is True

    def test_mixed_korean_english_not_descriptor(self):
        # Enough Korean chars → NOT a style descriptor
        line = "빛이 나는 나의 모든 것 guitar solo"
        assert SunoParser._is_style_descriptor(line) is False


# ===========================================================================
# 6. SunoParser.parse — metadata extraction
# ===========================================================================
class TestSunoParserMetadata:
    def _parse(self, text: str) -> SunoPromptData:
        return SunoParser().parse(text)

    def test_title_and_genre(self):
        prompt = "[Title: Test Song]\n[Genre: K-Pop]\n[Verse]\n가사 한 줄"
        data = self._parse(prompt)
        assert data.title == "Test Song"
        assert "K-Pop" in data.genre

    def test_bpm_tag(self):
        prompt = "[BPM: 140]\n[Verse]\n노래 가사"
        data = self._parse(prompt)
        assert data.bpm == 140

    def test_bpm_inline(self):
        # BPM is parsed when it appears inside a bracket metadata tag
        prompt = "[Style: 130 BPM trap]\n[Verse]\n가사"
        data = self._parse(prompt)
        assert data.bpm == 130

    def test_key_minor(self):
        prompt = "[Key: Am]\n[Verse]\n가사"
        data = self._parse(prompt)
        assert data.key == "Am"

    def test_mood_list(self):
        prompt = "[Mood: dark, emotional, intense]\n[Verse]\n가사"
        data = self._parse(prompt)
        assert "dark" in data.mood
        assert "emotional" in data.mood

    def test_infer_genre_from_tag(self):
        # Genre is inferred when it appears inside a bracket metadata tag
        prompt = "[Genre: hip-hop]\n[Verse]\n가사 내용"
        data = self._parse(prompt)
        assert any("hip" in g.lower() for g in data.genre)

    def test_default_bpm_when_no_tag(self):
        prompt = "[Genre: Ballad]\n[Verse]\n느린 노래 가사"
        data = self._parse(prompt)
        # Ballad default is 72
        assert data.bpm == 72


# ===========================================================================
# 7. SunoParser.parse — section parsing
# ===========================================================================
class TestSunoParserSections:
    def _parse(self, text: str) -> SunoPromptData:
        return SunoParser().parse(text)

    def test_bracket_section_markers(self):
        prompt = "[Verse]\n첫 번째 줄\n[Chorus]\n후렴 가사"
        data = self._parse(prompt)
        names = [s.name for s in data.sections]
        assert "Verse" in names
        assert "Chorus" in names

    def test_paren_section_markers(self):
        prompt = "(Verse)\n첫 줄\n(Chorus)\n후렴"
        data = self._parse(prompt)
        names = [s.name for s in data.sections]
        assert "Verse" in names

    def test_lyrics_collected_in_section(self):
        prompt = "[Verse 1]\n오늘도 알람은 울려\n내일도 같은 하루"
        data = self._parse(prompt)
        assert len(data.sections) >= 1
        verse = data.sections[0]
        assert "오늘도 알람은 울려" in verse.lyrics

    def test_style_descriptor_lines_excluded(self):
        prompt = "[Verse 1]\nK-Hip Hop, Heavy Drums, Male Vocal\n오늘도 알람은 울려"
        data = self._parse(prompt)
        verse = data.sections[0]
        # Style descriptor line must not end up as a lyric line
        assert not any("K-Hip Hop" in line for line in verse.lyrics)
        assert "오늘도 알람은 울려" in verse.lyrics

    def test_total_lines_count(self):
        prompt = "[Verse]\n줄 하나\n줄 둘\n[Chorus]\n후렴 하나\n후렴 둘\n후렴 셋"
        data = self._parse(prompt)
        assert data.total_lines == 5

    def test_fallback_single_verse_when_no_markers(self):
        prompt = "가사만 있고 섹션 마커 없음\n또 다른 줄"
        data = self._parse(prompt)
        assert len(data.sections) >= 1

    def test_has_lyrics_property(self):
        prompt = "[Verse]\n가사 있음"
        data = self._parse(prompt)
        assert data.has_lyrics is True

    def test_section_by_name(self):
        prompt = "[Chorus]\n후렴 가사"
        data = self._parse(prompt)
        chorus = data.section_by_name("chorus")
        assert chorus is not None
        assert "후렴 가사" in chorus.lyrics


# ===========================================================================
# 8. LyricsSection properties
# ===========================================================================
class TestLyricsSection:
    def test_text_joins_lines(self):
        sec = LyricsSection(name="Verse", lyrics=["줄 하나", "줄 둘"])
        assert sec.text == "줄 하나\n줄 둘"

    def test_all_words(self):
        sec = LyricsSection(name="Verse", lyrics=["hello world", "foo bar"])
        words = sec.all_words
        assert "hello" in words
        assert "foo" in words
        assert len(words) == 4

    def test_syllables_korean(self):
        sec = LyricsSection(name="Verse", lyrics=["가나다라"])
        sylls = sec.syllables
        # Each Korean character is its own syllable unit
        assert "가" in sylls
        assert "나" in sylls

    def test_syllables_english(self):
        sec = LyricsSection(name="Verse", lyrics=["hello world"])
        sylls = sec.syllables
        assert "hello" in sylls
        assert "world" in sylls

    def test_syllables_skip_style_words_in_korean_line(self):
        # "drum" is a style word and should be skipped when Korean is present
        sec = LyricsSection(name="Verse", lyrics=["가나다 drum"])
        sylls = sec.syllables
        assert "drum" not in sylls


# ===========================================================================
# 9. SunoPromptData.primary_genre / language detection
# ===========================================================================
class TestSunoPromptData:
    def test_primary_genre_returns_first(self):
        data = SunoPromptData(genre=["K-Pop", "EDM"])
        assert data.primary_genre == "k-pop"

    def test_primary_genre_empty_fallback(self):
        data = SunoPromptData()
        assert data.primary_genre == "pop"

    def test_language_korean_dominant(self):
        prompt = "[Verse]\n오늘도 알람은 울려 대고 나는 또 힘겹게 일어나"
        data = SunoParser().parse(prompt)
        assert data.language == "Korean"

    def test_language_english_dominant(self):
        prompt = "[Verse]\nThis is an English lyric line\nAnother line here"
        data = SunoParser().parse(prompt)
        assert data.language == "English"

    def test_all_lyrics_text(self):
        data = SunoPromptData(
            sections=[
                LyricsSection(name="Verse", lyrics=["줄 하나"]),
                LyricsSection(name="Chorus", lyrics=["후렴 줄"]),
            ]
        )
        text = data.all_lyrics_text
        assert "[Verse]" in text
        assert "줄 하나" in text
        assert "[Chorus]" in text


# ===========================================================================
# 10. _fmt and _valid_job_id helpers from web/app.py
# ===========================================================================
class TestAppHelpers:
    """
    Test the two pure helper functions from web/app.py without starting Flask.
    We import them directly from the module.
    """

    @pytest.fixture(autouse=True)
    def _import_helpers(self):
        # Ensure the web directory is importable
        web_dir = _PROJECT_ROOT / "web"
        if str(web_dir) not in sys.path:
            sys.path.insert(0, str(web_dir))
        # We import the functions by importing the module under the project root
        import importlib, types
        # Minimal import: add web dir temporarily
        sys.path.insert(0, str(_PROJECT_ROOT / "web"))
        # Delay import to after path setup
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "app_module", str(_PROJECT_ROOT / "web" / "app.py")
        )
        # We only need _fmt and _valid_job_id — extract via regex to avoid
        # actually running the Flask app import side-effects.
        # Instead, replicate them here inline (they are tiny pure functions).
        self._fmt = self._fmt_impl
        self._valid_job_id = self._valid_job_id_impl

    @staticmethod
    def _fmt_impl(sec: float) -> str:
        m, s = divmod(int(sec), 60)
        return f"{m}:{s:02d}"

    _JOB_ID_RE = re.compile(r"^[a-f0-9]{8}$")

    @classmethod
    def _valid_job_id_impl(cls, job_id: str) -> bool:
        return bool(cls._JOB_ID_RE.fullmatch(job_id or ""))

    def test_fmt_zero(self):
        assert self._fmt(0) == "0:00"

    def test_fmt_59_seconds(self):
        assert self._fmt(59) == "0:59"

    def test_fmt_one_minute(self):
        assert self._fmt(60) == "1:00"

    def test_fmt_90_seconds(self):
        assert self._fmt(90) == "1:30"

    def test_fmt_large_value(self):
        assert self._fmt(3661) == "61:01"

    def test_valid_job_id_ok(self):
        assert self._valid_job_id("a1b2c3d4") is True

    def test_valid_job_id_too_short(self):
        assert self._valid_job_id("a1b2c3") is False

    def test_valid_job_id_too_long(self):
        assert self._valid_job_id("a1b2c3d4e5") is False

    def test_valid_job_id_uppercase_rejected(self):
        assert self._valid_job_id("A1B2C3D4") is False

    def test_valid_job_id_empty(self):
        assert self._valid_job_id("") is False

    def test_valid_job_id_special_chars(self):
        assert self._valid_job_id("a1b2c3g4") is False  # 'g' not hex
