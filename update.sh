#!/bin/bash

# Print commands and exit on errors
set -ex

echo "🔄 Pulling latest changes from git..."
git pull

echo "🛑 Stopping containers..."
docker-compose down

echo "🏗️ Building containers..."
docker-compose build

echo "🚀 Starting containers..."
docker-compose up -d

echo "✅ Update completed successfully!" 