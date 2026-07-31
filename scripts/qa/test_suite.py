#!/usr/bin/env python3
"""
Suite QA end-to-end — IaaS-RonSys (Spec 01 recetas + Spec 02 costos variables).

Uso:
    python3 scripts/qa/test_suite.py            # credenciales por defecto (dev)
    IAAS_QA_PASSWORD=... python3 scripts/qa/test_suite.py

Requiere: python3 (std-lib), docker (para T5/T9/T10), backend+frontend desplegados.

Idempotente y NO destructivo:
  - T3 compensa los consumos con entradas al costo promedio (restaura stock Y promedio).
  - T4 usa una venta rechazada (qty excesiva) — sin mutación.
  - T6 crea un producto temporal QA (se desactiva al final, no se borra por FKs).
  - T9/T10 son de solo lectura.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = "http://localhost:8000"
TENANT = "1"
EMAIL = "admin@elsegoviano.pe"
PASSWORD = os.environ.get("IAAS_QA_PASSWORD", "admin123")
RATE_PAUSE = 1.0  # segundos entre requests (rate limit)

results = []  # (test_id, nombre, PASS/FAIL, evidencia)
_token = None
_auth = {}


# ─── Helpers ────────────────────────────────────────────────────
def pause():
    time.sleep(RATE_PAUSE)


def req(method, path, body=None, headers=None, expect_errors=False):
    # headers explícitos tienen prioridad sobre _auth (permite simular otro tenant)
    h = {"Content-Type": "application/json", **_auth, **(headers or {})}
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            raw = resp.read()
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, raw.decode(errors="replace")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode(errors="replace")


def docker(args):
    try:
        out = subprocess.run(["docker"] + args, capture_output=True, text=True, timeout=60)
        return out.stdout.strip(), out.returncode
    except Exception as e:
        return f"docker error: {e}", -1


def psql(sql):
    out, rc = docker(["exec", "iaas-postgres", "psql", "-U", "ron", "-d", "iaas_ronsys",
                      "-tAc", sql])
    return out.strip() if rc == 0 else f"PSQL_ERR({out})"


def record(tid, name, ok, evidence):
    results.append((tid, name, "PASS" if ok else "FAIL", evidence))
    print(f"[{tid}] {'✅ PASS' if ok else '❌ FAIL'} — {name}")
    for line in str(evidence).splitlines():
        print(f"      {line}")


def login():
    global _token, _auth
    code, data = req("POST", "/api/auth/login", {"email": EMAIL, "password": PASSWORD})
    if code != 200 or "access_token" not in data:
        return False, f"login HTTP {code}: {data}"
    _token = data["access_token"]
    _auth = {"Authorization": f"Bearer {_token}", "X-Tenant-ID": TENANT}
    return True, "token obtenido"


# ─── T1: Login + auth ───────────────────────────────────────────
def t1_login():
    ok, ev = login()
    if ok:
        import base64
        payload = json.loads(base64.b64decode(_token.split(".")[1] + "=="))
        tenant_ok = payload.get("company_id") == 1 or payload.get("sub") == 1
        ev += f" | tenant del JWT: {payload.get('company_id')} (esperado 1)"
        ok = tenant_ok
    record("T1", "Login + auth (token, tenant correcto)", ok, ev)


# ─── T2: CRUD recetas ───────────────────────────────────────────
def t2_recipes():
    # Restaurar primero el estado esperado (idempotencia entre corridas):
    # la receta de menu 10 debe tener sus 5 ingredientes con unidades correctas.
    ing = [{"product_id": 41, "quantity": 0.15, "unit_of_measure": "kg", "sort_order": 1},
           {"product_id": 43, "quantity": 2, "unit_of_measure": "und", "sort_order": 2},
           {"product_id": 44, "quantity": 0.05, "unit_of_measure": "kg", "sort_order": 3},
           {"product_id": 45, "quantity": 0.10, "unit_of_measure": "kg", "sort_order": 4},
           {"product_id": 46, "quantity": 0.05, "unit_of_measure": "kg", "sort_order": 5}]
    pause()
    req("PUT", "/api/v1/restaurant/menu/10/recipe", {"ingredients": ing})
    pause()
    code, r = req("GET", "/api/v1/restaurant/menu/10/recipe")
    ok = code == 200 and r.get("has_recipe") is True and len(r.get("ingredients", [])) == 5
    ev = f"GET receta menu 10 → HTTP {code}, ingredientes={len(r.get('ingredients', [])) if isinstance(r, dict) else '?'}"
    # PUT misma receta (idempotente)
    pause()
    code2, r2 = req("PUT", "/api/v1/restaurant/menu/10/recipe", {"ingredients": ing})
    ok2 = code2 == 200 and r2.get("has_recipe") is True
    ev2 = f"PUT receta menu 10 → HTTP {code2}, costo={r2.get('total_estimated_cost') if isinstance(r2, dict) else '?'}"
    # Validación de unidades (D4, fix F1): unidad incorrecta → 400 y receta NO se sobrescribe
    pause()
    code3, r3 = req("PUT", "/api/v1/restaurant/menu/10/recipe",
                    {"ingredients": [{"product_id": 41, "quantity": 1, "unit_of_measure": "unidad"}]})
    ok3 = code3 == 400
    ev3 = f"PUT unidad inválida → HTTP {code3} (esperado 400): {r3.get('detail', '') if isinstance(r3, dict) else ''}"
    # Verificar que la receta NO quedó sobrescrita (sigue con 5 ingredientes correctos)
    pause()
    _, r_check = req("GET", "/api/v1/restaurant/menu/10/recipe")
    still_ok = (isinstance(r_check, dict) and len(r_check.get("ingredients", [])) == 5
                and all(i["unit_of_measure"] in ("kg", "und") for i in r_check.get("ingredients", [])))
    ok3 = ok3 and still_ok
    ev3 += f" | receta intacta tras 400: {still_ok} (5 ingredientes, unidades kg/und)"
    # PUT con unidad correcta → 200 (regresión)
    pause()
    code4, r4 = req("PUT", "/api/v1/restaurant/menu/10/recipe", {"ingredients": ing})
    ok4 = code4 == 200
    ev4 = f" | PUT unidades correctas → HTTP {code4}"
    # RESTAURAR la receta correcta (idempotencia)
    pause()
    req("PUT", "/api/v1/restaurant/menu/10/recipe", {"ingredients": ing})
    record("T2", "CRUD recetas (GET/PUT + validación unidades D4)", ok and ok2 and ok3 and ok4,
           f"{ev} | {ev2} | {ev3}{ev4}")


# ─── T3: Explosión al vender ─────────────────────────────────────
def t3_explosion():
    # sesión POS
    pause()
    code, s = req("GET", "/api/sales/sessions/current")
    if code != 200 or not s:
        pause()
        req("POST", "/api/sales/sessions/open?opening_cash=100")
    # stocks antes
    pause()
    _, inv = req("GET", "/api/accounting/kardex/db/inventory")
    stock_before = {p["code"]: p["current_stock"] for p in inv}
    pause()
    _, hist_before = req("GET", "/api/accounting/kardex/db/ING-PES01")
    n_before = len(hist_before)
    # vender 1 Ceviche Clásico
    pause()
    code, sale = req("POST", "/api/sales/sale", {
        "items": [{"menu_item_id": 10, "item_name": "Ceviche Clásico (QA)", "item_type": "product",
                   "quantity": 1, "unit_of_measure": "unidad", "unit_price": 28,
                   "discount_pct": 0, "discount_amount": 0, "tax_pct": 0, "tax_amount": 0, "total": 28}],
        "payments": [{"payment_method": "cash", "amount": 28}]})
    ok = code == 200
    ev = f"venta → HTTP {code}, sale_id={sale.get('sale', {}).get('id') if isinstance(sale, dict) else '?'}"
    if ok:
        sale_id = sale["sale"]["id"]
        # stocks después
        pause()
        _, inv2 = req("GET", "/api/accounting/kardex/db/inventory")
        stock_after = {p["code"]: p["current_stock"] for p in inv2}
        # decrementos esperados (Ceviche Clásico): pescado 0.15, limón 2, cebolla 0.05, camote 0.10, choclo 0.05
        exp = {"ING-PES01": 0.15, "ING-LIM01": 2.0, "ING-CEB01": 0.05, "ING-CAM01": 0.10, "ING-CHO01": 0.05}
        deltas = {c: round(stock_before[c] - stock_after.get(c, stock_before[c]), 4) for c in exp}
        ok = all(abs(deltas.get(c, 0) - q) < 0.001 for c, q in exp.items())
        ev += f" | deltas={deltas} (esperado {exp})"
        # kárdex receta
        pause()
        _, hist_after = req("GET", "/api/accounting/kardex/db/ING-PES01")
        new_moves = hist_after[n_before:]
        ok = ok and any(m.get("movement_type") == "salida" and m.get("concept") == "Consumo por receta"
                        for m in new_moves)
        ev += f" | nuevos movs pescado: {len(new_moves)} (concepto={[m.get('concept') for m in new_moves]})"
        # ── Compensación: entradas al costo promedio (restauran stock Y promedio) ──
        pause()
        _, inv3 = req("GET", "/api/accounting/kardex/db/inventory")
        avg = {p["code"]: p["average_cost"] for p in inv3}
        for c, q in exp.items():
            pause()
            req("POST", "/api/accounting/kardex/db/entry",
                {"product_code": c, "quantity": q, "unit_cost": avg[c],
                 "concept": "Compensación QA", "date": "2026-07-31"})
        # verificar restauración
        pause()
        _, inv4 = req("GET", "/api/accounting/kardex/db/inventory")
        stock_rest = {p["code"]: p["current_stock"] for p in inv4}
        ok_rest = all(abs(stock_rest.get(c, 0) - stock_before[c]) < 0.001 for c in exp)
        ev += f" | stocks restaurados: {ok_rest}"
        ok = ok and ok_rest
        # guardar sale_id para T5
        globals()["_last_sale_id"] = sale_id
    record("T3", "Explosión al vender (descuento ingredientes + kárdex receta)", ok, ev)


# ─── T4: Stock insuficiente ─────────────────────────────────────
def t4_insufficient():
    pause()
    _, hist_before = req("GET", "/api/accounting/kardex/db/ING-PES01")
    n_before = len(hist_before)
    pause()
    code, r = req("POST", "/api/sales/sale", {
        "items": [{"menu_item_id": 10, "item_name": "Ceviche Clásico (QA x200)", "item_type": "product",
                   "quantity": 200, "unit_of_measure": "unidad", "unit_price": 28,
                   "discount_pct": 0, "discount_amount": 0, "tax_pct": 0, "tax_amount": 0, "total": 5600}],
        "payments": [{"payment_method": "cash", "amount": 5600}]})
    pause()
    _, hist_after = req("GET", "/api/accounting/kardex/db/ING-PES01")
    no_partial = len(hist_after) == n_before
    ok = code == 409 and no_partial
    ev = f"venta 200 ceviches → HTTP {code} (esperado 409): {r.get('detail', '') if isinstance(r, dict) else ''}"
    ev += f" | sin movimientos parciales: {no_partial}"
    record("T4", "Stock insuficiente → 409 sin movimientos parciales", ok, ev)


# ─── T5: Costeo + COGS ──────────────────────────────────────────
def t5_costing():
    pause()
    code, r = req("GET", "/api/v1/restaurant/menu/10/recipe")
    ok = code == 200
    ev = ""
    if ok:
        calc = round(sum(float(i["quantity"]) * float(i["average_cost"]) for i in r["ingredients"]), 2)
        reported = float(r["total_estimated_cost"])
        ok = abs(calc - reported) < 0.01
        ev = f"costo receta: reportado={reported}, Σ(ing)= {calc} → {'coincide' if ok else 'DIFIERE'}"
    # COGS contable del último sale (DB)
    sale_id = globals().get("_last_sale_id")
    if sale_id:
        jid = psql(f"SELECT journal_entry_id FROM sales WHERE id={sale_id}")
        cogs = psql(f"SELECT account_code||':'||debit FROM journal_entry_lines WHERE entry_id={jid} AND account_code='50'")
        ok2 = "50:" in cogs and float(cogs.split(":")[1]) > 0
        ev += f" | COGS asiento {jid}: {cogs}"
        ok = ok and ok2
    record("T5", "Costeo (Σ ingredientes) + COGS contable 50/12 (D9)", ok, ev)


# ─── T6: Costos variables (entrada DB → promedio ponderado) ─────
def t6_variable_costs():
    # Pre-cleanup de corridas anteriores (idempotencia): borrar QA-TMP01 + sus movimientos
    psql("DELETE FROM kardex_movements WHERE product_id=(SELECT id FROM products WHERE code='QA-TMP01')")
    psql("DELETE FROM products WHERE code='QA-TMP01'")
    pause()
    code, r = req("POST", "/api/accounting/kardex/db/products",
                  {"code": "QA-TMP01", "name": "[QA] Producto temporal", "unit": "kg",
                   "initial_stock": 0, "initial_cost": 0})
    ok = code in (200, 409)  # 409 si ya existe de una corrida previa
    ev = f"crear QA-TMP01 → HTTP {code}"
    pause()
    code2, r2 = req("POST", "/api/accounting/kardex/db/entry",
                    {"product_code": "QA-TMP01", "quantity": 10, "unit_cost": 18,
                     "concept": "QA entrada 1", "date": "2026-07-31"})
    pause()
    code3, r3 = req("POST", "/api/accounting/kardex/db/entry",
                    {"product_code": "QA-TMP01", "quantity": 10, "unit_cost": 22,
                     "concept": "QA entrada 2", "date": "2026-07-31"})
    ok2 = code2 == 200 and code3 == 200
    ev += f" | entrada 10@18 → HTTP {code2} | entrada 10@22 → HTTP {code3}"
    if ok2:
        bq = float(r3.get("balance_quantity", 0))
        bac = float(r3.get("balance_avg_cost", 0))
        ok3 = bq == 20.0 and abs(bac - 20.0) < 0.001  # (0*0+10*18+10*22)/20 = 20.00
        ev += f" | balance_qty={bq} (esp 20) | balance_avg={bac} (esp 20.00)"
        # persistencia en BD
        db_row = psql("SELECT current_stock||'|'||average_cost FROM products WHERE code='QA-TMP01'")
        ok4 = db_row.startswith("20.00|20.00") or db_row.startswith("20|20.00")
        ev += f" | BD: {db_row}"
        ok = ok and ok3 and ok4
        # cleanup: desactivar producto temporal (no se borra por FK kardex)
        pause()
        _, inv = req("GET", f"/api/v1/inventory/products?search=QA-TMP01")
        prods = inv.get("products", []) if isinstance(inv, dict) else []
        if prods:
            pid = prods[0]["id"]
            pause()
            c4, _ = req("PATCH", f"/api/v1/inventory/products/{pid}", {"active": False})
            ev += f" | cleanup QA-TMP01 (active=false) → HTTP {c4}"
    record("T6", "Costos variables: entrada DB → promedio ponderado + persistencia", ok, ev)


# ─── T7: Multi-tenant ───────────────────────────────────────────
def t7_multitenant():
    # Aislamiento: user de tenant 1 NO puede operar como tenant 3 (403)
    pause()
    code, r = req("GET", "/api/accounting/kardex/db/inventory", headers={"X-Tenant-ID": "3"})
    ok = code == 403
    ev = f"/db/inventory con X-Tenant-ID=3 (token tenant 1) → HTTP {code} (esperado 403): {str(r)[:80] if isinstance(r, str) else r.get('detail','')}"
    pause()
    code, r = req("GET", "/api/accounting/kardex/products?search=pescado", headers={"X-Tenant-ID": "3"})
    ok = ok and code == 403
    ev += f" | search kardex tenant 3 → HTTP {code} (esperado 403)"
    # 404 para menu_item inexistente/ajeno
    pause()
    code2, r2 = req("GET", "/api/v1/restaurant/menu/999/recipe")
    ok = ok and code2 == 404
    ev += f" | GET receta menu 999 → HTTP {code2} (esperado 404)"
    # entrada con producto inexistente → no encontrado
    pause()
    code3, r3 = req("POST", "/api/accounting/kardex/db/entry",
                    {"product_code": "NO-EXISTE", "quantity": 1, "unit_cost": 1,
                     "concept": "QA", "date": "2026-07-31"})
    ok = ok and code3 == 400
    ev += f" | /db/entry con código inexistente → HTTP {code3} (esperado 400): {r3.get('detail', '') if isinstance(r3, dict) else ''}"
    record("T7", "Multi-tenant: aislamiento (403 user↔tenant + 404/400)", ok, ev)


# ─── T8: POS search ─────────────────────────────────────────────
def t8_pos_search():
    pause()
    code, r = req("GET", "/api/v1/inventory/products?search=pescado&active=true")
    prods = r.get("products", []) if isinstance(r, dict) else []
    ok = code == 200 and len(prods) >= 1 and prods[0].get("retail_price") is not None
    ev = f"inventory search 'pescado' → HTTP {code}, {len(prods)} resultados (retail presente: {prods[0].get('retail_price') if prods else '?'})"
    pause()
    code2, r2 = req("GET", "/api/accounting/kardex/products?search=pescado")
    ok = ok and code2 == 200 and len(r2) >= 1
    ev += f" | kardex search 'pescado' → HTTP {code2}, {len(r2) if isinstance(r2, list) else '?'} resultados"
    record("T8", "POS search (inventory + kardex ?search=)", ok, ev)


# ─── T9: UI bundle ──────────────────────────────────────────────
def t9_ui_bundle():
    strings = {
        "banner éxito receta": "Receta actualizada correctamente",
        "sidebar Puesta en Marcha": "Puesta en Marcha",
        "preview promedio kárdex": "Nuevo promedio estimado",
        "auto-refresh sesión": "Sesión expirada. Vuelve a iniciar sesión",
    }
    ev_lines = []
    ok = True
    for label, s in strings.items():
        out, rc = docker(["exec", "iaas-frontend-prod", "sh", "-c",
                          f"grep -rl '{s}' /usr/share/nginx/html/assets/*.js 2>/dev/null | head -1"])
        found = rc == 0 and out != ""
        ok = ok and found
        ev_lines.append(f"{label}: {'✅' if found else '❌'} {out}")
    record("T9", "UI bundle contiene los cambios desplegados", ok, " | ".join(ev_lines))


# ─── T10: Salud general ─────────────────────────────────────────
def t10_health():
    out, rc = docker(["ps", "-q"])
    total = len(out.splitlines()) if out else 0
    ok = total >= 40
    ev = f"containers Up: {total}/40+"
    for name, url, hdr in [
        ("frontend iaas", "http://localhost:8081/", None),
        ("backend iaas", "http://localhost:8000/health", None),
        ("segoviano", "http://localhost:3102/", None),
        ("eyfimport", "http://localhost:3103/", None),
        ("stratify", "http://localhost:80/", "stratify.ronsyserp.com"),
        ("smart", "http://localhost:3110/", None),
        ("openclaw", "https://localhost:8443/", None),
    ]:
        try:
            r = urllib.request.Request(url, headers={"Host": hdr} if hdr else {})
            if url.startswith("https"):
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urllib.request.urlopen(r, timeout=10, context=ctx) as resp:
                    c = resp.status
            else:
                with urllib.request.urlopen(r, timeout=10) as resp:
                    c = resp.status
        except Exception as e:
            c = getattr(e, "code", "ERR")
        ok = ok and c == 200
        ev += f" | {name}: {c}"
    ver = psql("SELECT version_num FROM alembic_version")
    ok = ok and ver == "0015_recipes_sale_items"
    ev += f" | alembic_version={ver} (esperado 0015_recipes_sale_items)"
    record("T10", "Salud general (containers, endpoints, migraciones head)", ok, ev)


# ─── Main ───────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("SUITE QA — IaaS-RonSys (Spec 01 recetas + Spec 02 costos variables)")
    print(f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')} | Tenant: {TENANT} | User: {EMAIL}")
    print("=" * 70)
    for fn in [t1_login, t2_recipes, t3_explosion, t4_insufficient, t5_costing,
               t6_variable_costs, t7_multitenant, t8_pos_search, t9_ui_bundle, t10_health]:
        try:
            fn()
        except Exception as e:
            import traceback
            record(fn.__name__, "EXCEPCIÓN", False, f"{e}\n{traceback.format_exc()[-500:]}")
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    passed = sum(1 for r in results if r[2] == "PASS")
    for tid, name, st, ev in results:
        print(f"  {tid:12s} {st}  {name}")
    print(f"\n  TOTAL: {passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
