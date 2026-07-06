/**
 * Restaurant API — Section, table management, and recipe endpoints.
 *
 * Uses authFetch for consistency with the existing restaurant pages.
 *
 * @module services/restaurantApi
 */
import { authFetch } from "./authFetch";
import type { RestaurantSection, Recipe, RecipeUpdateRequest } from "@/types";

// ─── Sections ────────────────────────────────────────────

export async function getSections(): Promise<RestaurantSection[]> {
  const res = await authFetch("/api/v1/restaurant/sections");
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al cargar secciones");
  }
  const data = await res.json();
  return data.sections ?? data;
}

export async function createSection(
  data: { name: string; description?: string; sort_order?: number },
): Promise<RestaurantSection> {
  const res = await authFetch("/api/v1/restaurant/sections", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al crear sección");
  }
  return res.json();
}

export async function updateSection(
  id: number,
  data: { name?: string; description?: string; sort_order?: number },
): Promise<RestaurantSection> {
  const res = await authFetch(`/api/v1/restaurant/sections/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al actualizar sección");
  }
  return res.json();
}

export async function deleteSection(id: number): Promise<void> {
  const res = await authFetch(`/api/v1/restaurant/sections/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al eliminar sección");
  }
}

// ═══════════════════════════════════════════════════════════
// Recipes / Recetas
// ═══════════════════════════════════════════════════════════

/** Obtener la receta de un ítem del menú (GET /menu/{id}/recipe) */
export async function getRecipe(menuItemId: number): Promise<Recipe | null> {
  const res = await authFetch(`/api/v1/restaurant/menu/${menuItemId}/recipe`);
  if (res.status === 404) return null;
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al cargar receta");
  }
  const data = await res.json();
  return data;
}

/** Guardar/actualizar receta de un ítem del menú (PUT /menu/{id}/recipe) */
export async function updateRecipe(
  menuItemId: number,
  data: RecipeUpdateRequest,
): Promise<Recipe> {
  const res = await authFetch(`/api/v1/restaurant/menu/${menuItemId}/recipe`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al guardar receta");
  }
  return res.json();
}
