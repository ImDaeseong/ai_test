from pathlib import Path

from app.models.scene import Scene
from app.services.pexels_service import PexelsService, score_video, select_best_file


def test_select_best_file_prefers_resolution():
    video = {
        "video_files": [
            {"file_type": "video/mp4", "width": 640, "height": 360, "link": "a"},
            {"file_type": "video/mp4", "width": 1920, "height": 1080, "link": "b"},
        ]
    }
    assert select_best_file(video)["link"] == "b"


def test_score_video_rewards_matching_orientation():
    scene = Scene(
        scene="person walking",
        search_keywords="walking city",
        mood="quiet",
        camera="tracking",
        orientation="portrait",
        duration=5,
    )
    portrait = {"width": 1080, "height": 1920, "duration": 5}
    landscape = {"width": 1920, "height": 1080, "duration": 5}
    assert score_video(portrait, scene) > score_video(landscape, scene)


def test_empty_results_are_not_cached(tmp_path: Path, monkeypatch):
    """빈 검색 결과는 캐시에 저장되지 않아야 한다."""
    empty_response = {"videos": []}
    scene = Scene(scene="test", search_keywords="city", mood="calm", camera="wide", orientation="landscape", duration=5)

    cache_path = tmp_path / "pexels_landscape_city.json"
    service = PexelsService(api_key="test-key")

    monkeypatch.setattr(service, "_cache_file", lambda _: cache_path)
    monkeypatch.setattr(service, "_search", lambda *_: empty_response)

    try:
        service.search_best_video(scene)
    except RuntimeError:
        pass

    assert not cache_path.exists(), "빈 결과가 캐시에 저장되면 안 됨"


def test_score_video_rewards_landscape_orientation():
    scene = Scene(
        scene="wide city",
        search_keywords="wide city",
        mood="open",
        camera="wide",
        orientation="landscape",
        duration=5,
    )
    portrait = {"width": 1080, "height": 1920, "duration": 5}
    landscape = {"width": 1920, "height": 1080, "duration": 5}
    assert score_video(landscape, scene) > score_video(portrait, scene)
