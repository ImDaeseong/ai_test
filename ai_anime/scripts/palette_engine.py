"""palette_engine.py — 팔레트 상태 관리 및 색상 토큰 치환 엔진.

scene_generator.py에서 분리된 모듈.
BRAND_PALETTE 전역 상태, 치환 패턴 컴파일, select_theme/inject/apply 함수를 한 곳에 집중.

외부에서 사용하는 공개 API:
  select_theme(style_id)          — 생성마다 팔레트 초기화
  inject_song_color(main_color)   — 곡별 주색 주입
  apply_full_palette(text)        — 모든 색상 토큰 치환 (단일 진입점)
  BRAND_PALETTE                   — 현재 활성 팔레트 (읽기 전용으로 취급)
  COLOR_BALANCE_BY_STAGE          — 스테이지별 색상 비율
  ACTIVE_STYLE_ID                 — 현재 활성 스타일 ID
"""
from __future__ import annotations

import re
from typing import Any

from common import load_config


_STYLE_CONFIG = load_config("visual_styles")
_PALETTE_SUB_CONFIG = load_config("palette_substitutions")

# 전역 애니메이션 제약 — 모든 프롬프트에 공통 적용
_ANIME = _STYLE_CONFIG.get("global_anime_constraints", {})
STYLE_POSITIVE: str = ", ".join(_ANIME.get("style_enforcement", []))
STYLE_NEGATIVE: str = ". ".join(_ANIME.get("negative_enforcement", []))
VIDEO_NEGATIVE: str = ". ".join(_ANIME.get("video_negative_enforcement", []))

# 활성 팔레트 — select_theme() 호출 시 초기화, inject_song_color() 호출 시 주색 갱신.
# 웹 서버는 _generate_lock으로 직렬화하므로 단일 스레드처럼 사용 가능.
BRAND_PALETTE: dict[str, Any] = {}
COLOR_BALANCE_BY_STAGE: dict[str, Any] = {}
ACTIVE_STYLE_ID: str = ""


def _compile_patterns(patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


# 치환 패턴 — palette_substitutions.json 단일 소스
_COLOR_SUBS = _compile_patterns(_PALETTE_SUB_CONFIG.get("main_color_patterns", []))
_AMBIENT_SUBS: dict[str, list[re.Pattern[str]]] = {
    key: _compile_patterns(pats)
    for key, pats in _PALETTE_SUB_CONFIG.get("ambient_patterns", {}).items()
}
_STYLE_WORD_SUBS = [
    {**item, "compiled": re.compile(item["pattern"], re.IGNORECASE)}
    for item in _PALETTE_SUB_CONFIG.get("style_word_substitutions", [])
    if item.get("pattern")
]


def _replace_patterns(text: str, patterns: list[re.Pattern[str]], replacement: str) -> str:
    for pattern in patterns:
        text = pattern.sub(replacement, text)
    return text


def select_theme(style_id: str | None = None) -> None:
    """생성 시작 시 호출. 팔레트 전역 상태를 지정 스타일로 초기화한다."""
    global BRAND_PALETTE, COLOR_BALANCE_BY_STAGE, ACTIVE_STYLE_ID
    style_id = style_id or _STYLE_CONFIG.get("default_style", "dreamy_synth")
    style_data = _STYLE_CONFIG.get("styles", {}).get(style_id, {})
    if not style_data:
        first_key = next(iter(_STYLE_CONFIG.get("styles", {}).keys()), "dreamy_synth")
        style_id = first_key
        style_data = _STYLE_CONFIG.get("styles", {}).get(first_key, {})
    ACTIVE_STYLE_ID = style_id
    # shallow copy: _inject_song_color()의 변경이 _STYLE_CONFIG 원본에 영향 안 줌
    BRAND_PALETTE = dict(style_data.get("brand_palette", {}))
    COLOR_BALANCE_BY_STAGE = style_data.get("color_balance_by_stage", {})


def inject_song_color(main_color: str) -> None:
    """BRAND_PALETTE에 곡별 주색을 주입한다. 스타일 하이라이트/세컨더리는 보존."""
    style_highlight = BRAND_PALETTE.get("highlight", "silver-white rim highlights")
    style_secondary = BRAND_PALETTE.get("secondary_light", "subtle secondary reflections")
    BRAND_PALETTE["main_color"] = main_color
    BRAND_PALETTE["visual_identity"] = _replace_patterns(
        BRAND_PALETTE.get("visual_identity", "dark anime"), _COLOR_SUBS, main_color
    )
    BRAND_PALETTE["palette_rule"] = (
        f"limited-color anime palette: {main_color} dominant, "
        f"dark shadows, near-black backgrounds, {style_secondary}, {style_highlight}"
    )


def apply_full_palette(text: str) -> str:
    """모든 색상 토큰(주색 + ambient + 스타일 단어)을 활성 팔레트 값으로 치환한다.

    단일 진입점: 이 함수만 호출하면 누락 없음.
    _apply_color()는 이 함수 내부에서만 사용됨.
    """
    # 1. 주색 토큰 치환
    text = _replace_patterns(text, _COLOR_SUBS, BRAND_PALETTE.get("main_color", "neon magenta"))
    # 2. Ambient 토큰 치환 (shadow, secondary_light, highlight)
    for palette_key, patterns in _AMBIENT_SUBS.items():
        text = _replace_patterns(text, patterns, BRAND_PALETTE.get(palette_key, "accent light"))
    # 3. 스타일 단어 치환 (cyberpunk → stylized 등)
    for item in _STYLE_WORD_SUBS:
        replacement = item.get("replacement")
        if not replacement and item.get("palette_key"):
            replacement = BRAND_PALETTE.get(item["palette_key"], item.get("fallback", "accent-light"))
        text = item["compiled"].sub(str(replacement or ""), text)
    return text


def apply_main_color_only(text: str, color: str) -> str:
    """주색 토큰(neon magenta, cyber pink)만 color로 치환. ambient 토큰은 그대로."""
    return _replace_patterns(text, _COLOR_SUBS, color)


# 모듈 로드 시 기본 테마로 초기화 (scene_generator.py 동작과 동일)
select_theme()
