from __future__ import annotations

import html
import json
import os
from pathlib import Path

from app.models.response import GenerateVideoResponse
from app.services.data_input_service import DataAssets


class HtmlReportService:
    def write_report(self, result: GenerateVideoResponse, assets: DataAssets, report_path: Path) -> Path:
        return self.write_multi_report([result], assets, report_path)

    def write_multi_report(self, results: list[GenerateVideoResponse], assets: DataAssets, report_path: Path) -> Path:
        if not results:
            raise RuntimeError("No results to write.")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        sections = "\n".join(self._result_section(result, assets, report_path.parent) for result in results)
        report_path.write_text(self._document("AI Video Results", sections), encoding="utf-8")
        return report_path

    def _result_section(self, result: GenerateVideoResponse, assets: DataAssets, base_dir: Path) -> str:
        output_file = Path(result.output_file or "")
        video_src = self._relative(output_file, base_dir)
        ratio_class = self._ratio_class(result)
        metadata = {
            "status": result.status,
            "project_id": result.project_id,
            "output_file": result.output_file,
            "lyric_file": str(assets.lyric_file),
            "audio_file": str(assets.audio_file) if assets.audio_file else None,
            "subtitle_file": str(assets.subtitle_file) if assets.subtitle_file else None,
            "image_file": str(assets.image_file) if assets.image_file else None,
            "scene_count": len(result.scenes),
            "youtube_profile": "MP4, H.264 High Profile, yuv420p, 30fps, AAC 48kHz, faststart",
        }
        scene_cards = "\n".join(
            f"""
            <article class="scene-card">
              <div class="scene-media">
                <video class="{html.escape(ratio_class)}" controls src="{html.escape(self._scene_video_src(scene, base_dir))}"></video>
              </div>
              <div class="scene-body">
                <h3>Scene {index}</h3>
                <dl>
                  <dt>Korean</dt>
                  <dd>{html.escape(scene.scene_ko or "No Korean description.")}</dd>
                  <dt>English scene</dt>
                  <dd>{html.escape(scene.scene)}</dd>
                  <dt>Keywords</dt>
                  <dd>{html.escape(scene.search_keywords)}</dd>
                  <dt>Mood</dt>
                  <dd>{html.escape(scene.mood)}</dd>
                  <dt>Camera</dt>
                  <dd>{html.escape(scene.camera)}</dd>
                  <dt>Duration / Pexels ID</dt>
                  <dd>{html.escape(str(scene.duration))}s / {html.escape(str(scene.video_id or ""))}</dd>
                </dl>
              </div>
            </article>
            """
            for index, scene in enumerate(result.scenes, start=1)
        )
        return f"""
        <section>
          <h2>{html.escape(output_file.name or "Result")}</h2>
          <video class="{html.escape(ratio_class)}" controls src="{html.escape(video_src)}"></video>
        </section>
        <section>
          <h2>Summary</h2>
          <pre>{html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))}</pre>
        </section>
        <section>
          <h2>Scene Videos</h2>
          {scene_cards}
        </section>
        """

    def _document(self, title: str, content: str) -> str:
        return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Arial, "Malgun Gothic", sans-serif;
      background: #f6f7f9;
      color: #1e242c;
    }}
    body {{
      margin: 0;
      padding: 32px;
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
    }}
    h1 {{
      font-size: 28px;
      margin: 0 0 18px;
    }}
    video {{
      width: 100%;
      background: #111;
      border-radius: 8px;
    }}
    .ratio-landscape {{
      aspect-ratio: 16 / 9;
    }}
    .ratio-portrait {{
      aspect-ratio: 9 / 16;
      max-width: 390px;
    }}
    .ratio-square {{
      aspect-ratio: 1 / 1;
      max-width: 520px;
    }}
    section {{
      background: #fff;
      border: 1px solid #d9dee7;
      border-radius: 8px;
      padding: 18px;
      margin-bottom: 18px;
    }}
    .scene-card {{
      display: grid;
      grid-template-columns: 220px 1fr;
      gap: 16px;
      padding: 14px 0;
      border-top: 1px solid #e7ebf0;
    }}
    .scene-card:first-child {{
      border-top: 0;
    }}
    .scene-media video {{
      width: 100%;
      border-radius: 6px;
    }}
    h2 {{
      margin-top: 0;
    }}
    h3 {{
      margin: 0 0 10px;
      font-size: 18px;
    }}
    dl {{
      margin: 0;
      display: grid;
      grid-template-columns: 135px 1fr;
      gap: 8px 12px;
      font-size: 14px;
    }}
    dt {{
      font-weight: 700;
      color: #526071;
    }}
    dd {{
      margin: 0;
    }}
    pre {{
      overflow: auto;
      background: #f1f4f8;
      padding: 12px;
      border-radius: 6px;
      font-size: 13px;
    }}
    @media (max-width: 860px) {{
      body {{ padding: 18px; }}
      .scene-card {{ grid-template-columns: 1fr; }}
      .scene-media video {{ max-width: 320px; }}
      dl {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(title)}</h1>
    {content}
  </main>
</body>
</html>
"""

    def _relative(self, target: Path, base_dir: Path) -> str:
        return Path(os.path.relpath(target.resolve(), base_dir.resolve())).as_posix()

    def _scene_video_src(self, scene, base_dir: Path) -> str:
        if scene.processed_file:
            return self._relative(Path(scene.processed_file), base_dir)
        if scene.video_file:
            return self._relative(Path(scene.video_file), base_dir)
        return ""

    def _ratio_class(self, result: GenerateVideoResponse) -> str:
        orientation = result.scenes[0].orientation if result.scenes else "portrait"
        if orientation == "landscape":
            return "ratio-landscape"
        if orientation == "square":
            return "ratio-square"
        return "ratio-portrait"
