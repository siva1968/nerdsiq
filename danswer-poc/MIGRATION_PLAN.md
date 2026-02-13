# Migration Plan: NerdsIQ Custom → Danswer

## Migration Overview

**Goal:** Replace custom FastAPI/Qdrant/WordPress RAG system with Danswer enterprise search platform.

**Timeline:** 1-2 weeks (assuming POC approved)

**Risk Level:** Medium (parallel running period mitigates risk)

## Phase 1: Pre-Migration Preparation (2 days)

### 1.1 Data Inventory & Backup
```powershell
# Export conversation history
cd d:\dev\nerdsiq\backend
python scripts/export_conversations.py --output migration_backup/conversations.json

# Backup current indexed documents
python scripts/export_document_metadata.py --output migration_backup/documents.json

# Backup user accounts
python scripts/export_users.py --output migration_backup/users.json

# Archive database
copy nerdsiq.db migration_backup/nerdsiq.db.backup

# Document current settings
python scripts/export_config.py --output migration_backup/config.json
```

**Create export scripts if they don't exist:**
- Export all conversation threads with timestamps
- Export user credentials (for re-creation in Danswer)
- Export document indexing settings (chunk size, overlap, etc.)
- Export analytics/metrics for baseline comparison

### 1.2 Production Environment Setup
```bash
# On DigitalOcean droplet
cd /opt
git clone https://github.com/danswer-ai/danswer.git danswer-prod
cd danswer-prod

# Copy production docker-compose
# (with security hardening, resource limits, backup volumes)
cp docker-compose.prod.yml docker-compose.yml

# Configure environment
cp .env.example .env
nano .env  # Add production secrets
```

**Key production configurations:**
- SSL/TLS certificates (Let's Encrypt)
- Production database credentials (strong passwords)
- OpenAI API key (same as current)
- CORS origins (atiserve.com)
- Backup schedules (daily PostgreSQL dumps, Qdrant snapshots)
- Monitoring/alerting setup
- Resource limits (memory, CPU)

### 1.3 User Communication
**Email to NerdsToGo team:**
- Announce upcoming migration
- Explain benefits (better search, more features, easier maintenance)
- Timeline and parallel running period
- No action required from users
- Feedback channel setup

## Phase 2: Deployment & Configuration (2 days)

### 2.1 Deploy Danswer to Production
```bash
# Start services
docker-compose up -d

# Verify all containers healthy
docker-compose ps
docker-compose logs -f

# Initialize admin account
docker-compose exec api_server python scripts/create_admin.py \
  --email admin@nerdstoqgo.com \
  --password <secure-password>
```

### 2.2 Configure Google Drive Connector
1. **In Danswer Admin UI:**
   - Navigate to Connectors → Add Connector → Google Drive
   - Use existing service account JSON from current system: 
     `/opt/nerdsiq/backend/credentials/google-service-account.json`
   - Configure folder ID: `YOUR_GOOGLE_DRIVE_FOLDER_ID`
   - File type filters: `.pdf, .docx, .txt, .md, .xlsx`
   - Sync frequency: Every 6 hours (match current webhook schedule)
   - Enable "Auto-index on change" if available

2. **Run initial indexing:**
   - Click "Index Now"
   - Monitor indexing progress (expect 20-40 minutes for initial sync)
   - Verify document count matches current system

3. **Optimize RAG settings:**
   ```
   Chunk size: 500 tokens (match current system)
   Chunk overlap: 50 tokens
   Top-k retrieval: 5 documents
   Reranking: Enable (Danswer's default reranker)
   ```

### 2.3 Create User Accounts
```bash
# Import users from backup
docker-compose exec api_server python scripts/import_users.py \
  --input /opt/nerdsiq/migration_backup/users.json

# Or manually create (5 users total):
# admin@nerdstoqgo.com
# user1@nerdstoqgo.com
# user2@nerdstoqgo.com
# etc.
```

### 2.4 Customize Branding
In Danswer Admin → Settings:
- **App Name:** "NerdsIQ"
- **Logo:** Upload NerdsToGo logo
- **Primary Color:** `#0047AC` (NerdsIQ blue)
- **Accent Color:** `#FFD301` (NerdsIQ yellow)
- **Welcome Message:** "Ask me anything about NerdsToGo policies, procedures, and services!"

### 2.5 Configure System Prompt
In Danswer Admin → Personas:
```
You are NerdsIQ, an AI assistant for NerdsToGo employees. 

Your role:
- Answer questions about company policies, procedures, and technical documentation
- Provide accurate information with source citations
- Maintain a professional yet friendly tone
- If you don't know something, say so clearly
- Never make up information

When answering:
- Always cite your sources
- If multiple sources conflict, note the conflict
- Prioritize the most recent documentation
- Use bullet points for clarity when appropriate
```

## Phase 3: Parallel Running & Validation (5 days)

### 3.1 Setup Parallel Access
**Option A: Separate URL**
- Current system: `https://www.atiserve.com/ntg` (unchanged)
- New system: `https://beta.atiserve.com/ntg` or `https://danswer.atiserve.com`
- Users can test both

**Option B: Feature Flag in WordPress**
- Add toggle in WordPress admin: "Use new NerdsIQ (beta)"
- Users opt-in to try Danswer
- Easy rollback if issues

### 3.2 Validation Testing
**Week 1 checklist (run daily):**

**Answer Quality Test (10 queries):**
```
Test queries:
1. "What are NerdsToGo's business hours?"
2. "How do I submit a PTO request?"
3. "What's included in the Premium service plan?"
4. "Compare Nerds on Call vs. Nerds on Site"
5. "What's the escalation procedure for angry customers?"
6. "How do I access the VPN?"
7. "What are the hardware warranty policies?"
8. "Explain the franchise training process"
9. "What's the commission structure for sales?"
10. "How do I update customer information in the system?"

For each query:
- [ ] Run in both systems
- [ ] Compare answer accuracy
- [ ] Compare source citations
- [ ] Compare response time
- [ ] Note any quality differences
```

**Performance Monitoring:**
```bash
# Monitor Docker resource usage
docker stats

# Check response times
curl -w "@curl-format.txt" -o /dev/null -s https://danswer.atiserve.com/api/health

# Review error logs
docker-compose logs api_server | grep ERROR
docker-compose logs background | grep ERROR
```

**User Feedback Collection:**
- Add feedback form in Danswer UI
- Daily check-in with 2-3 users
- Track any issues or complaints
- Compare to baseline satisfaction with current system

### 3.3 Issue Tracking
Document any problems in `issues.md`:
```markdown
| Date | Issue | Severity | Status | Resolution |
|------|-------|----------|--------|------------|
| 2/10 | Slow indexing on large PDFs | Low | Open | Increase worker count |
| 2/11 | Citation link 404 on cached docs | High | Fixed | Cache invalidation |
```

## Phase 4: WordPress Integration Decision (1 day)

### Option A: Iframe Embed (Simplest)
```php
// In WordPress plugin
<iframe 
  src="https://danswer.atiserve.com" 
  width="100%" 
  height="600px"
  style="border: none;"
  allow="clipboard-write"
></iframe>
```

**Pros:**
- Zero custom code
- Full Danswer UI features
- Auto-updates

**Cons:**
- Less customization
- iframe limitations (full-screen, etc.)

### Option B: API Wrapper (More Control)
Keep WordPress widget UI, call Danswer API:
```php
// WordPress AJAX handler
function nerdsiq_query() {
  $question = sanitize_text_field($_POST['question']);
  
  $response = wp_remote_post('https://danswer.atiserve.com/api/query', [
    'headers' => [
      'Authorization' => 'Bearer ' . get_option('danswer_api_token'),
      'Content-Type' => 'application/json'
    ],
    'body' => json_encode(['question' => $question])
  ]);
  
  wp_send_json_success(json_decode($response['body']));
}
```

**Pros:**
- Maintain current NerdsIQ branding
- Custom UI control

**Cons:**
- More code to maintain
- Must keep up with Danswer API changes

### Option C: Standalone (Recommended)
**Retire WordPress integration entirely:**
- Direct users to `https://nerdsiq.atiserve.com` (Danswer UI)
- Update internal links/bookmarks
- Archive WordPress plugin

**Pros:**
- Zero maintenance
- Full feature access
- Simpler architecture

**Cons:**
- Loses atiserve.com URL integration
- Separate authentication (can use SSO)

**Recommendation:** Start with Option C (standalone). If business requires WordPress integration, implement Option A (iframe) as it's trivial and low-maintenance.

## Phase 5: Cutover (1 day)

### 5.1 Final Validation
```bash
# Health check
curl https://danswer.atiserve.com/api/health

# Verify all documents indexed
# Expected count: ~XXX documents

# Verify all users can log in

# Run final answer quality test
python tests/compare_answers.py --old-system --new-system
```

### 5.2 Execute Cutover
**If standalone approach:**
```nginx
# Update nginx config on atiserve.com
location /ntg {
  return 301 https://nerdsiq.atiserve.com$request_uri;
}
```

**If iframe approach:**
```php
// Update WordPress plugin to point to Danswer
update_option('nerdsiq_backend_url', 'https://danswer.atiserve.com');
```

### 5.3 Shutdown Old System
```bash
# Stop FastAPI backend
sudo systemctl stop nerdsiq

# Stop Qdrant
docker-compose -f /opt/nerdsiq/docker-compose.yml down

# Keep data for 30 days before deletion
mv /opt/nerdsiq /opt/nerdsiq-archived-YYYY-MM-DD
```

### 5.4 Post-Cutover Monitoring
**Week 1 after cutover:**
- Daily check error logs
- Monitor user feedback
- Track usage metrics
- Compare to pre-migration baseline

**Rollback procedure (if critical issues):**
```bash
# Restart old system
cd /opt/nerdsiq
sudo systemctl start nerdsiq
docker-compose up -d

# Revert nginx/WordPress config
# Notify users of temporary rollback
```

## Phase 6: Cleanup & Documentation (1 day)

### 6.1 Archive Old System
```bash
# Create archive
cd /opt
tar -czf nerdsiq-custom-v1-archive-$(date +%Y%m%d).tar.gz nerdsiq-archived/

# Upload to backup storage
rclone copy nerdsiq-custom-v1-archive-*.tar.gz remote:backups/

# Remove from server (after 30 days)
rm -rf /opt/nerdsiq-archived
```

### 6.2 Update Documentation
- **User guide:** How to access Danswer NerdsIQ
- **Admin guide:** How to manage connectors, users, settings
- **Troubleshooting:** Common issues and solutions
- **Architecture diagram:** New system overview

### 6.3 Update Monitoring
- Configure uptime monitoring (UptimeRobot, etc.)
- Set up alerts for Danswer downtime
- Configure backup verification (daily PostgreSQL dumps)
- Set up log aggregation if needed

### 6.4 Stakeholder Communication
**Email to NerdsToGo team:**
- Migration complete
- New URL/access method
- Summary of improvements
- Support contact

**Email to IT/management:**
- Technical migration summary
- Cost savings (maintenance time)
- Feature improvements
- Ongoing support plan

## Rollback Plan

**If critical issues arise during parallel running:**
1. Keep old system running (no change for users)
2. Debug Danswer issues in isolation
3. Extend parallel running period
4. Re-evaluate decision if issues can't be resolved

**If issues arise after cutover:**
1. Follow rollback procedure (see 5.4)
2. Investigate root cause
3. Fix in staging environment
4. Re-attempt migration when stable

**Rollback deadline:** 48 hours after cutover (after that, data divergence makes rollback complex)

## Success Metrics

**Technical:**
- [ ] All documents indexed successfully
- [ ] 99%+ uptime in first month
- [ ] Response time < 5 seconds (95th percentile)
- [ ] Zero data loss
- [ ] Backup/restore tested and validated

**User Satisfaction:**
- [ ] ≥ 80% user approval in feedback survey
- [ ] ≤ 5 support tickets in first month
- [ ] Usage metrics equal or exceed pre-migration
- [ ] Answer quality rated ≥ current system

**Business:**
- [ ] Maintenance time reduced by ≥ 50%
- [ ] Feature set expanded (analytics, multi-source, etc.)
- [ ] Scalability improved (can add more users without code changes)
- [ ] Total cost of ownership reduced

## Timeline Summary

| Phase | Duration | Key Activities |
|-------|----------|----------------|
| **Preparation** | 2 days | Backup data, set up production environment |
| **Deployment** | 2 days | Deploy Danswer, configure connectors, create users |
| **Parallel Running** | 5 days | Validation testing, user feedback, issue resolution |
| **Integration** | 1 day | Implement WordPress integration (if needed) |
| **Cutover** | 1 day | Execute migration, shutdown old system |
| **Cleanup** | 1 day | Archive, document, communicate |
| **TOTAL** | **~2 weeks** | From prep to full migration |

## Post-Migration Maintenance

**Weekly:**
- Review usage analytics
- Check for connector errors
- Monitor system health

**Monthly:**
- Update Docker images (security patches)
- Review user feedback
- Optimize performance if needed

**Quarterly:**
- Evaluate new Danswer features
- Review and update system prompts
- Assess whether to add new connectors

**Annually:**
- Full system audit
- Disaster recovery test
- Cost/benefit analysis

## Support Resources

**During migration:**
- **Primary contact:** [Your name/email]
- **Backup contact:** [Backup person]
- **Escalation:** Danswer Slack community

**Post-migration:**
- **User support:** [Support email/channel]
- **Admin support:** [Admin contact]
- **Vendor support:** Danswer GitHub issues, Slack

---

**Migration Plan Approval:**

**Approved by:** _________________  
**Date:** _________________  
**Go/No-Go Decision:** ☐ Approved  ☐ Deferred  ☐ Rejected  
**Notes:** _______________________________________________
