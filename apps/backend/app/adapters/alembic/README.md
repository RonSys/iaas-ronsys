# Migraciones Alembic

La migración inicial ya está creada: `0001_initial_setup`.

Crea todas las tablas (companies, accounts, journal_entries, journal_entry_lines,
products, kardex_movements) y siembra el plan de cuentas PCGE (60+ cuentas).

## Comandos

```bash
cd apps/backend

# Ejecutar migraciones pendientes
alembic upgrade head

# Crear nueva migración (autogenerate desde modelos)
alembic revision --autogenerate -m "descripcion"

# Revertir última migración
alembic downgrade -1

# Ver historial
alembic history

# Ver SQL que se ejecutaría (sin aplicarlo)
alembic upgrade head --sql
```

## Migraciones existentes

| ID | Descripción | Tablas |
|----|-------------|--------|
| `0001_initial_setup` | Setup inicial | companies, accounts, journal_entries, journal_entry_lines, products, kardex_movements + seed plan de cuentas |
