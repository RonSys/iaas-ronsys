/**
 * Cashflow types — Flujo de Caja (proyectado, real, comparativa).
 *
 * @module types/cashflow
 */

export interface CashflowLine {
  month: number;
  year: number;
  concept: string;
  category: "income" | "expense";
  projected: number;
  actual: number;
  difference: number;
}

export interface CashflowAlert {
  severity: "green" | "yellow" | "red";
  message: string;
}

export interface CashflowResponse {
  company_id: number;
  from_date: string;
  to_date: string;
  view: "projected" | "actual" | "comparison";
  lines: CashflowLine[];
  opening_balance: number;
  net_cashflow: number;
  closing_balance: number;
  alerts: CashflowAlert[];
}

export interface CashflowQueryParams {
  view?: "projected" | "actual" | "comparison";
  from?: string; // YYYY-MM
  to?: string; // YYYY-MM
  year?: number;
}
