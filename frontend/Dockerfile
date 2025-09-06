# Stage 1: Dependencies
FROM node:18-alpine AS deps
WORKDIR /frontend
COPY package*.json ./
RUN npm ci

# Stage 2: Builder
FROM node:18-alpine AS builder
WORKDIR /frontend
COPY --from=deps /frontend/node_modules ./node_modules
COPY . .
RUN npm run build

# Stage 3: Production
FROM nginx:alpine AS production

# Create required directories first
RUN mkdir -p /usr/share/nginx/html \
    && mkdir -p /usr/share/nginx/html/data \
    && mkdir -p /frontend/static \
    && mkdir -p /frontend/media

# Copy the built files
COPY --from=builder /frontend/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Set proper permissions
RUN chown -R nginx:nginx /usr/share/nginx \
    && chown -R nginx:nginx /frontend \
    && chown -R nginx:nginx /var/cache/nginx \
    && chown -R nginx:nginx /var/log/nginx \
    && chown -R nginx:nginx /etc/nginx/conf.d \
    && touch /var/run/nginx.pid \
    && chown -R nginx:nginx /var/run/nginx.pid \
    && chmod -R 755 /usr/share/nginx/html/data

USER nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

# Stage 4: Development
FROM node:18-alpine AS development
WORKDIR /frontend
COPY --from=deps /frontend/node_modules ./node_modules
COPY . .
RUN mkdir -p /usr/share/nginx/html/data
EXPOSE 5173
CMD ["npm", "run", "dev"]