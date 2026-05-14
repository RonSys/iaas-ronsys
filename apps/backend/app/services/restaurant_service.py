"""
🍽️ Restaurant Service — Lógica de negocio para restaurante.

HU-F0-004 a F0-008, HU-F0-013: Mesas, pedidos, comandas, takeaway, promociones, pagos.
"""

import json
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.accounting import Company, KardexMovement, Product
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
from app.core.ws_manager import manager as ws_manager


# ═══════════════════════════════════════════════════════════════
# Tables Service (HU-F0-004)
# ═══════════════════════════════════════════════════════════════


class TablesService:
    """Gestión de mesas del salón."""

    @staticmethod
    async def list_tables(db: AsyncSession, tenant_id: int, status: str | None = None) -> list[dict]:
        """Lista todas las mesas del tenant."""
        stmt = select(Table).where(Table.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(Table.status == status)
        stmt = stmt.order_by(Table.number)
        result = await db.execute(stmt)
        tables = result.scalars().all()

        return [
            {
                "id": t.id,
                "number": t.number,
                "capacity": t.capacity,
                "status": t.status,
                "section": t.section,
                "qr_code": t.qr_code,
            }
            for t in tables
        ]

    @staticmethod
    async def get_table(db: AsyncSession, table_id: int, tenant_id: int) -> Table:
        """Obtiene una mesa por ID con scoping de tenant."""
        stmt = select(Table).where(Table.id == table_id, Table.tenant_id == tenant_id)
        result = await db.execute(stmt)
        table = result.scalar_one_or_none()
        if not table:
            raise HTTPException(status_code=404, detail="Mesa no encontrada")
        return table

    @staticmethod
    async def open_table(db: AsyncSession, table_id: int, tenant_id: int,
                         guest_count: int = 1, waiter_id: int | None = None) -> dict:
        """HU-F0-004: Abre una mesa (free → occupied)."""
        table = await TablesService.get_table(db, table_id, tenant_id)

        if table.status != "free":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La mesa ya está ocupada",
            )

        table.status = "occupied"
        await db.flush()

        return {
            "id": table.id,
            "number": table.number,
            "status": "occupied",
            "opened_at": datetime.now(UTC).isoformat(),
            "guest_count": guest_count,
            "session_token": f"table_{table.id}_{int(datetime.now(UTC).timestamp())}",
        }

    @staticmethod
    async def close_table_if_free(db: AsyncSession, table_id: int, tenant_id: int):
        """Cierra una mesa (occupied → free), llamada después de pagar."""
        table = await TablesService.get_table(db, table_id, tenant_id)
        table.status = "free"
        await db.flush()


# ═══════════════════════════════════════════════════════════════
# Menu Service (HU-F0-005)
# ═══════════════════════════════════════════════════════════════


class MenuService:
    """Gestión del menú/carta."""

    @staticmethod
    async def list_menu_items(db: AsyncSession, tenant_id: int,
                               category: str | None = None,
                               available_only: bool = False) -> list[dict]:
        """Lista ítems del menú."""
        stmt = select(MenuItem).where(MenuItem.tenant_id == tenant_id)
        if category:
            stmt = stmt.where(MenuItem.category == category)
        if available_only:
            stmt = stmt.where(MenuItem.available == True)
        stmt = stmt.order_by(MenuItem.category, MenuItem.name)
        result = await db.execute(stmt)
        items = result.scalars().all()

        return [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "category": item.category,
                "price": float(item.price),
                "cost": float(item.cost) if item.cost else None,
                "unit": item.unit,
                "image_url": item.image_url,
                "available": item.available,
                "has_modifiers": item.has_modifiers,
                "modifiers": [
                    {
                        "id": m.id,
                        "name": m.name,
                        "price_adjustment": float(m.price_adjustment),
                        "max_select": m.max_select,
                    }
                    for m in item.modifiers
                ] if item.has_modifiers else [],
            }
            for item in items
        ]

    @staticmethod
    async def get_menu_item(db: AsyncSession, item_id: int, tenant_id: int) -> MenuItem:
        """Obtiene un ítem del menú por ID."""
        stmt = select(MenuItem).where(
            MenuItem.id == item_id,
            MenuItem.tenant_id == tenant_id,
        )
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Ítem de menú no encontrado")
        return item

    @staticmethod
    async def create_menu_item(db: AsyncSession, tenant_id: int, data: dict) -> dict:
        """Crea un ítem del menú con sus modificadores."""
        modifiers_data = data.pop("modifiers", [])

        item = MenuItem(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            category=data["category"],
            price=data["price"],
            cost=data.get("cost"),
            unit=data.get("unit", "plato"),
            image_url=data.get("image_url"),
            available=data.get("available", True),
            has_modifiers=bool(modifiers_data),
        )
        db.add(item)
        await db.flush()

        # Crear modificadores
        for mod_data in modifiers_data:
            modifier = MenuModifier(
                menu_item_id=item.id,
                name=mod_data["name"],
                price_adjustment=mod_data.get("price_adjustment", 0),
                max_select=mod_data.get("max_select", 1),
            )
            db.add(modifier)

        await db.flush()
        await db.refresh(item)

        # Retornar con modificadores
        result = await MenuService.list_menu_items(db, tenant_id)
        return next((i for i in result if i["id"] == item.id), {})

    @staticmethod
    async def update_menu_item(db: AsyncSession, item_id: int,
                                tenant_id: int, data: dict) -> dict:
        """Actualiza un ítem del menú (parcial)."""
        item = await MenuService.get_menu_item(db, item_id, tenant_id)

        allowed_fields = {
            "name", "description", "category", "price", "cost",
            "unit", "image_url", "available", "has_modifiers",
        }
        for key, value in data.items():
            if key in allowed_fields and value is not None:
                setattr(item, key, value)

        item.updated_at = func.now()
        await db.flush()
        await db.refresh(item)

        return {
            "id": item.id,
            "name": item.name,
            "available": item.available,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }


# ═══════════════════════════════════════════════════════════════
# Kitchen Orders Service (HU-F0-005, F0-006, F0-007)
# ═══════════════════════════════════════════════════════════════


class KitchenOrdersService:
    """Gestión de comandas/pedidos de cocina."""

    @staticmethod
    async def get_order(db: AsyncSession, order_id: int, tenant_id: int) -> KitchenOrder:
        """Obtiene una orden por ID con scoping."""
        stmt = select(KitchenOrder).where(
            KitchenOrder.id == order_id,
            KitchenOrder.tenant_id == tenant_id,
        )
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Orden no encontrada")
        return order

    @staticmethod
    async def create_order_for_table(
        db: AsyncSession, tenant_id: int, table_id: int,
        items_data: list[dict],
    ) -> dict:
        """HU-F0-005: Crea una orden para una mesa."""
        # Validar mesa ocupada
        table = await TablesService.get_table(db, table_id, tenant_id)
        if table.status != "occupied":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La mesa no está ocupada",
            )

        # Validar ítems y calcular total
        validated_items = []
        total = 0.0

        for item_data in items_data:
            menu_item = await MenuService.get_menu_item(
                db, item_data["menu_item_id"], tenant_id
            )
            if not menu_item.available:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Ítem '{menu_item.name}' no disponible",
                )

            qty = item_data.get("quantity", 1)
            unit_price = float(menu_item.price)
            modifiers_total = 0.0

            # Validar modificadores
            modifiers = item_data.get("modifiers", [])
            if menu_item.has_modifiers:
                # F0-005: Validar max_select por modificador
                modifier_counts: dict[int, int] = {}
                for mod in modifiers:
                    mod_id = mod.get("id") if isinstance(mod, dict) else mod.get("modifier_id")
                    if mod_id:
                        modifier_counts[mod_id] = modifier_counts.get(mod_id, 0) + 1

                for mod_id, count in modifier_counts.items():
                    from sqlalchemy import select as sa_select
                    stmt = sa_select(MenuModifier).where(MenuModifier.id == mod_id)
                    result = await db.execute(stmt)
                    db_mod = result.scalar_one_or_none()
                    if db_mod:
                        if count > db_mod.max_select:
                            raise HTTPException(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"Modificador '{db_mod.name}': máximo {db_mod.max_select} selección(es), se enviaron {count}",
                            )
                        modifiers_total += float(db_mod.price_adjustment) * count

            item_total = qty * (unit_price + modifiers_total)
            total += item_total

            validated_items.append({
                "menu_item_id": menu_item.id,
                "name": menu_item.name,
                "quantity": qty,
                "unit_price": unit_price,
                "modifiers": modifiers,
                "modifiers_total": modifiers_total,
                "notes": item_data.get("notes", ""),
                "total": item_total,
            })

        # Buscar orden existente (para agregar ítems)
        stmt = select(KitchenOrder).where(
            KitchenOrder.tenant_id == tenant_id,
            KitchenOrder.table_id == table_id,
            KitchenOrder.status.in_(["pending", "preparing"]),
        ).order_by(KitchenOrder.created_at.desc()).limit(1)

        result = await db.execute(stmt)
        existing_order = result.scalar_one_or_none()

        if existing_order:
            # Agregar ítems a orden existente
            current_items = list(existing_order.items or [])
            current_items.extend(validated_items)
            existing_order.items = current_items
            existing_order.updated_at = datetime.now(UTC)
            await db.flush()
            order = existing_order
        else:
            # Crear nueva orden
            order = KitchenOrder(
                tenant_id=tenant_id,
                table_id=table_id,
                order_type="dine_in",
                status="pending",
                items=validated_items,
                priority=0,
            )
            db.add(order)
            await db.flush()

        await db.refresh(order)
        return {
            "order_id": order.id,
            "items_count": len(validated_items),
            "total": round(total, 2),
            "status": order.status,
        }

    @staticmethod
    async def get_order_detail(
        db: AsyncSession, order_id: int, tenant_id: int,
    ) -> dict:
        """Obtiene detalle completo de una orden."""
        order = await KitchenOrdersService.get_order(db, order_id, tenant_id)

        items_list = list(order.items or [])
        subtotal = sum(
            float(i.get("total", 0)) for i in items_list
        )

        # Calcular minutos transcurridos
        elapsed = 0
        if order.sent_at:
            delta = datetime.now(UTC) - order.sent_at.replace(tzinfo=None) if order.sent_at.tzinfo else datetime.now(UTC) - order.sent_at
            elapsed = int(delta.total_seconds() / 60)

        # Obtener número de mesa
        table_number = None
        if order.table_id:
            try:
                table = await TablesService.get_table(db, order.table_id, tenant_id)
                table_number = table.number
            except Exception:
                pass

        return {
            "id": order.id,
            "tenant_id": order.tenant_id,
            "sale_id": order.sale_id,
            "table_id": order.table_id,
            "table_number": table_number,
            "order_type": order.order_type,
            "status": order.status,
            "items": items_list,
            "priority": order.priority,
            "notes": order.notes,
            "sent_at": order.sent_at.isoformat() if order.sent_at else None,
            "completed_at": order.completed_at.isoformat() if order.completed_at else None,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "subtotal": round(subtotal, 2),
            "elapsed_minutes": elapsed,
        }

    @staticmethod
    async def send_to_kitchen(
        db: AsyncSession, order_id: int, tenant_id: int,
    ) -> dict:
        """HU-F0-006: Envía orden a cocina (status → 'preparing')."""
        order = await KitchenOrdersService.get_order(db, order_id, tenant_id)

        if order.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La orden ya fue enviada a cocina",
            )

        order.status = "preparing"
        order.sent_at = datetime.now(UTC)
        await db.flush()

        # Emitir WebSocket new_order
        detail = await KitchenOrdersService.get_order_detail(db, order_id, tenant_id)
        await ws_manager.broadcast_to_kitchen(
            tenant_id, "new_order", detail
        )

        return {
            "order_id": order.id,
            "status": "preparing",
            "sent_at": order.sent_at.isoformat() if order.sent_at else None,
            "items_count": len(order.items or []),
        }

    @staticmethod
    async def update_order_status(
        db: AsyncSession, order_id: int, tenant_id: int, new_status: str,
    ) -> dict:
        """HU-F0-006: Cambia estado de una orden."""
        order = await KitchenOrdersService.get_order(db, order_id, tenant_id)

        valid_transitions = {
            "pending": ["preparing", "cancelled"],
            "preparing": ["ready", "cancelled"],
            "ready": ["served", "cancelled"],
            "served": [],
            "cancelled": [],
        }

        if new_status not in valid_transitions.get(order.status, []):
            raise HTTPException(
                status_code=400,
                detail=f"Transición inválida: {order.status} → {new_status}",
            )

        order.status = new_status

        if new_status == "ready":
            order.completed_at = datetime.now(UTC)
            # Notificar a meseros
            detail = await KitchenOrdersService.get_order_detail(db, order_id, tenant_id)
            await ws_manager.broadcast_to_waiter(
                tenant_id, "order_ready", {
                    "order_id": order_id,
                    "table_number": detail.get("table_number"),
                    "status": "ready",
                }
            )

        if new_status == "cancelled":
            await ws_manager.broadcast_to_all(
                tenant_id, "order_cancelled", {"order_id": order_id}
            )

        await db.flush()
        return {"order_id": order.id, "status": order.status}

    @staticmethod
    async def list_active_orders(
        db: AsyncSession, tenant_id: int,
        status_filter: str | None = None,
    ) -> list[dict]:
        """Lista órdenes activas (para sync de WS y pantalla cocina)."""
        stmt = select(KitchenOrder).where(
            KitchenOrder.tenant_id == tenant_id,
            KitchenOrder.status.in_(["pending", "preparing", "ready"]),
        )
        if status_filter:
            stmt = stmt.where(KitchenOrder.status == status_filter)
        stmt = stmt.order_by(KitchenOrder.sent_at.asc().nullsfirst(), KitchenOrder.created_at.asc())
        result = await db.execute(stmt)
        orders = result.scalars().all()

        output = []
        for order in orders:
            detail = await KitchenOrdersService.get_order_detail(db, order.id, tenant_id)
            output.append(detail)

        return output


# ═══════════════════════════════════════════════════════════════
# Close & Pay Service (HU-F0-007)
# ═══════════════════════════════════════════════════════════════


class ClosePayService:
    """Cierre de comanda y pago."""

    IGV_RATE = 0.18

    @staticmethod
    async def close_order(db: AsyncSession, table_id: int, tenant_id: int) -> dict:
        """HU-F0-007: Cierra comanda y genera resumen de cuenta."""
        table = await TablesService.get_table(db, table_id, tenant_id)

        # Buscar órdenes activas de la mesa
        stmt = select(KitchenOrder).where(
            KitchenOrder.tenant_id == tenant_id,
            KitchenOrder.table_id == table_id,
            KitchenOrder.order_type == "dine_in",
        ).order_by(KitchenOrder.created_at.desc())

        result = await db.execute(stmt)
        all_orders = result.scalars().all()

        # Verificar que no haya órdenes en preparing/pending
        pending = [o for o in all_orders if o.status in ("pending", "preparing")]
        if pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Hay órdenes pendientes de servir",
            )

        # Recopilar ítems servidos
        served_items = []
        for order in all_orders:
            if order.status in ("ready", "served"):
                served_items.extend(list(order.items or []))

        if not served_items:
            raise HTTPException(
                status_code=400,
                detail="No hay ítems consumidos en esta mesa",
            )

        subtotal = sum(float(i.get("total", 0)) for i in served_items)
        igv = round(subtotal * self.IGV_RATE / (1 + self.IGV_RATE), 2)
        total = round(subtotal, 2)

        return {
            "table_number": table.number,
            "items": served_items,
            "subtotal": round(subtotal, 2),
            "igv": igv,
            "total": total,
            "payment_pending": True,
        }

    @staticmethod
    async def pay_table(
        db: AsyncSession, table_id: int, tenant_id: int,
        payment_data: dict,
    ) -> dict:
        """HU-F0-007: Procesa pago, integra con sistema de ventas."""
        table = await TablesService.get_table(db, table_id, tenant_id)

        # Obtener resumen de cuenta
        summary = await ClosePayService.close_order(db, table_id, tenant_id)

        # Obtener usuario actual (pasado desde el router)
        user_id = payment_data.get("user_id", 1)

        # Buscar sesión POS abierta
        from app.adapters.db.models.sales import PosSession
        stmt = select(PosSession).where(
            PosSession.tenant_id == tenant_id,
            PosSession.status == "open",
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=400, detail="No hay sesión POS abierta")

        # Generar sale number
        today = datetime.now(UTC)
        sale_count_stmt = select(func.count()).select_from(Sale).where(
            Sale.tenant_id == tenant_id,
            func.extract("year", Sale.sale_date) == today.year,
        )
        count_result = await db.execute(sale_count_stmt)
        count = count_result.scalar() or 0

        sale_number = f"VEN-{today.year}-{count + 1:05d}"
        method = payment_data.get("payment_method", "cash")
        amount = payment_data.get("amount", summary["total"])
        tip_amount = payment_data.get("tip_amount", 0)
        tip_pct = payment_data.get("tip_pct", 0)
        igv = summary.get("igv", round(summary["total"] * 0.18 / 1.18, 2))

        # Crear venta
        sale = Sale(
            tenant_id=tenant_id,
            session_id=session.id,
            user_id=user_id,
            sale_number=sale_number,
            sale_date=today.date(),
            sale_time=today.time(),
            customer_name=payment_data.get("customer_name"),
            subtotal=summary["subtotal"],
            discount_total=0,
            tax_total=igv,
            tip_amount=tip_amount,
            total=summary["total"],
            business_type="restaurant",
        )
        db.add(sale)
        await db.flush()

        # Crear SaleItems desde los ítems de la orden
        for order_item in summary["items"]:
            sale_item = SaleItem(
                sale_id=sale.id,
                item_name=order_item.get("name", "Item"),
                item_type="product",
                quantity=order_item.get("quantity", 1),
                unit_of_measure="unidad",
                unit_price=order_item.get("unit_price", 0),
                total=order_item.get("total", 0),
            )
            db.add(sale_item)

        # Crear pago
        sale_payment = SalePayment(
            sale_id=sale.id,
            payment_method=method,
            amount=min(amount, summary["total"]),
            reference=payment_data.get("reference"),
        )
        db.add(sale_payment)

        # Crear especialización restaurante
        rs = RestaurantSaleModel(
            sale_id=sale.id,
            table_number=str(table.number),
            guests=payment_data.get("guest_count", 1),
            order_type="dine_in",
            waiter_name=payment_data.get("waiter_name"),
            tip_amount=tip_amount,
            tip_pct=tip_pct,
        )
        db.add(rs)

        # HU-F0-016: Registrar salidas de kárdex si los ítems tienen product_id
        for order_item in summary["items"]:
            product_id = order_item.get("product_id")
            if product_id:
                prod_result = await db.execute(
                    select(Product).where(Product.id == product_id)
                )
                product = prod_result.scalar_one_or_none()
                if product:
                    qty = float(order_item.get("quantity", 1))
                    avg_cost = float(product.average_cost)
                    exit_total = round(qty * avg_cost, 2)
                    new_qty = float(product.current_stock) - qty
                    new_total = round(new_qty * avg_cost, 2)

                    kardex_move = KardexMovement(
                        product_id=product_id,
                        movement_type="salida",
                        concept=f"Venta #{sale_number}",
                        reference_type="venta",
                        reference_id=sale.id,
                        quantity=qty,
                        unit_cost=avg_cost,
                        total=exit_total,
                        balance_quantity=new_qty,
                        balance_avg_cost=avg_cost,
                        balance_total=new_total,
                        date=today.date(),
                    )
                    db.add(kardex_move)
                    product.current_stock = new_qty

        # Liberar mesa
        table.status = "free"

        await db.flush()

        # Calcular vuelto si aplica
        change = max(0, amount - summary["total"])

        return {
            "sale_id": sale.id,
            "sale_number": sale_number,
            "total": summary["total"],
            "change": round(change, 2),
            "payment_method": method,
            "ticket": {
                "sale_number": sale_number,
                "items": summary["items"],
                "subtotal": summary["subtotal"],
                "igv": igv,
                "total": summary["total"],
                "tip": tip_amount,
            },
        }


# ═══════════════════════════════════════════════════════════════
# Takeaway Service (HU-F0-013)
# ═══════════════════════════════════════════════════════════════


class TakeawayService:
    """Gestión de pedidos takeaway."""

    @staticmethod
    async def create_takeaway(
        db: AsyncSession, tenant_id: int, data: dict,
    ) -> dict:
        """Crea un pedido takeaway y lo envía a cocina automáticamente."""
        items_data = data.get("items", [])
        validated_items = []

        for item_data in items_data:
            menu_item = await MenuService.get_menu_item(
                db, item_data["menu_item_id"], tenant_id
            )
            if not menu_item.available:
                raise HTTPException(
                    status_code=422,
                    detail=f"Ítem '{menu_item.name}' no disponible",
                )

            qty = item_data.get("quantity", 1)
            unit_price = float(menu_item.price)
            item_total = qty * unit_price

            validated_items.append({
                "menu_item_id": menu_item.id,
                "name": menu_item.name,
                "quantity": qty,
                "unit_price": unit_price,
                "modifiers": item_data.get("modifiers", []),
                "notes": item_data.get("notes", ""),
                "total": item_total,
            })

        # Crear orden de cocina primero
        kitchen_order = KitchenOrder(
            tenant_id=tenant_id,
            order_type="takeaway",
            status="pending",
            items=validated_items,
            notes=data.get("notes"),
        )
        db.add(kitchen_order)
        await db.flush()

        # Crear takeaway order
        pickup_time = data.get("pickup_time")
        if pickup_time and isinstance(pickup_time, str):
            from datetime import datetime as dt
            try:
                pickup_time = dt.fromisoformat(pickup_time)
            except (ValueError, TypeError):
                pickup_time = None

        takeaway = TakeawayOrder(
            tenant_id=tenant_id,
            customer_name=data.get("customer_name"),
            customer_phone=data.get("customer_phone"),
            status="pending",
            items=validated_items,
            pickup_time=pickup_time,
        )
        db.add(takeaway)
        await db.flush()

        # Enviar a cocina automáticamente
        kitchen_order.status = "preparing"
        kitchen_order.sent_at = datetime.now(UTC)
        await db.flush()

        # Notificar por WS
        await ws_manager.broadcast_to_kitchen(
            tenant_id, "new_order", {
                "order_id": kitchen_order.id,
                "order_type": "takeaway",
                "items": validated_items,
                "customer_name": data.get("customer_name"),
            }
        )

        return {
            "order_id": takeaway.id,
            "kitchen_order_id": kitchen_order.id,
            "status": takeaway.status,
            "items_count": len(validated_items),
            "estimated_pickup_time": pickup_time.isoformat() if pickup_time else None,
        }

    @staticmethod
    async def list_takeaway(
        db: AsyncSession, tenant_id: int,
        status: str | None = None,
    ) -> list[dict]:
        """Lista pedidos takeaway."""
        stmt = select(TakeawayOrder).where(TakeawayOrder.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(TakeawayOrder.status == status)
        stmt = stmt.order_by(TakeawayOrder.pickup_time.asc().nullsfirst(),
                             TakeawayOrder.created_at.desc())

        result = await db.execute(stmt)
        orders = result.scalars().all()

        now = datetime.now(UTC)
        output = []
        for o in orders:
            is_late = False
            if o.status in ("ready",) and o.pickup_time:
                if now > o.pickup_time.replace(tzinfo=None) if o.pickup_time.tzinfo else now > o.pickup_time:
                    is_late = True

            output.append({
                "id": o.id,
                "tenant_id": o.tenant_id,
                "sale_id": o.sale_id,
                "customer_name": o.customer_name,
                "customer_phone": o.customer_phone,
                "status": o.status,
                "items": o.items or [],
                "pickup_time": o.pickup_time.isoformat() if o.pickup_time else None,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "is_late": is_late,
            })

        return output

    @staticmethod
    async def mark_pickup(
        db: AsyncSession, order_id: int, tenant_id: int,
    ) -> dict:
        """Marca takeaway como recogido."""
        stmt = select(TakeawayOrder).where(
            TakeawayOrder.id == order_id,
            TakeawayOrder.tenant_id == tenant_id,
        )
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Pedido takeaway no encontrado")

        if order.status == "picked_up":
            raise HTTPException(status_code=409, detail="El pedido ya fue recogido")

        order.status = "picked_up"
        await db.flush()

        return {"id": order.id, "status": "picked_up"}


# ═══════════════════════════════════════════════════════════════
# Promotions Service (HU-F0-008)
# ═══════════════════════════════════════════════════════════════


class PromotionsService:
    """Gestión de promociones."""

    @staticmethod
    async def create_promotion(db: AsyncSession, tenant_id: int, data: dict) -> dict:
        """Crea una promoción."""
        # Validar fechas
        start_date = data.get("start_date")
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date)

        end_date = data.get("end_date")
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date) if end_date else None

        promotion = Promotion(
            tenant_id=tenant_id,
            name=data["name"],
            type=data["type"],
            discount_value=data["discount_value"],
            conditions=data.get("conditions", {}),
            start_date=start_date,
            end_date=end_date,
            active=data.get("active", True),
            max_uses=data.get("max_uses"),
        )
        db.add(promotion)
        await db.flush()
        await db.refresh(promotion)

        return {
            "id": promotion.id,
            "name": promotion.name,
            "type": promotion.type,
            "discount_value": float(promotion.discount_value),
            "active": promotion.active,
        }

    @staticmethod
    async def list_promotions(
        db: AsyncSession, tenant_id: int,
        active_only: bool = True,
    ) -> list[dict]:
        """Lista promociones del tenant."""
        stmt = select(Promotion).where(Promotion.tenant_id == tenant_id)
        if active_only:
            stmt = stmt.where(Promotion.active == True)
        stmt = stmt.order_by(Promotion.start_date.desc())
        result = await db.execute(stmt)
        promotions = result.scalars().all()

        return [
            {
                "id": p.id,
                "tenant_id": p.tenant_id,
                "name": p.name,
                "type": p.type,
                "discount_value": float(p.discount_value),
                "conditions": p.conditions,
                "start_date": p.start_date.isoformat() if p.start_date else None,
                "end_date": p.end_date.isoformat() if p.end_date else None,
                "active": p.active,
                "max_uses": p.max_uses,
                "current_uses": p.current_uses,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in promotions
        ]

    @staticmethod
    async def update_promotion(
        db: AsyncSession, promo_id: int, tenant_id: int, data: dict,
    ) -> dict:
        """Actualiza una promoción (parcial)."""
        stmt = select(Promotion).where(
            Promotion.id == promo_id,
            Promotion.tenant_id == tenant_id,
        )
        result = await db.execute(stmt)
        promo = result.scalar_one_or_none()
        if not promo:
            raise HTTPException(status_code=404, detail="Promoción no encontrada")

        allowed = {"name", "type", "discount_value", "conditions",
                   "start_date", "end_date", "active", "max_uses"}
        for key, value in data.items():
            if key in allowed and value is not None:
                if key in ("start_date", "end_date") and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                setattr(promo, key, value)

        await db.flush()
        return {"id": promo.id, "name": promo.name, "active": promo.active}

    @staticmethod
    async def apply_promotion(
        db: AsyncSession, order_id: int, promo_id: int, tenant_id: int,
    ) -> dict:
        """Aplica una promoción a una orden."""
        # Validar promoción
        stmt = select(Promotion).where(
            Promotion.id == promo_id,
            Promotion.tenant_id == tenant_id,
        )
        result = await db.execute(stmt)
        promo = result.scalar_one_or_none()
        if not promo:
            raise HTTPException(status_code=404, detail="Promoción no encontrada")

        now = datetime.now(UTC)

        # Validar activa
        if not promo.active:
            raise HTTPException(status_code=400, detail="Promoción inactiva")

        # Validar fechas
        if promo.end_date and now > promo.end_date.replace(tzinfo=None) if promo.end_date.tzinfo else now > promo.end_date:
            raise HTTPException(status_code=410, detail="Promoción expirada")

        if promo.start_date and promo.start_date.replace(tzinfo=None) if promo.start_date.tzinfo else now < promo.start_date:
            raise HTTPException(status_code=400, detail="Promoción aún no vigente")

        # Validar límite de usos
        if promo.max_uses and promo.current_uses >= promo.max_uses:
            raise HTTPException(status_code=409, detail="Límite de usos alcanzado")

        # Obtener orden
        order = await KitchenOrdersService.get_order(db, order_id, tenant_id)
        order_items = list(order.items or [])
        order_subtotal = sum(float(i.get("total", 0)) for i in order_items)

        # Validar condiciones
        conditions = promo.conditions or {}
        min_items = conditions.get("min_items", 0)
        min_amount = conditions.get("min_amount", 0)

        if min_items > 0 and len(order_items) < min_items:
            raise HTTPException(
                status_code=422,
                detail="No se cumplen las condiciones de la promoción",
            )

        if min_amount > 0 and order_subtotal < min_amount:
            raise HTTPException(
                status_code=422,
                detail="No se cumplen las condiciones de la promoción",
            )

        # Calcular descuento
        discount = 0.0
        if promo.type == "fixed_discount":
            discount = float(promo.discount_value)
        elif promo.type == "percentage_discount":
            discount = round(order_subtotal * float(promo.discount_value) / 100, 2)
        elif promo.type == "combo":
            discount = float(promo.discount_value)

        discount = min(discount, order_subtotal)  # No exceder subtotal
        new_total = round(order_subtotal - discount, 2)

        # Incrementar usos
        promo.current_uses += 1
        await db.flush()

        return {
            "order_id": order_id,
            "promotion_id": promo.id,
            "promotion_name": promo.name,
            "discount_applied": round(discount, 2),
            "new_total": new_total,
        }
