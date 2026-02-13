# Danswer POC - NerdsIQ Evaluation

## Overview
This proof-of-concept evaluates **Danswer** as a replacement for the custom NerdsIQ RAG implementation. Danswer is an open-source enterprise search and Q&A platform with built-in document connectors, advanced RAG capabilities, and polished UI.

## Quick Start

### 1. Prerequisites
- Docker Desktop installed and running
- OpenAI API key
- 8GB RAM minimum (16GB recommended)
- Ports 3000, 8080, 5432, 6379, 6333 available

### 2. Setup Steps

```powershell
# Navigate to POC directory
cd d:\dev\nerdsiq\danswer-poc

# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
notepad .env

# Start all services (first time will download images ~2-3GB)
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f
```

### 3. Access Danswer

- **Web UI:** http://localhost:3000
- **API Docs:** http://localhost:8080/docs
- **Qdrant Dashboard:** http://localhost:6333/dashboard

**First-time login:**
- Email: `admin@example.com`
- Password: `admin` (change immediately)

### 4. Connect Google Drive

1. In Danswer UI, go to **Admin > Connectors**
2. Click **Add Connector** → Select **Google Drive**
3. Choose authentication method:
   - **Option A: OAuth** (recommended for POC)
     - Click "Connect with Google"
     - Authorize access
   - **Option B: Service Account** (for production)
     - Upload your `google-service-account.json`
     - Specify folder ID: `YOUR_FOLDER_ID`
4. Configure sync settings:
   - File types: `.pdf, .docx, .txt, .md`
   - Update frequency: `Every 6 hours`
   - Include folders: Specify NerdsToGo folder
5. Click **Index Now** to start initial sync

### 5. Test the System

**Index Status:**
- Go to **Admin > Indexing Status**
- Watch documents being processed
- Verify all expected files are indexed

**Ask Questions:**
- Navigate to main chat interface
- Ask: "What are NerdsToGo's hours of operation?"
- Verify answers include source citations
- Check relevance and accuracy

**Test Features:**
- **Multi-document synthesis:** Ask questions requiring info from multiple docs
- **Source citations:** Click citation links to verify source documents
- **Conversation history:** Check if context is maintained across messages
- **Filters:** Test document filters and date range searches

### 6. Shutdown

```powershell
# Stop all services (preserves data)
docker-compose down

# Stop and remove all data (clean slate)
docker-compose down -v
```

## Key Features to Evaluate

### ✅ Out-of-the-Box Features
- **Document Connectors:**
  - Google Drive (native support, no webhook setup needed)
  - 30+ other connectors (Confluence, SharePoint, Notion, etc.)
  - Automatic sync with configurable frequency
  
- **Advanced Search:**
  - Semantic search with re-ranking
  - Keyword + semantic hybrid search
  - Filtering by source, date, document type
  
- **Answer Quality:**
  - Multi-document synthesis
  - Accurate source citations with snippets
  - Confidence scoring
  - "I don't know" when appropriate
  
- **User Experience:**
  - Clean, polished UI
  - Conversation history
  - Real-time streaming responses
  - Mobile-responsive
  
- **Admin Features:**
  - Usage analytics dashboard
  - Document management interface
  - User feedback tracking
  - Model configuration (GPT-4, GPT-3.5, etc.)
  - Custom prompts and personas

### 🔍 Comparison to Current NerdsIQ

| Feature | Current NerdsIQ | Danswer |
|---------|----------------|---------|
| **Setup Complexity** | Custom FastAPI + Qdrant + WordPress | Docker Compose (one command) |
| **Document Sync** | Custom webhook + renewal script | Native connector, auto-sync |
| **Source Citations** | Manual extraction from metadata | Built-in with snippets |
| **Admin UI** | WordPress plugin pages | Full-featured admin dashboard |
| **User Management** | Custom JWT + SQLAlchemy | Built-in with roles/permissions |
| **Analytics** | Basic custom tracking | Comprehensive usage analytics |
| **Maintenance** | ~2-3 days/month | Minimal (updates via Docker) |
| **Scalability** | Manual optimization needed | Production-ready architecture |
| **Feature Updates** | Custom development | Community releases |
| **Branding** | Custom CSS (NerdsIQ colors) | Configurable (logo, colors, name) |
| **Integration** | Custom WordPress widget | API + iframe or standalone |

## Evaluation Checklist

### Functionality (30 min)
- [ ] Successfully indexed Google Drive documents
- [ ] Ask 10 test questions, compare answers to current NerdsIQ
- [ ] Verify source citations are accurate
- [ ] Test conversation context retention
- [ ] Check answer quality on edge cases

### User Experience (15 min)
- [ ] Evaluate UI intuitiveness vs WordPress widget
- [ ] Test mobile responsiveness
- [ ] Check loading times and response speed
- [ ] Assess search/filter capabilities

### Admin Experience (20 min)
- [ ] Review analytics dashboard
- [ ] Test document management interface
- [ ] Configure custom prompt/persona
- [ ] Review user management features
- [ ] Check connector configuration ease

### Technical Assessment (30 min)
- [ ] Review Docker resource usage (RAM, CPU)
- [ ] Check logs for errors or warnings
- [ ] Evaluate monitoring/observability
- [ ] Assess backup/restore capabilities
- [ ] Review API documentation completeness

### Integration Planning (30 min)
- [ ] Determine if WordPress integration is still needed
- [ ] If yes: Test iframe embedding in WordPress
- [ ] If yes: Evaluate API for custom widget
- [ ] Plan user authentication approach
- [ ] Assess SSO/SAML requirements for future

## Expected Outcomes

### ✅ If Danswer Meets Requirements
- **Answer quality** equals or exceeds current system
- **Setup/maintenance** significantly simpler
- **Feature set** more comprehensive
- **UI/UX** acceptable for internal users
- **Integration** feasible with existing WordPress site

**Recommendation:** Proceed with migration

### ⚠️ If Danswer Has Gaps
Document specific gaps:
- Missing features: _______________
- Performance issues: _______________
- Integration challenges: _______________

**Options:**
1. Contribute to Danswer (it's open-source)
2. Hybrid: Danswer backend + custom frontend
3. Evaluate alternatives (Onyx, OpenSearch, Haystack)
4. Continue with custom build (with clear justification)

## Performance Benchmarks

Test and document:
```
Query: "What are NerdsToGo's hours?"
- Current NerdsIQ: ___ seconds
- Danswer POC: ___ seconds

Query: "Compare service plans" (multi-doc)
- Current NerdsIQ: ___ seconds
- Danswer POC: ___ seconds

Document sync time:
- Current NerdsIQ: ___ minutes
- Danswer POC: ___ minutes

Resource usage (idle):
- Current NerdsIQ: ___ MB RAM
- Danswer POC: ___ MB RAM
```

## Next Steps After POC

### If Proceeding with Migration:
1. **Data Export:** Export conversation history from current system
2. **Production Setup:** 
   - Configure production docker-compose with security hardening
   - Set up SSL/TLS termination
   - Configure backups (PostgreSQL + Qdrant)
3. **WordPress Integration:**
   - Option A: Embed Danswer UI via iframe
   - Option B: Build lightweight API wrapper widget
   - Option C: Retire WordPress integration, use Danswer standalone
4. **Migration:**
   - Run both systems in parallel for 1 week
   - Validate answer quality parity
   - Cutover DNS/routing
5. **Decommission:** Archive old NerdsIQ codebase

### Migration Resources Needed:
- **Time:** 1-2 days for production deployment
- **Testing:** 3-5 days parallel running
- **Documentation:** 1 day user guides
- **Total:** ~1 week for full migration

## Troubleshooting

**Services won't start:**
```powershell
# Check Docker is running
docker ps

# Check port conflicts
netstat -ano | findstr "3000 8080 5432"

# View logs
docker-compose logs api_server
docker-compose logs postgres
```

**Can't connect to Google Drive:**
- Verify API enabled in Google Cloud Console
- Check service account has folder access
- Review connector logs in Danswer Admin UI

**Slow indexing:**
- Increase `NUM_INDEXING_WORKERS` in `.env`
- Check OpenAI API rate limits
- Monitor Qdrant memory usage

**Poor answer quality:**
- Adjust chunk size in connector settings
- Try different LLM models (GPT-4 vs GPT-3.5)
- Customize system prompt in Admin > Settings

## Support & Documentation

- **Danswer Docs:** https://docs.danswer.dev
- **GitHub Issues:** https://github.com/danswer-ai/danswer
- **Slack Community:** https://join.slack.com/t/danswer/...
- **Architecture Overview:** https://docs.danswer.dev/architecture

## Decision Criteria Summary

**Proceed with Danswer if:**
- ✅ Answer quality ≥ current system
- ✅ Setup time < 4 hours
- ✅ Monthly maintenance < 4 hours
- ✅ Resource usage acceptable (< 4GB RAM)
- ✅ Integration path clear

**Stick with custom build if:**
- ❌ Critical features missing
- ❌ Performance significantly worse
- ❌ Integration requires major rework
- ❌ Vendor lock-in concerns

---

**POC Completion Date:** _________________  
**Evaluator:** _________________  
**Decision:** ☐ Migrate to Danswer  ☐ Continue Custom  ☐ Needs More Evaluation  
**Notes:** _______________________________________________
