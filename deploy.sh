#!/bin/bash

# Print commands and exit on errors
set -ex

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}   Tweet Optimizer Deployment Tool   ${NC}"
echo -e "${BLUE}=====================================${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# Create necessary directories
echo -e "${GREEN}Creating necessary directories...${NC}"
mkdir -p ssl
mkdir -p conf/nginx

# Check if SSL certificates exist, prompt if not
if [ ! -f ssl/cert.pem ] || [ ! -f ssl/key.pem ]; then
    echo -e "${YELLOW}SSL certificates not found in ./ssl directory.${NC}"
    echo -e "${YELLOW}For production, you will need to add:${NC}"
    echo -e "  - ssl/cert.pem (certificate file)"
    echo -e "  - ssl/key.pem (private key file)"
    echo ""
    echo -e "${YELLOW}Do you want to continue with development setup? [Y/n]${NC}"
    read -r response
    if [[ "$response" =~ ^([nN][oO]|[nN])$ ]]; then
        echo -e "${RED}Deployment aborted.${NC}"
        exit 1
    fi
fi

# Check if .env files exist and create them if needed
if [ ! -f backend/.env ]; then
    echo -e "${YELLOW}Backend .env file not found. Creating a template...${NC}"
    cat > backend/.env << EOF
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tweetoptimizer
DB_USER=postgres
DB_PASSWORD=password

# API Keys
STRIPE_API_KEY=your_stripe_api_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
RESEND_API_KEY=your_resend_api_key

# JWT Configuration
JWT_SECRET=your_jwt_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# General Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
EOF
    echo -e "${YELLOW}Please update backend/.env with your actual configuration values.${NC}"
    echo -e "${YELLOW}Press Enter to continue or Ctrl+C to abort and update the file.${NC}"
    read -r
fi

# Build and start the services
echo -e "${GREEN}Building and starting services...${NC}"
docker-compose build
docker-compose up -d

# Display service status and URLs
echo -e "${GREEN}Deployment completed!${NC}"
echo ""
echo -e "${BLUE}Container Status:${NC}"
docker-compose ps

echo ""
echo -e "${BLUE}Access the application at:${NC}"
echo -e "   Development: http://localhost:8080"
echo -e "   Production: https://tweet-optimize.com (when DNS is propagated)"
echo ""
echo -e "${BLUE}Check logs with:${NC} docker-compose logs -f [service_name]"
echo -e "   Services: tweet-optimizer-backend, tweet-optimizer-frontend, tweet-optimizer-nginx"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Update backend/.env with your database and API credentials"
echo -e "2. Add SSL certificates to the ./ssl directory for production use"
echo -e "3. Configure your server's Nginx (if needed) to handle SSL termination"
echo -e "4. Visit http://localhost:8080 to verify the application is working" 