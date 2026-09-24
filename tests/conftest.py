"""Fixtures compartidas para los tests del backend."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from core.config import settings
from main import app
from services.clips_service import SistemaExpertoService


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """Cliente HTTP de pruebas contra la app FastAPI completa.

    Usar `with TestClient(app) as c` dispara los eventos de `lifespan`
    (incluida la carga del motor CLIPS en `app.state.service`), tal como
    ocurriría en un despliegue real con `uvicorn`.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def servicio() -> SistemaExpertoService:
    """Instancia independiente de `SistemaExpertoService`, para tests unitarios
    del motor de reglas que no necesitan pasar por la capa HTTP.
    """
    return SistemaExpertoService(clips_rules_path=settings.clips_rules_path)
