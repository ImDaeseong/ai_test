from __future__ import annotations

import re
import statistics

from ..domain.enums import CueType
from ..domain.models import SubtitleCue

# 대괄호 전체 텍스트 패턴: [Verse], [Chorus 2] 등
_BRACKET_ONLY_RE = re.compile(r"^\s*\[[^\]]*\]\s*$")


def classify_cue(cue: SubtitleCue) -> CueType:
    """단일 cue를 lyric 또는 metadata로 분류한다.

    분류 기준:
    - 텍스트 전체가 대괄호 표현인 경우: metadata
    - 빈 텍스트인 경우: metadata
    - 그 외: lyric
    """
    text = cue.text.strip() if cue.text else ""
    if not text:
        return CueType.metadata
    if _BRACKET_ONLY_RE.match(text):
        return CueType.metadata
    return CueType.lyric


def is_suno_prompt_block(cues: list[SubtitleCue], idx: int) -> bool:
    """초반 고밀도 대괄호 메타데이터 블록을 탐지한다.

    조건:
    - idx 기준 cue가 처음 30초(30_000 ms) 이내에 위치
    - idx 자체가 metadata cue
    - idx 포함 연속 3개 이상 metadata cue
    - 해당 cue들의 텍스트가 모두 대괄호로 시작

    위 조건을 모두 만족하면 True를 반환한다.
    """
    if idx < 0 or idx >= len(cues):
        return False

    cue = cues[idx]

    # idx cue 자체가 metadata여야 한다
    if classify_cue(cue) != CueType.metadata:
        return False

    if cue.start_ms > 30_000:
        return False

    # idx 위치에서 연속 metadata cue 구간의 시작 인덱스를 찾는다
    block_start = idx
    while block_start > 0 and classify_cue(cues[block_start - 1]) == CueType.metadata:
        block_start -= 1

    # block_start 부터 연속 metadata cue 개수를 센다
    block_end = block_start
    while block_end < len(cues) and classify_cue(cues[block_end]) == CueType.metadata:
        block_end += 1

    consecutive_count = block_end - block_start
    if consecutive_count < 3:
        return False

    # 해당 블록의 모든 cue 텍스트가 대괄호로 시작하는지 확인
    for i in range(block_start, block_end):
        text = cues[i].text.strip() if cues[i].text else ""
        if not text.startswith("["):
            return False

    return True


def detect_long_cues(
    cues: list[SubtitleCue],
    median_mult: float = 2.5,
    floor_sec: float = 10.0,
) -> list[str]:
    """비정상적으로 긴 cue의 cue_id 목록을 반환한다.

    기준: duration_ms >= max(median * median_mult, floor_sec * 1000)

    cue가 없거나 duration 계산 불가 시 빈 목록을 반환한다.
    """
    if not cues:
        return []

    durations = [c.end_ms - c.start_ms for c in cues]
    durations_positive = [d for d in durations if d > 0]
    if not durations_positive:
        return []

    median_ms = statistics.median(durations_positive)
    threshold_ms = max(median_ms * median_mult, floor_sec * 1000)

    return [
        cue.cue_id
        for cue, dur in zip(cues, durations)
        if dur >= threshold_ms
    ]
