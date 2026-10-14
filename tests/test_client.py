from datetime import date

import pytest

from src.client import get_cuestionarios


@pytest.mark.parametrize(
    "inicio,fin",
    [
        (date(2026, 10, 10), date(2026, 10, 9)),
        (date(2026, 10, 1), date(2026, 10, 12)),
    ],
)
def test_rechaza_intervalos_invalidos(inicio, fin):
    with pytest.raises(ValueError):
        get_cuestionarios(
            settings=Settings(
                base_url="https://example.com",
                app_id="test-id",
                app_key="test-key",
                resource="test-resource",
                api_version="1",
            ),
            token="token-ficticio",
            fecha_inicial=inicio,
            fecha_final=fin,
        )

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from src.config import Settings


def test_reintentos_extraccion_http_503():
    class Handler(BaseHTTPRequestHandler):
        intentos = 0

        def do_POST(self):
            Handler.intentos += 1

            if Handler.intentos < 3:
                self.send_response(503)
                self.end_headers()
                return

            body = (
                b'{"status":"success","datos":'
                b'[{"id":123,"fecha":"2026-10-01"}]}'
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
        settings = Settings(
            base_url=f"http://127.0.0.1:{server.server_port}",
            app_id="test-id",
            app_key="test-key",
            resource="test-resource",
            api_version="1",
        )

        datos = get_cuestionarios(
            settings=settings,
            token="token-ficticio",
            fecha_inicial=date(2026, 10, 1),
            fecha_final=date(2026, 10, 10),
        )

        assert Handler.intentos == 3
        assert len(datos) == 1
        assert datos[0]["id"] == 123

    finally:
        server.shutdown()
        server.server_close()
        thread.join()