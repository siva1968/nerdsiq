# NerdsIQ Production Deployment Guide

## Overview

This guide covers deploying NerdsIQ to a DigitalOcean droplet with:
- **Backend API**: FastAPI + PostgreSQL + Qdrant
- **Access**: Cloudflare Tunnel (no exposed ports)
- **Frontend**: WordPress plugin on WPEngine (www.atiserve.com)

## Prerequisites

- DigitalOcean account
- Cloudflare account with Zero Trust enabled
- Domain configured in Cloudflare (e.g., `api.nerdsiq.com` or use tunnel subdomain)
- GitHub repository access
- Google Cloud project with Drive API enabled

---

## Part 1: Server Setup (DigitalOcean)

### 1.1 Create Droplet

1. **Log into DigitalOcean** → Create → Droplets
2. **Choose image**: Ubuntu 22.04 LTS
3. **Choose plan**: Basic → Regular → $24/mo (4GB RAM, 2 vCPUs, 80GB SSD)
4. **Datacenter**: Choose closest to users (e.g., NYC1 for US East)
5. **Authentication**: SSH keys (recommended) or password
6. **Hostname**: `nerdsiq-prod`
7. Click **Create Droplet**

### 1.2 Initial Server Setup

```bash
# SSH into server
ssh root@YOUR_DROPLET_IP

# Update system
apt update && apt upgrade -y

# Install required packages
apt install -y \
    git \
    curl \
    wget \
    unzip \
    htop \
    ufw \
    fail2ban

# Create app user
adduser --disabled-password --gecos "" nerdsiq
usermod -aG sudo nerdsiq

# Setup firewall (only SSH initially)
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw enable

# Switch to app user
su - nerdsiq
```

### 1.3 Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker nerdsiq

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version

# Log out and back in for group changes
exit
su - nerdsiq
```

---

## Part 2: Application Deployment

### 2.1 Clone Repository

```bash
# Create app directory
sudo mkdir -p /opt/nerdsiq
sudo chown nerdsiq:nerdsiq /opt/nerdsiq

# Clone repository
cd /opt/nerdsiq
git clone https://github.com/siva1968/nerdsiq.git .
```

### 2.2 Configure Environment

```bash
# Copy production environment template
cp backend/.env.prod.example backend/.env.prod

# Edit with production values
nano backend/.env.prod
```

**Required values in `.env.prod`:**

```env
# Application
APP_ENV=production
SECRET_KEY=<generate: openssl rand -hex 16>
DEBUG=false

# Database
POSTGRES_USER=nerdsiq
POSTGRES_PASSWORD=<generate: openssl rand -hex 24>
POSTGRES_DB=nerdsiq

# OpenAI
OPENAI_API_KEY=sk-proj-your-production-key
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=nerdsiq_docs

# Google Drive
GOOGLE_OAUTH_CLIENT_FILE=./credentials/oauth-client.json
GOOGLE_OAUTH_TOKEN_FILE=./credentials/oauth-token.json
GOOGLE_DRIVE_FOLDER_ID=1zWBVbJWMWahOgIZq-uztI-_A21j2gZgk

# JWT
JWT_SECRET_KEY=<generate: openssl rand -hex 16>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# WordPress SSO
WP_AUTH_SECRET=<must match WordPress plugin setting>

# CORS
CORS_ORIGINS=https://www.atiserve.com

# Rate Limiting
RATE_LIMIT_PER_MINUTE=30

# Logging
LOG_LEVEL=INFO
```

### 2.3 Setup Google OAuth Credentials

```bash
# Create credentials directory
mkdir -p backend/credentials

# Option A: Copy from local machine
# On your LOCAL machine:
scp backend/credentials/oauth-client.json nerdsiq@YOUR_DROPLET_IP:/opt/nerdsiq/backend/credentials/
scp backend/credentials/oauth-token.json nerdsiq@YOUR_DROPLET_IP:/opt/nerdsiq/backend/credentials/

# Option B: Re-authenticate on server
# (Requires browser access - use SSH tunnel or copy token after local auth)
```

### 2.4 Build and Start Services

```bash
cd /opt/nerdsiq

# Build production images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f api
```

### 2.5 Initialize Database

```bash
# Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Create admin user
docker-compose -f docker-compose.prod.yml exec api python scripts/create_user.py \
    --email admin@nerdstogofranchise.com \
    --password "SecurePassword123!" \
    --name "Admin User"

# Index documents
docker-compose -f docker-compose.prod.yml exec api python scripts/index_documents.py
```

### 2.6 Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"1.0.0","qdrant":"connected","database":"connected"}
```

---

## Part 3: Cloudflare Tunnel Setup

### 3.1 Create Tunnel in Cloudflare

1. **Log into Cloudflare** → Zero Trust → Networks → Tunnels
2. Click **Create a tunnel**
3. **Name**: `nerdsiq-prod`
4. **Choose environment**: Docker
5. Copy the **tunnel token** (starts with `eyJ...`)

### 3.2 Configure Tunnel on Server

```bash
# Add tunnel token to environment
echo "CLOUDFLARE_TUNNEL_TOKEN=eyJ..." >> backend/.env.prod

# Restart to apply
docker-compose -f docker-compose.prod.yml up -d cloudflared
```

### 3.3 Configure Public Hostname

In Cloudflare Zero Trust dashboard:

1. Go to **Tunnels** → `nerdsiq-prod` → **Public Hostname**
2. Add hostname:
   - **Subdomain**: `api` (or your choice)
   - **Domain**: `nerdsiq.com` (or your domain)
   - **Service**: `http://api:8000`
3. Save

Your API is now accessible at: `https://api.nerdsiq.com`

---

## Part 4: WordPress Plugin Configuration

### 4.1 Install Plugin on WPEngine

1. **Download plugin**: Zip the `wordpress-plugin/nerdsiq-chatbot/` folder
2. **Upload to WordPress**: Plugins → Add New → Upload Plugin
3. **Activate** the plugin

### 4.2 Configure Plugin Settings

Go to **Settings → NerdsIQ**:

| Setting | Value |
|---------|-------|
| API URL | `https://api.nerdsiq.com` (your tunnel URL) |
| WP Auth Secret | Same as `WP_AUTH_SECRET` in `.env.prod` |
| Enable Chat Widget | ✅ Checked |
| Widget Position | Bottom Right |

### 4.3 Add Widget to Pages

The widget auto-loads on all pages. To restrict to specific pages, edit the plugin settings or use:

```php
// In theme's functions.php
add_filter('nerdsiq_show_widget', function($show) {
    // Only show on specific page
    return is_page('ntg');
});
```

---

## Part 5: Monitoring & Maintenance

### 5.1 Setup Log Rotation

```bash
# Create logrotate config
sudo nano /etc/logrotate.d/nerdsiq

# Add:
/opt/nerdsiq/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 nerdsiq nerdsiq
}
```

### 5.2 Setup Automatic Backups

```bash
# Create backup script
nano /opt/nerdsiq/scripts/backup.sh

# Add:
#!/bin/bash
BACKUP_DIR="/opt/nerdsiq/backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup PostgreSQL
docker-compose -f /opt/nerdsiq/docker-compose.prod.yml exec -T postgres \
    pg_dump -U nerdsiq nerdsiq > "$BACKUP_DIR/postgres.sql"

# Backup Qdrant
docker cp nerdsiq-qdrant:/qdrant/storage "$BACKUP_DIR/qdrant"

# Compress
tar -czf "$BACKUP_DIR.tar.gz" -C "$(dirname $BACKUP_DIR)" "$(basename $BACKUP_DIR)"
rm -rf "$BACKUP_DIR"

# Keep only last 7 days
find /opt/nerdsiq/backups -name "*.tar.gz" -mtime +7 -delete

echo "Backup complete: $BACKUP_DIR.tar.gz"
```

```bash
# Make executable
chmod +x /opt/nerdsiq/scripts/backup.sh

# Add to crontab (daily at 2am)
crontab -e
# Add line:
0 2 * * * /opt/nerdsiq/scripts/backup.sh >> /opt/nerdsiq/logs/backup.log 2>&1
```

### 5.3 Health Monitoring

```bash
# Create health check script
nano /opt/nerdsiq/scripts/healthcheck.sh

# Add:
#!/bin/bash
HEALTH=$(curl -s http://localhost:8000/health)
STATUS=$(echo $HEALTH | jq -r '.status')

if [ "$STATUS" != "healthy" ]; then
    echo "$(date): API unhealthy - restarting..."
    docker-compose -f /opt/nerdsiq/docker-compose.prod.yml restart api
fi
```

```bash
# Add to crontab (every 5 minutes)
*/5 * * * * /opt/nerdsiq/scripts/healthcheck.sh >> /opt/nerdsiq/logs/healthcheck.log 2>&1
```

---

## Part 6: Updates & Maintenance

### 6.1 Deploy Updates

```bash
cd /opt/nerdsiq

# Pull latest code
git pull origin main

# Rebuild and restart API
docker-compose -f docker-compose.prod.yml up -d --build api

# Run any new migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Re-index documents if needed
docker-compose -f docker-compose.prod.yml exec api python scripts/index_documents.py
```

### 6.2 View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f api

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 api
```

### 6.3 Restart Services

```bash
# Restart all
docker-compose -f docker-compose.prod.yml restart

# Restart specific service
docker-compose -f docker-compose.prod.yml restart api
```

### 6.4 Stop Everything

```bash
docker-compose -f docker-compose.prod.yml down
```

---

## Part 7: Troubleshooting

### API Not Responding

```bash
# Check if container is running
docker ps | grep nerdsiq-api

# Check logs
docker-compose -f docker-compose.prod.yml logs --tail=50 api

# Restart API
docker-compose -f docker-compose.prod.yml restart api
```

### Database Connection Issues

```bash
# Check PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres pg_isready

# Check connection from API container
docker-compose -f docker-compose.prod.yml exec api python -c "
from app.database import engine
print(engine.url)
"
```

### Qdrant Issues

```bash
# Check Qdrant health
curl http://localhost:6333/health

# Check collection
curl http://localhost:6333/collections/nerdsiq_docs
```

### Google Drive Sync Issues

```bash
# Re-authenticate (requires token refresh)
docker-compose -f docker-compose.prod.yml exec api python scripts/authenticate_drive.py

# Re-index documents
docker-compose -f docker-compose.prod.yml exec api python scripts/index_documents.py
```

### Cloudflare Tunnel Issues

```bash
# Check tunnel status
docker-compose -f docker-compose.prod.yml logs cloudflared

# Restart tunnel
docker-compose -f docker-compose.prod.yml restart cloudflared
```

---

## Quick Reference

### URLs

| Service | URL |
|---------|-----|
| Production API | `https://api.nerdsiq.com` (your tunnel URL) |
| WordPress | `https://www.atiserve.com/ntg` |
| Health Check | `https://api.nerdsiq.com/health` |
| API Docs | `https://api.nerdsiq.com/docs` |

### Commands Cheat Sheet

```bash
# Start production
docker-compose -f docker-compose.prod.yml up -d

# Stop production
docker-compose -f docker-compose.prod.yml down

# View logs
docker-compose -f docker-compose.prod.yml logs -f api

# Rebuild after code changes
docker-compose -f docker-compose.prod.yml up -d --build api

# Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Create backup
./scripts/backup.sh

# Health check
curl http://localhost:8000/health
```

### Important Files

| File | Purpose |
|------|---------|
| `/opt/nerdsiq/docker-compose.prod.yml` | Production Docker config |
| `/opt/nerdsiq/backend/.env.prod` | Production secrets |
| `/opt/nerdsiq/backend/credentials/` | Google OAuth tokens |
| `/opt/nerdsiq/backups/` | Database backups |
| `/opt/nerdsiq/logs/` | Application logs |

---

## Security Checklist

- [ ] SSH key authentication only (disable password auth)
- [ ] UFW firewall enabled
- [ ] Fail2ban installed and configured
- [ ] Strong passwords in `.env.prod`
- [ ] CORS restricted to production domain
- [ ] Google credentials secured (chmod 600)
- [ ] Regular backups configured
- [ ] Health monitoring enabled
- [ ] Cloudflare WAF rules configured

---

## Support

For issues, check:
1. API logs: `docker-compose logs api`
2. Health endpoint: `/health`
3. GitHub Issues: https://github.com/siva1968/nerdsiq/issues

---

*Last updated: February 3, 2026*
