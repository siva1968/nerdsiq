# NerdsIQ - AI Coding Agent Instructions

## Project Context
NerdsIQ is a RAG-based AI chatbot for NerdsToGo that answers questions from Google Drive documents. Deployed to WordPress at www.atiserve.com/ntg for 1-5 internal users.

**Architecture:** FastAPI backend + Qdrant vector DB + WordPress plugin frontend  
**Key Flow:** User query → Embed question → Search Qdrant → Build context → GPT-4o-mini → Return answer + sources

## Tech Stack & Dependencies

### Backend (Python 3.11+)
- **FastAPI 0.109+** with async/await everywhere
- **SQLAlchemy 2.0+** for users/conversations/messages
- **LangChain 0.1.x** for RAG pipeline (ConversationBufferWindowMemory, k=5)
- **Qdrant** (Docker): 1536-dim vectors (text-embedding-3-small), cosine distance
- **JWT auth** (python-jose): 1-hour tokens, bcrypt passwords
- **Google Drive API v3** for document source

### Frontend (WordPress Plugin)
- **PHP 8.0+** using WordPress hooks/actions
- **Vanilla JS + jQuery** (WordPress bundled), no frameworks
- **Custom CSS** with BEM-like naming, `nerdsiq-*` prefixes

### Infrastructure
- **DigitalOcean** Ubuntu 22.04 droplet, Nginx reverse proxy, Let's Encrypt SSL
- **Docker** for Qdrant only

## Critical Patterns

### 1. RAG Pipeline (backend/app/services/rag_service.py)
```python
# 7-step process:
# 1. Embed user question (text-embedding-3-small)
# 2. Qdrant search top 5 chunks
# 3. Build context from payloads: {text, source_url, source_name, chunk_index}
# 4. Send to GPT-4o-mini with last 5 exchanges (ConversationBufferWindowMemory)
# 5. Extract source URLs from retrieved docs
# 6. Return answer + sources
# 7. Cache query (hash lowercase/trimmed, 60min TTL)

# Chunking config (tunable per document type):
CHUNK_SIZE = 500      # tokens - increase for technical docs, decrease for FAQs
CHUNK_OVERLAP = 50    # tokens - 10% overlap recommended minimum
TOP_K = 5             # retrieval count - balance relevance vs context length
```

### 2. API Structure
```
POST /api/v1/auth/login          → JWT token (1hr expiry)
POST /api/v1/chat/query          → RAG answer + sources (requires Bearer token)
GET  /api/v1/chat/history        → Session message history
GET  /health                     → Status check (no auth)
```

### 3. WordPress Integration
```php
// ALL AJAX endpoints require:
add_action('wp_ajax_nerdsiq_query', [$this, 'handler']);
add_action('wp_ajax_nopriv_nerdsiq_query', [$this, 'handler']); // For logged-out

// Security checklist:
wp_verify_nonce($_POST['nonce'], 'nerdsiq_nonce');
$input = sanitize_text_field($_POST['input']);
echo esc_html($output);
wp_send_json_success(['data' => $result]);
```

### 4. Type Hints & Validation
```python
# Use everywhere - Pydantic for API schemas, SQLAlchemy models with types
async def query_rag(
    question: str,
    session_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question required")
```

## Directory Structure
```
backend/
  app/
    main.py                    # FastAPI app, register routers here
    config.py                  # Pydantic Settings (load env vars)
    database.py                # SQLAlchemy engine/session
    models/                    # User, Conversation, Message SQLAlchemy models
    schemas/                   # Pydantic request/response schemas
    routers/                   # auth.py, chat.py, documents.py, health.py
    services/                  # rag_service, cache_service, drive_service, embedding_service
  scripts/                     # index_documents.py, create_user.py, renew_webhook.py
  tests/                       # pytest tests (>70% coverage target)
wordpress-plugin/
  nerdsiq-chatbot/
    includes/                  # class-nerdsiq-api, class-nerdsiq-auth, class-nerdsiq-widget
    assets/css/                # nerdsiq-style.css (BEM-like, CSS custom props)
    assets/js/                 # nerdsiq-chat.js (IIFE wrapped, async/await)
    templates/                 # chat-widget.php, login-form.php
```

## Local Development Setup

### Prerequisites
- Python 3.11+, Docker Desktop, Node.js (for WordPress dev if needed)
- VS Code with Python, Docker, and PHP extensions

### 1. Start Qdrant (Vector DB)
```powershell
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

### 2. Backend Setup
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env  # Then edit with your API keys
uvicorn app.main:app --reload --port 8000
```

### 3. Initialize Database & Index Documents
```powershell
# Create tables
alembic upgrade head
# Create first user
python scripts/create_user.py --email admin@example.com --password yourpass
# Index Google Drive documents
python scripts/index_documents.py
```

### 4. WordPress Plugin (Local Testing)
- Use Local by Flywheel or XAMPP
- Symlink/copy `wordpress-plugin/nerdsiq-chatbot/` to `wp-content/plugins/`
- Activate plugin, configure API URL in Settings → NerdsIQ

### Verify Setup
```powershell
# Health check
curl http://localhost:8000/health
# Test auth
curl -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"admin@example.com","password":"yourpass"}'
```

## DigitalOcean Deployment

### Server Setup (Ubuntu 22.04)
```bash
# Install dependencies
sudo apt update && sudo apt install -y python3.11 python3.11-venv nginx certbot python3-certbot-nginx docker.io
sudo systemctl enable docker && sudo systemctl start docker

# Clone and setup
git clone <repo> /opt/nerdsiq && cd /opt/nerdsiq/backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Configure production values
```

### Docker Compose (Qdrant + App)
```yaml
# docker-compose.yml
version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

volumes:
  qdrant_data:
```

### Systemd Service
```bash
# /etc/systemd/system/nerdsiq.service
[Unit]
Description=NerdsIQ FastAPI
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/nerdsiq/backend
Environment="PATH=/opt/nerdsiq/backend/venv/bin"
ExecStart=/opt/nerdsiq/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx Config
```nginx
# /etc/nginx/sites-available/nerdsiq
server {
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
# Then: sudo certbot --nginx -d api.yourdomain.com
```

### Deploy Commands
```bash
# Start services
docker-compose up -d
sudo systemctl start nerdsiq
sudo systemctl enable nerdsiq

# Update deployment
cd /opt/nerdsiq && git pull
source backend/venv/bin/activate
pip install -r backend/requirements.txt
alembic upgrade head
sudo systemctl restart nerdsiq
```

## Environment Variables Required
```env
OPENAI_API_KEY=sk-...              # GPT-4o-mini + text-embedding-3-small
DATABASE_URL=sqlite:///./nerdsiq.db
SECRET_KEY=<32-char-key>
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=nerdsiq_docs
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/credentials.json
GOOGLE_DRIVE_FOLDER_ID=1abc...
JWT_SECRET_KEY=<jwt-key>
CORS_ORIGINS=https://www.atiserve.com
RATE_LIMIT_PER_MINUTE=30
```

## Branding & UI
- **Colors:** `#0047AC` (primary blue), `#FFD301` (accent yellow)
- **Widget:** Bottom-right, 380px wide × 500px max height
- **Mobile:** Full width, 70vh height
- **Name:** Always "NerdsIQ" (capital I, capital Q)

## Common Tasks

### Adding API Endpoint
1. Define Pydantic schema in `schemas/`
2. Implement logic in `services/`
3. Create router endpoint in `routers/`
4. Register router in `main.py`: `app.include_router(router, prefix="/api/v1")`
5. Add test in `tests/`

### WordPress AJAX Action
1. Hook: `add_action('wp_ajax_*', [$this, 'method'])`
2. Verify nonce, sanitize inputs
3. Make API call to FastAPI backend
4. Return: `wp_send_json_success()` or `wp_send_json_error()`
5. Add JS handler using `nerdsiq_ajax.ajax_url`

### Document Sync
- Auto-sync via Google Drive webhook (renewal script runs weekly)
- Manual: `python backend/scripts/index_documents.py`
- Cache auto-invalidates on document changes

## Security Checklist
- ✅ JWT tokens (1hr), bcrypt passwords, no secrets in code
- ✅ CORS restricted to www.atiserve.com only
- ✅ Rate limit: 30 req/min per user
- ✅ WordPress nonces for all AJAX
- ✅ Sanitize inputs (`sanitize_text_field`), escape outputs (`esc_html`)
- ✅ Never trust user input - validate with Pydantic/WordPress functions

## Performance Targets
- Response time: <5s (95th percentile)
- Cached queries: <1s
- Document sync: <15min after change
- Support 5 concurrent users

## Reference
See [docs/NerdsIQ_Developer_Prompt.md](../docs/NerdsIQ_Developer_Prompt.md) for complete specifications, code examples, and detailed implementation patterns.
