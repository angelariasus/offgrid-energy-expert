"""Configuración de la aplicación, cargada desde variables de entorno / `.env`."""

from __future__ import annotations

from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración centralizada del backend.

    Se carga automáticamente desde un archivo `.env` en la raíz del proyecto
    (ver `.env.example`) y/o desde variables de entorno reales del proceso,
    con estas últimas teniendo prioridad. Nunca se hardcodean valores
    sensibles o dependientes de entorno (como los orígenes CORS) en el código.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    clips_rules_path: str = "logica/reglas.clp"
    """Ruta al archivo .clp con las reglas del sistema experto."""

    cors_allowed_origins: list[str] | str = ["http://localhost:3000"]
    """Orígenes permitidos por CORS (acepta lista JSON, string simple, separados por coma o lista)."""

    @field_validator("cors_allowed_origins", mode="after")
    @classmethod
    def parse_cors_origins(cls, v: list[str] | str) -> list[str]:
        """Parsea tolerantemente orígenes CORS desde variables de entorno."""
        import json

        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return ["http://localhost:3000"]
            if v.startswith("[") and v.endswith("]"):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed if str(x).strip()]
                except Exception:
                    inner = v[1:-1]
                    parts = [
                        x.strip().strip("'\"") for x in inner.split(",") if x.strip().strip("'\"")
                    ]
                    if parts:
                        return parts
            return [x.strip().strip("'\"") for x in v.split(",") if x.strip().strip("'\"")]
        return ["http://localhost:3000"]

    log_level: str = "INFO"
    """Nivel de logging raíz (DEBUG, INFO, WARNING, ERROR, CRITICAL)."""

    environment: Literal["dev", "prod"] = "dev"
    """Entorno de ejecución. Afecta el formato de logging (texto legible vs JSON)."""


settings = Settings()
