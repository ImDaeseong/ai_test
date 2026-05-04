# =============================================================================
# Suno AI 전용 로컬 자동 마스터링 프로세서
# 대상 환경: Windows 10/11, CPU 실행, 외부 API 사용 없음
# 사용 라이브러리: Pedalboard, Librosa, Pyloudnorm
# =============================================================================

import os
import sys
from typing import Callable, Optional

import numpy as np

try:
    from pedalboard import (
        Compressor,
        HighpassFilter,
        HighShelfFilter,
        Limiter,
        LowShelfFilter,
        PeakFilter,
        Pedalboard,
    )
    from pedalboard.io import AudioFile
except ImportError as exc:
    raise RuntimeError(
        "pedalboard 라이브러리가 설치되지 않았습니다. 실행: pip install pedalboard>=0.9.0"
    ) from exc

try:
    import librosa
except ImportError as exc:
    raise RuntimeError(
        "librosa 라이브러리가 설치되지 않았습니다. 실행: pip install librosa>=0.10.0"
    ) from exc

try:
    import pyloudnorm as pyln
except ImportError as exc:
    raise RuntimeError(
        "pyloudnorm 라이브러리가 설치되지 않았습니다. 실행: pip install pyloudnorm>=0.1.1"
    ) from exc


ProgressCallback = Optional[Callable[[dict], None]]

TARGET_HEADROOM_DB = -6.0
TARGET_LUFS = -14.0
LIMITER_THRESHOLD_DB = -1.0
SILENCE_PEAK_THRESHOLD = 1e-5


class AudioProcessingError(RuntimeError):
    """오디오 처리 과정에서 사용자에게 전달할 수 있는 오류입니다."""


def _emit(on_progress: ProgressCallback, event: dict) -> None:
    if on_progress:
        on_progress(event)


def _load_mono_for_analysis(file_path: str) -> tuple[np.ndarray, int]:
    try:
        audio_mono, sr = librosa.load(file_path, sr=None, mono=True)
    except Exception as exc:
        raise AudioProcessingError(f"오디오 파일을 읽을 수 없습니다: {exc}") from exc

    if audio_mono.size == 0:
        raise AudioProcessingError("오디오 데이터가 비어 있습니다.")

    return audio_mono, sr


def analyze_audio(file_path: str) -> dict:
    """
    Librosa를 사용하여 오디오 레벨과 길이를 분석합니다.
    반환값: {'peak_db', 'rms_db', 'sample_rate', 'duration', 'peak_linear'}
    """
    audio_mono, sr = _load_mono_for_analysis(file_path)

    peak = float(np.max(np.abs(audio_mono)))
    rms = float(np.sqrt(np.mean(audio_mono**2)))
    peak_db = float(20 * np.log10(peak + 1e-9))
    rms_db = float(20 * np.log10(rms + 1e-9))
    duration = float(librosa.get_duration(y=audio_mono, sr=sr))

    return {
        "peak_db": peak_db,
        "rms_db": rms_db,
        "sample_rate": sr,
        "duration": duration,
        "peak_linear": peak,
    }


def compute_gain_staging(peak_db: float, target_db: float = TARGET_HEADROOM_DB) -> float:
    """Peak 레벨을 target_db로 맞추는 선형 게인 배율을 계산합니다."""
    gain_db = target_db - peak_db
    gain_linear = 10 ** (gain_db / 20.0)
    print(f"\n[Gain Staging] Peak {peak_db:.1f} dBFS -> 목표 {target_db:.1f} dBFS")
    print(f"    적용 게인: {gain_db:+.1f} dB (선형 배율: {gain_linear:.4f})")
    return gain_linear


def build_dsp_chain() -> Pedalboard:
    """최종 리미터 전까지의 EQ/컴프레서 체인을 반환합니다."""
    return Pedalboard(
        [
            HighpassFilter(cutoff_frequency_hz=30.0),
            LowShelfFilter(cutoff_frequency_hz=100.0, gain_db=3.0, q=0.7),
            PeakFilter(cutoff_frequency_hz=350.0, gain_db=-3.0, q=1.2),
            PeakFilter(cutoff_frequency_hz=3000.0, gain_db=1.5, q=1.5),
            HighShelfFilter(cutoff_frequency_hz=10000.0, gain_db=4.0, q=0.7),
            Compressor(
                threshold_db=-18.0,
                ratio=3.0,
                attack_ms=10.0,
                release_ms=150.0,
            ),
        ]
    )


def build_final_limiter() -> Pedalboard:
    """LUFS 정규화 이후 최종 피크를 보호하는 리미터입니다."""
    return Pedalboard(
        [
            Limiter(
                threshold_db=LIMITER_THRESHOLD_DB,
                release_ms=100.0,
            )
        ]
    )


def normalize_lufs(
    audio: np.ndarray,
    sample_rate: int,
    target_lufs: float = TARGET_LUFS,
) -> tuple[np.ndarray, Optional[float]]:
    """
    Pyloudnorm으로 통합 라우드니스를 측정하고 target_lufs로 정규화합니다.
    입력/출력 배열은 Pedalboard 형식인 (channels, samples)입니다.
    """
    meter = pyln.Meter(sample_rate)
    audio_t = audio.T

    try:
        measured_lufs = float(meter.integrated_loudness(audio_t))
    except Exception as exc:
        raise AudioProcessingError(f"LUFS 측정 중 오류가 발생했습니다: {exc}") from exc

    if np.isinf(measured_lufs) or np.isnan(measured_lufs):
        print("    [경고] LUFS 측정 실패. 정규화를 건너뜁니다.")
        return audio, None

    normalized = pyln.normalize.loudness(audio_t, measured_lufs, target_lufs)
    return normalized.T.astype(np.float32, copy=False), measured_lufs


def _read_audio(file_path: str) -> tuple[np.ndarray, int]:
    try:
        with AudioFile(file_path) as f:
            audio = f.read(f.frames)
            sample_rate = int(f.samplerate)
    except Exception as exc:
        raise AudioProcessingError(f"오디오 파일을 디코딩할 수 없습니다: {exc}") from exc

    if audio.size == 0:
        raise AudioProcessingError("오디오 데이터가 비어 있습니다.")

    if audio.ndim == 1:
        audio = audio.reshape(1, -1)

    return audio.astype(np.float32, copy=False), sample_rate


def _write_audio(output_path: str, audio: np.ndarray, sample_rate: int) -> None:
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    try:
        with AudioFile(
            output_path,
            "w",
            samplerate=sample_rate,
            num_channels=int(audio.shape[0]),
        ) as f:
            f.write(audio.astype(np.float32, copy=False))
    except Exception as exc:
        raise AudioProcessingError(f"출력 파일을 저장할 수 없습니다: {exc}") from exc


def master_audio(
    input_path: str,
    output_path: Optional[str] = None,
    on_progress: ProgressCallback = None,
) -> str:
    """
    Suno AI 음원 마스터링 파이프라인을 실행하고 출력 파일 경로를 반환합니다.
    파이프라인: 분석 -> Gain Staging -> EQ/Compressor -> LUFS 정규화 -> Limiter -> 저장
    """
    if not os.path.isfile(input_path):
        raise AudioProcessingError(f"파일을 찾을 수 없습니다: {input_path}")

    if output_path is None:
        base, _ = os.path.splitext(input_path)
        output_path = base + "_mastered.wav"

    print("=" * 60)
    print("  Suno AI 전용 자동 마스터링 프로세서")
    print("=" * 60)

    _emit(
        on_progress,
        {"type": "step", "step": 1, "label": "오디오 분석", "detail": "Peak/RMS 측정 중..."},
    )
    print("\n[1/5] 분석 중...")

    # 파일을 한 번만 로딩하고 분석 수치를 직접 계산 (librosa 중복 로딩 제거)
    audio, sample_rate = _read_audio(input_path)
    audio_mono = audio.mean(axis=0) if audio.shape[0] > 1 else audio[0]
    peak = float(np.max(np.abs(audio_mono)))
    rms = float(np.sqrt(np.mean(audio_mono ** 2)))
    peak_db = float(20 * np.log10(peak + 1e-9))
    rms_db = float(20 * np.log10(rms + 1e-9))
    duration = float(audio_mono.size / sample_rate)

    _emit(
        on_progress,
        {
            "type": "analysis",
            "peak_db": round(peak_db, 1),
            "rms_db": round(rms_db, 1),
            "duration": round(duration, 1),
            "sample_rate": sample_rate,
        },
    )
    print(
        f"    Peak: {peak_db:.1f} dBFS  "
        f"RMS: {rms_db:.1f} dBFS  "
        f"{duration:.1f}s"
    )

    if peak < SILENCE_PEAK_THRESHOLD:
        raise AudioProcessingError("무음 또는 너무 작은 레벨의 파일은 마스터링할 수 없습니다.")

    _emit(
        on_progress,
        {
            "type": "step",
            "step": 2,
            "label": "Gain Staging",
            "detail": f"Peak {peak_db:.1f} -> {TARGET_HEADROOM_DB:.1f} dBFS",
        },
    )
    gain_linear = compute_gain_staging(peak_db, TARGET_HEADROOM_DB)

    _emit(
        on_progress,
        {
            "type": "step",
            "step": 3,
            "label": "DSP 체인 적용",
            "detail": "HPF, EQ, Compressor 적용 중...",
        },
    )
    print("\n[2/5] 이펙트 적용 중...")
    audio = audio * gain_linear
    audio = build_dsp_chain()(audio, sample_rate)

    _emit(
        on_progress,
        {
            "type": "step",
            "step": 4,
            "label": "LUFS 정규화",
            "detail": f"목표: {TARGET_LUFS:.1f} LUFS",
        },
    )
    print("\n[3/5] LUFS 정규화 중...")
    audio, measured_lufs = normalize_lufs(audio, sample_rate, TARGET_LUFS)
    if measured_lufs is None:
        _emit(on_progress, {"type": "lufs", "before": None, "after": None})
    else:
        _emit(
            on_progress,
            {
                "type": "lufs",
                "before": round(measured_lufs, 1),
                "after": TARGET_LUFS,
            },
        )
        print(f"    {measured_lufs:.1f} LUFS -> {TARGET_LUFS:.1f} LUFS")

    _emit(
        on_progress,
        {
            "type": "step",
            "step": 5,
            "label": "최종 리미터",
            "detail": f"피크 보호: {LIMITER_THRESHOLD_DB:.1f} dB",
        },
    )
    print("\n[4/5] 최종 리미터 적용 중...")
    audio = build_final_limiter()(audio, sample_rate)
    audio = np.clip(audio, -1.0, 1.0).astype(np.float32, copy=False)

    print("\n[5/5] 저장 중...")
    _write_audio(output_path, audio, sample_rate)

    _emit(
        on_progress,
        {
            "type": "done",
            "output_path": output_path,
            "filename": os.path.basename(output_path),
        },
    )
    print(f"\n[완료] {output_path}")
    print("=" * 60)

    return output_path


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        input_file = sys.argv[1].strip('"').strip("'")
    else:
        print("Suno AI 자동 마스터링 프로세서")
        print("마스터링할 오디오 파일 경로를 입력하세요.")
        input_file = input("파일 경로 > ").strip('"').strip("'")

    try:
        master_audio(input_file)
    except AudioProcessingError as exc:
        print(f"[오류] {exc}")
        sys.exit(1)
