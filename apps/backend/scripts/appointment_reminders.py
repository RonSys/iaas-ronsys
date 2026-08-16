#!/usr/bin/env python3
"""
⏰ Job de recordatorios de citas (Spec 07 F6, R9/CA-F6-7) — 24h antes.

Busca citas `confirmada` cuyo `starts_at` está dentro de la ventana
`(now, now + reminder_hours_before]` y SIN `reminded_at` → publica
`appointment.reminder` en la cola `iaas-tasks` (motor F1, dry-run sin
cuenta Meta) y marca `reminded_at` (idempotente: nunca re-envía).

Uso (cron diario / target Makefile):
  cd apps/backend
  .venv/bin/python -m scripts.appointment_reminders

Mecanismo deliberadamente LIGERO (Spec 07 §2.2: "no inventar infra nueva
pesada"): el proyecto no tiene celery/beat — este script es el job; el
scheduler externo (cron/systemd del host) decide CUÁNDO corre. Idempotencia
garantizada por `reminded_at` + filtro de ventana, no por el scheduler.

Exit 0 = procesado OK (0 o más recordatorios publicados); 1 = error.
"""

import asyncio
import logging
import sys

logger = logging.getLogger("appointment_reminders")


async def run() -> int:
    from app.adapters.db.database import get_session_factory
    from app.services import appointments_service

    async with get_session_factory()() as db:
        # R7: el job es multi-tenant — recorre TODOS los tenants con citas
        # confirmadas por vencer. Por tenant: ventana según sus settings.
        from sqlalchemy import select

        from app.adapters.db.models.appointments import Appointment

        tenant_ids = set((await db.execute(
            select(Appointment.tenant_id).where(
                Appointment.status == "confirmada",
                Appointment.reminded_at.is_(None),
            )
        )).scalars().all())

        published = 0
        for tenant_id in sorted(tenant_ids):
            due = await appointments_service.find_reminders_due(db, tenant_id)
            for item in due:
                result = await appointments_service.remind(db, tenant_id, item["id"])
                if result.get("published"):
                    published += 1
                    logger.info(
                        "recordatorio publicado: appointment=%s tenant=%s starts_at=%s",
                        item["id"], tenant_id, item["starts_at"],
                    )
        logger.info("job completado: %d recordatorio(s) publicado(s)", published)
        return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        return asyncio.run(run())
    except Exception as exc:  # noqa: BLE001 — exit code para cron
        logger.error("job falló: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
