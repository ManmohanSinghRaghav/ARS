#!/bin/bash

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         ARS Backend - System Health Monitor          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"

# Check backend service
echo -e "\n${YELLOW}Backend Service Status:${NC}"
if sudo systemctl is-active --quiet ars-backend; then
    echo -e "${GREEN}✅ ars-backend is running${NC}"
else
    echo -e "${RED}❌ ars-backend is NOT running${NC}"
fi

# Check nginx
echo -e "\n${YELLOW}Nginx Status:${NC}"
if sudo systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ nginx is running${NC}"
else
    echo -e "${RED}❌ nginx is NOT running${NC}"
fi

# Health endpoint check
echo -e "\n${YELLOW}Health Endpoint Check:${NC}"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost/api/health)
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
BODY=$(echo "$HEALTH_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Health endpoint responding${NC}"
    echo "Response: $BODY"
else
    echo -e "${RED}❌ Health endpoint returned HTTP $HTTP_CODE${NC}"
fi

# System resources
echo -e "\n${YELLOW}System Resources:${NC}"

# CPU
echo -e "${BLUE}CPU Usage:${NC}"
top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{printf "  Used: %.1f%%\n", 100 - $1}'

# Memory
echo -e "${BLUE}Memory Usage:${NC}"
free -h | awk '/^Mem/ {printf "  Total: %s, Used: %s, Available: %s\n", $2, $3, $7}'

# Disk
echo -e "${BLUE}Disk Usage:${NC}"
df -h / | awk 'NR==2 {printf "  Total: %s, Used: %s, Available: %s (%s)\n", $2, $3, $4, $5}'

# Process count
echo -e "${BLUE}Process Count:${NC}"
echo "  Total processes: $(ps aux | wc -l)"
echo "  Gunicorn workers: $(ps aux | grep -c '[g]unicorn')"

# Network connections
echo -e "\n${YELLOW}Network Connections:${NC}"
echo "  Listening on port 8000: $(sudo netstat -tulpn 2>/dev/null | grep -c ':8000' || echo 'N/A')"
echo "  Listening on port 80: $(sudo netstat -tulpn 2>/dev/null | grep -c ':80' || echo 'N/A')"
echo "  Listening on port 443: $(sudo netstat -tulpn 2>/dev/null | grep -c ':443' || echo 'N/A')"

# Recent errors
echo -e "\n${YELLOW}Recent Errors (Last 10):${NC}"
ERROR_COUNT=$(sudo journalctl -u ars-backend --since "1 hour ago" --priority err | wc -l)
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo -e "${RED}⚠️  Found $ERROR_COUNT errors in last hour:${NC}"
    sudo journalctl -u ars-backend --since "1 hour ago" --priority err | tail -5
else
    echo -e "${GREEN}✅ No errors in last hour${NC}"
fi

# Recommendations
echo -e "\n${YELLOW}Recommendations:${NC}"

# Check memory usage
MEMORY_PERCENT=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')
if [ "$MEMORY_PERCENT" -gt 80 ]; then
    echo -e "${RED}⚠️  High memory usage: ${MEMORY_PERCENT}%${NC}"
    echo "   Consider restarting the service or upgrading instance"
fi

# Check disk usage
DISK_PERCENT=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_PERCENT" -gt 80 ]; then
    echo -e "${RED}⚠️  High disk usage: ${DISK_PERCENT}%${NC}"
    echo "   Clean up old logs or increase disk space"
fi

# Check uptime
UPTIME=$(uptime -p)
echo -e "${GREEN}✅ System uptime: $UPTIME${NC}"

# Summary
echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
if sudo systemctl is-active --quiet ars-backend && [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ All systems operational!${NC}"
else
    echo -e "${RED}⚠️  Some systems need attention${NC}"
fi
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"

# Detailed log options
echo -e "${YELLOW}View detailed logs:${NC}"
echo "  Backend: ${YELLOW}sudo journalctl -u ars-backend -f${NC}"
echo "  Nginx:   ${YELLOW}sudo tail -f /var/log/nginx/ars-backend-error.log${NC}"
echo "  Full:    ${YELLOW}sudo tail -f /var/log/ars-backend/app.log${NC}"
