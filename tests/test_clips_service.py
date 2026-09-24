"""Tests unitarios del motor de reglas CLIPS (`SistemaExpertoService`),
basados en casos de estudio reales del proyecto de tesis.
"""

from __future__ import annotations

import pytest

from core.exceptions import SinRecomendacionError
from schemas.experto import EvaluacionRequest


def _req(**overrides: object) -> EvaluacionRequest:
    """Construye un `EvaluacionRequest` con valores base "neutros" (todo en
    niveles bajos/inviables) que los tests sobreescriben según el caso.
    """
    base: dict[str, object] = dict(
        id_comunidad="test",
        radiacion=0.0,
        velocidad_viento=0.0,
        hay_curso_agua="no",
        caudal=0.0,
        salto_neto=0.0,
        masa_estiercol=0.0,
        consumo_diario=0.0,
        presupuesto="bajo",
    )
    base.update(overrides)
    return EvaluacionRequest(**base)  # type: ignore[arg-type]


def test_caso_a_puno_solar_alta_sin_agua_presupuesto_bajo(servicio):
    """Caso A (Puno): radiación alta, sin curso de agua, presupuesto bajo."""
    request = _req(
        id_comunidad="Puno-A",
        radiacion=6.1,
        velocidad_viento=1.0,
        hay_curso_agua="no",
        masa_estiercol=2.0,
        consumo_diario=800.0,
        presupuesto="bajo",
    )

    response = servicio.evaluar(request)
    tecnologias = {r.tecnologia for r in response.recomendaciones}

    assert "Panel Solar Basico (SHS)" in tecnologias
    assert response.viabilidades["solar"] == "alta"


def test_caso_b_junin_hidraulica_media_demanda_alta_presupuesto_medio(servicio):
    """Caso B (Junín): hidráulica media, demanda alto_productivo, presupuesto medio."""
    request = _req(
        id_comunidad="Junin-B",
        radiacion=3.0,
        velocidad_viento=2.0,
        hay_curso_agua="si",
        caudal=50.0,
        salto_neto=10.0,
        masa_estiercol=2.0,
        consumo_diario=4000.0,
        presupuesto="medio",
    )

    response = servicio.evaluar(request)
    tecnologias = {r.tecnologia for r in response.recomendaciones}

    assert "Micro Central Hidraulica Banki-Michell" in tecnologias
    assert response.viabilidades["hidraulica"] == "media"
    assert response.demanda_clasificada == "alto_productivo"


def test_caso_hibrido_san_marcos_solar_eolica_alta_demanda_alta(servicio):
    """Caso híbrido (San Marcos): solar alta + eólica alta + demanda alto_productivo.

    Con presupuesto suficiente, deben dispararse simultáneamente
    recomendaciones monofuente (R19, R21) e híbridas (R27, R30).
    """
    request = _req(
        id_comunidad="San-Marcos-Hibrido",
        radiacion=6.1,
        velocidad_viento=6.5,
        hay_curso_agua="no",
        masa_estiercol=1.0,
        consumo_diario=5000.0,
        presupuesto="alto",
    )

    response = servicio.evaluar(request)
    tecnologias = {r.tecnologia for r in response.recomendaciones}

    # Recomendaciones monofuente
    assert "Sistema Solar Centralizado (Bombeo/Productivo)" in tecnologias
    assert "Sistema Eolico Comunitario con Baterias" in tecnologias
    # Recomendaciones híbridas, disparadas en el mismo ciclo de evaluación
    assert "Sistema Hibrido Solar-Eolico" in tecnologias
    assert "Microrred Hibrida Solar-Eolica con Banco LFP" in tecnologias
    assert len(response.recomendaciones) >= 4


def test_caso_sin_recomendacion_viable(servicio):
    """Caso sin recomendación: todos los recursos en nivel bajo/inviable y
    presupuesto bajo -> ninguna regla de Capa 2 debe dispararse.
    """
    request = _req(
        id_comunidad="Sin-Recomendacion",
        radiacion=1.0,
        velocidad_viento=1.0,
        hay_curso_agua="no",
        masa_estiercol=1.0,
        consumo_diario=300.0,
        presupuesto="bajo",
    )

    with pytest.raises(SinRecomendacionError) as exc_info:
        servicio.evaluar(request)

    assert exc_info.value.viabilidades["solar"] == "baja"
    assert exc_info.value.viabilidades["eolica"] == "inviable"
    assert exc_info.value.viabilidades["hidraulica"] == "inviable"
    assert exc_info.value.viabilidades["biomasa"] == "inviable"


def test_health_check_ok(servicio):
    assert servicio.health_check() is True
