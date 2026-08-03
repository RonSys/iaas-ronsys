# 🧪 Guía de Pruebas E2E — Credenciales, MCP Playwright y Acceso desde la Laptop (.39)

- **Fecha:** 2026-08-03
- **Proyecto:** IaaS-RonSys — Módulo Delivery / Dark Kitchen (Fase A en producción)
- **Producción:** https://www.ronsyserp.com · Landing delivery: `/menu/el-segoviano`
- **Servidor:** ronpk (192.168.1.35) — donde corre el Gateway de OpenClaw y el deploy
- **Laptop:** 192.168.1.39 — donde Ron quiere **ver cómo el agente interactúa con la web**

---

## 1. 🔑 Credenciales de los Tenants (producción — verificado en BD)

### 1.1 Tenants existentes (tabla `companies`)

| ID | Nombre | Slug | Tipo | Nota |
|---|---|---|---|---|
| 1 | **Admin Tenant** | `el-segoviano` | restaurant | **Tenant activo del delivery** (landing pública) |
| 3 | El Segoviano | `NULL` | restaurant | Cevichería (sin slug aún) |
| 5 | Ferretería El Segoviano | `NULL` | hardware | Demo ferretería |

### 1.2 Usuarios por tenant (producción — verificado en BD)

| Email | Password | Rol | Tenant | Uso recomendado |
|---|---|---|---|---|
| `admin@elsegoviano.pe` | `admin123` | admin | 1 (Admin Tenant) | ✅ **Principal para probar todo**: panel staff delivery, settings, POS, métricas |
| `mesero@elsegoviano.pe` | `mesero123` | operator | 1 | Mesas / toma de pedidos |
| `cocinero@elsegoviano.pe` | `cocinero123` | operator | 1 | Kanban de cocina |
| `test@elsegoviano.pe` | *(seed test)* | operator | 1 | Usuario de prueba genérico |
| `admincevicheria@elsegoviano.pe` | *(seed tenant 3)* | admin | 3 (El Segoviano) | Cevichería real |
| `mesero1@elsegoviano.pe` | `mesero123` | operator | 3 | Mesero cevichería |
| `cocinero1@elsegoviano.pe` | `cocinero123` | operator | 3 | Cocinero cevichería |
| `ferretero@elsegoviano.pe` | `ferreteria123` | admin | 5 (Ferretería) | Demo hardware |
| `admin@iaas.com` | `Admin2026!` | superadmin | — | **Superadmin del sistema** (seed_superadmin) |
| `demo@iaas.com` | `Demo2026!` | — | — | Usuario demo (corregido por seed_superadmin) |

> ⚠️ **Para tus pruebas de delivery usa `admin@elsegoviano.pe` / `admin123`** (tenant 1 = slug `el-segoviano`, el único con landing pública y Zona 1 configurada). El superadmin (`admin@iaas.com`) es para gestión global de tenants.

### 1.3 URL de prueba

- Landing pública (cliente): **https://www.ronsyserp.com/menu/el-segoviano**
- Panel staff (operación): **https://www.ronsyserp.com/restaurante/delivery** (login con admin@elsegoviano.pe)
- API pública (sin auth): `GET https://www.ronsyserp.com/api/public/el-segoviano/menu` y `/zones`
- API staff: `POST /api/auth/login` → Bearer token → `/api/v1/delivery/*`

---

## 2. 🧠 Investigación: MCP de Playwright — ¿conviene?

### 2.1 Qué es

**Playwright MCP** (`@playwright/mcp`) es un servidor MCP oficial de Microsoft que da a un agente de IA **control total de un navegador real** (Chrome/Chromium): navegar, hacer clic, escribir, leer la página (vía árbol de accesibilidad, no pixeles), tomar screenshots. Es la forma estándar de "ver y tocar" una web desde un agente.

### 2.2 Opciones comparadas

| Opción | Qué es | Ventaja | Desventaja | Veredicto |
|---|---|---|---|---|
| **A. Browser integrado de OpenClaw** | Plugin bundled `browser` (Playwright-backed) con CLI `openclaw browser` + tool de agente | Ya viene con OpenClaw; perfil aislado; snapshots/screenshots/PDF; sin dependencias extra | **Hoy está deshabilitado** (`plugins.allow` no incluye `browser`); necesita Chromium instalado en el servidor | ⭐ **Recomendado** — cero MCP extra, es el camino nativo |
| **B. MCP Playwright** (`@playwright/mcp` + `mcporter`) | Servidor MCP externo vía npx | Estándar Microsoft, multi-cliente (VS Code, Claude, etc.) | Requiere instalar node package + configurar MCP en OpenClaw (mcporter está `enabled: false`); más piezas que mantener | 👍 Bueno si quieres usarlo también desde VS Code/Cursor |
| **C. Playwright CLI + SKILLS** (`playwright-cli`) | CLI con skills (recomendación oficial para coding agents) | Más eficiente en tokens; comandos concisos | Menos "estado persistente" que MCP | 👍 Alternativa ligera para automatización de tests |
| **D. Screenshots + image tool** | Yo navego vía HTTP/API y tomo screenshots con `image` | Cero instalación | No interactúa con el DOM real; limitado | ❌ Solo como respaldo |

### 2.3 Estado ACTUAL del servidor (después de la implementación — 2026-08-03)

- ✅ Node 22 + npx disponibles (`/usr/bin/npx`)
- ✅ cloudflared corriendo (túnel Cloudflare activo → ronsyserp.com ya es público)
- ✅ Ping a la laptop .39: **0% pérdida** (red local OK)
- ✅ **Chrome for Testing 151 instalado**: `/home/ron/.local/share/chrome-linux64/chrome` (standalone, no depende del OS)
- ✅ **Monitor físico conectado** (DP-2, 1366x768) + Xorg + openbox + lightdm (autologin como ron)
- ✅ **Plugin `browser` de OpenClaw habilitado** (en `plugins.allow`) + `browser.enabled: true` con `headless: false`, `noSandbox: true` (AppArmor userns=1) y `executablePath` al CfT 151
- ✅ **Gateway corre con `DISPLAY=:0`** (env persistente en `/home/ron/.openclaw/gateway.systemd.env`)
- ✅ Browser de OpenClaw abriendo en el monitor y **controlado por el agente** (verificado en vivo: login → dashboard → panel Delivery)
- ⚠️ Playwright npm NO soporta ubuntu26.04-x64 (por eso se usa CfT standalone)

---

## 3. 🛠️ Plan propuesto — Ver cómo el agente interactúa con la web desde la .39

### Opción A (RECOMENDADA): Browser integrado de OpenClaw + screenshots al chat

Ron ve el avance **en el chat** (screenshots) y, si quiere, en vivo vía túnel.

**Pasos:**
1. **Instalar Chromium en el servidor** (headless shell basta):
   ```bash
   cd /mnt/disco_ssd/projectos/IaaS-RonSys/apps/web  # o cualquier dir
   npx playwright install chromium --with-deps   # instala Chromium + dependencias del SO
   ```
2. **Habilitar el plugin browser en OpenClaw** (`~/.openclaw/openclaw.json`):
   ```json5
   {
     plugins: { allow: [ "...actuales...", "browser" ] },
     browser: { enabled: true },
     tools: { profile: "coding", alsoAllow: [ "browser", "browser_navigate", "browser_snapshot", "browser_act" ] }
   }
   ```
3. **Reiniciar Gateway** (`openclaw gateway restart` o `~/gateway-restart.sh`).
4. **Verificar**: `openclaw browser --browser-profile openclaw doctor --deep`.
5. **Flujo de uso**: yo abro el browser aislado, navego a `https://www.ronsyserp.com/menu/el-segoviano`, tomo **screenshots** y te los envío por el chat (webchat/WhatsApp) → los ves desde la .39 sin instalar nada.
6. **Opcional — ver en vivo desde la .39**: exponer el puerto de control del browser vía túnel Cloudflare (ruta nueva, ej. `browser.ronsyserp.com`) o con Xvfb + noVNC para ver la pantalla real.

### Opción B: MCP Playwright (`@playwright/mcp`) — para usar también en VS Code

1. `npm install -g @playwright/mcp` (o vía npx sin instalar).
2. Configurar en OpenClaw el cliente MCP (`mcporter.enabled: true` + registro del server `playwright` con `npx @playwright/mcp@latest`).
3. `npx playwright install chromium`.
4. Desde VS Code/Cursor en la .39, conectar el mismo server MCP (config estándar `mcpServers.playwright`) — Ron puede **ver y controlar el mismo navegador** que el agente si se usa `--headful` y el puerto se expone por túnel.

### Opción C: Entorno local de pruebas (QA) accesible desde la .39

Ya existe el entorno QA del proyecto (backend :8001, frontend Vite :5173). Para pruebas sin tocar prod:

1. Levantar QA: `./deploy.sh --env qa` (puertos 8001/5173, BD `iaas_ronsys_qa`).
2. Exponerlo por el túnel Cloudflare existente: agregar ruta en `config.yml` de cloudflared, ej. `qa.ronsyserp.com → localhost:5173`.
3. Correr la suite QA: `python3 scripts/qa/test_suite.py`.
4. Hacer E2E con el browser (Opción A/B) apuntando a `https://qa.ronsyserp.com`.

> 💡 El túnel .35→.39 ya existe (ronsyserp.com). Desde la .39 solo se abre el navegador a la URL pública; **no hace falta abrir puertos en la .39** — todo sale por Cloudflare.

---

## 4. 📋 Recomendación final — ✅ IMPLEMENTADO (Opción A, monitor físico)

**Lo que Ron eligió:** monitor físico en el .35 (misma habitación) — cero túneles, cero streaming.

**Resultado (verificado 2026-08-03 ~07:00 UTC):**
1. ✅ Monitor conectado (DP-2, 1366x768) + Xorg/openbox/lightdm con autologin → el escritorio aparece solo al bootear
2. ✅ Chrome for Testing 151 instalado en `/home/ron/.local/share/chrome-linux64/chrome` (flags: `--no-sandbox --no-first-run --user-data-dir`)
3. ✅ Plugin browser de OpenClaw habilitado (`plugins.allow` + `browser.enabled` con `headless:false`, `noSandbox:true`, `executablePath`)
4. ✅ Gateway relanzado con `DISPLAY=:0 XAUTHORITY=/home/ron/.Xauthority` (env persistente en `gateway.systemd.env`)
5. ✅ **Prueba en vivo exitosa**: el agente navegó `https://www.ronsyserp.com/login`, hizo login con `admin@elsegoviano.pe`, llegó al Dashboard y al panel **Delivery Nocturno** (`/restaurante/delivery`) — todo visible en el monitor en tiempo real

**Desde la laptop .39:** Ron ve el navegador del agente **directamente en el monitor del servidor** (misma habitación). No requiere instalación en la .39 ni túneles extra.

**Para el futuro (si se quiere ver desde la .39 sin estar en la habitación):** MCP Playwright (Opción B) o noVNC (streaming) siguen disponibles como opciones, pero ya no son necesarias para el flujo actual.

---

## 5. 🔗 Referencias

- Playwright MCP (oficial): https://github.com/microsoft/playwright-mcp (config: `npx @playwright/mcp@latest`)
- Docs OpenClaw — Browser: `/home/ron/.npm-global/lib/node_modules/openclaw/docs/tools/browser.md`
- Docs OpenClaw — Browser control API: `/home/ron/.npm-global/lib/node_modules/openclaw/docs/tools/browser-control.md`
- Seed de usuarios demo: `docs/reports/qa-validation-seed-demo-users*.md` · `apps/backend/scripts/seed_superadmin.py`
- Deploy: `deploy.sh --env qa|prod` · Túnel: `cloudflared.service` (config en el servidor)
