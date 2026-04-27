from __future__ import annotations

import os
from functools import wraps
from pathlib import Path
from typing import Callable

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS

try:
    from .services.auth_service import AuthError, AuthService
    from .services.history_service import HistoryService
    from .services.index_service import IndexService
    from .services.qa_service import QAService
    from .services.settings_service import SettingsService
except ImportError:  # pragma: no cover
    from services.auth_service import AuthError, AuthService
    from services.history_service import HistoryService
    from services.index_service import IndexService
    from services.qa_service import QAService
    from services.settings_service import SettingsService


def create_app(
    base_dir: Path | None = None,
    docs_dir: Path | None = None,
    settings_path: Path | None = None,
    accounts_path: Path | None = None,
    history_path: Path | None = None,
    testing: bool = False,
) -> Flask:
    base_dir = (base_dir or Path(__file__).resolve().parent.parent).resolve()
    frontend_dir = base_dir / "frontend"
    docs_dir = docs_dir or (base_dir / "docs" / "policies")
    settings_path = settings_path or (base_dir / "runtime" / "model_settings.json")
    accounts_path = accounts_path or (base_dir / "runtime" / "accounts.json")
    history_path = history_path or (base_dir / "runtime" / "history.json")

    app = Flask(__name__, static_folder=str(frontend_dir), static_url_path="")
    app.config["SECRET_KEY"] = os.environ.get("APP_SECRET_KEY", "answer-system-dev-secret")
    app.config["TESTING"] = testing
    CORS(app, supports_credentials=True)

    docs_dir.mkdir(parents=True, exist_ok=True)

    app.index_service = IndexService(docs_dir)
    app.settings_service = SettingsService(settings_path)
    app.auth_service = AuthService(accounts_path)
    app.history_service = HistoryService(history_path)
    app.qa_service = QAService(app.index_service)

    def current_user():
        phone = session.get("phone")
        if not phone:
            return None
        return app.auth_service.get_account(str(phone))

    def error(message: str, status_code: int):
        return jsonify({"error": message}), status_code

    def require_login(view: Callable):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                return error("请先登录。", 401)
            return view(user, *args, **kwargs)

        return wrapped

    def require_admin(view: Callable):
        @require_login
        @wraps(view)
        def wrapped(user, *args, **kwargs):
            if user["role"] != "admin":
                return error("仅管理员可访问该功能。", 403)
            return view(user, *args, **kwargs)

        return wrapped

    @app.get("/")
    def root_page():
        return send_from_directory(str(frontend_dir), "index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/api/auth/login")
    def login():
        payload = request.get_json(silent=True) or {}
        phone = str(payload.get("phone") or "").strip()
        password = str(payload.get("password") or "")
        account = app.auth_service.authenticate(phone, password)
        if not account:
            return error("手机号或密码错误。", 401)
        session["phone"] = account["phone"]
        return jsonify({"user": account})

    @app.post("/api/auth/logout")
    def logout():
        session.clear()
        return jsonify({"ok": True})

    @app.get("/api/auth/session")
    def auth_session():
        user = current_user()
        return jsonify({"authenticated": bool(user), "user": user})

    @app.get("/api/me")
    @require_login
    def me(user):
        return jsonify({"user": user})

    @app.post("/api/me/profile")
    @require_login
    def update_profile(user):
        payload = request.get_json(silent=True) or {}
        new_phone = str(payload.get("phone") or "").strip()
        try:
            updated = app.auth_service.update_profile(str(user["phone"]), new_phone)
            app.history_service.migrate_phone(str(user["phone"]), str(updated["phone"]))
        except AuthError as exc:
            return error(str(exc), 400)
        session["phone"] = updated["phone"]
        return jsonify({"user": updated})

    @app.post("/api/me/password")
    @require_login
    def update_password(user):
        payload = request.get_json(silent=True) or {}
        current_password = str(payload.get("current_password") or "")
        new_password = str(payload.get("new_password") or "")
        if not app.auth_service.verify_password(str(user["phone"]), current_password):
            return error("当前密码不正确。", 400)
        try:
            app.auth_service.update_password(str(user["phone"]), new_password)
        except AuthError as exc:
            return error(str(exc), 400)
        return jsonify({"ok": True})

    @app.get("/api/history")
    @require_login
    def history(user):
        items = app.history_service.list_entries(str(user["phone"]))
        return jsonify({"items": items})

    @app.get("/api/status")
    @require_admin
    def status(user):
        return jsonify(app.index_service.status())

    @app.post("/api/reindex")
    @require_admin
    def reindex(user):
        result = app.index_service.reindex()
        return jsonify(result)

    @app.get("/api/settings")
    @require_admin
    def get_settings(user):
        return jsonify(app.settings_service.load(mask_secret=True))

    @app.post("/api/settings")
    @require_admin
    def save_settings(user):
        payload = request.get_json(silent=True) or {}
        return jsonify(app.settings_service.save(payload))

    @app.get("/api/admin/accounts")
    @require_admin
    def list_accounts(user):
        return jsonify({"items": app.auth_service.list_accounts()})

    @app.post("/api/admin/accounts")
    @require_admin
    def create_account(user):
        payload = request.get_json(silent=True) or {}
        try:
            account = app.auth_service.create_account(
                str(payload.get("phone") or "").strip(),
                str(payload.get("password") or ""),
                str(payload.get("role") or "user"),
            )
        except AuthError as exc:
            return error(str(exc), 400)
        return jsonify({"account": account})

    @app.post("/api/admin/accounts/password")
    @require_admin
    def reset_account_password(user):
        payload = request.get_json(silent=True) or {}
        phone = str(payload.get("phone") or "").strip()
        new_password = str(payload.get("new_password") or "")
        try:
            account = app.auth_service.update_password(phone, new_password)
        except AuthError as exc:
            return error(str(exc), 400)
        return jsonify({"account": account})

    @app.post("/api/ask")
    @require_login
    def ask(user):
        payload = request.get_json(silent=True) or {}
        question = str(payload.get("question") or "").strip()
        if not question:
            return error("问题不能为空。", 400)

        settings = app.settings_service.load(mask_secret=False)
        result = app.qa_service.ask(question, settings)
        app.history_service.add_entry(
            str(user["phone"]),
            question,
            str(result.get("answer") or ""),
            len(result.get("sources") or []),
        )
        return jsonify(result)

    @app.get("/<path:path>")
    def frontend_assets(path: str):
        asset = frontend_dir / path
        if asset.exists() and asset.is_file():
            return send_from_directory(str(frontend_dir), path)
        return send_from_directory(str(frontend_dir), "index.html")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
