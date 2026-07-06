// ─── Configuración / Branding ─────────────────────────────

export interface ColorPalette {
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  surface: string;
  text_primary: string;
  text_secondary: string;
  success: string;
  warning: string;
  error: string;
}

export interface CompanySettings {
  palette: ColorPalette;
  logo_url: string | null;
  favicon_url: string | null;
  date_format: string;
  currency: string;
  timezone: string;
}
