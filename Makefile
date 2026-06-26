.PHONY: help setup dev test lint migrate shell build clean

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Backend ───────────────────────────────────────────────────

setup: ## Crea venv e instala dependencias del backend (desarrollo local)
	cd apps/backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
	@echo "✅ Venv creado en apps/backend/.venv"
	@echo "💡 Actívalo con: source apps/backend/.venv/bin/activate"

dev: ## Levanta el backend en modo desarrollo
	cd apps/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Ejecuta tests del backend
	cd apps/backend && pytest -v --cov=app --cov-report=term

lint: ## Lintea el backend
	cd apps/backend && ruff check . && ruff format --check .

format: ## Formatea el backend
	cd apps/backend && ruff format .

# ─── Base de Datos ────────────────────────────────────────────

migrate: ## Ejecuta migraciones pendientes
	cd apps/backend && alembic upgrade head

migrate-new: ## Crea nueva migración (msg=descripción)
	cd apps/backend && alembic revision --autogenerate -m "$(msg)"

migrate-rollback: ## Revierte última migración
	cd apps/backend && alembic downgrade -1

# ─── Docker ────────────────────────────────────────────────────

build: ## Construye todas las imágenes
	docker-compose build

up: ## Levanta todos los servicios
	docker-compose up -d

down: ## Detiene todos los servicios
	docker-compose down

logs: ## Muestra logs de todos los servicios
	docker-compose logs -f

shell: ## Shell dentro del contenedor backend
	docker-compose exec backend bash

# ─── Git ──────────────────────────────────────────────────────

git-init: ## Inicializa el repo
	git init
	git add .
	git commit -m "chore: initial project scaffold"

# ─── Utilidades ───────────────────────────────────────────────

clean: ## Limpia archivos temporales
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf apps/backend/**/.egg-info
	@echo "🧹 Limpieza completa"
