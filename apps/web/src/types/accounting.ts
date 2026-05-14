// ─── Contabilidad ────────────────────────────────────────

export interface InvestmentInput {
  capital: number;
  loan_amount?: number;
  loan_rate_annual?: number;
  loan_term_months?: number;
  equipment_cost?: number;
  furniture_cost?: number;
  computer_cost?: number;
  software_cost?: number;
  guarantee_deposit?: number;
  initial_inventory?: number;
  monthly_sales: number[];
  monthly_cost_pct?: number;
  monthly_rent?: number;
  monthly_utilities?: number;
  monthly_salaries?: number;
  monthly_marketing?: number;
  monthly_admin?: number;
  monthly_maintenance?: number;
  equipment_life_years?: number;
  furniture_life_years?: number;
  computer_life_years?: number;
  software_life_years?: number;
  months?: number;
  start_date?: string;
}

export interface BCSSLine {
  account_code: string;
  account_name: string;
  total_debit: number;
  total_credit: number;
  balance: number;
  balance_nature: "D" | "A";
}

export interface BCSSResponse {
  lines: BCSSLine[];
  total_debits: number;
  total_credits: number;
  is_balanced: boolean;
}

export interface IncomeStatementResponse {
  period: string;
  revenue: number;
  cost_of_sales: number;
  gross_profit: number;
  gross_margin_pct: number;
  operating_expenses: Record<string, number>;
  depreciation: number;
  financial_expenses: number;
  ebitda: number;
  ebit: number;
  operating_margin_pct: number;
  income_before_tax: number;
  income_tax: number;
  net_income: number;
  net_margin_pct: number;
}

export interface BalanceSheetResponse {
  as_of: string;
  current_assets: Record<string, number>;
  non_current_assets: Record<string, number>;
  accumulated_depreciation: number;
  total_assets: number;
  current_liabilities: Record<string, number>;
  non_current_liabilities: Record<string, number>;
  total_liabilities: number;
  capital: number;
  retained_earnings: number;
  current_income: number;
  total_equity: number;
  total_liabilities_and_equity: number;
  is_balanced: boolean;
}

export interface RatioItem {
  name: string;
  value: number;
  target: string;
  traffic_light: "green" | "yellow" | "red";
  formula: string;
}

export interface FinancialReportResponse {
  period_start: string;
  period_end: string;
  total_entries: number;
  bcss: BCSSResponse | null;
  income_statement: IncomeStatementResponse | null;
  balance_sheet: BalanceSheetResponse | null;
  ratios: RatioItem[] | null;
  validations: Record<string, boolean>;
}

// ─── Kárdex ──────────────────────────────────────────────

export interface KardexProduct {
  code: string;
  name: string;
  unit: string;
  current_stock: number;
  average_cost: number;
  total_value: number;
  /** Precio de venta unitario (menorista) */
  unit_price?: number;
  /** Precio de venta al por mayor */
  wholesale_price?: number;
  /** Cantidad mínima para aplicar precio mayorista */
  wholesale_min_qty?: number;
  /** ID de categoría de producto */
  category_id?: number | null;
  /** Nombre de categoría */
  category_name?: string | null;
  /** Período de garantía en meses (ferretería) */
  warranty_period?: number | null;
  /** Código de barras (ferretería) */
  barcode?: string | null;
  /** Fabricante / marca (ferretería) */
  manufacturer?: string | null;
}

export interface KardexRecord {
  product_code: string;
  movement_type: "entrada" | "salida" | "ajuste";
  concept: string;
  quantity: number;
  unit_cost: number;
  total: number;
  balance_quantity: number;
  balance_avg_cost: number;
  balance_total: number;
  date: string;
}

export interface WarehouseCloseResponse {
  inventory_value: number;
  accounting_balance: number;
  difference: number;
  is_balanced: boolean;
  details: Record<string, { name: string; stock: number; unit_cost: number; total: number }>;
  alerts: string[];
}

// ─── Health ──────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}
