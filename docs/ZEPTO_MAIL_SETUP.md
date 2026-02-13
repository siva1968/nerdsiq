# Zepto Mail Setup Guide for NerdsIQ

This guide explains how to configure Zepto Mail for sending daily report emails and alerts in NerdsIQ.

## What is Zepto Mail?

Zepto Mail is a transactional email service by Zoho that provides reliable email delivery for applications. It offers:
- High deliverability rates
- Real-time analytics
- API and SMTP access
- Free tier with 10,000 emails/month
- Dedicated IP options

## Step 1: Create Zepto Mail Account

1. Go to [zeptomail.com](https://www.zeptomail.com/)
2. Sign up for a new account
3. Verify your email address
4. Complete account setup

## Step 2: Domain Verification

1. **Add Your Domain:**
   - Go to Configuration → Domains
   - Click "Add Domain"
   - Enter your domain (e.g., `yourdomain.com`)

2. **Verify Domain Ownership:**
   - Add the provided TXT record to your DNS
   - Wait for verification (usually takes a few minutes)

3. **Configure DKIM (Recommended):**
   - Add the DKIM records to your DNS
   - This improves email deliverability

## Step 3: Generate API Token

1. Go to Configuration → Mail Agents
2. Click "Create Mail Agent" 
3. Choose "Server Based"
4. Configure settings:
   - **Name:** NerdsIQ Notifications
   - **From Email:** `noreply@yourdomain.com`
   - **Reply To:** Your support email
5. Copy the generated **Send Mail Token** (for SMTP) or **API Key** (for REST API)

## Step 4: Configure NerdsIQ

### Option A: REST API (Recommended)

Add these settings to your `.env` file:

```env
# Zepto Mail API Configuration (Recommended)
ZEPTOMAIL_API_KEY=your-zoho-enczapikey-token-here
ZEPTOMAIL_REGION=in
USE_ZEPTOMAIL_API=true
FROM_EMAIL=noreply@yourdomain.com
NOTIFICATION_EMAILS=admin@yourdomain.com,alerts@yourdomain.com
```

### Option B: SMTP (Alternative)

```env
# Zepto Mail SMTP Configuration
SMTP_SERVER=smtp.zeptomail.com
SMTP_PORT=587
SMTP_USERNAME=emailapikey
SMTP_PASSWORD=your-zepto-mail-token-here
FROM_EMAIL=noreply@yourdomain.com
NOTIFICATION_EMAILS=admin@yourdomain.com,alerts@yourdomain.com
USE_ZEPTOMAIL_API=false
```

### Configuration Details:

**API Method:**
- **ZEPTOMAIL_API_KEY:** Your API token from Mail Agent settings (starts with `wSsVR6...`)
- **ZEPTOMAIL_REGION:** `in` (India), `com` (US/Global), or `eu` (Europe)
- **USE_ZEPTOMAIL_API:** Set to `true` to use REST API instead of SMTP

**SMTP Method:**
- **SMTP_SERVER:** Use region-specific server (`smtp.zeptomail.in`, `smtp.zeptomail.com`, `smtp.zeptomail.eu`)
- **SMTP_USERNAME:** Always `emailapikey` (literal value)
- **SMTP_PASSWORD:** Your Send Mail Token from Mail Agent

**Common Settings:**
- **FROM_EMAIL:** Must be from your verified domain
- **NOTIFICATION_EMAILS:** Comma-separated list of recipients

## Step 5: Test Email Configuration

Run the setup script to test your configuration:

```bash
cd backend
python scripts/setup_monitoring.py
```

Or test directly from WordPress admin:
1. Go to NerdsIQ → Daily Logs
2. Click "Test Email" button
3. Check your inbox for the test email

## Step 6: Configure Email Templates (Optional)

You can customize the email templates by modifying the `EmailNotifier` class in:
`backend/app/services/monitoring_service.py`

### Customization Options:
- Email subject lines
- HTML formatting
- Attachment inclusion
- Retry logic
- Error handling

## Troubleshooting

### Common Issues:

**1. Authentication Failed:**
- Verify your Send Mail Token is correct
- Ensure SMTP_USERNAME is exactly `emailapikey`
- Check that the token hasn't expired

**2. Domain Not Verified:**
- Complete domain verification in Zepto Mail console
- Wait for DNS propagation (can take 24-48 hours)
- Test with a verified domain first

**3. Emails Not Delivered:**
- Check Zepto Mail logs in the console
- Verify FROM_EMAIL is from verified domain
- Check recipient spam folders
- Review bounce reports

**4. Rate Limiting:**
- Zepto Mail free tier: 10,000 emails/month
- Paid plans have higher limits
- Monitor usage in the console

### Debug Mode:

Enable debug logging to troubleshoot issues:

```env
LOG_LEVEL=DEBUG
```

Then check logs:
```bash
python scripts/log_manager.py show --date $(date +%Y-%m-%d)
```

## Email Frequency

By default, NerdsIQ sends:
- **Daily Reports:** Summary of indexing activity (8 AM)
- **Error Alerts:** Immediate notifications for critical issues
- **Test Emails:** Manual testing from admin panel

### Scheduling Daily Reports:

**Windows (Task Scheduler):**
```
Program: python
Arguments: scripts/daily_report.py
Working Directory: D:\dev\nerdsiq\backend
Trigger: Daily at 8:00 AM
```

**Linux/Mac (Crontab):**
```bash
0 8 * * * cd /path/to/nerdsiq/backend && python scripts/daily_report.py
```

## Security Best Practices

1. **Rotate Tokens Regularly:** Generate new tokens every 90 days
2. **Limit Permissions:** Use domain-specific tokens when possible
3. **Monitor Usage:** Track email volume and delivery rates
4. **Secure Storage:** Never commit tokens to version control
5. **Backup Configuration:** Save settings in a secure location

## Zepto Mail Regions

Choose the server based on your location:

- **US/Global:** `smtp.zeptomail.com`
- **Europe:** `smtp.zeptomail.eu`
- **India:** `smtp.zeptomail.in`

Update SMTP_SERVER in your .env file accordingly.

## Cost Optimization

**Free Tier:** 10,000 emails/month
- Perfect for small teams (1-5 users)
- Daily reports: ~30 emails/month
- Error alerts: Variable based on activity

**Paid Plans:** Start at $2.50/month for 25,000 emails
- Better for larger organizations
- Includes advanced analytics
- Priority support

## Support

- **Zepto Mail Docs:** [help.zeptomail.com](https://help.zeptomail.com/)
- **NerdsIQ Logs:** Check WordPress Admin → NerdsIQ → Daily Logs
- **API Status:** Monitor via `/health` endpoint

---

Once configured, your NerdsIQ system will automatically send daily indexing reports and alert notifications through Zepto Mail with high deliverability rates!