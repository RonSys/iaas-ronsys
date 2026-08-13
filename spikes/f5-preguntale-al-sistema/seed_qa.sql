-- Seed data de prueba para spike F5 (tenant 1, solo lectura para las tools)
-- Idempotente: TRUNCATE antes (llamado desde seed_reset.sql)

-- Zonas de delivery
INSERT INTO delivery_zones (tenant_id, name, description, districts, fee, min_order, eta_min, active) VALUES
  (1, 'Montenegro', 'Zona 1 — San Juan de Lurigancho', '["Montenegro","SJL"]'::jsonb, 5.00, 35.00, 45, true),
  (1, 'Canto Grande', 'Zona 2 — Canto Grande', '["Canto Grande"]'::jsonb, 6.00, 40.00, 50, true),
  (1, 'Motupe', 'Zona 3 — Motupe', '["Motupe"]'::jsonb, 7.00, 45.00, 55, true);

-- Productos restaurante
INSERT INTO products (code, name, description, unit_of_measure, current_stock, average_cost, active, tenant_id, retail_price, category_id) VALUES
  ('CEV-CLAS', 'Ceviche Clásico', 'Ceviche de pescado con limón', 'unidad', 10, 8.50, true, 1, 28.00, NULL),
  ('ARROZ-MAR', 'Arroz con Mariscos', 'Arroz con mariscos mixtos', 'unidad', 12, 9.20, true, 1, 32.00, NULL),
  ('INCA-KOLA', 'Inca Kola 500ml', 'Gaseosa Inca Kola 500ml', 'unidad', 50, 2.50, true, 1, 5.00, NULL),
  ('CEV-MIX', 'Ceviche Mixto', 'Ceviche mixto con mariscos', 'unidad', 8, 11.00, true, 1, 36.00, NULL),
  ('LOMO-SALT', 'Lomo Saltado', 'Lomo saltado con arroz y papas', 'unidad', 15, 10.00, true, 1, 30.00, NULL);

-- Usuario admin (hash placeholder — no se usa para login en el spike)
INSERT INTO users (email, hashed_password, full_name, role, tenant_id, is_active, is_verified, failed_login_attempts) VALUES
  ('admin@elsegoviano.pe', 'spike-no-login', 'Admin Principal', 'admin', 1, true, true, 0);

-- Ventas delivery de HOY
INSERT INTO sales (tenant_id, user_id, sale_number, sale_date, sale_time, customer_name, subtotal, discount_total, tax_total, tip_amount, total, business_type, is_voided) VALUES
  (1, 1, 'SPK-1001', CURRENT_DATE, '12:30:00', 'Cliente A', 28.00, 0, 0, 0, 28.00, 'delivery', false),
  (1, 1, 'SPK-1002', CURRENT_DATE, '13:00:00', 'Cliente B', 37.00, 0, 0, 0, 37.00, 'delivery', false),
  (1, 1, 'SPK-1003', CURRENT_DATE, '13:30:00', 'Cliente C', 32.00, 0, 0, 0, 32.00, 'delivery', false),
  (1, 1, 'SPK-1004', CURRENT_DATE, '14:00:00', 'Cliente D', 42.00, 0, 0, 0, 42.00, 'delivery', false),
  (1, 1, 'SPK-1005', CURRENT_DATE, '14:30:00', 'Cliente E', 30.00, 0, 0, 0, 30.00, 'delivery', false),
  (1, 1, 'SPK-1006', CURRENT_DATE, '15:00:00', 'Cliente F', 36.00, 0, 0, 0, 36.00, 'delivery', false);

-- Items de esas ventas (sale_id 1-6 por RESTART IDENTITY)
INSERT INTO sale_items (sale_id, product_id, item_name, item_type, quantity, unit_of_measure, unit_price, discount_pct, discount_amount, tax_pct, tax_amount, total) VALUES
  (1, 1, 'Ceviche Clásico', 'product', 1, 'unidad', 28.00, 0, 0, 0, 0, 28.00),
  (2, 2, 'Arroz con Mariscos', 'product', 1, 'unidad', 32.00, 0, 0, 0, 0, 32.00),
  (2, 3, 'Inca Kola 500ml', 'product', 1, 'unidad', 5.00, 0, 0, 0, 0, 5.00),
  (3, 2, 'Arroz con Mariscos', 'product', 1, 'unidad', 32.00, 0, 0, 0, 0, 32.00),
  (4, 4, 'Ceviche Mixto', 'product', 1, 'unidad', 36.00, 0, 0, 0, 0, 36.00),
  (4, 3, 'Inca Kola 500ml', 'product', 1, 'unidad', 5.00, 0, 0, 0, 0, 5.00),
  (4, 5, 'Lomo Saltado', 'product', 1, 'unidad', 1.00, 0, 0, 0, 0, 1.00),
  (5, 5, 'Lomo Saltado', 'product', 1, 'unidad', 30.00, 0, 0, 0, 0, 30.00),
  (6, 4, 'Ceviche Mixto', 'product', 1, 'unidad', 36.00, 0, 0, 0, 0, 36.00);

-- Pedidos delivery ligados
INSERT INTO delivery_orders (tenant_id, sale_id, zone_id, tracking_code, customer_name, customer_phone, customer_address, fee, eta_min, status, received_at) VALUES
  (1, 1, 1, 'DLV-SPK-1001', 'Cliente A', '999111222', 'Av. Montenegro 100', 5.00, 45, 'delivered', now() - interval '3 hours'),
  (1, 2, 1, 'DLV-SPK-1002', 'Cliente B', '999333444', 'Calle Los Olivos 200', 5.00, 45, 'out_for_delivery', now() - interval '2 hours'),
  (1, 3, 2, 'DLV-SPK-1003', 'Cliente C', '999555666', 'Jr. Canto Grande 300', 6.00, 50, 'preparing', now() - interval '1 hour'),
  (1, 4, 3, 'DLV-SPK-1004', 'Cliente D', '999777888', 'Av. Motupe 400', 7.00, 55, 'received', now() - interval '30 minutes'),
  (1, 5, 1, 'DLV-SPK-1005', 'Cliente E', '999999000', 'Av. Montenegro 500', 5.00, 45, 'delivered', now() - interval '4 hours'),
  (1, 6, 2, 'DLV-SPK-1006', 'Cliente F', '998111222', 'Jr. Canto Grande 600', 6.00, 50, 'out_for_delivery', now() - interval '20 minutes');

-- Una venta de AYER (filtro por fecha)
INSERT INTO sales (tenant_id, user_id, sale_number, sale_date, sale_time, customer_name, subtotal, discount_total, tax_total, tip_amount, total, business_type, is_voided) VALUES
  (1, 1, 'SPK-0901', CURRENT_DATE - 1, '19:00:00', 'Cliente Ayer', 28.00, 0, 0, 0, 28.00, 'delivery', false);
INSERT INTO sale_items (sale_id, product_id, item_name, item_type, quantity, unit_of_measure, unit_price, discount_pct, discount_amount, tax_pct, tax_amount, total) VALUES
  (7, 1, 'Ceviche Clásico', 'product', 1, 'unidad', 28.00, 0, 0, 0, 0, 28.00);
INSERT INTO delivery_orders (tenant_id, sale_id, zone_id, tracking_code, customer_name, customer_phone, customer_address, fee, eta_min, status, received_at) VALUES
  (1, 7, 1, 'DLV-SPK-0901', 'Cliente Ayer', '997111222', 'Av. Montenegro 700', 5.00, 45, 'delivered', now() - interval '1 day');
