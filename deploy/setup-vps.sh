#!/bin/bash
# Finance Tracker VPS Setup Script
# Run this on your VPS to set up the finance tracker

set -e

echo "=== Finance Tracker VPS Setup ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./setup-vps.sh)"
    exit 1
fi

# Configuration - UPDATE THESE
DOMAIN="finance.yourdomain.com"  # Your domain (or leave empty for Tailscale-only)
APP_USER="finance"               # User to run the app
APP_DIR="/opt/finance-tracker"   # Installation directory
USE_HTTPS="false"                # Set to "true" for Let's Encrypt SSL

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Installing dependencies...${NC}"
apt-get update
apt-get install -y python3 python3-pip python3-venv nginx git curl

# Create app user if doesn't exist
if ! id "$APP_USER" &>/dev/null; then
    echo -e "${GREEN}Creating app user...${NC}"
    useradd -r -m -s /bin/bash $APP_USER
fi

# Create app directory
echo -e "${GREEN}Setting up app directory...${NC}"
mkdir -p $APP_DIR
chown $APP_USER:$APP_USER $APP_DIR

# Clone or update the app (assumes you're copying files manually or from git)
echo -e "${YELLOW}Please copy your finance_tracker files to $APP_DIR${NC}"
echo "You can use: scp -r finance_tracker/* user@your-vps:$APP_DIR/"
read -p "Press Enter when files are copied..."

# Set up Python virtual environment
echo -e "${GREEN}Setting up Python environment...${NC}"
cd $APP_DIR
sudo -u $APP_USER python3 -m venv venv
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r backend/requirements.txt

# Create data directory
mkdir -p $APP_DIR/data
chown $APP_USER:$APP_USER $APP_DIR/data

# Create .env file if doesn't exist
if [ ! -f "$APP_DIR/.env" ]; then
    echo -e "${GREEN}Creating .env file...${NC}"
    cp $APP_DIR/.env.example $APP_DIR/.env

    # Generate random secret key
    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
    sed -i "s/generate-a-random-secret-key-here/$SECRET_KEY/" $APP_DIR/.env

    echo -e "${YELLOW}IMPORTANT: Edit $APP_DIR/.env to set:${NC}"
    echo "  - AUTH_USERNAME"
    echo "  - AUTH_PASSWORD"
    echo "  - TZ (your timezone)"
    echo "  - CORS_ORIGINS (your domain/Tailscale IP)"
fi

# Build frontend
echo -e "${GREEN}Building frontend...${NC}"
cd $APP_DIR/frontend

# Install Node.js if not present
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi

sudo -u $APP_USER npm install
sudo -u $APP_USER npm run build

# Create systemd service
echo -e "${GREEN}Creating systemd service...${NC}"
cat > /etc/systemd/system/finance-tracker.service << EOF
[Unit]
Description=Finance Tracker API
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$APP_DIR/backend
Environment=PATH=$APP_DIR/venv/bin
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable finance-tracker
systemctl start finance-tracker

# Set up nginx
echo -e "${GREEN}Configuring nginx...${NC}"
if [ "$USE_HTTPS" = "true" ] && [ -n "$DOMAIN" ]; then
    # Install certbot for Let's Encrypt
    apt-get install -y certbot python3-certbot-nginx

    # Create nginx config with SSL
    cat > /etc/nginx/sites-available/finance-tracker << EOF
server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    # Get SSL certificate
    certbot --nginx -d $DOMAIN --non-interactive --agree-tos -m admin@$DOMAIN
else
    # Simple config for Tailscale (HTTP only)
    cat > /etc/nginx/sites-available/finance-tracker << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
fi

# Enable nginx site
ln -sf /etc/nginx/sites-available/finance-tracker /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ""
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Edit $APP_DIR/.env with your settings"
echo "2. Restart the service: systemctl restart finance-tracker"
echo "3. Check status: systemctl status finance-tracker"
echo "4. View logs: journalctl -u finance-tracker -f"
echo ""
if [ "$USE_HTTPS" = "true" ]; then
    echo "Access your app at: https://$DOMAIN"
else
    echo "Access your app at: http://<your-tailscale-ip> or http://<your-vps-ip>"
    echo ""
    echo "For Tailscale setup:"
    echo "  curl -fsSL https://tailscale.com/install.sh | sh"
    echo "  tailscale up"
fi
