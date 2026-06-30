FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy prisma schema for client generation
COPY prisma ./prisma
RUN npx prisma generate

# Copy rest of the app
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
