import os
import sys

from flask import Flask, Response, jsonify, render_template, request
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
from waitress import serve

MAX_REQUEST_BYTES = int(os.environ.get("LRC_MAX_REQUEST_BYTES", 1024 * 1024))
MAX_SEGMENTS = int(os.environ.get("LRC_MAX_SEGMENTS", 5000))
MAX_TEXT_LENGTH = int(os.environ.get("LRC_MAX_TEXT_LENGTH", 1000))
MAX_OUTPUT_BYTES = int(os.environ.get("LRC_MAX_OUTPUT_BYTES", 2 * 1024 * 1024))
SERVER_HOST = os.environ.get("LRC_HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("LRC_PORT", 5000))
SERVER_THREADS = int(os.environ.get("LRC_THREADS", 8))


def resource_path(relative_path):
    """Return a path that works both from source and from a PyInstaller exe."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("static"),
)
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES


@app.errorhandler(RequestEntityTooLarge)
def handle_too_large(error):
    return jsonify({"error": "request body is too large"}), 413


@app.errorhandler(HTTPException)
def handle_http_error(error):
    return jsonify({"error": error.description}), error.code


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    app.logger.exception("Unhandled error")
    return jsonify({"error": "internal server error"}), 500


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download_lrc", methods=["POST"])
def download_lrc():
    data = request.get_json(silent=True) or {}
    segments = data.get("segments")
    if not isinstance(segments, list):
        return jsonify({"error": "segments must be a list"}), 400
    if len(segments) > MAX_SEGMENTS:
        return jsonify({"error": f"segments must contain {MAX_SEGMENTS} items or fewer"}), 400

    lines = []
    for idx, segment in enumerate(segments):
        if not isinstance(segment, dict):
            return jsonify({"error": f"segment {idx} must be an object"}), 400

        try:
            start = float(segment.get("start", 0))
        except (TypeError, ValueError):
            return jsonify({"error": f"segment {idx} has an invalid start time"}), 400

        text = segment.get("text", "")
        if not isinstance(text, str):
            return jsonify({"error": f"segment {idx} has invalid text"}), 400
        if len(text) > MAX_TEXT_LENGTH:
            return jsonify({"error": f"segment {idx} text is too long"}), 400

        start = max(0.0, start)
        tag = f"[{int(start // 60):02d}:{start % 60:06.3f}]"
        lines.append(f"{tag}{text}")

    body = "\n".join(lines)
    if len(body.encode("utf-8")) > MAX_OUTPUT_BYTES:
        return jsonify({"error": "LRC output is too large"}), 400

    return Response(
        body,
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=lyrics.lrc"},
    )


if __name__ == "__main__":
    print(f"LRC Tagger 시작 중... http://{SERVER_HOST}:{SERVER_PORT}")
    serve(app, host=SERVER_HOST, port=SERVER_PORT, threads=SERVER_THREADS)
