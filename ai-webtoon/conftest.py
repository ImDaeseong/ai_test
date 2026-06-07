"""
Windows pytest 실행 시 한글 출력 깨짐 방지를 위해 stdout/stderr 인코딩을 UTF-8로 고정한다.
"""
import sys

if sys.platform == "win32":
    for _stream in ("stdout", "stderr"):
        _s = getattr(sys, _stream, None)
        if hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
