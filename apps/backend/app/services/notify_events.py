"""
🐇 Publicador de eventos de delivery a RabbitMQ (Spec 03 §7, Fase B).

Fire-and-forget: el pedido NUNCA depende de la notificación. Si RabbitMQ no
está disponible (o el publish falla) se loguea un warning y el checkout /
transición de estado continúan sin error.

Eventos publicados (cola `iaas-tasks`, routing `delivery.<event_type>`):
  - delivery.confirmed       checkout 201 OK (plantilla al cliente "confirmed")
  - delivery.new_order       checkout 201 OK (alerta al local "new_order")
  - delivery.status_changed  cada transición válida de la máquina de estados
  - delivery.cancelled       cancelación (alerta al local "order_cancelled")
"""

import json
import logging
from datetime import UTC, datetime

import aio_pika

from app.config import settings

logger = logging.getLogger(__name__)

# Mensajes que van al CLIENTE (customer_phone) vs alertas al LOCAL (alert_phone)
# CA-B8: confirmed/preparing/ready/delivered/cancelled → cliente;
#        new_order/order_cancelled → local.
CUSTOMER_EVENTS = {"confirmed", "status_changed"}
LOCAL_ALERT_EVENTS = {"new_order", "cancelled"}

# Retry/backoff del worker (Spec 03 §7.5 CA-B4): 0s / 60s / 300s
RETRY_DELAYS_SECONDS: tuple[float, ...] = (0.0, 60.0, 300.0)
MAX_ATTEMPTS = len(RETRY_DELAYS_SECONDS) + 1


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


def build_delivery_event_payload(
    *,
    event_type: str,
    tenant_id: int,
    tracking_code: str,
    sale_id: int | None,
    customer_phone: str | None,
    status: str,
    total: float | None = None,
    items_resumen: list[dict] | None = None,
    zone: str | None = None,
    bsuid: str | None = None,
) -> dict:
    """Payload del evento (Spec 03 §7.4 + Spec 04 F1 D3).

    Contrato existente intacto: tenant_id, tracking_code, sale_id,
    customer_phone, status, total, items_resumen, zone, timestamp.
    F1 añade `bsuid` (opcional, str|None) — el user_id/BSUID de Meta; el
    worker lo persiste en delivery_orders.whatsapp_bsuid cuando viene.
    """
    return {
        "event": f"delivery.{event_type}",
        "event_type": event_type,
        "tenant_id": tenant_id,
        "tracking_code": tracking_code,
        "sale_id": sale_id,
        "customer_phone": customer_phone,
        "bsuid": bsuid,
        "status": status,
        "total": total,
        "items_resumen": items_resumen or [],
        "zone": zone,
        "timestamp": _iso_now(),
    }


async def publish_delivery_event(
    event_type: str,
    *,
    tenant_id: int,
    tracking_code: str,
    sale_id: int | None,
    customer_phone: str | None,
    status: str,
    total: float | None = None,
    items_resumen: list[dict] | None = None,
    zone: str | None = None,
    bsuid: str | None = None,
) -> bool:
    """Publica `delivery.{event_type}` en la cola `iaas-tasks` (fire-and-forget).

    Retorna True si se publicó; False si RabbitMQ no estaba disponible
    (el caller NO debe romper el pedido en ese caso — CA-B1 sigue verde).
    """
    payload = build_delivery_event_payload(
        event_type=event_type,
        tenant_id=tenant_id,
        tracking_code=tracking_code,
        sale_id=sale_id,
        customer_phone=customer_phone,
        status=status,
        total=total,
        items_resumen=items_resumen,
        zone=zone,
        bsuid=bsuid,
    )
    try:
        connection = await aio_pika.connect(settings.rabbitmq_url, timeout=5)
        async with connection:
            channel = await connection.channel()
            # Declaración idempotente: la cola existe aunque el worker aún no
            # haya arrancado (el publish es al default exchange, routing = nombre).
            await channel.declare_queue(settings.rabbitmq_queue, durable=True)
            message = aio_pika.Message(
                body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )
            await channel.default_exchange.publish(
                message, routing_key=settings.rabbitmq_queue,
            )
        logger.info(
            "evento publicado: delivery.%s tracking=%s tenant=%s",
            event_type, tracking_code, tenant_id,
        )
        return True
    except Exception as exc:  # noqa: BLE001 — fire-and-forget: nunca romper el pedido
        logger.warning(
            "RabbitMQ no disponible — evento delivery.%s (tracking=%s) descartado: %s",
            event_type, tracking_code, exc,
        )
        return False


async def publish_checkout_events(
    *,
    tenant_id: int,
    tracking_code: str,
    sale_id: int | None,
    customer_phone: str | None,
    total: float | None,
    items_resumen: list[dict] | None,
    zone: str | None,
    bsuid: str | None = None,
) -> None:
    """Punto único de publicación tras checkout 201 (Spec 03 §7.4).

    Emite `delivery.confirmed` (cliente) + `delivery.new_order` (alerta local).
    Cada publish es fire-and-forget e independiente.
    """
    kwargs = dict(
        tenant_id=tenant_id,
        tracking_code=tracking_code,
        sale_id=sale_id,
        customer_phone=customer_phone,
        status="received",
        total=total,
        items_resumen=items_resumen,
        zone=zone,
        bsuid=bsuid,
    )
    await publish_delivery_event("confirmed", **kwargs)
    await publish_delivery_event("new_order", **kwargs)


async def publish_status_event(
    *,
    tenant_id: int,
    tracking_code: str,
    sale_id: int | None,
    customer_phone: str | None,
    new_status: str,
    total: float | None = None,
    items_resumen: list[dict] | None = None,
    zone: str | None = None,
    bsuid: str | None = None,
) -> None:
    """Punto único de publicación tras una transición válida de estado.

    - Siempre `delivery.status_changed` con el nuevo status (CA-B2).
    - Si el nuevo status es `cancelled` además `delivery.cancelled` (alerta
      al local con plantilla `order_cancelled`); el mensaje al cliente por la
      cancelación va vía status_changed (plantilla `cancelled`) — así el
      cliente recibe UN solo mensaje de cancelación y el local su alerta.
    """
    kwargs = dict(
        tenant_id=tenant_id,
        tracking_code=tracking_code,
        sale_id=sale_id,
        customer_phone=customer_phone,
        status=new_status,
        total=total,
        items_resumen=items_resumen,
        zone=zone,
        bsuid=bsuid,
    )
    await publish_delivery_event("status_changed", **kwargs)
    if new_status == "cancelled":
        await publish_delivery_event("cancelled", **kwargs)


# Re-export para compatibilidad con imports de tests/futuros usos
__all__: list[str] = [
    "CUSTOMER_EVENTS",
    "LOCAL_ALERT_EVENTS",
    "RETRY_DELAYS_SECONDS",
    "MAX_ATTEMPTS",
    "build_delivery_event_payload",
    "publish_delivery_event",
    "publish_checkout_events",
    "publish_status_event",
]
