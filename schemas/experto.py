"""Esquemas Pydantic v2 para la API del sistema experto."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvaluacionRequest(BaseModel):
    """Payload de entrada: mediciones de una zona/comunidad rural a evaluar."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
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
        },
    )

    id_comunidad: str = Field(
        min_length=1,
        max_length=100,
        description="Identificador único de la comunidad o zona evaluada.",
    )
    radiacion: float = Field(ge=0, le=10, description="Radiación solar promedio, en kWh/m2/día.")
    velocidad_viento: float = Field(
        ge=0, le=30, description="Velocidad del viento a 10-30m de altura, en m/s."
    )
    hay_curso_agua: Literal["si", "no"] = Field(
        description="Indica si existe un curso de agua aprovechable en la zona."
    )
    caudal: float = Field(
        ge=0, description="Caudal disponible (Q), en l/s. Debe ser 0.0 si hay_curso_agua='no'."
    )
    salto_neto: float = Field(
        ge=0,
        description="Salto neto disponible (H), en metros. Debe ser 0.0 si hay_curso_agua='no'.",
    )
    masa_estiercol: float = Field(
        ge=0, description="Masa de estiércol disponible por día, en kg/día."
    )
    consumo_diario: float = Field(
        ge=0, description="Consumo energético diario estimado, en Wh/día."
    )
    presupuesto: Literal["bajo", "medio", "alto"] = Field(
        description="Nivel de presupuesto disponible para la instalación."
    )

    @model_validator(mode="after")
    def validar_coherencia_hidraulica(self) -> EvaluacionRequest:
        """Si no hay curso de agua, `caudal` y `salto_neto` deben ser exactamente 0.0.

        Se rechaza explícitamente (en vez de silenciar/forzar a 0) un payload
        contradictorio donde el cliente afirma `hay_curso_agua='no'` pero
        envía mediciones hidráulicas distintas de cero, ya que eso suele
        indicar un error de origen de datos que el cliente debe corregir.
        """
        if self.hay_curso_agua == "no" and (self.caudal != 0.0 or self.salto_neto != 0.0):
            raise ValueError(
                "Datos contradictorios: hay_curso_agua='no' implica ausencia de curso de "
                "agua aprovechable, por lo que 'caudal' y 'salto_neto' deben enviarse en "
                "0.0. Verifique el payload; si sí existe un curso de agua, envíe "
                "hay_curso_agua='si' junto con las mediciones correspondientes."
            )
        return self


class RecomendacionItem(BaseModel):
    """Una recomendación tecnológica individual, con trazabilidad a la regla CLIPS que la originó."""

    tecnologia: str = Field(description="Nombre de la tecnología/configuración recomendada.")
    justificacion: str = Field(
        description="Explicación en lenguaje natural de por qué se recomienda."
    )
    regla_origen: str = Field(
        description="Código de la regla CLIPS de Capa 2 que disparó esta recomendación (p. ej. 'R23')."
    )


class EvaluacionResponse(BaseModel):
    """Resultado de evaluar una zona: cero, una o varias recomendaciones simultáneas."""

    id_comunidad: str = Field(
        description="Identificador de la comunidad evaluada (eco del request)."
    )
    recomendaciones: list[RecomendacionItem] = Field(
        description="Lista de recomendaciones tecnológicas. Puede estar vacía si ninguna tecnología es viable."
    )
    viabilidades: dict[str, str] = Field(
        description="Snapshot de la viabilidad calculada por recurso (solar, eolica, hidraulica, biomasa), "
        "útil para que el frontend explique el razonamiento del motor."
    )
    demanda_clasificada: str = Field(
        description="Nivel de demanda según el Multi-Tier Framework (bajo_basico, medio_transicion, alto_productivo)."
    )


class ErrorResponse(BaseModel):
    """Forma consistente de las respuestas de error de la API."""

    detail: str = Field(description="Mensaje descriptivo del error.")
    error_code: str = Field(
        description="Código corto y estable para manejo programático del error."
    )
