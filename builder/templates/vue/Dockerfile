# Stage 1: Build Vue app
FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:latest
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY start_app.sh /start_app.sh
RUN chmod +x /start_app.sh
EXPOSE 80
CMD ["/start_app.sh"]
