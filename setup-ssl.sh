#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        ARS Backend - SSL/TLS Certificate Setup       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    echo -e "${YELLOW}Installing certbot...${NC}"
    sudo apt-get update
    sudo apt-get install -y certbot python3-certbot-nginx
fi

# Get domain from user
echo -e "\n${YELLOW}Enter your domain name:${NC}"
read -p "Domain: " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}❌ Domain cannot be empty${NC}"
    exit 1
fi

# Ensure nginx is configured correctly
echo -e "\n${YELLOW}Updating nginx configuration for SSL...${NC}"

# Temporary server block for certbot verification
sudo tee /etc/nginx/sites-available/ars-backend > /dev/null <<'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name _;

    # Certbot challenge directory
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}
EOF

# Create certbot directory
sudo mkdir -p /var/www/certbot

# Test nginx
sudo nginx -t
sudo systemctl reload nginx

# Request certificate
echo -e "\n${YELLOW}Requesting SSL certificate for $DOMAIN...${NC}"
sudo certbot certonly \
    --webroot \
    -w /var/www/certbot \
    -d "$DOMAIN" \
    --non-interactive \
    --agree-tos \
    -m admin@$DOMAIN

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Certificate obtained successfully!${NC}"
    
    # Update nginx configuration with SSL paths
    echo -e "\n${YELLOW}Updating nginx configuration with SSL certificates...${NC}"
    
    CERT_PATH="/etc/letsencrypt/live/$DOMAIN"
    
    sudo tee /etc/nginx/sites-available/ars-backend > /dev/null <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    
    server_name $DOMAIN;
    
    ssl_certificate $CERT_PATH/fullchain.pem;
    ssl_certificate_key $CERT_PATH/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_stapling on;
    ssl_stapling_verify on;

    access_log /var/log/nginx/ars-backend-access.log;
    error_log /var/log/nginx/ars-backend-error.log;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    client_max_body_size 100M;

    proxy_connect_timeout 120s;
    proxy_send_timeout 120s;
    proxy_read_timeout 120s;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_buffering off;
        proxy_request_buffering off;
    }

    location /api/health {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        access_log off;
    }
}
EOF
    
    # Test and reload nginx
    sudo nginx -t
    sudo systemctl reload nginx
    
    # Set up auto-renewal
    echo -e "\n${YELLOW}Setting up automatic certificate renewal...${NC}"
    sudo systemctl enable certbot.timer
    sudo systemctl start certbot.timer
    
    echo -e "\n${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                  ✅ SSL Setup Complete!               ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
    
    echo -e "\n${GREEN}Your domain is now secured with HTTPS!${NC}"
    echo -e "Certificate will auto-renew 30 days before expiration."
    echo -e "\n${YELLOW}Test your setup:${NC}"
    echo -e "curl https://$DOMAIN/api/health"
    
else
    echo -e "${RED}❌ Failed to obtain certificate${NC}"
    echo -e "Please check your domain and try again"
    exit 1
fi
