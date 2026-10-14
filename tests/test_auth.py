
from unittest.mock import Mock, patch

import pytest
import requests

from src.auth import MedicloudAuthError, get_access_token
from src.config import Settings


@pytest.fixture
def settings():
    return Settings(
        base_url="https://example.com",
        app_id="test-id",
        app_key="test-key",
        resource="test-resource",
        api_version="1",
    )


def test_autenticacion_correcta(settings):
    response = Mock()
    response.json.return_value = {
        "status": "success",
        "token_type": "Bearer",
        "access_token": "token-ficticio",
    }

    with patch("src.auth.requests.Session") as session_class:
        session = session_class.return_value
        session.post.return_value = response

        token = get_access_token(settings)

        assert token == "token-ficticio"
        session.post.assert_called_once()
        session.close.assert_called_once()


def test_respuesta_sin_token(settings):
    response = Mock()
    response.json.return_value = {"status": "success"}

    with patch("src.auth.requests.Session") as session_class:
        session = session_class.return_value
        session.post.return_value = response

        with pytest.raises(MedicloudAuthError):
            get_access_token(settings)

        session.close.assert_called_once()


def test_error_de_conexion(settings):
    with patch("src.auth.requests.Session") as session_class:
        session = session_class.return_value
        session.post.side_effect = requests.ConnectionError(
            "connection failed"
        )

        with pytest.raises(MedicloudAuthError):
            get_access_token(settings)

        session.close.assert_called_once()


def test_configuracion_reintentos(settings):
    with patch("src.auth.requests.Session") as session_class:
        session = session_class.return_value
        session.post.return_value.json.return_value = {
            "status": "success",
            "access_token": "token-ficticio",
        }

        get_access_token(settings)

        adapter = session.mount.call_args.args[1]
        retry = adapter.max_retries

        assert retry.total == 2
        assert retry.read == 0
        assert "POST" in retry.allowed_methods
        assert 503 in retry.status_forcelist
        assert 401 not in retry.status_forcelist




from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread


def test_reintentos_http_503(settings):
    class Handler(BaseHTTPRequestHandler):
        intentos = 0

        def do_POST(self):
            Handler.intentos += 1

            if Handler.intentos < 3:
                self.send_response(503)
                self.end_headers()
                return

            body = (
                b'{"status":"success",'
                b'"access_token":"token-ficticio"}'
            )

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        local_settings = Settings(
            base_url=f"http://127.0.0.1:{server.server_port}",
            app_id=settings.app_id,
            app_key=settings.app_key,
            resource=settings.resource,
            api_version=settings.api_version,
        )

        token = get_access_token(local_settings)

        assert token == "token-ficticio"
        assert Handler.intentos == 3

    finally:
        server.shutdown()
        server.server_close()
        thread.join()