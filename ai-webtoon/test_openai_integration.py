"""Regression tests for the local OpenAI panel-generation integration."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import budget_guard
import credential_loader
import image_client
import web_app


def _response(payload: bytes) -> MagicMock:
    result = MagicMock()
    result.data = [MagicMock(b64_json=base64.b64encode(payload).decode())]
    result.usage = MagicMock(model_dump=lambda: {"total_tokens": 7})
    return result


@patch("image_client.OpenAI")
def test_image_client_disables_retry_and_decodes_png(mock_openai):
    sdk = MagicMock()
    sdk.images.generate.return_value = _response(b"png")
    mock_openai.return_value = sdk

    content, usage = image_client.ImageClient(api_key="test-key").generate("prompt")

    assert content == b"png"
    assert usage == {"total_tokens": 7}
    mock_openai.assert_called_once_with(
        api_key="test-key", timeout=image_client.IMAGE_TIMEOUT_SECONDS, max_retries=0
    )
    sdk.images.generate.assert_called_once_with(
        model="gpt-image-2", prompt="prompt", size="1536x1024", n=1
    )


def test_missing_key_fails_before_network(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        image_client.ImageClient()


def test_budget_log_excludes_prompt_and_key(tmp_path):
    budget_guard.record_call(
        {"total_tokens": 4, "prompt": "private", "api_key": "secret"},
        logs_dir=tmp_path,
    )
    record = json.loads(next(tmp_path.glob("*.jsonl")).read_text(encoding="utf-8"))
    assert record["usage"] == {"total_tokens": 4}
    assert "private" not in json.dumps(record)
    assert "secret" not in json.dumps(record)


def test_budget_limit_blocks_next_call(tmp_path):
    budget_guard.record_call({}, logs_dir=tmp_path)
    with pytest.raises(budget_guard.BudgetExceededError):
        budget_guard.check_limit(logs_dir=tmp_path, limit=1)


def test_generate_route_saves_image_and_records_success(tmp_path, monkeypatch):
    panel_dir = tmp_path / "song" / "panels"
    panel_dir.mkdir(parents=True)
    panel = panel_dir / "panel_001_intro_wide.md"
    panel.write_text("## GPT Image (gpt-image-2)\n```text\npaint this panel\n```\n", encoding="utf-8")
    monkeypatch.setattr(web_app, "OUTPUT_DIR", tmp_path)

    client = MagicMock()
    client.generate.return_value = (b"png-bytes", {"total_tokens": 9})
    with patch.object(web_app, "ImageClient", return_value=client), \
         patch.object(web_app, "check_limit") as check_limit, \
         patch.object(web_app, "record_call") as record_call:
        response = web_app.app.test_client().post(
            "/api/song/song/panel/panel_001_intro_wide/generate"
        )

    assert response.status_code == 200
    assert (panel_dir / "panel_001_intro_wide" / "image.png").read_bytes() == b"png-bytes"
    check_limit.assert_called_once_with()
    client.generate.assert_called_once_with("paint this panel")
    record_call.assert_called_once_with({"total_tokens": 9})


def test_generate_route_hides_provider_error_details(tmp_path, monkeypatch):
    panel_dir = tmp_path / "song" / "panels"
    panel_dir.mkdir(parents=True)
    (panel_dir / "panel_001_intro_wide.md").write_text(
        "## GPT Image\n```\npaint this panel\n```\n", encoding="utf-8"
    )
    monkeypatch.setattr(web_app, "OUTPUT_DIR", tmp_path)
    client = MagicMock()
    client.generate.side_effect = RuntimeError("private provider detail")
    with patch.object(web_app, "ImageClient", return_value=client), \
         patch.object(web_app, "check_limit"), \
         patch.object(web_app, "record_call") as record_call:
        response = web_app.app.test_client().post(
            "/api/song/song/panel/panel_001_intro_wide/generate"
        )

    assert response.status_code == 502
    assert "private provider detail" not in response.get_data(as_text=True)
    record_call.assert_not_called()


def test_missing_key_route_returns_actionable_message(tmp_path, monkeypatch):
    panel = tmp_path / "output" / "song" / "panels" / "panel_001_intro_wide.md"
    panel.parent.mkdir(parents=True)
    panel.write_text("## GPT Image\n```\nprompt\n```", encoding="utf-8")
    monkeypatch.setattr(web_app, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(web_app, "check_limit", lambda: None)
    monkeypatch.setattr(web_app, "load_openai_api_key", lambda: False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with web_app.app.test_client() as client:
        response = client.post("/api/song/song/panel/panel_001_intro_wide/generate")

    assert response.status_code == 400
    assert "ai_agent/keyinfo/keys.env" in response.get_json()["error"]


def test_generate_route_loads_shared_key_at_request_time(tmp_path, monkeypatch):
    panel = tmp_path / "song" / "panels" / "panel_001_intro_wide.md"
    panel.parent.mkdir(parents=True)
    panel.write_text("## GPT Image\n```\npaint this panel\n```", encoding="utf-8")
    monkeypatch.setattr(web_app, "OUTPUT_DIR", tmp_path)
    load_key = MagicMock(return_value=True)
    client = MagicMock()
    client.generate.return_value = (b"png", {})
    monkeypatch.setattr(web_app, "load_openai_api_key", load_key)
    monkeypatch.setattr(web_app, "ImageClient", lambda: client)
    monkeypatch.setattr(web_app, "check_limit", lambda: None)
    monkeypatch.setattr(web_app, "record_call", lambda usage: None)

    response = web_app.app.test_client().post(
        "/api/song/song/panel/panel_001_intro_wide/generate"
    )

    assert response.status_code == 200
    load_key.assert_called_once_with()


def test_song_detail_tracks_generated_images_per_panel(tmp_path, monkeypatch):
    panels = tmp_path / "song" / "panels"
    panels.mkdir(parents=True)
    for key in ("panel_001_intro_wide", "panel_002_intro_closeup"):
        (panels / f"{key}.md").write_text("panel", encoding="utf-8")
    generated = panels / "panel_001_intro_wide"
    generated.mkdir()
    (generated / "image.png").write_bytes(b"png")
    monkeypatch.setattr(web_app, "OUTPUT_DIR", tmp_path)

    detail = web_app.get_song_detail("song")

    assert detail is not None
    assert [panel["generated"] for panel in detail["panels"]] == [True, False]


def test_modal_resets_shared_generate_button_from_current_panel_state():
    assert "currentPanel.generated ? '생성 완료' : '이미지 생성'" in web_app.HTML
    assert "currentPanel.generated = true" in web_app.HTML


def test_done_status_is_isolated_to_selected_panel(tmp_path, monkeypatch):
    panels = tmp_path / "song" / "panels"
    panels.mkdir(parents=True)
    for key in ("panel_001_intro_wide", "panel_002_intro_closeup"):
        (panels / f"{key}.md").write_text("panel", encoding="utf-8")
    monkeypatch.setattr(web_app, "OUTPUT_DIR", tmp_path)

    with web_app.app.test_client() as client:
        response = client.post(
            "/api/song/song/panel/panel_001_intro_wide/done", json={"done": True}
        )
        detail = client.get("/api/song/song").get_json()

    assert response.status_code == 200
    assert [panel["done"] for panel in detail["panels"]] == [True, False]


def test_web_launcher_does_not_embed_a_key():
    base = Path(__file__).parent
    launcher = (base / "run_web.bat").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=" not in launcher
    assert "Start-Process" not in launcher


def test_shared_key_loader_sets_only_requested_environment_variable(tmp_path, monkeypatch):
    keys = tmp_path / "keys.env"
    keys.write_text("OTHER_KEY=do-not-load\nOPENAI_API_KEY=test-secret\n", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OTHER_KEY", raising=False)

    assert credential_loader.load_openai_api_key(keys) is True
    assert __import__("os").environ["OPENAI_API_KEY"] == "test-secret"
    assert "OTHER_KEY" not in __import__("os").environ


def test_panel_resolution_rejects_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(web_app, "OUTPUT_DIR", tmp_path)
    assert web_app._panel_file("..", "panel_001_intro_wide") is None
    assert web_app._panel_file("song", "../secret") is None


def test_get_song_detail_rejects_traversal(tmp_path, monkeypatch):
    """2026-09-26 독립 리뷰 발견: get_song_detail에는 _panel_file과 같은 경계 검사가 전혀

    없어서, song_name에 ".."을 넣으면 OUTPUT_DIR 밖 임의 디렉터리의 panel_*.md/
    01_storyboard.md/00_style_reference.md 내용을 그대로 읽어 반환할 수 있었다."""
    monkeypatch.setattr(web_app, "OUTPUT_DIR", tmp_path / "output")
    web_app.OUTPUT_DIR.mkdir()
    secret_dir = tmp_path / "evil_secret" / "panels"
    secret_dir.mkdir(parents=True)
    (secret_dir / "panel_001_intro_wide.md").write_text("secret content leaked", encoding="utf-8")

    assert web_app.get_song_detail("../evil_secret") is None

    with web_app.app.test_client() as client:
        response = client.get("/api/song/..%5Cevil_secret")
        assert response.status_code == 404
        assert b"secret content leaked" not in response.data


def test_api_panel_done_rejects_traversal_write(tmp_path, monkeypatch):
    """2026-09-26 독립 리뷰 발견: api_panel_done은 song_name/panel_key를 검증하지 않고

    그대로 write_text에 넘겨서, ".."을 넣으면 OUTPUT_DIR 밖 임의 경로에 파일을 쓸 수
    있었다(임의 파일 쓰기)."""
    monkeypatch.setattr(web_app, "OUTPUT_DIR", tmp_path / "output")
    web_app.OUTPUT_DIR.mkdir()
    escape_target = tmp_path / "evil_secret" / "panels"
    escape_target.mkdir(parents=True)

    with web_app.app.test_client() as client:
        response = client.post(
            "/api/song/..%5Cevil_secret/panel/pwned/done",
            json={"done": True},
        )
        assert response.status_code == 404

    assert not (escape_target / "pwned.status.json").exists()


def test_prompt_parser_accepts_production_heading_and_unicode_dash():
    content = "## GPT Image (gpt-image-2) — 1792x1024\r\n\r\n```\r\npaint this panel\r\n```\r\n"
    assert web_app._gpt_image_prompt(content) == "paint this panel"
