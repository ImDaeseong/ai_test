"""ai-webtoon 단위 테스트 — 순수 함수 검증"""
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import main as m


# ── song_slug ────────────────────────────────────────────────────────────────

def test_song_slug_basic():
    assert m.song_slug("Hello World") == "Hello World"

def test_song_slug_strips_forbidden_chars():
    result = m.song_slug('A/B:C"D')
    assert "/" not in result
    assert ":" not in result
    assert '"' not in result

def test_song_slug_korean():
    assert m.song_slug("안녕하세요") == "안녕하세요"

def test_song_slug_empty_raises():
    # 점(.)만 있으면 strip(".") 후 빈 문자열 → ValueError
    with pytest.raises(ValueError):
        m.song_slug("...")


# ── _normalize_field_key ─────────────────────────────────────────────────────

def test_normalize_field_key_title():
    assert m._normalize_field_key("Title") == "title"
    assert m._normalize_field_key("제목") == "title"
    assert m._normalize_field_key("song title") == "title"

def test_normalize_field_key_genre():
    assert m._normalize_field_key("Genre") == "genre"
    assert m._normalize_field_key("장르") == "genre"
    assert m._normalize_field_key("Style") == "genre"

def test_normalize_field_key_bpm():
    assert m._normalize_field_key("bpm") == "bpm"
    assert m._normalize_field_key("BPM") == "bpm"

def test_normalize_field_key_unknown():
    assert m._normalize_field_key("unknown_key") is None

def test_normalize_field_key_extra_spaces():
    assert m._normalize_field_key("  title  ") == "title"


# ── _is_negative_tag ─────────────────────────────────────────────────────────

def test_is_negative_tag_dash():
    assert m._is_negative_tag("-electric")
    assert m._is_negative_tag("- electric")

def test_is_negative_tag_no_prefix():
    assert m._is_negative_tag("no drums")
    assert m._is_negative_tag("not loud")

def test_is_negative_tag_normal():
    assert not m._is_negative_tag("acoustic")
    assert not m._is_negative_tag("pop ballad")


# ── _clean_genre ─────────────────────────────────────────────────────────────

def test_clean_genre_removes_negative():
    result = m._clean_genre("pop, -metal, ballad")
    assert "metal" not in result
    assert "pop" in result
    assert "ballad" in result

def test_clean_genre_strips_whitespace():
    result = m._clean_genre("  acoustic ,  folk  ")
    parts = [p.strip() for p in result.split(",")]
    assert "acoustic" in parts
    assert "folk" in parts

def test_clean_genre_empty():
    assert m._clean_genre("") == ""


# ── _normalize_section_label ─────────────────────────────────────────────────

def test_normalize_section_label_pre():
    assert m._normalize_section_label("pre chorus") == "Pre-Chorus"
    assert m._normalize_section_label("pre-chorus") == "Pre-Chorus"

def test_normalize_section_label_post():
    assert m._normalize_section_label("post chorus") == "Post-Chorus"

def test_normalize_section_label_final():
    assert m._normalize_section_label("final chorus") == "Final Chorus"

def test_normalize_section_label_basic():
    assert m._normalize_section_label("verse") == "Verse"
    assert m._normalize_section_label("intro") == "Intro"
    assert m._normalize_section_label("outro") == "Outro"


# ── _normalize_section_key ───────────────────────────────────────────────────

def test_normalize_section_key_basic():
    assert m._normalize_section_key("Verse") == "verse"
    assert m._normalize_section_key("Chorus") == "chorus"
    assert m._normalize_section_key("Intro") == "intro"
    assert m._normalize_section_key("Outro") == "outro"

def test_normalize_section_key_numbered():
    assert m._normalize_section_key("Verse 2") == "verse"
    assert m._normalize_section_key("Chorus 3") == "chorus"

def test_normalize_section_key_final_chorus():
    assert m._normalize_section_key("Final Chorus") == "chorus"

def test_normalize_section_key_aliases():
    assert m._normalize_section_key("Drop") == "chorus"
    assert m._normalize_section_key("Hook") == "chorus"
    assert m._normalize_section_key("Build") == "pre_chorus"
    assert m._normalize_section_key("Solo") == "instrumental"
    assert m._normalize_section_key("Interlude") == "instrumental"


# ── _parse_key_value ─────────────────────────────────────────────────────────

def test_parse_key_value_title():
    result = m._parse_key_value("Title: 나의 노래")
    assert result == ("title", "나의 노래")

def test_parse_key_value_bpm():
    result = m._parse_key_value("BPM: 120")
    assert result == ("bpm", "120")

def test_parse_key_value_no_colon():
    assert m._parse_key_value("no colon here") is None

def test_parse_key_value_unknown_key():
    assert m._parse_key_value("Unknown: value") is None


# ── _strip_noise_lines ───────────────────────────────────────────────────────

def test_strip_noise_lines_removes_timestamps():
    lines = m._strip_noise_lines("3:45\nhello\n2:30:10")
    assert "3:45" not in lines
    assert "hello" in lines

def test_strip_noise_lines_removes_ago():
    lines = m._strip_noise_lines("3d ago\nhello")
    assert "3d ago" not in " ".join(lines)

def test_strip_noise_lines_keeps_normal():
    result = m._strip_noise_lines("[Chorus]\n사랑해\n")
    assert any("[Chorus]" in ln for ln in result)
    assert any("사랑해" in ln for ln in result)


# ── has_identity_lock ────────────────────────────────────────────────────────

def test_has_identity_lock_true():
    text = "original fantasy skeleton music band performing on stage"
    assert m.has_identity_lock(text)

def test_has_identity_lock_false():
    assert not m.has_identity_lock("A generic pop band")

def test_has_identity_lock_do_not_redesign():
    assert m.has_identity_lock("Do not redesign the characters")


# ── detect_bpm_range ─────────────────────────────────────────────────────────

def test_detect_bpm_range_no_number():
    result = m.detect_bpm_range("")
    assert result == "medium"

def test_detect_bpm_range_fast():
    result = m.detect_bpm_range("140 BPM")
    assert result in ("fast", "very_fast")

def test_detect_bpm_range_slow():
    result = m.detect_bpm_range("70 BPM")
    assert result == "slow"

def test_detect_bpm_range_string_prefix():
    result = m.detect_bpm_range("Tempo: 120 bpm")
    assert isinstance(result, str)


# ── _infer_title ─────────────────────────────────────────────────────────────

def test_infer_title_from_fields():
    assert m._infer_title([], {"title": "테스트 곡"}) == "테스트 곡"

def test_infer_title_override():
    result = m._infer_title([], {"title": "무시"}, title_override="덮어쓰기 제목")
    assert result == "덮어쓰기 제목"

def test_infer_title_fallback():
    result = m._infer_title([], {}, title_fallback="파일명 제목")
    assert result == "파일명 제목"

def test_infer_title_no_title_raises():
    with pytest.raises(ValueError):
        m._infer_title([], {})


# ── parse_song / select_style regression ────────────────────────────────────

def _parse_text(text: str) -> m.Song:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "song.txt"
        path.write_text(text, encoding="utf-8")
        return m.parse_song(path, title_fallback="song")


def test_parse_song_missing_mood_and_emotion_remain_empty():
    song = _parse_text("Title: Fast\nGenre: Hardcore Punk, 175 BPM\n[Intro]\n")
    assert song.mood == ""
    assert song.emotion == ""


def test_parse_song_preserves_explicit_mood_and_emotion():
    song = _parse_text(
        "Title: Slow\nGenre: Pop, 80 BPM\nMood: Nostalgic\n"
        "Emotion: Heartfelt\n[Verse]\n"
    )
    assert song.mood == "Nostalgic"
    assert song.emotion == "Heartfelt"


def test_fast_hardcore_without_emotion_selects_action_style():
    song = _parse_text(
        "Title: Fast\nGenre: Hardcore Punk, Garage Rock, 175 BPM\n[Intro]\n"
    )
    assert m.select_style(song)[0] == "cute_action"


def test_fast_hardcore_lofi_production_selects_action_style():
    song = _parse_text(
        "Title: Fast\n"
        "Genre: Hardcore Punk, Garage Rock, 175 BPM, aggressive shouting, "
        "fast driving drums, Lo-fi analog distortion\n[Intro]\n"
    )
    assert m.select_style(song)[0] == "cute_action"


def test_explicit_fast_bittersweet_still_selects_emotional_style():
    song = _parse_text(
        "Title: Memory\nGenre: 80s Indie Pop, 174 BPM, Bittersweet\n[Intro]\n"
    )
    assert m.select_style(song)[0] == "cute_manhwa"


def test_display_metadata_falls_back_only_for_output():
    assert m.display_metadata("") == "미지정"
    assert m.display_metadata("  nostalgic  ") == "nostalgic"


def test_hardcore_selects_raw_or_heavy_performance_profile():
    song = _parse_text(
        "Title: Fast\nGenre: Hardcore Punk, Garage Rock, 175 BPM\n[Intro]\n"
    )
    profile_key, _ = m.select_performance_profile(song)
    assert profile_key in {"raw_power_stage", "in_the_round_heavy"}


def test_electronic_selects_geometric_profile():
    song = _parse_text(
        "Title: Signal\nGenre: Electronic, Synthwave, 128 BPM, pulse\n[Intro]\n"
    )
    assert m.select_performance_profile(song)[0] == "geometric_electronic"


def test_profile_variant_is_deterministic_and_changes_by_panel():
    song = _parse_text("Title: Variant\nGenre: Pop Rock, 128 BPM\n[Intro]\n")
    profile_key, profile = m.select_performance_profile(song)
    first = m.select_profile_variant(song, profile_key, profile, "camera_variants", 1)
    repeat = m.select_profile_variant(song, profile_key, profile, "camera_variants", 1)
    variants = {
        m.select_profile_variant(song, profile_key, profile, "camera_variants", panel)
        for panel in range(1, 12)
    }
    assert first == repeat
    assert len(variants) > 1


def test_profile_dataset_references_existing_sources():
    sources = m._BAND_PROFILES["sources"]
    for profile in m._BAND_PROFILES["profiles"].values():
        assert profile["source_refs"]
        assert all(source_key in sources for source_key in profile["source_refs"])


def test_profile_archetypes_cover_distinct_genres():
    songs = [
        _parse_text("Title: A\nGenre: Hardcore Punk, 175 BPM\n[Intro]\n"),
        _parse_text("Title: B\nGenre: Synthwave, Electronic, 128 BPM\n[Intro]\n"),
        _parse_text("Title: C\nGenre: Shoegaze, Post-Punk, 100 BPM\n[Intro]\n"),
        _parse_text("Title: D\nGenre: Funk, New Wave, 120 BPM\n[Intro]\n"),
        _parse_text("Title: E\nGenre: Acoustic Folk, 75 BPM\n[Intro]\n"),
    ]
    profiles = {m.select_performance_profile(song)[0] for song in songs}
    assert len(profiles) >= 5
