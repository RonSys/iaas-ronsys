/**
 * Tipos del Panel del Dueño (Spec 04 — dashboard ejecutivo).
 *
 * Contrato GET /api/v1/dashboard/owner?date_from=&date_to=
 * Ver docs/specs/04-panel-indicadores/spec-panel-dueño.md §3.1
 */

export interface OwnerKpis {
  sales_total: number;
  orders_count: number;
  avg_ticket: number;
  orders_delivery: number;
  orders_dine_in: number;
  orders_takeout: number;
  delivery_pct: number;
  kitchen_open: number;
  delivery_in_route: number;
}

export interface HourlySale {
  hour: number;
  dine_in: number;
  delivery: number;
}

export interface WeekdaySale {
  weekday: number; // 1=Mon..7=Sun
  total: number;
}

export interface ChannelsData {
  dine_in: number;
  takeout: number;
  delivery: number;
}

export interface TopPlato {
  name: string;
  qty: number;
  total: number;
}

export interface PaymentsData {
  yape: number;
  plin: number;
  cash: number;
  card: number;
  transfer: number;
}

export interface DeliveryFunnel {
  received: number;
  preparing: number;
  ready: number;
  out_for_delivery: number;
  delivered: number;
  cancelled: number;
}

export interface ZoneOrders {
  zone: string;
  orders: number;
}

export interface DeliveryMetrics {
  orders_by_zone: ZoneOrders[];
  funnel: DeliveryFunnel;
  avg_delivery_min: number | null;
  gmv: number;
  fee_total: number;
}

export interface CampaignMetric {
  campaign_id: number;
  name: string;
  channel: string;
  spend: number;
  orders: number;
  gmv: number;
  aov: number;
  roas: number;
}

export interface OwnerDashboardResponse {
  kpis: OwnerKpis;
  sales_by_hour: HourlySale[];
  sales_by_weekday: WeekdaySale[];
  channels: ChannelsData;
  top_platos: TopPlato[];
  payments: PaymentsData;
  delivery: DeliveryMetrics;
  campaigns: CampaignMetric[];
}

export interface OwnerDashboardParams {
  date_from?: string;
  date_to?: string;
}
