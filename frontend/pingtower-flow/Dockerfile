# --- build stage ---
FROM node:20-alpine AS build

WORKDIR /app

# Установим зависимости (чтобы кэшировалось)
COPY package*.json ./
RUN npm install

# Скопируем исходники
COPY . .

# Сборка (production билд)
RUN npm run build

# --- run stage ---
FROM node:20-alpine

WORKDIR /app

# Скопируем билд
COPY --from=build /app/dist ./dist
COPY package*.json ./

# Установим serve для preview
RUN npm install -g serve

# Условие для запуска
EXPOSE 8080

CMD if [ "$NODE_ENV" = "development" ]; then \
      npm install && npm run dev -- --host 0.0.0.0 --port 8080; \
    else \
      serve -s dist -l 8080; \
    fi

