FROM node:22-alpine AS build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend /app/frontend
RUN npm run build

FROM node:22-alpine

ENV NODE_ENV=production \
    NITRO_HOST=0.0.0.0 \
    NITRO_PORT=3000 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

WORKDIR /app/frontend

COPY --from=build /app/frontend/.output ./.output

CMD ["node", ".output/server/index.mjs"]
