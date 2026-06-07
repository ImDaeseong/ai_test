# 데이터 계약 V2

## 1. 계약 원칙

- 경로는 manifest 파일 기준 상대 경로로 저장한다.
- 시간은 정수 밀리초로 저장한다.
- 모든 JSON에 `schema_version`을 포함한다.
- 입력 파일 해시와 설정 해시를 기록한다.
- 추론된 값에는 source, confidence, review 상태를 기록한다.
- 알 수 없는 값을 임의 값으로 채우지 않고 `null`로 보존한다.

## 2. Song Manifest

```json
{
  "schema_version": "2.0",
  "song_id": "upgrade-a1b2c3d4",
  "title": "UPGRADE",
  "source": {
    "song_dir": "../../ai-webtoon/output/UPGRADE",
    "storyboard": "01_storyboard.md",
    "song_text": "../../ai-webtoon/input/UPGRADE.txt",
    "image_dir": "img",
    "audio": "UPGRADE.wav",
    "lrc": "lyrics.lrc",
    "srt": "lyrics.srt"
  },
  "input_hashes": {},
  "profile": "youtube_1080p",
  "status": "BUILD_READY",
  "warnings": []
}
```

`song_id`는 안전한 slug와 입력 식별 해시로 만든다. 같은 제목의 다른 버전을 구분해야 한다.

## 3. Asset Inventory

```json
{
  "schema_version": "2.0",
  "storyboard_panel_count": 42,
  "images": [
    {
      "panel_id": "panel_001",
      "path": "img/panel_001_intro_wide.png",
      "extension": ".png",
      "width": 1659,
      "height": 948,
      "sha256": "...",
      "status": "MATCHED"
    }
  ],
  "audio_candidates": [],
  "subtitle_candidates": [],
  "conflicts": []
}
```

## 4. Storyboard Model

```json
{
  "schema_version": "2.0",
  "panels": [
    {
      "panel_id": "panel_001",
      "order": 1,
      "section_label": "Intro",
      "section_type": "intro",
      "section_occurrence": 1,
      "panel_type": "wide",
      "recommended_duration_ms": 5000,
      "lyric_preview": "Instrumental"
    }
  ]
}
```

`section_occurrence`는 같은 canonical type의 반복 순서를 나타낸다.

## 5. Subtitle Model

```json
{
  "schema_version": "2.0",
  "normalization_state": "NORMALIZED",
  "cues": [
    {
      "cue_id": "cue_001",
      "start_ms": 24335,
      "end_ms": 26888,
      "raw_text": "어제의 껍질을 찢어 발겨",
      "text": "어제의 껍질을 찢어 발겨",
      "type": "lyric",
      "source_format": "srt",
      "confidence": 0.98,
      "review_required": false
    }
  ],
  "metadata_events": [],
  "issues": []
}
```

허용 상태:

```text
RAW
NORMALIZED
ALIGNED
HUMAN_APPROVED
```

## 6. Section Timeline

```json
{
  "schema_version": "2.0",
  "sections": [
    {
      "section_id": "chorus-2",
      "label": "Final Chorus",
      "type": "chorus",
      "occurrence": 2,
      "start_ms": 192048,
      "end_ms": 217100,
      "boundary_source": "lyrics_alignment",
      "confidence": 0.91,
      "panel_ids": [
        "panel_032",
        "panel_033"
      ],
      "review_required": false
    }
  ]
}
```

허용 `boundary_source`:

```text
explicit_sidecar
trusted_section_cue
lyrics_alignment
storyboard_weight
uniform_fallback
human_override
```

## 7. Edit Timeline

```json
{
  "schema_version": "2.0",
  "audio_duration_ms": 242952,
  "canvas": {
    "width": 1920,
    "height": 1080,
    "fps": 30
  },
  "clips": [
    {
      "clip_id": "clip_001",
      "panel_id": "panel_001",
      "section_id": "intro-1",
      "media_path": "../../../source/img/panel_001_intro_wide.png",
      "start_ms": 0,
      "end_ms": 8112,
      "duration_ms": 8112,
      "motion_preset": "slow_zoom_in",
      "reuse_index": 0,
      "fit": "cover",
      "transition_out": {
        "type": "crossfade",
        "duration_ms": 250
      }
    }
  ],
  "validation": {
    "first_start_ms": 0,
    "last_end_ms": 242952,
    "gap_count": 0,
    "invalid_clip_count": 0
  }
}
```

## 8. Review Issue

```json
{
  "issue_id": "SUBTITLE_LONG_CUE_001",
  "stage": "subtitle_normalization",
  "severity": "HOLD",
  "code": "LONG_LYRIC_CUE",
  "message": "가사 cue 종료와 다음 섹션 사이에 긴 연주 구간이 있습니다.",
  "evidence": {
    "cue_id": "cue_089",
    "duration_ms": 57048
  },
  "suggested_action": "보컬 종료와 솔로 시작을 확인하십시오.",
  "resolved": false
}
```

심각도:

```text
INFO
WARNING
REVIEW
HOLD
BLOCKER
```

## 9. Run Record

```json
{
  "schema_version": "2.0",
  "run_id": "20260606T140000Z-a1b2c3d4",
  "song_id": "upgrade-a1b2c3d4",
  "command": "plan",
  "config_hash": "...",
  "input_hash": "...",
  "started_at": "2026-06-06T14:00:00Z",
  "finished_at": "2026-06-06T14:00:03Z",
  "status": "REVIEW_REQUIRED",
  "artifacts": [],
  "issues": []
}
```

## 10. 설정 프로필

```yaml
schema_version: "2.0"

canvas:
  width: 1920
  height: 1080
  fps: 30
  fit: cover

clips:
  min_seconds: 2.5
  preferred_min_seconds: 4.0
  preferred_max_seconds: 8.0
  hard_max_seconds: 12.0
  max_reuse_per_image: 3

subtitles:
  prefer: auto_score
  normalize_suno_metadata: true
  forced_alignment: false
  require_human_approval_on_hold: true

render:
  preview_scale: 0.5
  full_video: true
  section_videos: false
```

## 11. 스키마 검증 규칙

- panel ID는 곡 안에서 유일하다.
- panel order는 1부터 연속적이어야 한다.
- image 매칭은 panel마다 정확히 하나여야 한다.
- section start < end다.
- clip start < end다.
- 첫 clip은 0에서 시작한다.
- 인접 clip은 허용된 transition 중첩 외에 빈 구간이 없어야 한다.
- 마지막 clip은 오디오 길이와 1프레임 이내 일치한다.
- 모든 media path는 허용된 source root 아래에 있어야 한다.
- `HOLD` 또는 `BLOCKER` 이슈가 있으면 `HUMAN_APPROVED` 상태가 될 수 없다.

