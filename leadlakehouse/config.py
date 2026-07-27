"""Configuração central (pydantic-settings). Tudo por variável de ambiente `LLH_*`."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LLH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Banco operacional (Postgres via docker-compose)
    database_url: str = "postgresql+psycopg://llh:llh@localhost:5433/leadlakehouse"

    # Tenant — single-tenant por enquanto, já preparado p/ multi-tenant
    tenant_id: str = "default"

    # Coleta / browser
    headless: bool = True
    concorrencia: int = 4
    delay_min_ms: int = 800
    delay_max_ms: int = 2500
    bronze_dir: str = "data/bronze"

    # Proxy — DESLIGADO por padrão (custo zero)
    proxy_url: str = ""

    # Fontes/enriquecimento pagos — DESLIGADOS por padrão (custo zero)
    google_places_api_key: str = ""
    pagespeed_api_key: str = ""

    # Integração zapagente (F4)
    zapagente_base_url: str = ""
    zapagente_token: str = ""


settings = Settings()
