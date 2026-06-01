"""
Flask web server for AI Music & Visual Content Executive Producer.
Provides file upload + prompt input UI, with real-time SSE progress.
"""
from __future__ import annotations

import json
import os
import queue
import re
import shutil
import sys
import threading
import time
import uuid
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────────────
_BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BASE))
os.chdir(str(_BASE))

from flask import Flask, Response, jsonify, render_template, request, send_from_directory

try:
    import bleach
except ImportError:
    bleach = None

try:
    import markdown2
    def _md(text: str) -> str:
        html = markdown2.markdown(
            text,
            extras=["tables", "fenced-code-blocks", "strike", "header-ids"],
        )
        return _sanitize_html(html)
except ImportError:
    def _md(text: str) -> str:
        import html
        return f"<pre>{html.escape(text)}</pre>"

# ── App setup ────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

_secret_key = os.getenv("FLASK_SECRET_KEY")
if not _secret_key:
    _key_file = _BASE / ".flask_secret"
    if _key_file.exists():
        _secret_key = _key_file.read_text().strip()
    else:
        _secret_key = os.urandom(24).hex()
        try:
            _key_file.write_text(_secret_key)
        except OSError:
            pass
app.config["SECRET_KEY"] = _secret_key

_UPLOAD = _BASE / "uploads"
_OUT = _BASE / "outputs"
_UPLOAD.mkdir(exist_ok=True)
_OUT.mkdir(exist_ok=True)

_JOBS: dict[str, dict] = {}
_QUEUES: dict[str, queue.Queue] = {}
_JOB_LOCK = threading.Lock()
_JOB_ID_RE = re.compile(r"^[a-f0-9]{8}$")
_JOB_TTL_SECONDS = int(os.getenv("JOB_TTL_SECONDS", "21600"))

# ── Helpers ──────────────────────────────────────────────────────────────────

def _push(job_id: str, msg: dict) -> None:
    if q := _QUEUES.get(job_id):
        q.put(msg)


def _sanitize_html(html: str) -> str:
    if bleach is None:
        # bleach 미설치 시 최소 XSS 방어: script/iframe 태그만 제거
        html = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<iframe\b[^>]*>.*?</iframe>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'\s+on\w+\s*=\s*"[^"]*"', '', html, flags=re.IGNORECASE)
        return html

    allowed_tags = set(bleach.sanitizer.ALLOWED_TAGS) | {
        "h1", "h2", "h3", "h4", "h5", "h6",
        "p", "pre", "code", "table", "thead", "tbody", "tr", "th", "td",
        "blockquote", "hr", "br", "span", "div",
    }
    allowed_attrs = {
        **bleach.sanitizer.ALLOWED_ATTRIBUTES,
        "a": ["href", "title", "target", "rel"],
        "code": ["class"],
        "span": ["class"],
        "div": ["class"],
        "th": ["align"],
        "td": ["align"],
    }
    return bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attrs,
        protocols=["http", "https", "mailto"],
        strip=True,
    )


def _valid_job_id(job_id: str) -> bool:
    return bool(_JOB_ID_RE.fullmatch(job_id or ""))


def _cleanup_old_jobs() -> None:
    cutoff = time.time() - _JOB_TTL_SECONDS
    expired: list[tuple[str, str | None]] = []
    with _JOB_LOCK:
        for jid, info in list(_JOBS.items()):
            created_at = float(info.get("created_at", 0))
            if created_at and created_at < cutoff:
                expired.append((jid, info.get("audio_path")))
                _JOBS.pop(jid, None)
                _QUEUES.pop(jid, None)

    out_root = _OUT.resolve()
    upload_root = _UPLOAD.resolve()
    for jid, audio_path in expired:
        out_dir = (_OUT / jid).resolve()
        if out_root in out_dir.parents and out_dir.exists():
            shutil.rmtree(out_dir, ignore_errors=True)
        if audio_path:
            audio_file = Path(audio_path).resolve()
            if upload_root in audio_file.parents and audio_file.exists():
                audio_file.unlink(missing_ok=True)


def _fmt(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    return f"{m}:{s:02d}"


# ── Analysis task (runs in background thread) ────────────────────────────────

def _run_analysis(job_id: str, prompt: str, audio_path: str | None) -> None:
    out = _OUT / job_id
    out.mkdir(exist_ok=True)
    try:
        from analyzer.suno_parser import SunoParser
        from analyzer.audio_analyzer import AudioAnalyzer
        from generators.lilypond_gen import LilyPondGenerator
        from generators.report_gen import ReportGenerator
        from generators.visual_gen import VisualGenerator

        # ── Step 1: Parse ────────────────────────────────────────────────────
        _push(job_id, {"type": "step", "pct": 8, "label": "Suno 프롬프트 파싱 중..."})
        data = SunoParser().parse(prompt)
        _push(job_id, {
            "type": "parsed",
            "title": data.title,
            "genre": ", ".join(data.genre),
            "bpm": data.bpm,
            "key": data.key,
            "sections": len(data.sections),
        })

        # ── Step 2: Audio (optional) ─────────────────────────────────────────
        audio_res = None
        if audio_path:
            _push(job_id, {"type": "step", "pct": 25, "label": "오디오 분석 중 (librosa)..."})
            audio_res = AudioAnalyzer().analyze(
                audio_path, [s.name for s in data.sections]
            )
            if not audio_res.available:
                _push(job_id, {"type": "warn", "message": f"오디오 분석 실패: {audio_res.error}"})
                audio_res = None

        # ── Step 3: Report ───────────────────────────────────────────────────
        _push(job_id, {"type": "step", "pct": 42, "label": "음악 분석 리포트 생성 중..."})
        ReportGenerator().generate(data, audio_res, out)

        # ── Step 4: LilyPond ─────────────────────────────────────────────────
        _push(job_id, {"type": "step", "pct": 62, "label": "LilyPond 악보 생성 중..."})
        ly_path = LilyPondGenerator().generate(data, out)

        # ── Step 5: Visual ───────────────────────────────────────────────────
        _push(job_id, {"type": "step", "pct": 80, "label": "비주얼 프롬프트 생성 중..."})
        visual, _ = VisualGenerator().generate(data, out)

        _push(job_id, {"type": "step", "pct": 95, "label": "결과 정리 중..."})

        # ── Build result payload ─────────────────────────────────────────────
        report_html = ""
        rp = out / "report.md"
        if rp.exists():
            report_html = _md(rp.read_text("utf-8"))

        ly_code = ly_path.read_text("utf-8") if ly_path.exists() else ""

        # Timeline
        cursor = 0.0
        timeline = []

        # Base section energy (0–1 scale), then scaled by genre/BPM
        # Key order matters: longer/specific names BEFORE their substrings
        # so next(..., k in s.name.lower()) matches correctly.
        _base_energy = {
            "intro": 0.30, "build": 0.55,
            "verse": 0.50,
            "pre-chorus": 0.65, "pre chorus": 0.65,
            "post-chorus": 0.72, "post chorus": 0.72,
            "chorus": 0.90, "hook": 0.90, "refrain": 0.85,
            "drop": 1.00, "breakdown": 0.30, "interlude": 0.30,
            "bridge": 0.50,
            "rap": 0.80, "verse rap": 0.75, "spoken": 0.40,
            "outro": 0.25, "coda": 0.15,
        }

        def _energy_label(lv: float) -> str:
            if lv >= 0.85: return "high"
            if lv >= 0.65: return "medium-high"
            if lv >= 0.40: return "medium"
            if lv >= 0.20: return "medium-low"
            return "low"

        _all_tags = " ".join(data.genre + data.mood + data.instruments + data.vocal_style).lower()

        def _tag(*kws: str) -> bool:
            return any(k in _all_tags for k in kws)

        if _tag("edm", "metal", "rock", "punk", "hardcore", "techno", "trance",
                "trap", "drill", "dance", "dnb", "drum and bass", "dubstep"):
            _emult = 1.15
        elif _tag("ballad", "lo-fi", "lofi", "ambient", "acoustic",
                  "chill", "gentle", "classical", "folk"):
            _emult = 0.75
        elif data.bpm > 140:
            _emult = 1.10
        elif data.bpm < 80:
            _emult = 0.80
        else:
            _emult = 1.00

        energy_hints = {
            k: _energy_label(min(1.0, v * _emult))
            for k, v in _base_energy.items()
        }

        for i, s in enumerate(data.sections, 1):
            dur = s.duration_hint or 0.0
            ek = next((k for k in energy_hints if k in s.name.lower()), "medium")
            timeline.append({
                "idx": i, "name": s.name,
                "start": _fmt(cursor), "end": _fmt(cursor + dur),
                "duration": f"{dur:.0f}s", "lines": len(s.lyrics),
                "energy": energy_hints[ek],
            })
            cursor += dur

        # Audio stats for display
        audio_stats = None
        if audio_res and audio_res.available:
            audio_stats = {
                "bpm": round(audio_res.bpm, 1),
                "key": audio_res.estimated_key,
                "duration": audio_res.duration_str,
                "dynamic_range": round(audio_res.dynamic_range_db, 1),
                "spectral_centroid": round(audio_res.spectral_centroid_mean),
            }

        result = {
            "metadata": {
                "title": data.title,
                "artist": data.artist,
                "genre": data.genre,
                "bpm": data.bpm,
                "key": data.key,
                "mood": data.mood,
                "instruments": data.instruments,
                "vocal_style": data.vocal_style,
                "language": data.language,
                "time_signature": data.time_signature,
                "chord_progression": data.chord_progression,
                "total_sections": len(data.sections),
                "total_lines": data.total_lines,
            },
            "audio_stats": audio_stats,
            "timeline": timeline,
            "report_html": report_html,
            "lilypond_code": ly_code,
            "visual": {
                "theme": visual.theme,
                "palette": visual.color_palette,
                "album_art_prompt": visual.album_art_prompt,
                "video_scenes": visual.video_scenes,
                "style_guide": visual.style_guide,
                "keyword_map": visual.keyword_map,
            },
            "files": sorted(f.name for f in out.iterdir() if f.is_file()),
            "job_id": job_id,
        }

        with _JOB_LOCK:
            current = _JOBS.get(job_id, {})
            _JOBS[job_id] = {
                **current,
                "status": "done",
                "result": result,
                "completed_at": time.time(),
            }
        _push(job_id, {"type": "done", "pct": 100, "result": result})

    except Exception as exc:
        import traceback
        traceback.print_exc()
        with _JOB_LOCK:
            current = _JOBS.get(job_id, {})
            _JOBS[job_id] = {
                **current,
                "status": "error",
                "error": str(exc),
                "completed_at": time.time(),
            }
        _push(job_id, {"type": "error", "message": str(exc)})


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/sample")
def sample():
    sp = _BASE / "sample_prompt.txt"
    if sp.exists():
        return sp.read_text("utf-8"), 200, {"Content-Type": "text/plain; charset=utf-8"}
    return "", 404


@app.route("/api/analyze", methods=["POST"])
def analyze():
    _cleanup_old_jobs()
    prompt = (request.form.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "프롬프트를 입력해주세요."}), 400

    audio_path = None
    f = request.files.get("audio")
    if f and f.filename:
        from config import AUDIO_FORMATS
        ext = Path(f.filename).suffix.lower()
        if ext in AUDIO_FORMATS:
            p = _UPLOAD / f"{uuid.uuid4().hex}{ext}"
            f.save(str(p))
            audio_path = str(p)
        else:
            return jsonify({"error": f"지원하지 않는 오디오 형식: {ext}"}), 400

    jid = uuid.uuid4().hex[:8]
    with _JOB_LOCK:
        _JOBS[jid] = {
            "status": "running",
            "created_at": time.time(),
            "audio_path": audio_path,
        }
        _QUEUES[jid] = queue.Queue()
    threading.Thread(
        target=_run_analysis, args=(jid, prompt, audio_path), daemon=True
    ).start()
    return jsonify({"job_id": jid})


@app.route("/api/stream/<jid>")
def stream(jid: str):
    _cleanup_old_jobs()
    if not _valid_job_id(jid):
        return jsonify({"error": "Invalid job id"}), 400

    def gen():
        job = _JOBS.get(jid)
        if job and job.get("status") == "done":
            msg = {"type": "done", "pct": 100, "result": job["result"]}
            yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
            return
        if job and job.get("status") == "error":
            msg = {"type": "error", "message": job.get("error", "Unknown error")}
            yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
            return

        q = _QUEUES.get(jid)
        if not q:
            yield f'data: {{"type":"error","message":"Job not found"}}\n\n'
            return
        while True:
            try:
                msg = q.get(timeout=60)
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                if msg["type"] in ("done", "error"):
                    break
            except queue.Empty:
                yield 'data: {"type":"ping"}\n\n'

    return Response(
        gen(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/download/<jid>/<fname>")
def download(jid: str, fname: str):
    _cleanup_old_jobs()
    if not _valid_job_id(jid):
        return jsonify({"error": "Invalid job id"}), 400
    if jid not in _JOBS:
        return jsonify({"error": "Job not found"}), 404

    safe = Path(fname).name  # prevent path traversal
    out_root = _OUT.resolve()
    job_dir = (_OUT / jid).resolve()
    if out_root not in job_dir.parents or not job_dir.exists():
        return jsonify({"error": "Output not found"}), 404
    return send_from_directory(str(job_dir), safe, as_attachment=True)


if __name__ == "__main__":
    print("\n  AI Music Producer Web UI")
    print("  http://localhost:5000\n")
    app.run(debug=False, port=5000, threaded=True)
