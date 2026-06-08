from enum import Enum


class ErrorCode(str, Enum):
    STORYBOARD_MISSING = "STORYBOARD_MISSING"
    AUDIO_MISSING = "AUDIO_MISSING"
    AUDIO_AMBIGUOUS = "AUDIO_AMBIGUOUS"
    IMAGE_MISSING = "IMAGE_MISSING"
    IMAGE_AMBIGUOUS = "IMAGE_AMBIGUOUS"
    IMAGE_INVALID = "IMAGE_INVALID"
    SUBTITLE_INVALID = "SUBTITLE_INVALID"
    SECTION_LOW_CONFIDENCE = "SECTION_LOW_CONFIDENCE"
    TIMELINE_INVALID = "TIMELINE_INVALID"
    RENDER_FAILED = "RENDER_FAILED"
    PATH_OUTSIDE_ROOT = "PATH_OUTSIDE_ROOT"
    REVIEW_HOLD = "REVIEW_HOLD"
    CONFIG_INVALID = "CONFIG_INVALID"


class WCError(Exception):
    pass


class WCValidationError(WCError):
    def __init__(self, code: ErrorCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"[{code}] {detail}")


class WCBlockedError(WCError):
    def __init__(self, code: ErrorCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"[{code}] {detail}")
