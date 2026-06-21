"""Tests for the dedicated Recollectium WebUI shell."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from recollectium.webui import create_app


def test_webui_static_assets_are_packaged() -> None:
    static_dir = (
        Path(__file__).resolve().parents[1] / "src" / "recollectium" / "webui_static"
    )

    assert (static_dir / "index.html").exists()
    assert (static_dir / "app.js").exists()
    assert (static_dir / "styles.css").exists()


def test_webui_app_serves_shell_and_bootstrap_endpoints() -> None:
    client = TestClient(create_app(host="127.0.0.1", port=8766))

    root_response = client.get("/")
    assert root_response.status_code == 200
    assert "Recollectium WebUI" in root_response.text

    app_js = client.get("/assets/app.js")
    assert app_js.status_code == 200
    assert "/v1/status" in app_js.text

    health = client.get("/v1/health").json()
    assert health["status"] == "ok"
    assert health["local_first"] is True
    assert health["security"] == {"authentication": "none", "tls": False}
    assert health["endpoints"]["health"].endswith("/v1/health")

    status = client.get("/v1/status").json()
    assert status["status"] == "running"
    assert status["service_type"] == "webui"
    assert status["local_first"] is True
    assert status["security"]["recommended_bind"] == "127.0.0.1"
    assert status["endpoints"]["status"].endswith("/v1/status")

    capabilities = client.get("/v1/capabilities").json()
    assert capabilities["status"] == "ok"
    assert "static-shell" in capabilities["capabilities"]
    assert "/assets/app.js" in capabilities["ui_assets"]
