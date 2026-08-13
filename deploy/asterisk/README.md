# 📞 Central Telefónica — Infraestructura Asterisk (F2, Spec 05 §3.3)

Servicio Docker `asterisk` (imagen `asterisk/asterisk:20`, A20 LTS) con
`network_mode: host` (D1: evita el docker-proxy UDP que degradaría RTP/jitter).
La configuración vive en `deploy/asterisk/conf/` (montada como `/etc/asterisk:ro`)
y las grabaciones MixMonitor en el volumen `asterisk_recordings`.

> ⚠️ **Estado actual**: infraestructura lista para QA con **SIP local de prueba**
> (patrón dry-run de F1). El **trunk SIP real depende del cliente** (número
> prepago + proveedor) — ver [Go-live](#go-live-trunk-real).

---

## 1. Levantar el servicio

```bash
docker compose up -d asterisk
docker compose logs -f asterisk        # verificar arranque sin errores
docker exec iaas-asterisk asterisk -rx "core show uptime"
docker exec iaas-asterisk asterisk -rx "core show channels"   # llamadas activas
```

Verificación de config cargada:

```bash
docker exec iaas-asterisk asterisk -rx "pjsip show endpoints"
docker exec iaas-asterisk asterisk -rx "module show like res_ari"   # ARI cargado
```

## 2. Simulación local SIN trunk (QA — patrón dry-run de F1)

No hace falta el trunk del proveedor para validar el flujo completo
(inbound/outbound + grabación R1 + eventos AMI → backend):

1. **Descomentar los endpoints QA** en `deploy/asterisk/conf/pjsip.conf`
   (extensiones `100` operador, `200`/`201` clientes de prueba, sección
   `SOLO QA`) y el contexto `[from-qa]` en `extensions.conf`.
2. **Reiniciar** el servicio: `docker compose restart asterisk`.
3. **Softphone** (Linphone / MicroSIP / Zoiper) apuntando a la IP del
   servidor (192.168.1.35 en LAN):
   - Cuenta QA-100 (operador): usuario `100`, password `qa-100-secret`
   - Cuenta QA-200 / QA-201 (clientes de prueba)
4. **Llamada de prueba**: el softphone QA-200 llama a la extensión `100`
   (o al contexto from-qa) → debe sonar en QA-100, grabarse en
   `asterisk_recordings` y generar eventos AMI (Newchannel → Newstate →
   Hangup) que el `call-bridge` reenvía al backend.

Con el `call-bridge` corriendo, la llamada aparece en el panel
"Central Telefónica" (`/restaurante/central`) en tiempo real y queda como
`CallRecord` en BD (CA-F2.1/CA-F2.2/CA-F2.8 sin trunk).

## 3. AMI / ARI (solo localhost, D3)

- **AMI** (eventos): `127.0.0.1:5038` — `manager.conf` (usuario/password
  placeholder; generar con `openssl rand -hex 24`).
- **ARI** (control/Originate): `127.0.0.1:8088` — `ari.conf` (credenciales
  placeholder; el `call-bridge` hace `POST /ari/channels` con basic auth).

Nunca exponer estos puertos: el `call-bridge` corre en la misma máquina
(`network_mode: host` o red interna).

## 4. fail2ban (D3)

Jail `asterisk-sip` listo en `deploy/asterisk/fail2ban/`. Instalación en el
host (una sola vez):

```bash
sudo cp deploy/asterisk/fail2ban/filter.d/asterisk-sip.conf /etc/fail2ban/filter.d/
sudo cp deploy/asterisk/fail2ban/jail.local /etc/fail2ban/jail.d/asterisk-sip.local
# Ajustar whitelist con las IPs reales del proveedor (ignoreip)
sudo systemctl restart fail2ban
sudo fail2ban-client status asterisk-sip
```

Reglas: 5 fallos de registro/invite → ban 15 min (regex de
`Registration from '.*' failed` y `SecurityEventAuthFailure`).

## 5. NAT / port-forward (pendiente del router del local)

En el router (IP pública **190.235.163.29** → servidor 192.168.1.35),
abrir SOLO:

| Puerto | Proto | Uso |
|---|---|---|
| 5060 | UDP | Señalización SIP (trunk) |
| 10000–10100 | UDP | RTP (audio) — acotado en `rtp.conf` |

AMI (5038) y ARI (8088) **NO** se exponen (D3). El port-forward depende del
router del local/cliente — sin él, el trunk real no puede entregar llamadas.

## 6. Prerrequisito RAM (go-live)

Servidor ronpk: 7.1 GB RAM total, **3.0 GB disponibles, swap 2.8/4 GB en
uso** (medición 2026-08-13). Asterisk idle ~150–250 MB + call-bridge
~50–100 MB **caben para QA con SIP local**, pero **+8 GB RAM es
prerrequisito antes del go-live con trunk real** (margen para picos y evitar
swap → jitter de audio).

## 7. Go-live (trunk real)

1. Cliente contrata el número + proveedor SIP peruano (4 canales, G.711).
2. Rellenar en `pjsip.conf`: `permit` con las IPs reales del proveedor (D3),
   `username`/`password` (generados por secret).
3. Quitar/descomentar los endpoints QA y `[from-qa]`.
4. Port-forward UDP 5060 + 10000–10100 en el router del local.
5. `companies.settings.calls` en BD: `enabled=true`, `dids=[<número>]`,
   `extensions=["100"]`, `recording=true`, `retention_days=90`.
6. Configurar `.env` del backend: `CALL_BRIDGE_TOKEN` (`openssl rand -hex 32`),
   `CALL_EVENTS_ALLOWED_IPS` (subred del bridge) y del bridge:
   `AMI_USER/AMI_PASS`, `ARI_USER/ARI_PASS`, `SERVICE_TOKEN`, `BACKEND_INTERNAL_URL`.
7. Prueba real: llamada → panel en vivo → convertir a pedido (DLV-).

## 8. Archivos

```
deploy/asterisk/
├── conf/
│   ├── asterisk.conf / modules.conf / logger.conf / http.conf   (base mínima)
│   ├── pjsip.conf        (trunk + transport + endpoints QA)
│   ├── extensions.conf   (from-pstn / from-internal / from-qa)
│   ├── rtp.conf          (10000–10100)
│   ├── manager.conf      (AMI, 127.0.0.1:5038)
│   └── ari.conf          (ARI, 127.0.0.1:8088)
└── fail2ban/
    ├── jail.local
    └── filter.d/asterisk-sip.conf
```
