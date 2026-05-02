#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

BACKEND_DIR="/home/ubuntu/ARS/backend"
BRANCH="${1:-v1}"

echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       ARS Backend - Update and Redeploy Script       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"

# Check if running
echo -e "\n${YELLOW}Checking current status...${NC}"
if sudo systemctl is-active --quiet ars-backend; then
    WAS_RUNNING=true
    echo -e "${GREEN}✅ Service is currently running${NC}"
else
    WAS_RUNNING=false
    echo -e "${YELLOW}⚠️  Service is not running${NC}"
fi

# Fetch latest code
echo -e "\n${YELLOW}[1/5] Pulling latest code from $BRANCH...${NC}"
cd "$BACKEND_DIR"
git fetch origin
git reset --hard origin/"$BRANCH"
echo -e "${GREEN}✅ Code updated${NC}"

# Update dependencies
echo -e "\n${YELLOW}[2/5] Updating Python dependencies...${NC}"
source /home/ubuntu/ARS/backend/venv/bin/activate
pip install --upgrade -r requirements.txt
pip install gunicorn uvicorn
echo -e "${GREEN}✅ Dependencies updated${NC}"

# Verify configuration
echo -e "\n${YELLOW}[3/5] Verifying configuration...${NC}"
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo -e "   Create it with: cp $BACKEND_DIR/.env.example $BACKEND_DIR/.env"
    exit 1
fi
echo -e "${GREEN}✅ Configuration verified${NC}"

# Restart service
echo -e "\n${YELLOW}[4/5] Restarting backend service...${NC}"
if [ "$WAS_RUNNING" = true ]; then
    sudo systemctl restart ars-backend
    echo -e "${GREEN}✅ Service restarted${NC}"
else
    sudo systemctl start ars-backend
    echo -e "${GREEN}✅ Service started${NC}"
fi

# Health check
echo -e "\n${YELLOW}[5/5] Running health check...${NC}"
sleep 2

HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost/api/health)
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
BODY=$(echo "$HEALTH_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Health check passed!${NC}"
    echo "Response: $BODY"
else
    echo -e "${RED}❌ Health check failed with HTTP $HTTP_CODE${NC}"
    echo -e "${YELLOW}Checking logs:${NC}"
    sudo journalctl -u ars-backend -n 20
    exit 1
fi

echo -e "\n${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}✅ Redeployment Complete!${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"

echo -e "\n${YELLOW}Next steps:${NC}"
echo "  - Verify changes in logs: ${YELLOW}sudo journalctl -u ars-backend -f${NC}"
echo "  - Test API: ${YELLOW}curl http://localhost/api/health${NC}"
echo "  - Check metrics: ${YELLOW}bash /home/ubuntu/ARS/monitor.sh${NC}"
