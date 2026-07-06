# ═══════════════════════════════════════════════════════════════
#  IaaS-RonSys — Frontend Web Dockerfile (multistage)
#
#  Stage 1: Build con Node
#  Stage 2: Runtime con nginx:alpine
#
#  Build:
#    docker build -t iaas-web .
#
#  Run:
#    docker run -p 80:80 iaas-web
#
#  O con docker-compose desde la raíz del monorepo:
#    docker-compose up -d web
# ═══════════════════════════════════════════════════════════════

# ─── Stage 1: Build ───────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copiar package.json y lock para cache de capa de dependencias
COPY package.json package-lock.json ./
RUN npm ci --production=false

# Copiar código fuente
COPY . .

# TypeScript check + build
RUN npx tsc --noEmit && npm run build

# ─── Stage 2: Runtime ─────────────────────────────────────────
FROM nginx:alpine

# Copiar build de producción
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar configuración de nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
