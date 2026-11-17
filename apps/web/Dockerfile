FROM node:24-alpine

WORKDIR /repo

COPY package.json package-lock.json ./
COPY apps/web/package.json ./apps/web/package.json
COPY packages/shared-contracts/package.json ./packages/shared-contracts/package.json

RUN npm ci

COPY apps/web ./apps/web
COPY packages/shared-contracts ./packages/shared-contracts

EXPOSE 5173

CMD ["npm", "run", "dev", "--workspace", "@petrosense/web", "--", "--host", "0.0.0.0"]
