# 📊 Casos de Uso de Éxito — Kárdex Funcional para Ferretería (HU-F0-009-08)

**Versión:** v0.5-ferreteria-kardex
**Para probar por:** Cliente ferretero
**URL:** https://ronsyserp.com/inventario/kardex

---

## 🎯 Caso 1 — Ver productos ferreteros en el Kárdex

Cubre: Escenario 1 de HU-F0-009-08

### Pasos

- [ ] 1. Inicia sesión con `ferretero@elsegoviano.pe`
- [ ] 2. Ve a **Inventario → Kárdex**
- [ ] 3. Deberías ver tarjetas con los productos que creaste en **Inventario → Productos**
- [ ] 4. Cada tarjeta muestra:
      - **Nombre** del producto (ej: "Taladro Bosch GSB 13")
      - **Stock** actual (cantidad disponible)
      - **C.U. Prom.** (costo promedio por unidad)
      - **Valor Total** (stock × costo promedio)
- [ ] 5. Verifica que aparezcan al menos:
      - Taladro Bosch GSB 13 (stock: 3 si los seriales no se vendieron aún)
      - Cemento Sol 42.5kg (si lo creaste)
      - Arena Fina x m³ (stock debería ser 50 o 45 si ya vendiste)

### Esperado
✅ Los productos de ferretería aparecen en el grid del Kárdex, con stock actualizado en tiempo real.

---

## 🎯 Caso 2 — Ver movimientos de un producto ferretero

Cubre: Escenario 2 de HU-F0-009-08

Requiere: Haber realizado al menos una venta desde **Ventas → Nueva Venta** de un producto sin serial (ej: "Arena Fina x m³", vendiste 5 unidades de 50).

### Pasos

- [ ] 1. En **Inventario → Kárdex**, haz clic en la tarjeta de **"Arena Fina x m³"**
- [ ] 2. Se despliega la tabla de movimientos debajo
- [ ] 3. Deberías ver una fila como esta:

| Fecha | Concepto | Tipo | Cantidad | C.U. | Total | Saldo Cant. | Saldo C.U. | Saldo Total |
|-------|----------|:----:|:--------:|:----:|:-----:|:-----------:|:----------:|:-----------:|
| 20/05/2026 | Venta #VEN-2026-00002 | salida | 5 | S/ | S/ | 45 | S/ | S/ |

- [ ] 4. Si anulaste la venta, debería aparecer un segundo movimiento (entrada de devolución):

| Fecha | Concepto | Tipo | Cantidad |
|-------|----------|:----:|:--------:|
| 20/05/2026 | Anulación venta #VEN-2026-00002 | entrada | 5 |

- [ ] 5. El **Saldo Cant.** final debe coincidir con el stock actual del producto

### Esperado
✅ Cada clic en un producto muestra el historial completo de movimientos (ventas, anulaciones, etc.).

---

## 🎯 Caso 3 — Producto ferretero con seriales

Cubre: Escenarios 1 y 2 para productos con `has_serial=true`

Requiere: Haber creado "Taladro Bosch GSB 13" con 3 seriales (BOSCH-001/002/003).

### Pasos

- [ ] 1. En **Inventario → Kárdex**, busca la tarjeta **"Taladro Bosch GSB 13"**
- [ ] 2. Verifica que muestre stock = **3** (si no se vendió ninguno)
- [ ] 3. Haz clic en la tarjeta → debería mostrar movimientos si se realizaron ventas
- [ ] 4. Si vendiste un taladro (BOSCH-001), deberías ver un movimiento de salida

### Esperado
✅ Los productos con seriales también aparecen en el Kárdex con su stock actual.

---

## 🎯 Caso 4 — Producto no encontrado (error controlado)

Cubre: Escenario 4 de HU-F0-009-08

### Pasos

- [ ] 1. Abre la consola del navegador (F12 → Console)
- [ ] 2. Ejecuta:
      ```js
      await fetch('/api/accounting/kardex/XYZ-999').then(r => r.json())
      ```
- [ ] 3. La respuesta debe ser:
      ```json
      {"detail": "Producto XYZ-999 no encontrado"}
      ```
- [ ] 4. Verifica el código HTTP en la pestaña Network: debe ser **404**

### Esperado
✅ Códigos de producto inexistentes devuelven 404 sin romper la página.

---

## 🎯 Caso 5 — Regresión: Restaurant sigue funcionando

Cubre: Escenario 3 de HU-F0-009-08

Requiere: Tener otro tenant de tipo restaurant con productos registrados en el viejo sistema.

Para probar con el tenant de restaurante:

### Pasos

- [ ] 1. Inicia sesión con usuario de restaurante (ej: `admin@elsegoviano.pe`)
- [ ] 2. Ve a **Inventario → Kárdex**
- [ ] 3. Deberías ver los productos registrados en el sistema contable (simulador)
- [ ] 4. La página debe funcionar exactamente como antes

### Esperado
✅ El comportamiento anterior para restaurant no se rompió.

---

## ✅ Checklist final para el cliente

- [ ] **Caso 1:** Productos ferreteros visibles en el Kárdex con stock actual
- [ ] **Caso 2:** Movimientos de venta/anulación visibles al hacer clic en un producto
- [ ] **Caso 3:** Productos con seriales también aparecen en el Kárdex
- [ ] **Caso 4:** Producto inexistente → error 404 controlado (no crashea)
- [ ] **Caso 5:** Restaurant sigue funcionando sin cambios (regresión)

---

*Documento generado por Jarvis — 2026-05-20*
*Basado en: `docs/backlog/gherkin-f0-009-ferreteria.md` · HU-F0-009-08*
