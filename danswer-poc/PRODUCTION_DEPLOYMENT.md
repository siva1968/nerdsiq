# Production Deployment Guide - NerdsIQ Onyx

**Status:** Ready for Live Deployment  
**Date:** February 15, 2026

## ✅ Pre-Deployment Checklist

### 1. Security Configuration
- [x] Authentication enabled (`AUTH_TYPE=basic`)
- [x] Secure secrets generated (SECRET_KEY, NEXTAUTH_SECRET)
- [x] Strong database password set
- [x] HTTPS configured via Cloudflare Tunnel
- [x] Cookie security enabled
- [ ] Admin user created (see step 3 below)
- [ ] Default admin password changed

### 2. System Configuration  
- [x] Indexed documents only mode enabled
- [x] Source citations enabled
- [x] Logout functionality enabled
- [x] Production branding applied
- [x] Session timeout configured (24 hours)
- [ ] Email notifications configured (optional)
- [ ] Google Drive connector configured

### 3. Infrastructure
- [x] Docker containers configured
- [x] Cloudflare Tunnel configured
- [x] Domain: https://onyx.getinstantleads.in
- [x] Reverse proxy (nginx) configured
- [ ] Backup strategy implemented
- [ ] Monitoring alerts configured

---

## 🚀 Deployment Steps

### Step 1: Stop Current Services

```bash
cd /home/prasad/Documents/dev/NERDSIQ/nerdsiq/danswer-poc
sudo docker compose -f docker-compose-onyx.yml down
```

### Step 2: Backup Current Data

```bash
# Backup PostgreSQL database
sudo docker exec onyx-postgres pg_dump -U postgres postgres > backup_$(date +%Y%m%d).sql

# Backup vector database
sudo docker exec onyx-index tar -czf /tmp/vespa-backup.tar.gz /opt/vespa/var
sudo docker cp onyx-index:/tmp/vespa-backup.tar.gz ./vespa_backup_$(date +%Y%m%d).tar.gz

# Backup environment
cp .env .env.backup_$(date +%Y%m%d)
```

### Step 3: Deploy with Production Configuration

```bash
# Start all services
sudo docker compose -f docker-compose-onyx.yml up -d

# Wait for services to be healthy (2-3 minutes)
watch -n 5 'sudo docker ps --filter "name=onyx" --format "table {{.Names}}\t{{.Status}}"'
```

### Step 4: Create Admin User

```bash
# Access the API container
sudo docker exec -it onyx-api bash

# Inside container, create admin user
python -m alembic revision --autogenerate -m "create_admin"

# Or use the following API call after services are up:
```

Create admin user via API:
```bash
curl -X POST https://onyx.getinstantleads.in/api/manage/admin/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@nerdsiq.com",
    "password": "ChangeThisPassword123!",
    "is_admin": true,
    "full_name": "NerdsIQ Admin"
  }'
```

### Step 5: Configure System Prompt

1. **Access Admin UI:** https://onyx.getinstantleads.in
2. **Login** with admin credentials
3. **Navigate to:** Admin → Personas
4. **Create Default Persona** with this system prompt:

```
You are NerdsIQ, an AI assistant for NerdsToGo employees.

CRITICAL - INDEXED DOCUMENTS ONLY:
1. You can ONLY answer questions using information from the provided document context below
2. If information is NOT in the context, say: "I don't have that information in our indexed documents. Please check with your manager or contact IT support."
3. NEVER use your general knowledge or training data - ONLY use the provided context
4. NEVER make assumptions or infer information not explicitly stated in the context
5. NEVER access external sources, internet, or tools

SOURCE TRANSPARENCY:
- ALWAYS cite your sources with document names and links
- If multiple documents have relevant information, cite all of them
- Show exact quotes when possible using quotation marks

RESPONSE FORMAT:
- Be helpful and professional
- Use numbered lists for procedures and steps
- Use **bold** for key terms and important points
- Keep answers concise but complete

WHEN INFORMATION IS MISSING:
- Clearly state what information is available and what isn't
- Suggest who to contact (manager, IT, HR)
- Never fill gaps with general knowledge

Context from indexed documents:
{context}

Previous conversation:
{history}
```

5. **Save** and set as default for all users

### Step 6: Configure Google Drive Connector

1. In Admin UI: **Admin → Connectors → Add Connector**
2. Select **Google Drive**
3. Upload service account: `/opt/nerdsiq/backend/credentials/google-service-account.json`
4. Configure:
   - **Folder ID:** Your Google Drive folder ID
   - **File types:** `.pdf, .docx, .txt, .md, .xlsx`
   - **Sync frequency:** Every 6 hours
   - **Auto-index:** Enabled
5. Click **Index Now** for initial sync

### Step 7: Verification Tests

**Test 1: Authentication**
```bash
# Should redirect to login
curl -I https://onyx.getinstantleads.in

# Should return 401 without auth
curl https://onyx.getinstantleads.in/api/manage/users
```

**Test 2: Login/Logout**
- Access https://onyx.getinstantleads.in
- Login with admin credentials
- Verify dashboard loads
- Click logout - should redirect to login page (no 500 error)

**Test 3: Indexed Documents Only**
- Ask: "What is the capital of France?"
- Expected: "I don't have that information in our indexed documents..."

**Test 4: Document Search**
- Ask: "What are our company policies?"
- Expected: Answer with source citations from Google Drive docs

**Test 5: Source Citations**
- Verify all answers include document links
- Click a citation link - should open the source document

---

## 🔐 Security Best Practices

### Immediate Actions
1. **Change Admin Password** after first login
2. **Create individual user accounts** - don't share admin credentials
3. **Save backup** of `.env` file securely (contains secrets)
4. **Enable MFA** if supported in future updates

### Regular Maintenance
- **Weekly:** Review access logs for suspicious activity
- **Monthly:** Rotate secrets (SECRET_KEY, NEXTAUTH_SECRET)
- **Quarterly:** Review user permissions
- **Before updates:** Backup database and configuration

### Environment Variables Security
**DO NOT** commit `.env` to version control. Current secrets:
- ✅ Stored only on server
- ✅ Accessible only to authorized users
- ✅ Backed up securely

---

## 📊 Monitoring & Alerts

### Health Checks

```bash
# Quick health check
curl https://onyx.getinstantleads.in/api/health

# Container status
sudo docker ps --filter "name=onyx" --format "table {{.Names}}\t{{.Status}}"

# View logs
sudo docker logs onyx-api --tail 100
sudo docker logs onyx-web --tail 100
```

### Key Metrics to Monitor
- **API Response Time** (< 2 seconds)
- **Document Index Size** (check growth)
- **Memory Usage** (< 16GB total)
- **Disk Space** (PostgreSQL + Vespa)
- **Failed Login Attempts**

### Set Up Alerts (Recommended)
1. **Cloudflare Analytics** - track uptime
2. **Docker health checks** - auto-restart on failure
3. **Disk space alerts** - notify at 80% usage
4. **Log aggregation** - centralize error logs

---

## 🔄 Backup & Recovery

### Automated Backup Script

Create `/opt/backups/onyx-backup.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/onyx"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
sudo docker exec onyx-postgres pg_dump -U postgres postgres | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup Vespa index
sudo docker exec onyx-index tar -czf /tmp/vespa.tar.gz /opt/vespa/var
sudo docker cp onyx-index:/tmp/vespa.tar.gz $BACKUP_DIR/vespa_$DATE.tar.gz

# Backup configuration
cp /home/prasad/Documents/dev/NERDSIQ/nerdsiq/danswer-poc/.env $BACKUP_DIR/env_$DATE

# Keep only last 7 days
find $BACKUP_DIR -name "db_*" -mtime +7 -delete
find $BACKUP_DIR -name "vespa_*" -mtime +7 -delete

echo "Backup completed: $DATE"
```

Add to crontab:
```bash
# Run daily at 2 AM
0 2 * * * /opt/backups/onyx-backup.sh >> /var/log/onyx-backup.log 2>&1
```

### Recovery Procedure

**Database Recovery:**
```bash
# Stop services
sudo docker compose -f docker-compose-onyx.yml down

# Restore database
cat backup_20260215.sql | sudo docker exec -i onyx-postgres psql -U postgres postgres

# Restart services
sudo docker compose -f docker-compose-onyx.yml up -d
```

---

## 👥 User Management

### Create Regular Users

**Via Admin UI:**
1. Admin → Users → Add User
2. Enter email and temporary password
3. Assign to appropriate groups
4. User changes password on first login

**Via API:**
```bash
curl -X POST https://onyx.getinstantleads.in/api/manage/admin/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{
    "email": "user@nerdsiq.com",
    "password": "TempPassword123!",
    "is_admin": false,
    "full_name": "Employee Name"
  }'
```

### User Roles
- **Admin:** Full system access, can manage users and connectors
- **User:** Can search documents and chat, no admin access

---

## 🔍 Troubleshooting

### Issue: 403 Errors on Admin Endpoints
**Solution:** Check `AUTH_TYPE=basic` in `.env`, restart containers

### Issue: Logout Returns 500 Error
**Solution:** Verify `NEXTAUTH_SECRET` is set properly, check web server logs

### Issue: Documents Not Indexing
**Solution:** 
1. Check Google Drive connector status in Admin UI
2. Verify service account has proper permissions
3. Review indexing logs: `sudo docker logs onyx-background`

### Issue: Slow Query Response
**Solution:**
1. Check document count - may need index optimization
2. Review `ENABLE_RERANKING_REAL_TIME_FLOW` setting
3. Increase `GEN_AI_MAX_OUTPUT_TOKENS` if needed

### Issue: Container Unhealthy
**Solution:**
```bash
# Check specific container logs
sudo docker logs onyx-web --tail 50

# Restart unhealthy container
sudo docker restart onyx-web

# Full restart if needed
sudo docker compose -f docker-compose-onyx.yml restart
```

---

## 📞 Support Contacts

**Technical Issues:**
- Internal: [Your IT Team]
- Onyx Support: https://docs.onyx.app
- GitHub Issues: https://github.com/onyxdotapp/onyx

**Urgent (System Down):**
1. Check Cloudflare status
2. Verify Docker containers: `sudo docker ps`
3. Check system resources: `htop`
4. Review logs: `sudo docker logs onyx-api`

**Business Questions:**
- [Your business contact]

---

## 📝 Change Log

### February 15, 2026 - Production Deployment
- ✅ Enabled authentication (AUTH_TYPE=basic)
- ✅ Generated secure production secrets
- ✅ Fixed logout functionality
- ✅ Applied "indexed documents only" configuration
- ✅ Production branding applied
- ✅ HTTPS via Cloudflare Tunnel
- 📋 Pending: Initial admin user creation
- 📋 Pending: Google Drive connector configuration
- 📋 Pending: System prompt configuration

---

## 🎯 Success Criteria

### Day 1 (Today)
- [x] Authentication enabled
- [x] Secure secrets in place
- [ ] Admin user created
- [ ] System prompt configured
- [ ] Google Drive connected
- [ ] Initial document indexing complete

### Week 1
- [ ] All users migrated from old system
- [ ] Verify all documents indexed
- [ ] User training completed
- [ ] Monitor for issues

### Month 1
- [ ] User feedback collected
- [ ] Performance optimizations applied
- [ ] Backup/restore tested
- [ ] Old system decommissioned

---

## ✅ Go-Live Checklist

Print this and check off before going live:

```
□ All services healthy (docker ps)
□ Admin user created and password changed
□ System prompt configured
□ Google Drive connector active
□ Documents indexed and verified
□ Authentication tested (login/logout)
□ "Indexed only" mode verified
□ Source citations working
□ Backup script configured
□ Monitoring alerts configured
□ Team trained on new system
□ Support contacts documented
□ Rollback plan ready
□ Client approval received
```

---

**Ready to deploy?** Follow the steps in order and check each item off.

For questions, review [SYSTEM_PROMPT_INDEXED_ONLY.md](SYSTEM_PROMPT_INDEXED_ONLY.md) and [README.md](README.md).
