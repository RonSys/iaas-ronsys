/**
 * Inventory API — Endpoints para el módulo Ferretería.
 *
 * DT-F0-009: Módulo Ferretería
 *
 * Usa authFetch para autenticación automática.
 *
 * @module services/inventoryApi
 */

import { authFetch } from "./authFetch";
import type {
  ProductCategory,
  CategoryTreeNode,
  CategoryCreateRequest,
  CategoryUpdateRequest,
  ProductResponse,
  ProductCreateRequest,
  ProductUpdateRequest,
  ProductListParams,
  ProductListResponse,
  ProductSerial,
  SerialCreateRequest,
  SerialBatchRequest,
  SerialListParams,
  SerialTraceability,
  WarrantyAlert,
} from "@/types";

const BASE = "/api/v1/inventory";

// ─── Helpers ─────────────────────────────────────────────

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = "";
    try {
      const data = await res.json();
      detail = data.detail ?? "";
    } catch {
      detail = res.statusText;
    }
    throw new Error(detail || `Error ${res.status}`);
  }
  const data = await res.json();
  // Algunos endpoints devuelven { categories: [...] }, otros el array directo
  if (data && typeof data === "object") {
    if (data.categories) return data.categories as T;
    if (data.products) return data.products as T;
    if (data.serials) return data.serials as T;
  }
  return data as T;
}

// ═══════════════════════════════════════════════════════════
// Categorías
// ═══════════════════════════════════════════════════════════

export async function getCategories(): Promise<ProductCategory[]> {
  const res = await authFetch(`${BASE}/categories`);
  const data = await res.json();
  return data.categories ?? data;
}

export async function getCategoryTree(): Promise<CategoryTreeNode[]> {
  const res = await authFetch(`${BASE}/categories?tree=true`);
  const data = await res.json();
  return data.categories ?? data;
}

export async function createCategory(
  data: CategoryCreateRequest,
): Promise<ProductCategory> {
  const res = await authFetch(`${BASE}/categories`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<ProductCategory>(res);
}

export async function updateCategory(
  id: number,
  data: CategoryUpdateRequest,
): Promise<ProductCategory> {
  const res = await authFetch(`${BASE}/categories/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<ProductCategory>(res);
}

export async function deleteCategory(id: number): Promise<void> {
  const res = await authFetch(`${BASE}/categories/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? "Error al eliminar categoría");
  }
}

// ═══════════════════════════════════════════════════════════
// Productos
// ═══════════════════════════════════════════════════════════

export async function getProducts(
  params: ProductListParams = {},
): Promise<ProductListResponse> {
  const sp = new URLSearchParams();
  if (params.search) sp.set("search", params.search);
  if (params.category_id) sp.set("category_id", String(params.category_id));
  if (params.active !== undefined) sp.set("active", String(params.active));
  if (params.sort_by) sp.set("sort_by", params.sort_by);
  if (params.order) sp.set("order", params.order);
  if (params.page) sp.set("page", String(params.page));
  if (params.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  const res = await authFetch(`${BASE}/products${qs ? `?${qs}` : ""}`);
  const data = await res.json();
  return data;
}

export async function getProduct(id: number): Promise<ProductResponse> {
  const res = await authFetch(`${BASE}/products/${id}`);
  return handleResponse<ProductResponse>(res);
}

/** Búsqueda por código de barras */
export async function searchProductByBarcode(
  barcode: string,
): Promise<ProductResponse | null> {
  const res = await authFetch(
    `${BASE}/products?barcode=${encodeURIComponent(barcode)}`,
  );
  const data = await res.json();
  if (data.products && data.products.length > 0) return data.products[0];
  return null;
}

export async function createProduct(
  data: ProductCreateRequest,
): Promise<ProductResponse> {
  const res = await authFetch(`${BASE}/products`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<ProductResponse>(res);
}

export async function updateProduct(
  id: number,
  data: ProductUpdateRequest,
): Promise<ProductResponse> {
  const res = await authFetch(`${BASE}/products/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<ProductResponse>(res);
}

export async function deleteProduct(id: number): Promise<ProductResponse & { warnings?: string[] }> {
  const res = await authFetch(`${BASE}/products/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? "Error al eliminar producto");
  }
  return res.json();
}

// ═══════════════════════════════════════════════════════════
// Seriales
// ═══════════════════════════════════════════════════════════

export async function getSerials(
  productId: number,
  params: SerialListParams = {},
): Promise<ProductSerial[]> {
  const sp = new URLSearchParams();
  if (params.status) sp.set("status", params.status);
  if (params.search) sp.set("search", params.search);
  const qs = sp.toString();
  const res = await authFetch(
    `${BASE}/products/${productId}/serials${qs ? `?${qs}` : ""}`,
  );
  const data = await res.json();
  return data.serials ?? data;
}

export async function createSerial(
  productId: number,
  data: SerialCreateRequest,
): Promise<ProductSerial> {
  const res = await authFetch(`${BASE}/products/${productId}/serials`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<ProductSerial>(res);
}

export async function createSerialBatch(
  productId: number,
  data: SerialBatchRequest,
): Promise<ProductSerial[]> {
  const res = await authFetch(`${BASE}/products/${productId}/serials/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  const json = await res.json();
  return json.serials ?? json;
}

/** Obtener seriales disponibles para un producto (usado en POS) */
export async function getAvailableSerials(
  productId: number,
): Promise<ProductSerial[]> {
  return getSerials(productId, { status: "available" });
}

// ═══════════════════════════════════════════════════════════
// Trazabilidad
// ═══════════════════════════════════════════════════════════

export async function getSerialTraceability(
  serialNumber: string,
): Promise<SerialTraceability> {
  const res = await authFetch(
    `${BASE}/serials/${encodeURIComponent(serialNumber)}/traceability`,
  );
  return handleResponse<SerialTraceability>(res);
}

// ═══════════════════════════════════════════════════════════
// Alertas de garantía
// ═══════════════════════════════════════════════════════════

export async function getWarrantyAlerts(
  daysThreshold: number = 30,
): Promise<WarrantyAlert[]> {
  const res = await authFetch(
    `${BASE}/serials/warranty-alerts?days=${daysThreshold}`,
  );
  const data = await res.json();
  return data.alerts ?? data;
}
