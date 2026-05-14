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
  multi_warehouse: boolean;
}

export interface BrandingConfig {
  logo_url: string | null;
  favicon_url: string | null;
  primary_color: string;
  secondary_color: string;
  business_name: string;
}

export interface CompanyTaxConfig {
  igv_included_in_price: boolean;
  igv_rate: number;
  icb_perception_pct: number;
  withholding_tax_rate: number;
}

export interface CompanySettingsResponse {
  company_id: number;
  business_type: "restaurant" | "hardware" | "retail" | "service";
  business_name: string;
  features: CompanyFeatures;
  tax_config: CompanyTaxConfig;
  branding: BrandingConfig;
  palette: import("./settings").ColorPalette;
  logo_url: string | null;
  favicon_url: string | null;
  date_format: string;
  currency: string;
  timezone: string;
  investment_vars?: Record<string, unknown> | null;
}

export type BusinessType = "restaurant" | "hardware" | "retail" | "service";
