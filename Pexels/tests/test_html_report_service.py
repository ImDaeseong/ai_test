from app.models.response import GenerateVideoResponse
from app.models.scene import SceneWithVideo
from app.services.data_input_service import DataAssets
from app.services.html_report_service import HtmlReportService


def test_multi_report_contains_both_outputs(tmp_path):
    assets = DataAssets(
        data_dir=tmp_path,
        lyric_file=tmp_path / "lyrics.lrc",
        text="hello",
    )
    landscape = GenerateVideoResponse(
        status="success",
        project_id="land",
        output_file=str(tmp_path / "final_landscape.mp4"),
        scenes=[
            SceneWithVideo(
                scene="wide scene",
                scene_ko="넓은 장면",
                search_keywords="wide",
                mood="open",
                camera="wide",
                orientation="landscape",
                duration=5,
                processed_file=str(tmp_path / "land_scene.mp4"),
            )
        ],
    )
    shorts = GenerateVideoResponse(
        status="success",
        project_id="shorts",
        output_file=str(tmp_path / "final_shorts.mp4"),
        scenes=[
            SceneWithVideo(
                scene="vertical scene",
                scene_ko="세로 장면",
                search_keywords="vertical",
                mood="close",
                camera="close",
                orientation="portrait",
                duration=5,
                processed_file=str(tmp_path / "shorts_scene.mp4"),
            )
        ],
    )

    report = tmp_path / "index.html"
    HtmlReportService().write_multi_report([landscape, shorts], assets, report)
    content = report.read_text(encoding="utf-8")

    assert "final_landscape.mp4" in content
    assert "final_shorts.mp4" in content
    assert "ratio-landscape" in content
    assert "ratio-portrait" in content
    assert "넓은 장면" in content
