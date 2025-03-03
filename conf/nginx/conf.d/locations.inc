# Frontend for tweet-optimize.com
location / {
    proxy_pass http://tweet-optimizer-frontend:80;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $http_cf_connecting_ip;
    proxy_set_header X-Forwarded-For $http_cf_connecting_ip;
    proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
    proxy_set_header CF-Visitor $http_cf_visitor;
    proxy_set_header CF-IPCountry $http_cf_ipcountry;
    # Extended WebSocket timeout
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
}

# Backend API for tweet-optimize.com
location /api {
    rewrite ^/api/?(.*)$ /$1 break;
    proxy_pass http://tweet-optimizer-backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $http_cf_connecting_ip;
    proxy_set_header X-Forwarded-For $http_cf_connecting_ip;
    proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
    proxy_set_header CF-Visitor $http_cf_visitor;
    proxy_set_header CF-IPCountry $http_cf_ipcountry;
    proxy_cache_bypass $http_upgrade;
    # Extended WebSocket timeout
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
}

# Direct auth endpoint (for compatibility)
location /auth {
    proxy_pass http://tweet-optimizer-backend:8000/auth;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $http_cf_connecting_ip;
    proxy_set_header X-Forwarded-For $http_cf_connecting_ip;
    proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
    proxy_set_header CF-Visitor $http_cf_visitor;
    proxy_set_header CF-IPCountry $http_cf_ipcountry;
    proxy_cache_bypass $http_upgrade;
    # Extended WebSocket timeout
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
}

# Health check endpoint for tweet-optimize.com
location /health {
    access_log off;
    add_header Content-Type text/plain;
    return 200 'healthy';
} 