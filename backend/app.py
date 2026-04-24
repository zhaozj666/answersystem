from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from services.index_service import IndexService
from services.qa_service import QAService

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DOCS_DIR = BASE_DIR / "docs" / "policies"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
CORS(app)

index_service = IndexService(DOCS_DIR)
qa_service = QAService(index_service)


@app.get("/")
def root_page():
    return send_from_directory(str(FRONTEND_DIR), "index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/status")
def status():
    return jsonify(index_service.status())


@app.post("/api/reindex")
def reindex():
    result = index_service.reindex()
    return jsonify(result)


@app.post("/api/ask")
def ask():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question 不能为空"}), 400

    result = qa_service.ask(question)
    return jsonify(result)


@app.get("/<path:path>")
def frontend_assets(path: str):
    asset = FRONTEND_DIR / path
    if asset.exists() and asset.is_file():
        return send_from_directory(str(FRONTEND_DIR), path)
    return send_from_directory(str(FRONTEND_DIR), "index.html")


if __name__ == "__main__":
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host="127.0.0.1", port=8000, debug=True)
