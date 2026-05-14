"""
🍽️ Restaurant Router — Endpoints para módulo Restaurante.

HU-F0-004 a F0-008, HU-F0-013:
  - Tables (abrir/cerrar/listar)
  - Menu (CRUD menú + modificadores)
  - Orders (tomar pedido, enviar a cocina, cambiar estado)
  - Close & Pay (cerrar comanda, pagar)
  - Takeaway (crear/listar/marcar recogido)
  - Promotions (CRUD + aplicar)
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.core.dependencies import get_current_active_user, require_role
from app.core.tenant import get_tenant_id
from app.core.ws_manager import manager as ws_manager
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


# ═══════════════════════════════════════════════════════════════
# TABLES (HU-F0-004)
# ═══════════════════════════════════════════════════════════════


@router.get("/tables")
async def list_tables(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(None, description="Filtrar por estado"),
):
    """Lista todas las mesas del tenant."""
    return await TablesService.list_tables(db, tenant_id, status)


@router.get("/tables/{table_id}")
async def get_table(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Obtiene detalle de una mesa por ID."""
    table = await TablesService.get_table(db, table_id, tenant_id)
    return {
        "id": table.id,
        "number": table.number,
        "capacity": table.capacity,
        "status": table.status,
        "section": table.section,
        "qr_code": table.qr_code,
    }


@router.post("/tables/{table_id}/open")
async def open_table(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """HU-F0-004: Abre una mesa."""
    guest_count = body.get("guest_count", 1)
    return await TablesService.open_table(
        db, table_id, tenant_id,
        guest_count=guest_count,
        waiter_id=int(current_user.id),
    )


# ═══════════════════════════════════════════════════════════════
# ORDERS (HU-F0-005, F0-006)
# ═══════════════════════════════════════════════════════════════


@router.post("/tables/{table_id}/order")
async def take_order(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """HU-F0-005: Toma pedido en una mesa."""
    items = body.get("items", [])
    if not items:
        raise HTTPException(status_code=400, detail="Se requiere al menos un ítem")

    return await KitchenOrdersService.create_order_for_table(
        db, tenant_id, table_id, items,
    )


@router.get("/orders/{order_id}")
async def get_order_detail(
    order_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Obtiene detalle completo de una orden."""
    return await KitchenOrdersService.get_order_detail(db, order_id, tenant_id)


@router.post("/orders/{order_id}/send-to-kitchen")
async def send_to_kitchen(
    order_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """HU-F0-006: Envía orden a cocina."""
    return await KitchenOrdersService.send_to_kitchen(db, order_id, tenant_id)


@router.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """Cambia estado de orden."""
    new_status = body.get("status", "")
    if not new_status:
        raise HTTPException(status_code=400, detail="Se requiere 'status'")

    return await KitchenOrdersService.update_order_status(
        db, order_id, tenant_id, new_status,
    )


@router.get("/orders/active")
async def list_active_orders(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(None, description="Filtrar por estado"),
):
    """Lista órdenes activas (para pantalla de cocina y sync WS)."""
    return await KitchenOrdersService.list_active_orders(db, tenant_id, status)


# ═══════════════════════════════════════════════════════════════
# CLOSE & PAY (HU-F0-007)
# ═══════════════════════════════════════════════════════════════


@router.post("/tables/{table_id}/close-order")
async def close_order(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """HU-F0-007: Cierra comanda de una mesa y genera resumen."""
    service = ClosePayService()
    return await service.close_order(db, table_id, tenant_id)


@router.post("/tables/{table_id}/pay")
async def pay_table(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """HU-F0-007: Procesa pago de mesa."""
    body["user_id"] = int(current_user.id)
    service = ClosePayService()
    return await service.pay_table(db, table_id, tenant_id, body)


# ═══════════════════════════════════════════════════════════════
# TAKEAWAY (HU-F0-013)
# ═══════════════════════════════════════════════════════════════


@router.post("/takeaway")
async def create_takeaway(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """Crea pedido takeaway y lo envía a cocina automáticamente."""
    return await TakeawayService.create_takeaway(db, tenant_id, body)


@router.get("/takeaway")
async def list_takeaway(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(None, description="Filtrar por estado"),
):
    """Lista pedidos takeaway."""
    return await TakeawayService.list_takeaway(db, tenant_id, status)


@router.patch("/takeaway/{order_id}/pickup")
async def mark_takeaway_pickup(
    order_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Marca takeaway como recogido."""
    return await TakeawayService.mark_pickup(db, order_id, tenant_id)


# ═══════════════════════════════════════════════════════════════
# PROMOTIONS (HU-F0-008)
# ═══════════════════════════════════════════════════════════════


@router.post("/promotions")
async def create_promotion(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """Crea una promoción."""
    return await PromotionsService.create_promotion(db, tenant_id, body)


@router.get("/promotions")
async def list_promotions(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    active_only: bool = Query(True, alias="active"),
):
    """Lista promociones."""
    return await PromotionsService.list_promotions(db, tenant_id, active_only)


@router.patch("/promotions/{promotion_id}")
async def update_promotion(
    promotion_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """Actualiza una promoción."""
    return await PromotionsService.update_promotion(db, promotion_id, tenant_id, body)


@router.post("/orders/{order_id}/apply-promotion/{promotion_id}")
async def apply_promotion(
    order_id: int,
    promotion_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Aplica una promoción a una orden."""
    return await PromotionsService.apply_promotion(db, order_id, promotion_id, tenant_id)


# ═══════════════════════════════════════════════════════════════
# MENU (CRUD)
# ═══════════════════════════════════════════════════════════════


@router.get("/menu")
async def list_menu(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = Query(None),
    available_only: bool = Query(False, alias="available"),
):
    """Lista ítems del menú."""
    return await MenuService.list_menu_items(db, tenant_id, category, available_only)


@router.post("/menu")
async def create_menu_item(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """Crea un ítem del menú."""
    return await MenuService.create_menu_item(db, tenant_id, body)


@router.patch("/menu/{item_id}")
async def update_menu_item(
    item_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """Actualiza un ítem del menú."""
    return await MenuService.update_menu_item(db, item_id, tenant_id, body)


# ═══════════════════════════════════════════════════════════════
# WEBHOOKS / WEBSOCKET (HU-F0-006)
# ═══════════════════════════════════════════════════════════════


@router.websocket("/ws/kitchen/{tenant_id}")
async def kitchen_websocket(ws: WebSocket, tenant_id: int):
    """WebSocket para pantalla de cocina."""
    await ws_manager.connect_kitchen(tenant_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            # Los mensajes entrantes pueden incluir heartbeats o requests de sync
            if data == "ping":
                await ws.send_text('{"event": "pong"}')
    except WebSocketDisconnect:
        ws_manager.disconnect_kitchen(tenant_id, ws)
    except Exception:
        ws_manager.disconnect_kitchen(tenant_id, ws)


@router.websocket("/ws/waiter/{tenant_id}")
async def waiter_websocket(ws: WebSocket, tenant_id: int):
    """WebSocket para notificaciones a meseros."""
    await ws_manager.connect_waiter(tenant_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text('{"event": "pong"}')
    except WebSocketDisconnect:
        ws_manager.disconnect_waiter(tenant_id, ws)
    except Exception:
        ws_manager.disconnect_waiter(tenant_id, ws)
