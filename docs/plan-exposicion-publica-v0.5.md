# Plan de Exposición Pública — IaaS-RonSys v0.5

> **Versión:** v0.5 — Acceso público en fase de prueba
> **Objetivo:** Usuarios externos (posibles clientes) accedan al ERP desde internet vía HTTPS
> **Estado actual:** Servidor local `192.168.1.35:80` (HTTP, solo red local)
> **Proveedor:** Cloudflare Tunnel (no necesita abrir puertos ni IP fija)

---

## 🧱 Arquitectura

```
Usuario internet
      │
      ▼  HTTPS :443
 ☁️ Cloudflare (SSL automático + DDoS + CDN)
      │  ──── túnel cifrado ────
      ▼
 🖥️ Servidor .35 (corre cloudflared)
      │
      ├── localhost:80 (nginx → Frontend + Backend API)
      ├── PostgreSQL (:5432) — interno
      ├── Redis (:6379) — interno
      └── RabbitMQ (:5672) — interno
```

---

## 📋 Pasos

1 Comprar dominio + registrarse en Cloudflare 🧑‍💼 Ron
2 Commit + tag v0.5 (incluye TODO el desarrollo actual) 🚀 DevOps Agent
3 Instalar cloudflared + autenticar en el servidor 🚀 DevOps Agent
4 Crear túnel + configurar config.yml (localhost:80) 🚀 DevOps Agent
5 Configurar rutas DNS (dominio → túnel) 🚀 DevOps Agent
6 Probar túnel + instalar como servicio systemd 🚀 DevOps Agent
7 Fail2ban 🚀 DevOps Agent
8 Rate limiting + CORS 🚀 DevOps Agent + 🔧 Backend Agent
9 Formulario de feedback (endpoint + modal) 🔧 Backend Agent + 🎨 Frontend Agent
10 Pruebas de acceso desde internet 🧪 QA Agent

---

## 🧑‍💼 Paso 1 — Ron: Comprar dominio + Cloudflare

1. Ir a **https://dash.cloudflare.com**
2. Crear cuenta (gratis, solo email)
3. Comprar un dominio (desde Cloudflare mismo):
   - Ej: `ronsys.pe` ~$10/año
   - Ej: `elsegoviano.com` ~$10/año
   - Ej: `iaas-ronsys.com` ~$12/año
4. **Decirme el dominio elegido** para que arranque el DevOps Agent

> 💡 Si ya tenés dominio en otro proveedor (GoDaddy, Namecheap), solo cambiá los nameservers a los que Cloudflare te asigna.

---

## 🚀 Pasos 2-8 — DevOps Agent

### Paso 2: Commit + tag v0.5

Antes de desplegar, se consolida todo el desarrollo actual:

```bash
cd /home/ron/projectos/IaaS-RonSys
git add -A
git commit -m "v0.5 — Snapshot pre-exposición pública"
git tag -a v0.5 -m "v0.5 — Exposición pública + feedback usuarios"
```

> 📌 La rama `main` sigue recibiendo commits después de v0.5. La versión desplegada es el tag `v0.5`. Futuros cambios se despliegan como v0.6, v0.7, etc.

---

## 🚀 Pasos 2-7 — DevOps Agent

### Paso 2: Instalar cloudflared + autenticar

```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared
cloudflared tunnel login
```

### Paso 3: Crear túnel + config.yml

```bash
cloudflared tunnel create ronsys-tunnel

cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: ronsys-tunnel
credentials-file: /root/.cloudflared/ronsys-tunnel.json
ingress:
  - hostname: MIDOMINIO.pe
    service: http://localhost:80
  - hostname: www.MIDOMINIO.pe
    service: http://localhost:80
  - service: http_status:404
EOF
```

### Paso 4: Rutas DNS

```bash
cloudflared tunnel route dns ronsys-tunnel MIDOMINIO.pe
cloudflared tunnel route dns ronsys-tunnel www.MIDOMINIO.pe
```

### Paso 5: Probar + servicio

```bash
cloudflared tunnel run ronsys-tunnel
sudo cloudflared service install
sudo systemctl status cloudflared
```

### Paso 6: Fail2ban

```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Paso 7: Rate limiting + CORS (con Backend Agent)

- DevOps: Configurar rate limiting en nginx (límite de requests/min)
- Backend: Configurar CORS para el dominio público

---

## 🔧🎨 Paso 8 — Backend + Frontend Agent

| Agente | Qué hace |
|--------|----------|
| 🔧 Backend Agent | Endpoint `POST /api/feedback` que guarda en tabla `feedback` (nombre, mensaje, created_at) |
| 🎨 Frontend Agent | Botón flotante "💬 Enviar sugerencia" → modal con campos nombre + mensaje → envía al endpoint |

---

## 🧪 Paso 9 — QA Agent

Valida:
- ✅ HTTPS funcionando desde internet (candado verde)
- ✅ Login desde dispositivo externo
- ✅ Formulario de feedback recibe datos
- ✅ Carga inicial de la app
- ✅ Navegación básica (Dashboard, Restaurante, Ferretería)

---

## 🗺️ Pipeline

```
🧑‍💼 Ron (paso 1: dominio + Cloudflare)
  └──→ 🚀 DevOps Agent (paso 2: commit + tag v0.5)
          └──→ 🚀 DevOps Agent (pasos 3-7: tunnel + seguridad)
                  │
                  ├── 🔧 Backend Agent (paso 8: CORS)
                  └── 🎨 Frontend Agent + 🔧 Backend Agent (paso 9: feedback)
                  │
                  └──→ 🧪 QA Agent (paso 10: validación)
                          │
                          🚀 v0.5 LIVE
```

---

## 🆚 ¿Qué reemplaza Cloudflare Tunnel?

| Ya no se necesita | Porque Cloudflare... |
|-------------------|---------------------|
| ❌ IP fija / DDNS | El túnel no expone tu IP |
| ❌ Port Forwarding en router | El túnel sale del servidor a Cloudflare (conexión saliente) |
| ❌ Certbot / Let's Encrypt | SSL automático incluido |
| ❌ nginx con HTTPS | nginx queda en HTTP local, Cloudflare termina SSL |
| ❌ Abrir puertos 80/443 en UFW | No se expone nada, solo SSH |

---

## 📁 Archivo relacionado

- `docs/backlog/deuda-tecnica-fase0.md`

---

*Plan generado: 2026-05-15. Versión target: v0.5*
