"""Importing helpers must not initialize application logging or close stdout."""
import os
from pathlib import Path
import subprocess
import sys


def test_import_and_logging_startup_are_separate(tmp_path):
    root = Path(__file__).resolve().parents[1]
    code = """
import sys
from pathlib import Path
stdout = sys.stdout
import main
assert sys.stdout is stdout and not stdout.closed
assert not Path('logs').exists()
main.configure_logging()
assert sys.stdout is stdout and not stdout.closed
main.logger.info('startup probe')
main.logger.remove()
assert 'startup probe' in Path('logs/weather_alarm.log').read_text(encoding='utf-8')
print('STARTUP_PASS')
"""
    result = subprocess.run(
        [sys.executable, '-B', '-c', code], cwd=tmp_path,
        env={**os.environ, 'PYTHONPATH': str(root)},
        capture_output=True, text=True, encoding='utf-8', timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert 'STARTUP_PASS' in result.stdout
