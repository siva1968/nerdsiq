# Danswer POC - Testing Checklist

## Initial Setup Verification (30 minutes)

### Docker Services
- [ ] All containers started successfully (`docker-compose ps`)
- [ ] No error logs in `docker-compose logs`
- [ ] Health checks passing for all services
- [ ] Memory usage acceptable (< 4GB total)
- [ ] CPU usage low at idle (< 20%)

### First Login
- [ ] Can access http://localhost:3000
- [ ] Login page loads correctly
- [ ] Default credentials work (admin@example.com / admin)
- [ ] Password change prompt appears
- [ ] Dashboard loads after login

### Google Drive Connector
- [ ] Connector configuration page loads
- [ ] Can authenticate with Google (or upload service account JSON)
- [ ] Folder ID accepted and validated
- [ ] Indexing starts when "Index Now" clicked
- [ ] Progress bar shows document count
- [ ] All expected documents appear in index
- [ ] Indexing completes without errors

## Answer Quality Comparison (1 hour)

### Standard Queries (compare with current NerdsIQ)

| # | Question | Current NerdsIQ | Danswer | Winner | Notes |
|---|----------|----------------|---------|--------|-------|
| 1 | What are NerdsToGo's business hours? | | | | |
| 2 | How do I submit a PTO request? | | | | |
| 3 | What's included in the Premium service plan? | | | | |
| 4 | Compare Nerds on Call vs. Nerds on Site | | | | |
| 5 | What's the escalation procedure for angry customers? | | | | |
| 6 | How do I access the company VPN? | | | | |
| 7 | What are the hardware warranty policies? | | | | |
| 8 | Explain the franchise training process | | | | |
| 9 | What's the commission structure? | | | | |
| 10 | How do I update customer info in the system? | | | | |

**Scoring:** For each question, rate 1-5 stars for:
- Accuracy
- Completeness
- Source citations
- Relevance
- Response time

### Edge Cases

- [ ] **Ambiguous question:** "Tell me about hours"
  - Does it clarify (business hours vs billable hours)?
  
- [ ] **No answer:** "What's the CEO's favorite color?"
  - Does it say "I don't know" instead of guessing?
  
- [ ] **Multi-document synthesis:** "Compare all service plan pricing"
  - Does it pull from multiple sources correctly?
  
- [ ] **Recent document:** Index a new document, ask about it
  - Does it find and use the new content?
  
- [ ] **Long conversation:** Ask 10 follow-up questions
  - Does context remain accurate throughout?

## Source Citations (30 minutes)

- [ ] Citations appear for every answer
- [ ] Citation links are clickable
- [ ] Links go to correct source documents
- [ ] Snippet preview is accurate
- [ ] Multiple sources cited when appropriate
- [ ] Sources ranked by relevance
- [ ] No hallucinated sources

## User Experience (30 minutes)

### Interface
- [ ] UI is intuitive and easy to navigate
- [ ] Search bar is prominent and functional
- [ ] Conversation history is accessible
- [ ] Settings are easy to find
- [ ] Help/documentation links work

### Performance
- [ ] Page loads in < 2 seconds
- [ ] Queries return in < 5 seconds (95% of time)
- [ ] Typing is responsive (no lag)
- [ ] No UI freezes or crashes
- [ ] Works in Chrome, Firefox, Edge

### Mobile (if applicable)
- [ ] Interface adapts to mobile screen
- [ ] Touch interactions work
- [ ] Keyboard doesn't obscure input
- [ ] Readable font sizes

### Accessibility
- [ ] Can navigate with keyboard only
- [ ] Tab order is logical
- [ ] Focus indicators visible
- [ ] Color contrast sufficient

## Admin Features (30 minutes)

### User Management
- [ ] Can create new user accounts
- [ ] Can assign roles/permissions
- [ ] Can reset passwords
- [ ] Can disable accounts
- [ ] Can view user activity

### Document Management
- [ ] Can view all indexed documents
- [ ] Can see document metadata
- [ ] Can re-index specific documents
- [ ] Can delete documents from index
- [ ] Can filter/search documents

### Analytics Dashboard
- [ ] Total queries visible
- [ ] Query trends over time
- [ ] Most common questions shown
- [ ] User engagement metrics
- [ ] Search success rate
- [ ] Average response time

### Connector Management
- [ ] Can add new connectors
- [ ] Can edit connector settings
- [ ] Can pause/resume indexing
- [ ] Can set sync schedule
- [ ] Can view sync logs
- [ ] Can manually trigger sync

### Settings & Customization
- [ ] Can change app name/logo
- [ ] Can customize colors/theme
- [ ] Can edit system prompt
- [ ] Can configure LLM model
- [ ] Can set rate limits
- [ ] Can enable/disable auth

## Technical Evaluation (1 hour)

### Resource Usage
```
Idle state:
- RAM usage: _____ MB
- CPU usage: _____ %
- Disk usage: _____ GB

Under load (5 concurrent queries):
- RAM usage: _____ MB
- CPU usage: _____ %
- Response time: _____ seconds
```

### Logs & Monitoring
- [ ] Application logs are readable
- [ ] Error logs clearly indicate issues
- [ ] Can filter logs by severity
- [ ] Timestamps are accurate
- [ ] No excessive logging spam

### Backup & Recovery
- [ ] PostgreSQL backup script works
- [ ] Qdrant snapshot can be created
- [ ] Restore process documented
- [ ] Backup files are readable
- [ ] Automated backup schedule configured

### Security
- [ ] HTTPS enforced (in production)
- [ ] Passwords hashed (bcrypt)
- [ ] JWT tokens expire appropriately
- [ ] CORS configured correctly
- [ ] No sensitive data in logs
- [ ] Rate limiting works

### API
- [ ] API documentation accessible (/docs)
- [ ] Can authenticate via API
- [ ] Can submit queries via API
- [ ] Can retrieve results via API
- [ ] Rate limiting applies to API
- [ ] Error responses are clear

## Integration Testing (30 minutes)

### WordPress Integration Options

**If testing iframe embed:**
- [ ] Iframe loads Danswer UI
- [ ] No CORS errors in console
- [ ] Looks good in WordPress theme
- [ ] Responsive on mobile
- [ ] No scrolling issues

**If testing API wrapper:**
- [ ] Can authenticate from WordPress
- [ ] Can send queries from WordPress
- [ ] Responses render correctly
- [ ] Sources display properly
- [ ] Error handling works

### SSO/Authentication (if applicable)
- [ ] Google OAuth works
- [ ] User roles sync correctly
- [ ] Logout works properly

## Comparison Summary

### Pros of Danswer (vs current NerdsIQ)
- 
- 
- 

### Cons of Danswer (vs current NerdsIQ)
- 
- 
- 

### Missing Features
- 
- 
- 

### Performance Comparison
| Metric | Current NerdsIQ | Danswer | Winner |
|--------|----------------|---------|--------|
| Average query time | | | |
| Index time (all docs) | | | |
| Memory usage | | | |
| Setup time | | | |
| Maintenance hours/month | | | |

## Final Recommendation

**Overall rating:** ☐ Excellent  ☐ Good  ☐ Acceptable  ☐ Needs Improvement  ☐ Not Suitable

**Proceed with migration?** ☐ Yes  ☐ No  ☐ Needs More Testing

**Key reasons:**
1. 
2. 
3. 

**Concerns:**
1. 
2. 
3. 

**Next steps:**
1. 
2. 
3. 

---

**Tested by:** ___________________  
**Date:** ___________________  
**Completion time:** ___________________
