"""Jerarquía de excepciones de dominio para el sistema experto.

Separar las excepciones de dominio de las excepciones crudas de `clipspy`
permite que las capas superiores (router, tests) razonen en términos del
negocio ("no hubo recomendación viable", "falló el motor") en vez de
excepciones genéricas de una librería C envuelta en Python.
"""

from __future__ import annotations


class ClipsEngineError(Exception):
    """Excepción base para cualquier error relacionado con el motor de reglas CLIPS.

    Attributes:
        context: Información adicional para diagnóstico (nunca datos sensibles),
            útil para logging estructurado y para depuración.
    """

    def __init__(self, message: str, *, context: dict | None = None) -> None:
        self.context = context or {}
        super().__init__(message)


class ClipsLoadError(ClipsEngineError):
    """Se produjo un fallo al cargar el archivo `.clp` de reglas en el entorno CLIPS.

    Típicamente indica un error de sintaxis en `reglas.clp` o una ruta inválida
    configurada en `Settings.clips_rules_path`. Es un error fatal de arranque.
    """


class ClipsAssertError(ClipsEngineError):
    """Se produjo un fallo al insertar (assert) un hecho en el entorno CLIPS.

    Suele indicar un desajuste entre el payload recibido y los slots/tipos
    esperados por el deftemplate `mediciones-zona`.
    """


class SinRecomendacionError(ClipsEngineError):
    """El motor CLIPS ejecutó correctamente pero ninguna regla de Capa 2 disparó
    una recomendación de tecnología.

    Este es un **resultado válido del dominio** (ninguna tecnología resultó
    viable con los parámetros suministrados por el cliente), no un bug del
    sistema. El router HTTP debe capturarla y traducirla en una respuesta
    `200 OK` con una lista de recomendaciones vacía, nunca en un error `500`.

    Attributes:
        viabilidades: Snapshot de los niveles de viabilidad por recurso al
            momento en que se determinó que no había recomendación, útil
            para que el cliente entienda por qué no hubo resultado.
        demanda: Nivel de demanda (MTF) clasificado, si se logró determinar.
    """

    def __init__(
        self,
        message: str,
        *,
        viabilidades: dict[str, str] | None = None,
        demanda: str | None = None,
    ) -> None:
        self.viabilidades = viabilidades or {}
        self.demanda = demanda
        super().__init__(message, context={"viabilidades": self.viabilidades, "demanda": demanda})
