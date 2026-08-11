"""
📲 Notifier WhatsApp — interfaz agnóstica + Meta Cloud API (Spec 03 §7, Fase B).

Diseño (D-B1): la lógica de eventos NO conoce al proveedor. `Notifier` es un
Protocol con un único método `send`; `build_notifier` decide la implementación
según la config del tenant:

- `MetaCloudNotifier`: HTTP POST a la Graph API de Meta (plantillas aprobadas).
- `DryRunNotifier`: solo loguea (tenant sin config / sin token / modo dry-run).

Regla dura (Spec 03 §7.3): los tokens NUNCA van en código — solo en
`companies.settings.whatsapp.token` (JSONB por tenant).
"""

import logging
from typing import Protocol

import httpx

from app.schemas import WhatsAppSettings

logger = logging.getLogger(__name__)

# Meta Graph API — versión estable v21.0 (D-B1)
GRAPH_API_URL = "https://graph.facebook.com/v21.0/{phone_number_id}/messages"
DEFAULT_LANGUAGE = "es"


class Notifier(Protocol):
    """Contrato agnóstico de envío de notificaciones WhatsApp."""

    async def send(self, *, phone: str, template: str, params: dict) -> None: ...


class MetaCloudNotifier:
    """Envía plantillas aprobadas vía Meta Cloud API (HTTP)."""

    def __init__(self, settings: WhatsAppSettings, timeout: float = 10.0):
        self.settings = settings
        self.timeout = timeout

    async def send(self, *, phone: str, template: str, params: dict) -> None:
        """POST /{phone_number_id}/messages con la plantilla indicada.

        `template` es el NOMBRE real de la plantilla aprobada en Meta
        (resuelto por el worker desde `settings.templates[event_type]`).
        `params` se serializan en orden de inserción como parámetros de texto.
        """
        url = GRAPH_API_URL.format(phone_number_id=self.settings.phone_number_id)
        body = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template,
                "language": {"code": DEFAULT_LANGUAGE},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": str(v)} for v in params.values()
                        ],
                    }
                ],
            },
        }
        headers = {
            "Authorization": f"Bearer {self.settings.token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
        logger.info(
            "whatsapp sent: phone=%s template=%s params=%s (status %s)",
            phone, template, params, resp.status_code,
        )


class DryRunNotifier:
    """Modo dry-run: loguea el envío, NO hace HTTP (CA-B5/CA-B7)."""

    async def send(self, *, phone: str, template: str, params: dict) -> None:
        logger.info(
            "DRY-RUN whatsapp (sin envío): phone=%s template=%s params=%s",
            phone, template, params,
        )


def build_notifier(settings: WhatsAppSettings) -> Notifier:
    """Devuelve el notifier adecuado según la config del tenant.

    DryRun si el tenant no habilitó whatsapp o le faltan credenciales;
    MetaCloud solo con enabled + token + phone_number_id.
    """
    if (
        settings.enabled
        and settings.token
        and settings.phone_number_id
    ):
        if settings.provider == "meta_cloud":
            return MetaCloudNotifier(settings)
        logger.warning(
            "whatsapp provider '%s' no soportado — dry-run", settings.provider,
        )
    else:
        logger.info(
            "whatsapp sin config completa (enabled=%s token=%s phone_number_id=%s) — dry-run",
            settings.enabled,
            bool(settings.token),
            bool(settings.phone_number_id),
        )
    return DryRunNotifier()
