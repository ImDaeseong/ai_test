"""
master_tag/tests/test_core.py
오디오 마스터링 도구의 순수 함수 단위 테스트

외부 오디오 라이브러리(pedalboard, librosa, pyloudnorm) 없이 테스트 가능한
순수 수학/유틸리티 로직만 대상으로 한다.
필요한 외부 모듈은 import 전에 sys.modules에 Mock을 주입해 격리한다.
"""

import sys
import os
import types
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# 외부 라이브러리 Mock 주입 (pedalboard, librosa, pyloudnorm)
# main.py는 module-level에서 이 세 패키지를 import하므로
# sys.modules에 stub을 삽입한 뒤 import해야 한다.
# ---------------------------------------------------------------------------

def _make_pedalboard_stub():
    pb = types.ModuleType("pedalboard")
    pb.Pedalboard = MagicMock(return_value=MagicMock(side_effect=lambda audio, sr: audio))
    for cls_name in ("Compressor", "HighpassFilter", "HighShelfFilter",
                     "Limiter", "LowShelfFilter", "PeakFilter"):
        setattr(pb, cls_name, MagicMock())
    io_mod = types.ModuleType("pedalboard.io")
    io_mod.AudioFile = MagicMock()
    pb.io = io_mod
    return pb, io_mod


_pb_stub, _pb_io_stub = _make_pedalboard_stub()
sys.modules.setdefault("pedalboard", _pb_stub)
sys.modules.setdefault("pedalboard.io", _pb_io_stub)

_librosa_stub = types.ModuleType("librosa")
_librosa_stub.load = MagicMock(return_value=(np.zeros(44100, dtype=np.float32), 44100))
_librosa_stub.get_duration = MagicMock(return_value=1.0)
sys.modules.setdefault("librosa", _librosa_stub)

_pyln_stub = types.ModuleType("pyloudnorm")
_pyln_stub.Meter = MagicMock()
_pyln_normalize = types.ModuleType("pyloudnorm.normalize")
_pyln_normalize.loudness = MagicMock(side_effect=lambda audio, measured, target: audio)
_pyln_stub.normalize = _pyln_normalize
sys.modules.setdefault("pyloudnorm", _pyln_stub)

# ---------------------------------------------------------------------------
# main.py import — stub 주입 후
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main as m  # noqa: E402


# ---------------------------------------------------------------------------
# 헬퍼 상수
# ---------------------------------------------------------------------------
SR = 44100  # 샘플레이트


# ---------------------------------------------------------------------------
# 1. compute_gain_staging — 순수 수학 함수
# ---------------------------------------------------------------------------

class TestComputeGainStaging:
    def test_zero_peak_to_target(self):
        """peak_db == target_db -> gain 1.0 (무변환)."""
        gain = m.compute_gain_staging(-6.0, target_db=-6.0)
        assert abs(gain - 1.0) < 1e-6

    def test_boost_quiet_signal(self):
        """peak_db -20 dBFS -> target -6 dBFS: +14 dB 부스트."""
        gain = m.compute_gain_staging(-20.0, target_db=-6.0)
        expected = 10 ** (14.0 / 20.0)
        assert abs(gain - expected) < 1e-4

    def test_attenuate_hot_signal(self):
        """peak_db -1 dBFS -> target -6 dBFS: -5 dB 감쇠, gain < 1."""
        gain = m.compute_gain_staging(-1.0, target_db=-6.0)
        expected = 10 ** (-5.0 / 20.0)
        assert abs(gain - expected) < 1e-4

    def test_default_target_constant(self):
        """기본 target은 TARGET_HEADROOM_DB 상수 사용 확인."""
        gain_default = m.compute_gain_staging(-12.0)
        gain_explicit = m.compute_gain_staging(-12.0, target_db=m.TARGET_HEADROOM_DB)
        assert abs(gain_default - gain_explicit) < 1e-9

    def test_return_type_is_float(self):
        """반환값이 Python float."""
        gain = m.compute_gain_staging(-6.0)
        assert isinstance(gain, float)


# ---------------------------------------------------------------------------
# 2. normalize_lufs — LUFS 정규화 로직 (pyloudnorm Mocking)
# ---------------------------------------------------------------------------

class TestNormalizeLufs:
    def _make_audio(self, channels=2, samples=SR):
        """(channels, samples) 형태의 테스트용 float32 배열."""
        rng = np.random.default_rng(42)
        return rng.uniform(-0.5, 0.5, (channels, samples)).astype(np.float32)

    def test_normal_path_returns_tuple(self):
        """정상 LUFS 반환 시 (audio_array, float) 튜플을 반환."""
        audio = self._make_audio()
        meter_instance = MagicMock()
        meter_instance.integrated_loudness.return_value = -18.0
        _pyln_stub.Meter.return_value = meter_instance

        result_audio, measured = m.normalize_lufs(audio, SR, target_lufs=-14.0)
        assert isinstance(measured, float)
        assert result_audio.dtype == np.float32

    def test_inf_lufs_triggers_peak_normalization(self):
        """LUFS 측정값이 inf -> 피크 정규화로 대체, measured=None 반환."""
        audio = self._make_audio()
        meter_instance = MagicMock()
        meter_instance.integrated_loudness.return_value = float("-inf")
        _pyln_stub.Meter.return_value = meter_instance

        result_audio, measured = m.normalize_lufs(audio, SR)
        assert measured is None

    def test_silent_audio_returns_none_lufs(self):
        """완전 묵음 배열 -> measured=None, 배열 그대로 반환."""
        audio = np.zeros((2, SR), dtype=np.float32)
        meter_instance = MagicMock()
        meter_instance.integrated_loudness.return_value = float("-inf")
        _pyln_stub.Meter.return_value = meter_instance

        result_audio, measured = m.normalize_lufs(audio, SR)
        assert measured is None
        assert result_audio.shape == audio.shape

    def test_output_shape_preserved(self):
        """정규화 후 배열 shape이 유지된다."""
        audio = self._make_audio(channels=2, samples=SR * 3)
        meter_instance = MagicMock()
        meter_instance.integrated_loudness.return_value = -20.0
        _pyln_stub.Meter.return_value = meter_instance

        result_audio, _ = m.normalize_lufs(audio, SR)
        assert result_audio.shape == audio.shape


# ---------------------------------------------------------------------------
# 3. master_audio 입력 검증 — 파일 없음 오류
# ---------------------------------------------------------------------------

class TestMasterAudioValidation:
    def test_nonexistent_file_raises(self):
        """존재하지 않는 파일 경로 -> AudioProcessingError."""
        with pytest.raises(m.AudioProcessingError, match="파일을 찾을 수 없습니다"):
            m.master_audio("/nonexistent/path/audio.mp3")

    def test_default_output_path_derivation(self, tmp_path):
        """output_path 생략 시 '_mastered.wav' 접미어가 붙은 경로가 반환될 것."""
        # _read_audio 를 mock해서 실제 파일 I/O 없이 경로 생성 로직만 검증한다.
        dummy_audio = np.ones((2, SR), dtype=np.float32) * 0.3
        fake_input = str(tmp_path / "song.mp3")
        # 실제 파일이 없으면 os.path.isfile 체크에서 걸리므로 빈 파일 생성
        open(fake_input, "wb").close()

        with patch.object(m, "_read_audio", return_value=(dummy_audio, SR)), \
             patch.object(m, "build_dsp_chain") as mock_dsp, \
             patch.object(m, "normalize_lufs", return_value=(dummy_audio, -18.0)), \
             patch.object(m, "build_final_limiter") as mock_lim, \
             patch.object(m, "_write_audio"):
            mock_dsp.return_value.return_value = dummy_audio
            mock_lim.return_value.return_value = dummy_audio

            out = m.master_audio(fake_input)

        assert out.endswith("_mastered.wav")
        assert "song" in os.path.basename(out)


# ---------------------------------------------------------------------------
# 4. _emit — on_progress 콜백 유틸리티
# ---------------------------------------------------------------------------

class TestEmitHelper:
    def test_emit_calls_callback(self):
        """on_progress가 None이 아니면 이벤트 dict와 함께 호출된다."""
        received = []
        m._emit(received.append, {"type": "step", "step": 1})
        assert len(received) == 1
        assert received[0]["type"] == "step"

    def test_emit_none_callback_no_error(self):
        """on_progress=None 이면 조용히 아무것도 하지 않는다."""
        m._emit(None, {"type": "done"})  # 예외 없음

    def test_emit_multiple_events(self):
        """여러 이벤트를 순서대로 수신한다."""
        log = []
        events = [{"type": "step", "step": i} for i in range(5)]
        for ev in events:
            m._emit(log.append, ev)
        assert [e["step"] for e in log] == list(range(5))


# ---------------------------------------------------------------------------
# 5. 모듈 상수 존재 확인
# ---------------------------------------------------------------------------

class TestModuleConstants:
    def test_target_headroom_db(self):
        assert m.TARGET_HEADROOM_DB == -6.0

    def test_target_lufs(self):
        assert m.TARGET_LUFS == -14.0

    def test_limiter_threshold_db(self):
        assert m.LIMITER_THRESHOLD_DB == -1.0

    def test_silence_peak_threshold_positive(self):
        assert m.SILENCE_PEAK_THRESHOLD > 0
