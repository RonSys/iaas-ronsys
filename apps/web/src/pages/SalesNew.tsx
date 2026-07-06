/**
 * SalesNewPage — Página de registro de nueva venta.
 *
 * Usa SaleForm + useCompanySettings para feature flags.
 *
 * HU-F2-009: UI de registro de venta base
 * HU-F2-010: UI de venta especializada por tipo de negocio
 *
 * @module pages/SalesNew
 */
import { useCallback } from "react";
import { authFetch } from "@/services/authFetch";
import { useCompanySettings } from "@/hooks/useCompanySettings";
import { SaleForm } from "@/components/sales/SaleForm";
import { Skeleton } from "@/components/dashboard/KPICard";
import type { SaleCreateRequest } from "@/types";

interface SalesNewPageProps {
  onCreateSale?: (sale: SaleCreateRequest) => Promise<void>;
  submitLoading?: boolean;
  submitError?: string | null;
}

export function SalesNewPage({
  onCreateSale,
  submitLoading = false,
  submitError = null,
}: SalesNewPageProps) {
  const { loading, error, features, taxConfig, businessType } =
    useCompanySettings();

  const handleSubmit = useCallback(
    async (sale: SaleCreateRequest) => {
      if (onCreateSale) {
        await onCreateSale(sale);
      } else {
        // Default: post to API
        const response = await authFetch("/api/sales/sale", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(sale),
        });
        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.detail ?? "Error al crear venta");
        }
      }
    },
    [onCreateSale],
  );

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-brand-text-primary">
            🛒 Nueva Venta
          </h2>
          <p className="text-sm text-brand-text-secondary">
            {businessType === "restaurant"
              ? "Restaurante"
              : businessType === "hardware"
                ? "Ferretería"
                : businessType === "service"
                  ? "Servicio"
                  : "Retail"}
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          Error cargando configuración: {error}
        </div>
      )}

      {!error && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main form - 2/3 width on desktop */}
          <div className="lg:col-span-2 card">
            <SaleForm
              features={features}
              taxConfig={taxConfig}
              businessType={businessType}
              onSubmit={handleSubmit}
              loading={submitLoading}
              error={submitError}
            />
          </div>

          {/* Sidebar - 1/3 width (resumen rápido en desktop) */}
          <div className="hidden lg:block">
            <div className="card sticky top-20">
              <h3 className="font-bold text-brand-text-primary mb-2">
                📋 Resumen Rápido
              </h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-brand-text-secondary">Negocio:</span>
                  <span className="font-medium capitalize">{businessType}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-brand-text-secondary">IGV:</span>
                  <span className="font-medium">
                    {Math.round(taxConfig.igv_rate)}%
                    {taxConfig.igv_included_in_price ? " (incl.)" : ""}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-brand-text-secondary">Mesas:</span>
                  <span>
                    {features.tables_enabled ? "✅" : "❌"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-brand-text-secondary">Propina:</span>
                  <span>
                    {features.tips_enabled ? "✅" : "❌"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-brand-text-secondary">Factura:</span>
                  <span>
                    {features.invoice_required ? "✅" : "❌"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
