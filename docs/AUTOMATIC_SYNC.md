# Automatic Document Synchronization

NerdsIQ now supports **automatic document synchronization** using Google Drive webhooks. This means your knowledge base will automatically update whenever files are added, modified, or removed from your Google Drive folder.

## 🚀 Features

- **Real-time sync**: Changes are detected within seconds
- **Fully recursive**: Works with all subfolders, regardless of names
- **Smart debouncing**: Batches multiple changes to avoid excessive reindexing
- **Auto-renewal**: Webhooks automatically renew every 6 days
- **Cache invalidation**: Cached queries are cleared when documents change
- **"Set and forget"**: No manual maintenance required

## 📋 Requirements

1. **Public HTTPS endpoint**: Your API must be accessible via HTTPS from the internet
2. **Google Drive API access**: Service account or OAuth with Drive API enabled
3. **Folder permissions**: Your credentials must have access to the monitored folder

## 🛠 Setup

### 1. Configure Environment Variables

```env
# Your public domain (required for webhooks)
WEBHOOK_CALLBACK_BASE_URL=https://api.yourdomain.com

# Google Drive folder to monitor
GOOGLE_DRIVE_FOLDER_ID=1abc123...

# Google credentials (service account or OAuth)
GOOGLE_SERVICE_ACCOUNT_FILE=./credentials/google-service-account.json
```

### 2. Run Setup Script

```bash
cd backend
python scripts/setup_webhooks.py
```

Or with a custom callback URL:

```bash
python scripts/setup_webhooks.py --callback-url https://api.yourdomain.com
```

### 3. Verify Setup

Check webhook status via API:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  https://api.yourdomain.com/api/v1/documents/webhook/status
```

## 🔄 How It Works

1. **Webhook Creation**: A webhook is registered with Google Drive API
2. **Change Detection**: Google sends notifications when files change
3. **Debouncing**: System waits 30 seconds for multiple changes
4. **Cache Clearing**: All cached queries are invalidated
5. **Reindexing**: Document indexing runs automatically
6. **Auto-renewal**: Webhooks are renewed every 6 days

### Webhook Flow

```
Google Drive Change → Webhook Notification → Debounce Wait → Clear Cache → Reindex Documents
```

## 🏗 Development Setup

For local development, you need to expose your local API to the internet:

### Option 1: Cloudflare Tunnel

```bash
# Install cloudflared
# Create a tunnel and configure it to point to localhost:8000

# Your webhook URL would be:
WEBHOOK_CALLBACK_BASE_URL=https://your-tunnel.trycloudflare.com
```

### Option 2: ngrok

```bash
# Install ngrok
ngrok http 8000

# Your webhook URL would be:
WEBHOOK_CALLBACK_BASE_URL=https://abc123.ngrok.io
```

## 🔧 API Endpoints

### Setup Webhook
```http
POST /api/v1/documents/webhook/setup
Authorization: Bearer <token>
```

### Check Status
```http
GET /api/v1/documents/webhook/status
Authorization: Bearer <token>
```

### Stop Webhook
```http
POST /api/v1/documents/webhook/stop
Authorization: Bearer <token>
```

### Webhook Callback (Internal)
```http
POST /api/v1/documents/webhook/drive-changes
X-Goog-Channel-ID: nerdsiq-abc123
X-Goog-Resource-State: update
```

## ⚡ Performance & Optimization

### Debouncing
- **Purpose**: Prevents excessive reindexing when many files change quickly
- **Delay**: 30 seconds after the last change
- **Benefit**: Batches multiple changes into a single reindex operation

### Smart Caching
- **Query Cache**: Cleared automatically when documents change
- **TTL**: 60 minutes for cached queries
- **Invalidation**: All cache cleared on document changes

### Background Processing
- **Non-blocking**: Reindexing runs in the background
- **Async**: Uses asyncio for concurrent processing
- **Logging**: Comprehensive logging for troubleshooting

## 🛡 Security

### Webhook Verification
- Google Drive webhooks include verification headers
- Channel IDs are unique and tracked
- Only valid Google notifications are processed

### Authentication
- All management endpoints require JWT authentication
- Webhook callback is public (by design) but validated

## 📊 Monitoring

### Logs
- All webhook events are logged with details
- Reindexing progress and results are logged
- Errors include full stack traces

### Status Endpoint
Check webhook health:
```json
{
  "status": "active",
  "webhook": {
    "channel_id": "nerdsiq-abc123",
    "resource_id": "xyz789",
    "expiration": "2026-02-10T15:30:00",
    "expires_in_hours": 142.5
  }
}
```

## 🐛 Troubleshooting

### Webhook Not Receiving Events

1. **Check URL accessibility**: Ensure your callback URL is reachable via HTTPS
2. **Verify permissions**: Service account needs access to the monitored folder
3. **Check logs**: Look for webhook setup errors in application logs
4. **Test manually**: Use the status endpoint to verify webhook is active

### Reindexing Not Working

1. **Check background task**: Look for reindexing task errors in logs
2. **Verify script path**: Ensure indexing script is in correct location
3. **Check dependencies**: Ensure all required packages are installed
4. **Manual test**: Run indexing script manually to verify it works

### Webhook Expiration

- **Auto-renewal**: Webhooks automatically renew every 6 days
- **Manual renewal**: Use setup script to create new webhook
- **Monitoring**: Check expiration time via status endpoint

## 🔮 Future Enhancements

### Selective Reindexing
Currently, the system reindexes all documents when any change occurs. Future versions could:
- Parse webhook payload for specific file changes
- Only reindex changed files
- Use Google Drive's `changes.list` API for detailed change information

### Change Types
Handle different change types more intelligently:
- **Add**: Only index new files
- **Update**: Only reindex modified files  
- **Remove**: Only remove deleted files from vector database

### Real-time Processing
- Process changes immediately without debouncing (optional)
- Stream processing for very large document sets
- Incremental indexing for large files

## 📝 Example Usage

After setup, your system will automatically handle scenarios like:

1. **Adding a new folder** "RingCentral - Archives" → Automatically indexed
2. **Updating an existing document** → Reindexed within 30 seconds
3. **Removing old files** → Removed from search results
4. **Renaming folders** → All contents remain searchable
5. **Moving files between folders** → Automatically detected and updated

The client's request for "set and forget" functionality is now fully implemented! 🎉

## 💡 Tips

- **Monitor initially**: Watch logs during first few days to ensure everything works
- **Test thoroughly**: Make test changes to verify automatic sync
- **Backup strategy**: Keep regular backups of your vector database
- **Performance tuning**: Adjust debounce timing based on your change frequency