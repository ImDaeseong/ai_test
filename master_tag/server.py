# =============================================================================
# Suno AI 마스터링 웹 서버
# Flask + SSE(Server-Sent Events)로 실시간 진행 상태를 UI에 전달합니다.
# 실행: python server.py  ->  http://localhost:5000
# =============================================================================

import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from flask import Flask, Response, jsonify, request, send_file
    from werkzeug.utils import secure_filename
except ImportError:
    print("[오류] flask가 설치되지 않았습니다.")
    print("       실행: pip install flask")
    raise

from main import AudioProcessingError, master_audio


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg"}
MAX_UPLOAD_BYTES = 300 * 1024 * 1024
MAX_WORKERS = int(os.getenv("MASTERING_MAX_WORKERS", max(1, min(4, (os.cpu_count() or 2) // 2))))
MAX_ACTIVE_JOBS = int(os.getenv("MASTERING_MAX_ACTIVE_JOBS", MAX_WORKERS * 8))
MAX_STORED_JOBS = int(os.getenv("MASTERING_MAX_STORED_JOBS", 1000))
JOB_TTL_SECONDS = int(os.getenv("MASTERING_JOB_TTL_SECONDS", 6 * 60 * 60))
CLEANUP_INTERVAL_SECONDS = int(os.getenv("MASTERING_CLEANUP_INTERVAL_SECONDS", 10 * 60))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="mastering")
jobs_lock = threading.RLock()
cleanup_started = False


@dataclass
class Job:
    id: str
    input_path: Path
    output_path: Path
    download_name: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    status: str = "queued"
    events: list[dict] = field(default_factory=list)
    condition: threading.Condition = field(default_factory=lambda: threading.Condition(threading.RLock()))
    error: Optional[str] = None

    def add_event(self, event: dict) -> None:
        with self.condition:
            self.updated_at = time.time()
            self.events.append(event)
            if event.get("type") == "done":
                self.status = "done"
            elif event.get("type") == "error":
                self.status = "error"
                self.error = event.get("message")
            self.condition.notify_all()


jobs: dict[str, Job] = {}


def _json_error(message: str, status_code: int):
    return jsonify({"error": message}), status_code



def _cleanup_old_jobs() -> None:
    now = time.time()
    stale_ids: list[str] = []

    with jobs_lock:
        for job_id, job in jobs.items():
            if now - job.updated_at > JOB_TTL_SECONDS:
                stale_ids.append(job_id)

        stale_jobs = [jobs.pop(job_id) for job_id in stale_ids]

    for job in stale_jobs:
        for path in (job.input_path, job.output_path):
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                pass


def _count_jobs() -> dict[str, int]:
    counts = {
        "queued": 0,
        "running": 0,
        "done": 0,
        "error": 0,
    }
    for job in jobs.values():
        counts[job.status] = counts.get(job.status, 0) + 1
    counts["active"] = counts.get("queued", 0) + counts.get("running", 0)
    counts["total"] = len(jobs)
    return counts


def _can_accept_job() -> tuple[bool, str]:
    with jobs_lock:
        counts = _count_jobs()

    if counts["active"] >= MAX_ACTIVE_JOBS:
        return False, "현재 처리 대기열이 가득 찼습니다. 잠시 후 다시 시도해 주세요."

    if counts["total"] >= MAX_STORED_JOBS:
        return False, "서버 작업 보관 한도에 도달했습니다. 잠시 후 다시 시도해 주세요."

    return True, ""


def _get_job(job_id: str) -> Optional[Job]:
    with jobs_lock:
        return jobs.get(job_id)


def _try_store_job(job: Job) -> tuple[bool, str]:
    with jobs_lock:
        counts = _count_jobs()
        if counts["active"] >= MAX_ACTIVE_JOBS:
            return False, "현재 처리 대기열이 가득 찼습니다. 잠시 후 다시 시도해 주세요."
        if counts["total"] >= MAX_STORED_JOBS:
            return False, "서버 작업 보관 한도에 도달했습니다. 잠시 후 다시 시도해 주세요."
        jobs[job.id] = job
    return True, ""


def _run_job(job: Job) -> None:
    try:
        job.add_event(
            {
                "type": "queued",
                "message": "작업을 시작했습니다.",
                "max_workers": MAX_WORKERS,
            }
        )
        with job.condition:
            job.status = "running"
            job.updated_at = time.time()
            job.condition.notify_all()

        master_audio(
            input_path=str(job.input_path),
            output_path=str(job.output_path),
            on_progress=job.add_event,
        )
    except AudioProcessingError as exc:
        job.add_event({"type": "error", "message": str(exc)})
    except Exception as exc:
        job.add_event({"type": "error", "message": f"예상하지 못한 오류가 발생했습니다: {exc}"})
    finally:
        try:
            if job.input_path.exists():
                job.input_path.unlink()
        except OSError:
            pass


def _cleanup_loop() -> None:
    while True:
        time.sleep(CLEANUP_INTERVAL_SECONDS)
        _cleanup_old_jobs()


def _ensure_cleanup_thread() -> None:
    global cleanup_started
    with jobs_lock:
        if cleanup_started:
            return
        cleanup_started = True

    thread = threading.Thread(target=_cleanup_loop, name="job-cleanup", daemon=True)
    thread.start()


@app.route("/")
def index():
    return send_file(BASE_DIR / "index.html")


@app.before_request
def before_request():
    _ensure_cleanup_thread()


@app.route("/health")
def health():
    with jobs_lock:
        counts = _count_jobs()

    return jsonify(
        {
            "ok": True,
            "max_workers": MAX_WORKERS,
            "max_active_jobs": MAX_ACTIVE_JOBS,
            "max_stored_jobs": MAX_STORED_JOBS,
            "jobs": counts,
        }
    )


@app.route("/job/<job_id>")
def job_status(job_id):
    job = _get_job(job_id)
    if job is None:
        return _json_error("잡을 찾을 수 없습니다.", 404)

    with job.condition:
        last_event = job.events[-1] if job.events else None
        payload = {
            "job_id": job.id,
            "status": job.status,
            "error": job.error,
            "download_ready": job.status == "done" and job.output_path.is_file(),
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "event_count": len(job.events),
            "last_event": last_event,
        }

    return jsonify(payload)


@app.route("/master", methods=["POST"])
def start_master():
    _cleanup_old_jobs()

    can_accept, reason = _can_accept_job()
    if not can_accept:
        return _json_error(reason, 503)

    if "file" not in request.files:
        return _json_error("파일이 없습니다.", 400)

    file = request.files["file"]
    if not file.filename:
        return _json_error("파일명이 비어 있습니다.", 400)

    # 확장자는 원본 파일명에서 추출 (secure_filename은 한글 등 비ASCII 문자를 제거해
    # "음악.mp3" → "mp3" 처럼 확장자 앞 점까지 사라지므로 확장자 검사에 사용 불가)
    suffix = Path(file.filename).suffix.lower()
    if not suffix or suffix not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return _json_error(f"지원하지 않는 파일 형식입니다. 허용 형식: {allowed}", 400)

    safe_name = secure_filename(file.filename)
    # 한글 전용 파일명처럼 ASCII 문자가 없으면 secure_filename이 빈 문자열 반환
    stem = Path(safe_name).stem if safe_name else "upload"

    job_id = str(uuid.uuid4())
    input_path = UPLOAD_DIR / f"{job_id}_{stem}{suffix}"
    output_path = OUTPUT_DIR / f"{job_id}_{stem}_mastered.wav"
    download_name = f"{stem}_mastered.wav"

    try:
        file.save(input_path)
    except OSError as exc:
        return _json_error(f"업로드 파일을 저장할 수 없습니다: {exc}", 500)

    job = Job(
        id=job_id,
        input_path=input_path,
        output_path=output_path,
        download_name=download_name,
    )
    job.add_event({"type": "queued", "message": "작업 대기열에 등록되었습니다."})

    stored, reason = _try_store_job(job)
    if not stored:
        try:
            if input_path.exists():
                input_path.unlink()
        except OSError:
            pass
        return _json_error(reason, 503)

    executor.submit(_run_job, job)

    return jsonify({"job_id": job_id, "status": job.status})


@app.route("/progress/<job_id>")
def progress(job_id):
    job = _get_job(job_id)
    if job is None:
        return _json_error("잡을 찾을 수 없습니다.", 404)

    def generate():
        index = 0

        while True:
            with job.condition:
                if index >= len(job.events):
                    job.condition.wait(timeout=30)

                if index >= len(job.events):
                    event = {"type": "heartbeat"}
                else:
                    event = job.events[index]
                    index += 1

            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            if event.get("type") in ("done", "error"):
                break

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/download/<job_id>")
def download(job_id):
    job = _get_job(job_id)
    if job is None:
        return _json_error("잡을 찾을 수 없습니다.", 404)

    if job.status != "done" or not job.output_path.is_file():
        return _json_error("아직 처리가 완료되지 않았습니다.", 404)

    return send_file(
        job.output_path,
        as_attachment=True,
        download_name=job.download_name,
        mimetype="audio/wav",
    )


@app.errorhandler(413)
def upload_too_large(_exc):
    mb = MAX_UPLOAD_BYTES // (1024 * 1024)
    return _json_error(f"파일이 너무 큽니다. 최대 {mb}MB까지 업로드할 수 있습니다.", 413)


if __name__ == "__main__":
    _ensure_cleanup_thread()
    print("=" * 50)
    print("  Suno AI 마스터링 웹 UI 시작")
    print("  브라우저에서 열기 -> http://localhost:5000")
    print(f"  동시 처리 작업 수: {MAX_WORKERS}")
    print(f"  최대 활성 작업 수: {MAX_ACTIVE_JOBS}")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
