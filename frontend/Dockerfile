# Base stage for shared configuration
FROM node:18-alpine AS base
WORKDIR /app
COPY package*.json ./

# Development stage
FROM base AS development
RUN npm install
EXPOSE 5173
ENV HOST=0.0.0.0
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Build stage
FROM base AS build
RUN npm install
# Copy .env file first
COPY .env .env
# Then copy the rest of the application
COPY . .
RUN npm run build

# Production stage - using a simple static file server
FROM node:18-alpine AS production
WORKDIR /app
RUN npm install -g serve

# Copy the build output from the build stage
COPY --from=build /app/build ./build

EXPOSE 80
CMD ["serve", "-s", "build", "-l", "80"]