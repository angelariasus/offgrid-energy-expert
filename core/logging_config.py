"""Configuración de logging para el backend.

Elección de `logging` estándar en vez de `structlog`
------------------------------------------------------
Se optó por el módulo `logging` de la librería estándar, con un
`Formatter` JSON propio, en vez de `structlog`. Justificación: el proyecto
ya integra una dependencia "pesada" de por sí (`clipspy`, que embebe el
motor CLIPS en C) y busca mantener la superficie de dependencias mínima.
`logging` estándar se integra sin fricción con los loggers internos de
`uvicorn`/`fastapi` (que también usan `logging`), y un formatter JSON de
~20 líneas cubre el requisito de logging estructurado para producción sin
sumar una dependencia adicional ni una curva de aprendizaje extra para el
equipo académico que mantendrá este proyecto.

Qué se loguea
-------------
- Carga del motor CLIPS al arrancar (o fallo de carga).
- Cada evaluación recibida: solo `id_comunidad` y `presupuesto` (nunca se
  loguean mediciones crudas completas como dato "sensible" de la zona,
  aunque no sean PII, para mantener los logs concisos y auditables).
- Reglas disparadas (códigos `regla-origen`) por cada evaluación exitosa.
- Errores, siempre con `exc_info=True` para incluir el stacktrace completo.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

from core.config import settings


class JSONFormatter(logging.Formatter):
    """Formatter que serializa cada registro de log como una línea JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra_fields = getattr(record, "extra_fields", None)
        if extra_fields:
            payload.update(extra_fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    """Configura el logger raíz según `settings.environment` y `settings.log_level`.

    En `prod` se emite JSON estructurado (una línea por evento, apto para
    recolectores tipo ELK/CloudWatch/Loki). En `dev` se usa un formato de
    texto legible por humanos, más cómodo para desarrollo local.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())

    handler = logging.StreamHandler(sys.stdout)
    if settings.environment == "prod":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root_logger.handlers.clear()
    root_logger.addHandler(handler)
