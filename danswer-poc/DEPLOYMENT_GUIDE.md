# Deployment Guide - Onyx with Logout Fix

This guide shows how to reproduce the NerdsIQ deployment with the logout bug fix on any new server.

## Prerequisites

- Ubuntu Server (22.04+ recommended)
- Docker and Docker Compose installed
- Git installed
- sudo access
- Domain with Cloudflare Tunnel (optional)

---

## Quick Deployment

```bash
# 1. Clone repository
git clone https://github.com/siva1968/nerdsiq.git
cd nerdsiq/danswer-poc

# 2. Build custom web container with logout fix
./build-custom-web.sh

# 3. Configure environment
cp .env.example .env
nano .env  # Edit with your settings

# 4. Start services
sudo docker compose -f docker-compose-onyx.yml up -d

# 5. Verify deployment
sudo docker ps
curl http://localhost:3100/health
```

---

## Detailed Steps

### 1. Initial Setup

```bash
# Clone repository
git clone https://github.com/siva1968/nerdsiq.git
cd nerdsiq/danswer-poc

# Verify files
ls -la
# Should see: docker-compose-onyx.yml, build-custom-web.sh, patches/
```

### 2. Build Custom Web Container

The custom web container includes fixes for the logout bug in Onyx v2.11.0.

```bash
# Run automated build script
chmod +x build-custom-web.sh
./build-custom-web.sh

# This will:
# - Clone Onyx v2.11.0 source
# - Apply logout patches
# - Build custom Docker image: onyx-web-custom:logout-fix
```

**Manual build** (if script fails):
```bash
cd ..
git clone --depth 1 --branch v2.11.0 https://github.com/onyx-dot-app/onyx.git onyx-source
cd onyx-source
git apply ../danswer-poc/patches/logout-route-fix.patch
git apply ../danswer-poc/patches/userss-header-filter-fix.patch
cd web
sudo docker build -t onyx-web-custom:logout-fix .
```

### 3. Configure Environment Variables

```bash
cd danswer-poc

# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env
```

**Critical settings:**
```env
# Authentication
AUTH_TYPE=basic
SECRET_KEY=<generate-with: openssl rand -base64 32>
NEXTAUTH_SECRET=<generate-with: openssl rand -base64 32>
NEXTAUTH_URL=https://your-domain.com

# Indexed-only mode (no external search)
DISABLE_LLM_CHOOSE_SEARCH=true
DISABLE_LLM_FILTER_EXTRACTION=true
DISABLE_LLM_CHUNK_FILTER=true

# OpenAI
OPENAI_API_KEY=sk-...

# UI Configuration
NEXT_PUBLIC_URL=https://your-domain.com
NEXT_PUBLIC_SHOW_CITATIONS=true
NEXT_PUBLIC_CLOUD_ENABLED=true
NEXT_PUBLIC_MODEL_SELECTION_ENABLED=false
DISABLE_AUTH_COOKIE_SECURE=true

# Domain
WEB_DOMAIN=https://your-domain.com
```

### 4. Configure System Prompt & Database Settings

**After first startup**, configure the AI persona:

```bash
# Access PostgreSQL
sudo docker exec -it onyx-postgres psql -U postgres -d postgres

# Run these SQL commands:
UPDATE persona SET 
  llm_relevance_filter = false,
  llm_filter_extraction = false,
  llm_model_provider_override = 'openai',
  llm_model_version_override = 'gpt-4o-mini'
WHERE id = 0;

-- Verify
SELECT id, name, llm_relevance_filter, llm_filter_extraction, 
       llm_model_version_override 
FROM persona WHERE id = 0;

\q
```

**System Prompt** (via Admin UI):
1. Go to https://your-domain.com/admin
2. Navigate to **Personas** → Edit "Assistant"
3. Paste prompt from [SYSTEM_PROMPT_INDEXED_ONLY.md](./SYSTEM_PROMPT_INDEXED_ONLY.md)

### 5. Start Services

```bash
# Start all containers
sudo docker compose -f docker-compose-onyx.yml up -d

# Wait for services to initialize (2-3 minutes)
sleep 120

# Check container status
sudo docker ps --filter name=onyx
```

**Expected containers:**
- onyx-web ✓ (using custom image)
- onyx-api ✓
- onyx-postgres ✓
- onyx-vespa ✓
- onyx-redis ✓
- onyx-minio ✓
- onyx-inference ✓
- onyx-indexing ✓
- onyx-background ✓
- onyx-nginx ✓

### 6. Configure Google Drive Connector

```bash
# Access admin UI
https://your-domain.com/admin

# Navigate to: Admin → Connectors → Google Drive
# 1. Upload service account JSON
# 2. Enter folder ID to index
# 3. Click "Create Connector"
# 4. Wait for indexing to complete
```

### 7. Verify Deployment

**Check services:**
```bash
# API health
curl http://localhost:8180/health

# Web health
curl http://localhost:3100/

# Check logs
sudo docker logs onyx-api --tail 50
sudo docker logs onyx-web --tail 50
```

**Test logout (most important!):**
```bash
# Should return 401 (not 500)
curl -v -X POST http://localhost:3100/auth/logout 2>&1 | grep HTTP

# Check for errors in logs
sudo docker logs onyx-web --tail 50 | grep -i "TypeError\|error"
# Should be empty (no connection header errors)
```

**Test document search:**
1. Login at https://your-domain.com/auth/login
2. Ask: "What are our company policies?"
3. Verify:
   - Shows "2 steps" or tool calling activity
   - Reads from Google Drive documents
   - Provides citations
4. Ask: "What is the capital of France?"
5. Verify: Says "I do not have that information in our indexed documents"

---

## Troubleshooting

### Logout Returns 500 Error

**Problem:** Custom web image not running

**Check:**
```bash
sudo docker ps --filter name=onyx-web --format "{{.Image}}"
```

**Should show:** `onyx-web-custom:logout-fix`

**If showing official image:**
```bash
# Rebuild custom image
cd danswer-poc
./build-custom-web.sh

# Recreate container
sudo docker compose -f docker-compose-onyx.yml up -d --force-recreate web_server
```

### Documents Not Being Retrieved

**Problem:** Filters preventing search

**Fix:**
```bash
sudo docker exec -it onyx-postgres psql -U postgres -d postgres
UPDATE persona SET llm_relevance_filter = false, llm_filter_extraction = false WHERE id = 0;
\q
sudo docker compose -f docker-compose-onyx.yml restart api_server
```

### Vespa Index Empty

**Problem:** Documents in PostgreSQL but not Vespa

**Fix:**
```bash
sudo docker exec -it onyx-postgres psql -U postgres -d postgres
UPDATE document SET last_synced = NULL LIMIT 100;
\q
# Wait 10-15 minutes for reindexing
```

---

## File Structure

```
nerdsiq/danswer-poc/
├── docker-compose-onyx.yml        # Main deployment configuration
├── .env                           # Environment variables
├── build-custom-web.sh           # Automated build script
├── patches/
│   ├── README.md                 # Patch documentation
│   ├── logout-route-fix.patch   # Cookie deletion fix
│   └── userss-header-filter-fix.patch  # Header filtering fix
├── LOGOUT_FIX_SUMMARY.md         # Technical documentation
├── PRODUCTION_READINESS_CHECKLIST.md  # Deployment checklist
└── SYSTEM_PROMPT_INDEXED_ONLY.md # Configuration guide
```

---

## Maintenance

### Updating Onyx

When a new version is released:

1. **Check if logout is fixed upstream:**
   ```bash
   # Check release notes
   https://github.com/onyx-dot-app/onyx/releases
   ```

2. **If fixed, use official image:**
   ```yaml
   # In docker-compose-onyx.yml
   web_server:
     image: onyxdotapp/onyx-web-server:v2.XX.X
   ```

3. **If not fixed, rebuild patches:**
   ```bash
   git clone --depth 1 --branch v2.XX.X https://github.com/onyx-dot-app/onyx.git onyx-new
   cd onyx-new
   git apply ../danswer-poc/patches/logout-route-fix.patch
   git apply ../danswer-poc/patches/userss-header-filter-fix.patch
   cd web
   sudo docker build -t onyx-web-custom:v2.XX.X-logout-fix .
   ```

### Backup

**Critical files to backup:**
```bash
# Environment configuration
cp .env .env.backup

# Database
sudo docker exec onyx-postgres pg_dump -U postgres postgres > backup-$(date +%Y%m%d).sql

# Custom image (optional)
sudo docker save onyx-web-custom:logout-fix -o onyx-web-custom-logout-fix.tar
```

---

## Production Checklist

- [ ] Custom web image built successfully
- [ ] All containers running and healthy
- [ ] Environment variables configured
- [ ] System prompt applied
- [ ] Database filters disabled (llm_relevance_filter = false)
- [ ] Google Drive connector configured
- [ ] Documents indexed (check Vespa count)
- [ ] Logout tested (returns 401, no errors in logs)
- [ ] Document search working (retrieves and cites sources)
- [ ] General knowledge blocked (returns "I don't have that information")
- [ ] HTTPS configured (Cloudflare Tunnel or nginx)
- [ ] Authentication enabled (AUTH_TYPE=basic)
- [ ] Signup disabled (via nginx)

---

## Support

**Documentation:**
- [LOGOUT_FIX_SUMMARY.md](./LOGOUT_FIX_SUMMARY.md)
- [PRODUCTION_READINESS_CHECKLIST.md](./PRODUCTION_READINESS_CHECKLIST.md)
- [SYSTEM_PROMPT_INDEXED_ONLY.md](./SYSTEM_PROMPT_INDEXED_ONLY.md)

**Upstream:**
- Onyx GitHub: https://github.com/onyx-dot-app/onyx
- Onyx Docs: https://docs.onyx.app

**Issues:**
- Create issue at: https://github.com/siva1968/nerdsiq/issues
