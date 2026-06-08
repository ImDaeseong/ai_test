from __future__ import annotations

from ..domain.enums import CueType, IssueSeverity, NormalizationState
from ..domain.models import SubtitleCue, SubtitleDocument, SubtitlePolicy
from .classifier import classify_cue, detect_long_cues, is_suno_prompt_block

# issue가 이 개수 이상이면 normalization_state를 RAW로 유지한다
_TOO_MANY_ISSUES_THRESHOLD = 10


def normalize_subtitles(
    cues: list[SubtitleCue],
    policy: SubtitlePolicy,
) -> SubtitleDocument:
    """cue 목록을 정규화하여 SubtitleDocument를 반환한다.

    처리 단계:
    1. classify_cue()로 각 cue 분류
    2. is_suno_prompt_block()으로 프롬프트 블록 탐지 후 metadata_events로 이동
    3. detect_long_cues()로 긴 cue 탐지 후 issues 추가
    4. 역전/중복 cue 탐지 후 issues 추가
    5. normalization_state 결정
    """
    doc = SubtitleDocument()
    issues: list[dict] = []
    metadata_events: list[dict] = []
    lyric_cues: list[SubtitleCue] = []

    # 단계 1 & 2: 분류 및 프롬프트 블록 탐지
    for idx, cue in enumerate(cues):
        cue_type = classify_cue(cue)

        if cue_type == CueType.metadata:
            # 프롬프트 블록 탐지
            if is_suno_prompt_block(cues, idx):
                metadata_events.append({
                    "cue_id": cue.cue_id,
                    "start_ms": cue.start_ms,
                    "end_ms": cue.end_ms,
                    "text": cue.text,
                    "reason": "suno_prompt_block",
                })
            else:
                metadata_events.append({
                    "cue_id": cue.cue_id,
                    "start_ms": cue.start_ms,
                    "end_ms": cue.end_ms,
                    "text": cue.text,
                    "reason": "metadata_cue",
                })
        else:
            # cue_type을 lyric으로 갱신하여 저장
            updated = SubtitleCue(
                cue_id=cue.cue_id,
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                raw_text=cue.raw_text,
                text=cue.text,
                cue_type=CueType.lyric,
                source_format=cue.source_format,
                confidence=cue.confidence,
                review_required=cue.review_required,
            )
            lyric_cues.append(updated)

    # 단계 3: 긴 cue 탐지 (lyric cue 대상)
    long_cue_ids = detect_long_cues(
        lyric_cues,
        median_mult=policy.long_cue_median_multiplier,
        floor_sec=policy.long_cue_floor_seconds,
    )
    for cue_id in long_cue_ids:
        severity = (
            IssueSeverity.HOLD
            if policy.hold_on_unresolved_long_cue
            else IssueSeverity.WARNING
        )
        issues.append({
            "code": "LONG_CUE",
            "severity": severity.value,
            "cue_id": cue_id,
            "message": f"cue {cue_id!r} duration exceeds threshold",
        })

    # 단계 4: 역전/중복 cue 탐지 (lyric cue 대상)
    for i, cue in enumerate(lyric_cues):
        # 역전: end_ms <= start_ms
        if cue.end_ms <= cue.start_ms:
            issues.append({
                "code": "INVERTED_CUE",
                "severity": IssueSeverity.REVIEW.value,
                "cue_id": cue.cue_id,
                "message": (
                    f"cue {cue.cue_id!r} end_ms ({cue.end_ms}) "
                    f"<= start_ms ({cue.start_ms})"
                ),
            })

        # 중복: 이전 cue와 시작 시간 겹침
        if i > 0:
            prev = lyric_cues[i - 1]
            if cue.start_ms < prev.end_ms:
                issues.append({
                    "code": "OVERLAPPING_CUE",
                    "severity": IssueSeverity.WARNING.value,
                    "cue_id": cue.cue_id,
                    "message": (
                        f"cue {cue.cue_id!r} start_ms ({cue.start_ms}) "
                        f"overlaps previous end_ms ({prev.end_ms})"
                    ),
                    "prev_cue_id": prev.cue_id,
                })

        # 순서 역전: 이전 cue보다 시작 시간이 앞
        if i > 0:
            prev = lyric_cues[i - 1]
            if cue.start_ms < prev.start_ms:
                issues.append({
                    "code": "OUT_OF_ORDER_CUE",
                    "severity": IssueSeverity.REVIEW.value,
                    "cue_id": cue.cue_id,
                    "message": (
                        f"cue {cue.cue_id!r} start_ms ({cue.start_ms}) "
                        f"precedes previous cue start_ms ({prev.start_ms})"
                    ),
                    "prev_cue_id": prev.cue_id,
                })

    # 단계 5: normalization_state 결정
    if len(issues) >= _TOO_MANY_ISSUES_THRESHOLD:
        state = NormalizationState.RAW
    else:
        state = NormalizationState.NORMALIZED

    doc.normalization_state = state
    doc.cues = lyric_cues
    doc.metadata_events = metadata_events
    doc.issues = issues
    return doc


def _quality_score(cues: list[SubtitleCue]) -> float:
    """cue 목록의 품질 점수를 계산한다 (높을수록 좋음).

    평가 기준:
    - lyric cue 비율
    - 역전/중복 cue 비율 (낮을수록 좋음)
    - confidence 평균
    """
    if not cues:
        return 0.0

    lyric_count = sum(1 for c in cues if classify_cue(c) == CueType.lyric)
    lyric_ratio = lyric_count / len(cues)

    inverted = sum(1 for c in cues if c.end_ms <= c.start_ms)
    overlap = sum(
        1 for i, c in enumerate(cues)
        if i > 0 and c.start_ms < cues[i - 1].end_ms
    )
    bad_ratio = (inverted + overlap) / len(cues)

    avg_confidence = sum(c.confidence for c in cues) / len(cues)

    # 가중 합산: lyric 비율과 confidence 우선, 문제 cue 패널티
    return lyric_ratio * 0.5 + avg_confidence * 0.4 - bad_ratio * 0.3


def select_best_subtitle(
    lrc_cues: list[SubtitleCue] | None,
    srt_cues: list[SubtitleCue] | None,
) -> tuple[list[SubtitleCue], str]:
    """LRC/SRT 중 품질 점수가 높은 쪽을 선택하고 이유를 반환한다.

    - 둘 다 있으면 quality_score를 비교하여 높은 쪽을 선택
    - 한쪽만 있으면 그쪽을 선택
    - 둘 다 없으면 빈 목록 반환
    """
    has_lrc = bool(lrc_cues)
    has_srt = bool(srt_cues)

    if has_lrc and has_srt:
        lrc_score = _quality_score(lrc_cues)  # type: ignore[arg-type]
        srt_score = _quality_score(srt_cues)  # type: ignore[arg-type]
        if lrc_score >= srt_score:
            return (
                lrc_cues,  # type: ignore[return-value]
                f"lrc selected: score {lrc_score:.3f} >= srt score {srt_score:.3f}",
            )
        return (
            srt_cues,  # type: ignore[return-value]
            f"srt selected: score {srt_score:.3f} > lrc score {lrc_score:.3f}",
        )

    if has_lrc:
        return lrc_cues, "lrc selected: only lrc available"  # type: ignore[return-value]

    if has_srt:
        return srt_cues, "srt selected: only srt available"  # type: ignore[return-value]

    return [], "no subtitle candidates available"
