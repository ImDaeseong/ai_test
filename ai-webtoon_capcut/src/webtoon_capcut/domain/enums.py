from enum import Enum


class SongStatus(Enum):
    PROMPTS_ONLY = "PROMPTS_ONLY"
    IMAGES_READY = "IMAGES_READY"
    MEDIA_READY = "MEDIA_READY"
    SUBTITLE_READY = "SUBTITLE_READY"
    BUILD_READY = "BUILD_READY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"


class CanonicalType(Enum):
    verse = "verse"
    chorus = "chorus"
    pre_chorus = "pre_chorus"
    post_chorus = "post_chorus"
    hook = "hook"
    drop = "drop"
    build = "build"
    bridge = "bridge"
    breakdown = "breakdown"
    instrumental = "instrumental"
    intro = "intro"
    outro = "outro"
    other = "other"


class IssueSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    REVIEW = "REVIEW"
    HOLD = "HOLD"
    BLOCKER = "BLOCKER"


class NormalizationState(Enum):
    RAW = "RAW"
    NORMALIZED = "NORMALIZED"
    ALIGNED = "ALIGNED"
    HUMAN_APPROVED = "HUMAN_APPROVED"


class BoundarySource(Enum):
    explicit_sidecar = "explicit_sidecar"
    trusted_section_cue = "trusted_section_cue"
    lyrics_alignment = "lyrics_alignment"
    storyboard_weight = "storyboard_weight"
    uniform_fallback = "uniform_fallback"
    human_override = "human_override"


class PanelType(Enum):
    wide = "wide"
    medium = "medium"
    closeup = "closeup"
    detail = "detail"
    crowd = "crowd"
    silhouette = "silhouette"
    atmosphere = "atmosphere"
    unknown = "unknown"


class SubtitleFormat(Enum):
    lrc = "lrc"
    srt = "srt"


class CueType(Enum):
    lyric = "lyric"
    metadata = "metadata"
    unknown = "unknown"


class RunStatus(Enum):
    OK = "OK"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    HOLD = "HOLD"
    FAILED = "FAILED"
