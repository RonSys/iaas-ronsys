"""
🍽️ Restaurant Router — Endpoints Restaurante (F0-004 a F0-008).

Endpoints:
  Tables:  GET /tables, GET /tables/{id}, POST /tables/{id}/open
  Menu:    GET /menu, POST /menu, PATCH /menu/{id}
  Orders:  POST /tables/{id}/order, GET /orders/{id}
           POST /orders/{id}/send-to-kitchen, PATCH /orders/{id}/status
           GET /orders/active
  Close:   POST /tables/{id}/close-order, POST /tables/{id}/pay
  Takeaway: POST /takeaway, GET /takeaway, PATCH /takeaway/{id}/pickup
  Promos:  POST /promotions, GET /promotions, PATCH /promotions/{id}
           POST /orders/{id}/apply-promotion/{promo_id}
  WebSocket: /ws/kitchen/{tenant_id}, /ws/waiter/{tenant_id}
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.core.dependencies import get_current_active_user, require_role
from app.core.ws_manager import manager
from app.models.user import User
from app.services.restaurant_service import (
    ClosePayService,
    KitchenOrdersService,
    MenuService,
    PromotionsService,
    TablesService,
    TakeawayService,
)

router = APIRouter(prefix="/api/v1/restaurant", tags=["Restaurante"])

# ─── Tenant depende de get_current_active_user ────────────
from app.core.tenant import get_tenant_id  # noqa: E402


# ═══════════════════════════════════════════════════════════════
# TABLES (F0-004)
# ═══════════════════════════════════════════════════════════════

@router.post("/tables", status_code=201)
async def create_table(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """Crea una nueva mesa."""
    number = body.get("number")
    if not number:
        raise HTTPException(status_code=400, detail="'number' es requerido")
    return await TablesService.create_table(
        db, tenant_id,
        number=str(number),
        capacity=body.get("capacity", 4),
        section=body.get("section"),
    )


@router.patch("/tables/{table_id}")
async def update_table(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """Actualiza una mesa (número, capacidad, sección)."""
    return await TablesService.update_table(db, table_id, tenant_id, body)


@router.delete("/tables/{table_id}", status_code=204)
async def delete_table(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Elimina una mesa (solo si está libre)."""
    await TablesService.delete_table(db, table_id, tenant_id)


@router.get("/tables")
async def list_tables(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(None, description="Filtrar por estado"),
):
    return await TablesService.list_tables(db, tenant_id, status)


@router.get("/tables/{table_id}")
async def get_table(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    table = await TablesService.get_table(db, table_id, tenant_id)
    return {
        "id": table.id, "number": table.number,
        "capacity": table.capacity, "status": table.status,
        "section": table.section,
    }


@router.post("/tables/{table_id}/open")
async def open_table(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    return await TablesService.open_table(
        db, table_id, tenant_id,
        guests=body.get("guests", 1),
        waiter_name=body.get("waiter_name"),
    )


# ═══════════════════════════════════════════════════════════════
# MENU (F0-005)
# ═══════════════════════════════════════════════════════════════

@router.get("/menu")
async def list_menu(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = Query(None),
    active_only: bool = Query(False, alias="available"),
):
    return await MenuService.list_items(db, tenant_id, category, active_only)


@router.post("/menu")
async def create_menu_item(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    return await MenuService.create_item(db, tenant_id, body)


@router.patch("/menu/{item_id}")
async def update_menu_item(
    item_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    return await MenuService.update_item(db, item_id, tenant_id, body)


# ═══════════════════════════════════════════════════════════════
# ORDERS (F0-005, F0-006)
# ═══════════════════════════════════════════════════════════════

@router.post("/tables/{table_id}/order")
async def take_order(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    items = body.get("items", [])
    if not items:
        raise HTTPException(status_code=400, detail="Se requiere al menos un ítem")
    return await KitchenOrdersService.create_order(db, tenant_id, table_id, items)


@router.get("/orders/{order_id}")
async def get_order_detail(
    order_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await KitchenOrdersService.get_order_detail(db, order_id, tenant_id)


@router.post("/orders/{order_id}/send-to-kitchen")
async def send_to_kitchen(
    order_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await KitchenOrdersService.send_to_kitchen(db, order_id, tenant_id)


@router.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    new_status = body.get("status", "")
    if not new_status:
        raise HTTPException(status_code=400, detail="Se requiere 'status'")
    return await KitchenOrdersService.update_status(db, order_id, tenant_id, new_status)


@router.get("/orders/active")
async def list_active_orders(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(None),
):
    return await KitchenOrdersService.list_active_orders(db, tenant_id, status)


# ═══════════════════════════════════════════════════════════════
# CLOSE & PAY (F0-007)
# ═══════════════════════════════════════════════════════════════

@router.post("/tables/{table_id}/close-order")
async def close_order(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await ClosePayService().close_order(db, table_id, tenant_id)


@router.post("/tables/{table_id}/pay")
async def pay_table(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    body["user_id"] = current_user.id
    return await ClosePayService().pay_table(db, table_id, tenant_id, body)


# ═══════════════════════════════════════════════════════════════
# TAKEAWAY (F0-009)
# ═══════════════════════════════════════════════════════════════

@router.post("/takeaway")
async def create_takeaway(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    return await TakeawayService.create(db, tenant_id, body)


@router.get("/takeaway")
async def list_takeaway(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(None),
):
    return await TakeawayService.list_orders(db, tenant_id, status)


@router.patch("/takeaway/{order_id}/pickup")
async def mark_takeaway_pickup(
    order_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await TakeawayService.mark_pickup(db, order_id, tenant_id)


# ═══════════════════════════════════════════════════════════════
# PROMOTIONS (F0-008)
# ═══════════════════════════════════════════════════════════════

@router.post("/promotions")
async def create_promotion(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    return await PromotionsService.create_promotion(db, tenant_id, body)


@router.get("/promotions")
async def list_promotions(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    active_only: bool = Query(True, alias="active"),
):
    return await PromotionsService.list_promotions(db, tenant_id, active_only)


@router.patch("/promotions/{promotion_id}")
async def update_promotion(
    promotion_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    return await PromotionsService.update_promotion(db, promotion_id, tenant_id, body)


@router.post("/orders/{order_id}/apply-promotion/{promotion_id}")
async def apply_promotion(
    order_id: int,
    promotion_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await PromotionsService.apply_promotion(db, order_id, promotion_id, tenant_id)


# ═══════════════════════════════════════════════════════════════
# WEBSOCKET (F0-006)
# ═══════════════════════════════════════════════════════════════

@router.websocket("/ws/kitchen/{tenant_id}")
async def kitchen_websocket(ws: WebSocket, tenant_id: int):
    await manager.connect_kitchen(tenant_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text('{"event": "pong"}')
    except WebSocketDisconnect:
        manager.disconnect_kitchen(tenant_id, ws)
    except Exception:
        manager.disconnect_kitchen(tenant_id, ws)


@router.websocket("/ws/waiter/{tenant_id}")
async def waiter_websocket(ws: WebSocket, tenant_id: int):
    await manager.connect_waiter(tenant_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text('{"event": "pong"}')
    except WebSocketDisconnect:
        manager.disconnect_waiter(tenant_id, ws)
    except Exception:
        manager.disconnect_waiter(tenant_id, ws)
