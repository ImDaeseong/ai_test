from __future__ import annotations

import io
from contextlib import redirect_stdout
from unittest.mock import patch

from scripts import check_source_only


def _run_with_index(*paths: str) -> tuple[int, str]:
    encoded = b"\0".join(path.encode("utf-8") for path in paths) + b"\0"
    output = io.StringIO()
    with patch("scripts.check_source_only.subprocess.check_output", return_value=encoded):
        with redirect_stdout(output):
            result = check_source_only.main()
    return result, output.getvalue()


def test_rejects_tracked_runtime_input_with_specific_diagnostic():
    result, output = _run_with_index("ai-webtoon/input/private-song.txt")

    assert result == 1
    assert "[TRACKED-LOCAL-DATA] 1 runtime input/output files remain tracked" in output


def test_rejects_tracked_generated_output_with_specific_diagnostic():
    result, output = _run_with_index("ai-webtoon/output/song/panels/panel.md")

    assert result == 1
    assert "[TRACKED-LOCAL-DATA] 1 runtime input/output files remain tracked" in output


def test_allows_directory_markers_and_source_files():
    result, output = _run_with_index(
        "ai-webtoon/input/.gitkeep",
        "ai-webtoon/output/.gitkeep",
        "ai-webtoon/app.py",
    )

    assert result == 0
    assert "[SOURCE-ONLY] PASS" in output
