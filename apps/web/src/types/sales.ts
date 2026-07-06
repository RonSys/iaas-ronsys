/**
 * Sales types — POS sessions, sales, items, payments.
 *
 * @module types/sales
 */

import type { BusinessType } from "./company";

// ─── POS Session ─────────────────────────────────────────

export type PosSessionStatus = "open" | "closed";

export interface PosSession {
  id: number;
  company_id: number;
  user_id: number;
  opened_at: string;
  closed_at: string | null;
  opening_cash: number;
  closing_cash: number | null;
  expected_cash: number | null;
  difference: number | null;
  status: PosSessionStatus;
  notes: string | null;
  total_sales?: number;
  cash_sales?: number;
  card_sales?: number;
  yape_sales?: number;
  plin_sales?: number;
  transfer_sales?: number;
  sale_count?: number;
}

export interface PosSessionOpenRequest {
  opening_cash: number;
}

export interface PosSessionCloseRequest {
  closing_cash: number;
  notes?: string;
}

export interface PosSessionCloseResponse {
  session: PosSession;
  total_sales: number;
  cash_expected: number;
  difference: number;
}

// ─── Sale ────────────────────────────────────────────────

export type PaymentMethod = "cash" | "card" | "yape" | "plin" | "transfer";
export type OrderType = "dine_in" | "takeout" | "delivery";
export type InvoiceType = "boleta" | "factura";

export interface SaleItem {
  id?: number;
  product_id: string | null;
  /** Numeric product ID for serial operations */
  product_numeric_id?: number;
  item_name: string;
  item_type: "product" | "service" | "combo";
  quantity: number;
  unit_of_measure: string;
  unit_price: number;
  discount_pct: number;
  discount_amount: number;
  tax_pct: number;
  tax_amount: number;
  total: number;
  kitchen_notes?: string;
  kardex_movement_id?: number;
  /** Seriales seleccionados para este item (DT-F0-009) */
  serials?: string[];
  /** Precio retail original (para restaurar al bajar cantidad) */
  retail_price?: number;
  /** Precio mayorista (si aplica) */
  wholesale_price?: number;
  /** Cantidad mínima para precio mayorista */
  wholesale_min_qty?: number;
}

export interface SalePayment {
  id?: number;
  payment_method: PaymentMethod;
  amount: number;
  reference: string | null;
}

export interface RestaurantSaleData {
  table_number: number;
  guests: number;
  order_type: OrderType;
  waiter_name: string;
  tip_amount: number;
  tip_pct: number;
  kitchen_notes?: string;
}

export interface HardwareSaleData {
  invoice_type: InvoiceType;
  customer_doc: string;
  delivery_address?: string;
  requires_install: boolean;
  warranty_months: number;
}

export interface SaleCreateRequest {
  customer_name?: string;
  customer_doc?: string;
  discount_total: number;
  items: SaleItem[];
  payments: SalePayment[];
  restaurant_data?: RestaurantSaleData;
  hardware_data?: HardwareSaleData;
}

export interface Sale {
  id: number;
  company_id: number;
  session_id: number;
  user_id: number;
  sale_number: string;
  sale_date: string;
  sale_time: string;
  customer_name: string | null;
  customer_doc: string | null;
  subtotal: number;
  discount_total: number;
  tax_total: number;
  tip_amount: number;
  total: number;
  business_type: BusinessType;
  is_voided: boolean;
  void_reason: string | null;
  journal_entry_id: number | null;
  cashier_name?: string;
  payment_methods?: string[];
}

export interface SaleDetail extends Sale {
  items: SaleItem[];
  payments: SalePayment[];
  restaurant_data: RestaurantSaleData | null;
  hardware_data: HardwareSaleData | null;
}

export interface SaleListResponse {
  sales: Sale[];
  total: number;
  page: number;
  limit: number;
}

export interface SaleFilters {
  from?: string;
  to?: string;
  business_type?: BusinessType;
  session_id?: number;
  is_voided?: boolean;
  payment_method?: string;
  page?: number;
  limit?: number;
}

export interface TicketResponse {
  sale: SaleDetail;
  ticket_text: string;
  format: "json" | "text";
}

export interface VoidSaleRequest {
  reason: string;
}

export interface PaymentMethodsResponse {
  methods: PaymentMethod[];
}
