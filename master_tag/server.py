# =============================================================================
# Suno AI 마스터링 웹 서버
# Flask + SSE(Server-Sent Events)로 실시간 진행 상태를 UI에 전달합니다.
# 실행: python server.py  →  http://localhost:5000
# =============================================================================

import os
import uuid
import json
import queue
import threading

try:
    from flask import Flask, request, jsonify, Response, send_file
except ImportError:
    print("[오류] flask가 설치되지 않았습니다.")
    print("       실행: pip install flask")
    raise

from main import master_audio

app = Flask(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# job_id → {'queue': Queue, 'output_path': str | None}
_jobs: dict = {}


# ---------------------------------------------------------------------------
# 페이지
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_file(os.path.join(os.path.dirname(__file__), "index.html"))


# ---------------------------------------------------------------------------
# 파일 업로드 → 백그라운드 처리 시작
# ---------------------------------------------------------------------------

@app.route("/master", methods=["POST"])
def start_master():
    if "file" not in request.files:
        return jsonify({"error": "파일이 없습니다."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "파일명이 비어 있습니다."}), 400

    job_id = str(uuid.uuid4())
    safe_name = f"{job_id}_{file.filename}"
    input_path = os.path.join(UPLOAD_DIR, safe_name)
    file.save(input_path)

    base, _ = os.path.splitext(file.filename)
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}_{base}_mastered.wav")

    q: queue.Queue = queue.Queue()
    _jobs[job_id] = {"queue": q, "output_path": None}

    def run():
        try:
            master_audio(
                input_path=input_path,
                output_path=output_path,
                on_progress=lambda event: q.put(event),
            )
            _jobs[job_id]["output_path"] = output_path
        except Exception as exc:
            q.put({"type": "error", "message": str(exc)})

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


# ---------------------------------------------------------------------------
# SSE 진행 스트림
# ---------------------------------------------------------------------------

@app.route("/progress/<job_id>")
def progress(job_id):
    if job_id not in _jobs:
        return jsonify({"error": "잡을 찾을 수 없습니다."}), 404

    def generate():
        q = _jobs[job_id]["queue"]
        while True:
            try:
                event = q.get(timeout=60)
            except queue.Empty:
                yield "data: {\"type\":\"heartbeat\"}\n\n"
                continue

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


# ---------------------------------------------------------------------------
# 완성 파일 다운로드
# ---------------------------------------------------------------------------

@app.route("/download/<job_id>")
def download(job_id):
    if job_id not in _jobs:
        return jsonify({"error": "잡을 찾을 수 없습니다."}), 404

    output_path = _jobs[job_id].get("output_path")
    if not output_path or not os.path.isfile(output_path):
        return jsonify({"error": "아직 처리가 완료되지 않았습니다."}), 404

    return send_file(
        output_path,
        as_attachment=True,
        download_name=os.path.basename(output_path),
        mimetype="audio/wav",
    )


# ---------------------------------------------------------------------------
# 진입점
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 50)
    print("  Suno AI 마스터링 웹 UI 시작")
    print("  브라우저에서 열기 → http://localhost:5000")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
