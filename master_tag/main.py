# =============================================================================
# Suno AI 전용 로컬 자동 마스터링 프로세서
# 대상 환경: Windows 10/11, CPU 실행, 외부 API 사용 없음
# 사용 라이브러리: Pedalboard, Librosa, Pyloudnorm
# =============================================================================

import sys
import os
import numpy as np

# ---------------------------------------------------------------------------
# 라이브러리 임포트 (미설치 시 친절한 안내)
# ---------------------------------------------------------------------------
try:
    from pedalboard import (
        Pedalboard,
        HighpassFilter,
        LowShelfFilter,
        HighShelfFilter,
        PeakFilter,
        Compressor,
        Limiter,
    )
    from pedalboard.io import AudioFile
except ImportError:
    print("[오류] pedalboard 라이브러리가 설치되지 않았습니다.")
    print("       실행: pip install pedalboard>=0.9.0")
    sys.exit(1)

try:
    import librosa
except ImportError:
    print("[오류] librosa 라이브러리가 설치되지 않았습니다.")
    print("       실행: pip install librosa>=0.10.0")
    sys.exit(1)

try:
    import pyloudnorm as pyln
except ImportError:
    print("[오류] pyloudnorm 라이브러리가 설치되지 않았습니다.")
    print("       실행: pip install pyloudnorm>=0.1.1")
    sys.exit(1)


# =============================================================================
# 1단계: 오디오 분석
# =============================================================================

def analyze_audio(file_path: str) -> dict:
    """
    Librosa를 사용하여 오디오의 주파수 응답 및 레벨을 분석합니다.
    반환값: { 'peak_db', 'rms_db', 'sample_rate', 'duration' }
    """
    print("\n[1/4] 분석 중... (FFT, Peak/RMS 측정)")

    # librosa로 로드 (스테레오 유지, 원본 샘플레이트 사용)
    audio_mono, sr = librosa.load(file_path, sr=None, mono=True)

    # Peak 레벨 (dBFS)
    peak = np.max(np.abs(audio_mono))
    peak_db = 20 * np.log10(peak + 1e-9)

    # RMS 레벨 (dBFS)
    rms = np.sqrt(np.mean(audio_mono ** 2))
    rms_db = 20 * np.log10(rms + 1e-9)

    # 재생 길이 (초)
    duration = librosa.get_duration(y=audio_mono, sr=sr)

    print(f"    └ 샘플레이트  : {sr} Hz")
    print(f"    └ 재생 시간   : {duration:.1f}초")
    print(f"    └ Peak 레벨  : {peak_db:.1f} dBFS")
    print(f"    └ RMS 레벨   : {rms_db:.1f} dBFS")

    return {
        "peak_db": peak_db,
        "rms_db": rms_db,
        "sample_rate": sr,
        "duration": duration,
    }


# =============================================================================
# 2단계: Gain Staging (헤드룸 확보)
# =============================================================================

def compute_gain_staging(peak_db: float, target_db: float = -6.0) -> float:
    """
    Peak 레벨을 target_db(기본 -6dBFS)로 맞추는 선형 게인(배율)을 계산합니다.
    DSP 체인 앞단에서 헤드룸을 확보하여 클리핑을 방지합니다.
    """
    gain_db = target_db - peak_db
    gain_linear = 10 ** (gain_db / 20.0)
    print(f"\n[Gain Staging] Peak {peak_db:.1f} dBFS → 목표 {target_db:.1f} dBFS")
    print(f"    └ 적용 게인  : {gain_db:+.1f} dB (선형 배율: {gain_linear:.4f})")
    return gain_linear


# =============================================================================
# 3단계: DSP 체인 구성 (Pedalboard)
# =============================================================================

def build_dsp_chain() -> Pedalboard:
    """
    Suno AI 음원 특성에 최적화된 DSP 이펙트 체인을 반환합니다.

    Suno AI 주요 결함:
      - 고음역대(8kHz~16kHz) 에너지 손실 → 평탄하고 답답한 음색
      - 저음역대(60~120Hz) 빈약함 → 무게감·펀치감 부족
      - 중역대(250~500Hz) 혼탁함 → 보컬·악기 분리도 저하
    """

    board = Pedalboard([

        # ------------------------------------------------------------------
        # [HPF] 초저역 노이즈 제거
        # 30Hz 이하의 초저역 DC 오프셋 및 마이크 럼블(rumble)을 제거합니다.
        # Suno AI 인코딩 과정에서 발생하는 서브베이스 노이즈 정리.
        # ------------------------------------------------------------------
        HighpassFilter(
            cutoff_frequency_hz=30.0  # 컷오프: 30Hz (변경 범위: 20~60Hz)
        ),

        # ------------------------------------------------------------------
        # [EQ-1] 저역 보강 (Low Shelf)
        # Suno AI의 빈약한 저음역(100Hz 이하)에 무게감을 추가합니다.
        # 과도하게 올리면 부밍(booming)이 발생하므로 +3dB 이내 권장.
        # ------------------------------------------------------------------
        LowShelfFilter(
            cutoff_frequency_hz=100.0,  # 셸프 주파수: 100Hz (변경 범위: 80~120Hz)
            gain_db=3.0,                # 부스트량: +3dB (변경 범위: +1~+5dB)
            q=0.7,                      # Q값: 0.7 (낮을수록 넓은 대역에 영향)
        ),

        # ------------------------------------------------------------------
        # [EQ-2] 중저역 정리 (Parametric Peak - Cut)
        # 250~500Hz 대역은 Suno AI에서 과도하게 쌓여 답답함을 유발합니다.
        # -2~-4dB 컷으로 보컬과 기타 분리도를 향상시킵니다.
        # ------------------------------------------------------------------
        PeakFilter(
            cutoff_frequency_hz=350.0,  # 컷 중심 주파수: 350Hz (변경 범위: 250~500Hz)
            gain_db=-3.0,               # 컷량: -3dB (변경 범위: -2~-6dB)
            q=1.2,                      # Q값: 1.2 (높을수록 좁은 대역만 영향)
        ),

        # ------------------------------------------------------------------
        # [EQ-3] 존재감 부스트 (Parametric Peak - Boost)
        # 3kHz 대역을 살짝 올려 보컬과 스네어의 존재감(presence)을 강화합니다.
        # Suno AI 음원이 묻히는 느낌을 해소합니다.
        # ------------------------------------------------------------------
        PeakFilter(
            cutoff_frequency_hz=3000.0,  # 부스트 중심: 3kHz (변경 범위: 2k~5kHz)
            gain_db=1.5,                 # 부스트량: +1.5dB (변경 범위: +1~+3dB)
            q=1.5,                       # Q값: 1.5 (중간 밴드폭)
        ),

        # ------------------------------------------------------------------
        # [EQ-4] 고역 샤프니스 보정 (High Shelf)
        # Suno AI의 최대 약점: 10kHz 이상의 에어(air) 대역 손실.
        # High Shelf로 공기감과 선명함(brilliance)을 복원합니다.
        # +4dB 초과 시 치찰음(sibilance) 증가 주의.
        # ------------------------------------------------------------------
        HighShelfFilter(
            cutoff_frequency_hz=10000.0,  # 셸프 시작: 10kHz (변경 범위: 8k~12kHz)
            gain_db=4.0,                  # 부스트량: +4dB (변경 범위: +2~+6dB)
            q=0.7,                        # Q값: 0.7
        ),

        # ------------------------------------------------------------------
        # [Compressor] 다이나믹 밀도 강화
        # 소리의 밀도와 레이어링을 높여 "꽉 찬" 음감을 만듭니다.
        # Suno AI 특성상 다이나믹 범위가 넓어 부분적으로 빈약하게 들립니다.
        # ------------------------------------------------------------------
        Compressor(
            threshold_db=-18.0,  # 압축 시작 임계값: -18dBFS (변경 범위: -24~-12dB)
            ratio=3.0,           # 압축 비율: 3:1 (변경 범위: 2:1~6:1)
            attack_ms=10.0,      # 어택 타임: 10ms (빠를수록 트랜지언트 억제)
            release_ms=150.0,    # 릴리즈 타임: 150ms (변경 범위: 100~300ms)
        ),

        # ------------------------------------------------------------------
        # [Limiter] 피크 방지 및 음압 최대화
        # DSP 체인 마지막 단에서 클리핑을 막고 최종 음압을 확보합니다.
        # threshold_db는 true peak 기준이며 -1.0dBTP가 스트리밍 표준입니다.
        # ------------------------------------------------------------------
        Limiter(
            threshold_db=-1.0,   # 리미팅 임계값: -1.0dBTP (스트리밍 표준)
            release_ms=100.0,    # 릴리즈 타임: 100ms
        ),
    ])

    return board


# =============================================================================
# 4단계: LUFS 정규화
# =============================================================================

def normalize_lufs(
    audio: np.ndarray,
    sample_rate: int,
    target_lufs: float = -14.0
) -> np.ndarray:
    """
    Pyloudnorm으로 통합 라우드니스를 측정하고 -14 LUFS(유튜브 표준)로 정규화합니다.
    오디오 배열은 (samples, channels) 형태여야 합니다.
    """
    print(f"\n[3/4] LUFS 정규화 중... (목표: {target_lufs} LUFS, 유튜브/스포티파이 표준)")

    meter = pyln.Meter(sample_rate)  # ITU-R BS.1770-4 기반 미터

    # pyloudnorm은 (samples, channels) 형태를 요구
    audio_t = audio.T  # (channels, samples) → (samples, channels)

    measured_lufs = meter.integrated_loudness(audio_t)
    print(f"    └ 측정 LUFS  : {measured_lufs:.1f} LUFS")

    if np.isinf(measured_lufs) or np.isnan(measured_lufs):
        print("    └ [경고] LUFS 측정 실패 (무음 또는 너무 짧은 파일). 정규화 건너뜁니다.")
        return audio

    normalized = pyln.normalize.loudness(audio_t, measured_lufs, target_lufs)
    print(f"    └ 보정 후    : {target_lufs:.1f} LUFS")

    return normalized.T  # (samples, channels) → (channels, samples)


# =============================================================================
# 메인 파이프라인
# =============================================================================

def master_audio(input_path: str, output_path: str = None, on_progress=None) -> str:
    """
    Suno AI 음원 마스터링 풀 파이프라인을 실행하고 출력 파일 경로를 반환합니다.
    파이프라인: 분석 → Gain Staging → DSP 체인 → LUFS 정규화 → 저장

    Args:
        input_path:  입력 오디오 파일 경로
        output_path: 출력 파일 경로 (None이면 {원본}_mastered.wav)
        on_progress: 진행 이벤트 콜백 fn(event: dict) — Web UI 연동용
    """

    def emit(event: dict):
        """콜백이 있으면 이벤트를 전달하고, 없으면 콘솔에 출력합니다."""
        if on_progress:
            on_progress(event)

    # ------------------------------------------------------------------
    # 파일 존재 확인
    # ------------------------------------------------------------------
    if not os.path.isfile(input_path):
        msg = f"파일을 찾을 수 없습니다: {input_path}"
        emit({"type": "error", "message": msg})
        print(f"[오류] {msg}")
        sys.exit(1)

    # 출력 파일명 생성
    if output_path is None:
        base, _ = os.path.splitext(input_path)
        output_path = base + "_mastered.wav"

    print("=" * 60)
    print("  Suno AI 전용 자동 마스터링 프로세서")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1단계: 오디오 분석
    # ------------------------------------------------------------------
    emit({"type": "step", "step": 1, "label": "오디오 분석", "detail": "FFT, Peak/RMS 측정 중..."})
    print("\n[1/4] 분석 중...")

    audio_mono, _ = librosa.load(input_path, sr=None, mono=True)
    sr_mono = librosa.get_samplerate(input_path)
    peak = np.max(np.abs(audio_mono))
    peak_db = float(20 * np.log10(peak + 1e-9))
    rms = np.sqrt(np.mean(audio_mono ** 2))
    rms_db = float(20 * np.log10(rms + 1e-9))
    duration = float(librosa.get_duration(y=audio_mono, sr=sr_mono))

    emit({"type": "analysis", "peak_db": round(peak_db, 1), "rms_db": round(rms_db, 1),
          "duration": round(duration, 1), "sample_rate": sr_mono})
    print(f"    └ Peak: {peak_db:.1f} dBFS  RMS: {rms_db:.1f} dBFS  {duration:.1f}s")

    # ------------------------------------------------------------------
    # 2단계: Gain Staging
    # ------------------------------------------------------------------
    gain_linear = compute_gain_staging(peak_db, target_db=-6.0)
    emit({"type": "step", "step": 2, "label": "Gain Staging",
          "detail": f"Peak {peak_db:.1f} → -6.0 dBFS (헤드룸 확보)"})

    # ------------------------------------------------------------------
    # 3단계: DSP 체인 적용
    # ------------------------------------------------------------------
    emit({"type": "step", "step": 3, "label": "DSP 체인 적용",
          "detail": "HPF → EQ × 4 → Compressor → Limiter"})
    print("\n[2/4] 이펙트 적용 중...")
    board = build_dsp_chain()

    with AudioFile(input_path) as f:
        sample_rate = f.samplerate
        audio = f.read(f.frames)

    audio = audio * gain_linear
    audio = board(audio, sample_rate)

    # ------------------------------------------------------------------
    # 4단계: LUFS 정규화
    # ------------------------------------------------------------------
    emit({"type": "step", "step": 4, "label": "LUFS 정규화",
          "detail": "목표: -14 LUFS (YouTube / Spotify 표준)"})
    print("\n[3/4] LUFS 정규화 중...")

    meter = pyln.Meter(sample_rate)
    audio_t = audio.T
    measured_lufs = meter.integrated_loudness(audio_t)

    if not (np.isinf(measured_lufs) or np.isnan(measured_lufs)):
        audio_t = pyln.normalize.loudness(audio_t, measured_lufs, -14.0)
        audio = audio_t.T
        emit({"type": "lufs", "before": round(float(measured_lufs), 1), "after": -14.0})
        print(f"    └ {measured_lufs:.1f} LUFS → -14.0 LUFS")
    else:
        emit({"type": "lufs", "before": None, "after": None})
        print("    └ [경고] LUFS 측정 실패. 건너뜁니다.")

    # ------------------------------------------------------------------
    # 저장
    # ------------------------------------------------------------------
    print("\n[4/4] 저장 중...")
    with AudioFile(output_path, "w", samplerate=sample_rate, num_channels=audio.shape[0]) as f:
        f.write(audio.astype(np.float32))

    emit({"type": "done", "output_path": output_path,
          "filename": os.path.basename(output_path)})
    print(f"\n[완료] {output_path}")
    print("=" * 60)

    return output_path


# =============================================================================
# CLI 진입점
# =============================================================================

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        input_file = sys.argv[1].strip('"').strip("'")
    else:
        print("Suno AI 자동 마스터링 프로세서")
        print("마스터링할 오디오 파일 경로를 입력하세요.")
        input_file = input("파일 경로 > ").strip('"').strip("'")

    master_audio(input_file)
