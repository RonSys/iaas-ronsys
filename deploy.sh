#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
#  deploy.sh — IaaS-RonSys MVP Deployment
#
#  Uso:   chmod +x deploy.sh && ./deploy.sh
#
#  Entornos soportados:
#    - Linux Mint / Ubuntu (con o sin Docker)
#    - Debian / any Linux con bash
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
NC='\033[0m' # No Color

# ─── Config ─────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PROJECT_NAME="IaaS-RonSys"
ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

FIRST_DEPLOY=false
DEPLOY_START_TIME=$(date +%s)

# ─── Funciones de log ───────────────────────────────────────────
log_info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()      { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo -e "\n${CYAN}${BOLD}━━━ $1 ━━━${NC}"; }
log_detail()  { echo -e "        $1"; }

banner() {
    echo ""
    echo -e "${CYAN}${BOLD}"
    echo "  ╔══════════════════════════════════════════╗"
    echo "  ║   🐟  IaaS-RonSys  —  MVP Deployer      ║"
    echo "  ║   ERP SaaS · Motor Contable · Kárdex    ║"
    echo "  ╚══════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ─── Detección de primer deploy ──────────────────────────────────
detect_deploy_type() {
    if [ -f "$ENV_FILE" ]; then
        FIRST_DEPLOY=false
        log_info "Detectado redeploy — .env ya existe"
    else
        FIRST_DEPLOY=true
        log_info "PRIMER DEPLOY — configurando entorno desde cero"
    fi
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
    check_dependency "Node.js" "node --version" "sudo apt install nodejs npm  (se necesita ≥18)" || missing=1
    check_dependency "npm" "npm --version" "sudo apt install npm" || missing=1

    # Python 3.12 check — solo warn, el backend usa Docker
    if python3.12 --version &>/dev/null; then
        log_ok "Python 3.12 encontrado"
    elif python3 --version &>/dev/null; then
        local pyver=$(python3 --version 2>&1 | awk '{print $2}')
        log_warn "Python $pyver detectado (se necesita 3.12)"
        log_detail "El backend se ejecutará en Docker con Python 3.12-slim — no hay problema"
    else
        log_warn "Python no detectado — el backend usará Docker, no hay problema"
    fi

    if [ $missing -eq 1 ]; then
        log_error "Faltan dependencias. Instálalas y vuelve a ejecutar."
        exit 1
    fi
}

# ─── Configurar .env ─────────────────────────────────────────────
setup_env() {
    log_step "2. Configurando variables de entorno"

    if [ ! -f "$ENV_FILE" ]; then
        log_info "Creando .env desde .env.example..."
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        log_ok ".env creado desde .env.example"
        FIRST_DEPLOY=true
    else
        log_ok ".env ya existe — usando configuración actual"
    fi

    # SECRET_KEY
    if grep -q 'SECRET_KEY=CHANGE_ME\|SECRET_KEY=sk-tu\|SECRET_KEY=a1b2c3d4\|SECRET_KEY=$' "$ENV_FILE" 2>/dev/null || ! grep -q '^SECRET_KEY=' "$ENV_FILE" 2>/dev/null; then
        local new_key=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || date +%s | sha256sum | head -c 64)
        if grep -q '^SECRET_KEY=' "$ENV_FILE" 2>/dev/null; then
            sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$new_key/" "$ENV_FILE"
        else
            echo "SECRET_KEY=$new_key" >> "$ENV_FILE"
        fi
        log_ok "SECRET_KEY generada automáticamente"
    else
        log_ok "SECRET_KEY ya configurada"
    fi

    # Cargar variables para usar en el script
    set -a
    source "$ENV_FILE" 2>/dev/null
    set +a
}

# ─── Levantar infraestructura Docker ─────────────────────────────
start_infra() {
    log_step "3. Levantando infraestructura (Docker)"

    log_info "Iniciando PostgreSQL + Redis..."
    docker compose up -d postgres redis 2>&1 | grep -v "version is obsolete" || true

    log_info "Esperando health checks..."
    local max_wait=60
    local waited=0
    local interval=3

    while [ $waited -lt $max_wait ]; do
        local pg_healthy=$(docker inspect iaas-postgres --format='{{.State.Health.Status}}' 2>/dev/null)
        local redis_healthy=$(docker inspect iaas-redis --format='{{.State.Health.Status}}' 2>/dev/null)

        if [ "$pg_healthy" = "healthy" ] && [ "$redis_healthy" = "healthy" ]; then
            log_ok "PostgreSQL + Redis healthy (${waited}s)"
            break
        fi

        sleep $interval
        waited=$((waited + interval))
        echo -n "."
    done
    echo ""

    if [ $waited -ge $max_wait ]; then
        log_error "Timeout esperando infraestructura. Revisa: docker compose ps"
        log_detail "  PostgreSQL: $(docker inspect iaas-postgres --format='{{.State.Health.Status}}' 2>/dev/null || echo 'no running')"
        log_detail "  Redis:      $(docker inspect iaas-redis --format='{{.State.Health.Status}}' 2>/dev/null || echo 'no running')"
        exit 1
    fi
}

# ─── Construir y levantar backend ────────────────────────────────
start_backend() {
    log_step "4. Construyendo y levantando backend"

    log_info "Construyendo imagen Docker del backend..."
    docker compose build backend 2>&1 | tail -3

    log_info "Iniciando backend..."
    docker compose up -d backend 2>&1 | grep -v "version is obsolete" || true

    # Esperar que el backend esté corriendo
    local max_wait=45
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if curl -sf http://localhost:${BACKEND_PORT:-8000}/health > /dev/null 2>&1; then
            log_ok "Backend respondiendo en http://localhost:${BACKEND_PORT:-8000}"
            break
        fi
        sleep 2
        waited=$((waited + 2))
    done

    if [ $waited -ge $max_wait ]; then
        log_warn "Backend no responde aún — continuando (puede estar compilando)"
        log_detail "Últimos logs:"
        docker logs iaas-backend --tail 5 2>&1 | while read line; do log_detail "  $line"; done
    fi
}

# ─── Ejecutar migraciones ────────────────────────────────────────
run_migrations() {
    log_step "5. Ejecutando migraciones Alembic"

    log_info "Aplicando migraciones..."
    local migration_output
    migration_output=$(docker exec -w /app iaas-backend env PYTHONPATH=/app alembic upgrade head 2>&1)
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_ok "Migraciones aplicadas"
        echo "$migration_output" | grep -E "Running upgrade|alembic" | while read line; do log_detail "$line"; done
    else
        log_error "Error en migraciones:"
        echo "$migration_output" | tail -15 | while read line; do log_detail "  $line"; done
        log_warn "¿Ya se aplicaron antes? Intentando continuar..."
    fi
}

# ─── Cargar seed data ────────────────────────────────────────────
load_seed_data() {
    log_step "6. Cargando datos de prueba (seed)"

    # Verificar si ya hay datos
    local has_data
    has_data=$(docker exec iaas-postgres psql -U "${POSTGRES_USER:-ron}" -d "${POSTGRES_DB:-iaas_ronsys}" -tAc "SELECT count(*) FROM companies;" 2>/dev/null)

    if [ "${has_data:-0}" -gt 0 ] 2>/dev/null; then
        log_warn "Ya hay $has_data empresa(s) en la BD — omitiendo seed para no duplicar"
        log_detail "Para forzar reseed: docker exec iaas-postgres psql -U ron -d iaas_ronsys -c \"DELETE FROM kardex_movements; DELETE FROM products; DELETE FROM journal_entry_lines; DELETE FROM journal_entries; DELETE FROM companies;\" && docker exec -w /app iaas-backend env PYTHONPATH=/app python scripts/seed_db.py"
        return 0
    fi

    log_info "Ejecutando seed_db.py..."
    local seed_output
    seed_output=$(docker exec -w /app iaas-backend env PYTHONPATH=/app python scripts/seed_db.py 2>&1)
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_ok "Seed data cargado exitosamente"
        echo "$seed_output" | grep -E "✅|📊|📦|Empresa|Ventas" | while read line; do log_detail "$line"; done
    else
        log_error "Error en seed data:"
        echo "$seed_output" | tail -20 | while read line; do log_detail "  $line"; done
        log_warn "¿Ya hay datos? El seed puede fallar si ya se ejecutó."
    fi

    # Verificar estado del admin
    local admin_exists
    admin_exists=$(docker exec iaas-postgres psql -U "${POSTGRES_USER:-ron}" -d "${POSTGRES_DB:-iaas_ronsys}" -tAc "SELECT count(*) FROM users WHERE email='admin@elsegoviano.pe';" 2>/dev/null)
    if [ "${admin_exists:-0}" -gt 0 ] 2>/dev/null; then
        log_ok "Usuario admin existe en BD"
    else
        log_warn "Usuario admin NO encontrado — la migración 0002 debió crearlo"
    fi
}

# ─── Instalar dependencias frontend ──────────────────────────────
setup_frontend() {
    log_step "7. Preparando frontend"

    cd "$SCRIPT_DIR/apps/web"

    if [ ! -d "node_modules" ]; then
        log_info "Instalando dependencias npm..."
        npm install --silent 2>&1 | tail -3
        log_ok "Dependencias npm instaladas"
    else
        log_ok "node_modules ya existe — npm ci para asegurar consistencia"
        npm ci --silent 2>&1 | tail -3 || true
    fi

    cd "$SCRIPT_DIR"
}

# ─── Verificar/resetear contraseña admin ─────────────────────────
verify_admin_password() {
    log_step "8. Verificando credenciales demo"

    # Resetear admin a contraseña conocida para consistencia
    log_info "Reseteando contraseña admin a 'admin123'..."
    local hashed
    hashed=$(docker exec -w /app iaas-backend env PYTHONPATH=/app python -c "
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
ph = PasswordHash([Argon2Hasher()])
print(ph.hash('admin123'))
" 2>/dev/null)

    if [ -n "$hashed" ]; then
        docker exec iaas-postgres psql -U "${POSTGRES_USER:-ron}" -d "${POSTGRES_DB:-iaas_ronsys}" \
            -c "UPDATE users SET hashed_password='$hashed', is_verified=true WHERE email='admin@elsegoviano.pe';" \
            > /dev/null 2>&1
        log_ok "Contraseña admin reseteada"
    else
        log_warn "No se pudo resetear contraseña admin"
    fi
}

# ─── Resumen final ────────────────────────────────────────────────
show_summary() {
    local elapsed=$(($(date +%s) - DEPLOY_START_TIME))
    local backend_port="${BACKEND_PORT:-8000}"

    echo ""
    echo -e "${GREEN}${BOLD}"
    echo "  ╔════════════════════════════════════════════════════╗"
    echo "  ║  ✅  IaaS-RonSys desplegado correctamente         ║"
    echo "  ╚════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
    echo -e "  ${BOLD}Tiempo total:${NC} ${elapsed}s"
    echo ""
    echo -e "  ${BOLD}━━━ URLs ━━━${NC}"
    echo -e "  ${CYAN}Frontend:${NC}     http://localhost:5173"
    echo -e "  ${CYAN}Backend API:${NC}   http://localhost:$backend_port"
    echo -e "  ${CYAN}Swagger Docs:${NC}  http://localhost:$backend_port/docs"
    echo -e "  ${CYAN}Health Check:${NC}  http://localhost:$backend_port/health"
    echo ""
    echo -e "  ${BOLD}━━━ Credenciales Demo ━━━${NC}"
    echo -e "  ${GREEN}Email:${NC}     admin@elsegoviano.pe"
    echo -e "  ${GREEN}Password:${NC}  admin123"
    echo -e "  ${GREEN}Rol:${NC}       admin"
    echo ""
    echo -e "  ${BOLD}━━━ Infraestructura ━━━${NC}"
    echo -e "  PostgreSQL:   localhost:5432  (user: ${POSTGRES_USER:-ron})"
    echo -e "  Redis:        localhost:6379"
    echo ""
    echo -e "  ${BOLD}━━━ Comandos Útiles ━━━${NC}"
    echo -e "  Ver logs backend:  ${YELLOW}docker logs -f iaas-backend${NC}"
    echo -e "  Ver logs BD:       ${YELLOW}docker logs -f iaas-postgres${NC}"
    echo -e "  Parar todo:        ${YELLOW}docker compose down${NC}"
    echo -e "  Redeploy:          ${YELLOW}./deploy.sh${NC}"
    echo -e "  Login test:        ${YELLOW}curl -X POST http://localhost:$backend_port/api/auth/login -H 'Content-Type: application/json' -d '{\"email\":\"admin@elsegoviano.pe\",\"password\":\"admin123\"}'${NC}"
    echo ""
}

# ─── Main ────────────────────────────────────────────────────────
main() {
    banner
    detect_deploy_type
    check_dependencies
    setup_env
    start_infra
    start_backend
    run_migrations
    load_seed_data
    setup_frontend
    verify_admin_password
    show_summary
}

# ═══════════════════════════════════════════════════════════════════
main "$@"
