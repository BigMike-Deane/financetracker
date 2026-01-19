# Finance Tracker Deployment Guide

## Quick Start (VPS + Tailscale)

### Prerequisites
- VPS with Ubuntu 22.04+ (DigitalOcean, Linode, etc.)
- Tailscale account (free tier works)
- Domain name (optional, for public HTTPS access)

### 1. Set Up Tailscale on VPS

```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate and start
sudo tailscale up

# Note your Tailscale IP (100.x.x.x)
tailscale ip -4
```

### 2. Set Up Tailscale on Phone
- Install Tailscale from App Store/Play Store
- Sign in with same account
- Your phone can now access the VPS via Tailscale IP

### 3. Deploy Finance Tracker

#### Option A: Docker (Recommended)

```bash
# Clone/copy the project to your VPS
cd /opt
git clone <your-repo> finance-tracker
cd finance-tracker

# Copy and edit environment file
cp .env.example .env
nano .env
```

Edit `.env`:
```env
SECRET_KEY=<generate-random-string>
AUTH_USERNAME=your-username
AUTH_PASSWORD=your-secure-password
TZ=America/Chicago
CORS_ORIGINS=http://100.x.x.x:8000
```

```bash
# Build and run
docker-compose up -d --build

# Check status
docker-compose logs -f
```

#### Option B: Manual Setup

```bash
# Run setup script (as root)
sudo bash deploy/setup-vps.sh

# Edit config
sudo nano /opt/finance-tracker/.env

# Restart service
sudo systemctl restart finance-tracker
```

### 4. Access the App

From your phone (connected to Tailscale):
- Open browser to: `http://100.x.x.x:8000`
- Or with nginx: `http://100.x.x.x`
- Sign in with your AUTH_USERNAME/AUTH_PASSWORD

### 5. Install as PWA

**iOS:**
1. Open the app in Safari
2. Tap Share button
3. Select "Add to Home Screen"

**Android:**
1. Open in Chrome
2. Tap Menu (3 dots)
3. Select "Install app" or "Add to Home screen"

## Configuration Reference

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Random secret for sessions | `abc123...` |
| `AUTH_USERNAME` | Login username | `admin` |
| `AUTH_PASSWORD` | Login password | `secure-password` |
| `TZ` | Timezone for syncs | `America/Chicago` |
| `CORS_ORIGINS` | Allowed origins | `http://100.x.x.x:8000` |
| `DEBUG` | Debug mode | `false` |

### Useful Commands

```bash
# View logs
docker-compose logs -f
# or
sudo journalctl -u finance-tracker -f

# Restart service
docker-compose restart
# or
sudo systemctl restart finance-tracker

# Manual sync
curl -X POST http://localhost:8000/api/sync \
  -u username:password

# Check status
curl http://localhost:8000/api/institutions \
  -u username:password
```

## HTTPS Setup (Optional)

If you want HTTPS with a public domain:

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d finance.yourdomain.com

# Update .env
CORS_ORIGINS=https://finance.yourdomain.com
```

## Troubleshooting

### "AUTH_REQUIRED" error
- Check AUTH_USERNAME and AUTH_PASSWORD in .env
- Ensure credentials match what you're entering

### Sync not working
- Check logs: `docker-compose logs finance-tracker`
- Verify SimpleFIN token is valid
- Try manual sync from Settings page

### PWA not installable
- Must access via HTTPS or localhost
- Tailscale uses HTTP, so PWA install works differently
- On iOS Safari, you can still "Add to Home Screen"

### Can't connect from phone
- Ensure Tailscale is running on both VPS and phone
- Check VPS firewall allows port 8000
- Try: `curl http://100.x.x.x:8000` from phone terminal

## Backup

The SQLite database is stored in `data/finance.db`:

```bash
# Backup
cp data/finance.db data/finance.db.backup

# Or with Docker
docker cp finance-tracker:/app/data/finance.db ./backup/
```
