# Deployment Guide for tweet-optimize.com

This guide outlines the steps to deploy the Twitter Forecast application to a server where an identical application is already running.

## Prerequisites

1. Docker and Docker Compose installed on the server
2. DNS A record for `tweet-optimize.com` pointed to the server IP (already done)
3. SSL certificates (optional but recommended for production)

## Configuration Files

The following files have been configured for this deployment:

- `docker-compose.yaml` - Updated with unique service names and different ports
- `conf/nginx/nginx.conf` - Main Nginx configuration with socket optimizations
- `conf/nginx/conf.d/default.conf` - Nginx server configuration for tweet-optimize.com
- `conf/nginx/conf.d/locations.inc` - Common location blocks for our application
- `frontend/.env` - Development environment variables
- `frontend/.env.production` - Production environment variables

## Port Changes

To avoid conflicts with the existing application, we've changed the following ports:

| Service   | Original Port | New Port |
|-----------|---------------|----------|
| Backend   | 8000          | 8001     |
| Frontend  | 3000          | 3001     |
| Nginx     | 80            | 8080     |
| Nginx SSL | 443           | 4443     |

## Deployment Steps

1. Clone the repository to the server:
   ```
   git clone <repository-url> tweet-optimizer
   cd tweet-optimizer
   ```

2. Set up environment variables:
   - Create/update `backend/.env` with database credentials, API keys, etc.
   - Frontend environment variables are already configured

3. SSL setup (optional for development, required for production):
   ```
   mkdir -p ssl
   # Place SSL certificates in the ssl directory
   # cert.pem and key.pem
   ```

4. Start the application:
   ```
   docker-compose up -d
   ```

5. Verify deployment:
   - Check if containers are running: `docker-compose ps`
   - Access the development site at: `http://localhost:8080`

## Production Deployment with SSL

For production deployment, you'll need to:

1. Obtain SSL certificates for `tweet-optimize.com`
2. Configure a reverse proxy (like Nginx) on the host machine to:
   - Route traffic from port 80/443 to our internal ports 8080/4443
   - Handle SSL termination if preferred at the host level

### External Nginx Configuration Example

If you have Nginx installed on the host machine, add this configuration:

```nginx
server {
    listen 80;
    server_name tweet-optimize.com www.tweet-optimize.com;
    return 301 https://tweet-optimize.com$request_uri;
}

server {
    listen 443 ssl;
    server_name tweet-optimize.com;

    ssl_certificate /path/to/your/cert.pem;
    ssl_certificate_key /path/to/your/key.pem;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting

- **Port conflicts**: If you still encounter port conflicts, modify the ports in `docker-compose.yaml`
- **Connection issues**: Check that the services can communicate within the Docker network
- **SSL issues**: Verify certificate paths and permissions

## Monitoring and Maintenance

- Monitor logs: `docker-compose logs -f`
- Restart services: `docker-compose restart <service-name>`
- Update application: 
  ```
  git pull
  docker-compose down
  docker-compose up -d --build
  ``` 