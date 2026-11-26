"""Configuración común de las pruebas.

Bloquea la red real de ``httpx`` (la que usa ElevenLabs) en todas las pruebas:
si una prueba intentara llamar a ElevenLabs de verdad, falla en vez de gastar
créditos (RNF-06). Los transportes falsos (``httpx.MockTransport``) siguen
funcionando, porque no pasan por ``HTTPTransport``.
"""

import httpx
import pytest


@pytest.fixture(autouse=True)
def sin_red_real(monkeypatch):
    def bloquear(self, request):
        raise AssertionError(f"Una prueba intentó salir a internet: {request.url.host}")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", bloquear)
