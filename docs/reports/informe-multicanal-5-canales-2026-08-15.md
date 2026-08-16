---
titulo: "IaaS-RonSys — Roadmap Multicanal (5 canales): Estado y Pendientes"
fecha: 2026-08-15
proyecto: IaaS-RonSys (ERP El Segoviano)
categoria: roadmap / canales de atencion / IA
tags: [multicanal, whatsapp, llamadas, agenda, recepcionista-ia, cloudcode]
relacionado:
  - informe-cliente: "docs/reports/informe-ejecutivo-cliente-2026-08.md"
  - reel-inspiracion: "/home/ron/investigacion/07-varios/20260815_Video-by-andreaeskailet_DcEGTmVonzh.md"
---

# 📱 IaaS-RonSys — Roadmap Multicanal (5 canales): Estado y Pendientes

> **Contexto:** Ron quiere que el ERP (IaaS-RonSys) llegue a tener los **5 canales de atención** que muestra el reel de CloudCode (WhatsApp, Instagram, web, email y llamadas telefónicas), con la regla de prioridad: **1) que WhatsApp funcione de verdad (envío real) → 2) canal llamadas** (agente que contesta, consulta la agenda, reserva la cita, con grabación + transcripción).
>
> **Metodología del proyecto:** Spec Anchor (SDD) — la spec está sincronizada con el código; ningún requerimiento se codea sin estar registrado en el informe ejecutivo y sin su spec actualizada.
>
> **Fuentes:** informe ejecutivo al cliente (2026-08-10/12), índice de specs (verificado 2026-08-14, head `0020_assistant`), inspección de código del backend, y el reel de CloudCode como referencia de producto.

---

## 1️⃣ Estado actual por canal 🗺️

| Canal | Estado | Spec / Módulo | Pendiente para que funcione |
|---|---|---|---|
| 🌐 **Web** | ✅ **OPERATIVO** | Landing + menú público delivery + panel del dueño + chat IA (F5) | — |
| 💬 **WhatsApp** | 🟡 **F1 desplegada (2026-08-13)** | `docs/specs/03-delivery/04-spec-whatsapp-en-vivo-v0.1.md` (F1) + motor de eventos Fase B (dry-run) | **Solo el trámite externo Meta del cliente** + activar envío real del motor (ver §2) |
| ☎️ **Llamadas** | 🟡 **F2 + F3 desplegadas (2026-08-13)** | `05-spec-central-telefonica-v0.1.md` (F2) + `06-spec-recepcionista-ia-v0.1.md` (F3) | Trunk SIP real + port-forward UDP + RAM; **proveedor de voz IA (STT/TTS)**; PoC llamadas reales; **falta módulo agenda/citas** para el flujo completo del reel (ver §3) |
| 📸 **Instagram** | ❌ **NO existe** | — | Diseño + desarrollo desde cero (ver §4 propuesta) |
| 📧 **Email** | ❌ **NO existe** | — | Diseño + desarrollo desde cero (ver §4 propuesta) |

**Lectura clave:** el proyecto ya tiene 3 de 5 canales (web, WhatsApp, llamadas) con backend desplegado. Lo que falta es mayormente **externo/trámite** (Meta, SIP, proveedor de voz) y **2 canales nuevos** (Instagram, email) + el **módulo de agenda/citas** para completar el flujo telefónico del reel.

---

## 2️⃣ Canal WHATSAPP — qué falta exactamente (prioridad #1)

### ✅ Ya implementado y desplegado (F1, 2026-08-13)
- Botones **"Pedir por WhatsApp" / "Llamar"** en landing y campañas (wa.me con BSUID)
- Migración `0017` (`whatsapp_bsuid`), endpoint público `contact` en `GET /api/public/{slug}/menu`
- **Motor de eventos WhatsApp (Fase B)**: colas RabbitMQ, avisos al cliente (confirmado, en cocina, en camino, entregado, cancelado) + alertas al local — **verificado en producción en modo dry-run** (2026-08-11) sin costo ni cuenta Meta
- 16 tests + E2E en caliente en prod

### ⏳ Pendiente — TODO es el trámite externo de Meta (no hay desarrollo interno pendiente)
Según `docs/manuales/manual-servicio-meta-whatsapp-f1.md` (manual completo ya escrito):
1. **Número prepago del negocio** (chip celular del cliente, titular El Segoviano — regla dura: NUNCA usar números personales del equipo)
2. **Cuenta Meta Business Manager** del cliente + **verificación del negocio** (RUC, dominio ronsyserp.com — toma días a semanas, iniciar día 1)
3. **App en Meta for Developers** (tipo Business) + producto **WhatsApp Cloud API** → App ID/Secret
4. **Registro del número** + aprobación de **7 plantillas Utility** (Meta 24h window)
5. **Carga de configuración** en `companies.settings.whatsapp` (JSONB) — solo config, sin deploy
6. **Activar el envío real** del motor de eventos (hoy dry-run) → conectar credenciales Cloud API

> ⚠️ Sin la cuenta Meta: el sistema sigue en dry-run (simulación validada en `docs/reports/simulacion-f1-datos-ficticios-2026-08-13.md`). El desarrollo NO bloquea — bloquea el trámite del cliente.

---

## 3️⃣ Canal LLAMADAS — estado y el hueco de "agenda + cita" ⭐

### ✅ Ya implementado y desplegado (F2 + F3, 2026-08-13)
- **F2 Central Telefónica**: Asterisk (Docker host `mlan/asterisk:20.15.2`), call-bridge AMI/ARI, CallRecords (migración `0018`), panel `/restaurante/central` (WS en vivo, historial, click-to-call, **convertir llamada → pedido** con kárdex/contabilidad). QA en vivo P6 con SIP local ✅
- **F3 Recepcionista IA**: migración `0019_voice_ai` (`call_transcriptions` + columnas IA), `voice_ai_service` (máquina de estados), `voice_bridge` (Stasis + RTP→WS), endpoints `/api/v1/calls/{id}/transcript|ai-state|ai-context|transfer|complete` + alias `/ai-calls/*`, panel IA. Suite 516 passed + E2E en caliente (transcripción + transferencia con contexto)
- **Lo que la IA de voz ya hace hoy:** contesta el teléfono, **toma el pedido** (notas + dirección), confirma por WhatsApp, **graba y transcribe**, transfiere a humano con contexto, y **el pedido entra solo al sistema** (crea pedido delivery DLV- con zona sugerida por distrito, kárdex, contabilidad)

### ⏳ Pendiente — externo (no bloquea desarrollo)
- **Trunk SIP real del cliente** + port-forward UDP 5060/10000-10100 en el router del local (documentado en spec F2)
- **+8 GB RAM recomendados** antes del go-live con trunk real (hoy 3.0 GB libres, swap 2.8/4 GB en uso)
- **Proveedor de voz IA (STT/TTS)** para el agente (hoy el bridge está listo; falta el proveedor) + **PoC de 2 semanas con llamadas reales**

### 🟥 HALLAZGO: NO existe módulo de agenda/citas (el hueco del reel)
- **Verificado en código:** no hay modelo `Reservation`/`Appointment` en `apps/backend/app/adapters/db/models/`; el grep de `appointment|agenda|booking` no arroja resultados en backend.
- Existen estados de **mesa "reservada"** en el módulo restaurante (flujo de salón), pero **no es una agenda de citas consultable** por la IA.
- `voice_ai_service.py` (intents/contexto) está enfocado en **pedidos** (notas, dirección, zona), NO en **citas**.
- **Consecuencia:** el flujo del reel *"el agente coge la llamada, consulta la agenda y reserva la cita"* **no se puede cumplir hoy** con el código existente — falta el dominio de agenda/citas.
- **Acción propuesta:** nuevo requerimiento **F6 "Agenda de Citas"** (módulo `appointments`: crear/consultar/cancelar, slots por local, integración con la F3 para que el agente de voz consulte disponibilidad y reserve, notificación de confirmación). Se registra en el informe ejecutivo §5.3 y se crea su spec (Spec Anchor obligatorio) antes de codear.

---

## 4️⃣ Canales NUEVOS (Instagram y Email) — propuesta inicial

### 📸 Instagram
- **Realidad técnica:** Instagram no permite mensajes directos automatizados sin **cuenta Instagram Business** + integración con la **Graph API de Meta** (Messenger/IG Direct API). Alternativa más realista a corto plazo: **DM con respuesta automática** vía IG Business + Meta Graph API (requiere el mismo Business Manager del trámite WhatsApp → sinergia).
- **Opción B (rápida):** botones/link del menú público en la bio del IG + campañas IG con enlace de atribución (ya existe el sistema de campañas con ROAS) → sin API, pero sin chatbot en IG.
- **Opción C (como el reel):** plataforma multicanal tipo CloudCode (n8n/CloudCode) orquestando IG + WhatsApp. Evaluar si conviene construir o integrar.

### 📧 Email
- **Opción A:** motor de emails transaccionales propio (SMTP + plantillas) para confirmaciones de pedido/citas — reutiliza el motor de eventos (RabbitMQ) del WhatsApp.
- **Opción B:** proveedor transaccional (Resend/SendGrid/Brevo como el reel) con webhook de estado.
- Recomendación: **Opción A primero** (sin costo, mismo patrón del motor WhatsApp dry-run), Opción B cuando escale.

---

## 5️⃣ Hoja de ruta sugerida (prioridades)

| Orden | Hito | Tipo | Esfuerzo |
|---|---|---|---|
| 1 | **Canal WhatsApp REAL**: trámite Meta con el cliente (número prepago + Business Manager + verificación + app + 7 plantillas) + activar motor dry-run → real | Externo (cliente) + config | Días a semanas (depende de Meta) |
| 2 | **Módulo Agenda de Citas (F6)** — dominio `appointments` + spec + integración con F3 (agente consulta/reserva) | Desarrollo (con Jarvis) | ~1-2 semanas (estimar con Jarvis) |
| 3 | **Proveedor voz IA (STT/TTS)** para F3 + PoC llamadas reales | Externo/proveedor + integración | Semanas |
| 4 | **Canal Email** (motor SMTP propio con plantillas, patrón dry-run primero) | Desarrollo | ~1 semana |
| 5 | **Canal Instagram** (Graph API con el Business Manager de Meta + sinergia con WhatsApp) | Desarrollo + trámite | 2-4 semanas |
| 6 | Franquicia conectada (F4, ya propuesta) — activar cuando el modelo funcione en 1 local | Desarrollo | — |

> **Regla Spec Anchor:** cada hito de desarrollo (F6, email, Instagram) debe registrarse primero en `docs/reports/informe-ejecutivo-cliente-2026-08.md` §5.3 y crear/actualizar su spec en `docs/specs/`, antes de codear.

---

## 6️⃣ Conexión con el reel de CloudCode (referencia de producto)

| Funcionalidad del reel | En IaaS-RonSys hoy |
|---|---|
| Chatbot WhatsApp sin N8N | ✅ F1 (WhatsApp en vivo + motor de eventos) — falta solo el trámite Meta |
| 5 canales: WhatsApp, IG, web, email, teléfono | 🌐✅ web · 💬🟡 WhatsApp · ☎️🟡 llamadas · ❌ IG · ❌ email |
| Agentes configurables por canal | 🟡 Parcial: agente de voz (F3) y agente de consultas (F5) son por dominio, no por canal |
| Modo de entrenamiento (prueba antes de enviar) | ❌ No existe — buena idea a futuro (dry-run actual es similar en espíritu) |
| Plantillas Meta oficiales (ventana 24h, sin baneo) | ✅ 7 plantillas Utility en el trámite F1 |
| CRM con ficha del cliente (etiquetas, historial, resumen) | 🟡 El ERP tiene clientes/pedidos, pero no ficha CRM con etiquetas — oportunidad |
| RAG vectorizado de archivos | 🟡 F5 "Pregúntale al Sistema" usa NL2SQL controlado (no RAG) — RAG sería ampliación |
| ☎️ Agente contesta, consulta agenda, reserva cita, graba + transcribe | 🟡 Graba + transcribe + toma pedidos ✅ · **agenda/citas ❌ (F6 pendiente)** |

---

## 7️⃣ Referencias

- Informe ejecutivo al cliente: `/home/ron/projectos/IaaS-RonSys/docs/reports/informe-ejecutivo-cliente-2026-08.md`
- Índice de specs (Spec Anchor): `/home/ron/projectos/IaaS-RonSys/docs/specs/README.md`
- Spec F1 WhatsApp: `/home/ron/projectos/IaaS-RonSys/docs/specs/03-delivery/04-spec-whatsapp-en-vivo-v0.1.md`
- Manual trámite Meta: `/home/ron/projectos/IaaS-RonSys/docs/manuales/manual-servicio-meta-whatsapp-f1.md`
- Spec F2 Central Telefónica: `/home/ron/projectos/IaaS-RonSys/docs/specs/03-delivery/05-spec-central-telefonica-v0.1.md`
- Spec F3 Recepcionista IA: `/home/ron/projectos/IaaS-RonSys/docs/specs/03-delivery/06-spec-recepcionista-ia-v0.1.md`
- Spec F5 Pregúntale al Sistema: `/home/ron/projectos/IaaS-RonSys/docs/specs/06-asistente-ia/08-spec-preguntale-al-sistema-v0.1.md`
- Reel CloudCode (inspiración): `/home/ron/investigacion/07-varios/20260815_Video-by-andreaeskailet_DcEGTmVonzh.md`
- Simulación F1 dry-run: `/home/ron/projectos/IaaS-RonSys/docs/reports/simulacion-f1-datos-ficticios-2026-08-13.md`

---
*Informe generado por Asistente (chatbot) el 2026-08-15, con inspección de código + specs + informe ejecutivo. **Validado por JARVIS (2026-08-15) contra código real, specs 04/05/06 y git** — ver §8.*

---

## 8️⃣ Validación de JARVIS (2026-08-15) ✅ — confirmaciones y matices

> Jarvis verificó contra código real, specs (04/05/06) y git. Confirma TODO lo anterior y agrega precisión:

### WhatsApp (F1) — detalles finos
- Motor completo verificado en prod dry-run: publicador RabbitMQ (`notify_events.py`), worker con **reintentos 3× + DLQ**, `MetaCloudNotifier` real implementado (HTTP httpx — solo espera token/phone_number_id válidos).
- **Activación dry-run → real = SOLO configuración (D6)**: `enabled=true` + `token` + `phone_number_id` en `companies.settings.whatsapp`. Sin cambio de código ni deploy; reversible.
- ⚠️ **Matiz importante: NO hay webhook de recepción (D7)** — F1 es **envío unidireccional con plantillas**; chatbot bidireccional/estados de entrega quedan FUERA de F1 (columna BSUID ya lista para cuando se haga).

### Llamadas — precisión sobre el hueco de agenda
- Lo único que existe hoy es un **toggle de estado de mesa**: `POST /tables/{id}/reserve` cambia `available → reserved` (sin fecha, hora, cliente, duración ni tabla de reservas). Verificado en modelo `Table` (`restaurant.py:60-90`), 4 estados, **sin entidad Reservation/Booking** en migraciones ni frontend.
- Desglose del flujo del reel: ✅ contestar (F2, pendiente solo trunk SIP) · ✅ grabar/transcribir (F2 MixMonitor + F3 `call_transcriptions`) · ❌ consultar agenda (no hay) · ❌ reservar cita (la IA F3 está acotada a pedidos/menú/estado — dominio cerrado, requisito Meta 15-ene-2026; llamadas salientes/recordatorios fuera de alcance F3).
- **Para el flujo completo**: módulo de reservas/citas (BD + CRUD + reglas de disponibilidad por mesa/horario) + extender el skill de la IA F3 para consultar/crear reservas + **proveedor de voz IA (STT/TTS)** externo (**costo real S/500–900/mes, aprobado por Ron**, PoC 2 semanas).

### Otros pendientes (Jarvis)
- **F5 Pregúntale al Sistema**: implementada solo para delivery (10 consultas catálogo) — extensión a salón/inventario/contabilidad pendiente; test sets formales + human-in-the-loop del Bloque C pendientes (parcial).
- **F4 Franquicia Conectada**: solo propuesta, sin implementar.
- **Deuda técnica registrada**: DT-F0-001..011 en `docs/backlog/deuda-tecnica-fase0.md` (seguridad perimetral DT-F0-010 antes de v1.0, módulo pérdidas, cancelación de comandas, etc.).
- **Bloqueo operacional F3**: requiere proveedor STT/TTS + llamadas reales para validar el PoC de 2 semanas.

> **Resumen Jarvis en una línea:** *"WhatsApp está a un trámite Meta de funcionar de verdad; el canal llamadas con reservas requiere un módulo de agenda/citas que hoy no existe (la central + grabación + IA de voz ya están desplegadas)."*
