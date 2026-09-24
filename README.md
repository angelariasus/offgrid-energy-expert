# Sistema Experto de Energías Renovables Off-Grid — Backend

Backend en **FastAPI** que expone, vía API RESTful, un sistema experto en
**CLIPS** (motor `clipspy`) para la selección de fuentes de energía renovable
off-grid en comunidades rurales (solar fotovoltaica, eólica de pequeña
escala, micro/mini hidráulica *run-of-river*, biodigestión anaeróbica y
configuraciones híbridas).

Proyecto universitario — UNMSM, curso Sistemas Inteligentes.

## Arquitectura

- **Motor de reglas**: `logica/reglas.clp` — 30 reglas (`R01`–`R30`) en 2
  capas de `salience` (Abstracción Técnica → Decisión Tecnológica) más una
  regla de reporte (Capa 3), sobre encadenamiento hacia adelante (algoritmo
  Rete, resolución de conflictos Depth/LIFO).
- **Integración Python↔CLIPS**: `services/clips_service.py`, vía `clipspy`.
  El motor se carga **una sola vez** al arrancar; cada evaluación usa
  `env.reset()` (no recarga el `.clp`) protegido por un `threading.Lock`,
  ya que `clips.Environment` no es thread-safe. El razonamiento completo de
  este trade-off está documentado en el docstring del módulo.
- **API**: `routers/api.py` + `main.py`, con `lifespan` (no `@app.on_event`,
  deprecado) para instanciar el servicio una única vez.
- **Gestión de dependencias**: `pip` clásico (`requirements.txt` /
  `requirements-dev.txt`), no Poetry — ver justificación en `pyproject.toml`.

## Estructura del proyecto

```
offgrid-energy-expert/
├── logica/reglas.clp          # Las 30 reglas CLIPS + regla de reporte
├── core/                      # Config, logging, excepciones, metadata de reglas
├── schemas/experto.py         # Modelos Pydantic v2 (request/response)
├── services/clips_service.py  # Integración con clipspy
├── routers/api.py             # Endpoints /api/*
├── tests/                     # pytest (unitarios + integración)
├── main.py                    # App FastAPI (lifespan, CORS, /health)
├── Dockerfile / docker-compose.yml
└── .github/workflows/ci.yml
```

## Instalación

Requiere Python 3.11+ y un compilador de C (para compilar `clipspy`).

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
# Para desarrollo (incluye ruff y black):
pip install -r requirements-dev.txt

cp .env.example .env             # ajustar valores si es necesario
```

## Variables de entorno (`.env`)

| Variable                | Descripción                                              | Default                          |
|--------------------------|-----------------------------------------------------------|-----------------------------------|
| `CLIPS_RULES_PATH`       | Ruta al archivo `.clp` de reglas                          | `logica/reglas.clp`               |
| `CORS_ALLOWED_ORIGINS`   | Lista JSON de orígenes permitidos por CORS                | `["http://localhost:3000"]`       |
| `LOG_LEVEL`              | Nivel de logging raíz                                     | `INFO`                            |
| `ENVIRONMENT`            | `dev` (logs legibles) o `prod` (logs JSON estructurados)  | `dev`                             |

## Ejecutar en desarrollo

```bash
uvicorn main:app --reload
```

- Documentación interactiva (Swagger): http://localhost:8000/docs
- Salud del servicio: http://localhost:8000/health

## Ejecutar en producción

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

O vía Docker:

```bash
docker compose up --build
```

## Ejemplo de uso

```bash
curl -X POST http://localhost:8000/api/evaluar-zona \
  -H "Content-Type: application/json" \
  -d '{
        "id_comunidad": "San-Marcos-Test",
        "radiacion": 4.8,
        "velocidad_viento": 1.5,
        "hay_curso_agua": "si",
        "caudal": 75.0,
        "salto_neto": 14.0,
        "masa_estiercol": 6.0,
        "consumo_diario": 4200.0,
        "presupuesto": "medio"
      }'
```

```bash
curl http://localhost:8000/api/reglas   # metadata de las 30 reglas
curl http://localhost:8000/health
```

## Tests

```bash
pytest -v
```

Incluye:
- `tests/test_clips_service.py`: casos de estudio del motor de reglas
  (Puno, Junín, híbrido San Marcos, caso sin recomendación viable).
- `tests/test_api.py`: integración HTTP (200, 422, 500 simulado, `/api/reglas`).

## Linting y formateo

```bash
ruff check .
black --check .    # black . para aplicar el formateo
```

## CI

`.github/workflows/ci.yml` corre, en cada push/PR a `main`, sobre Python 3.11:
`ruff check .` → `black --check .` → `pytest`. El build falla si cualquiera
de los tres pasos falla.

## Notas de diseño relevantes

- **Múltiples recomendaciones por evaluación**: varias reglas de Capa 2
  pueden dispararse simultáneamente (p. ej. una recomendación monofuente y
  una híbrida a la vez). `EvaluacionResponse.recomendaciones` es siempre una
  lista, nunca un único resultado.
- **`SinRecomendacionError` no es un error HTTP 500**: si ninguna regla de
  Capa 2 dispara, es un resultado válido del dominio ("ninguna tecnología es
  viable con estos parámetros") y el endpoint responde `200 OK` con
  `recomendaciones: []`.
- **Trazabilidad**: cada `RecomendacionItem` incluye `regla_origen` (p. ej.
  `"R23"`), y `GET /api/reglas` expone la metadata completa de las 30 reglas
  para que el frontend construya una vista de auditoría/explicabilidad.
