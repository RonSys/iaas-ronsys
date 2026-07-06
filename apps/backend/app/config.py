"""
Configuración centralizada del backend.
Todas las variables de entorno se cargan y validan aquí.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # ─── App ──────────────────────────────────────────────────
    app_name: str = "IaaS-RonSys"
    app_version: str = "0.1.0"
    debug: bool = True

    # ─── PostgreSQL ──────────────────────────────────────────
    # LOCAL: postgresql+asyncpg://ron:ron123@localhost:5432/iaas_ronsys
    # DOCKER: postgresql+asyncpg://ron:ron123@postgres:5432/iaas_ronsys
    # Se configura en .env (raíz del proyecto) según el entorno
    database_url: str = "postgresql+asyncpg://ron:ron123@localhost:5432/iaas_ronsys"

    # ─── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ─── RabbitMQ ─────────────────────────────────────────────
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_queue: str = "iaas-tasks"

    # ─── LLM / IA ─────────────────────────────────────────────
    llm_api_key: Optional[str] = None
    llm_model: str = "gpt-4o"
    llm_provider: str = "openai"

    # ─── CORS ─────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ─── Auth / Seguridad ────────────────────────────────────
    # ⚠️  Generar con: openssl rand -hex 32
    #     NUNCA hardcodear en archivos .py
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    login_max_attempts: int = 10
    login_lock_minutes: int = 15
    login_rate_limit_per_ip: str = "5/minute"

    # ─── Rate Limiting ────────────────────────────────────────
    rate_limit_enabled: bool = True
    rate_limit_default: str = "100/hour"

    # ─── Monitoreo ────────────────────────────────────────────
    metrics_enabled: bool = True
    otel_service_name: str = "iaas-ronsys-backend"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"

    @property
    def cors_origins_list(self) -> list[str]:
        """Convierte el string de CORS a lista."""
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
