#!/bin/bash
# Finance Tracker VPS Setup Script
# Run this on a fresh Ubuntu 22.04/24.04 VPS
# Usage: curl -fsSL <url> | sudo bash

set -e

echo "=========================================="
echo "  Finance Tracker - VPS Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo)${NC}"
    exit 1
fi

# Get the non-root user (who called sudo)
ACTUAL_USER=${SUDO_USER:-$USER}
HOME_DIR=$(eval echo ~$ACTUAL_USER)

echo -e "${GREEN}Setting up for user: $ACTUAL_USER${NC}"

# Update system
echo -e "${YELLOW}Updating system...${NC}"
apt-get update && apt-get upgrade -y

# Install required packages
echo -e "${YELLOW}Installing required packages...${NC}"
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    ufw \
    git

# Install Docker
echo -e "${YELLOW}Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker $ACTUAL_USER
    systemctl enable docker
    systemctl start docker
    echo -e "${GREEN}Docker installed successfully${NC}"
else
    echo -e "${GREEN}Docker already installed${NC}"
fi

# Install Docker Compose plugin
echo -e "${YELLOW}Installing Docker Compose...${NC}"
apt-get install -y docker-compose-plugin

# Install Tailscale
echo -e "${YELLOW}Installing Tailscale...${NC}"
if ! command -v tailscale &> /dev/null; then
    curl -fsSL https://tailscale.com/install.sh | sh
    echo -e "${GREEN}Tailscale installed successfully${NC}"
else
    echo -e "${GREEN}Tailscale already installed${NC}"
fi

# Configure firewall - BLOCK all public access
echo -e "${YELLOW}Configuring firewall (blocking public access)...${NC}"
ufw default deny incoming
ufw default allow outgoing

# Allow SSH only (you'll access via Tailscale after setup)
ufw allow ssh

# Allow Tailscale interface
ufw allow in on tailscale0

# Enable firewall
ufw --force enable

echo -e "${GREEN}Firewall configured - only SSH and Tailscale allowed${NC}"

# Create app directory
APP_DIR="$HOME_DIR/finance-tracker"
echo -e "${YELLOW}Creating app directory at $APP_DIR...${NC}"
mkdir -p $APP_DIR
mkdir -p $APP_DIR/data
chown -R $ACTUAL_USER:$ACTUAL_USER $APP_DIR

# Create a helper script to start Tailscale
cat > $APP_DIR/start-tailscale.sh << 'EOF'
#!/bin/bash
echo "Starting Tailscale..."
echo "You'll need to authenticate via the URL provided."
sudo tailscale up
echo ""
echo "Your Tailscale IP:"
tailscale ip -4
EOF
chmod +x $APP_DIR/start-tailscale.sh

# Create a helper script to deploy the app
cat > $APP_DIR/deploy.sh << 'EOF'
#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Building and starting Finance Tracker..."
docker compose down 2>/dev/null || true
docker compose build --no-cache
docker compose up -d

echo ""
echo "Finance Tracker is running!"
echo "Access it at: http://$(tailscale ip -4):8000"
echo ""
echo "To view logs: docker compose logs -f"
EOF
chmod +x $APP_DIR/deploy.sh

echo ""
echo "=========================================="
echo -e "${GREEN}  Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start Tailscale and authenticate:"
echo "   cd $APP_DIR && ./start-tailscale.sh"
echo ""
echo "2. Copy your app files to: $APP_DIR"
echo "   (Dockerfile, docker-compose.yml, backend/, frontend/)"
echo ""
echo "3. Deploy the app:"
echo "   cd $APP_DIR && ./deploy.sh"
echo ""
echo "4. Install Tailscale on your phone/laptop:"
echo "   https://tailscale.com/download"
echo ""
echo "5. Access your app via Tailscale IP (shown after step 1)"
echo ""
echo -e "${YELLOW}IMPORTANT: After Tailscale is working, disable SSH:${NC}"
echo "   sudo ufw delete allow ssh"
echo ""
