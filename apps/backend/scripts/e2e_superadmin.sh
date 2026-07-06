#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# E2E Tests — Superadmin IaaS-RonSys
# ═══════════════════════════════════════════════════════════════
# Ejecutar desde la máquina host
# ═══════════════════════════════════════════════════════════════

source_url="http://localhost:8000"
PASSES=0
FAILS=0

green() { echo -e "\033[32m✅ $1\033[0m"; }
red()   { echo -e "\033[31m❌ $1\033[0m"; }

test() {
  local desc="$1" expected="$2" actual="$3"
  if [[ "$actual" == "$expected" ]]; then
    green "$desc"
    PASSES=$((PASSES+1))
  else
    red "$desc (expected: $expected, got: $actual)"
    FAILS=$((FAILS+1))
  fi
}

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║    🧪 E2E: SUPERADMIN IaaS-RonSys                         ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# ─── 1. Login Superadmin ──────────────────────────────────────
echo "━━━ 1. Autenticación ━━━"
SA_PASS="Admin2026!"
LOGIN=$(curl -s -X POST "$source_url/api/auth/login" \
  -H "Content-Type: application/json" \
  --data-raw "{\"email\":\"admin@iaas.com\",\"password\":\"$SA_PASS\"}")

ROLE=$(echo "$LOGIN" | python3 -c "import sys,json;print(json.load(sys.stdin).get('user',{}).get('role','FAIL'))" 2>/dev/null)
test "Superadmin login" "superadmin" "$ROLE"

CID=$(echo "$LOGIN" | python3 -c "import sys,json;print(json.load(sys.stdin).get('user',{}).get('company_id','NONE'))" 2>/dev/null)
test "company_id=null para superadmin" "null" "$CID"

TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json;print(json.load(sys.stdin).get('access_token','FAIL'))" 2>/dev/null)

# ─── 2. Dashboard ────────────────────────────────────────────
echo ""
echo "━━━ 2. Dashboard Global ━━━"
DASHBOARD=$(curl -s "$source_url/api/superadmin/dashboard" \
  -H "Authorization: Bearer $TOKEN")
TOTAL_CO=$(echo "$DASHBOARD" | python3 -c "import sys,json;print(json.load(sys.stdin).get('total_companies','FAIL'))" 2>/dev/null)
TOTAL_US=$(echo "$DASHBOARD" | python3 -c "import sys,json;print(json.load(sys.stdin).get('total_users','FAIL'))" 2>/dev/null)
test "Dashboard: companies exists" 3 "$TOTAL_CO"
test "Dashboard: users exists" 8 "$TOTAL_US"

# ─── 3. List Users ────────────────────────────────────────────
echo ""
echo "━━━ 3. Listar Usuarios ━━━"
USERS=$(curl -s "$source_url/api/superadmin/users" \
  -H "Authorization: Bearer $TOKEN")
U_TOTAL=$(echo "$USERS" | python3 -c "import sys,json;print(json.load(sys.stdin).get('total','FAIL'))" 2>/dev/null)
test "List users total" 8 "$U_TOTAL"

HAS_SA=$(echo "$USERS" | python3 -c "import sys,json;users=json.load(sys.stdin)['users'];print(any(u['role']=='superadmin' for u in users))" 2>/dev/null)
test "Superadmin in list" "True" "$HAS_SA"

# ─── 4. List Companies ───────────────────────────────────────
echo ""
echo "━━━ 4. Listar Empresas ━━━"
COMPS=$(curl -s "$source_url/api/superadmin/companies" \
  -H "Authorization: Bearer $TOKEN")
C_TOTAL=$(echo "$COMPS" | python3 -c "import sys,json;print(json.load(sys.stdin).get('total','FAIL'))" 2>/dev/null)
test "List companies total" 3 "$C_TOTAL"

# ─── 5. Crear usuario en tenant específico ───────────────────
echo ""
echo "━━━ 5. Crear Usuario Multi-Tenant ━━━"
NEW_USER=$(curl -s -X POST "$source_url/api/superadmin/users" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"e2e-test@elsegoviano.pe","full_name":"E2E Test","password":"E2EPass2026!","role":"operator","tenant_id":2,"is_verified":true}')
NEW_ROLE=$(echo "$NEW_USER" | python3 -c "import sys,json;print(json.load(sys.stdin).get('role','FAIL'))" 2>/dev/null)
NEW_TID=$(echo "$NEW_USER" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tenant_id','FAIL'))" 2>/dev/null)
test "Create user in tenant 2" "operator" "$NEW_ROLE"
test "User tenant_id is 2" "2" "$NEW_TID"

# ─── 6. Aislamiento: admin NO puede crear en otro tenant ────
echo ""
echo "━━━ 6. Seguridad Multi-Tenant ━━━"
ADMIN_PASS="admin123"
ADMIN_LOGIN=$(curl -s -X POST "$source_url/api/auth/login" \
  -H "Content-Type: application/json" \
  --data-raw "{\"email\":\"admin@elsegoviano.pe\",\"password\":\"$ADMIN_PASS\"}")
ADMIN_TOKEN=$(echo "$ADMIN_LOGIN" | python3 -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

CROSS_TENANT=$(curl -s -X POST "$source_url/api/admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: 4" \
  -d '{"email":"intruso@test.pe","full_name":"Intruso","password":"Test1234","role":"operator"}')
CROSS_DETAIL=$(echo "$CROSS_TENANT" | python3 -c "import sys,json;print(json.load(sys.stdin).get('detail','NO_ERROR'))" 2>/dev/null)
test "admin blocked from other tenant" "Access denied to this tenant" "$CROSS_DETAIL"

# ─── 7. Superadmin crea usuario en ferretería ────────────────
echo ""
echo "━━━ 7. Superadmin crea en ferreteria ━━━"
FERR_USER=$(curl -s -X POST "$source_url/api/superadmin/users" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin-ferreteria@test.pe","full_name":"Admin Ferreteria Test","password":"Test1234","role":"admin","tenant_id":4,"is_verified":true}')
FERR_TID=$(echo "$FERR_USER" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tenant_id','FAIL'))" 2>/dev/null)
test "Create in tenant 4" "4" "$FERR_TID"

# ─── 8. Crear empresa nueva ──────────────────────────────────
echo ""
echo "━━━ 8. Crear Empresa ━━━"
NEW_COMP=$(curl -s -X POST "$source_url/api/superadmin/companies" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Empresa E2E Test","ruc":"99999999999","business_type":"services"}')
NEW_CNAME=$(echo "$NEW_COMP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('name','FAIL'))" 2>/dev/null)
test "Create company" "Empresa E2E Test" "$NEW_CNAME"

# ─── 9. Crear usuario en empresa nueva ──────────────────────
# Get the new company ID
COMP_ID=$(echo "$NEW_COMP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',0))" 2>/dev/null)
if [ "$COMP_ID" -gt 0 ]; then
  NEW_USER2=$(curl -s -X POST "$source_url/api/superadmin/users" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"admin-nueva@test.pe\",\"full_name\":\"Admin Nueva Empresa\",\"password\":\"Test1234\",\"role\":\"admin\",\"tenant_id\":$COMP_ID,\"is_verified\":true}")
  NEW2_TID=$(echo "$NEW_USER2" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tenant_id','FAIL'))" 2>/dev/null)
  test "Create user in new company" "$COMP_ID" "$NEW2_TID"
fi

# ─── 10. Login del nuevo usuario creado por superadmin ──────
echo ""
echo "━━━ 10. Nuevo usuario puede loguearse ━━━"
NUEVO_LOGIN=$(curl -s -X POST "$source_url/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"e2e-test@elsegoviano.pe","password":"E2EPass2026!"}')
NUEVO_ROLE=$(echo "$NUEVO_LOGIN" | python3 -c "import sys,json;print(json.load(sys.stdin).get('user',{}).get('role','FAIL'))" 2>/dev/null)
test "New user can login" "operator" "$NUEVO_ROLE"

# ─── Resumen ─────────────────────────────────────────────────
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  📊 RESULTADOS                                           ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║  ✅ Passed: $PASSES"
echo "║  ❌ Failed: $FAILS"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Cleanup test users
curl -s -X DELETE "$source_url/api/superadmin/users/$(echo "$NUEVO_LOGIN" | python3 -c "import sys,json;print(json.load(sys.stdin).get('user',{}).get('id',''))" 2>/dev/null)" \
  -H "Authorization: Bearer $TOKEN" > /dev/null 2>&1
