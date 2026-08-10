/**
 * Dashboard API — Panel del Dueño (Spec 04, V1 + V2).
 *
 * Endpoints autenticados (solo lectura):
 *  - GET /api/v1/dashboard/owner (resumen, §3.1 + §3.1-V2)
 *  - GET /api/v1/dashboard/owner/export?format=csv (CA13 — CSV descargable)
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

/** Resultado de la descarga CSV (CA13): blob + filename del header si existe. */
export interface OwnerDashboardExport {
  blob: Blob;
  filename: string | null;
}

/**
 * Extrae el filename de un header Content-Disposition.
 * Soporta RFC 5987 (`filename*=UTF-8''...`) y el filename plano ASCII.
 */
export function parseContentDispositionFilename(header: string | null): string | null {
  if (!header) return null;
  const star = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (star) {
    try {
      return decodeURIComponent(star[1]);
    } catch {
      // fallthrough al filename plano
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(header);
  return plain ? plain[1] : null;
}

/**
 * CA13 — Descarga el reporte CSV del período seleccionado.
 * @param params Rango de fechas (YYYY-MM-DD); format siempre `csv` (R3)
 * @returns Blob del CSV + filename tomado del header Content-Disposition (si existe)
 */
export async function exportOwnerDashboardCsv(
  params: OwnerDashboardParams = {},
): Promise<OwnerDashboardExport> {
  const qs = new URLSearchParams();
  qs.set("format", "csv");
  if (params.date_from) qs.set("date_from", params.date_from);
  if (params.date_to) qs.set("date_to", params.date_to);
  const res = await authFetch(`/api/v1/dashboard/owner/export?${qs.toString()}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al descargar el reporte");
  }
  const blob = await res.blob();
  return {
    blob,
    filename: parseContentDispositionFilename(res.headers.get("Content-Disposition")),
  };
}
