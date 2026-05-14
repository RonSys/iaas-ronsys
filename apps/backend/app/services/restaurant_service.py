"""
🍽️ Restaurant Service — Lógica de negocio (F0-004 a F0-008).

HU: Mesas, menú, comandas, takeaway, pagos y promociones.
"""

from datetime import datetime, UTC
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.restaurant import (
    KitchenOrder,
    MenuItem,
    MenuModifier,
    Promotion,
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
    ) -> list[dict]:
        stmt = select(Table).where(Table.tenant_id == tenant_id)
        if status_filter:
            stmt = stmt.where(Table.status == status_filter)
        stmt = stmt.order_by(Table.number)
        result = await db.execute(stmt)
        return [
            {"id": t.id, "number": t.number, "capacity": t.capacity,
             "status": t.status, "section": t.section,
             "guests": t.guests, "waiter_name": t.waiter_name,
             "opened_at": t.opened_at.isoformat() if t.opened_at else None}
            for t in result.scalars().all()
        ]

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
    async def create_table(
        db: AsyncSession, tenant_id: int, number: str,
        capacity: int = 4, section: str | None = None,
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
        )
        db.add(table)
        await db.flush()
        await db.refresh(table)
        return {
            "id": table.id, "number": table.number,
            "capacity": table.capacity, "status": table.status,
            "section": table.section,
        }

    @staticmethod
    async def update_table(
        db: AsyncSession, table_id: int, tenant_id: int, body: dict,
    ) -> dict:
        table = await TablesService.get_table(db, table_id, tenant_id)
        for key in ("number", "capacity", "section"):
            if key in body and body[key] is not None:
                setattr(table, key, body[key])
        table.updated_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(table)
        return {
            "id": table.id, "number": table.number,
            "capacity": table.capacity, "status": table.status,
            "section": table.section,
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


# ═══════════════════════════════════════════════════════════════
# Menu Service (F0-005)
# ═══════════════════════════════════════════════════════════════

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
                "category": item.category, "item_type": item.item_type,
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
            db.add(MenuModifier(
                menu_item_id=item.id,
                name=mod["name"],
                price_adjustment=mod.get("price_adjustment", 0),
                max_select=mod.get("max_select", 1),
            ))
        await db.flush()
        await db.refresh(item)
        return {"id": item.id, "name": item.name, "active": item.active}

    @staticmethod
    async def update_item(
        db: AsyncSession, item_id: int, tenant_id: int, data: dict,
    ) -> dict:
        item = await MenuService.get_item(db, item_id, tenant_id)
        allowed = {"name", "description", "price", "cost_price", "category",
                   "item_type", "image_url", "active"}
        for key, value in data.items():
            if key in allowed and value is not None:
                setattr(item, key, value)
        item.updated_at = datetime.now(UTC)
        await db.flush()
        return {"id": item.id, "name": item.name, "active": item.active}


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
                    mod_counts[mid] = mod_counts.get(mid, 0) + 1

            for mid, count in mod_counts.items():
                db_mod = (await db.execute(
                    select(MenuModifier).where(MenuModifier.id == mid)
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
            })

        order = KitchenOrder(
            tenant_id=tenant_id, table_id=table_id,
            status="pending", items=validated,
            notes=None,
        )
        db.add(order)
        await db.flush()
        await db.refresh(order)

        # Broadcast a cocina
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
        stmt = select(KitchenOrder).where(
            KitchenOrder.tenant_id == tenant_id,
            KitchenOrder.status != "delivered",
            KitchenOrder.status != "cancelled",
        )
        if status_filter:
            stmt = stmt.where(KitchenOrder.status == status_filter)
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

        method = payment_data.get("payment_method", "cash")
        amount = payment_data.get("amount", summary["total"])
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

        # Crear pago
        db.add(SalePayment(
            sale_id=sale.id, payment_method=method,
            amount=min(amount, summary["total"]),
            reference=payment_data.get("reference"),
        ))

        # Especialización restaurante
        db.add(RestaurantSaleModel(
            sale_id=sale.id,
            table_number=str(table.number),
            guests=payment_data.get("guest_count", 1),
            order_type="dine_in",
            waiter_name=payment_data.get("waiter_name"),
            tip_amount=tip_amount, tip_pct=tip_pct,
        ))

        # Liberar mesa
        table.status = "available"
        table.guests = None
        table.waiter_name = None
        table.opened_at = None
        await db.flush()

        change = max(0, amount - summary["total"])

        return {
            "sale_id": sale.id, "sale_number": sale_number,
            "table_number": str(table.number),
            "subtotal": summary["subtotal"], "igv": igv,
            "tip": tip_amount, "total": summary["total"],
            "payment_method": method, "amount_paid": min(amount, summary["total"]),
            "change": round(change, 2),
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
            item_total = qty * float(menu_item.price)
            total += item_total
            validated.append({
                "menu_item_id": menu_item.id, "name": menu_item.name,
                "quantity": qty, "unit_price": float(menu_item.price),
                "modifiers": item_data.get("modifiers", []),
                "notes": item_data.get("notes", ""), "total": item_total,
            })

        order = TakeawayOrder(
            tenant_id=tenant_id,
            customer_name=data.get("customer_name"),
            customer_phone=data.get("customer_phone"),
            items=validated, pickup_time=data.get("pickup_time"),
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
            "pickup_time": order.pickup_time.isoformat() if order.pickup_time else None,
            "notes": order.notes,
            "created_at": order.created_at.isoformat() if order.created_at else None,
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
            stmt = stmt.where(TakeawayOrder.status == status_filter)
        stmt = stmt.order_by(TakeawayOrder.created_at.desc())
        result = await db.execute(stmt)
        return [
            {
                "id": o.id, "customer_name": o.customer_name,
                "customer_phone": o.customer_phone,
                "status": o.status, "items": o.items or [],
                "pickup_time": o.pickup_time.isoformat() if o.pickup_time else None,
                "notes": o.notes,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in result.scalars().all()
        ]

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
