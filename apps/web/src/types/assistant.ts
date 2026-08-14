/**
 * Tipos del Asistente IA — "Pregúntale al Sistema" (Spec 06, F5).
 *
 * Contratos (docs/specs/06-asistente-ia/08-spec-preguntale-al-sistema-v0.1.md §3.3.1):
 *  - POST /api/v1/assistant/ask      → AskResponse
 *  - GET  /api/v1/assistant/catalog  → CatalogItem[]
 */

/** Consulta del catálogo elegida por el motor para responder (null = fallback "no entendí"). */
export interface CatalogQueryUsed {
  id: number;
  name: string;
  skill: string;
}

/** Respuesta de POST /api/v1/assistant/ask. */
export interface AskResponse {
  /** Respuesta en español, lista para el dueño. */
  answer: string;
  /** Datos reales de la consulta ejecutada (dict o list — shape variable según skill). */
  data: unknown;
  catalog_query_used: CatalogQueryUsed | null;
  /** Parámetros finales usados por el motor (fechas ISO, límites, canal…). */
  params: Record<string, unknown> | null;
  /** Sugerencias del catálogo (fallback R5 o respuesta normal). */
  suggestions?: string[];
}

/** Parámetro declarado en `params_schema` de una consulta del catálogo. */
export interface CatalogParamSchema {
  name: string;
  type: string;
  required: boolean;
  description_es: string;
  allowed_values?: Array<string | number>;
}

/** Ítem del catálogo de consultas seguras (GET /api/v1/assistant/catalog). */
export interface CatalogItem {
  id: number;
  skill: string;
  name: string;
  /** Descripción natural en español — se muestra al dueño como sugerencia. */
  description_es: string;
  params_schema: CatalogParamSchema[];
}

/** Mensaje del historial de la sesión del chat (solo memoria, no persiste). */
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  /** Datos estructurados de la respuesta (solo mensajes del asistente). */
  data?: unknown;
}
