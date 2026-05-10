# IaaS-RonSys Backend

## Requisitos

- **Python 3.12.x** ⚠️ (no 3.13+, asyncpg no compila)
- PostgreSQL 16
- Redis 7 (opcional, rate limiting usa memoria si no está)
- RabbitMQ 4 (opcional, para tareas asíncronas futuras)

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env  # Editar DATABASE_URL
```

## Ejecutar

```bash
uvicorn app.main:app --reload
```

## Probar

```bash
pytest -v                          # 59 tests
python scripts/seed.py             # Demo en memoria
python scripts/seed_db.py          # Seed data en PostgreSQL
```

## Seed Data

```bash
# Requiere PostgreSQL corriendo
python scripts/seed_db.py
```

Crea:
- Empresa "El Segoviano" (RUC: 10777555551)
- 50 cuentas contables (PCGE)
- Simulación financiera 12 meses → 152 asientos
- 5 productos: pollo, cerdo, papa, aceite, arroz
- Movimientos de kárdex iniciales

## Migraciones

```bash
alembic upgrade head               # Aplicar migraciones
alembic revision --autogenerate -m "desc"  # Nueva migración
```

## Endpoints

| Ruta | Descripción |
|------|-------------|
| `/` | Info básica |
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |
| `/metrics` | Prometheus |
| `/api/health` | Health check |
| `/api/ready` | Readiness (verifica DB) |
| `/api/accounting/*` | Motor contable |
| `/api/accounting/kardex/*` | Kárdex |
| `/api/settings` | Configuración / Branding |
