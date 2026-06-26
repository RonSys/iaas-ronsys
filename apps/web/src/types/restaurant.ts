/**
 * Restaurant types — Sections, tables, menu items.
 *
 * @module types/restaurant
 */

export interface RestaurantSection {
  id: number;
  name: string;
  description?: string;
  sort_order: number;
  table_count: number;
  created_at: string;
}

// ─── Recipes / Recetas ─────────────────────────────────────

export interface RecipeIngredient {
  id?: number;
  product_id: number;
  product_name?: string;
  quantity: number;
  unit_of_measure: string;
  average_cost?: number;
  sort_order?: number;
}

export interface Recipe {
  id?: number;
  menu_item_id: number;
  ingredients: RecipeIngredient[];
  total_cost?: number;
  created_at?: string;
  updated_at?: string;
}

// ─── Investment / Inversión ───────────────────────────────

export interface InvestmentItem {
  id: number;
  tenant_id: number;
  name: string;
  category: InvestmentCategory;
  estimated_cost: number;
  actual_cost: number | null;
  receipt_code: string | null;
  status: "pending" | "acquired";
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export type InvestmentCategory =
  | "infraestructura"
  | "mobiliario"
  | "equipamiento_cocina"
  | "instalaciones"
  | "vestimenta"
  | "dyl"
  | "tecnologia"
  | "marketing"
  | "gastos_operativos";

export interface InvestmentSummary {
  total_estimated: number;
  total_actual: number;
  difference: number;
  acquired_count: number;
  pending_count: number;
  total_count: number;
}

export interface InvestmentFormData {
  name: string;
  category: InvestmentCategory;
  estimated_cost: number;
  actual_cost: number | null;
  receipt_code: string;
  status: "pending" | "acquired";
  notes: string | null;
}

export interface RecipeUpdateRequest {
  ingredients: {
    product_id: number;
    quantity: number;
    unit_of_measure: string;
    sort_order?: number;
  }[];
}
