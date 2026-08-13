# 🧪 Simulación con Datos Ficticios — F1 WhatsApp en Vivo (respuesta a consulta del cliente)

- **Proyecto:** IaaS-RonSys — Cliente "El Segoviano"
- **Spec:** `docs/specs/03-delivery/04-spec-whatsapp-en-vivo-v0.1.md` (F1)
- **Fecha:** 2026-08-13
- **Consulta del cliente:** *"¿No pueden simular con datos ficticios lo pendiente de la Fase 1, para proseguir con las siguientes fases, y después hacemos las pruebas con datos reales?"*

---

## 1. Respuesta corta

**SÍ, se puede simular todo lo pendiente de la F1 con datos ficticios — y de hecho ya está hecho en un 90%.** El motor de WhatsApp lleva semanas funcionando en **modo dry-run** (simulación): se generan los eventos de pedido, se publican en la cola, el worker los procesa y "envía" las notificaciones **sin hacer llamadas reales a Meta** — todo se registra en logs como si se hubiera enviado. Lo que NO se puede simular es el **último kilómetro**: que un celular real reciba el mensaje de WhatsApp (eso exige la cuenta Meta real).

**Estrategia acordada:** simulamos con datos ficticios todo lo verificable ahora (flujos, lógica, botones, BSUID, config), lo documentamos como validado, y las únicas pruebas que quedan para "datos reales" son las que tocan físicamente la cuenta Meta (envío real + plantillas aprobadas). Así las siguientes fases (F2–F5) pueden avanzar sin esperar a Meta.

---

## 2. Qué se puede simular HOY (sin cuenta Meta) ✅

| # | Qué se simula | Cómo (herramienta) | Evidencia |
|---|---|---|---|
| 1 | Checkout de pedido con evento `delivery.confirmed` + `delivery.new_order` | Crear pedido de prueba en QA con datos ficticios (cliente "Cliente Demo", teléfono ficticio +51999999999, items ficticios) | Evento en RabbitMQ `iaas-tasks` + log del worker |
| 2 | Transiciones de estado (en cocina → listo → en camino → entregado → cancelado) | PATCH status en QA con pedido ficticio DLV-XXXX | Eventos `delivery.status_changed` + `delivery.cancelled` |
| 3 | **Envío simulado de las 5 notificaciones al cliente + 2 alertas al local** | `DryRunNotifier` (config sin token o `enabled=false`) — loguea "enviaría a X con plantilla Y" sin HTTP | Logs del worker: destinatario + plantilla + payload |
| 4 | **Plantillas (los 7 textos)** | Los textos reales de las plantillas se prueban como **strings** en el payload y en los logs (con variables {{1}}, {{2}} resueltas con datos ficticios) | Logs con el mensaje renderizado |
| 5 | Botones "Pedir por WhatsApp" / "Llamar" / "Ver mi pedido" | Landing QA `/menu/el-segoviano` con `contact` configurado con número ficticio +51 999 999 999 (wa.me/tel:) | Captura de pantalla / E2E Playwright |
| 6 | **BSUID** (columna nueva `delivery_orders.whatsapp_bsuid`) | Payload de evento con `bsuid: "PE.demo123"` ficticio → verificar que el worker lo persiste | SQL: `SELECT whatsapp_bsuid FROM delivery_orders` |
| 7 | **Config** en `companies.settings.whatsapp` (con token ficticio) | PATCH `/api/settings` con estructura completa pero valores demo | `GET /api/settings` devuelve la estructura; persistencia en BD |
| 8 | Switch dry-run ↔ real | `enabled: true` con token ficticio → el notifier intenta llamar a Meta y **falla de forma controlada** (error capturado, reintentos, DLQ) — verifica la ruta de fallo sin costo | Logs de error controlado + mensaje a DLQ |

**Resultado de la simulación:** todos los CA-F1 que no requieren Meta real quedan **validados con datos ficticios** (CA-F1.5/6/7/8/9/10/12/14/15 — ya verificados por JARVIS en el QA de cierre, 62 tests pass).

---

## 3. Qué NO se puede simular (requiere cuenta Meta real) 🔴

| Ítem | Por qué no se simula |
|---|---|
| **Entrega real del mensaje en un celular** | Meta entrega el mensaje solo con número registrado + token real + plantilla aprobada. La simulación termina en el "intento de envío" |
| **Aprobación de las 7 plantillas por Meta** | Es un proceso de revisión humana/algorítmica de Meta; no hay forma de simularlo. Solo se puede **enviar temprano** y esperar |
| **Número del negocio verificado en Cloud API** | Requiere el chip prepago del cliente + SMS de verificación real |
| **Costo real por mensaje** | Solo se factura con cuenta real; con ficticios no hay factura |

**Estos 4 puntos son los únicos pendientes para la F1 "completa"**, y dependen 100% del trámite Meta (ver `manual-servicio-meta-whatsapp-f1.md`).

---

## 4. Plan acordado: simular ahora → probar real después

```
HOY (sin Meta)                          CUANDO META ESTÉ LISTO
────────────────────                    ─────────────────────────────
✅ Simulación datos ficticios           🔴 QA en vivo (spec §3.9):
   - 62 tests pass (QA JARVIS)            1. dry-run con plantillas reales
   - Eventos → RabbitMQ → worker          2. enabled=true
   - DryRunNotifier logs                  3. 1 pedido real de prueba
   - Botones wa.me/tel en QA              4. rollback probado
   - BSUID persistido ficticio
   - Config cargada (token demo)
        │
        ▼
✅ F1 "validada por simulación"        →  🔴 F1 "completa en producción"
   → PERMITE AVANZAR F2-F5                (solo cuando Meta apruebe)
```

**Consecuencia importante (positiva para el cliente):** las **Fases 2, 3, 4 y 5 pueden avanzar** sin esperar a Meta, porque no dependen de la cuenta (F2/F4/F5 no tocan Meta; F3 toca Meta solo en la parte de confirmación por WhatsApp, que reutiliza lo de F1).

---

## 5. Evidencia de la simulación (dónde está documentada)

| Evidencia | Ubicación |
|---|---|
| 62 tests backend pass (16 F1 + regresión) | `apps/backend/tests/test_f1_whatsapp_vivo.py` + reporte QA de JARVIS (2026-08-13) |
| Validación dry-run en vivo (checkout → confirmed/new_order, transiciones, cancelación) | Bitácora Spec 03 §5 — entrada 2026-08-11 (verificación en vivo, cero HTTP) |
| Contratos de plantillas (textos y variables) | Spec 04 §3.3 |
| Config JSONB de ejemplo | Spec 04 §3.2 + manual §6 |
| Migración BSUID verificada (upgrade/downgrade) | `0017_whatsapp_bsuid.py` + commit `4a227bf` |

---

## 6. Compromiso de cierre (para el cliente)

1. Al terminar la simulación, el equipo entrega el **reporte de simulación F1** (este documento + evidencia de tests/logs).
2. Las pruebas con **datos reales** se ejecutan apenas Meta apruebe (checklist del manual §7, pasos 8–10) — sin costo adicional de desarrollo, es QA en vivo.
3. Mientras tanto, **el trámite Meta corre en paralelo** (cuello de botella externo) y **F2–F5 avanzan** sin bloqueo.

---

*Documento de simulación — Equipo IaaS-RonSys · 2026-08-13 · Respuesta a consulta del cliente sobre datos ficticios en F1.*
