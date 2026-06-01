"""
Generates report.md combining prompt analysis + optional audio analysis.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import OUTPUT_DIR
from analyzer.suno_parser import SunoPromptData
from analyzer.audio_analyzer import AudioAnalysisResult


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


class ReportGenerator:
    def generate(
        self,
        data: SunoPromptData,
        audio: Optional[AudioAnalysisResult] = None,
        out_dir: Path = OUTPUT_DIR,
    ) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        improvement = self._dynamic_advice(data)
        md = self._build_markdown(data, audio, improvement)
        out_path = out_dir / "report.md"
        out_path.write_text(md, encoding="utf-8")
        return out_path

    @staticmethod
    def _modulation_hint(key: str) -> str:
        """조성에 맞는 전조 제안 (항상 +1 semitone 고정이 아닌 조성별 동적 생성)."""
        chromatic = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        flat_map = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}
        is_minor = key.endswith("m")
        root = key[:-1] if is_minor else key
        root_s = flat_map.get(root, root)
        try:
            idx = chromatic.index(root_s)
        except ValueError:
            idx = 0
        up = chromatic[(idx + 1) % 12]
        if is_minor:
            rel_maj = chromatic[(idx + 3) % 12]
            return (f"- 마지막 코러스: {key} → {up}m (반음 상행) "
                    f"또는 {rel_maj} (나란한 장조) 전조")
        return (f"- 마지막 코러스: {key} → {up} (반음 상행) "
                f"또는 {key}m (동명 단조) 전조")

    @staticmethod
    def _genre_advice(data: SunoPromptData) -> tuple[list[str], str, list[str]]:
        """장르/스타일 태그 점수 기반으로 (개선항목, add_tags, 음악적권고) 반환.
        단일 if/elif 체인이 아닌 점수 집계 방식 → 하이브리드 장르도 정확히 분류."""
        tags = " ".join(data.genre + data.instruments + data.mood + data.vocal_style).lower()
        mod = ReportGenerator._modulation_hint(data.key)

        def score(*kws: str) -> int:
            return sum(1 for kw in kws if kw in tags)

        scores = {
            "trap":      score("trap", "drill", "808", "phonk", "dark trap",
                               "uk drill", "ny drill"),
            "hiphop":    score("hip hop", "hiphop", "rap", "boom bap", "boombap",
                               "grime", "mc", "freestyle"),
            "edm":       score("edm", "electronic", "techno", "house", "dance",
                               "rave", "trance", "dubstep", "future bass", "dnb",
                               "drum and bass", "footwork", "juke", "uk garage"),
            "synthwave": score("synthwave", "retrowave", "outrun", "vaporwave",
                               "chillwave", "dreamwave", "electropop"),
            "jazz":      score("jazz", "swing", "blues", "bossa", "bebop",
                               "soul", "funk", "cool jazz", "big band"),
            "rock":      score("rock", "punk", "hardcore", "grunge",
                               "alternative", "shoegaze", "prog rock", "post-rock"),
            "metal":     score("metal", "heavy metal", "thrash", "death metal",
                               "metalcore", "djent", "prog metal", "power metal"),
            "rnb":       score("r&b", "rnb", "neo soul", "groove", "motown",
                               "new jack swing", "trap soul"),
            "ballad":    score("ballad", "slow", "acoustic", "gentle", "lo-fi",
                               "lofi", "ambient", "chill", "chillwave", "chillhop"),
            "folk":      score("folk", "country", "bluegrass", "singer-songwriter",
                               "americana", "celtic", "acoustic folk"),
            "classical": score("classical", "orchestral", "baroque", "cinematic",
                               "film score", "opera", "symphonic"),
            "afrobeats": score("afrobeats", "afropop", "afrobeat", "afro",
                               "reggaeton", "dancehall", "reggae", "caribbean"),
            "kpop":      score("k-pop", "kpop", "idol", "k pop"),
        }

        best = max(scores, key=lambda k: scores[k])
        if scores[best] == 0:
            best = "default"

        if best == "trap":
            return (
                ["- 808 베이스와 멜로디 음역 레이어링 최적화",
                 "- 트랩 하이햇 패턴에 오픈/클로즈 변화 추가"],
                "808 Sub Bass Layer, Trap Hi-Hat Roll, Beat Switch",
                ["- 비트 스위치 포인트에서 16분음표 하이햇 패턴 변화",
                 "- 드랍 전 1박 공백으로 임팩트 강화",
                 mod],
            )
        if best == "hiphop":
            return (
                ["- 훅과 버스 사이 에너지 대비 강화",
                 "- 라임 스킴과 멜로디 보이싱 연동 강화"],
                "Boom Bap Groove, Vinyl Texture, Ad-lib Layer",
                ["- 훅 진입 전 1박 공백으로 임팩트 극대화",
                 "- 코드 샘플에 sus2 / maj7 보이싱 활용",
                 mod],
            )
        if best == "edm":
            return (
                ["- 빌드업 구간 긴장감 곡선 최적화",
                 "- 드랍 직전 서브 베이스 사이드체인 강화"],
                "Build-Up Tension, Filter Sweep, Drop Energy Layer",
                ["- 드랍 직전 4박 필터 스윕 + 1박 완전 공백",
                 "- 베이스라인에 사이드체인 컴프레션 적용",
                 "- 브리지에서 리듬 반 템포 (half-time) 전환"],
            )
        if best == "synthwave":
            return (
                ["- 아르페지오 신스 레이어와 드럼 머신 그루브 최적화",
                 "- 리버브/딜레이 공간감 확장으로 레트로 분위기 강화"],
                "Analog Synth Arp, Retro Drum Machine, Gated Reverb",
                ["- 코러스 전 옥타브 상승 신스 리드 추가",
                 "- 브리지에서 신스 패드 레이어 + 코러스 이펙트 강화",
                 mod],
            )
        if best == "jazz":
            return (
                ["- 코드 확장(9th, 11th, 13th) 활용으로 색채 강화",
                 "- 스윙 그루브의 레이드백 포켓 강화"],
                "Jazz Comping, Extended Harmony, Swing Groove",
                ["- 코러스 전 ii–V–I 진행으로 텐션 해소",
                 "- 솔로 섹션에 크로매틱 접근음 활용",
                 mod],
            )
        if best == "rock":
            return (
                ["- 기타 레이어와 보컬 에너지 균형 조정",
                 "- 드럼 킥/스네어 다이나믹 최적화"],
                "Guitar Layer, Power Chords, Dynamic Contrast",
                ["- 코러스 진입 전 드럼 필 + 1박 공백",
                 "- 브리지에서 파워 코드 → 클린 기타 대비",
                 mod],
            )
        if best == "metal":
            return (
                ["- 기타 리프와 드럼 블라스트 비트 동기화 최적화",
                 "- 더블 킥과 기타 팜뮤트 타이밍 정밀도 강화"],
                "Heavy Riff Layer, Double Kick, Distortion Wall",
                ["- 브리지에서 클린/헤비 다이나믹 대비 극대화",
                 "- 드랍 전 전체 밴드 유니즌 + 1박 공백",
                 mod],
            )
        if best == "rnb":
            return (
                ["- 그루브 포켓 및 보컬 멜리스마 강화",
                 "- 현악/패드 레이어와 보컬 밸런스 조정"],
                "Groove Pocket, Vocal Harmony, Melodic Ad-libs",
                ["- 코러스 전 보컬 하모니 레이어 추가",
                 "- 배경 패드에 maj7/9 코드 보이싱 활용",
                 mod],
            )
        if best == "ballad":
            return (
                ["- 감정 크레셴도 구간 동적 표현 강화",
                 "- 어쿠스틱 텍스처와 패드 레이어 균형"],
                "String Arrangement, Emotional Swell, Dynamic Contrast",
                ["- 코러스 진입 전 현악 스웰로 감정 예열",
                 "- 브리지에서 동명 단조(parallel minor) 일시 전조",
                 mod],
            )
        if best == "folk":
            return (
                ["- 어쿠스틱 기타 핑거피킹 다이나믹 표현 강화",
                 "- 보컬 하모니 레이어로 깊이감 추가"],
                "Fingerpicking Pattern, Vocal Harmony, Natural Reverb",
                ["- 브리지에서 카포 포지션 변경으로 색채 전환",
                 "- 코러스에 밴조/피들 레이어 추가",
                 mod],
            )
        if best == "classical":
            return (
                ["- 선율 발전과 모티프 반복 구조 정교화",
                 "- 다이나믹 마킹(pp→ff) 표현 범위 확장"],
                "Orchestral Swell, Counterpoint Layer, Dynamic Arc",
                ["- 코러스에서 전체 오케스트라 투티 효과",
                 "- 브리지에서 현악 피치카토 → 아르코 전환",
                 mod],
            )
        if best == "afrobeats":
            return (
                ["- 퍼커션 레이어와 멜로디 인터플레이 강화",
                 "- 오프비트 리듬 그루브 포켓 최적화"],
                "Percussion Layer, Afro Groove, Call-Response Melody",
                ["- 코러스에서 워킹 베이스라인 추가",
                 "- 브리지에서 타악기 브레이크다운 삽입",
                 mod],
            )
        if best == "kpop":
            return (
                ["- 훅 직전 드랍 포인트 에너지 집중",
                 "- 보컬 레이어링과 코러스 풀니스 강화"],
                "Vocal Layering, Hook Drop, Cinematic Build",
                ["- 코러스 진입 전 1박 공백으로 임팩트 강화",
                 "- 브릿지에서 동명 단조 일시 전조",
                 mod],
            )
        # Default
        return (
            ["- 감정 표현을 위한 다이나믹 변화 추가 권장"],
            "Emotional build-up, Dynamic contrast, Bridge modulation",
            ["- 코러스 진입 전 1박 쉬어서 임팩트 강화",
             "- 배경 패드 보이싱에 sus2 코드 활용",
             mod],
        )

    @staticmethod
    def _dynamic_advice(data: SunoPromptData) -> str:
        lines = ["### 현재 강점 (Current Strengths)"]
        lines.append(f"- 명확한 장르 설정: {', '.join(data.genre)}")

        _gtags = " ".join(data.genre + data.mood).lower()
        if any(g in _gtags for g in ("edm", "metal", "punk", "dnb", "drum and bass",
                                      "techno", "trance", "hardcore", "footwork")):
            tempo_desc = ("초고속" if data.bpm > 170 else "고속" if data.bpm > 140
                          else "적정" if data.bpm > 110 else "느린")
        elif any(g in _gtags for g in ("ballad", "lo-fi", "lofi", "ambient",
                                        "jazz", "blues", "acoustic", "chill")):
            tempo_desc = ("빠른" if data.bpm > 100 else "적정" if data.bpm > 65 else "슬로우")
        else:
            tempo_desc = ("빠른 에너지감" if data.bpm > 130
                          else "안정적인 중간" if data.bpm > 90 else "슬로우")
        lines.append(f"- BPM {data.bpm} — {tempo_desc} 템포")

        extended = [c for c in data.chord_progression
                    if any(x in c for x in ["7", "maj7", "m7", "sus", "dim", "aug"])]
        if extended:
            lines.append(f"- 확장 코드 활용: {', '.join(extended[:3])}")

        section_names_lower = {s.name.lower() for s in data.sections}
        if any("chorus" in n or "hook" in n for n in section_names_lower):
            lines.append("- 명확한 후렴 구조 포함")
        if data.mood:
            lines.append(f"- 감정 방향성 명확: {', '.join(data.mood[:3])}")

        genre_improve, add_tags, recs = ReportGenerator._genre_advice(data)

        lines += ["", "### 개선할 점 (Areas to Improve)"]

        if data.bpm < 75:
            lines.append("- 슬로우 템포 — 현악 또는 피아노 레이어로 긴장감 유지 권장")
        elif data.bpm > 150:
            lines.append("- 고속 템포 — 브레이크다운 섹션으로 에너지 조절 고려")
        lines.extend(genre_improve)

        has_bridge = any("bridge" in n for n in section_names_lower)
        if not has_bridge and len(data.sections) >= 3:
            lines.append("- 브리지 섹션 추가로 곡 구조 다양화 권장")
        else:
            lines.append("- 브리지 섹션에서 조성 변화(전조) 고려")

        if not extended:
            lines.append("- 7th / maj7 코드 활용으로 화성 색채 강화 권장")

        if data.key.endswith("m"):
            lines.append("- 단조 곡 — 전환부에서 동명 장조 활용으로 감정 해소 포인트 생성 권장")
        else:
            lines.append("- 장조 곡 — 단조 평행조 일시 전조로 감정 깊이 추가 권장")

        lines += [
            "",
            "### 수정된 Suno 프롬프트 제안 (Revised Suno Prompt)",
            f"[Genre: {', '.join(data.genre)}]",
            f"[BPM: {data.bpm}]",
            f"[Key: {data.key}]",
            f"[Add: {add_tags}]",
            "",
            "### 음악적 보완점 (Musical Recommendations)",
        ]
        lines.extend(recs)
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Markdown builder
    # ------------------------------------------------------------------ #

    def _build_markdown(
        self,
        data: SunoPromptData,
        audio: Optional[AudioAnalysisResult],
        improvement: str,
    ) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        sections = []

        sections.append(f"# Music Analysis Report\n\n*Generated: {now}*\n")

        # 1. Track Overview
        sections.append(self._section_overview(data, audio))

        # 2. Section Timeline
        sections.append(self._section_timeline(data, audio))

        # 3. Energy Flow
        sections.append(self._section_energy(data, audio))

        # 4. Lyrical Analysis
        sections.append(self._section_lyrics(data))

        # 5. Technical Stats
        sections.append(self._section_technical(data, audio))

        # 6. Improvement Suggestions
        sections.append(f"## 6. Improvement Suggestions\n\n{improvement}\n")

        # 7. Chord Progression
        sections.append(self._section_chords(data))

        return "\n---\n\n".join(sections)

    def _section_overview(
        self, data: SunoPromptData, audio: Optional[AudioAnalysisResult]
    ) -> str:
        duration = audio.duration_str if (audio and audio.available) else "N/A"
        detected_bpm = f" *(detected: {audio.bpm:.1f})*" if (audio and audio.available) else ""
        detected_key = f" *(detected: {audio.estimated_key})*" if (audio and audio.available) else ""
        return (
            "## 1. Track Overview\n\n"
            f"| Field | Value |\n"
            f"|-------|-------|\n"
            f"| **Title** | {data.title} |\n"
            f"| **Artist** | {data.artist} |\n"
            f"| **Genre** | {', '.join(data.genre)} |\n"
            f"| **BPM** | {data.bpm}{detected_bpm} |\n"
            f"| **Key** | {data.key}{detected_key} |\n"
            f"| **Mood** | {', '.join(data.mood) or 'N/A'} |\n"
            f"| **Instruments** | {', '.join(data.instruments) or 'N/A'} |\n"
            f"| **Vocal Style** | {', '.join(data.vocal_style) or 'N/A'} |\n"
            f"| **Time Signature** | {data.time_signature} |\n"
            f"| **Language** | {data.language} |\n"
            f"| **Duration** | {duration} |\n"
            f"| **Total Sections** | {len(data.sections)} |\n"
            f"| **Total Lyric Lines** | {data.total_lines} |\n"
        )

    def _section_timeline(
        self, data: SunoPromptData, audio: Optional[AudioAnalysisResult]
    ) -> str:
        rows = ["## 2. Section Timeline\n", "| # | Section | Start | End | Duration | Lines |", "|---|---------|-------|-----|----------|-------|"]
        cursor = 0.0
        for i, s in enumerate(data.sections, 1):
            dur = s.duration_hint or 0.0
            end = cursor + dur
            rows.append(
                f"| {i} | **{s.name}** | {_fmt_time(cursor)} | {_fmt_time(end)} | "
                f"{dur:.0f}s | {len(s.lyrics)} |"
            )
            cursor = end

        # If real audio available, add energy column note
        if audio and audio.available and audio.section_energies:
            rows.append(
                "\n> Energy values measured from audio file.\n"
            )
        return "\n".join(rows)

    def _section_energy(
        self, data: SunoPromptData, audio: Optional[AudioAnalysisResult]
    ) -> str:
        header = "## 3. Energy Flow\n"
        if audio and audio.available and audio.section_energies:
            chart = audio.ascii_energy_chart(width=40)
            return f"{header}\n```\n{chart}\n```\n"

        # Heuristic energy: section type × BPM/genre multiplier
        lines = [header, "```"]
        # post-chorus / breakdown MUST precede chorus in iteration order
        base = {
            "intro": 0.30, "build": 0.55,
            "verse": 0.50,
            "pre-chorus": 0.65, "pre chorus": 0.65,
            "post-chorus": 0.72, "post chorus": 0.72,
            "chorus": 0.90, "hook": 0.90, "refrain": 0.85,
            "drop": 1.00, "breakdown": 0.30, "interlude": 0.30,
            "bridge": 0.60,
            "rap": 0.75, "verse rap": 0.70, "spoken": 0.40,
            "outro": 0.20, "coda": 0.15,
        }
        tags = " ".join(data.genre + data.mood + data.instruments).lower()
        def _has(*kws): return any(kw in tags for kw in kws)
        if _has("edm", "metal", "rock", "techno", "trap", "drill", "dance",
                "hardcore", "punk", "dnb", "drum and bass", "dubstep"):
            mult = 1.15
        elif _has("ballad", "lo-fi", "lofi", "ambient", "acoustic",
                  "chill", "gentle", "classical", "chillwave"):
            mult = 0.75
        elif data.bpm > 140:
            mult = 1.10
        elif data.bpm < 80:
            mult = 0.80
        else:
            mult = 1.00
        width = 40
        for s in data.sections:
            key = next((k for k in base if k in s.name.lower()), "verse")
            level = min(1.0, base[key] * mult)
            bar_len = int(level * width)
            bar = "█" * bar_len + "░" * (width - bar_len)
            label = "High" if level >= 0.8 else "Med" if level >= 0.5 else "Low"
            lines.append(f"{s.name:<16} [{bar}] {label}")
        lines.append("```")
        lines.append("\n> *Estimated from section type (no audio file provided)*")
        return "\n".join(lines)

    def _section_lyrics(self, data: SunoPromptData) -> str:
        keywords = self._extract_keywords(data)
        all_words = [w for s in data.sections for w in s.all_words]
        unique = len(set(w.lower() for w in all_words))

        rows = ["## 4. Lyrical Analysis\n"]
        rows.append(f"- **Total Words:** {len(all_words)}")
        rows.append(f"- **Unique Words:** {unique}")
        rows.append(f"- **Language:** {data.language}")
        rows.append(f"- **Key Visual Keywords:** {', '.join(keywords[:12])}")
        rows.append("")

        rows.append("### Lyrics by Section\n")
        for s in data.sections:
            if s.lyrics:
                rows.append(f"**[{s.name}]**")
                for line in s.lyrics:
                    rows.append(f"> {line}")
                rows.append("")
        return "\n".join(rows)

    def _section_technical(
        self, data: SunoPromptData, audio: Optional[AudioAnalysisResult]
    ) -> str:
        rows = ["## 5. Technical Statistics\n"]
        rows.append("### From Prompt")
        rows.append(f"- Chord Progression: `{' - '.join(data.chord_progression)}`")
        rows.append(f"- BPM: {data.bpm}")
        rows.append(f"- Key: {data.key}")
        rows.append(f"- Sections: {len(data.sections)}")
        beats_per_bar = self._beats_per_bar(data.time_signature)
        seconds_per_bar = (60.0 / data.bpm) * beats_per_bar
        total_bars = sum(
            max(4, len(s.lyrics) * 2) for s in data.sections
        )
        rows.append(f"- Estimated Bars: {total_bars}")
        rows.append(f"- Estimated Duration: ~{_fmt_time(total_bars * seconds_per_bar)}")

        if audio and audio.available:
            rows.append("\n### From Audio File")
            rows.append(f"- Detected BPM: **{audio.bpm:.1f}**")
            rows.append(f"- Detected Key: **{audio.estimated_key}**")
            rows.append(f"- Duration: **{audio.duration_str}**")
            rows.append(f"- RMS Energy (mean): {audio.rms_mean:.4f}")
            rows.append(f"- RMS Energy (std): {audio.rms_std:.4f}")
            rows.append(f"- Dynamic Range: {audio.dynamic_range_db:.1f} dB")
            rows.append(f"- Spectral Centroid: {audio.spectral_centroid_mean:.0f} Hz")
            rows.append(f"- Spectral Roll-off: {audio.spectral_rolloff_mean:.0f} Hz")
            rows.append(f"- Zero-Crossing Rate: {audio.zero_crossing_rate:.4f}")
        return "\n".join(rows)

    def _section_chords(self, data: SunoPromptData) -> str:
        progression = " → ".join(data.chord_progression)
        rows = [
            "## 7. Chord Progression Analysis\n",
            f"**Global Progression:** `{progression}`\n",
        ]
        for s in data.sections:
            if s.chords:
                rows.append(f"**{s.name}:** `{' - '.join(s.chords)}`")
        # Roman numeral analysis (simplified)
        rows.append("\n### Scale Degree Mapping")
        roman = self._to_roman(data.chord_progression, data.key)
        rows.append(f"`{' - '.join(roman)}`")
        return "\n".join(rows)

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _beats_per_bar(time_signature: str) -> float:
        """Quarter-note beats per bar, correct for compound time (6/8→3.0, 12/8→6.0)."""
        m = re.match(r"^\s*(\d{1,2})\s*/\s*(\d{1,2})\s*$", time_signature or "")
        if not m:
            return 4.0
        return (int(m.group(1)) / int(m.group(2))) * 4.0

    @staticmethod
    def _extract_keywords(data: SunoPromptData) -> list[str]:
        stopwords = {
            "이", "가", "을", "를", "은", "는", "의", "에", "로", "으로",
            "와", "과", "도", "만", "에서", "the", "a", "an", "and", "or",
            "in", "on", "at", "to", "of", "is", "are", "was", "be",
        }
        freq: dict[str, int] = {}
        for s in data.sections:
            for word in s.all_words:
                w = word.strip(".,!?\"'").lower()
                if w and w not in stopwords and len(w) > 1:
                    freq[w] = freq.get(w, 0) + 1
        return sorted(freq, key=lambda k: freq[k], reverse=True)

    # Flat → enharmonic sharp mapping for chromatic lookups
    _FLAT_TO_SHARP: dict[str, str] = {
        "Cb": "B", "Db": "C#", "Eb": "D#", "Fb": "E",
        "Gb": "F#", "Ab": "G#", "Bb": "A#",
    }

    @staticmethod
    def _to_roman(chords: list[str], key: str) -> list[str]:
        chromatic = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        flat_to_sharp = ReportGenerator._FLAT_TO_SHARP
        is_minor = key.endswith("m")
        root_name = key[:-1] if is_minor else key
        root_name = flat_to_sharp.get(root_name, root_name)
        try:
            root_idx = next(i for i, n in enumerate(chromatic) if n == root_name)
        except StopIteration:
            return chords

        scale_major = [0, 2, 4, 5, 7, 9, 11]
        scale_minor = [0, 2, 3, 5, 7, 8, 10]
        scale = scale_minor if is_minor else scale_major
        roman_nums = (
            ["i", "ii°", "III", "iv", "v", "VI", "VII"]
            if is_minor
            else ["I", "ii", "iii", "IV", "V", "vi", "vii°"]
        )

        result = []
        for ch in chords:
            ch_root = re.match(r"[A-Gb#]+", ch)
            if not ch_root:
                result.append(ch)
                continue
            cr = ch_root.group()
            cr_normalized = flat_to_sharp.get(cr, cr)
            try:
                ci = next(i for i, n in enumerate(chromatic) if n == cr_normalized)
            except StopIteration:
                result.append(ch)
                continue
            interval = (ci - root_idx) % 12
            if interval in scale:
                deg = scale.index(interval)
                roman = roman_nums[deg]
                if "m" in ch and not ch.endswith("maj7"):
                    roman = roman.lower()
                result.append(roman)
            else:
                result.append(f"♭{cr}")
        return result
