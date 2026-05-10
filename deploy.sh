#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
#  deploy.sh — IaaS-RonSys MVP Deployment
#
#  Uso:
#    ./deploy.sh                  # default: prod
#    ./deploy.sh --env qa         # entorno QA (backend :8001, BD separada)
#    ./deploy.sh --env prod       # entorno producción (backend :8000, nginx :80)
#
#  Idempotente: se puede ejecutar múltiples veces sin romper.
# ═══════════════════════════════════════════════════════════════════════

set -o pipefail

# ─── Colores ─────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Config ─────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PROJECT_NAME="IaaS-RonSys"
DEPLOY_START_TIME=$(date +%s)

# ─── Valores default ────────────────────────────────────────────
DEPLOY_ENV="prod"
COMPOSE_FILES="-f docker-compose.yml"
ENV_FILE=".env.prod"
BACKEND_CONTAINER="iaas-backend-prod"
BACKEND_PORT="8000"
QA_DB_NAME="iaas_ronsys_qa"

# ─── Parse args ──────────────────────────────────────────────────
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --env)
                DEPLOY_ENV="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    if [ "$DEPLOY_ENV" = "qa" ]; then
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.qa.yml"
        ENV_FILE=".env.qa"
        BACKEND_CONTAINER="iaas-backend-qa"
        BACKEND_PORT="8001"
    else
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
        ENV_FILE=".env.prod"
        BACKEND_CONTAINER="iaas-backend-prod"
        BACKEND_PORT="8000"
    fi
}

# ─── Funciones de log ───────────────────────────────────────────
log_info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()      { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo -e "\n${CYAN}${BOLD}━━━ $1 ━━━${NC}"; }
log_detail()  { echo -e "        $1"; }

banner() {
    local env_label="PRODUCCIÓN"
    [ "$DEPLOY_ENV" = "qa" ] && env_label="QA (Quality Assurance)"

    echo ""
    echo -e "${CYAN}${BOLD}"
    echo "  ╔══════════════════════════════════════════╗"
    echo "  ║   🐟  IaaS-RonSys  —  Deployer          ║"
    echo "  ║   ERP SaaS · Motor Contable · Kárdex    ║"
    echo "  ║                                          ║"
    printf "  ║   Entorno: %-30s ║\n" "$env_label"
    echo "  ╚══════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ─── Verificar dependencias ──────────────────────────────────────
check_dependency() {
    local name="$1"
    local check_cmd="$2"
    local install_hint="$3"

    if eval "$check_cmd" &>/dev/null; then
        log_ok "$name encontrado"
        return 0
    else
        log_error "$name NO encontrado"
        if [ -n "$install_hint" ]; then
            log_detail "Instalar: $install_hint"
        fi
        return 1
    fi
}

check_dependencies() {
    log_step "1. Verificando dependencias"
    local missing=0

    check_dependency "Docker" "docker --version" "sudo apt install docker.io && sudo usermod -aG docker \$USER" || missing=1
    check_dependency "Docker Compose" "docker compose version" "Incluido con Docker" || missing=1

    if [ "$DEPLOY_ENV" = "qa" ]; then
        check_dependency "Node.js" "node --version" "sudo apt install nodejs npm" || missing=1
        check_dependency "npm" "npm --version" "sudo apt install npm" || missing=1
        log_detail "QA usa Vite dev server para frontend — Node.js requerido"
    fi

    # Python check — informativo, el backend usa Docker
    if python3.12 --version &>/dev/null; then
        log_ok "Python 3.12 encontrado"
    elif python3 --version &>/dev/null; then
        local pyver=$(python3 --version 2>&1 | awk '{print $2}')
        log_warn "Python $pyver detectado (se necesita 3.12)"
        log_detail "El backend se ejecuta en Docker con Python 3.12-slim"
    else
        log_warn "Python no detectado — el backend usa Docker"
    fi

    if [ $missing -eq 1 ]; then
        log_error "Faltan dependencias. Instálalas y vuelve a ejecutar."
        exit 1
    fi
}

# ─── Configurar .env del entorno ─────────────────────────────────
setup_env() {
    log_step "2. Configurando variables de entorno ($DEPLOY_ENV)"

    if [ ! -f "$ENV_FILE" ]; then
        log_error "$ENV_FILE no existe. Créalo a partir de .env.example."
        log_detail "  cp .env.example $ENV_FILE"
        log_detail "  # Luego edita las variables específicas del entorno"
        exit 1
    fi

    log_ok "$ENV_FILE encontrado"

    # SECRET_KEY — generar si está vacía o es placeholder
    local current_key
    current_key=$(grep '^SECRET_KEY=' "$ENV_FILE" 2>/dev/null | cut -d= -f2-)

    if [ -z "$current_key" ] || [ "$current_key" = "CHANGE_ME" ]; then
        local new_key
        new_key=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || date +%s | sha256sum | head -c 64)
        if grep -q '^SECRET_KEY=' "$ENV_FILE" 2>/dev/null; then
            sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$new_key|" "$ENV_FILE"
        else
            echo "SECRET_KEY=$new_key" >> "$ENV_FILE"
        fi
        log_ok "SECRET_KEY generada automáticamente"
    else
        log_ok "SECRET_KEY configurada"
    fi

    # Source env vars for script use
    set -a
    source "$ENV_FILE" 2>/dev/null
    set +a

    BACKEND_PORT="${BACKEND_PORT:-8000}"
    [ "$DEPLOY_ENV" = "qa" ] && BACKEND_PORT="8001"
}

# ─── Levantar infraestructura base ───────────────────────────────
start_infra() {
    log_step "3. Levantando infraestructura base"

    docker compose up -d postgres redis 2>&1 | grep -v "version is obsolete" || true

    log_info "Esperando health checks..."
    local max_wait=60
    local waited=0

    while [ $waited -lt $max_wait ]; do
        local pg_healthy
        local redis_healthy
        pg_healthy=$(docker inspect iaas-postgres --format='{{.State.Health.Status}}' 2>/dev/null)
        redis_healthy=$(docker inspect iaas-redis --format='{{.State.Health.Status}}' 2>/dev/null)

        if [ "$pg_healthy" = "healthy" ] && [ "$redis_healthy" = "healthy" ]; then
            log_ok "PostgreSQL + Redis healthy (${waited}s)"
            break
        fi
        sleep 3
        waited=$((waited + 3))
        echo -n "."
    done
    echo ""

    if [ $waited -ge $max_wait ]; then
        log_error "Timeout esperando infraestructura."
        log_detail "  PostgreSQL: $(docker inspect iaas-postgres --format='{{.State.Health.Status}}' 2>/dev/null || echo 'no running')"
        log_detail "  Redis:      $(docker inspect iaas-redis --format='{{.State.Health.Status}}' 2>/dev/null || echo 'no running')"
        exit 1
    fi

    # ─── QA: crear BD separada si no existe ──────────────────
    if [ "$DEPLOY_ENV" = "qa" ]; then
        log_info "Verificando BD de QA ($QA_DB_NAME)..."
        local db_exists
        db_exists=$(docker exec iaas-postgres psql -U "${POSTGRES_USER:-ron}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$QA_DB_NAME';" 2>/dev/null)
        if [ "$db_exists" != "1" ]; then
            docker exec iaas-postgres psql -U "${POSTGRES_USER:-ron}" -d postgres -c "CREATE DATABASE $QA_DB_NAME;" 2>/dev/null
            log_ok "BD $QA_DB_NAME creada"
        else
            log_ok "BD $QA_DB_NAME ya existe"
        fi
    fi
}

# ─── Construir y levantar servicios del entorno ──────────────────
start_services() {
    log_step "4. Construyendo y levantando servicios ($DEPLOY_ENV)"

    log_info "Construyendo imágenes..."
    docker compose $COMPOSE_FILES build 2>&1 | tail -5

    log_info "Iniciando servicios..."
    docker compose $COMPOSE_FILES up -d 2>&1 | grep -v "version is obsolete" || true

    # Esperar backend
    log_info "Esperando backend..."
    local max_wait=60
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if curl -sf http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
            log_ok "Backend respondiendo en http://localhost:$BACKEND_PORT"
            break
        fi
        sleep 2
        waited=$((waited + 2))
    done

    if [ $waited -ge $max_wait ]; then
        log_warn "Backend no responde aún — verificando logs:"
        docker logs "$BACKEND_CONTAINER" --tail 8 2>&1 | while read line; do log_detail "  $line"; done
    fi

    # Prod: verificar frontend nginx
    if [ "$DEPLOY_ENV" = "prod" ]; then
        if curl -sf http://localhost:80/ > /dev/null 2>&1; then
            log_ok "Frontend nginx respondiendo en http://localhost:80"
        else
            log_warn "Frontend nginx no responde — verificando:"
            docker logs iaas-frontend-prod --tail 5 2>&1 | while read line; do log_detail "  $line"; done
        fi
    fi
}

# ─── Ejecutar migraciones ────────────────────────────────────────
run_migrations() {
    log_step "5. Ejecutando migraciones Alembic"

    local migration_output
    migration_output=$(docker exec -w /app "$BACKEND_CONTAINER" env PYTHONPATH=/app alembic upgrade head 2>&1)
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_ok "Migraciones aplicadas"
        echo "$migration_output" | grep -E "Running upgrade|alembic" | while read line; do log_detail "$line"; done
    else
        log_warn "Migraciones — posiblemente ya aplicadas:"
        echo "$migration_output" | tail -5 | while read line; do log_detail "  $line"; done
    fi
}

# ─── Cargar seed data ────────────────────────────────────────────
load_seed_data() {
    log_step "6. Cargando datos de prueba (seed)"

    local db_name="${POSTGRES_DB:-iaas_ronsys}"
    local has_data
    has_data=$(docker exec iaas-postgres psql -U "${POSTGRES_USER:-ron}" -d "$db_name" -tAc "SELECT count(*) FROM companies;" 2>/dev/null)

    if [ "${has_data:-0}" -gt 0 ] 2>/dev/null; then
        log_warn "Ya hay $has_data empresa(s) en $db_name — omitiendo seed"
        return 0
    fi

    log_info "Ejecutando seed_db.py en $db_name..."
    local seed_output
    seed_output=$(docker exec -w /app "$BACKEND_CONTAINER" env PYTHONPATH=/app python scripts/seed_db.py 2>&1)
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_ok "Seed data cargado"
        echo "$seed_output" | grep -E "✅|Ventas|Empresa" | while read line; do log_detail "$line"; done
    else
        log_error "Error en seed:"
        echo "$seed_output" | tail -10 | while read line; do log_detail "  $line"; done
    fi
}

# ─── Resetear contraseña admin ───────────────────────────────────
verify_admin_password() {
    log_step "7. Verificando credenciales demo"

    local db_name
    if [ "$DEPLOY_ENV" = "qa" ]; then
        db_name="iaas_ronsys_qa"
    else
        db_name="${POSTGRES_DB:-iaas_ronsys}"
    fi

    local hashed
    hashed=$(docker exec -w /app "$BACKEND_CONTAINER" env PYTHONPATH=/app python -c "
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
ph = PasswordHash([Argon2Hasher()])
print(ph.hash('admin123'))
" 2>/dev/null)

    if [ -n "$hashed" ]; then
        docker exec iaas-postgres psql -U "${POSTGRES_USER:-ron}" -d "$db_name" \
            -c "UPDATE users SET hashed_password='$hashed', is_verified=true WHERE email='admin@elsegoviano.pe';" \
            > /dev/null 2>&1
        log_ok "Contraseña admin reseteada a 'admin123'"
    else
        log_warn "No se pudo resetear contraseña admin"
    fi
}

# ─── QA: Levantar Vite dev server ────────────────────────────────
start_frontend_qa() {
    log_step "8. Frontend QA (Vite dev server)"

    log_info "Instalando dependencias..."
    cd "$SCRIPT_DIR/apps/web"
    npm ci --silent 2>&1 | tail -3 || npm install --silent 2>&1 | tail -3

    # Verificar si ya hay un Vite corriendo
    if lsof -i:5173 -t &>/dev/null; then
        log_ok "Vite ya está corriendo en http://localhost:5173"
    else
        log_info "Iniciando Vite dev server..."
        npm run dev &
        sleep 3
        if curl -sf http://localhost:5173/ > /dev/null 2>&1; then
            log_ok "Frontend QA: http://localhost:5173"
        else
            log_warn "Vite puede estar iniciando — verifica: http://localhost:5173"
        fi
    fi

    cd "$SCRIPT_DIR"
}

# ─── Resumen final ────────────────────────────────────────────────
show_summary() {
    local elapsed=$(($(date +%s) - DEPLOY_START_TIME))

    echo ""
    echo -e "${GREEN}${BOLD}"
    echo "  ╔════════════════════════════════════════════════════╗"
    echo "  ║  ✅  IaaS-RonSys desplegado ($DEPLOY_ENV)         ║"
    echo "  ╚════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
    echo -e "  ${BOLD}Tiempo total:${NC} ${elapsed}s  |  ${BOLD}Entorno:${NC} $DEPLOY_ENV"
    echo ""

    if [ "$DEPLOY_ENV" = "qa" ]; then
        echo -e "  ${BOLD}━━━ URLs (QA) ━━━${NC}"
        echo -e "  ${CYAN}Frontend:${NC}     http://localhost:5173  (Vite dev server)"
        echo -e "  ${CYAN}Backend API:${NC}   http://localhost:8001"
        echo -e "  ${CYAN}Swagger Docs:${NC}  http://localhost:8001/docs"
        echo -e "  ${CYAN}Health Check:${NC}  http://localhost:8001/health"
    else
        echo -e "  ${BOLD}━━━ URLs (Producción) ━━━${NC}"
        echo -e "  ${CYAN}Frontend:${NC}     http://localhost        (nginx)"
        echo -e "  ${CYAN}Backend API:${NC}   http://localhost:8000"
        echo -e "  ${CYAN}Swagger Docs:${NC}  http://localhost:8000/docs"
        echo -e "  ${CYAN}Health Check:${NC}  http://localhost:8000/health"
    fi

    echo ""
    echo -e "  ${BOLD}━━━ Credenciales Demo ━━━${NC}"
    echo -e "  ${GREEN}Email:${NC}     admin@elsegoviano.pe"
    echo -e "  ${GREEN}Password:${NC}  admin123"
    echo -e "  ${GREEN}Rol:${NC}       admin"
    echo ""
    echo -e "  ${BOLD}━━━ Infraestructura ━━━${NC}"
    echo -e "  PostgreSQL:   localhost:5432"
    echo -e "  Redis:        localhost:6379"
    echo ""
    echo -e "  ${BOLD}━━━ Comandos Útiles ━━━${NC}"

    if [ "$DEPLOY_ENV" = "qa" ]; then
        echo -e "  Parar todo:        ${YELLOW}docker compose -f docker-compose.yml -f docker-compose.qa.yml down${NC}"
        echo -e "  Reiniciar backend: ${YELLOW}docker restart $BACKEND_CONTAINER${NC}"
        echo -e "  Login test:        ${YELLOW}curl -X POST http://localhost:8001/api/auth/login -H 'Content-Type: application/json' -d '{\"email\":\"admin@elsegoviano.pe\",\"password\":\"admin123\"}'${NC}"
    else
        echo -e "  Parar todo:        ${YELLOW}docker compose -f docker-compose.yml -f docker-compose.prod.yml down${NC}"
        echo -e "  Logs frontend:     ${YELLOW}docker logs -f iaas-frontend-prod${NC}"
        echo -e "  Login test:        ${YELLOW}curl -X POST http://localhost:8000/api/auth/login -H 'Content-Type: application/json' -d '{\"email\":\"admin@elsegoviano.pe\",\"password\":\"admin123\"}'${NC}"
    fi
    echo ""
}

# ─── Main ────────────────────────────────────────────────────────
main() {
    parse_args "$@"
    banner
    check_dependencies
    setup_env
    start_infra
    start_services
    run_migrations
    load_seed_data
    verify_admin_password

    if [ "$DEPLOY_ENV" = "qa" ]; then
        start_frontend_qa
    fi

    show_summary
}

# ═══════════════════════════════════════════════════════════════════
main "$@"
