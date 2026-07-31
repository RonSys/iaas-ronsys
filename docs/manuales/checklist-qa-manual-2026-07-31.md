# ✅ Checklist QA Manual — Funcionalidad de Recetas y Costos (2026-07-31)

- **Proyecto**: IaaS-RonSys · tenant 1 (Admin Tenant, restaurant)
- **Specs**: [`01-spec-recetas-productos-v0.2.md`](../specs/01-spec-recetas-productos-v0.2.md) · [`02-spec-costos-variables-v0.1.md`](../specs/02-spec-costos-variables-v0.1.md)
- **Acceso**: https://www.ronsyserp.com · admin@elsegoviano.pe (recarga con Ctrl+Shift+R)

> Marca ✅/❌ cada paso. Resultado esperado incluido. Cualquier ❌ repórtalo con detalle.

---

## 1. Login y navegación

- [ ] Login con admin@elsegoviano.pe → Dashboard (Proyecto de Inversión)
- [ ] En el sidebar, el grupo **Proyecto de Inversión** muestra: Dashboard, Setup, Simulador, Reportes Financieros y **🏗️ Puesta en Marcha** (antes "Inversión" estaba en Restaurante)
- [ ] El grupo **Restaurante** ya NO contiene el item Inversión

## 2. Gestión de Recetas (UI)

- [ ] Restaurante → **Menú** → plato **Ceviche Clásico** → botón **📋 Receta** (CA9)
- [ ] El modal muestra 5 ingredientes: Pescado fresco (0.15 kg), Limón (2 und), Cebolla (0.05 kg), Camote (0.10 kg), Choclo (0.05 kg)
- [ ] **Costo estimado** ≈ S/ 4.58 (pescado a S/20.03) y **margen** = 28.00 − costo (CA2)
- [ ] Edita la cantidad de un ingrediente → el costo/margen se recalculan en vivo
- [ ] **Actualizar receta** → aparece el **banner verde "✅ Receta actualizada correctamente"** ~1s y cierra (UX)
- [ ] Si dejas la sesión 15 min y guardas → **no se rompe** (auto-refresh de token, 401 → renovación automática)

## 3. Venta con explosión (POS)

- [ ] Kárdex/Inventario: anota el **stock de Pescado fresco** (debe ser ~19.70 kg)
- [ ] POS: vende **1 Ceviche Clásico** (S/ 28) con pago en efectivo → venta OK (CA3)
- [ ] Kárdex → Pescado fresco: aparece **salida "Consumo por receta"** de 0.15 kg y el stock bajó a ~19.55 kg (CA3)
- [ ] Los demás ingredientes (Limón −2, Cebolla −0.05, Camote −0.10, Choclo −0.05) también decrementaron
- [ ] Contabilidad → asiento de la venta: líneas **50 Costo de Ventas** y **12 Inventarios** por el costo de ingredientes (CA11/D9)
- [ ] Intenta vender **200 ceviches** → la venta se **rechaza (409)** con "Stock insuficiente…" y NO quedan movimientos parciales (CA4)

## 4. Costos variables (Kárdex → + Entrada)

- [ ] Kárdex → selecciona **Pescado fresco** → **+ Entrada** (CA1)
- [ ] El formulario muestra **Stock actual** (19.70) y **Costo promedio actual** (S/20.03) (UX)
- [ ] Ingresa Cantidad 10 y Costo unitario 22 → el **"Nuevo promedio estimado"** muestra ≈ S/20.69 en vivo (UX, misma fórmula del backend)
- [ ] Registrar Entrada → ✅ "Entrada registrada" → stock sube a 29.70 y el promedio se actualiza (persistente en BD)
- [ ] Registra una **Salida** → el promedio NO cambia (solo el stock) (CA2)
- [ ] Inventario → Productos → Editar Pescado → ajusta **Precio Retail** → guarda (CA4, no toca kárdex)

## 5. Búsqueda de productos (POS)

- [ ] POS → buscador de productos → escribe "pescado" → aparecen Ceviche de Pescado y Pescado fresco con precio y stock (T8)

## 6. Multi-tenant (sanity)

- [ ] Con la sesión de tenant 1, el inventario NO muestra productos de otros tenants (aislamiento 403 si se intenta otro X-Tenant-ID) (T7)

---

## Trazabilidad

| Paso | Spec | CA |
|---|---|---|
| §2 Recetas | Spec 01 §3.1/§3.4 | CA2, CA9, CA10 |
| §3 Explosión | Spec 01 §3.3 | CA3, CA4, CA5, CA11 |
| §4 Costos variables | Spec 02 | CA1–CA4 |
| §5 POS search | Spec 02 | T8 |
| §6 Multi-tenant | — | T7 |
