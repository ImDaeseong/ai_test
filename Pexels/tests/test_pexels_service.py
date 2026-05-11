from app.models.scene import Scene
from app.services.pexels_service import score_video, select_best_file


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
