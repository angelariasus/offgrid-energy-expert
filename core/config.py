"""Configuración de la aplicación, cargada desde variables de entorno / `.env`."""

from __future__ import annotations

from typing import Literal

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

    cors_allowed_origins: list[str] = ["http://localhost:3000"]
    """Orígenes permitidos por CORS (frontend Next.js/React). Nunca usar ["*"] en prod."""

    log_level: str = "INFO"
    """Nivel de logging raíz (DEBUG, INFO, WARNING, ERROR, CRITICAL)."""

    environment: Literal["dev", "prod"] = "dev"
    """Entorno de ejecución. Afecta el formato de logging (texto legible vs JSON)."""


settings = Settings()
