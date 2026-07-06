/**
 * Inventory types — Products, Categories, Serials.
 *
 * DT-F0-009: Módulo Ferretería
 *
 * @module types/inventory
 */

// ─── Categorías ──────────────────────────────────────────

export interface ProductCategory {
  id: number;
  name: string;
  description?: string | null;
  parent_id?: number | null;
  active?: boolean;
  sort_order?: number;
  product_count?: number;
}

/** Árbol jerárquico de categorías */
export interface CategoryTreeNode extends ProductCategory {
  children: CategoryTreeNode[];
}

export interface CategoryCreateRequest {
  name: string;
  description?: string;
  parent_id?: number | null;
  sort_order?: number;
}

export interface CategoryUpdateRequest {
  name?: string;
  description?: string;
  parent_id?: number | null;
  sort_order?: number;
  active?: boolean;
}

// ─── Productos ──────────────────────────────────────────

export type ProductUnit = "unidad" | "kg" | "g" | "L" | "mL" | "m" | "cm" | "m²" | "m³" | "caja" | "paquete" | "docena" | "juego" | "par" | "rollo" | "plancha" | "bolsa" | "galón" | "barril" | "lata";

export interface ProductResponse {
  id: number;
  code: string;
  name: string;
  description?: string | null;
  category_id?: number | null;
  category_name?: string | null;
  unit: string;
  retail_price: number;
  wholesale_price?: number | null;
  wholesale_min_qty?: number | null;
  barcode?: string | null;
  has_serial: boolean;
  warranty_months: number;
  manufacturer?: string | null;
  current_stock: number;
  average_cost: number;
  serial_available_count?: number;
  serial_total_count?: number;
  active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ProductCreateRequest {
  code?: string | null;
  name: string;
  description?: string;
  category_id?: number | null;
  unit_of_measure?: string;
  retail_price: number;
  wholesale_price?: number | null;
  wholesale_min_qty?: number | null;
  barcode?: string | null;
  has_serial?: boolean;
  warranty_months?: number;
  manufacturer?: string | null;
  current_stock?: number;
}

export interface ProductUpdateRequest {
  name?: string;
  description?: string;
  category_id?: number | null;
  unit_of_measure?: string;
  retail_price?: number;
  wholesale_price?: number | null;
  wholesale_min_qty?: number | null;
  barcode?: string | null;
  has_serial?: boolean;
  warranty_months?: number;
  manufacturer?: string | null;
  active?: boolean;
}

export interface ProductListParams {
  search?: string;
  category_id?: number;
  active?: boolean;
  sort_by?: string;
  order?: "asc" | "desc";
  page?: number;
  limit?: number;
}

export interface ProductListResponse {
  products: ProductResponse[];
  total: number;
  page: number;
  limit: number;
}

// ─── Seriales ────────────────────────────────────────────

export type SerialStatus = "available" | "reserved" | "sold" | "voided" | "returned" | "warranty";

export interface ProductSerial {
  id: number;
  product_id: number;
  product_name?: string;
  serial_number: string;
  status: SerialStatus;
  purchase_date: string;
  cost_price: number;
  warranty_expiry?: string | null;
  sale_id?: number | null;
  sale_item_id?: number | null;
  notes?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface SerialCreateRequest {
  serial_number: string;
  purchase_date?: string;
  cost_price?: number;
  notes?: string;
}

export interface SerialBatchRequest {
  serials: SerialCreateRequest[];
}

export interface SerialListParams {
  status?: SerialStatus;
  search?: string;
}

// ─── Trazabilidad ────────────────────────────────────────

export type TraceabilityEventType = "registered" | "sold" | "voided" | "returned" | "warranty_claimed";

export interface TraceabilityEvent {
  event_type: TraceabilityEventType;
  timestamp: string;
  description: string;
  reference_id?: string | null;
  user_name?: string | null;
  sale_number?: string | null;
  customer_name?: string | null;
}

export interface SerialTraceability {
  serial_number: string;
  product_name: string;
  manufacturer?: string | null;
  warranty_months: number;
  warranty_expiry?: string | null;
  is_warranty_active?: boolean;
  current_status: SerialStatus;
  events: TraceabilityEvent[];
}

// ─── Alertas de garantía ─────────────────────────────────

export interface WarrantyAlert {
  serial_number: string;
  product_name: string;
  warranty_expiry: string;
  days_remaining: number;
  customer_name?: string | null;
  sale_number?: string | null;
}
