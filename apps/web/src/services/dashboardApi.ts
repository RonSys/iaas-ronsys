/**
 * Dashboard API — Panel del Dueño (Spec 04, V1).
 *
 * Endpoint autenticado GET /api/v1/dashboard/owner (solo lectura).
 *
 * @module services/dashboardApi
 */
import { authFetch } from "./authFetch";
import type { OwnerDashboardParams, OwnerDashboardResponse } from "@/types";

/**
 * Obtiene el resumen ejecutivo del panel del dueño.
 * @param params Rango de fechas opcional (YYYY-MM-DD)
 */
export async function getOwnerDashboard(
  params: OwnerDashboardParams = {},
): Promise<OwnerDashboardResponse> {
  const qs = new URLSearchParams();
  if (params.date_from) qs.set("date_from", params.date_from);
  if (params.date_to) qs.set("date_to", params.date_to);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  const res = await authFetch(`/api/v1/dashboard/owner${suffix}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al cargar el panel del dueño");
  }
  return res.json();
}
