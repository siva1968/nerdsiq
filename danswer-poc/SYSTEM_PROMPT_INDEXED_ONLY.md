# System Prompt Configuration - Indexed Documents Only

## ✅ LOGOUT FIX APPLIED (v2.11.0 + Custom Patch)

**Status:** Logout button now works correctly!

**Fix Applied:** Custom-built web image with two patches:
1. **Cookie deletion fix** - Changed `if (NEXT_PUBLIC_CLOUD_ENABLED)` to `if (true)` in `route.ts` 
2. **Header filtering fix** - Removed problematic `Connection` and `Upgrade` headers in `userSS.ts`

**Custom Image:** `onyx-web-custom:logout-fix` (built from v2.11.0 source)

**Files Modified:**
- `/web/src/app/auth/logout/route.ts` - Force cookie deletion on logout
- `/web/src/lib/userSS.ts` - Filter headers to prevent undici fetch errors

**Testing:** Logout now returns 401 (expected when unauthenticated) instead of 500 error. No more "InvalidArgumentError: invalid connection header" in logs.

---

## Overview
This system prompt ensures the AI assistant ONLY uses indexed Google Drive documents and never provides information from external sources or general knowledge.

## Recommended System Prompt for Onyx/Danswer

Copy this prompt into **Admin → Personas → Create/Edit Persona**:

```
You are NerdsIQ, an AI assistant for NerdsToGo employees.

CRITICAL RULES - INDEXED DOCUMENTS ONLY:
1. You can ONLY answer questions using information from indexed document search results
2. If information is NOT found in search results, say: "I do not have that information in our indexed documents"
3. NEVER use your general knowledge or training data - ONLY use information from search results
4. NEVER make assumptions or infer information not in the documents
5. ALWAYS search documents before answering

SOURCE TRANSPARENCY:
- ALWAYS cite sources with document names and links
- If multiple documents have relevant information, cite all of them
- Show exact quotes when possible

RESPONSE FORMAT:
- Be helpful and professional
- Keep answers concise but complete

Remember: You are a document search assistant. Always search indexed documents first, then answer based only on what you find.
```

## How to Apply

### In Onyx/Danswer Admin UI:
1. Log in to admin panel (http://localhost:3100 or your domain)
2. Navigate to **Admin** → **Personas**
3. Click **Create Persona** or edit default persona
4. Paste the system prompt above
5. Set as default persona for all users
6. Save changes

### Verification Steps:
1. Ask: "What is the capital of France?" (should respond: "I don't have that information...")
2. Ask: "What are our company policies?" (should answer from indexed docs with citations)
3. Check that all answers include source document links
4. Verify citations match actual indexed documents

## Additional Settings

Ensure your `.env` file has:
```env
DISABLE_LLM_CHOOSE_SEARCH=true          # No external search
NEXT_PUBLIC_SHOW_CITATIONS=true         # Always show sources
QUOTE_EXTRACTION_ENABLED=true           # Extract exact quotes
```

## Critical Persona Settings (Admin → Personas → Assistant):

**IMPORTANT:** These settings MUST be configured in the database:
```sql
-- Run these commands to ensure document search always happens:
UPDATE persona SET llm_relevance_filter = false WHERE id = 0;
UPDATE persona SET llm_filter_extraction = false WHERE id = 0;

-- Verify settings:
SELECT id, name, llm_relevance_filter, llm_filter_extraction FROM persona WHERE id = 0;
-- Should show: llm_relevance_filter = f, llm_filter_extraction = f
```

**Why these are needed:**
- `llm_relevance_filter = false`: Prevents LLM from filtering out documents before searching
- `llm_filter_extraction = false`: Forces document search on EVERY query (doesn't let LLM decide to skip search)

## Testing Compliance

### Test Queries:
| Query | Expected Behavior |
|-------|------------------|
| "What time is it?" | "I don't have that information in indexed documents" |
| "Who is the US president?" | "I don't have that information in indexed documents" |
| "What is our return policy?" | Answers from docs + citations |
| "How do I reset a password?" | Answers from docs + citations |

### Red Flags:
- ❌ Answers general knowledge questions
- ❌ Provides info without citations
- ❌ Makes assumptions not in docs
- ❌ Suggests actions not documented

### Green Flags:
- ✅ Only answers from indexed docs
- ✅ Always provides citations
- ✅ Admits when info is missing
- ✅ Shows exact document quotes

## Maintenance

**Monthly Audit:**
1. Review chat logs for non-cited answers
2. Test edge cases (general knowledge queries)
3. Verify all citations link to real documents
4. Update system prompt if needed

**When Adding New Documents:**
1. Wait for indexing to complete
2. Test that new docs are searchable
3. Verify answers include new sources
4. No changes to system prompt needed

## Support

If the system provides information not in indexed documents:
1. Check `.env` that `DISABLE_LLM_CHOOSE_SEARCH=true`
2. Verify system prompt is configured correctly
3. Review admin logs for external API calls
4. Contact Onyx/Danswer support if issue persists
