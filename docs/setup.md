# Setup — IaaS-RonSys Backend

## ⚠️ Requisito Crítico: Python 3.12.x

El proyecto **NO funciona con Python 3.13+ ni 3.14** porque las dependencias nativas
(`pydantic-core`, `asyncpg`) usan PyO3 y no compilan en versiones superiores.

```bash
# Verificar versión
python3 --version   # Debe ser 3.12.x

# Si tienes pyenv
pyenv install 3.12
pyenv local 3.12
```

---

## Instalación

### Opción A: Local con Python 3.12

```bash
cd apps/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Opción B: Docker (recomendado)

```bash
docker-compose up -d
```

El Dockerfile ya usa `python:3.12-slim`.

---

## Servicios requeridos

| Servicio | Puerto | Docker |
|----------|--------|--------|
| PostgreSQL 16 | 5432 | ✅ en compose |
| Redis 7 | 6379 | ✅ en compose |
| RabbitMQ 4 | 5672 | ✅ en compose |
| Prometheus | 9090 | ✅ en compose |
| Grafana | 3000 | ✅ en compose |

---

## Comandos

```bash
pytest -v                          # Tests
python scripts/seed.py             # Demo motor contable
uvicorn app.main:app --reload      # Servidor dev
alembic upgrade head               # Migraciones
make test                          # Tests con cobertura
make lint                          # Ruff check
```

---

## Variables de entorno

Copiar `.env.example` → `.env` en la raíz del proyecto.

Un solo `.env` para todo el monorepo. Docker Compose lo distribuye.
