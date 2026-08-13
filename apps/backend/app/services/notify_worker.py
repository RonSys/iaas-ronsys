"""
📨 Worker consumidor — Notificaciones WhatsApp (Spec 03 §7, Fase B).

Consume eventos `delivery.*` de la cola `iaas-tasks` (RabbitMQ) y dispara el
envío vía el `Notifier` agnóstico (Meta Cloud API o dry-run):

  - Resuelve tenant → `companies.settings.whatsapp` (patrón D-03).
  - Tenant sin config / sin token → dry-run: loguea, cero envíos (CA-B5/CA-B7).
  - CA-B8: eventos al cliente usan `customer_phone`; alertas al local usan
    `alert_phone` (new_order/order_cancelled).
  - Reintentos 3 (0s/60s/300s, CA-B4) → agotados → dead-letter `iaas-tasks-dlq`.

Entrypoint: `python -m app.services.notify_worker`
"""

import asyncio
import hashlib
import json
import logging

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy import select, update

from app.adapters.db.database import get_session_factory
from app.adapters.db.models.accounting import Company
from app.adapters.db.models.delivery import DeliveryOrder
from app.config import settings
from app.schemas import WhatsAppSettings
from app.services.notify_events import RETRY_DELAYS_SECONDS
from app.services.whatsapp_notifier import Notifier, build_notifier

logger = logging.getLogger(__name__)

DLQ_QUEUE = "iaas-tasks-dlq"

# Estado de reintentos en memoria: {sha1(body): attempts}. Persiste entre
# redeliveries del mismo mensaje (mismo body → misma clave).
_attempts: dict[str, int] = {}


def _message_key(message: AbstractIncomingMessage) -> str:
    return hashlib.sha1(message.body).hexdigest()


def _whatsapp_from_raw(raw: dict | None) -> WhatsAppSettings:
    """Resuelve settings.whatsapp del tenant con defaults (patrón D-03).

    Mismo contrato que `_merge_settings` de app.routers.setup: lo persistido
    gana, los campos ausentes toman el default del schema.
    """
    raw = raw or {}
    whatsapp = raw.get("whatsapp", {}) if isinstance(raw.get("whatsapp"), dict) else {}
    return WhatsAppSettings(**whatsapp)


def _recipient_and_template(
    event_type: str, payload: dict, whatsapp: WhatsAppSettings,
) -> tuple[str | None, str | None]:
    """CA-B8: destinatario + plantilla según el evento.

    - new_order / cancelled (order_cancelled) → alert_phone (local).
    - confirmed / status_changed → customer_phone (cliente); para
      status_changed la plantilla se resuelve por el NUEVO status
      (preparing/ready/out_for_delivery/delivered/cancelled).
    """
    templates = whatsapp.templates
    if event_type == "new_order":
        return whatsapp.alert_phone, templates.get("new_order")
    if event_type == "cancelled":
        return whatsapp.alert_phone, templates.get("order_cancelled")
    if event_type == "confirmed":
        return payload.get("customer_phone"), templates.get("confirmed")
    if event_type == "status_changed":
        status = payload.get("status") or ""
        return payload.get("customer_phone"), templates.get(status)
    logger.info("event_type '%s' sin mapeo de plantilla — ignorado", event_type)
    return None, None


def _build_params(payload: dict) -> dict:
    return {
        "tracking_code": payload.get("tracking_code") or "",
        "status": payload.get("status") or "",
        "total": payload.get("total"),
        "items_resumen": payload.get("items_resumen") or [],
        "zone": payload.get("zone") or "",
        "sale_id": payload.get("sale_id"),
    }


async def _load_company(tenant_id: int) -> Company | None:
    async with get_session_factory()() as db:
        company = (await db.execute(
            select(Company).where(Company.id == tenant_id)
        )).scalar_one_or_none()
    return company


async def _persist_bsuid(payload: dict) -> None:
    """Spec 04 F1 (D3): persiste el BSUID de Meta cuando el payload lo trae.

    Update ligero y fire-and-forget: solo si el payload trae `bsuid` y la
    columna `delivery_orders.whatsapp_bsuid` está NULL para ese tracking
    (R-F1.6: nunca reemplaza a `customer_phone`). Un fallo de BD aquí NO
    bloquea el envío ni provoca reintentos del mensaje (se loguea y se sigue).
    """
    bsuid = payload.get("bsuid")
    tracking_code = payload.get("tracking_code")
    if not bsuid or not tracking_code:
        return
    try:
        async with get_session_factory()() as db:
            await db.execute(
                update(DeliveryOrder)
                .where(
                    DeliveryOrder.tracking_code == tracking_code,
                    DeliveryOrder.whatsapp_bsuid.is_(None),
                )
                .values(whatsapp_bsuid=str(bsuid)[:64])
            )
            await db.commit()
        logger.info(
            "bsuid persistido: tracking=%s bsuid=%s", tracking_code, str(bsuid)[:16],
        )
    except Exception as exc:  # noqa: BLE001 — fire-and-forget: nunca bloquear el envío
        logger.warning(
            "no se pudo persistir bsuid (tracking=%s): %s",
            tracking_code, exc,
        )


async def _process_event(payload: dict) -> None:
    """Procesa UN evento: tenant → config → notifier → envío.

    Levanta excepción ante fallo transitorio (proveedor/red) para que el
    wrapper de reintentos decida. Los problemas de CONFIG (sin plantilla /
    sin destinatario) no reintentan: se loguean y se hace ack.
    """
    event_type = payload.get("event_type") or payload.get("event") or ""
    event_type = event_type.removeprefix("delivery.")
    if not event_type:
        raise ValueError("evento sin event_type")
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise ValueError("evento sin tenant_id")

    company = await _load_company(int(tenant_id))
    if not company:
        raise ValueError(f"tenant {tenant_id} no existe")

    # Spec 04 F1 (D3): BSUID desde el día 1 — persiste cuando el payload lo
    # trae (update ligero, fire-and-forget; un fallo aquí no bloquea el envío).
    await _persist_bsuid(payload)

    whatsapp = _whatsapp_from_raw(company.settings)
    notifier: Notifier = build_notifier(whatsapp)
    phone, template_name = _recipient_and_template(event_type, payload, whatsapp)
    if not phone or not template_name:
        # CA-B5/CA-B7: sin config completa o sin plantilla → dry-run logueado,
        # cero envíos HTTP. No es un fallo transitorio → ack.
        logger.info(
            "whatsapp dry-run: evento delivery.%s sin destinatario/plantilla "
            "(phone=%s template=%s)",
            event_type, phone, template_name,
        )
        return

    await notifier.send(
        phone=phone, template=template_name, params=_build_params(payload),
    )


async def _publish_to_dlq(message: AbstractIncomingMessage) -> None:
    """Reenvía el cuerpo crudo del mensaje a la dead-letter queue."""
    connection = await aio_pika.connect(settings.rabbitmq_url, timeout=5)
    async with connection:
        channel = await connection.channel()
        await channel.declare_queue(DLQ_QUEUE, durable=True)
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=message.body,
                content_type=message.content_type or "application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=DLQ_QUEUE,
        )
    logger.error("mensaje movido a DLQ %s (sha=%s)", DLQ_QUEUE, _message_key(message)[:12])


async def _handle_message(
    message: AbstractIncomingMessage,
    *,
    delays: tuple[float, ...] = RETRY_DELAYS_SECONDS,
) -> bool:
    """Procesa con reintentos (0s/60s/300s, CA-B4) → DLQ al agotar.

    Retorna True si el mensaje se ack'eo; False si se reencoló (retry) o se
    movió a DLQ.
    """
    key = _message_key(message)
    attempts = _attempts.get(key, 0) + 1
    _attempts[key] = attempts
    max_attempts = len(delays) + 1
    try:
        payload = json.loads(message.body)
        await _process_event(payload)
        _attempts.pop(key, None)
        await message.ack()
        return True
    except Exception as exc:  # noqa: BLE001 — reintentos cubren cualquier fallo del proveedor
        if attempts < max_attempts:
            delay = delays[attempts - 1]
            logger.warning(
                "evento falló (intento %d/%d): %s — reintento en %ss",
                attempts, max_attempts, exc, delay,
            )
            await asyncio.sleep(delay)
            await message.nack(requeue=True)
            return False
        logger.error(
            "reintentos agotados (%d): %s — enviando a DLQ", max_attempts, exc,
        )
        try:
            await _publish_to_dlq(message)
        except Exception as dlq_exc:  # noqa: BLE001
            logger.critical("no se pudo publicar a DLQ: %s", dlq_exc)
        finally:
            # Ack aunque la DLQ falle: evita mensaje veneno en el loop infinito.
            await message.ack()
            _attempts.pop(key, None)
        return False


async def _on_message(message: AbstractIncomingMessage) -> None:
    await _handle_message(message)


async def consume() -> None:
    """Consume `iaas-tasks` (routing delivery.*) de forma indefinida.

    Declara la cola principal y la DLQ al iniciar (idempotente).
    """
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        await channel.declare_queue(settings.rabbitmq_queue, durable=True)
        await channel.declare_queue(DLQ_QUEUE, durable=True)
        queue = await channel.declare_queue(settings.rabbitmq_queue, durable=True)
        await queue.consume(_on_message)
        logger.info(
            "worker notificaciones activo: cola=%s routing=delivery.* dlq=%s",
            settings.rabbitmq_queue, DLQ_QUEUE,
        )
        await asyncio.Future()  # corre para siempre


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(consume())
