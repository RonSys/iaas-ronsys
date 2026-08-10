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

// ─── V2 (Spec 04 §3.1-V2: CA10-CA14) ──────────────────────────

/** CA10 — Celda de heatmap: ventas (S/) en una hora × día de semana. */
export interface HeatmapRow {
  hour: number; // 0-23
  weekday: number; // 1=Lun..7=Dom
  total: number; // S/ (0 si no hubo ventas)
}

export interface HeatmapChannel {
  rows: HeatmapRow[]; // hasta 24×7 = 168 rows, sin huecos
}

/** CA10 — Heatmap hora×día por canal (takeout ya sumado a dine_in por el backend). */
export interface HeatmapData {
  dine_in: HeatmapChannel;
  delivery: HeatmapChannel;
}

/** CA11 — Margen de un canal (costeo vía recetas, decisión R2). */
export interface MarginByChannel {
  channel: "dine_in" | "takeout" | "delivery";
  revenue: number;
  cost: number;
  margin_pct: number; // 0.0 si revenue == 0
}

export interface MarginsData {
  by_channel: MarginByChannel[];
  costable_note: string;
}

/** CA12 — Resumen de un período (actual o previo). */
export interface ComparisonPeriod {
  sales_total: number;
  orders_count: number;
  avg_ticket: number;
  delivery_pct: number;
}

/** CA12 — Deltas relativos (*_pct null si previous == 0; delivery_pct_delta en puntos). */
export interface ComparisonDeltas {
  sales_total_pct: number | null;
  orders_count_pct: number | null;
  avg_ticket_pct: number | null;
  delivery_pct_delta: number | null;
}

export interface ComparisonData {
  current: ComparisonPeriod;
  previous: ComparisonPeriod;
  deltas: ComparisonDeltas;
}

/** CA14 — Alerta de desviación vs promedio de los 7 días previos. */
export interface AlertItem {
  severity: "red" | "yellow";
  metric: string;
  message: string;
}

export interface OwnerDashboardResponse {
  period: { date_from: string; date_to: string };
  kpis: OwnerKpis;
  sales_by_hour: HourlySale[];
  sales_by_weekday: WeekdaySale[];
  channels: ChannelsData;
  top_platos: TopPlato[];
  payments: PaymentsData;
  delivery: DeliveryMetrics;
  campaigns: CampaignMetric[];
  // V2 (CA10-CA14)
  heatmap: HeatmapData;
  margins: MarginsData;
  comparison: ComparisonData;
  alerts: AlertItem[];
}

export interface OwnerDashboardParams {
  date_from?: string;
  date_to?: string;
}
