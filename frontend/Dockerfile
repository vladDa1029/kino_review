FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Вторая стадия - запуск сервера для раздачи статических файлов
FROM node:20-alpine

WORKDIR /app

# Копируем все файлы package* (включая package-lock.json)
COPY --from=build /app/package*.json ./

# Устанавливаем только production зависимости
RUN npm ci --only=production

# Устанавливаем serve для раздачи статических файлов
RUN npm install -g serve

# Копируем сконструированные файлы
COPY --from=build /app/dist ./dist

# Expose порт
EXPOSE 80

# Запускаем serve для раздачи статических файлов
CMD ["serve", "-s", "dist", "-l", "80"]