import pytest

from app.services.gemini_service import parse_scenes_json


def test_parse_valid_scene_json():
    scenes = parse_scenes_json(
        """
        [
          {
            "scene": "rainy neon city street",
            "search_keywords": "rainy neon city",
            "mood": "lonely",
            "camera": "slow tracking",
            "orientation": "portrait",
            "duration": 5
          }
        ]
        """
    )
    assert len(scenes) == 1
    assert scenes[0].orientation == "portrait"


def test_parse_rejects_invalid_json():
    with pytest.raises(ValueError):
        parse_scenes_json("not json")


def test_parse_rejects_empty_array():
    with pytest.raises(ValueError):
        parse_scenes_json("[]")
