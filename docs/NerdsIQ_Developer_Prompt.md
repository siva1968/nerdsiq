# NerdsIQ Development System Prompt
# Use this prompt in your code editor (Cursor, VS Code + Copilot, Claude, etc.)
# Copy everything below the line into your editor's system prompt or .cursorrules file

---

# NerdsIQ - AI Knowledge Assistant

You are an expert developer building NerdsIQ, a RAG-based AI chatbot for NerdsToGo. Follow these specifications exactly.

## Project Overview

**Client:** NerdsToGo (Lyla Narvaez)
**Purpose:** Internal AI knowledge assistant that answers questions from Google Drive documents
**Users:** 1-5 internal staff members
**Deployment:** WordPress site (www.atiserve.com/ntg)

## Technology Stack

### Backend (Python)
- **Framework:** FastAPI 0.109+
- **Python:** 3.11+
- **ORM:** SQLAlchemy 2.0+
- **Auth:** python-jose (JWT), passlib (bcrypt)
- **AI/ML:** LangChain 0.1.x, OpenAI API
- **Vector DB:** Qdrant (self-hosted Docker)
- **Document Source:** Google Drive API v3

### Frontend (WordPress Plugin)
- **Language:** PHP 8.0+
- **JavaScript:** Vanilla JS with jQuery (WordPress bundled)
- **Styling:** Custom CSS (no frameworks)
- **Integration:** WordPress AJAX API

### Infrastructure
- **Server:** DigitalOcean 4GB Droplet (Ubuntu 22.04)
- **Reverse Proxy:** Nginx
- **SSL:** Let's Encrypt
- **Container:** Docker for Qdrant

## Project Structure

```
nerdsiq/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Pydantic settings
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py          # User model
│   │   │   └── conversation.py  # Conversation, Message models
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py          # Auth request/response schemas
│   │   │   └── chat.py          # Chat request/response schemas
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py          # /api/v1/auth/*
│   │   │   ├── chat.py          # /api/v1/chat/*
│   │   │   ├── documents.py     # /api/v1/docs/*
│   │   │   └── health.py        # /health
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── rag_service.py   # LangChain RAG implementation
│   │   │   ├── cache_service.py # Query caching
│   │   │   ├── drive_service.py # Google Drive integration
│   │   │   └── embedding_service.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── helpers.py
│   ├── scripts/
│   │   ├── index_documents.py   # Initial indexing
│   │   ├── create_user.py       # User creation
│   │   └── renew_webhook.py     # Webhook renewal
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_auth.py
│   │   └── test_chat.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic/                 # DB migrations
├── wordpress-plugin/
│   └── nerdsiq-chatbot/
│       ├── nerdsiq-chatbot.php  # Main plugin file
│       ├── includes/
│       │   ├── class-nerdsiq-api.php
│       │   ├── class-nerdsiq-auth.php
│       │   └── class-nerdsiq-widget.php
│       ├── assets/
│       │   ├── css/
│       │   │   └── nerdsiq-style.css
│       │   └── js/
│       │       └── nerdsiq-chat.js
│       ├── templates/
│       │   ├── chat-widget.php
│       │   └── login-form.php
│       └── admin/
│           └── settings-page.php
├── docker-compose.yml
├── .env.example
└── README.md
```

## Coding Standards

### Python (Backend)

```python
# Use type hints everywhere
def get_user(user_id: int) -> User | None:
    pass

# Use async for I/O operations
async def query_rag(question: str, session_id: str) -> dict:
    pass

# Pydantic for all request/response schemas
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    session_id: str

# Use dependency injection
@router.post("/query")
async def query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pass

# Error handling with HTTPException
if not user:
    raise HTTPException(status_code=404, detail="User not found")

# Use environment variables via config
from app.config import settings
api_key = settings.openai_api_key
```

### PHP (WordPress Plugin)

```php
<?php
// Always check for direct access
if (!defined('ABSPATH')) exit;

// Use proper WordPress hooks
add_action('wp_enqueue_scripts', [$this, 'enqueue_assets']);
add_action('wp_ajax_nerdsiq_query', [$this, 'ajax_query']);
add_action('wp_ajax_nopriv_nerdsiq_query', [$this, 'ajax_query']);

// Sanitize all inputs
$email = sanitize_email($_POST['email']);
$question = sanitize_text_field($_POST['question']);

// Use nonces for security
wp_verify_nonce($_POST['nonce'], 'nerdsiq_nonce');

// Escape all outputs
echo esc_html($message);
echo esc_url($link);
echo esc_attr($attribute);

// Use WordPress options API
update_option('nerdsiq_api_url', $api_url);
$api_url = get_option('nerdsiq_api_url');

// Return JSON responses properly
wp_send_json_success(['answer' => $answer, 'sources' => $sources]);
wp_send_json_error(['message' => 'Invalid request']);
```

### JavaScript

```javascript
// Use strict mode
'use strict';

// Wrap in IIFE for WordPress
(function($) {
    // Use const/let, never var
    const NerdsIQ = {
        token: localStorage.getItem('nerdsiq_token'),
        
        init: function() {
            this.bindEvents();
        },
        
        // Always escape HTML
        escapeHtml: function(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        },
        
        // Use async/await for AJAX when possible
        handleQuery: async function(question) {
            try {
                const response = await $.ajax({
                    url: nerdsiq_ajax.ajax_url,
                    type: 'POST',
                    data: {
                        action: 'nerdsiq_query',
                        nonce: nerdsiq_ajax.nonce,
                        question: question
                    }
                });
                return response;
            } catch (error) {
                console.error('Query failed:', error);
                throw error;
            }
        }
    };
    
    $(document).ready(function() {
        NerdsIQ.init();
    });
})(jQuery);
```

### CSS

```css
/* Use CSS custom properties for theming */
:root {
    --nerdsiq-blue: #0047AC;
    --nerdsiq-yellow: #FFD301;
    --nerdsiq-white: #FFFFFF;
    --nerdsiq-gray: #F5F5F5;
    --nerdsiq-dark: #333333;
}

/* Prefix all classes to avoid conflicts */
.nerdsiq-widget { }
.nerdsiq-header { }
.nerdsiq-message { }

/* Use BEM-like naming */
.nerdsiq-message { }
.nerdsiq-message.user { }
.nerdsiq-message.assistant { }
.nerdsiq-message__content { }
.nerdsiq-message__sources { }

/* Mobile-first responsive */
.nerdsiq-widget {
    width: 100%;
}

@media (min-width: 480px) {
    .nerdsiq-widget {
        width: 380px;
    }
}
```

## API Endpoints

### Authentication
```
POST /api/v1/auth/login
Body: { "username": "email", "password": "pass" }
Response: { "access_token": "jwt...", "token_type": "bearer" }

POST /api/v1/auth/refresh
Headers: Authorization: Bearer <token>
Response: { "access_token": "new_jwt...", "token_type": "bearer" }
```

### Chat
```
POST /api/v1/chat/query
Headers: Authorization: Bearer <token>
Body: { "question": "How do I create an invoice?", "session_id": "sess_123" }
Response: {
    "answer": "To create an invoice...",
    "sources": ["https://docs.google.com/..."],
    "session_id": "sess_123"
}

GET /api/v1/chat/history?session_id=sess_123
Headers: Authorization: Bearer <token>
Response: {
    "messages": [
        { "role": "user", "content": "...", "created_at": "..." },
        { "role": "assistant", "content": "...", "sources": [...] }
    ]
}
```

### Health
```
GET /health
Response: { "status": "healthy", "version": "1.0.0", "qdrant": "connected" }
```

## Database Models

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);
```

### Conversations Table
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    session_id VARCHAR(100) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_session ON conversations(session_id);
```

### Messages Table
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER REFERENCES conversations(id),
    role VARCHAR(20) NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    sources TEXT, -- JSON array of URLs
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Qdrant Collection

```python
# Collection: nerdsiq_docs
# Vector size: 1536 (OpenAI text-embedding-3-small)
# Distance: Cosine

payload_schema = {
    "text": str,           # Chunk text content
    "source_id": str,      # Google Drive file ID
    "source_name": str,    # Document name
    "source_url": str,     # Google Drive web view URL
    "chunk_index": int     # Position in document
}
```

## Key Implementation Details

### RAG Pipeline
1. User question → Generate embedding (text-embedding-3-small)
2. Query Qdrant for top 5 similar chunks
3. Build context from retrieved chunks
4. Send to GPT-4o-mini with custom prompt
5. Extract and format source URLs
6. Store in session memory (last 5 exchanges)
7. Cache frequent queries (1-hour TTL)

### Document Chunking
- Chunk size: 500 tokens
- Overlap: 50 tokens
- Store with metadata: source_url, source_name, chunk_index

### Session Memory
- Use LangChain ConversationBufferWindowMemory
- Keep last 5 exchanges (k=5)
- Clear on logout or 1-hour inactivity

### Query Caching
- Hash query (lowercase, trimmed) as cache key
- TTL: 60 minutes
- Invalidate all cache when documents update

## Environment Variables

```env
# Application
APP_ENV=production
SECRET_KEY=your-32-char-secret-key-here

# Database
DATABASE_URL=sqlite:///./nerdsiq.db

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=nerdsiq_docs

# Google Drive
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/credentials.json
GOOGLE_DRIVE_FOLDER_ID=1abc123...

# JWT
JWT_SECRET_KEY=another-secret-key-for-jwt
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# CORS
CORS_ORIGINS=https://www.atiserve.com

# Rate Limiting
RATE_LIMIT_PER_MINUTE=30
```

## Branding Requirements

- **Primary Blue:** #0047AC
- **Accent Yellow:** #FFD301
- **Chatbot Name:** NerdsIQ
- **Widget Position:** Bottom-right corner
- **Widget Size:** 380px wide, 500px max height
- **Mobile:** Full width, 70vh height

## Security Requirements

1. **Authentication:** JWT tokens with 1-hour expiry
2. **Password:** bcrypt hashing with salt
3. **CORS:** Only allow www.atiserve.com
4. **Rate Limiting:** 30 requests/minute per user
5. **Input Validation:** All inputs sanitized and validated
6. **XSS Prevention:** Escape all user-generated content
7. **CSRF:** WordPress nonce verification for AJAX

## Performance Requirements

- Response time: < 5 seconds (95th percentile)
- Cached query response: < 1 second
- Document sync: < 15 minutes after change
- Concurrent users: 5 simultaneous

## Error Handling

### Backend
```python
# Custom exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"}
    )

# Specific errors
raise HTTPException(status_code=401, detail="Invalid credentials")
raise HTTPException(status_code=404, detail="Document not found")
raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

### Frontend
```javascript
// Always handle errors gracefully
try {
    const response = await this.query(question);
    this.displayResponse(response);
} catch (error) {
    this.displayError("Sorry, something went wrong. Please try again.");
    console.error("Query error:", error);
}
```

## Testing Requirements

- Unit test coverage: > 70%
- Test authentication flow
- Test RAG query accuracy
- Test error handling
- Cross-browser testing: Chrome, Firefox, Safari, Edge
- Mobile responsive testing

## When Writing Code

1. **Always** include proper error handling
2. **Always** validate and sanitize inputs
3. **Always** use type hints (Python) or PHPDoc (PHP)
4. **Always** follow the coding standards above
5. **Never** hardcode secrets or API keys
6. **Never** expose sensitive data in responses
7. **Never** trust user input without validation

## Common Tasks

### Add new API endpoint
1. Create schema in `schemas/`
2. Add service method in `services/`
3. Create router in `routers/`
4. Register router in `main.py`
5. Add tests in `tests/`

### Add WordPress AJAX action
1. Add `add_action('wp_ajax_...')` in main plugin file
2. Create handler method
3. Verify nonce
4. Sanitize inputs
5. Return with `wp_send_json_success/error`
6. Add JavaScript handler

### Update document indexing
1. Documents auto-sync via webhook
2. Manual reindex: `python scripts/index_documents.py`
3. Cache invalidates automatically on document changes

---

# Usage Instructions

## For Cursor / VS Code
1. Create `.cursorrules` file in project root
2. Paste this entire prompt content
3. Cursor will use this context for all suggestions

## For GitHub Copilot
1. Create `.github/copilot-instructions.md`
2. Paste this entire prompt content
3. Copilot will reference these instructions

## For Claude / ChatGPT
1. Start conversation with this prompt
2. Then ask specific implementation questions
3. Reference sections: "Following the RAG Pipeline section..."

## For Other AI Tools
1. Add as system prompt or context
2. Reference when asking for code generation
3. Remind AI of specific sections when needed
