# Build stage
FROM node:18-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Production stage - using a simple static file server
FROM node:18-alpine

WORKDIR /app
RUN npm install -g serve

# Copy the build output from the build stage
COPY --from=build /app/build ./build

EXPOSE 80
CMD ["serve", "-s", "build", "-l", "80"]