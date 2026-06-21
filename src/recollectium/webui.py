"""FastAPI local WebUI shell for Recollectium Core."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from recollectium import __version__
from recollectium.config import RecollectiumConfig
from recollectium.logging import setup_logging
from recollectium.service_contract import SERVICE_API_PREFIX

WEBUI_SERVICE_TYPE = "webui"
WEBUI_DEFAULT_HOST = "127.0.0.1"
WEBUI_DEFAULT_PORT = 8766
WEBUI_TITLE = "Recollectium WebUI"
WEBUI_VERSION = "1"
WEBUI_LOCAL_FIRST = True
WEBUI_AUTHENTICATION = "none"
WEBUI_TLS = False
WEBUI_STATIC_DIR = Path(__file__).with_name("webui_static")


def _webui_urls(host: str, port: int) -> dict[str, str]:
    base = f"http://{host}:{port}"
    return {
        "base": base,
        "health": f"{base}{SERVICE_API_PREFIX}/health",
        "status": f"{base}{SERVICE_API_PREFIX}/status",
        "version": f"{base}{SERVICE_API_PREFIX}/version",
        "capabilities": f"{base}{SERVICE_API_PREFIX}/capabilities",
    }


def webui_capabilities_payload(host: str, port: int) -> dict[str, Any]:
    urls = _webui_urls(host, port)
    return {
        "status": "ok",
        "surface": WEBUI_TITLE,
        "service_type": WEBUI_SERVICE_TYPE,
        "version": __version__,
        "webui_version": WEBUI_VERSION,
        "local_first": WEBUI_LOCAL_FIRST,
        "security": {
            "authentication": WEBUI_AUTHENTICATION,
            "tls": WEBUI_TLS,
            "recommended_bind": WEBUI_DEFAULT_HOST,
            "warning": (
                "Recollectium WebUI is localhost-first and unauthenticated in v1. "
                "Do not bind it to a public interface without private-network controls."
            ),
        },
        "capabilities": [
            "health",
            "status",
            "capabilities",
            "static-shell",
        ],
        "endpoints": urls,
        "ui_assets": ["/", "/assets/app.js", "/assets/styles.css"],
    }


def webui_health_payload(host: str, port: int) -> dict[str, Any]:
    urls = _webui_urls(host, port)
    return {
        "status": "ok",
        "ready": True,
        "surface": WEBUI_TITLE,
        "service_type": WEBUI_SERVICE_TYPE,
        "version": __version__,
        "webui_version": WEBUI_VERSION,
        "local_first": WEBUI_LOCAL_FIRST,
        "security": {
            "authentication": WEBUI_AUTHENTICATION,
            "tls": WEBUI_TLS,
        },
        "endpoints": urls,
    }


def webui_status_payload(host: str, port: int) -> dict[str, Any]:
    urls = _webui_urls(host, port)
    return {
        "status": "running",
        "surface": WEBUI_TITLE,
        "service_type": WEBUI_SERVICE_TYPE,
        "version": __version__,
        "webui_version": WEBUI_VERSION,
        "local_first": WEBUI_LOCAL_FIRST,
        "security": {
            "authentication": WEBUI_AUTHENTICATION,
            "tls": WEBUI_TLS,
            "recommended_bind": WEBUI_DEFAULT_HOST,
            "warning": (
                "Recollectium WebUI is localhost-first and unauthenticated in v1."
            ),
        },
        "endpoints": urls,
        "capabilities": [
            "health",
            "status",
            "capabilities",
            "static-shell",
        ],
        "ui_assets": ["/", "/assets/app.js", "/assets/styles.css"],
    }


def create_app(
    *,
    host: str = WEBUI_DEFAULT_HOST,
    port: int = WEBUI_DEFAULT_PORT,
) -> FastAPI:
    app = FastAPI(
        title=WEBUI_TITLE,
        version=WEBUI_VERSION,
        description=(
            "Local-first Recollectium WebUI shell. In v1, this surface has no "
            "authentication and is intended for localhost use only."
        ),
    )
    app.state.webui_host = host
    app.state.webui_port = port

    if WEBUI_STATIC_DIR.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(WEBUI_STATIC_DIR)),
            name="webui-assets",
        )

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return HTMLResponse(
            (WEBUI_STATIC_DIR / "index.html").read_text(encoding="utf-8")
        )

    @app.get(f"{SERVICE_API_PREFIX}/health")
    def health() -> JSONResponse:
        return JSONResponse(webui_health_payload(host, port))

    @app.get(f"{SERVICE_API_PREFIX}/status")
    def status() -> JSONResponse:
        return JSONResponse(webui_status_payload(host, port))

    @app.get(f"{SERVICE_API_PREFIX}/version")
    def version() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "surface": WEBUI_TITLE,
                "service_type": WEBUI_SERVICE_TYPE,
                "version": __version__,
                "webui_version": WEBUI_VERSION,
            }
        )

    @app.get(f"{SERVICE_API_PREFIX}/capabilities")
    def capabilities() -> JSONResponse:
        return JSONResponse(webui_capabilities_payload(host, port))

    return app


def run_webui(
    *,
    host: str | None = None,
    port: int | None = None,
    config_path: str | Path | None = None,
    log_level: str | None = None,
    foreground_stderr_logs: bool = False,
) -> None:
    import uvicorn

    cfg = RecollectiumConfig(config_path, log_level=log_level)
    effective_webui = cfg.effective_config.get("webui", {})
    resolved_host = str(host or effective_webui.get("host", WEBUI_DEFAULT_HOST))
    resolved_port = int(port or effective_webui.get("port", WEBUI_DEFAULT_PORT))
    if foreground_stderr_logs:
        effective_level = str(cfg.effective_config["logging"]["level"])
        setup_logging(
            cfg,
            stderr_level=effective_level,
            library_log_level=effective_level,
        )

    app = create_app(host=resolved_host, port=resolved_port)
    uvicorn.run(
        app,
        host=resolved_host,
        port=resolved_port,
        log_level=str(cfg.effective_config["logging"]["level"]),
        log_config=None,
    )
