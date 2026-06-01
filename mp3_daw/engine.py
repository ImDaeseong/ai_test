#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
engine.py — Suno AI 음원 처리 엔진
오디오를 '데이터(주파수 대역, LUFS, Stem)' 관점에서 처리한다.
"""

import sys
import json
import time
import shutil
import logging
import argparse
import traceback
from pathlib import Path

# ── Windows CP949 → UTF-8 강제 변환 (한글 깨짐 방지) ──
# PYTHONUTF8=1 환경변수도 설정되지만 이중 보호
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
else:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

import numpy as np

# ──────────────────────────────────────────────
# 로거 설정 (한글 로그)
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s │ %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
log = logging.getLogger("engine")

# ──────────────────────────────────────────────
# 사전 의존성 체크
# ──────────────────────────────────────────────

def check_dependencies() -> dict:
    """필수 의존성 및 외부 도구 확인."""
    result = {"ok": True, "missing": [], "warnings": []}

    # FFmpeg 체크
    if shutil.which("ffmpeg") is None:
        result["warnings"].append(
            "FFmpeg 미설치 — MP3 디코딩이 제한될 수 있습니다. "
            "https://ffmpeg.org/download.html 에서 설치 후 PATH에 추가하세요."
        )
        log.warning("⚠️  FFmpeg를 찾을 수 없습니다. MP3 처리가 제한될 수 있습니다.")
    else:
        log.info("✅ FFmpeg 확인 완료: %s", shutil.which("ffmpeg"))

    # Python 패키지 체크
    required = ["librosa", "pyloudnorm", "pedalboard", "soundfile", "demucs"]
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            result["ok"] = False
            result["missing"].append(pkg)
            log.error("❌ 패키지 누락: %s — pip install -r requirements.txt 실행 필요", pkg)

    return result


# ──────────────────────────────────────────────
# 오디오 로딩 (재시도 로직 포함)
# ──────────────────────────────────────────────

def load_audio_with_retry(file_path: str, max_retries: int = 5, delay: float = 2.0):
    """
    파일 점유 문제(다운로드 중 처리 방지) 해결을 위한 재시도 로직.
    파일 크기가 안정될 때까지 대기 후 로드한다.
    """
    import librosa

    path = Path(file_path)
    log.info("📂 파일 로드 시도: %s", path.name)

    prev_size = -1
    for attempt in range(max_retries):
        if not path.exists():
            log.warning("  [%d/%d] 파일 없음, 대기 중...", attempt + 1, max_retries)
            time.sleep(delay)
            continue

        current_size = path.stat().st_size
        if current_size == prev_size and current_size > 0:
            # 파일 크기가 안정됨 → 다운로드 완료로 판단
            break
        prev_size = current_size
        log.info("  [%d/%d] 파일 쓰기 진행 중 (크기: %d bytes), 대기...", attempt + 1, max_retries, current_size)
        time.sleep(delay)
    else:
        raise RuntimeError(f"파일 안정화 실패 (최대 재시도 초과): {file_path}")

    # 실제 로드
    y, sr = librosa.load(file_path, sr=None, mono=False)
    # mono 변환 (librosa 분석용)
    if y.ndim > 1:
        y_mono = np.mean(y, axis=0)
    else:
        y_mono = y
        y = y[np.newaxis, :]  # (1, samples)

    log.info("✅ 오디오 로드 완료 — 샘플레이트: %d Hz, 길이: %.2f 초", sr, len(y_mono) / sr)
    return y, y_mono, sr


# ──────────────────────────────────────────────
# 1. 분석: BPM / Key / 주파수 대역 / LUFS
# ──────────────────────────────────────────────

def analyze_audio(file_path: str) -> dict:
    """
    Librosa를 사용하여 BPM, Key, 정밀 주파수 대역 분석.
    결과를 JSON-직렬화 가능한 dict로 반환.
    """
    import librosa
    import pyloudnorm as pyln

    log.info("🔍 [분석 시작] %s", Path(file_path).name)
    y, y_mono, sr = load_audio_with_retry(file_path)

    # ── BPM 감지 ──
    beat_result = librosa.beat.beat_track(y=y_mono, sr=sr)
    tempo = beat_result[0] if isinstance(beat_result, (tuple, list)) else beat_result
    bpm = float(np.mean(tempo))
    log.info("  🥁 BPM: %.1f", bpm)

    # ── Key / Chroma 분석 ──
    chroma = librosa.feature.chroma_cqt(y=y_mono, sr=sr)
    chroma_mean = chroma.mean(axis=1)
    key_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    key_idx = int(np.argmax(chroma_mean))
    key = key_names[key_idx]
    log.info("  🎵 추정 키: %s", key)

    # ── FFT 주파수 대역 분석 ──
    n_fft = 2048
    D = np.abs(librosa.stft(y_mono, n_fft=n_fft))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    def band_energy(f_low, f_high):
        mask = (freqs >= f_low) & (freqs < f_high)
        if not mask.any():
            return 0.0
        return float(np.mean(D[mask, :]))

    bands = {
        "sub_bass_20_60hz":    band_energy(20, 60),
        "bass_60_250hz":       band_energy(60, 250),
        "low_mid_250_500hz":   band_energy(250, 500),
        "mid_500_2khz":        band_energy(500, 2000),
        "upper_mid_2k_4khz":   band_energy(2000, 4000),
        "presence_4k_8khz":    band_energy(4000, 8000),
        "brilliance_8k_16khz": band_energy(8000, 16000),
    }
    log.info("  📊 주파수 대역 분석 완료")

    # ── LUFS 측정 ──
    meter = pyln.Meter(sr)
    # pyloudnorm은 (samples, channels) 형식 필요
    audio_for_lufs = y.T  # (samples, channels)
    try:
        loudness = meter.integrated_loudness(audio_for_lufs)
    except Exception:
        loudness = meter.integrated_loudness(y_mono)
    log.info("  📢 통합 라우드니스: %.2f LUFS", loudness)

    # ── 파형 데이터 (다운샘플 — Wavesurfer.js용) ──
    waveform_peaks = _compute_waveform_peaks(y_mono, num_points=1000)

    result = {
        "file": str(file_path),
        "duration_sec": float(len(y_mono) / sr),
        "sample_rate": int(sr),
        "bpm": round(bpm, 2),
        "key": key,
        "lufs_integrated": round(loudness, 2),
        "frequency_bands": {k: round(v, 6) for k, v in bands.items()},
        "waveform_peaks": waveform_peaks,
        "status": "analyzed",
    }

    log.info("✅ [분석 완료] BPM=%.1f, Key=%s, LUFS=%.1f", bpm, key, loudness)
    return result


def _compute_waveform_peaks(y_mono: np.ndarray, num_points: int = 1000) -> list:
    """Wavesurfer.js 렌더링용 파형 피크 데이터 생성."""
    chunk_size = max(1, len(y_mono) // num_points)
    peaks = []
    for i in range(0, len(y_mono), chunk_size):
        chunk = y_mono[i:i + chunk_size]
        peaks.append(round(float(np.max(np.abs(chunk))), 4))
    return peaks[:num_points]


# ──────────────────────────────────────────────
# 2. Stem 분리 (Demucs)
# ──────────────────────────────────────────────

_VALID_DEMUCS_MODELS = {"htdemucs", "htdemucs_ft", "mdx", "mdx_extra"}


def separate_stems(file_path: str, output_dir: str = None, model: str = "htdemucs") -> dict:
    """
    로컬 Demucs 모델로 보컬/드럼/베이스/기타 트랙 분리.
    최초 실행 시 모델 가중치 자동 다운로드 (~1.5 GB).
    """
    import subprocess

    if model not in _VALID_DEMUCS_MODELS:
        raise ValueError(f"지원하지 않는 모델: {model}. 사용 가능: {', '.join(sorted(_VALID_DEMUCS_MODELS))}")

    log.info("🎚️  [Stem 분리 시작] 모델: %s", model)
    log.info("  ℹ️  최초 실행 시 Demucs 모델 다운로드가 필요합니다 (~1.5 GB).")

    src = Path(file_path)
    if output_dir is None:
        # 기본값: 소스 파일 옆 stems/ 가 아닌 ./output/stems/ 로 저장
        # (inbox로 돌아가 재처리되는 것 방지)
        output_dir = str(Path("./output/stems").resolve())
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "demucs.separate",
        "--name", model,
        "--out", str(out_path),
        str(src),
    ]

    log.info("  ▶ 실행: %s", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=False, text=True)

    if proc.returncode != 0:
        raise RuntimeError(f"Demucs 실패 (반환코드={proc.returncode})")

    # demucs 출력 → 한국어 접두사 파일명으로 이동
    stem_dir = out_path / model / src.stem
    stem_labels = {
        "vocals": "보컬",
        "drums":  "드럼",
        "bass":   "베이스",
        "other":  "기타",
    }
    stems = {}
    for stem_name, label in stem_labels.items():
        src_p = stem_dir / f"{stem_name}.wav"
        if src_p.exists():
            dst_p = out_path / f"{label}_{src.stem}.wav"
            shutil.move(str(src_p), str(dst_p))
            stems[stem_name] = str(dst_p)
            log.info("  ✅ %s → %s", stem_name, dst_p.name)
        else:
            log.warning("  ⚠️  %s 파일 없음", stem_name)

    # 빈 demucs 임시 디렉토리 정리
    try:
        if stem_dir.exists():
            shutil.rmtree(str(stem_dir))
        model_dir = out_path / model
        if model_dir.exists() and not any(model_dir.iterdir()):
            model_dir.rmdir()
    except Exception as e:
        log.warning("  ⚠️  임시 디렉토리 정리 실패: %s", e)

    log.info("✅ [Stem 분리 완료] 총 %d 트랙", len(stems))
    return {
        "file": str(file_path),
        "model": model,
        "stems": stems,
        "status": "separated",
    }


# ──────────────────────────────────────────────
# 3. 마스터링 (Pedalboard + pyloudnorm)
# ──────────────────────────────────────────────

def apply_mastering(file_path: str, target_lufs: float = -14.0, output_path: str = None) -> dict:
    """
    개선된 마스터링 체인:
      1. HPF 20Hz  — DC + 초저역 제거
      2. 적응형 EQ — 곡 스펙트럼 분석 후 LowShelf / HighShelf / Presence 자동 조정
      3. 글루 컴프레서 — 2:1 투명 압축 (트랜지언트 보존)
      4. M/S 스테레오 처리 — 사이드 채널 컴프레션으로 스테레오 폭 안정화
      5. pyloudnorm LUFS 정규화
      6. 브릭월 리미터 — -1.0 dBFS 천장 (스트리밍 플랫폼 기준)
    """
    import math
    import librosa
    import soundfile as sf
    import pyloudnorm as pyln
    from pedalboard import (
        Pedalboard, HighpassFilter, LowpassFilter,
        LowShelfFilter, HighShelfFilter, PeakFilter,
        Compressor, Limiter,
    )

    if not (-30.0 <= target_lufs <= 0.0):
        raise ValueError(f"target_lufs {target_lufs:.1f} 은 -30.0 ~ 0.0 범위여야 합니다")

    log.info("🎛️  [마스터링 시작] 타겟: %.1f LUFS", target_lufs)

    src = Path(file_path)
    if output_path is None:
        output_path = str(src.parent / f"마스터링_{src.stem}.wav")

    audio, sr = sf.read(str(src), always_2d=True)
    is_stereo = audio.shape[1] >= 2
    log.info("  📥 원본 로드 — %d Hz, %.2f 초, %s",
             sr, len(audio) / sr, "스테레오" if is_stereo else "모노")

    # ── 1. 사전 스펙트럼 분석 (적응형 EQ 파라미터 결정) ──
    y_mono = audio.mean(axis=1).astype(np.float32)
    n_fft = 2048
    D = np.abs(librosa.stft(y_mono, n_fft=n_fft))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    def band_energy(f_low, f_high):
        mask = (freqs >= f_low) & (freqs < f_high)
        return float(np.mean(D[mask, :])) if mask.any() else 0.0

    sub_bass_e   = band_energy(20, 60)
    bass_e       = band_energy(60, 250)
    mid_e        = band_energy(500, 2000)
    presence_e   = band_energy(4000, 8000)
    brilliance_e = band_energy(8000, 16000)

    # 저역 비율 → 과다 시 컷, 부족 시 부스트
    bass_ratio   = (sub_bass_e + bass_e) / (mid_e + 1e-9)
    low_shelf_db = -2.0 if bass_ratio > 2.5 else (1.0 if bass_ratio < 0.8 else 0.0)

    # 에어 밴드 (12 kHz 셀빙) → 고역 어두운 곡 보정
    air_ratio      = brilliance_e / (presence_e + 1e-9)
    high_shelf_db  = 1.5 if air_ratio < 0.6 else 0.0

    # 프레즌스 (3 kHz 피크) → 존재감 부족 시 부스트
    presence_ratio = presence_e / (mid_e + 1e-9)
    presence_db    = 1.0 if presence_ratio < 0.5 else 0.0

    log.info("  📊 적응형 EQ — LowShelf@80Hz: %+.1fdB  HighShelf@12kHz: %+.1fdB  Presence@3kHz: %+.1fdB",
             low_shelf_db, high_shelf_db, presence_db)

    # ── 2. EQ + 글루 컴프레서 ──
    eq_chain = [
        HighpassFilter(cutoff_frequency_hz=20.0),
        LowpassFilter(cutoff_frequency_hz=20000.0),
        LowShelfFilter(cutoff_frequency_hz=80.0, gain_db=low_shelf_db),
        HighShelfFilter(cutoff_frequency_hz=12000.0, gain_db=high_shelf_db),
    ]
    if presence_db != 0.0:
        eq_chain.append(PeakFilter(cutoff_frequency_hz=3000.0, gain_db=presence_db, q=0.8))
    eq_chain.append(
        Compressor(
            threshold_db=-16.0,  # 기존 -18 → -16 (자연스러운 글루)
            ratio=2.0,           # 기존 3:1 → 2:1 (투명한 압축)
            attack_ms=20.0,      # 기존 10ms → 20ms (트랜지언트 보존)
            release_ms=200.0,    # 기존 150ms → 200ms
        )
    )
    board = Pedalboard(eq_chain)
    processed = board(audio.T.astype(np.float32), sr).T
    log.info("  ✅ EQ + 글루 컴프레서 완료")

    # ── 3. M/S 스테레오 처리 (스테레오 전용) ──
    if is_stereo and processed.shape[1] >= 2:
        k = 1.0 / np.sqrt(2)
        mid_ch  = (processed[:, 0] + processed[:, 1]) * k
        side_ch = (processed[:, 0] - processed[:, 1]) * k

        side_board = Pedalboard([
            Compressor(threshold_db=-20.0, ratio=2.5, attack_ms=15.0, release_ms=100.0)
        ])
        side_proc = side_board(side_ch[np.newaxis, :].astype(np.float32), sr)[0]

        processed = np.column_stack([
            (mid_ch + side_proc) * k,
            (mid_ch - side_proc) * k,
        ])
        log.info("  🔀 M/S 스테레오 처리 완료")

    # ── 4. LUFS 정규화 ──
    meter = pyln.Meter(sr)
    current_lufs = meter.integrated_loudness(processed)
    if math.isinf(current_lufs):
        log.warning("  ⚠️  라우드니스 측정 불가 (무음 또는 너무 짧은 파일) — 정규화 스킵")
        normalized = processed
    else:
        log.info("  📢 %.2f LUFS → %.2f LUFS", current_lufs, target_lufs)
        normalized = pyln.normalize.loudness(processed, current_lufs, target_lufs)

    # ── 5. 브릭월 리미터 (기존 크루드 피크 클램프 대체) ──
    limiter = Pedalboard([Limiter(threshold_db=-1.0, release_ms=100.0)])
    limited = limiter(normalized.T.astype(np.float32), sr).T
    log.info("  🔒 브릭월 리미터 완료 (-1.0 dBFS)")

    # ── 6. 저장 ──
    sf.write(output_path, limited, sr, subtype="PCM_24")
    log.info("  💾 저장: %s", output_path)

    final_lufs = meter.integrated_loudness(limited)
    log.info("✅ [마스터링 완료] 최종 라우드니스: %.2f LUFS", final_lufs)

    return {
        "file": str(file_path),
        "output": output_path,
        "original_lufs": round(current_lufs, 2) if not math.isinf(current_lufs) else None,
        "final_lufs": round(final_lufs, 2),
        "target_lufs": target_lufs,
        "sample_rate": sr,
        "eq_adjustments": {
            "low_shelf_db": low_shelf_db,
            "high_shelf_db": high_shelf_db,
            "presence_db": presence_db,
        },
        "status": "mastered",
    }


# ──────────────────────────────────────────────
# CLI 엔트리포인트 (Go exec.Command 호출용)
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Suno AI 오디오 처리 엔진")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # check
    subparsers.add_parser("check", help="의존성 확인")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="오디오 분석")
    p_analyze.add_argument("file", help="오디오 파일 경로")

    # separate
    p_sep = subparsers.add_parser("separate", help="Stem 분리")
    p_sep.add_argument("file", help="오디오 파일 경로")
    p_sep.add_argument("--output", default=None, help="출력 디렉토리")
    p_sep.add_argument("--model", default="htdemucs", help="Demucs 모델명")

    # master
    p_master = subparsers.add_parser("master", help="마스터링")
    p_master.add_argument("file", help="오디오 파일 경로")
    p_master.add_argument("--lufs", type=float, default=-14.0, help="타겟 LUFS")
    p_master.add_argument("--output", default=None, help="출력 파일 경로")

    # pipeline (분석 + 마스터링 묶음)
    p_pipe = subparsers.add_parser("pipeline", help="전체 파이프라인 (분석 → 마스터링)")
    p_pipe.add_argument("file", help="오디오 파일 경로")
    p_pipe.add_argument("--lufs", type=float, default=-14.0)

    args = parser.parse_args()

    try:
        if args.command == "check":
            result = check_dependencies()

        elif args.command == "analyze":
            result = analyze_audio(args.file)

        elif args.command == "separate":
            result = separate_stems(args.file, output_dir=args.output, model=args.model)

        elif args.command == "master":
            result = apply_mastering(args.file, target_lufs=args.lufs, output_path=args.output)

        elif args.command == "pipeline":
            log.info("🚀 [파이프라인] 전체 처리 시작: %s", args.file)
            analysis = analyze_audio(args.file)
            mastering = apply_mastering(args.file, target_lufs=args.lufs)
            result = {
                "pipeline": "complete",
                "analysis": analysis,
                "mastering": mastering,
            }

        # JSON 결과 stdout 출력 (Go가 파싱)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        error = {
            "status": "error",
            "command": args.command,
            "message": str(e),
            "traceback": traceback.format_exc(),
        }
        log.error("❌ 처리 실패: %s", e)
        print(json.dumps(error, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
