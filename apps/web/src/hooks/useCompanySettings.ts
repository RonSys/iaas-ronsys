/**
 * useCompanySettings — Hook para configuración de empresa y feature flags.
 *
 * Consume GET /api/admin/company/settings y expone:
 * - features: flags que controlan visibilidad de funcionalidades
 * - taxConfig: configuración tributaria (IGV, ICB, retención)
 * - branding: datos de marca (logo, colores, nombre)
 * - businessType: tipo de negocio (restaurant, hardware, retail, service)
 * - loading / error / refetch: estado de la petición
 *
 * Cachea en estado local — no refetch en cada render.
 *
 * HU-F1-003: UI adaptativa según business_type y feature flags
 *
 * @module hooks/useCompanySettings
 */
import { useState, useEffect, useCallback } from "react";
import { getCompanySettings } from "@/services";
import type {
  CompanySettingsResponse,
  CompanyFeatures,
  CompanyTaxConfig,
  BrandingConfig,
  BusinessType,
} from "@/types";

const DEFAULT_FEATURES: CompanyFeatures = {
  tables_enabled: false,
  tips_enabled: false,
  invoice_required: false,
  warranty_tracking: false,
  recipe_explosion: false,
  delivery_enabled: false,
  multi_waiter: false,
  multi_warehouse: false,
};

const DEFAULT_TAX_CONFIG: CompanyTaxConfig = {
  igv_included_in_price: false,
  igv_rate: 0.18,
  icb_perception_pct: 0,
  withholding_tax_rate: 0,
};

const DEFAULT_BRANDING: BrandingConfig = {
  logo_url: null,
  favicon_url: null,
  primary_color: "#1a365d",
  secondary_color: "#2b6cb0",
  business_name: "",
};

export function useCompanySettings() {
  const [settings, setSettings] = useState<CompanySettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getCompanySettings();
      setSettings(data);
      return data;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error cargando config";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  return {
    settings,
    features: settings?.features ?? DEFAULT_FEATURES,
    taxConfig: settings?.tax_config ?? DEFAULT_TAX_CONFIG,
    branding: settings?.branding ?? DEFAULT_BRANDING,
    businessType: (settings?.business_type ?? "retail") as BusinessType,
    loading,
    error,
    refetch: fetch,
  };
}
