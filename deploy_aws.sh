#!/bin/bash
# AWS EC2 Deployment Script for ARS Backend
# Run this on your EC2 instance after SSH connection

set -e  # Exit on error

echo "🚀 ARS Backend AWS Deployment Script"
echo "===================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running as ubuntu user
if [ "$(whoami)" != "ubuntu" ]; then
    echo -e "${RED}❌ Please run this script as ubuntu user${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Update System${NC}"
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3.11 python3-pip python3-venv git nginx curl wget supervisor

echo -e "${GREEN}✓ System updated${NC}"

echo -e "${YELLOW}Step 2: Clone Repository${NC}"
cd ~
if [ -d "ARS" ]; then
    echo "Repository already exists, pulling latest changes..."
    cd ARS
    git pull
else
    git clone https://github.com/YOUR_USERNAME/ARS.git
    cd ARS
fi

echo -e "${GREEN}✓ Repository ready${NC}"

echo -e "${YELLOW}Step 3: Setup Python Virtual Environment${NC}"
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✓ Virtual environment ready${NC}"

echo -e "${YELLOW}Step 4: Create .env File${NC}"
if [ ! -f ".env" ]; then
    echo "⚠️  Please create .env file manually with your API keys:"
    echo "   nano .env"
    echo ""
    echo "Required environment variables:"
    echo "  - GEMINI_API_KEY"
    echo "  - GROQ_API_KEY"
    echo "  - CLAUDE_API_KEY"
    echo "  - FIREBASE_SERVICE_ACCOUNT_PATH=/home/ubuntu/ARS/service-account.json"
    echo "  - REDIS_URL=redis://localhost:6379"
    echo "  - CORS_ORIGINS=[your-vercel-frontend-url]"
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

echo -e "${YELLOW}Step 5: Create Gunicorn Config${NC}"
cat > gunicorn_config.py << 'EOF'
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 100
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

accesslog = "/var/log/ars/access.log"
errorlog = "/var/log/ars/error.log"
loglevel = "info"
EOF

echo -e "${GREEN}✓ Gunicorn config created${NC}"

echo -e "${YELLOW}Step 6: Create Log Directory${NC}"
sudo mkdir -p /var/log/ars
sudo chown ubuntu:ubuntu /var/log/ars
sudo chmod 755 /var/log/ars

echo -e "${GREEN}✓ Log directory ready${NC}"

echo -e "${YELLOW}Step 7: Create Systemd Service${NC}"
sudo tee /etc/systemd/system/ars-backend.service > /dev/null << 'EOF'
[Unit]
Description=ARS Backend FastAPI Service
After=network.target

[Service]
Type=notify
User=ubuntu
WorkingDirectory=/home/ubuntu/ARS/backend
Environment="PATH=/home/ubuntu/ARS/venv/bin"
ExecStart=/home/ubuntu/ARS/venv/bin/gunicorn app.main:app -c gunicorn_config.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload

echo -e "${GREEN}✓ Systemd service created${NC}"

echo -e "${YELLOW}Step 8: Create Nginx Config${NC}"
sudo tee /etc/nginx/sites-available/ars-backend > /dev/null << 'EOF'
upstream gunicorn {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name _;
    
    client_max_body_size 100M;
    
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
    limit_req zone=general burst=20;
    
    location / {
        proxy_pass http://gunicorn;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /health {
        access_log off;
        proxy_pass http://gunicorn;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/ars-backend /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

sudo nginx -t
echo -e "${GREEN}✓ Nginx config created${NC}"

echo -e "${YELLOW}Step 9: Start Services${NC}"
sudo systemctl start ars-backend
sudo systemctl enable ars-backend
sudo systemctl restart nginx
sudo systemctl enable nginx

echo -e "${GREEN}✓ Services started${NC}"

echo -e "${YELLOW}Step 10: Test Backend${NC}"
sleep 2
if curl -s http://localhost/api/health > /dev/null; then
    echo -e "${GREEN}✓ Backend is responding!${NC}"
    curl http://localhost/api/health
else
    echo -e "${RED}❌ Backend not responding, check logs:${NC}"
    sudo journalctl -u ars-backend -n 20
fi

echo ""
echo -e "${GREEN}===================================="
echo "✅ ARS Backend Deployment Complete!"
echo "====================================${NC}"
echo ""
echo "📌 Next Steps:"
echo "1. Copy service account: scp service-account.json to /home/ubuntu/ARS/"
echo "2. Update .env file with your API keys"
echo "3. Verify health: curl http://$(hostname -I | awk '{print $1}')/api/health"
echo "4. Update frontend API URL in Vercel"
echo ""
echo "📊 Useful Commands:"
echo "   - View logs: sudo journalctl -u ars-backend -f"
echo "   - Restart: sudo systemctl restart ars-backend"
echo "   - Status: sudo systemctl status ars-backend"
echo "   - Nginx: sudo systemctl restart nginx"
echo ""
echo "🔍 Get your EC2 public IP:"
echo "   - AWS Console → EC2 → Instances"
echo "   - Or: curl http://169.254.169.254/latest/meta-data/public-ipv4"
