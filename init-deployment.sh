#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/ManmohanSinghRaghav/ARS.git"
BRANCH="v1"
APP_DIR="/home/ubuntu/ARS"
BACKEND_DIR="$APP_DIR/backend"
LOG_DIR="/var/log/ars-backend"
VENV_DIR="$BACKEND_DIR/venv"

echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ARS Backend - EC2 Deployment Initialization      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"

# Step 1: Update system
echo -e "\n${YELLOW}[1/10]${NC} Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Step 2: Install system dependencies
echo -e "\n${YELLOW}[2/10]${NC} Installing system dependencies..."
sudo apt-get install -y \
    git \
    curl \
    wget \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    certbot \
    python3-certbot-nginx \
    supervisor \
    build-essential \
    libssl-dev \
    libffi-dev \
    redis-server

# Step 3: Create app directory
echo -e "\n${YELLOW}[3/10]${NC} Setting up application directories..."
mkdir -p "$APP_DIR"
mkdir -p "$LOG_DIR"
sudo chown -R ubuntu:ubuntu "$APP_DIR"
sudo chown -R ubuntu:ubuntu "$LOG_DIR"

# Step 4: Clone repository
echo -e "\n${YELLOW}[4/10]${NC} Cloning ARS repository..."
if [ -d "$APP_DIR/.git" ]; then
    cd "$APP_DIR"
    git pull origin "$BRANCH"
else
    cd /home/ubuntu
    git clone -b "$BRANCH" "$REPO_URL"
fi

# Step 5: Create Python virtual environment
echo -e "\n${YELLOW}[5/10]${NC} Creating Python virtual environment..."
cd "$BACKEND_DIR"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Step 6: Install Python dependencies
echo -e "\n${YELLOW}[6/10]${NC} Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install gunicorn uvicorn

# Step 7: Create .env file
echo -e "\n${YELLOW}[7/10]${NC} Setting up environment configuration..."
if [ ! -f "$BACKEND_DIR/.env" ]; then
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo -e "${RED}⚠️  Please edit $BACKEND_DIR/.env with your API keys${NC}"
fi

# Step 8: Copy configuration files
echo -e "\n${YELLOW}[8/10]${NC} Installing configuration files..."

# Copy systemd service file
sudo cp "$APP_DIR/ars-backend.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ars-backend

# Copy nginx configuration
sudo cp "$BACKEND_DIR/nginx.conf" /etc/nginx/sites-available/ars-backend
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/ars-backend /etc/nginx/sites-enabled/ars-backend

# Test nginx configuration
sudo nginx -t
echo -e "${GREEN}✅ Nginx configuration valid${NC}"

# Step 9: Set up log rotation
echo -e "\n${YELLOW}[9/10]${NC} Setting up log rotation..."
sudo tee /etc/logrotate.d/ars-backend > /dev/null <<EOF
/var/log/ars-backend/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 ubuntu ubuntu
    sharedscripts
    postrotate
        systemctl reload ars-backend > /dev/null 2>&1 || true
    endscript
}
EOF

# Step 10: Summary
echo -e "\n${YELLOW}[10/10]${NC} Deployment initialization complete!"

echo -e "\n${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Next Steps (IMPORTANT!)                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"

echo -e "\n${YELLOW}1. Configure Environment Variables:${NC}"
echo -e "   ${YELLOW}nano $BACKEND_DIR/.env${NC}"
echo "   - Add Firebase credentials"
echo "   - Add API keys (Gemini, Groq, Claude)"
echo "   - Update CORS_ORIGINS with your frontend URL"

echo -e "\n${YELLOW}2. Upload Firebase Service Account:${NC}"
echo "   ${YELLOW}scp -i /path/to/key.pem service-account.json ubuntu@\$EC2_IP:$APP_DIR/${NC}"

echo -e "\n${YELLOW}3. Start the backend services:${NC}"
echo "   ${YELLOW}sudo systemctl start ars-backend${NC}"
echo "   ${YELLOW}sudo systemctl start nginx${NC}"

echo -e "\n${YELLOW}4. Check status:${NC}"
echo "   ${YELLOW}sudo systemctl status ars-backend${NC}"
echo "   ${YELLOW}sudo systemctl status nginx${NC}"

echo -e "\n${YELLOW}5. View logs:${NC}"
echo "   ${YELLOW}sudo journalctl -u ars-backend -f${NC}"

echo -e "\n${YELLOW}6. Test health endpoint:${NC}"
echo "   ${YELLOW}curl http://localhost/api/health${NC}"

echo -e "\n${GREEN}✅ Your ARS backend is ready!${NC}\n"
