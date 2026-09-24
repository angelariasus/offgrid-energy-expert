"""Tests de integración contra los endpoints HTTP del sistema experto."""

from __future__ import annotations

from unittest.mock import patch

from core.exceptions import ClipsEngineError

# Payload de ejemplo tomado literalmente de la documentación del proyecto:
# debe activar viabilidad hidráulica=media, biomasa=media, demanda=alto_productivo,
# con recomendaciones que incluyan al menos R23 y R24.
VALID_PAYLOAD = {
    "id_comunidad": "San-Marcos-Test",
    "radiacion": 4.8,
    "velocidad_viento": 1.5,
    "hay_curso_agua": "si",
    "caudal": 75.0,
    "salto_neto": 14.0,
    "masa_estiercol": 6.0,
    "consumo_diario": 4200.0,
    "presupuesto": "medio",
}


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_evaluar_zona_caso_ejemplo_documentacion(client):
    response = client.post("/api/evaluar-zona", json=VALID_PAYLOAD)
    assert response.status_code == 200

    body = response.json()
    tecnologias = {r["tecnologia"] for r in body["recomendaciones"]}

    assert "Micro Central Hidraulica Banki-Michell" in tecnologias  # R23
    assert "Biodigestor Tubular con Invernadero" in tecnologias  # R24
    assert body["viabilidades"]["hidraulica"] == "media"
    assert body["viabilidades"]["biomasa"] == "media"
    assert body["demanda_clasificada"] == "alto_productivo"

    # Trazabilidad: cada recomendación debe traer su regla de origen.
    reglas_origen = {r["regla_origen"] for r in body["recomendaciones"]}
    assert "R23" in reglas_origen
    assert "R24" in reglas_origen


def test_evaluar_zona_payload_invalido_422(client):
    payload_invalido = dict(VALID_PAYLOAD)
    payload_invalido["radiacion"] = -1.0  # viola Field(ge=0)

    response = client.post("/api/evaluar-zona", json=payload_invalido)

    assert response.status_code == 422


def test_evaluar_zona_contradiccion_hidraulica_422(client):
    payload_invalido = dict(VALID_PAYLOAD)
    payload_invalido["hay_curso_agua"] = "no"
    # caudal/salto_neto no se ajustan a 0 -> debe ser rechazado por el model_validator

    response = client.post("/api/evaluar-zona", json=payload_invalido)

    assert response.status_code == 422


def test_evaluar_zona_error_motor_500(client):
    with patch(
        "routers.api.SistemaExpertoService.evaluar",
        side_effect=ClipsEngineError("fallo simulado del motor"),
    ):
        response = client.post("/api/evaluar-zona", json=VALID_PAYLOAD)

    assert response.status_code == 500
    body = response.json()
    assert body["error_code"] == "CLIPS_ENGINE_ERROR"
    assert "fallo simulado del motor" in body["detail"]


def test_evaluar_zona_sin_recomendacion_devuelve_200(client):
    payload = dict(VALID_PAYLOAD)
    payload.update(
        {
            "id_comunidad": "Sin-Recomendacion-API",
            "radiacion": 1.0,
            "velocidad_viento": 1.0,
            "hay_curso_agua": "no",
            "caudal": 0.0,
            "salto_neto": 0.0,
            "masa_estiercol": 1.0,
            "consumo_diario": 300.0,
            "presupuesto": "bajo",
        }
    )

    response = client.post("/api/evaluar-zona", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["recomendaciones"] == []
    assert body["viabilidades"]["solar"] == "baja"


def test_listar_reglas_devuelve_30(client):
    response = client.get("/api/reglas")

    assert response.status_code == 200
    reglas = response.json()
    assert len(reglas) == 30

    codigos_esperados = {f"R{i:02d}" for i in range(1, 31)}
    codigos_obtenidos = {r["codigo"] for r in reglas}
    assert codigos_obtenidos == codigos_esperados

    for regla in reglas:
        assert regla["capa"] in (1, 2)
        assert "descripcion" in regla
        assert "condicion" in regla
