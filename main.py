"""Punto de entrada de la aplicación FastAPI del sistema experto de energías
renovables off-grid.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.logging_config import setup_logging
from routers.api import router as api_router
from schemas.experto import ErrorResponse
from services.clips_service import SistemaExpertoService

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Instancia el `SistemaExpertoService` (y carga el motor CLIPS) una única
    vez al arrancar la aplicación, guardándolo en `app.state` para que los
    endpoints lo reutilicen vía `Depends`, en vez de recrearlo por request.
    """
    logger.info("Iniciando sistema experto: cargando motor CLIPS...")
    app.state.service = SistemaExpertoService(clips_rules_path=settings.clips_rules_path)
    logger.info("Motor CLIPS listo. Aplicación iniciada.")
    yield
    logger.info("Apagando aplicación.")


app = FastAPI(
    title="Sistema Experto de Energías Renovables Off-Grid",
    version="1.0.0",
    description=(
        "API para la selección de fuentes de energía renovable (solar fotovoltaica, "
        "eólica de pequeña escala, micro/mini hidráulica run-of-river y biodigestión "
        "anaeróbica, incluyendo configuraciones híbridas) para comunidades rurales "
        "off-grid, basada en un motor de reglas CLIPS (forward chaining, algoritmo "
        "Rete, resolución de conflictos Depth/LIFO)."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Red de seguridad final: cualquier excepción no capturada explícitamente
    en un endpoint se traduce en un 500 con la forma consistente de `ErrorResponse`,
    nunca en un stacktrace crudo expuesto al cliente.
    """
    logger.error("Excepción no controlada en %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            detail="Error interno no controlado.", error_code="INTERNAL_ERROR"
        ).model_dump(),
    )


@app.get(
    "/health", tags=["health"], summary="Verifica que el motor CLIPS esté cargado y operativo."
)
def health() -> dict[str, str]:
    ok = app.state.service.health_check()
    return {"status": "ok" if ok else "degraded"}
