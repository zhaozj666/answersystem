from __future__ import annotations

__version__ = "3.1.0"

import contextvars
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

_request_var: contextvars.ContextVar["_Request"] = contextvars.ContextVar("request")


class _Request:
    def __init__(self, handler: BaseHTTPRequestHandler):
        self._handler = handler

    def get_json(self, silent: bool = False):
        length = int(self._handler.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return None
        raw = self._handler.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            if silent:
                return None
            raise


class _RequestProxy:
    def __getattr__(self, item):
        req = _request_var.get(None)
        if req is None:
            raise RuntimeError("request context unavailable")
        return getattr(req, item)


request = _RequestProxy()


class JsonResponse:
    def __init__(self, data: Any, status_code: int = 200):
        self.data = data
        self.status_code = status_code


def jsonify(data: Any):
    return JsonResponse(data, 200)


def render_template(template_name: str, **context: Any):
    app = _current_app.get(None)
    if app is None:
        raise RuntimeError("app context unavailable")
    path = Path(app.template_folder) / template_name
    html = path.read_text(encoding="utf-8")
    for key, value in context.items():
        html = html.replace("{{ " + key + " }}", str(value))
    return html


_current_app: contextvars.ContextVar["Flask"] = contextvars.ContextVar("current_app")


class Flask:
    def __init__(self, import_name: str, template_folder: str | None = None, static_folder: str | None = None):
        self.import_name = import_name
        self.template_folder = template_folder or "templates"
        self.static_folder = static_folder or "static"
        self._routes: Dict[Tuple[str, str], Callable[..., Any]] = {}

    def route(self, path: str, methods=None):
        methods = methods or ["GET"]

        def decorator(func):
            for method in methods:
                self._routes[(method.upper(), path)] = func
            return func

        return decorator

    def get(self, path: str):
        return self.route(path, methods=["GET"])

    def post(self, path: str):
        return self.route(path, methods=["POST"])

    def run(self, host: str = "127.0.0.1", port: int = 5000, debug: bool = False):
        app = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self._handle("GET")

            def do_POST(self):
                self._handle("POST")

            def log_message(self, format, *args):
                return

            def _handle(self, method: str):
                path = self.path.split("?", 1)[0]

                if method == "GET" and path.startswith("/static/"):
                    static_path = Path(app.static_folder) / path.replace("/static/", "", 1)
                    if static_path.exists() and static_path.is_file():
                        body = static_path.read_bytes()
                        ctype = "text/css" if static_path.suffix == ".css" else "application/octet-stream"
                        self.send_response(HTTPStatus.OK)
                        self.send_header("Content-Type", ctype)
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                        return

                fn = app._routes.get((method, path))
                if fn is None:
                    self.send_response(HTTPStatus.NOT_FOUND)
                    self.end_headers()
                    self.wfile.write(b"Not Found")
                    return

                token_req = _request_var.set(_Request(self))
                token_app = _current_app.set(app)
                try:
                    result = fn()
                finally:
                    _request_var.reset(token_req)
                    _current_app.reset(token_app)

                status_code = 200
                body: bytes
                content_type = "text/plain; charset=utf-8"

                if isinstance(result, tuple) and len(result) == 2:
                    payload, status_code = result
                    if isinstance(payload, JsonResponse):
                        payload = payload.data
                    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                    content_type = "application/json; charset=utf-8"
                elif isinstance(result, JsonResponse):
                    status_code = result.status_code
                    body = json.dumps(result.data, ensure_ascii=False).encode("utf-8")
                    content_type = "application/json; charset=utf-8"
                elif isinstance(result, (dict, list)):
                    body = json.dumps(result, ensure_ascii=False).encode("utf-8")
                    content_type = "application/json; charset=utf-8"
                else:
                    body = str(result).encode("utf-8")
                    if str(result).lstrip().startswith("<!doctype html"):
                        content_type = "text/html; charset=utf-8"

                self.send_response(status_code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer((host, port), Handler)
        server.serve_forever()
