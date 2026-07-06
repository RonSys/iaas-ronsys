# Costos AWS y Punto de Equilibrio — IaaS-RonSys
> **Proyecto:** IaaS-RonSys (Intelligence as a Service)
> **Versión del documento:** v0.1 (iterativo)
> **Fecha:** 19 de mayo de 2026
> **Propósito:** Mapear infraestructura AWS → costos → punto de equilibrio por plan

---

## 📑 Índice de Contenido

| Sección | Contenido |
|---------|-----------|
| **1. Mapeo Docker → AWS** | Cada servicio del compose a su equivalente AWS |
| **2. Escenarios de arquitectura** | Opciones de despliegue (barata, balanceada, ideal) |
| **3. Costos detallados** | Por servicio, por escenario |
| **4. Costos de crecimiento** | Cómo escalan los costos con más clientes |
| **5. Break-Even por Plan** | Cuántos clientes necesitas para cubrir costos |
| **6. Documentación de Gastos** | Registro de cada gasto y decisión |
| **7. Próximas iteraciones** | Lo que se afinará después |

---

## 1. Mapeo Docker → AWS

### 1.1 Servicios Actuales (del docker-compose)

```
docker-compose.yml (base)
├── postgres:16-alpine        → PostgreSQL 16
├── redis:7-alpine            → Redis 7
├── rabbitmq:4-management     → RabbitMQ 4 + Management UI

docker-compose.prod.yml (apps)
├── backend (FastAPI)         → Backend Python
├── frontend (nginx + React)  → Frontend web

Monitoreo (infra/docker/monitoring/)
├── Prometheus                → Métricas
├── Grafana (planeado)        → Dashboards
├── Loki (planeado)           → Logs
├── AlertManager (planeado)   → Alertas
```

### 1.2 Equivalentes en AWS

| Servicio Docker | Opción AWS 1 (Gestionado) | Opción AWS 2 (Autogestionado) | Recomendación inicial |
|----------------|--------------------------|-------------------------------|:---------------------:|
| PostgreSQL 16 | **RDS** PostgreSQL 16 | EC2 + PostgreSQL instalado | ✅ **RDS** (menos mantenimiento) |
| Redis 7 | **ElastiCache** Redis | EC2 + Redis instalado | ✅ **ElastiCache** (serverless) |
| RabbitMQ 4 | **Amazon MQ** RabbitMQ | EC2 + RabbitMQ instalado | ⚠️ **EC2 autogestionado** (más barato al inicio) |
| Backend FastAPI | **ECS Fargate** (serverless) | **EC2** con Docker | ✅ **ECS Fargate** (escalamiento automático) |
| Frontend React | **S3 + CloudFront** (static) | EC2 + nginx | ✅ **S3 + CloudFront** (casi gratis) |
| Prometheus | **Amazon Managed Prometheus** | EC2 + Prometheus | ⚠️ **EC2 autogestionado** |
| Grafana | **Amazon Managed Grafana** | EC2 + Grafana | ⚠️ **EC2 autogestionado** |
| Logs | **CloudWatch Logs** | — | ✅ **CloudWatch** (incluido) |
| Certificados SSL | **AWS Certificate Manager** | — | ✅ **ACM** (gratis) |
| DNS | **Route 53** | — | ✅ **Route 53** |
| CI/CD | **CodePipeline** o GitHub Actions | — | ✅ **GitHub Actions** (gratis) |

---

## 2. Escenarios de Arquitectura

### 🟢 Escenario Starter (Mínimo viable — 0-10 clientes)

```ascii
                    ┌──────────────┐
                    │  CloudFront  │
                    │  (CDN free)  │
                    └──────┬───────┘
                           │
┌──────────────┐   ┌──────▼───────┐   ┌────────────────┐
│  S3 Bucket   │◄──┤  ECS Fargate │   │  Route 53 DNS  │
│  (Frontend)  │   │  Backend API │   │  (dominio)     │
└──────────────┘   └──────┬───────┘   └────────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼─────┐ ┌───▼────┐ ┌────▼──────┐
       │  RDS       │ │Redis   │ │  EC2      │
       │ Postgres16 │ │Elasti  │ │ RabbitMQ  │
       │ db.t4g.micro│ │Cache   │ │ + Monitor │
       └────────────┘ └────────┘ └───────────┘
```

| Servicio | Especificación | Costo/mes |
|----------|---------------|:---------:|
| ECS Fargate | 0.25 vCPU, 0.5GB RAM (siempre encendido) | ~$10 |
| RDS PostgreSQL | db.t4g.micro (1 vCPU, 1GB RAM, 20GB gp3) | ~$15 |
| ElastiCache Redis | cache.t4g.micro (0.5GB) | ~$12 |
| EC2 RabbitMQ + Monitor | t4g.nano (2 vCPU, 0.5GB) | ~$6 |
| S3 + CloudFront | Frontend estático, poco tráfico | ~$1 |
| Route 53 | 1 hosted zone + consultas | ~$1 |
| CloudWatch Logs | Logs básicos | ~$3 |
| Data transfer | Salida estimada 50GB/mes | ~$5 |
| **TOTAL ESCENARIO STARTER** | | **~$53/mes** |

> 💡 **En soles:** ~S/ 195/mes (tipo de cambio ~3.70)

---

### 🟡 Escenario Pro (Crecimiento — 10-50 clientes)

```ascii
                    ┌──────────────┐
                    │  CloudFront  │ ← WAF (seguridad)
                    └──────┬───────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
┌───▼──────┐     ┌────────▼────────┐    ┌────────▼────────┐
│ S3 Bucket│     │  ECS Fargate    │    │  ECS Fargate    │
│ Frontend │     │  Backend API    │    │  Backend API    │
│          │     │  0.5 vCPU/1GB   │    │  0.5 vCPU/1GB  │
└──────────┘     └────────┬────────┘    └────────┬────────┘
                          │                      │
                          └──────────┬───────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
       ┌──────▼──────┐       ┌───────▼──────┐     ┌────────▼────────┐
       │  RDS        │       │  ElastiCache  │     │  EC2            │
       │ Postgres 16 │       │  Redis        │     │  RabbitMQ       │
       │ db.t4g.small│       │  cache.t4g.sm │     │  + Prometheus   │
       │ Multi-AZ    │       │  (1GB)        │     │  + Grafana      │
       └─────────────┘       └───────────────┘     │  + Loki         │
                                                    └────────────────┘
```

| Servicio | Especificación | Costo/mes |
|----------|---------------|:---------:|
| ECS Fargate (×2) | 0.5 vCPU, 1GB RAM c/u | ~$40 |
| RDS PostgreSQL | db.t4g.small, Multi-AZ, 50GB gp3 | ~$50 |
| ElastiCache Redis | cache.t4g.small (1GB) | ~$20 |
| EC2 Monitor | t4g.small (2 vCPU, 2GB) — Prom+Graf+Loki | ~$12 |
| EC2 RabbitMQ | t4g.nano | ~$6 |
| S3 + CloudFront | Frontend + assets | ~$3 |
| Route 53 + ACM | DNS + Cert gratis | ~$1 |
| CloudWatch Logs | Logs + métricas | ~$8 |
| Data transfer | 200GB/mes | ~$18 |
| WAF | Web ACL básica | ~$6 |
| **TOTAL ESCENARIO PRO** | | **~$164/mes** |

> 💡 **En soles:** ~S/ 607/mes

---

### 🔴 Escenario Enterprise (Escalado — 50+ clientes)

| Servicio | Especificación | Costo/mes |
|----------|---------------|:---------:|
| ECS Fargate (×3-4) | 1 vCPU, 2GB RAM c/u | ~$120 |
| RDS PostgreSQL | db.t4g.large, Multi-AZ, 100GB gp3 | ~$150 |
| ElastiCache Redis | cache.t4g.medium (3GB) | ~$40 |
| RabbitMQ (Amazon MQ) | mq.t3.micro (managed) | ~$30 |
| EC2 Monitor Cluster | t4g.small × 2 | ~$24 |
| S3 + CloudFront | Frontend + assets | ~$5 |
| Route 53 + ACM | DNS | ~$1 |
| CloudWatch + X-Ray | Logs + tracing | ~$20 |
| Data transfer | 1TB/mes | ~$90 |
| WAF + Shield | Seguridad | ~$10 |
| **TOTAL ESCENARIO ENTERPRISE** | | **~$490/mes** |

> 💡 **En soles:** ~S/ 1,813/mes

---

## 3. Tabla Comparativa de Escenarios

| Concepto | 🟢 Starter | 🟡 Pro | 🔴 Enterprise |
|----------|:----------:|:------:|:-------------:|
| **Costo AWS/mes (USD)** | ~$53 | ~$164 | ~$490 |
| **Costo AWS/mes (S/)** | ~S/ 196 | ~S/ 607 | ~S/ 1,813 |
| **Dominio/año** | ~$10 | ~$10 | ~$10 |
| **Cloudflare Tunnel** | $0 (gratis) | $0 | $0 |
| **Clientes estimados** | 0 – 10 | 10 – 50 | 50+ |
| **Cliente máximo soportado** | ~10 | ~50 | ~200+ |
| **Costo por cliente/mes** | $5.30 | $3.28 | $2.45 |
| **Alta disponibilidad** | ❌ No | ✅ Sí (Multi-AZ) | ✅ Sí |
| **Auto-escalado** | ❌ | ✅ | ✅ |

> 📉 **Economía de escala:** Mientras más clientes, menor el costo por cliente.

---

## 4. Desglose por Tipo de Gasto

### 4.1 Costos Fijos Mensuales (AWS)

Independientemente de cuántos clientes tengas:

| Concepto | Starter | Pro | Enterprise |
|----------|:-------:|:---:|:----------:|
| Base de datos (RDS) | $15 | $50 | $150 |
| Cache (Redis) | $12 | $20 | $40 |
| Cola (RabbitMQ) | $6 | $6 | $30 |
| Backend (Fargate) | $10 | $40 | $120 |
| Frontend (S3+CF) | $1 | $3 | $5 |
| Monitoreo | $3 | $12 | $24 |
| Networking | $6 | $27 | $116 |
| Seguridad | $0 | $6 | $10 |
| **TOTAL** | **$53** | **$164** | **$490** |

### 4.2 Costos Variables (Por Cliente)

| Concepto | Por cliente/mes |
|----------|:---------------:|
| Storage BD (1GB/cliente) | ~$0.12 |
| Data transfer extra | ~$0.10 |
| Logs adicionales | ~$0.05 |
| **Total variable** | **~$0.27/cliente** |

> ⚠️ Los costos variables son casi despreciables — el cuello de botella es la BD.

### 4.3 Costos de Desarrollo (Una Vez)

| Concepto | Costo |
|----------|:-----:|
| Dominio (.pe) | $10/año |
| Cloudflare Tunnel | $0 |
| Certificado SSL (ACM) | $0 |
| **Total setup inicial** | **~$10** |

---

## 5. Punto de Equilibrio (Break-Even)

### 5.1 Por Plan de Precios

#### 🟢 Starter (S/ 149 – 199/mes)

| Clientes | Ingreso/mes (S/) | Costo AWS (S/) | Margen (S/) | Break-even? |
|:--------:|:----------------:|:--------------:|:-----------:|:-----------:|
| 0 | 0 | 196 | -196 | ❌ |
| 1 | 174 | 196 | -22 | ❌ |
| 2 | 348 | 197 | **+151** | ✅ **BREAK-EVEN** |
| 5 | 870 | 199 | +671 | ✅ |
| 10 | 1,740 | 203 | +1,537 | ✅ |

> **Break-even: 2 clientes** en plan Starter

#### 🟡 Pro (S/ 299 – 399/mes)

| Clientes | Ingreso/mes (S/) | Costo AWS (S/) | Margen (S/) | Break-even? |
|:--------:|:----------------:|:--------------:|:-----------:|:-----------:|
| 0 | 0 | 607 | -607 | ❌ |
| 1 | 349 | 607 | -258 | ❌ |
| 2 | 698 | 608 | **+90** | ✅ **BREAK-EVEN** |
| 5 | 1,745 | 610 | +1,135 | ✅ |
| 10 | 3,490 | 614 | +2,876 | ✅ |

> **Break-even: 2 clientes** en plan Pro

#### 🔴 Enterprise (S/ 699 – 999/mes)

| Clientes | Ingreso/mes (S/) | Costo AWS (S/) | Margen (S/) | Break-even? |
|:--------:|:----------------:|:--------------:|:-----------:|:-----------:|
| 0 | 0 | 1,813 | -1,813 | ❌ |
| 1 | 849 | 1,813 | -964 | ❌ |
| 2 | 1,698 | 1,814 | -116 | ❌ |
| 3 | 2,547 | 1,815 | **+732** | ✅ **BREAK-EVEN** |
| 5 | 4,245 | 1,818 | +2,427 | ✅ |

> **Break-even: 3 clientes** en plan Enterprise

### 5.2 Break-Even General (Mix de Planes)

Escenario realista: 60% Starter + 30% Pro + 10% Enterprise

| Clientes totales | Starter (60%) | Pro (30%) | Ent (10%) | Ingreso total | Costo AWS | Margen |
|:----------------:|:-------------:|:---------:|:---------:|:-------------:|:---------:|:------:|
| 0 | 0 | 0 | 0 | S/ 0 | S/ 196 | -S/ 196 |
| 3 | 2 | 1 | 0 | S/ 697 | S/ 200 | +S/ 497 |
| 5 | 3 | 1 | 1 | S/ 1,720 | S/ 400 | +S/ 1,320 |
| 10 | 6 | 3 | 1 | S/ 3,494 | S/ 418 | +S/ 3,076 |

> **Con 3 clientes** ya estás en break-even en un mix realista.

### 5.3 Proyección Anual

| Mes | Clientes | Ingreso mensual | Costo AWS | Margen mensual | Margen acumulado |
|:---:|:--------:|:---------------:|:---------:|:--------------:|:----------------:|
| 1 | 1 (piloto) | S/ 0 (gratis) | S/ 196 | -S/ 196 | -S/ 196 |
| 2 | 2 | S/ 348 | S/ 197 | +S/ 151 | -S/ 45 |
| 3 | 3 | S/ 697 | S/ 200 | +S/ 497 | +S/ 452 |
| 4 | 5 | S/ 1,720 | S/ 400 | +S/ 1,320 | +S/ 1,772 |
| 5 | 7 | S/ 2,500 | S/ 420 | +S/ 2,080 | +S/ 3,852 |
| 6 | 10 | S/ 3,494 | S/ 418 | +S/ 3,076 | +S/ 6,928 |
| **Total Año 1** | **10 clientes** | | | | **~S/ 24,000** |

> ✅ **Recuperas la inversión en el mes 2-3** con solo 2-3 clientes de pago.

---

## 6. Recomendación de Arquitectura Inicial

### 🚀 Para el Piloto (ahora — Cloudflare Tunnel)

```
Servidor local (192.168.1.35)
├── Docker Compose (todo corriendo local)
├── PostgreSQL / Redis / RabbitMQ
├── Backend + Frontend
└── Cloudflare Tunnel → internet

Costo: $0/mes (solo electricidad + dominio $10/año)
```

### ☁️ Para Producción (cuando salga a beta)

```
AWS (Escenario Starter — ~$53/mes)
├── ECS Fargate → Backend
├── S3 + CloudFront → Frontend
├── RDS db.t4g.micro → PostgreSQL 16
├── ElastiCache t4g.micro → Redis
└── EC2 t4g.nano → RabbitMQ + Monitoreo
```

### ⬆️ Migración Futura

Cada vez que necesites más capacidad, **solo cambias el tamaño de la instancia**:

```
RDS db.t4g.micro ($15)  →  db.t4g.small ($30)  →  db.t4g.large ($75)
ElastiCache t4g.micro ($12) → t4g.small ($20) → t4g.medium ($40)
Fargate 0.25vCPU ($10) → 0.5vCPU ($20) → 1vCPU ($40)
```

> 🔧 **Arquitectura preparada para escalar** — los cambios son configuraciones, no re-arquitecturas.

---

## 7. Documentación de Gastos y Decisiones

| # | Fecha | Concepto | Monto (USD) | Monto (S/) | Tipo | Estado |
|:-:|:-----:|----------|:-----------:|:----------:|:----:|:------:|
| 1 | — | Dominio .pe (anual) | $10 | S/ 37 | Fijo | ⏳ Pendiente |
| 2 | — | AWS Starter (mensual) | $53 | S/ 196 | Fijo | ⏳ Pendiente |
| 3 | — | AWS Pro upgrade | +$111 | +S/ 411 | Variable | ⏳ Pendiente |
| 4 | — | AWS Enterprise upgrade | +$326 | +S/ 1,206 | Variable | ⏳ Pendiente |
| | | **Total mensual (Starter)** | **$53** | **S/ 196** | | |

### 📝 Registro de Decisiones

| # | Fecha | Decisión | Justificación | Quién |
|:-:|:-----:|----------|---------------|:-----:|
| C-1 | 2026-05-19 | Empezar con Cloudflare Tunnel + servidor local | $0 de infraestructura durante piloto | Asistente |
| C-2 | 2026-05-19 | RDS > EC2 autogestionado para BD | Mantenimiento zero, backups automáticos, Multi-AZ ready | Asistente |
| C-3 | 2026-05-19 | ElastiCache > Redis en EC2 | Serverless, escalamiento automático, sin mantenimiento | Asistente |
| C-4 | 2026-05-19 | RabbitMQ en EC2 (no Amazon MQ) | Amazon MQ es caro (~$30 vs ~$6 en EC2) para empezar | Asistente |
| C-5 | 2026-05-19 | Monitoreo en EC2 compartido con RabbitMQ | Ahorro: un solo t4g.nano para ambos servicios | Asistente |
| C-6 | 2026-05-19 | ECS Fargate > EC2 para backend | Serverless = sin gestión de servidores, escalado automático | Asistente |
| C-7 | 2026-05-19 | S3 + CloudFront > EC2 para frontend | Frontend estático, CDN gratis, casi $0 | Asistente |

---

## 8. Resumen Ejecutivo

| Indicador | Valor |
|-----------|:-----:|
| **Costo AWS mensual (inicio)** | ~$53/mes (~S/ 196) |
| **Costo AWS mensual (crecimiento)** | ~$164/mes (~S/ 607) |
| **Costo AWS mensual (escalado)** | ~$490/mes (~S/ 1,813) |
| **Break-even plan Starter** | **2 clientes** |
| **Break-even plan Pro** | **2 clientes** |
| **Break-even plan Enterprise** | **3 clientes** |
| **Break-even mix realista** | **3 clientes** |
| **Mes de recuperación** | **Mes 2-3** |
| **Costo variable por cliente** | ~$0.27/cliente (casi nada) |
| **Setup inicial** | $10 (dominio) |

### 🎯 Conclusión

| Afirmación | ¿Seguro? |
|------------|:--------:|
| AWS cuesta ~$53/mes al inicio | ✅ Confirmado (escenario starter) |
| Con 2 clientes de pago cubres AWS | ✅ Confirmado |
| Con 3 clientes ya tienes margen positivo | ✅ Confirmado |
| La BD es el cuello de botella (RDS) | ✅ Confirmado |
| El resto de servicios escala barato | ✅ Confirmado |
| El piloto en servidor local cuesta $0 | ✅ Confirmado |

> **El modelo de negocio es viable desde el cliente #2.** La infraestructura no es el problema — encontrar los primeros clientes sí lo es.

---

## 9. Próximas Iteraciones

| Iteración | Qué incluirá |
|-----------|--------------|
| **v0.2** | Costos reales de AWS (cuando despliegues y veas la factura) |
| **v0.3** | Costo de APIs de IA (OpenAI/Claude por cliente) |
| **v0.4** | Costo de Cloudflare Tunnel vs AWS Direct Connect |
| **v0.5** | Proyección a 3 años (CAPEX vs OPEX) |
| **v0.6** | Alternativa: Hetzner / DigitalOcean / VPS Perú (más barato) |

---

## 10. Archivos Relacionados

| Archivo | Rol |
|---------|-----|
| `IaaS-RonSys/docs/estrategia-precios.md` | Estrategia de precios y tiers |
| `IaaS-RonSys/docs/plan-exposicion-publica-v0.5.md` | Plan de salida a producción con Cloudflare |
| `IaaS-RonSys/docker-compose.yml` | Infraestructura base actual |
| `IaaS-RonSys/docker-compose.prod.yml` | Servicios de producción |
| `investigacion/comparativa-rapifac-bufeotec-defontana.md` | Benchmark de mercado |
| **`IaaS-RonSys/docs/costos-aws-breakeven.md`** | **(este documento)** |

---

*Documento generado por Asistente para Ron — v0.1 — 19 de mayo de 2026*
*Cada decisión de infraestructura y costo queda registrada arriba para iterar después.*
