"""
💰 Investment Service — Lógica de negocio para el módulo de Inversión / Puesta en Marcha (Caso 7).

HU: Administrar bienes de inversión, registrar costos estimados vs reales,
    asociar comprobantes y calcular resumen de totes.
"""

from datetime import datetime, UTC
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.restaurant import InvestmentItem


INVESTMENT_CATEGORIES = [
    "infraestructura",
    "mobiliario",
    "equipamiento_cocina",
    "instalaciones",
    "vestimenta",
    "dyl",
    "tecnologia",
    "marketing",
    "gastos_operativos",
]


class InvestmentService:
    """CRUD + resumen para bienes de inversión."""

    # ─── Helpers ──────────────────────────────────────────

    @staticmethod
    async def _get_item(
        db: AsyncSession, item_id: int, tenant_id: int,
    ) -> InvestmentItem:
        """Obtiene un bien validando tenant. Lanza 404 si no existe."""
        stmt = select(InvestmentItem).where(
            InvestmentItem.id == item_id,
            InvestmentItem.tenant_id == tenant_id,
        )
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bien de inversión no encontrado",
            )
        return item

    @staticmethod
    def _to_dict(item: InvestmentItem) -> dict[str, Any]:
        """Serializa un InvestmentItem a dict."""
        return {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "estimated_cost": float(item.estimated_cost),
            "actual_cost": float(item.actual_cost) if item.actual_cost is not None else None,
            "receipt_code": item.receipt_code,
            "status": item.status,
            "notes": item.notes,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }

    # ─── CRUD ─────────────────────────────────────────────

    @staticmethod
    async def list_items(
        db: AsyncSession, tenant_id: int,
        category: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista todos los bienes de inversión del tenant."""
        stmt = select(InvestmentItem).where(
            InvestmentItem.tenant_id == tenant_id,
        )
        if category:
            stmt = stmt.where(InvestmentItem.category == category)
        if status:
            stmt = stmt.where(InvestmentItem.status == status)
        stmt = stmt.order_by(InvestmentItem.created_at.desc())
        result = await db.execute(stmt)
        return [InvestmentService._to_dict(item) for item in result.scalars().all()]

    @staticmethod
    async def get_item(
        db: AsyncSession, item_id: int, tenant_id: int,
    ) -> dict[str, Any]:
        """Obtiene un bien de inversión por ID."""
        item = await InvestmentService._get_item(db, item_id, tenant_id)
        return InvestmentService._to_dict(item)

    @staticmethod
    async def create_item(
        db: AsyncSession, tenant_id: int, data: dict,
    ) -> dict[str, Any]:
        """Crea un nuevo bien de inversión."""
        # Validar categoría
        category = data.get("category", "").lower()
        if category not in INVESTMENT_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Categoría inválida: '{category}'. Permitidas: {', '.join(INVESTMENT_CATEGORIES)}",
            )

        # Validar costos
        estimated_cost = data.get("estimated_cost", 0)
        if estimated_cost < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="estimated_cost debe ser >= 0",
            )

        actual_cost = data.get("actual_cost")
        if actual_cost is not None and actual_cost < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="actual_cost debe ser >= 0",
            )

        # Validar status
        status_val = data.get("status", "pending")
        if status_val not in ("pending", "acquired"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="status debe ser 'pending' o 'acquired'",
            )

        item = InvestmentItem(
            tenant_id=tenant_id,
            name=data["name"],
            category=category,
            estimated_cost=estimated_cost,
            actual_cost=actual_cost,
            receipt_code=data.get("receipt_code"),
            status=status_val,
            notes=data.get("notes"),
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return InvestmentService._to_dict(item)

    @staticmethod
    async def update_item(
        db: AsyncSession, item_id: int, tenant_id: int, data: dict,
    ) -> dict[str, Any]:
        """Actualiza un bien de inversión."""
        item = await InvestmentService._get_item(db, item_id, tenant_id)

        # Validar campos antes de aplicarlos
        if "name" in data and data["name"] is not None:
            item.name = data["name"]

        if "category" in data and data["category"] is not None:
            cat = data["category"].lower()
            if cat not in INVESTMENT_CATEGORIES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Categoría inválida: '{cat}'. Permitidas: {', '.join(INVESTMENT_CATEGORIES)}",
                )
            item.category = cat

        if "estimated_cost" in data and data["estimated_cost"] is not None:
            if data["estimated_cost"] < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="estimated_cost debe ser >= 0",
                )
            item.estimated_cost = data["estimated_cost"]

        if "actual_cost" in data:
            # Puede ser None (borrar costo real) o un valor >= 0
            if data["actual_cost"] is not None and data["actual_cost"] < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="actual_cost debe ser >= 0",
                )
            item.actual_cost = data["actual_cost"]

        if "receipt_code" in data:
            item.receipt_code = data["receipt_code"]

        if "status" in data and data["status"] is not None:
            if data["status"] not in ("pending", "acquired"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="status debe ser 'pending' o 'acquired'",
                )
            item.status = data["status"]

        if "notes" in data:
            item.notes = data["notes"]

        item.updated_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(item)
        return InvestmentService._to_dict(item)

    @staticmethod
    async def delete_item(
        db: AsyncSession, item_id: int, tenant_id: int,
    ) -> None:
        """Elimina un bien de inversión."""
        item = await InvestmentService._get_item(db, item_id, tenant_id)
        await db.delete(item)
        await db.flush()

    # ─── Resumen ──────────────────────────────────────────

    @staticmethod
    async def get_summary(
        db: AsyncSession, tenant_id: int,
    ) -> dict[str, Any]:
        """
        Calcula el resumen de totes de inversión.

        Returns:
            {
                "total_estimated": 5700.00,
                "total_actual": 3950.00,
                "difference": 1750.00,
                "acquired_count": 2,
                "pending_count": 2,
                "total_count": 4
            }
        """
        # Total estimado
        est_result = await db.execute(
            select(func.coalesce(func.sum(InvestmentItem.estimated_cost), 0)).where(
                InvestmentItem.tenant_id == tenant_id,
            )
        )
        total_estimated = float(est_result.scalar() or 0)

        # Total real (solo acquired)
        act_result = await db.execute(
            select(func.coalesce(func.sum(InvestmentItem.actual_cost), 0)).where(
                InvestmentItem.tenant_id == tenant_id,
                InvestmentItem.status == "acquired",
            )
        )
        total_actual = float(act_result.scalar() or 0)

        # Conteos — queries separadas
        total_count_result = await db.execute(
            select(func.count()).where(
                InvestmentItem.tenant_id == tenant_id,
            )
        )
        total_count = total_count_result.scalar() or 0

        acquired_result = await db.execute(
            select(func.count()).where(
                InvestmentItem.tenant_id == tenant_id,
                InvestmentItem.status == "acquired",
            )
        )
        acquired_count = acquired_result.scalar() or 0

        pending_count = total_count - acquired_count

        return {
            "total_estimated": round(total_estimated, 2),
            "total_actual": round(total_actual, 2),
            "difference": round(total_estimated - total_actual, 2),
            "acquired_count": acquired_count,
            "pending_count": pending_count,
            "total_count": total_count,
        }
