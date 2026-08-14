/**
 * Assistant API — "Pregúntale al Sistema" (Spec 06, F5, frontend).
 *
 * Endpoints autenticados (JWT staff + X-Tenant-ID, patrón de authFetch
 * igual que dashboardApi.ts):
 *  - POST /api/v1/assistant/ask      { question } → AskResponse
 *  - GET  /api/v1/assistant/catalog               → CatalogItem[]
 *
 * Errores manejados de forma amigable:
 *  - 429 (rate limit por tenant, R6) → mensaje claro de "espera un momento"
 *  - 401/403 (sin auth / rol)        → mensaje del backend (o genérico)
 *
 * @module services/assistantApi
 */
import { authFetch } from "./authFetch";
import type { AskResponse, CatalogItem } from "@/types";

/** Mensaje amigable para el rate limit 429 (R6: 10 req/min por tenant). */
export const ASSISTANT_RATE_LIMIT_MESSAGE =
  "Demasiadas consultas en poco tiempo. Espera un momento y vuelve a intentar.";

/**
 * Envía una pregunta en lenguaje natural al asistente.
 * @param question Pregunta del dueño (ej. "¿cuál es el producto más vendido hoy por delivery?")
 * @throws Error con mensaje amigable (429 → ASSISTANT_RATE_LIMIT_MESSAGE)
 */
export async function askAssistant(question: string): Promise<AskResponse> {
  const res = await authFetch("/api/v1/assistant/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (res.status === 429) {
    throw new Error(ASSISTANT_RATE_LIMIT_MESSAGE);
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      err.detail ??
        (res.status === 401 || res.status === 403
          ? "No autorizado. Inicia sesión para usar el asistente."
          : "Error al consultar al sistema. Intenta de nuevo."),
    );
  }
  return res.json();
}

/**
 * Obtiene el catálogo de consultas seguras disponibles para el rol.
 * Se usa para mostrar chips de sugerencias al dueño.
 */
export async function getAssistantCatalog(): Promise<CatalogItem[]> {
  const res = await authFetch("/api/v1/assistant/catalog");
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      err.detail ?? "Error al cargar el catálogo de consultas",
    );
  }
  return res.json();
}
