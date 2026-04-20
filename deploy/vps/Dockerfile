FROM node:22-alpine

RUN apk add --no-cache bash docker-cli docker-cli-compose

WORKDIR /opt/schedra-deploy

COPY webhook-listener.mjs ./webhook-listener.mjs
COPY deploy.sh ./deploy.sh

RUN chmod +x ./deploy.sh

ENV NODE_ENV=production
ENV DEPLOY_PORT=8787
ENV DEPLOY_SCRIPT=/opt/schedra-deploy/deploy.sh

EXPOSE 8787

CMD ["node", "/opt/schedra-deploy/webhook-listener.mjs"]
