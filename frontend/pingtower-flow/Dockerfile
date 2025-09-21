# --- build stage ---
FROM node:20-alpine AS build

WORKDIR /app

# Устанавливаем ВСЕ зависимости (включая devDependencies)
COPY package*.json ./
RUN npm install --include=dev

# Копируем исходники
COPY . .

# Сборка (production билд)
RUN npm run build

# --- run stage ---
FROM node:20-alpine

WORKDIR /app

# Копируем только билд
COPY --from=build /app/dist ./dist
COPY package*.json ./

# Ставим serve для запуска статики
RUN npm install -g serve

EXPOSE 8080

CMD if [ "$NODE_ENV" = "development" ]; then \
      npm install --include=dev && npm run dev -- --host 0.0.0.0 --port 8080; \
    else \
      serve -s dist -l 8080; \
    fi
