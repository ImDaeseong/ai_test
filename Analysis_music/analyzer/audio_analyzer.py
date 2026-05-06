"""
Optional audio analysis using librosa.
Falls back gracefully if librosa is unavailable or no audio file provided.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import numpy as np
    import librosa
    _LIBROSA_OK = True
except ImportError:
    _LIBROSA_OK = False


@dataclass
class SectionEnergy:
    name: str
    start_sec: float
    end_sec: float
    mean_rms: float
    peak_rms: float
    energy_label: str = ""

    def __post_init__(self):
        if not self.energy_label:
            if self.mean_rms > 0.15:
                self.energy_label = "High"
            elif self.mean_rms > 0.07:
                self.energy_label = "Medium"
            else:
                self.energy_label = "Low"

    @property
    def duration(self) -> float:
        return self.end_sec - self.start_sec


@dataclass
class AudioAnalysisResult:
    available: bool = False
    file_path: str = ""
    duration: float = 0.0
    bpm: float = 0.0
    bpm_confidence: float = 0.0
    estimated_key: str = ""
    time_signature: str = "4/4"
    rms_mean: float = 0.0
    rms_std: float = 0.0
    spectral_centroid_mean: float = 0.0
    spectral_rolloff_mean: float = 0.0
    zero_crossing_rate: float = 0.0
    dynamic_range_db: float = 0.0
    section_energies: list[SectionEnergy] = field(default_factory=list)
    error: str = ""

    @property
    def duration_str(self) -> str:
        m, s = divmod(int(self.duration), 60)
        return f"{m}:{s:02d}"

    def ascii_energy_chart(self, width: int = 50) -> str:
        if not self.section_energies:
            return "(no audio data)"
        max_e = max(s.mean_rms for s in self.section_energies) or 1.0
        lines = []
        for se in self.section_energies:
            bar_len = int((se.mean_rms / max_e) * width)
            bar = "█" * bar_len + "░" * (width - bar_len)
            lines.append(
                f"{se.name:<16} [{bar}] {se.energy_label}"
            )
        return "\n".join(lines)


class AudioAnalyzer:
    def __init__(self, sr: int = 22050, hop_length: int = 512):
        self.sr = sr
        self.hop_length = hop_length

    def analyze(
        self,
        audio_path: str,
        section_names: Optional[list[str]] = None,
    ) -> AudioAnalysisResult:
        if not _LIBROSA_OK:
            return AudioAnalysisResult(
                available=False,
                error="librosa not installed — run: pip install librosa",
            )

        path = Path(audio_path)
        if not path.exists():
            return AudioAnalysisResult(
                available=False,
                error=f"Audio file not found: {audio_path}",
            )

        try:
            y, sr = librosa.load(str(path), sr=self.sr, mono=True)
        except Exception as exc:
            return AudioAnalysisResult(available=False, error=str(exc))

        result = AudioAnalysisResult(available=True, file_path=str(path))
        result.duration = librosa.get_duration(y=y, sr=sr)

        # BPM
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=self.hop_length)
        result.bpm = float(np.atleast_1d(tempo)[0])
        result.bpm_confidence = min(1.0, len(beats) / max(1, result.duration / 0.5))

        # Key estimation via chroma
        result.estimated_key = self._estimate_key(y, sr)

        # RMS energy
        rms = librosa.feature.rms(y=y, hop_length=self.hop_length)[0]
        result.rms_mean = float(np.mean(rms))
        result.rms_std = float(np.std(rms))
        result.dynamic_range_db = float(
            20 * np.log10(np.max(rms) / (np.min(rms) + 1e-9))
        )

        # Spectral features
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=self.hop_length)[0]
        result.spectral_centroid_mean = float(np.mean(centroid))

        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=self.hop_length)[0]
        result.spectral_rolloff_mean = float(np.mean(rolloff))

        zcr = librosa.feature.zero_crossing_rate(y, hop_length=self.hop_length)[0]
        result.zero_crossing_rate = float(np.mean(zcr))

        # Section energies
        result.section_energies = self._slice_sections(
            y, sr, result.duration, section_names or []
        )

        return result

    def _estimate_key(self, y, sr) -> str:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_mean = chroma.mean(axis=1)
        key_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        # Major vs minor templates (Krumhansl-Schmuckler)
        major_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
        minor_profile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

        best_score, best_key = -999.0, "C"
        for i, name in enumerate(key_names):
            rotated_chroma = np.roll(chroma_mean, -i)
            maj_score = float(np.corrcoef(rotated_chroma, major_profile)[0, 1])
            min_score = float(np.corrcoef(rotated_chroma, minor_profile)[0, 1])
            if maj_score > best_score:
                best_score, best_key = maj_score, name
            if min_score > best_score:
                best_score, best_key = min_score, name + "m"
        return best_key

    def _slice_sections(
        self,
        y,
        sr: int,
        duration: float,
        section_names: list[str],
    ) -> list[SectionEnergy]:
        if not section_names:
            # Auto-divide into 8 equal slices
            section_names = [f"Part {i+1}" for i in range(8)]

        n = len(section_names)
        slice_dur = duration / n
        result = []
        for i, name in enumerate(section_names):
            start_s = i * slice_dur
            end_s = min((i + 1) * slice_dur, duration)
            start_samp = int(start_s * sr)
            end_samp = int(end_s * sr)
            chunk = y[start_samp:end_samp]
            if len(chunk) == 0:
                continue
            rms = librosa.feature.rms(y=chunk)[0]
            result.append(
                SectionEnergy(
                    name=name,
                    start_sec=start_s,
                    end_sec=end_s,
                    mean_rms=float(rms.mean()),
                    peak_rms=float(rms.max()),
                )
            )
        return result
