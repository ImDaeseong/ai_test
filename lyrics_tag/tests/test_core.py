"""
lyrics_tag/tests/test_core.py
Flask LRC 가사 편집 도구의 핵심 로직 단위 테스트

테스트 대상:
- LRC 타임스탬프 생성 공식 (센티초 변환, 분/초 분리)
- /download_lrc 엔드포인트의 입력 검증 및 응답 포맷
- 경계값 및 오류 케이스
"""

import sys
import os
import types
from unittest.mock import MagicMock

import pytest

# waitress 및 기타 미설치 의존성을 sys.modules에 stub 주입 (import 전에 처리)
if "waitress" not in sys.modules:
    _waitress_stub = types.ModuleType("waitress")
    _waitress_stub.serve = MagicMock()
    sys.modules["waitress"] = _waitress_stub

# lyrics_tag 패키지 경로를 sys.path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app as lrc_app  # noqa: E402 — 경로 삽입 후 import


# ---------------------------------------------------------------------------
# 헬퍼: 순수 함수로 추출한 타임스탬프 생성 로직
# ---------------------------------------------------------------------------

def make_lrc_tag(start_sec: float) -> str:
    """app.py download_lrc 내부의 태그 생성 공식을 그대로 복제."""
    start = max(0.0, float(start_sec))
    total_cs = round(start * 100)
    minutes, rem_cs = divmod(total_cs, 6000)
    return f"[{minutes:02d}:{rem_cs // 100:02d}.{rem_cs % 100:02d}]"


# ---------------------------------------------------------------------------
# 1. 타임스탬프 생성 — 정상 케이스
# ---------------------------------------------------------------------------

class TestMakeLrcTag:
    def test_zero_seconds(self):
        """0초 -> [00:00.00]"""
        assert make_lrc_tag(0) == "[00:00.00]"

    def test_one_minute_exact(self):
        """60초 -> [01:00.00]"""
        assert make_lrc_tag(60.0) == "[01:00.00]"

    def test_one_minute_thirty(self):
        """90초 -> [01:30.00]"""
        assert make_lrc_tag(90.0) == "[01:30.00]"

    def test_fractional_seconds(self):
        """1.23초 -> [00:01.23]"""
        assert make_lrc_tag(1.23) == "[00:01.23]"

    def test_negative_clamps_to_zero(self):
        """-5초 는 0으로 클램핑 -> [00:00.00]"""
        assert make_lrc_tag(-5.0) == "[00:00.00]"

    def test_near_minute_boundary(self):
        """59.995초 는 반올림 후 60.00초 -> [01:00.00] (float 오버플로우 방지 검증)"""
        assert make_lrc_tag(59.995) == "[01:00.00]"

    def test_large_time(self):
        """3661초 (1시간 1분 1초) -> [61:01.00]"""
        assert make_lrc_tag(3661.0) == "[61:01.00]"

    def test_centisecond_precision(self):
        """0.05초 (5 센티초) -> [00:00.05]"""
        assert make_lrc_tag(0.05) == "[00:00.05]"


# ---------------------------------------------------------------------------
# 2. Flask 엔드포인트 — /download_lrc
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """Flask 테스트 클라이언트."""
    lrc_app.app.config["TESTING"] = True
    with lrc_app.app.test_client() as c:
        yield c


class TestDownloadLrcEndpoint:
    def test_valid_single_segment(self, client):
        """/download_lrc: 정상 단일 세그먼트 -> 200 OK, LRC 텍스트 반환."""
        resp = client.post(
            "/download_lrc",
            json={"segments": [{"start": 0.0, "text": "Hello World"}]},
        )
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        assert "[00:00.00]Hello World" in body

    def test_valid_multiple_segments(self, client):
        """/download_lrc: 다중 세그먼트 -> 줄 개수와 타임스탬프 순서 확인."""
        segments = [
            {"start": 0.0, "text": "첫 번째"},
            {"start": 30.5, "text": "두 번째"},
            {"start": 61.0, "text": "세 번째"},
        ]
        resp = client.post("/download_lrc", json={"segments": segments})
        assert resp.status_code == 200
        lines = resp.data.decode("utf-8").splitlines()
        assert len(lines) == 3
        assert lines[0].startswith("[00:00.00]")
        assert lines[1].startswith("[00:30.50]")
        assert lines[2].startswith("[01:01.00]")

    def test_missing_segments_key(self, client):
        """/download_lrc: segments 키 없음 -> 400."""
        resp = client.post("/download_lrc", json={"foo": "bar"})
        assert resp.status_code == 400

    def test_segments_not_a_list(self, client):
        """/download_lrc: segments가 리스트가 아님 -> 400."""
        resp = client.post("/download_lrc", json={"segments": "not a list"})
        assert resp.status_code == 400

    def test_segment_not_a_dict(self, client):
        """/download_lrc: 세그먼트 항목이 dict가 아님 -> 400."""
        resp = client.post("/download_lrc", json={"segments": ["string_item"]})
        assert resp.status_code == 400

    def test_invalid_start_type(self, client):
        """/download_lrc: start 값이 변환 불가 타입 -> 400."""
        resp = client.post(
            "/download_lrc",
            json={"segments": [{"start": "abc", "text": "test"}]},
        )
        assert resp.status_code == 400

    def test_text_too_long(self, client):
        """/download_lrc: text가 MAX_TEXT_LENGTH 초과 -> 400."""
        long_text = "A" * (lrc_app.MAX_TEXT_LENGTH + 1)
        resp = client.post(
            "/download_lrc",
            json={"segments": [{"start": 0.0, "text": long_text}]},
        )
        assert resp.status_code == 400

    def test_empty_segments_list(self, client):
        """/download_lrc: 빈 리스트 -> 200 OK, 빈 본문."""
        resp = client.post("/download_lrc", json={"segments": []})
        assert resp.status_code == 200
        assert resp.data.decode("utf-8") == ""

    def test_content_disposition_header(self, client):
        """/download_lrc: 응답 헤더에 Content-Disposition 파일명 포함."""
        resp = client.post(
            "/download_lrc",
            json={"segments": [{"start": 1.0, "text": "test"}]},
        )
        assert resp.status_code == 200
        cd = resp.headers.get("Content-Disposition", "")
        assert "lyrics.lrc" in cd

    def test_negative_start_clamped(self, client):
        """/download_lrc: 음수 start -> 0으로 클램핑 후 정상 처리."""
        resp = client.post(
            "/download_lrc",
            json={"segments": [{"start": -10.0, "text": "negative"}]},
        )
        assert resp.status_code == 200
        assert resp.data.decode("utf-8").startswith("[00:00.00]")
