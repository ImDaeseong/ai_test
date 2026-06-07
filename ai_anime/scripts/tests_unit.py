"""단위 테스트 — 순수 함수 대상 (외부 의존·파일 I/O 없음)

실행:  python scripts/tests_unit.py
또는:  python -m pytest scripts/tests_unit.py -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


# ──────────────────────────────────────────────────────────────────────────────
# scene_composer 순수 함수
# ──────────────────────────────────────────────────────────────────────────────

class TestHasBrokenText(unittest.TestCase):
    def _run(self, text: str) -> bool:
        from scene_composer import has_broken_text
        return has_broken_text(text)

    def test_empty(self):
        self.assertFalse(self._run(""))

    def test_normal_english(self):
        self.assertFalse(self._run("clear night sky with distant lights"))

    def test_normal_korean(self):
        self.assertFalse(self._run("비 내리는 밤거리"))

    def test_mojibake_markers(self):
        # 3개 이상의 mojibake 마커 → True
        self.assertTrue(self._run("諛섑빆 蹂닿쾶 醫뚯떆 怨좎슂"))

    def test_question_mark_spam(self):
        # 3개 이상의 고립 ? → True
        self.assertTrue(self._run("? ? ? broken text here"))

    def test_two_markers_not_enough(self):
        self.assertFalse(self._run("諛 one marker 蹂"))


class TestCleanExcerpt(unittest.TestCase):
    def setUp(self):
        from scene_composer import clean_excerpt
        self.fn = clean_excerpt

    def test_normal_text_truncated(self):
        result = self.fn("hello world", limit=5)
        self.assertEqual(result, "hello")

    def test_whitespace_normalized(self):
        result = self.fn("  lots   of   spaces  ")
        self.assertEqual(result, "lots of spaces")

    def test_damaged_text_replaced(self):
        damaged = "諛섑빆 蹂닿쾶 醫뚯떆 怨좎슂 broken"
        result = self.fn(damaged)
        self.assertIn("encoding-damaged", result)

    def test_empty(self):
        self.assertEqual(self.fn(""), "")

    def test_none_like_empty(self):
        self.assertEqual(self.fn(None), "")  # type: ignore[arg-type]


class TestGenreReferenceProfiles(unittest.TestCase):
    def test_six_family_mappings(self):
        from genre_reference import select_genre_reference

        cases = {
            "high-contrast rock anime noir": "rock",
            "intimate acoustic anime noir": "acoustic_ballad",
            "rhythmic trap-pop anime noir": "hip_hop_trap",
            "dreamy synth anime noir": "electronic_synth",
            "vivid idol anime pop": "idol_pop",
            "late-night jazz anime noir": "jazz_soul",
        }
        for profile_name, expected in cases.items():
            with self.subTest(profile_name=profile_name):
                self.assertEqual(select_genre_reference({"name": profile_name})["id"], expected)

    def test_unsupported_profile_is_empty(self):
        from genre_reference import select_genre_reference

        self.assertEqual(select_genre_reference({"name": "unknown future genre"}), {})

    def test_every_configured_genre_profile_has_reference_family(self):
        from common import load_config
        from genre_reference import select_genre_reference

        missing = [
            profile["name"]
            for profile in load_config("genres")
            if not select_genre_reference(profile)
        ]
        self.assertEqual(missing, [])

    def test_reference_choice_is_deterministic(self):
        from genre_reference import reference_variant, select_genre_reference

        reference = select_genre_reference({"name": "high-contrast rock anime noir"})
        first = reference_variant(reference, "camera_language", "same-song", "camera")
        second = reference_variant(reference, "camera_language", "same-song", "camera")
        self.assertEqual(first, second)
        self.assertTrue(first)

    def test_provenance_names_are_not_generation_values(self):
        from common import load_config
        from genre_reference import source_output_terms

        data = load_config("genre_reference_profiles")
        generation_text = " ".join(
            str(value)
            for family in data["families"].values()
            for key, value in family.items()
            if key not in {"source_ids", "profile_names"}
        ).lower()
        for term in source_output_terms():
            self.assertNotIn(term.lower(), generation_text)

    def test_visual_world_uses_reference_without_source_metadata(self):
        import palette_engine
        from world_builder import create_visual_world

        palette_engine.select_theme("rock_edge")
        song = {
            "title": "Reference Test",
            "genre": "rock",
            "bpm": 150,
            "energy": "high",
            "mood": ["defiant"],
            "instruments": ["electric guitar", "drums"],
            "style_tags": ["rock"],
            "atmosphere": "live performance",
            "sections": [{"name": "Intro", "lyrics": "", "description": "guitar opening"}],
            "visual_cues": [],
            "negative_tags": [],
        }
        emotion = {"visual_symbolism": [], "urban_rural_mood": "performance space"}
        world = create_visual_world(song, emotion)

        self.assertEqual(world["genre_reference"]["id"], "rock")
        self.assertTrue(world["genre_reference"]["camera_language"])
        self.assertTrue(world["genre_reference"]["motion_language"])
        self.assertNotIn("source_ids", world["genre_reference"])
        self.assertNotEqual(world["core_locations"][0], "abandoned live house exterior")

    def test_reference_camera_avoids_duplicate_final_direction(self):
        from scene_composer import apply_reference_camera

        reference = {
            "id": "rock",
            "camera_language": ["camera grammar A", "camera grammar B"],
        }
        section = {"name": "Verse", "lyrics": "same", "description": ""}
        used = ["base shot; genre framing: camera grammar A"]
        result = apply_reference_camera("base shot", reference, section, 2, used)
        self.assertEqual(result, "base shot; genre framing: camera grammar B")


class TestStoryStage(unittest.TestCase):
    def setUp(self):
        from scene_composer import story_stage
        self.fn = story_stage

    def test_first_scene_is_opening(self):
        self.assertEqual(self.fn(1, 8, "Intro"), "opening")

    def test_last_scene_is_resolution(self):
        self.assertEqual(self.fn(8, 8, "Outro"), "resolution")

    def test_bridge_is_climax(self):
        self.assertEqual(self.fn(5, 8, "Bridge"), "climax")

    def test_chorus_late_is_climax(self):
        # scene 6/8 = 75% >= 60% ratio → climax
        self.assertEqual(self.fn(6, 8, "Chorus"), "climax")

    def test_chorus_early_is_development(self):
        # scene 2/8 = 25% < 60% ratio → not climax
        result = self.fn(2, 8, "Verse")
        self.assertIn(result, ("development", "opening"))


class TestStoryBeat(unittest.TestCase):
    def test_opening_ko(self):
        from scene_composer import story_beat_ko
        scene = {"music_section": "Intro", "scene_action": "walks", "symbolic_focus": "umbrella"}
        result = story_beat_ko(scene, "opening")
        self.assertIn("Intro", result)
        self.assertIn("umbrella", result)

    def test_climax_en(self):
        from scene_composer import story_beat_en
        scene = {"music_section": "Chorus", "scene_action": "runs", "symbolic_focus": "lamp"}
        result = story_beat_en(scene, "climax")
        self.assertIn("Chorus", result)
        self.assertIn("runs", result)


class TestPickKeyLyricPhrase(unittest.TestCase):
    def setUp(self):
        from scene_composer import _pick_key_lyric_phrase
        self.fn = _pick_key_lyric_phrase

    def test_empty(self):
        self.assertEqual(self.fn(""), "")

    def test_returns_string(self):
        result = self.fn("I walk along the empty street tonight")
        self.assertIsInstance(result, str)

    def test_max_length(self):
        long_line = "a" * 200
        result = self.fn(long_line)
        self.assertLessEqual(len(result), 100)

    def test_bracket_only_excluded(self):
        result = self.fn("[Production note only]")
        self.assertEqual(result, "")

    def test_leading_bracket_stripped(self):
        result = self.fn("[Intro] I see the light")
        self.assertNotIn("[Intro]", result)
        self.assertIn("I see the light", result)


class TestVideoRhythm(unittest.TestCase):
    def setUp(self):
        from scene_composer import video_rhythm
        self.fn = video_rhythm

    def test_with_bpm(self):
        song = {"bpm": 120}
        section = {"intensity": "high"}
        result = self.fn(song, section)
        self.assertIn("120 BPM", result)
        self.assertIn("high", result)

    def test_without_bpm(self):
        song = {}
        section = {"intensity": "medium"}
        result = self.fn(song, section)
        self.assertIn("medium", result)
        self.assertNotIn("None", result)

    def test_with_timing(self):
        song = {"bpm": 90}
        section = {"intensity": "low", "start_time": 30.0, "end_time": 60.0}
        result = self.fn(song, section)
        self.assertIn("30.00s", result)
        self.assertIn("60.00s", result)


# ──────────────────────────────────────────────────────────────────────────────
# video_prompt_generator 순수 함수
# ──────────────────────────────────────────────────────────────────────────────

class TestSlugSection(unittest.TestCase):
    def setUp(self):
        from video_prompt_generator import _slug_section
        self.fn = _slug_section

    def test_lowercase(self):
        self.assertEqual(self.fn("Chorus"), "chorus")

    def test_spaces_to_underscore(self):
        self.assertEqual(self.fn("Pre-Chorus"), "pre_chorus")

    def test_empty_fallback(self):
        self.assertEqual(self.fn(""), "scene")

    def test_numbers_preserved(self):
        self.assertIn("2", self.fn("Verse 2"))


class TestSceneDuration(unittest.TestCase):
    def setUp(self):
        from video_prompt_generator import _scene_duration
        self.fn = _scene_duration

    def test_valid(self):
        self.assertAlmostEqual(self.fn({"start_time": 0.0, "end_time": 30.0}), 30.0)

    def test_missing_start(self):
        self.assertIsNone(self.fn({"end_time": 30.0}))

    def test_missing_end(self):
        self.assertIsNone(self.fn({"start_time": 0.0}))

    def test_negative_duration(self):
        # end < start → None (invalid)
        self.assertIsNone(self.fn({"start_time": 10.0, "end_time": 5.0}))

    def test_zero_duration(self):
        self.assertIsNone(self.fn({"start_time": 5.0, "end_time": 5.0}))


class TestClipCount(unittest.TestCase):
    def setUp(self):
        from video_prompt_generator import _clip_count
        self.fn = _clip_count

    def test_no_timing_returns_4(self):
        self.assertEqual(self.fn({}), 4)

    def test_short_scene_1_clip(self):
        # 6s max per clip → 5s scene = 1 clip
        self.assertEqual(self.fn({"start_time": 0.0, "end_time": 5.0}), 1)

    def test_long_scene_multiple_clips(self):
        # 30s / 8s max = 4 clips (ceil)
        self.assertEqual(self.fn({"start_time": 0.0, "end_time": 30.0}), 4)


class TestClipTimeRange(unittest.TestCase):
    def setUp(self):
        from video_prompt_generator import _clip_time_range
        self.fn = _clip_time_range

    def test_no_timing(self):
        s, e = self.fn({}, 1, 4)
        self.assertIsNone(s)
        self.assertIsNone(e)

    def test_first_clip(self):
        scene = {"start_time": 0.0, "end_time": 16.0}
        s, e = self.fn(scene, 1, 4)
        self.assertAlmostEqual(s, 0.0)
        self.assertAlmostEqual(e, 4.0)

    def test_last_clip(self):
        scene = {"start_time": 0.0, "end_time": 16.0}
        s, e = self.fn(scene, 4, 4)
        self.assertAlmostEqual(s, 12.0)
        self.assertAlmostEqual(e, 16.0)


class TestClipRole(unittest.TestCase):
    def setUp(self):
        from video_prompt_generator import _clip_role
        self.fn = _clip_role

    def test_single_clip(self):
        self.assertIn("single", self.fn(1, 1))

    def test_opening_clip(self):
        self.assertIn("opening", self.fn(1, 4))

    def test_transition_clip(self):
        self.assertIn("transition", self.fn(4, 4))

    def test_detail_clip(self):
        self.assertIn("detail", self.fn(2, 4))


class TestClipReferenceImageLabel(unittest.TestCase):
    def setUp(self):
        from video_prompt_generator import _clip_reference_image_label
        self.fn = _clip_reference_image_label

    def test_four_clips(self):
        labels = [self.fn(i, 4) for i in range(1, 5)]
        self.assertEqual(labels, ["wide", "action", "emotion", "detail"])

    def test_first_always_wide(self):
        self.assertEqual(self.fn(1, 2), "wide")
        self.assertEqual(self.fn(1, 3), "wide")

    def test_last_always_detail(self):
        self.assertEqual(self.fn(2, 2), "detail")
        self.assertEqual(self.fn(3, 3), "detail")


class TestMatchCameraKeyword(unittest.TestCase):
    def setUp(self):
        from video_prompt_generator import _match_camera_keyword
        self.fn = _match_camera_keyword

    def test_empty_camera(self):
        result = self.fn("", ["push-in", "tracking shot"])
        self.assertEqual(result, "tracking shot")

    def test_exact_keyword(self):
        result = self.fn("slow push-in from wide", ["push-in", "tracking shot", "dolly"])
        self.assertEqual(result, "push-in")

    def test_stopword_shot_not_matched(self):
        # "shot" is a stopword — should not cause "drone shot" to match on "shot"
        result = self.fn("wide establishing crane move", ["drone shot", "tracking shot", "crane"])
        self.assertNotEqual(result, "drone shot")

    def test_stopword_angle_not_matched(self):
        result = self.fn("medium forward dolly", ["low angle", "dolly", "static shot"])
        self.assertEqual(result, "dolly")

    def test_short_keywords_skipped(self):
        # Keywords ≤ 3 chars are skipped by the meaningful filter
        result = self.fn("fly through the air", ["fly", "orbital"])
        # "fly" is 3 chars — treated as not meaningful; fallback = "tracking shot"
        self.assertEqual(result, "tracking shot")


class TestStrategyPatternCoverage(unittest.TestCase):
    """모든 platforms.json 플랫폼 ID가 핸들러 테이블에 등록되었는지 검증."""

    def test_all_platforms_have_handlers(self):
        import video_prompt_generator as vpg
        missing = []
        for p in vpg._PLATFORMS:
            pid = p.get("id", "")
            if pid == "remotion":
                continue  # remotion은 별도 분기
            if pid not in vpg._PLATFORM_HANDLERS:
                missing.append(pid)
        self.assertEqual(missing, [], f"핸들러 미등록 플랫폼: {missing}")

    def test_no_phantom_handlers(self):
        import video_prompt_generator as vpg
        platform_ids = {p.get("id") for p in vpg._PLATFORMS if p.get("id") != "remotion"}
        extra = set(vpg._PLATFORM_HANDLERS.keys()) - platform_ids
        self.assertEqual(extra, set(), f"platforms.json에 없는 핸들러: {extra}")



class TestGenreSelectorSignalPop(unittest.TestCase):
    def test_signal_pop_profile_selected(self):
        import genre_selector
        song = {
            "title": "그래서 더 좋아",
            "genre": "korean signal pop, warm male vocal, ajaeng lead, telephone pulse rhythm, minimal drums, spacious uplifting atmosphere",
            "style_tags": [],
            "mood": [],
            "instruments": [],
            "atmosphere": "",
            "sections": [],
            "energy": "medium",
            "bpm": None,
        }
        profile = genre_selector.choose_genre_profile(song)
        self.assertEqual(profile.get("name"), "telephone-signal-pop")
        self.assertNotEqual(profile.get("name"), "intimate acoustic anime noir")


class TestRegressionAudioAsset(unittest.TestCase):
    def test_directory_without_audio(self):
        from run_regression import source_has_audio
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "raw_song.txt").write_text("Title: test", encoding="utf-8")
            self.assertFalse(source_has_audio(path))

    def test_directory_with_audio(self):
        from run_regression import source_has_audio
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "song.wav").write_bytes(b"RIFF")
            self.assertTrue(source_has_audio(path))

    def test_sibling_audio_for_text_input(self):
        from run_regression import source_has_audio
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "song.txt"
            path.write_text("Title: test", encoding="utf-8")
            path.with_suffix(".mp3").write_bytes(b"ID3")
            self.assertTrue(source_has_audio(path))


if __name__ == "__main__":
    unittest.main(verbosity=2)

