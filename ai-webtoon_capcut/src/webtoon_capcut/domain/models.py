from __future__ import annotations

from dataclasses import dataclass, field

from .enums import (
    BoundarySource,
    CanonicalType,
    CueType,
    IssueSeverity,
    NormalizationState,
    PanelType,
    RunStatus,
    SongStatus,
    SubtitleFormat,
)


@dataclass
class CanvasConfig:
    width: int = 1920
    height: int = 1080
    fps: int = 30
    fit: str = "cover"
    transition_ms: int = 300


@dataclass
class ClipPolicy:
    min_seconds: float = 2.5
    preferred_min_seconds: float = 4.0
    preferred_max_seconds: float = 8.0
    hard_max_seconds: float = 12.0
    max_reuse_per_image: int = 3


@dataclass
class SubtitlePolicy:
    long_cue_median_multiplier: float = 2.5
    long_cue_floor_seconds: float = 10.0
    long_cue_absolute_floor_seconds: float = 10.0
    alignment_mode: str = "auto"
    hold_on_unresolved_long_cue: bool = True


@dataclass
class Config:
    canvas: CanvasConfig = field(default_factory=CanvasConfig)
    clips: ClipPolicy = field(default_factory=ClipPolicy)
    subtitles: SubtitlePolicy = field(default_factory=SubtitlePolicy)
    schema_version: str = "3.0"


@dataclass
class PanelEntry:
    panel_id: str
    order: int
    section_label: str
    section_type: CanonicalType
    section_occurrence: int
    panel_type: PanelType
    recommended_duration_ms: int | None
    lyric_preview: str | None


@dataclass
class Storyboard:
    schema_version: str = "2.0"
    panels: list[PanelEntry] = field(default_factory=list)


@dataclass
class ImageCandidate:
    panel_id: str
    path: str
    extension: str
    width: int | None
    height: int | None
    sha256: str
    status: str = "MATCHED"


@dataclass
class AudioCandidate:
    path: str
    extension: str
    duration_ms: int | None
    sha256: str


@dataclass
class SubtitleCandidate:
    path: str
    fmt: SubtitleFormat
    cue_count: int
    quality_score: float
    sha256: str


@dataclass
class AssetInventory:
    schema_version: str = "2.0"
    storyboard_panel_count: int = 0
    images: list[ImageCandidate] = field(default_factory=list)
    audio_candidates: list[AudioCandidate] = field(default_factory=list)
    subtitle_candidates: list[SubtitleCandidate] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


@dataclass
class SongSource:
    song_dir: str
    storyboard: str | None
    song_text: str | None
    image_dir: str | None
    audio: str | None
    lrc: str | None
    srt: str | None


@dataclass
class SongManifest:
    schema_version: str = "2.0"
    song_id: str = ""
    title: str = ""
    source: SongSource = field(default_factory=lambda: SongSource(
        song_dir="", storyboard=None, song_text=None,
        image_dir=None, audio=None, lrc=None, srt=None,
    ))
    input_hashes: dict = field(default_factory=dict)
    profile: str = ""
    status: SongStatus = SongStatus.PROMPTS_ONLY
    warnings: list[str] = field(default_factory=list)


@dataclass
class SubtitleCue:
    cue_id: str
    start_ms: int
    end_ms: int
    raw_text: str
    text: str
    cue_type: CueType
    source_format: SubtitleFormat
    confidence: float
    review_required: bool


@dataclass
class SubtitleDocument:
    schema_version: str = "2.0"
    normalization_state: NormalizationState = NormalizationState.RAW
    cues: list[SubtitleCue] = field(default_factory=list)
    metadata_events: list[dict] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)


@dataclass
class SectionEntry:
    section_id: str
    label: str
    canonical_type: CanonicalType
    occurrence: int
    start_ms: int
    end_ms: int
    boundary_source: BoundarySource
    confidence: float
    panel_ids: list[str]
    review_required: bool


@dataclass
class SectionTimeline:
    schema_version: str = "2.0"
    sections: list[SectionEntry] = field(default_factory=list)


@dataclass
class TransitionOut:
    type: str = "crossfade"
    duration_ms: int = 250


@dataclass
class Clip:
    clip_id: str
    panel_id: str
    section_id: str
    media_path: str
    start_ms: int
    end_ms: int
    duration_ms: int
    motion_preset: str
    reuse_index: int
    fit: str
    transition_out: TransitionOut | None


@dataclass
class TimelineValidation:
    first_start_ms: int
    last_end_ms: int
    gap_count: int
    invalid_clip_count: int


@dataclass
class EditTimeline:
    schema_version: str = "2.0"
    audio_duration_ms: int = 0
    canvas: CanvasConfig = field(default_factory=CanvasConfig)
    clips: list[Clip] = field(default_factory=list)
    validation: TimelineValidation = field(
        default_factory=lambda: TimelineValidation(
            first_start_ms=0, last_end_ms=0, gap_count=0, invalid_clip_count=0
        )
    )


@dataclass
class ReviewIssue:
    issue_id: str
    stage: str
    severity: IssueSeverity
    code: str
    message: str
    evidence: dict
    suggested_action: str
    resolved: bool = False


@dataclass
class RunRecord:
    schema_version: str = "2.0"
    run_id: str = ""
    song_id: str = ""
    command: str = ""
    config_hash: str = ""
    input_hash: str = ""
    started_at: str = ""
    finished_at: str = ""
    status: RunStatus = RunStatus.OK
    artifacts: list[str] = field(default_factory=list)
    issues: list[ReviewIssue] = field(default_factory=list)


@dataclass
class SongCandidate:
    title: str
    song_dir: str
    status: SongStatus
    reasons: list[str] = field(default_factory=list)
