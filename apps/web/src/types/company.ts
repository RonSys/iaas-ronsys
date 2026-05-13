/**
 * Company settings types — feature flags + tax config.
 *
 * @module types/company
 */

export interface CompanyFeatures {
  tables_enabled: boolean;
  tips_enabled: boolean;
  invoice_required: boolean;
  warranty_tracking: boolean;
  recipe_explosion: boolean;
  delivery_enabled: boolean;
  multi_waiter: boolean;
}

export interface CompanyTaxConfig {
  igv_included_in_price: boolean;
  igv_rate: number;
  icb_perception_pct: number;
}

export interface CompanySettingsResponse {
  company_id: number;
  business_type: "restaurant" | "hardware" | "retail" | "service";
  business_name: string;
  features: CompanyFeatures;
  tax_config: CompanyTaxConfig;
  palette: import("./settings").ColorPalette;
  logo_url: string | null;
  favicon_url: string | null;
  date_format: string;
  currency: string;
  timezone: string;
}

export type BusinessType = "restaurant" | "hardware" | "retail" | "service";
