"""
🍽️ Restaurant Service — Lógica de negocio (F0-004 a F0-008).

HU: Mesas, menú, comandas, takeaway, pagos y promociones.
"""

from datetime import date, datetime, UTC
from zoneinfo import ZoneInfo

LIMA_TZ = ZoneInfo("America/Lima")


def _fmt_dt(dt: datetime | None) -> str | None:
    """Serialize datetime to ISO string in America/Lima timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # SQLAlchemy puede devolver naive datetime a pesar de DateTime(timezone=True)
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(LIMA_TZ).isoformat()
from decimal import Decimal
from typing import Any
import logging

logger = logging.getLogger(__name__)

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.accounting import Product, KardexMovement
from app.adapters.db.models.restaurant import (
    KitchenOrder,
    MenuItem,
    MenuModifier,
    Promotion,
    Recipe,
    RecipeIngredient,
    RestaurantSection,
    Table,
    TakeawayOrder,
)
from app.adapters.db.models.sales import (
    Sale,
    SaleItem,
    SalePayment,
    RestaurantSale as RestaurantSaleModel,
)
from app.core.ws_manager import manager


# ═══════════════════════════════════════════════════════════════
# Tables Service (F0-004)
# ═══════════════════════════════════════════════════════════════

class TablesService:

    @staticmethod
    async def list_tables(
        db: AsyncSession, tenant_id: int, status_filter: str | None = None,
        section_id: int | None = None,
    ) -> list[dict]:
        stmt = select(Table).options(selectinload(Table.section_rel)).where(Table.tenant_id == tenant_id)
        if status_filter:
            stmt = stmt.where(Table.status == status_filter)
        if section_id is not None:
            stmt = stmt.where(Table.section_id == section_id)
        stmt = stmt.order_by(Table.number)
        result = await db.execute(stmt)
        output = []
        for t in result.scalars().all():
            section_name = t.section
            if t.section_rel:
                section_name = t.section_rel.name
            # Buscar order_id activo y total provisional para mesas ocupadas
            order_id = None
            total_provisional = 0.0
            if t.status == "occupied":
                # SUMAR TODAS las órdenes no canceladas (no solo la última)
                orders_result = await db.execute(
                    select(KitchenOrder).where(
                        KitchenOrder.table_id == t.id,
                        KitchenOrder.tenant_id == tenant_id,
                        KitchenOrder.status != "cancelled",
                    ).order_by(KitchenOrder.ordered_at.desc())
                )
                all_orders = orders_result.scalars().all()
                if all_orders:
                    # Usar la más reciente para order_id (UI reference)
                    order_id = all_orders[0].id
                    # Sumar items de TODAS las órdenes
                    for o in all_orders:
                        for item in (o.items or []):
                            total_provisional += item.get("total", 0) or 0
            output.append({
                "id": t.id, "number": t.number, "capacity": t.capacity,
                "status": t.status, "section": section_name,
                "section_name": section_name,
                "section_id": t.section_id,
                "guests": t.guests, "waiter_name": t.waiter_name,
                "opened_at": t.opened_at.isoformat() if t.opened_at else None,
                "order_id": order_id,
                "total_provisional": total_provisional if total_provisional > 0 else None,
            })
        return output

    @staticmethod
    async def get_table(db: AsyncSession, table_id: int, tenant_id: int) -> Table:
        stmt = select(Table).where(
            Table.id == table_id, Table.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        table = result.scalar_one_or_none()
        if not table:
            raise HTTPException(status_code=404, detail="Mesa no encontrada")
        return table

    @staticmethod
    def _get_section_name(table: Table) -> str | None:
        """Resuelve section_name desde la relación o fallback al campo legacy."""
        if table.section_rel:
            return table.section_rel.name
        return table.section

    @staticmethod
    async def create_table(
        db: AsyncSession, tenant_id: int, number: str,
        capacity: int = 4, section: str | None = None,
        section_id: int | None = None,
    ) -> dict:
        existing = await db.execute(
            select(Table).where(
                Table.tenant_id == tenant_id, Table.number == number,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una mesa con número '{number}'",
            )
        table = Table(
            tenant_id=tenant_id, number=number,
            capacity=capacity, section=section,
            section_id=section_id,
        )
        if section_id and not section:
            sec = await db.get(RestaurantSection, section_id)
            if sec:
                table.section = sec.name
        db.add(table)
        await db.flush()
        await db.refresh(table)
        return {
            "id": table.id, "number": table.number,
            "capacity": table.capacity, "status": table.status,
            "section": table.section, "section_id": table.section_id,
        }

    @staticmethod
    async def update_table(
        db: AsyncSession, table_id: int, tenant_id: int, body: dict,
    ) -> dict:
        table = await TablesService.get_table(db, table_id, tenant_id)
        for key in ("number", "capacity", "section"):
            if key in body and body[key] is not None:
                setattr(table, key, body[key])
        if "section_id" in body:
            table.section_id = body["section_id"]
            if body["section_id"] is not None:
                sec = await db.get(RestaurantSection, body["section_id"])
                if sec:
                    table.section = sec.name
            else:
                table.section = None
        table.updated_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(table)
        section_name = TablesService._get_section_name(table)
        return {
            "id": table.id, "number": table.number,
            "capacity": table.capacity, "status": table.status,
            "section": section_name, "section_name": section_name,
            "section_id": table.section_id,
        }

    @staticmethod
    async def delete_table(
        db: AsyncSession, table_id: int, tenant_id: int,
    ) -> None:
        table = await TablesService.get_table(db, table_id, tenant_id)
        if table.status != "available":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Solo se pueden eliminar mesas libres",
            )
        await db.delete(table)
        await db.flush()


# ═══════════════════════════════════════════════════════════════
    @staticmethod
    async def open_table(
        db: AsyncSession, table_id: int, tenant_id: int,
        guests: int = 1, waiter_name: str | None = None,
    ) -> dict:
        table = await TablesService.get_table(db, table_id, tenant_id)
        if table.status != "available":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La mesa ya está ocupada",
            )
        table.status = "occupied"
        table.guests = guests
        table.waiter_name = waiter_name
        table.opened_at = datetime.now(UTC)
        await db.flush()
        return {
            "id": table.id, "number": table.number,
            "status": "occupied",
            "opened_at": table.opened_at.isoformat(),
            "guests": guests, "waiter_name": waiter_name,
            "session_token": f"table_{table.id}_{int(table.opened_at.timestamp())}",
        }





    @staticmethod
    async def update_table_status(
        db: AsyncSession, table_id: int, tenant_id: int, status: str,
    ) -> dict:
        table = await TablesService.get_table(db, table_id, tenant_id)
        table.status = status
        if status != "occupied":
            table.guests = None
            table.waiter_name = None
            table.opened_at = None
        table.updated_at = datetime.now(UTC)
        await db.flush()
        return {"id": table.id, "number": table.number, "status": table.status}

# ═══════════════════════════════════════════════════════════════
# Menu Service (F0-005)
# ═══════════════════════════════════════════════════════════════


# Sections Service (Caso 2: Mantenimiento de Secciones)
# ═══════════════════════════════════════════════════════════════

class SectionsService:

    @staticmethod
    async def _get_section(
        db: AsyncSession, section_id: int, tenant_id: int,
    ) -> RestaurantSection:
        stmt = select(RestaurantSection).where(
            RestaurantSection.id == section_id,
            RestaurantSection.tenant_id == tenant_id,
        )
        result = await db.execute(stmt)
        section = result.scalar_one_or_none()
        if not section:
            raise HTTPException(status_code=404, detail="Sección no encontrada")
        return section

    @staticmethod
    async def _resolve_section_response(
        db: AsyncSession, section: RestaurantSection,
    ) -> dict:
        # Contar mesas asociadas
        count_result = await db.execute(
            select(func.count()).select_from(Table).where(
                Table.section_id == section.id,
            )
        )
        table_count = count_result.scalar() or 0
        return {
            "id": section.id,
            "name": section.name,
            "description": section.description,
            "sort_order": section.sort_order,
            "table_count": table_count,
            "created_at": section.created_at.isoformat() if section.created_at else None,
        }

    @staticmethod
    async def create_section(
        db: AsyncSession, tenant_id: int, data: dict,
    ) -> dict:
        # Verificar unicidad
        existing = await db.execute(
            select(RestaurantSection).where(
                RestaurantSection.tenant_id == tenant_id,
                RestaurantSection.name == data["name"],
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una sección con nombre '{data['name']}'",
            )
        section = RestaurantSection(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            sort_order=data.get("sort_order", 0),
        )
        db.add(section)
        await db.flush()
        await db.refresh(section)
        return await SectionsService._resolve_section_response(db, section)

    @staticmethod
    async def list_sections(
        db: AsyncSession, tenant_id: int,
    ) -> list[dict]:
        stmt = select(RestaurantSection).where(
            RestaurantSection.tenant_id == tenant_id,
        ).order_by(RestaurantSection.sort_order, RestaurantSection.name)
        result = await db.execute(stmt)
        sections = result.scalars().all()
        output = []
        for section in sections:
            output.append(
                await SectionsService._resolve_section_response(db, section)
            )
        return output

    @staticmethod
    async def get_section(
        db: AsyncSession, section_id: int, tenant_id: int,
    ) -> dict:
        section = await SectionsService._get_section(db, section_id, tenant_id)
        return await SectionsService._resolve_section_response(db, section)

    @staticmethod
    async def update_section(
        db: AsyncSession, section_id: int, tenant_id: int, data: dict,
    ) -> dict:
        section = await SectionsService._get_section(db, section_id, tenant_id)
        if "name" in data and data["name"] is not None:
            # Verificar unicidad si cambia el nombre
            if data["name"] != section.name:
                existing = await db.execute(
                    select(RestaurantSection).where(
                        RestaurantSection.tenant_id == tenant_id,
                        RestaurantSection.name == data["name"],
                        RestaurantSection.id != section_id,
                    )
                )
                if existing.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Ya existe otra sección con nombre '{data['name']}'",
                    )
            section.name = data["name"]
        if "description" in data:
            section.description = data["description"]
        if "sort_order" in data and data["sort_order"] is not None:
            section.sort_order = data["sort_order"]
        section.updated_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(section)
        return await SectionsService._resolve_section_response(db, section)

    @staticmethod
    async def delete_section(
        db: AsyncSession, section_id: int, tenant_id: int,
    ) -> None:
        section = await SectionsService._get_section(db, section_id, tenant_id)
        # Verificar si hay mesas asociadas
        count_result = await db.execute(
            select(func.count()).select_from(Table).where(
                Table.section_id == section.id,
            )
        )
        table_count = count_result.scalar() or 0
        if table_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"No se puede eliminar: {table_count} mesa(s) asociada(s). Reasigne las mesas primero.",
            )
        await db.delete(section)
        await db.flush()


class MenuService:

    @staticmethod
    async def list_items(
        db: AsyncSession, tenant_id: int,
        category: str | None = None, active_only: bool = False,
    ) -> list[dict]:
        stmt = select(MenuItem).where(MenuItem.tenant_id == tenant_id)
        if category:
            stmt = stmt.where(MenuItem.category == category)
        if active_only:
            stmt = stmt.where(MenuItem.active == True)
        stmt = stmt.order_by(MenuItem.category, MenuItem.name)
        result = await db.execute(stmt)
        items = result.scalars().all()

        output = []
        for item in items:
            mods_result = await db.execute(
                select(MenuModifier).where(MenuModifier.menu_item_id == item.id)
            )
            mods = mods_result.scalars().all()
            output.append({
                "id": item.id, "name": item.name,
                "description": item.description,
                "price": float(item.price),
                "cost_price": float(item.cost_price) if item.cost_price else None,
                "category": item.category, "item_type": item.item_type, "preparation_area": item.preparation_area,
                "modifiers": [
                    {"id": m.id, "name": m.name,
                     "price_adjustment": float(m.price_adjustment),
                     "max_select": m.max_select}
                    for m in mods
                ] if item.modifiers or mods else (item.modifiers or []),
                "image_url": item.image_url, "active": item.active,
            })
        return output

    @staticmethod
    async def get_item(db: AsyncSession, item_id: int, tenant_id: int) -> MenuItem:
        stmt = select(MenuItem).where(
            MenuItem.id == item_id, MenuItem.tenant_id == tenant_id,
        )
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Ítem de menú no encontrado")
        return item

    @staticmethod
    async def create_item(
        db: AsyncSession, tenant_id: int, data: dict,
    ) -> dict:
        modifiers_data = data.pop("modifiers", [])
        item = MenuItem(tenant_id=tenant_id, **data)
        db.add(item)
        await db.flush()

        for mod in (modifiers_data or []):
            pa = mod.get("price_adjustment", 0)
            if not isinstance(pa, (int, float)) or pa < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"price_adjustment inválido para '{mod.get('name')}': debe ser >= 0",
                )
            ms = mod.get("max_select", 1)
            if not isinstance(ms, int) or ms < 1 or ms > 100:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"max_select inválido para '{mod.get('name')}': debe ser entre 1 y 100",
                )
            db.add(MenuModifier(
                menu_item_id=item.id,
                name=mod["name"],
                price_adjustment=pa,
                max_select=ms,
            ))
        await db.flush()
        await db.refresh(item)
        return {"id": item.id, "name": item.name,
                "active": item.active, "preparation_area": item.preparation_area,
                "modifiers": modifiers_data or []}

    @staticmethod
    async def update_item(
        db: AsyncSession, item_id: int, tenant_id: int, data: dict,
    ) -> dict:
        item = await MenuService.get_item(db, item_id, tenant_id)
        allowed = {"name", "description", "price", "cost_price", "category",
                   "item_type", "preparation_area", "image_url", "active"}
        for key, value in data.items():
            if key in allowed and value is not None:
                setattr(item, key, value)

        # ── Modifiers: replace all if present ──
        if "modifiers" in data:
            # 1. Delete existing modifiers for this item
            existing_mods = await db.execute(
                select(MenuModifier).where(MenuModifier.menu_item_id == item.id)
            )
            for mod in existing_mods.scalars().all():
                db.delete(mod)

            # 2. Create new modifiers
            for mod in (data["modifiers"] or []):
                pa = mod.get("price_adjustment", 0)
                if not isinstance(pa, (int, float)) or pa < 0:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"price_adjustment inválido para '{mod.get('name')}': debe ser >= 0",
                    )
                ms = mod.get("max_select", 1)
                if not isinstance(ms, int) or ms < 1 or ms > 100:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"max_select inválido para '{mod.get('name')}': debe ser entre 1 y 100",
                    )
                db.add(MenuModifier(
                    menu_item_id=item.id,
                    name=mod["name"],
                    price_adjustment=pa,
                    max_select=ms,
                ))

        item.updated_at = datetime.now(UTC)
        await db.flush()
        return {"id": item.id, "name": item.name,
                "active": item.active, "preparation_area": item.preparation_area}


# ═══════════════════════════════════════════════════════════════
# Kitchen Orders Service (F0-005, F0-006)
# ═══════════════════════════════════════════════════════════════

class KitchenOrdersService:

    @staticmethod
    async def get_order(db: AsyncSession, order_id: int, tenant_id: int) -> KitchenOrder:
        stmt = select(KitchenOrder).where(
            KitchenOrder.id == order_id, KitchenOrder.tenant_id == tenant_id,
        )
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Orden no encontrada")
        return order

    @staticmethod
    async def remove_item(
        db: AsyncSession, order_id: int, menu_item_id: int, tenant_id: int,
    ) -> dict:
        order = await KitchenOrdersService.get_order(db, order_id, tenant_id)
        if order.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La orden ya fue enviada a cocina",
            )
        items = list(order.items or [])
        found = False
        for i, item in enumerate(items):
            if item.get("menu_item_id") == menu_item_id:
                if item.get("quantity", 1) > 1:
                    items[i]["quantity"] -= 1
                else:
                    items.pop(i)
                found = True
                break
        if not found:
            raise HTTPException(status_code=404, detail="Item no encontrado en la orden")
        order.items = items
        await db.flush()
        await db.refresh(order)
        detail = await KitchenOrdersService.get_order_detail(db, order.id, tenant_id)
        await manager.broadcast_to_kitchen(tenant_id, "update_order", detail)
        return detail

    @staticmethod
    async def get_order_detail(
        db: AsyncSession, order_id: int, tenant_id: int,
    ) -> dict:
        order = await KitchenOrdersService.get_order(db, order_id, tenant_id)
        table_number = None
        if order.table_id:
            table = await db.execute(
                select(Table).where(Table.id == order.table_id)
            )
            t = table.scalar_one_or_none()
            if t:
                table_number = t.number
        return {
            "id": order.id, "tenant_id": order.tenant_id,
            "table_id": order.table_id, "table_number": table_number,
            "status": order.status, "items": order.items or [],
            "notes": order.notes,
            "ordered_at": order.ordered_at.isoformat() if order.ordered_at else None,
            "started_at": order.started_at.isoformat() if order.started_at else None,
            "completed_at": order.completed_at.isoformat() if order.completed_at else None,
        }

    @staticmethod
    async def create_order(
        db: AsyncSession, tenant_id: int, table_id: int,
        items_data: list[dict],
    ) -> dict:
        # Validar mesa ocupada
        table = await TablesService.get_table(db, table_id, tenant_id)
        if table.status != "occupied":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La mesa no está ocupada",
            )

        validated = []
        total = 0.0
        for item_data in items_data:
            menu_item = await MenuService.get_item(
                db, item_data["menu_item_id"], tenant_id,
            )
            if not menu_item.active:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Ítem '{menu_item.name}' no disponible",
                )

            qty = item_data.get("quantity", 1)
            unit_price = float(menu_item.price)
            mods_total = 0.0

            # Validar modifiers con max_select (F0-005)
            modifiers = item_data.get("modifiers", [])
            mod_counts: dict[int, int] = {}
            for mod in modifiers:
                mid = mod.get("id") if isinstance(mod, dict) else mod
                if mid:
                    mod_qty = mod.get("quantity", 1) if isinstance(mod, dict) else 1
                    mod_counts[mid] = mod_counts.get(mid, 0) + max(1, mod_qty)

            for mid, count in mod_counts.items():
                db_mod = (await db.execute(
                    select(MenuModifier).where(
                        MenuModifier.id == mid,
                        MenuModifier.menu_item_id == menu_item.id,
                    )
                )).scalar_one_or_none()
                if db_mod:
                    if count > db_mod.max_select:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Modificador '{db_mod.name}': máximo {db_mod.max_select}, enviados {count}",
                        )
                    mods_total += float(db_mod.price_adjustment) * count

            item_total = qty * (unit_price + mods_total)
            total += item_total

            validated.append({
                "menu_item_id": menu_item.id, "name": menu_item.name,
                "quantity": qty, "unit_price": unit_price,
                "modifiers": modifiers, "modifiers_total": mods_total,
                "notes": item_data.get("notes", ""), "total": item_total,
                "item_type": menu_item.item_type, "preparation_area": menu_item.preparation_area,
            })

        # Buscar orden pending existente de esta mesa
        existing = await db.execute(
            select(KitchenOrder).where(
                KitchenOrder.table_id == table_id,
                KitchenOrder.tenant_id == tenant_id,
                KitchenOrder.status == "pending",
            )
        )
        existing_order = existing.scalar_one_or_none()

        if existing_order:
            # Agregar items a la orden existente
            current_items = list(existing_order.items or [])
            current_items.extend(validated)
            existing_order.items = current_items
            existing_order.notes = None
            await db.flush()
            await db.refresh(existing_order)
            detail = await KitchenOrdersService.get_order_detail(db, existing_order.id, tenant_id)
            await manager.broadcast_to_kitchen(tenant_id, "update_order", detail)
            return detail

        # Crear nueva orden (primera vez)
        order = KitchenOrder(
            tenant_id=tenant_id, table_id=table_id,
            status="pending", items=validated,
            notes=None,
        )
        db.add(order)
        await db.flush()
        await db.refresh(order)
        detail = await KitchenOrdersService.get_order_detail(db, order.id, tenant_id)
        await manager.broadcast_to_kitchen(tenant_id, "new_order", detail)
        return detail

    @staticmethod
    async def send_to_kitchen(
        db: AsyncSession, order_id: int, tenant_id: int,
    ) -> dict:
        order = await KitchenOrdersService.get_order(db, order_id, tenant_id)
        if order.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"No se puede enviar: estado actual '{order.status}'",
            )
        order.status = "preparing"
        order.started_at = datetime.now(UTC)
        await db.flush()

        detail = await KitchenOrdersService.get_order_detail(db, order_id, tenant_id)
        await manager.broadcast_to_kitchen(tenant_id, "order_updated", detail)
        return detail

    @staticmethod
    async def update_status(
        db: AsyncSession, order_id: int, tenant_id: int, new_status: str,
    ) -> dict:
        order = await KitchenOrdersService.get_order(db, order_id, tenant_id)
        valid_transitions = {
            "pending": ["preparing", "cancelled"],
            "preparing": ["ready", "cancelled"],
            "ready": ["delivered"],
            "delivered": [],
            "cancelled": [],
        }
        allowed = valid_transitions.get(order.status, [])
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Transición inválida: '{order.status}' → '{new_status}'",
            )

        order.status = new_status
        if new_status == "preparing":
            order.started_at = datetime.now(UTC)
        elif new_status == "ready":
            order.completed_at = datetime.now(UTC)

        await db.flush()

        detail = await KitchenOrdersService.get_order_detail(db, order_id, tenant_id)
        await manager.broadcast_to_kitchen(tenant_id, "order_updated", detail)

        if new_status == "ready":
            await manager.broadcast_to_waiter(tenant_id, "order_ready", {
                "order_id": order_id,
                "table_number": detail.get("table_number"),
                "status": "ready",
            })

        return detail

    @staticmethod
    async def list_active_orders(
        db: AsyncSession, tenant_id: int,
        status_filter: str | None = None,
    ) -> list[dict]:
        stmt = select(KitchenOrder).where(KitchenOrder.tenant_id == tenant_id)
        if status_filter:
            stmt = stmt.where(KitchenOrder.status == status_filter)
        else:
            # Sin filtro: excluir solo cancelados, mantener delivered
            stmt = stmt.where(KitchenOrder.status != "cancelled")
        stmt = stmt.order_by(KitchenOrder.ordered_at.desc())
        result = await db.execute(stmt)
        orders = result.scalars().all()

        output = []
        for o in orders:
            table_number = None
            if o.table_id:
                t_result = await db.execute(
                    select(Table).where(Table.id == o.table_id)
                )
                t = t_result.scalar_one_or_none()
                if t:
                    table_number = t.number
            output.append({
                "id": o.id, "table_id": o.table_id,
                "table_number": table_number,
                "status": o.status, "items": o.items or [],
                "notes": o.notes,
                "ordered_at": o.ordered_at.isoformat() if o.ordered_at else None,
                "started_at": o.started_at.isoformat() if o.started_at else None,
                "completed_at": o.completed_at.isoformat() if o.completed_at else None,
            })
        return output


# ═══════════════════════════════════════════════════════════════
# Close & Pay Service (F0-007)
# ═══════════════════════════════════════════════════════════════

class ClosePayService:

    @staticmethod
    async def close_order(
        db: AsyncSession, table_id: int, tenant_id: int,
    ) -> dict:
        table = await TablesService.get_table(db, table_id, tenant_id)
        if table.status != "occupied":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La mesa no está ocupada",
            )

        # Obtener órdenes activas de la mesa
        stmt = select(KitchenOrder).where(
            KitchenOrder.table_id == table_id,
            KitchenOrder.tenant_id == tenant_id,
            KitchenOrder.status != "cancelled",
        ).order_by(KitchenOrder.ordered_at.asc())

        result = await db.execute(stmt)
        orders = result.scalars().all()

        all_items = []
        subtotal = 0.0
        for order in orders:
            for item in (order.items or []):
                all_items.append(item)
                subtotal += float(item.get("total", 0))

        igv = round(subtotal * 0.18 / 1.18, 2)
        total = subtotal

        return {
            "table_id": table_id, "table_number": table.number,
            "status": table.status, "subtotal": round(subtotal, 2),
            "igv": igv, "total": round(total, 2),
            "items": all_items,
        }

    @staticmethod
    async def pay_table(
        db: AsyncSession, table_id: int, tenant_id: int,
        payment_data: dict,
    ) -> dict:
        summary = await ClosePayService.close_order(db, table_id, tenant_id)
        table = await TablesService.get_table(db, table_id, tenant_id)

        user_id = payment_data.get("user_id", 1)

        # Buscar sesión POS abierta
        from app.adapters.db.models.sales import PosSession
        session_result = await db.execute(
            select(PosSession).where(
                PosSession.tenant_id == tenant_id,
                PosSession.status == "open",
            )
        )
        session = session_result.scalar_one_or_none()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay sesión POS abierta. Abra una caja primero.",
            )

        # Generar número de venta
        now = datetime.now(UTC)
        count_result = await db.execute(
            select(func.count()).select_from(Sale).where(
                Sale.tenant_id == tenant_id,
                func.extract("year", Sale.sale_date) == now.year,
            )
        )
        count = count_result.scalar() or 0
        sale_number = f"VEN-{now.year}-{count + 1:05d}"

        # ── Resolver payments (nuevo formato o legacy) ──
        from app.schemas.restaurant import PayTableRequest
        payments = PayTableRequest.resolve_payments(payment_data)

        if not payments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere al menos un método de pago",
            )

        total_paid = sum(p["amount"] for p in payments)
        if total_paid < summary["total"] - 0.01:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Los montos no cubren el total ({summary['total']})",
            )

        tip_amount = payment_data.get("tip_amount", 0)
        tip_pct = payment_data.get("tip_pct", 0)
        igv = summary["igv"]

        # Crear venta
        sale = Sale(
            tenant_id=tenant_id, session_id=session.id,
            user_id=user_id, sale_number=sale_number,
            sale_date=now.date(), sale_time=now.time(),
            customer_name=payment_data.get("customer_name"),
            subtotal=summary["subtotal"], discount_total=0,
            tax_total=igv, tip_amount=tip_amount,
            total=summary["total"], business_type="restaurant",
        )
        db.add(sale)
        await db.flush()

        # Crear SaleItems
        for item in summary["items"]:
            db.add(SaleItem(
                sale_id=sale.id,
                item_name=item.get("name", "Item"),
                item_type="product",
                quantity=item.get("quantity", 1),
                unit_of_measure="unidad",
                unit_price=item.get("unit_price", 0),
                total=item.get("total", 0),
            ))

        # ── Kardex: Descontar insumos de platos con receta ──
        for item in summary["items"]:
            menu_item_id = item.get("menu_item_id")
            if menu_item_id:
                qty_sold = float(item.get("quantity", 1))
                await RecipesService.explode_for_sale(
                    db=db,
                    menu_item_id=menu_item_id,
                    quantity_sold=qty_sold,
                    sale_id=sale.id,
                    sale_number=sale_number,
                    menu_item_name=item.get("name", "Item"),
                    today=now.date(),
                    tenant_id=tenant_id,
                )

        # Crear pagos (múltiples si split)
        created_payments = []
        for p in payments:
            sp = SalePayment(
                sale_id=sale.id,
                payment_method=p["method"],
                amount=p["amount"],
                reference=p.get("reference"),
            )
            db.add(sp)
            created_payments.append({
                "method": p["method"],
                "amount": p["amount"],
                "reference": p.get("reference"),
            })

        # Especialización restaurante
        db.add(RestaurantSaleModel(
            sale_id=sale.id,
            table_number=str(table.number),
            guests=payment_data.get("guest_count", 1),
            order_type="dine_in",
            waiter_name=payment_data.get("waiter_name"),
            tip_amount=tip_amount, tip_pct=tip_pct,
        ))

        # NO liberar mesa — el mesero libera manualmente
        await db.flush()

        first_method = payments[0]["method"]
        total_paid_actual = sum(p["amount"] for p in payments)
        change = max(0, total_paid_actual - summary["total"])

        return {
            "sale_id": sale.id, "sale_number": sale_number,
            "table_number": str(table.number),
            "subtotal": summary["subtotal"], "igv": igv,
            "tip": tip_amount, "total": summary["total"],
            "payments": created_payments,
            "payment_method": first_method,
            "amount_paid": round(total_paid_actual, 2),
            "change": round(change, 2),
        }


    @staticmethod
    async def get_table_orders_status(
        db: AsyncSession, table_id: int, tenant_id: int,
    ) -> dict:
        """
        Retorna el estado de las comandas de una mesa.
        Útil para que el frontend sepa si habilitar el botón Pagar.

        Returns:
            {"all_delivered": bool, "total": float, "items": [...]}
        """
        table = await TablesService.get_table(db, table_id, tenant_id)

        stmt = select(KitchenOrder).where(
            KitchenOrder.table_id == table_id,
            KitchenOrder.tenant_id == tenant_id,
            KitchenOrder.status != "cancelled",
        ).order_by(KitchenOrder.ordered_at.asc())

        result = await db.execute(stmt)
        orders = result.scalars().all()

        all_items = []
        total = 0.0
        delivered_count = 0
        total_orders = len(orders)

        for order in orders:
            if order.status == "delivered":
                delivered_count += 1
            for item in (order.items or []):
                all_items.append({
                    "name": item.get("name", "Item"),
                    "quantity": item.get("quantity", 1),
                    "unit_price": item.get("unit_price", 0),
                    "total": item.get("total", 0),
                    "menu_item_id": item.get("menu_item_id"),
                })
                total += float(item.get("total", 0))

        all_delivered = total_orders > 0 and delivered_count == total_orders

        return {
            "all_delivered": all_delivered,
            "total": round(total, 2),
            "items": all_items,
            "orders_count": total_orders,
            "delivered_count": delivered_count,
        }


# ═══════════════════════════════════════════════════════════════
# Takeaway Service (F0-009)
# ═══════════════════════════════════════════════════════════════

class TakeawayService:

    @staticmethod
    async def create(
        db: AsyncSession, tenant_id: int, data: dict,
    ) -> dict:
        items_data = data.get("items", [])
        if not items_data:
            raise HTTPException(status_code=400, detail="Se requiere al menos un ítem")

        validated = []
        total = 0.0
        for item_data in items_data:
            menu_item = await MenuService.get_item(
                db, item_data["menu_item_id"], tenant_id,
            )
            if not menu_item.active:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Ítem '{menu_item.name}' no disponible",
                )

            qty = item_data.get("quantity", 1)
            unit_price = float(menu_item.price)
            mods_total = 0.0

            # Validar modifiers con max_select y sumar price_adjustment (HU-F0-016)
            modifiers = item_data.get("modifiers", [])
            mod_counts: dict[int, int] = {}
            for mod in modifiers:
                mid = mod.get("id") if isinstance(mod, dict) else mod
                if mid:
                    mod_qty = mod.get("quantity", 1) if isinstance(mod, dict) else 1
                    mod_counts[mid] = mod_counts.get(mid, 0) + max(1, mod_qty)

            for mid, count in mod_counts.items():
                db_mod = (await db.execute(
                    select(MenuModifier).where(
                        MenuModifier.id == mid,
                        MenuModifier.menu_item_id == menu_item.id,
                    )
                )).scalar_one_or_none()
                if db_mod:
                    if count > db_mod.max_select:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Modificador '{db_mod.name}': máximo {db_mod.max_select}, enviados {count}",
                        )
                    mods_total += float(db_mod.price_adjustment) * count

            item_total = qty * (unit_price + mods_total)
            total += item_total

            validated.append({
                "menu_item_id": menu_item.id, "name": menu_item.name,
                "quantity": qty, "unit_price": unit_price,
                "modifiers": modifiers, "modifiers_total": mods_total,
                "notes": item_data.get("notes", ""), "total": item_total,
                "item_type": menu_item.item_type, "preparation_area": menu_item.preparation_area,
            })

        raw_pickup = data.get("pickup_time")
        if raw_pickup:
            try:
                pickup_dt = datetime.fromisoformat(raw_pickup)
                if pickup_dt.tzinfo is None:
                    pickup_dt = pickup_dt.replace(tzinfo=LIMA_TZ)
            except (ValueError, TypeError):
                pickup_dt = None
        else:
            pickup_dt = None

        order = TakeawayOrder(
            tenant_id=tenant_id,
            customer_name=data.get("customer_name"),
            customer_phone=data.get("customer_phone"),
            items=validated, pickup_time=pickup_dt,
            status="pending", notes=data.get("notes"),
        )
        db.add(order)
        await db.flush()
        await db.refresh(order)

        await manager.broadcast_to_kitchen(tenant_id, "new_takeaway", {
            "id": order.id, "customer_name": order.customer_name,
            "items": validated, "status": "pending",
        })

        return {
            "id": order.id, "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "status": order.status, "items": validated,
            "pickup_time": _fmt_dt(order.pickup_time),
            "notes": order.notes,
            "created_at": _fmt_dt(order.created_at),
        }

    @staticmethod
    async def list_orders(
        db: AsyncSession, tenant_id: int,
        status_filter: str | None = None,
    ) -> list[dict]:
        stmt = select(TakeawayOrder).where(
            TakeawayOrder.tenant_id == tenant_id,
        )
        if status_filter:
            # Soporta múltiples status separados por coma (HU-F0-016 Kanban)
            statuses = [s.strip() for s in status_filter.split(",") if s.strip()]
            if statuses:
                stmt = stmt.where(TakeawayOrder.status.in_(statuses))
        else:
            # Sin filtro: solo activos (excluye terminales para Kanban)
            stmt = stmt.where(
                TakeawayOrder.status != "picked_up",
                TakeawayOrder.status != "cancelled",
            )
        stmt = stmt.order_by(TakeawayOrder.created_at.desc())
        result = await db.execute(stmt)
        return [
            {
                "id": o.id, "customer_name": o.customer_name,
                "customer_phone": o.customer_phone,
                "status": o.status, "items": o.items or [],
                "pickup_time": _fmt_dt(o.pickup_time),
                "notes": o.notes,
                "created_at": _fmt_dt(o.created_at),
            }
            for o in result.scalars().all()
        ]

    @staticmethod
    async def update_status(
        db: AsyncSession, order_id: int, tenant_id: int, new_status: str,
    ) -> dict:
        """Actualiza el estado de un pedido takeaway desde cocina (HU-F0-016)."""
        stmt = select(TakeawayOrder).where(
            TakeawayOrder.id == order_id,
            TakeawayOrder.tenant_id == tenant_id,
        )
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")

        valid_transitions = {
            "pending": ["preparing", "cancelled"],
            "preparing": ["ready", "cancelled"],
            "ready": ["picked_up"],
            "picked_up": [],
            "cancelled": [],
        }
        allowed = valid_transitions.get(order.status, [])
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Transición inválida: '{order.status}' → '{new_status}'",
            )

        order.status = new_status
        if new_status == "preparing":
            order.updated_at = datetime.now(UTC)
        elif new_status == "ready":
            order.updated_at = datetime.now(UTC)
        elif new_status == "picked_up":
            order.updated_at = datetime.now(UTC)
        else:
            order.updated_at = datetime.now(UTC)

        await db.flush()

        detail = {
            "id": order.id, "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "status": order.status, "items": order.items or [],
            "pickup_time": _fmt_dt(order.pickup_time),
            "notes": order.notes,
            "created_at": _fmt_dt(order.created_at),
            "type": "takeaway",
        }
        await manager.broadcast_to_kitchen(tenant_id, "order_updated", detail)
        return detail

    @staticmethod
    async def mark_pickup(
        db: AsyncSession, order_id: int, tenant_id: int,
    ) -> dict:
        stmt = select(TakeawayOrder).where(
            TakeawayOrder.id == order_id,
            TakeawayOrder.tenant_id == tenant_id,
        )
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        if order.status == "picked_up":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El pedido ya fue recogido",
            )
        order.status = "picked_up"
        order.updated_at = datetime.now(UTC)
        await db.flush()
        return {"id": order.id, "status": "picked_up"}


# ═══════════════════════════════════════════════════════════════
# Promotions Service (F0-008)
# ═══════════════════════════════════════════════════════════════

class PromotionsService:

    @staticmethod
    async def create_promotion(
        db: AsyncSession, tenant_id: int, data: dict,
    ) -> dict:
        promo = Promotion(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            promo_type=data["promo_type"],
            rules=data.get("rules"),
            discount_value=data["discount_value"],
            valid_from=data["valid_from"],
            valid_to=data.get("valid_to"),
            active=data.get("active", True),
        )
        db.add(promo)
        await db.flush()
        await db.refresh(promo)
        return {
            "id": promo.id, "tenant_id": promo.tenant_id,
            "name": promo.name, "description": promo.description,
            "promo_type": promo.promo_type, "rules": promo.rules,
            "discount_value": float(promo.discount_value),
            "valid_from": promo.valid_from.isoformat() if promo.valid_from else None,
            "valid_to": promo.valid_to.isoformat() if promo.valid_to else None,
            "active": promo.active,
            "created_at": promo.created_at.isoformat() if promo.created_at else None,
        }

    @staticmethod
    async def list_promotions(
        db: AsyncSession, tenant_id: int, active_only: bool = True,
    ) -> list[dict]:
        stmt = select(Promotion).where(Promotion.tenant_id == tenant_id)
        if active_only:
            stmt = stmt.where(Promotion.active == True)
        stmt = stmt.order_by(Promotion.created_at.desc())
        result = await db.execute(stmt)
        return [
            {
                "id": p.id, "tenant_id": p.tenant_id,
                "name": p.name, "description": p.description,
                "promo_type": p.promo_type, "rules": p.rules,
                "discount_value": float(p.discount_value),
                "valid_from": p.valid_from.isoformat() if p.valid_from else None,
                "valid_to": p.valid_to.isoformat() if p.valid_to else None,
                "active": p.active,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in result.scalars().all()
        ]

    @staticmethod
    async def update_promotion(
        db: AsyncSession, promo_id: int, tenant_id: int, data: dict,
    ) -> dict:
        stmt = select(Promotion).where(
            Promotion.id == promo_id, Promotion.tenant_id == tenant_id,
        )
        result = await db.execute(stmt)
        promo = result.scalar_one_or_none()
        if not promo:
            raise HTTPException(status_code=404, detail="Promoción no encontrada")

        allowed = {"name", "description", "rules", "discount_value",
                   "valid_from", "valid_to", "active"}
        for key, value in data.items():
            if key in allowed and value is not None:
                setattr(promo, key, value)
        promo.updated_at = datetime.now(UTC)
        await db.flush()
        return {"id": promo.id, "name": promo.name, "active": promo.active}

    @staticmethod
    async def apply_promotion(
        db: AsyncSession, order_id: int, promo_id: int, tenant_id: int,
    ) -> dict:
        # Validar promoción
        promo = (await db.execute(
            select(Promotion).where(
                Promotion.id == promo_id, Promotion.tenant_id == tenant_id,
            )
        )).scalar_one_or_none()
        if not promo:
            raise HTTPException(status_code=404, detail="Promoción no encontrada")
        if not promo.active:
            raise HTTPException(status_code=400, detail="Promoción inactiva")

        now = datetime.now(UTC)
        if promo.valid_to and now > promo.valid_to:
            raise HTTPException(status_code=410, detail="Promoción expirada")
        if now < promo.valid_from:
            raise HTTPException(status_code=400, detail="Promoción aún no vigente")

        # Obtener orden
        order = await KitchenOrdersService.get_order(db, order_id, tenant_id)
        items = list(order.items or [])
        subtotal = sum(float(i.get("total", 0)) for i in items)

        # Validar condiciones
        rules = promo.rules or {}

        discount = 0.0
        if promo.promo_type == "combo":
            required_ids = set(rules.get("items", []))
            order_ids = {i.get("menu_item_id") for i in items}
            if required_ids and required_ids.issubset(order_ids):
                discount = subtotal - float(promo.discount_value)
        elif promo.promo_type == "discount_pct":
            discount = round(subtotal * float(promo.discount_value) / 100, 2)
        elif promo.promo_type == "discount_fixed":
            min_amount = rules.get("min_amount", 0)
            if subtotal >= min_amount:
                discount = float(promo.discount_value)
        elif promo.promo_type == "bogof":
            buy_id = rules.get("buy_item_id")
            qty_per_item: dict[int, int] = {}
            for i in items:
                mid = i.get("menu_item_id")
                qty_per_item[mid] = qty_per_item.get(mid, 0) + i.get("quantity", 1)
            if buy_id and buy_id in qty_per_item:
                free_units = qty_per_item[buy_id] // 2
                for i in items:
                    if i.get("menu_item_id") == buy_id:
                        discount = free_units * float(i.get("unit_price", 0))

        discount = min(discount, subtotal)
        new_total = round(subtotal - discount, 2)

        return {
            "order_id": order_id,
            "promotion_id": promo.id,
            "promotion_name": promo.name,
            "discount_applied": round(discount, 2),
            "new_total": new_total,
        }


# ═══════════════════════════════════════════════════════════════
# Recipes Service (Caso 6: Recetas e Insumos)
# ═══════════════════════════════════════════════════════════════


class RecipesService:
    """
    Lógica de negocio para recetas de platos.

    Solo ítems con preparation_area='cocina' pueden tener receta.
    """

    @staticmethod
    async def _get_menu_item(
        db: AsyncSession, menu_item_id: int, tenant_id: int,
    ) -> MenuItem:
        """Obtiene un ítem de menú validando tenant."""
        from app.services.restaurant_service import MenuService
        return await MenuService.get_item(db, menu_item_id, tenant_id)

    @staticmethod
    async def _validate_cooking_item(
        db: AsyncSession, menu_item_id: int, tenant_id: int,
    ) -> MenuItem:
        """Valida que el ítem sea de cocina y retorna el item."""
        item = await RecipesService._get_menu_item(db, menu_item_id, tenant_id)
        if item.preparation_area != "cocina":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo platos con área de preparación '🍳 Cocina' pueden tener receta",
            )
        return item

    @staticmethod
    async def get_recipe(
        db: AsyncSession, menu_item_id: int, tenant_id: int,
    ) -> dict:
        """
        GET /menu/{id}/recipe — Obtener receta de un plato.

        Retorna ingredientes + costo total + margen.
        Si el plato no es de cocina, retorna error.
        Si no tiene receta, retorna estructura vacía.
        """
        item = await RecipesService._validate_cooking_item(db, menu_item_id, tenant_id)

        # Buscar receta
        stmt = select(Recipe).options(
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.product),
        ).where(Recipe.menu_item_id == menu_item_id)
        result = await db.execute(stmt)
        recipe = result.scalar_one_or_none()

        if not recipe:
            return {
                "id": None,
                "menu_item_id": menu_item_id,
                "menu_item_name": item.name,
                "has_recipe": False,
                "ingredients": [],
                "total_estimated_cost": 0.0,
                "menu_item_price": float(item.price),
                "margin": float(item.price) if item.price else 0.0,
                "margin_pct": 100.0 if item.price else 0.0,
                "created_at": None,
                "updated_at": None,
            }

        ingredients = []
        total_cost = 0.0
        for ing in recipe.ingredients:
            avg_cost = float(ing.product.average_cost) if ing.product and ing.product.average_cost else 0.0
            est_cost = round(avg_cost * float(ing.quantity), 4)
            total_cost += est_cost
            ingredients.append({
                "product_id": ing.product_id,
                "product_name": ing.product.name if ing.product else "Producto eliminado",
                "quantity": float(ing.quantity),
                "unit_of_measure": ing.unit_of_measure,
                "sort_order": ing.sort_order,
                "average_cost": avg_cost,
                "estimated_cost": est_cost,
            })

        total_cost = round(total_cost, 2)
        menu_price = float(item.price) if item.price else 0.0
        margin = round(menu_price - total_cost, 2) if menu_price else 0.0
        margin_pct = round((margin / menu_price) * 100, 1) if menu_price > 0 else 0.0

        return {
            "id": recipe.id,
            "menu_item_id": menu_item_id,
            "menu_item_name": item.name,
            "has_recipe": True,
            "ingredients": ingredients,
            "total_estimated_cost": total_cost,
            "menu_item_price": menu_price,
            "margin": margin,
            "margin_pct": margin_pct,
            "created_at": recipe.created_at.isoformat() if recipe.created_at else None,
            "updated_at": recipe.updated_at.isoformat() if recipe.updated_at else None,
        }

    @staticmethod
    async def save_recipe(
        db: AsyncSession, menu_item_id: int, tenant_id: int,
        ingredients_data: list[dict],
    ) -> dict:
        """
        PUT /menu/{id}/recipe — Guardar/actualizar receta completa.

        Reemplaza ingredientes completamente (delete + insert).
        Solo funciona para platos de cocina.
        """
        item = await RecipesService._validate_cooking_item(db, menu_item_id, tenant_id)

        # Buscar o crear receta
        stmt = select(Recipe).where(Recipe.menu_item_id == menu_item_id)
        result = await db.execute(stmt)
        recipe = result.scalar_one_or_none()

        if not recipe:
            recipe = Recipe(menu_item_id=menu_item_id)
            db.add(recipe)
            await db.flush()

        # Eliminar ingredientes existentes (cascade)
        existing_ingredients = await db.execute(
            select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
        )
        for ing in existing_ingredients.scalars().all():
            await db.delete(ing)

        # Validar productos y crear nuevos ingredientes
        for i, ing_data in enumerate(ingredients_data):
            product_id = ing_data["product_id"]
            quantity = ing_data["quantity"]
            unit_of_measure = ing_data.get("unit_of_measure", "unidad")
            sort_order = ing_data.get("sort_order", i)

            # Validar que el producto exista y pertenezca al tenant
            product_stmt = select(Product).where(
                Product.id == product_id,
                Product.tenant_id == tenant_id,
            )
            product_result = await db.execute(product_stmt)
            product = product_result.scalar_one_or_none()
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Producto #{product_id} no encontrado",
                )

            db.add(RecipeIngredient(
                recipe_id=recipe.id,
                product_id=product_id,
                quantity=quantity,
                unit_of_measure=unit_of_measure,
                sort_order=sort_order,
            ))

        await db.flush()
        await db.refresh(recipe)

        # Devolver la receta actualizada
        return await RecipesService.get_recipe(db, menu_item_id, tenant_id)

    @staticmethod
    async def list_products_for_recipe(
        db: AsyncSession, tenant_id: int,
    ) -> list[dict]:
        """
        GET /products — Listar productos del inventario para selector de receta.

        Retorna id, name, unit_of_measure, average_cost, current_stock.
        Solo productos activos con stock > 0.
        """
        stmt = select(Product).where(
            Product.tenant_id == tenant_id,
            Product.active == True,
        ).order_by(Product.name)
        result = await db.execute(stmt)
        products = result.scalars().all()

        return [
            {
                "id": p.id,
                "name": p.name,
                "unit_of_measure": p.unit_of_measure,
                "average_cost": float(p.average_cost) if p.average_cost else 0.0,
                "current_stock": float(p.current_stock) if p.current_stock else 0.0,
            }
            for p in products
        ]

    @staticmethod
    async def explode_for_sale(
        db: AsyncSession,
        menu_item_id: int,
        quantity_sold: float,
        sale_id: int,
        sale_number: str,
        menu_item_name: str,
        today: date,
        tenant_id: int,
    ) -> list[dict]:
        """
        Crea movimientos kárdex de salida para cada ingrediente de la receta
        de un plato vendido.

        Args:
            db: Sesión de base de datos
            menu_item_id: ID del ítem de menú vendido
            quantity_sold: Cuántas porciones se vendieron
            sale_id: ID de la venta asociada
            sale_number: Número de venta (ej: VEN-2026-00001)
            menu_item_name: Nombre del plato para el concepto
            today: Fecha del movimiento
            tenant_id: ID del tenant

        Returns:
            Lista de dicts con info de kárdex creados, vacía si el plato no tiene receta

        Nota:
            - Si el plato no tiene receta → retorna [] (sin error)
            - Si un ingrediente no existe como producto → skip con log
            - Si no hay suficiente stock → NO bloquea, registra kárdex con stock negativo
        """
        if quantity_sold <= 0:
            return []

        # Buscar receta del plato
        stmt = select(Recipe).options(
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.product),
        ).where(Recipe.menu_item_id == menu_item_id)
        result = await db.execute(stmt)
        recipe = result.scalar_one_or_none()

        if not recipe:
            # Plato sin receta — skip sin error
            return []

        kardex_movements = []

        for ing in recipe.ingredients:
            product = ing.product
            if not product:
                logger.warning(
                    "explode_for_sale: ingrediente #%d sin producto (product_id=%d) — skip",
                    ing.id, ing.product_id,
                )
                continue

            # Calcular cantidad a deducir
            qty_to_deduct = round(float(ing.quantity) * quantity_sold, 4)
            if qty_to_deduct <= 0:
                continue

            avg_cost = float(product.average_cost) if product.average_cost else 0.0
            exit_total = round(qty_to_deduct * avg_cost, 2)

            # Calcular nuevo stock (puede ser negativo)
            new_qty = round(float(product.current_stock) - qty_to_deduct, 4)
            new_avg_cost = avg_cost if new_qty > 0 else 0.0
            new_balance_total = round(new_qty * new_avg_cost, 2)

            concept = f"Venta #{sale_number} - Plato: {menu_item_name}"

            kardex_move = KardexMovement(
                product_id=product.id,
                movement_type="salida",
                concept=concept,
                reference_type="venta",
                reference_id=sale_id,
                quantity=qty_to_deduct,
                unit_cost=avg_cost,
                total=exit_total,
                balance_quantity=new_qty,
                balance_avg_cost=new_avg_cost,
                balance_total=new_balance_total,
                date=today,
            )
            db.add(kardex_move)
            await db.flush()
            await db.refresh(kardex_move)

            # Actualizar stock del producto
            product.current_stock = new_qty

            kardex_movements.append({
                "kardex_movement_id": kardex_move.id,
                "product_id": product.id,
                "product_name": product.name,
                "quantity": qty_to_deduct,
                "unit_cost": avg_cost,
                "total": exit_total,
                "new_stock": new_qty,
            })

        await db.flush()
        return kardex_movements
