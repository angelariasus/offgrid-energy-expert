"""Servicio de integración con el motor de reglas CLIPS (`clipspy`).

Decisión de diseño: aislamiento de estado entre evaluaciones
--------------------------------------------------------------
`clips.Environment()` mantiene tanto la base de conocimiento (deftemplates y
defrules cargados desde el `.clp`) como la memoria de trabajo (hechos
asertados). Recargar el archivo `.clp` completo (`env.load(...)`) en cada
request sería correcto en términos de aislamiento entre evaluaciones, pero
costoso: implica volver a parsear y compilar la red Rete completa (30 reglas)
en cada petición HTTP.

En su lugar, el archivo `.clp` se carga **una sola vez**, en el constructor
de `SistemaExpertoService`, y cada evaluación llama a `env.reset()` antes de
asertar hechos nuevos. `reset()` en CLIPS limpia la memoria de trabajo
(hechos) y reinicia la agenda de activaciones, pero **no** descarta los
deftemplates/defrules ya compilados. Esto preserva el aislamiento funcional
que necesitamos (cada evaluación arranca desde una memoria de trabajo vacía,
sin hechos residuales de la evaluación anterior) a una fracción del costo de
recargar el archivo. Ese es el trade-off elegido: aislamiento completo entre
requests, sin pagar el costo de recompilar la red Rete en cada llamada.

Concurrencia
------------
`clips.Environment()` no es thread-safe: es un wrapper sobre una librería en
C con estado mutable por entorno. FastAPI/uvicorn puede despachar múltiples
requests concurrentes sobre la misma instancia de `SistemaExpertoService`
(instanciada una única vez en el `lifespan` de `main.py` y guardada en
`app.state`), por lo que todo el ciclo
`reset() -> assert_fact() -> run() -> lectura de hechos` se envuelve en un
`threading.Lock()`. Los endpoints de FastAPI que invocan `evaluar()` se
declaran como funciones síncronas (`def`, no `async def`); FastAPI ejecuta
las funciones síncronas en su threadpool interno, y el `Lock` serializa el
acceso real al `Environment` sin bloquear el event loop de asyncio del
proceso (otras requests que no toquen el motor CLIPS siguen sirviéndose
normalmente mientras una evaluación mantiene el lock).
"""

from __future__ import annotations

import logging
from pathlib import Path
from threading import Lock

import clips

from core.exceptions import (
    ClipsAssertError,
    ClipsEngineError,
    ClipsLoadError,
    SinRecomendacionError,
)
from schemas.experto import EvaluacionRequest, EvaluacionResponse, RecomendacionItem

logger = logging.getLogger(__name__)

_TEMPLATE_MEDICIONES = "mediciones-zona"
_TEMPLATE_VIABILIDAD = "viabilidad-recurso"
_TEMPLATE_DEMANDA = "clasificacion-demanda"
_TEMPLATE_RECOMENDACION = "recomendacion-energetica"

# Mapeo explícito snake_case (Pydantic) -> kebab-case (slots del .clp).
_SLOT_MAPPING: dict[str, str] = {
    "radiacion": "radiacion",
    "velocidad_viento": "velocidad-viento",
    "hay_curso_agua": "hay-curso-agua",
    "caudal": "caudal",
    "salto_neto": "salto-neto",
    "masa_estiercol": "masa-estiercol",
    "consumo_diario": "consumo-diario",
    "presupuesto": "presupuesto",
}

# Slots del deftemplate `mediciones-zona` declarados como SYMBOL en CLIPS.
# clipspy no infiere el tipo CLIPS a partir de un `str` de Python: hay que
# envolver explícitamente estos valores en `clips.Symbol(...)`, o el motor
# los insertará como STRING y las reglas (que hacen pattern-matching contra
# símbolos sin comillas, p. ej. `(hay-curso-agua si)`) nunca matchearán.
_SLOTS_SIMBOLICOS = {"hay-curso-agua", "presupuesto"}


class SistemaExpertoService:
    """Envoltorio de alto nivel sobre el motor CLIPS de selección de energías renovables."""

    def __init__(self, clips_rules_path: str) -> None:
        """Carga el entorno CLIPS una única vez.

        Args:
            clips_rules_path: Ruta (relativa o absoluta) al archivo `.clp`.

        Raises:
            ClipsLoadError: Si el archivo no existe o falla al cargarse.
        """
        self._rules_path = Path(clips_rules_path)
        self._lock = Lock()
        self._env = clips.Environment()
        self._cargar_reglas()

    def _cargar_reglas(self) -> None:
        if not self._rules_path.exists():
            raise ClipsLoadError(
                f"No se encontró el archivo de reglas CLIPS en '{self._rules_path}'.",
                context={"ruta": str(self._rules_path)},
            )
        try:
            self._env.load(str(self._rules_path))
        except Exception as exc:  # clipspy propaga errores del parser C como excepciones genéricas
            raise ClipsLoadError(
                f"Fallo al cargar '{self._rules_path}' en el entorno CLIPS: {exc}",
                context={"ruta": str(self._rules_path)},
            ) from exc
        logger.info(
            "Motor CLIPS cargado correctamente",
            extra={"extra_fields": {"ruta_reglas": str(self._rules_path)}},
        )

    def health_check(self) -> bool:
        """Verifica que el entorno CLIPS siga cargado y operativo.

        Returns:
            `True` si el deftemplate principal está disponible en el entorno.
        """
        try:
            return self._env.find_template(_TEMPLATE_MEDICIONES) is not None
        except Exception:  # cualquier fallo al consultar el entorno = no saludable
            return False

    def evaluar(self, request: EvaluacionRequest) -> EvaluacionResponse:
        """Ejecuta una evaluación completa sobre el motor CLIPS.

        Args:
            request: Mediciones y contexto de la zona a evaluar.

        Returns:
            La respuesta con todas las recomendaciones disparadas (puede ser
            más de una: monofuente e híbrida simultáneamente).

        Raises:
            ClipsAssertError: Si falla la inserción del hecho de entrada.
            ClipsEngineError: Ante cualquier otro fallo inesperado del motor.
            SinRecomendacionError: Si el motor corrió correctamente pero
                ninguna regla de Capa 2 produjo una recomendación (resultado
                válido del dominio, no un error del sistema).
        """
        logger.info(
            "Evaluación recibida",
            extra={
                "extra_fields": {
                    "id_comunidad": request.id_comunidad,
                    "presupuesto": request.presupuesto,
                }
            },
        )

        with self._lock:
            try:
                self._env.reset()
                self._asertar_mediciones(request)
                self._env.run()
            except ClipsAssertError:
                raise
            except Exception as exc:
                raise ClipsEngineError(
                    f"Fallo inesperado del motor CLIPS durante la evaluación de "
                    f"'{request.id_comunidad}': {exc}",
                    context={"id_comunidad": request.id_comunidad},
                ) from exc

            recomendaciones, viabilidades, demanda = self._extraer_resultados()

        if not recomendaciones:
            raise SinRecomendacionError(
                f"Ninguna tecnología resultó viable para '{request.id_comunidad}' con los "
                f"parámetros suministrados. Viabilidades detectadas: {viabilidades}. "
                f"Demanda clasificada: {demanda}.",
                viabilidades=viabilidades,
                demanda=demanda,
            )

        logger.info(
            "Evaluación completada",
            extra={
                "extra_fields": {
                    "id_comunidad": request.id_comunidad,
                    "reglas_disparadas": [r.regla_origen for r in recomendaciones],
                }
            },
        )

        return EvaluacionResponse(
            id_comunidad=request.id_comunidad,
            recomendaciones=recomendaciones,
            viabilidades=viabilidades,
            demanda_clasificada=demanda or "desconocida",
        )

    def _asertar_mediciones(self, request: EvaluacionRequest) -> None:
        """Construye y asevera (`assert_fact`) el hecho `mediciones-zona` a partir del request.

        Debe llamarse siempre bajo `self._lock` y luego de `self._env.reset()`.
        """
        try:
            template = self._env.find_template(_TEMPLATE_MEDICIONES)
            if template is None:
                raise ClipsAssertError(
                    f"El deftemplate '{_TEMPLATE_MEDICIONES}' no existe en el entorno CLIPS cargado."
                )

            slots_clips: dict[str, object] = {}
            payload = request.model_dump(exclude={"id_comunidad"})
            for campo_pydantic, valor in payload.items():
                slot_clips = _SLOT_MAPPING.get(campo_pydantic)
                if slot_clips is None:
                    continue
                if slot_clips in _SLOTS_SIMBOLICOS:
                    slots_clips[slot_clips] = clips.Symbol(str(valor))
                else:
                    slots_clips[slot_clips] = float(valor)

            # `Template.assert_fact(**slots)` es el equivalente clipspy de
            # `(assert (mediciones-zona ...))`. Los slots CLIPS son
            # kebab-case (p. ej. "hay-curso-agua"), que no son identificadores
            # Python válidos; se pasan igualmente vía desempaquetado de un
            # dict (`**slots_clips`), lo cual es válido en Python siempre que
            # la función los capture en un `**kwargs` genérico, como hace
            # `assert_fact`.
            template.assert_fact(**slots_clips)
        except ClipsAssertError:
            raise
        except Exception as exc:
            raise ClipsAssertError(
                f"Fallo al asertar el hecho '{_TEMPLATE_MEDICIONES}' para "
                f"'{request.id_comunidad}': {exc}",
                context={"id_comunidad": request.id_comunidad},
            ) from exc

    def _extraer_resultados(
        self,
    ) -> tuple[list[RecomendacionItem], dict[str, str], str | None]:
        """Recorre la memoria de trabajo tras `run()` y separa los hechos por template."""
        recomendaciones: list[RecomendacionItem] = []
        viabilidades: dict[str, str] = {}
        demanda: str | None = None

        for fact in self._env.facts():
            nombre_template = fact.template.name
            if nombre_template == _TEMPLATE_RECOMENDACION:
                recomendaciones.append(
                    RecomendacionItem(
                        tecnologia=str(fact["tecnologia"]),
                        justificacion=str(fact["justificacion"]),
                        regla_origen=str(fact["regla-origen"]),
                    )
                )
            elif nombre_template == _TEMPLATE_VIABILIDAD:
                viabilidades[str(fact["recurso"])] = str(fact["nivel"])
            elif nombre_template == _TEMPLATE_DEMANDA:
                demanda = str(fact["nivel"])

        return recomendaciones, viabilidades, demanda
