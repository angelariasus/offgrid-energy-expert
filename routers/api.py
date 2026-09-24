"""Endpoints de la API RESTful del sistema experto de energías renovables off-grid."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from core.exceptions import ClipsEngineError, SinRecomendacionError
from core.reglas_metadata import REGLAS_METADATA
from schemas.experto import ErrorResponse, EvaluacionRequest, EvaluacionResponse
from services.clips_service import SistemaExpertoService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_service(request: Request) -> SistemaExpertoService:
    """Inyecta la instancia única de `SistemaExpertoService` creada en el `lifespan` de la app.

    Se obtiene desde `app.state` (poblado una sola vez al arrancar) en vez de
    instanciarse dentro del endpoint, evitando recargar el motor CLIPS en
    cada request.
    """
    return request.app.state.service


@router.post(
    "/evaluar-zona",
    response_model=EvaluacionResponse,
    responses={
        422: {"model": ErrorResponse, "description": "Payload inválido (validación de Pydantic)."},
        500: {"model": ErrorResponse, "description": "Error interno del motor CLIPS."},
    },
    summary="Evalúa una zona rural y devuelve las tecnologías de energía renovable recomendadas.",
)
def evaluar_zona(
    payload: EvaluacionRequest,
    service: SistemaExpertoService = Depends(get_service),
) -> EvaluacionResponse | JSONResponse:
    """Ejecuta el motor de reglas CLIPS sobre las mediciones de una zona.

    Puede devolver cero, una o varias recomendaciones simultáneas (por
    ejemplo, una recomendación monofuente y una híbrida a la vez), ya que
    varias reglas de Capa 2 pueden dispararse para el mismo caso.

    - Si ninguna tecnología resulta viable, responde `200 OK` con
      `recomendaciones: []` (no es un error del sistema).
    - Si el motor CLIPS falla de forma inesperada, responde `500` con un
      `ErrorResponse`.
    """
    try:
        return service.evaluar(payload)
    except SinRecomendacionError as exc:
        logger.info(
            "Evaluación sin recomendaciones viables para '%s': %s", payload.id_comunidad, exc
        )
        return EvaluacionResponse(
            id_comunidad=payload.id_comunidad,
            recomendaciones=[],
            viabilidades=exc.viabilidades,
            demanda_clasificada=exc.demanda or "desconocida",
        )
    except ClipsEngineError as exc:
        logger.error(
            "Error del motor CLIPS evaluando '%s': %s", payload.id_comunidad, exc, exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(detail=str(exc), error_code="CLIPS_ENGINE_ERROR").model_dump(),
        )


@router.get(
    "/reglas",
    summary="Devuelve la metadata de las 30 reglas del sistema experto (trazabilidad/explicabilidad).",
)
def listar_reglas() -> list[dict[str, object]]:
    """Expone la base de reglas (R01-R30) como datos, para que el frontend
    construya una vista de auditoría sin duplicar el texto de las reglas."""
    return REGLAS_METADATA
