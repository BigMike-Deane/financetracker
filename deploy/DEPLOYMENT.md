# Finance Tracker - Secure Cloud Deployment Guide

This guide walks you through deploying Finance Tracker to a VPS with Tailscale for secure, private access.

## Overview

```
Your Phone  ──┐                    ┌── Finance Tracker
              ├── Tailscale VPN ───┤   (Docker on VPS)
Wife's Phone ─┘                    └── SQLite Database
```

- **No public URL** - The app is only accessible via Tailscale
- **Encrypted traffic** - All data travels through Tailscale's encrypted tunnel
- **Simple access** - Just install Tailscale app on your devices

---

## Step 1: Get a VPS

### Recommended: Hetzner Cloud (~$4.50/month)

1. Go to [Hetzner Cloud](https://www.hetzner.com/cloud)
2. Create an account
3. Create a new project
4. Add a server:
   - **Location:** Choose nearest to you (Ashburn for US East)
   - **Image:** Ubuntu 24.04
   - **Type:** CX22 (2 vCPU, 4GB RAM) - $4.50/month
   - **SSH Key:** Add your public SSH key (see below)
   - Click "Create & Buy Now"

### Alternative: DigitalOcean (~$6/month)

1. Go to [DigitalOcean](https://www.digitalocean.com)
2. Create a Droplet:
   - Ubuntu 24.04
   - Basic plan, $6/month (1GB RAM)
   - Choose datacenter region
   - Add SSH key

### Generate SSH Key (if you don't have one)

```bash
# On your local machine (Mac/Linux/WSL)
ssh-keygen -t ed25519 -C "your-email@example.com"

# View your public key to copy to VPS provider
cat ~/.ssh/id_ed25519.pub
```

---

## Step 2: Initial VPS Setup

### Connect to your VPS

```bash
ssh root@YOUR_VPS_IP
```

### Run the setup script

```bash
# Download and run setup script
curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/main/deploy/vps-setup.sh | sudo bash

# Or if you have the file locally:
chmod +x vps-setup.sh
sudo ./vps-setup.sh
```

This script:
- Installs Docker and Docker Compose
- Installs Tailscale
- Configures firewall (blocks public access)
- Creates app directory

---

## Step 3: Setup Tailscale

### On your VPS

```bash
cd ~/finance-tracker
./start-tailscale.sh
```

You'll see a URL like:
```
To authenticate, visit:
https://login.tailscale.com/a/abc123xyz
```

1. Open that URL in your browser
2. Sign in with Google, Microsoft, or email
3. Authorize the device

After authentication, note your Tailscale IP:
```bash
tailscale ip -4
# Example output: 100.100.100.100
```

### On your phone/laptop

1. Download Tailscale:
   - **iOS:** [App Store](https://apps.apple.com/app/tailscale/id1470499037)
   - **Android:** [Play Store](https://play.google.com/store/apps/details?id=com.tailscale.ipn)
   - **Mac/Windows:** [tailscale.com/download](https://tailscale.com/download)

2. Sign in with the **same account** you used on the VPS

3. Your devices are now on the same private network!

---

## Step 4: Deploy the App

### Option A: Copy files via SCP (Recommended)

From your local machine (where the code is):

```bash
# Create a zip of the project
cd /mnt/c/Users/bayer/finance_tracker
zip -r finance-tracker.zip . -x "node_modules/*" -x ".git/*" -x "data/*" -x "__pycache__/*"

# Copy to VPS (use Tailscale IP for security)
scp finance-tracker.zip root@YOUR_TAILSCALE_IP:~/finance-tracker/

# SSH into VPS and extract
ssh root@YOUR_TAILSCALE_IP
cd ~/finance-tracker
unzip finance-tracker.zip
```

### Option B: Git clone (if you push to a private repo)

```bash
ssh root@YOUR_TAILSCALE_IP
cd ~/finance-tracker
git clone https://github.com/YOUR_USERNAME/finance-tracker.git .
```

### Build and run

```bash
cd ~/finance-tracker
./deploy.sh
```

This builds the Docker image and starts the app.

---

## Step 5: Migrate Your Data

Your existing database has your SimpleFIN connection and transaction history. Copy it to the VPS:

```bash
# From your local machine
scp /mnt/c/Users/bayer/finance_tracker/data/finance.db root@YOUR_TAILSCALE_IP:~/finance-tracker/data/

# Restart the container to pick up the database
ssh root@YOUR_TAILSCALE_IP
cd ~/finance-tracker
docker compose restart
```

---

## Step 6: Access Your App

On any device with Tailscale installed and signed in:

```
http://YOUR_TAILSCALE_IP:8000
```

Example: `http://100.100.100.100:8000`

### Add to Home Screen (PWA)

**iPhone:**
1. Open Safari, go to `http://YOUR_TAILSCALE_IP:8000`
2. Tap Share button
3. Tap "Add to Home Screen"

**Android:**
1. Open Chrome, go to the URL
2. Tap menu (three dots)
3. Tap "Add to Home screen"

---

## Step 7: Lock Down SSH (Important!)

Once Tailscale is working, disable public SSH:

```bash
# SSH via Tailscale IP now
ssh root@YOUR_TAILSCALE_IP

# Remove public SSH access
sudo ufw delete allow ssh

# Verify only Tailscale is allowed
sudo ufw status
```

Now the VPS is **completely invisible** to the public internet.

---

## Maintenance

### View logs
```bash
cd ~/finance-tracker
docker compose logs -f
```

### Restart the app
```bash
cd ~/finance-tracker
docker compose restart
```

### Update the app
```bash
cd ~/finance-tracker
# Pull new code (if using git) or copy new files
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Backup your data
```bash
# Copy database to your local machine
scp root@YOUR_TAILSCALE_IP:~/finance-tracker/data/finance.db ./backup-$(date +%Y%m%d).db
```

---

## Sharing with Your Wife

1. Have her install Tailscale on her phone
2. Sign in with **the same Tailscale account** (or invite her to your Tailnet)
3. She can access the same URL: `http://YOUR_TAILSCALE_IP:8000`

### To invite her to your Tailnet (separate login):
1. Go to [Tailscale Admin Console](https://login.tailscale.com/admin)
2. Go to Users → Invite users
3. Enter her email
4. She signs up and her devices join your network

---

## Troubleshooting

### Can't connect to the app
1. Make sure Tailscale is running on your device
2. Check VPS: `docker compose ps` - container should be "Up"
3. Check logs: `docker compose logs`

### App is slow
- The CX22 (4GB RAM) should be plenty
- Check: `docker stats` for resource usage

### Database is empty after deploy
- Make sure you copied `data/finance.db` to the VPS
- Check file exists: `ls -la ~/finance-tracker/data/`

---

## Security Notes

1. **SimpleFIN credentials** are stored in the SQLite database
2. **Database is unencrypted** - the security comes from Tailscale isolation
3. **Backups** should be stored securely (encrypted drive, etc.)
4. **Tailscale account** is your security perimeter - use a strong password + 2FA
