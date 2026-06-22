# CI
FROM node:22-alpine AS builder

WORKDIR /app

# dependency
COPY package.json package-lock.json ./
RUN npm ci

# 复制源码
COPY . .

# run test
RUN npm run lint
RUN npm run type-check
RUN npm run test
RUN npm run build

# CD
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
