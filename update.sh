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

# Display service status and URLs
echo ""
echo "🔍 Container Status:"
docker-compose ps

echo ""
echo "🌐 Access the application at:"
echo "   Development: http://localhost:8080"
echo "   Production: https://tweet-optimize.com (when DNS is propagated)"
echo ""
echo "📊 Check logs with: docker-compose logs -f [service_name]"
echo "   Services: tweet-optimizer-backend, tweet-optimizer-frontend, tweet-optimizer-nginx" 