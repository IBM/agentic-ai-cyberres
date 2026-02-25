# SendGrid SMTP Configuration Guide

## Quick Setup for SendGrid

SendGrid is a popular email delivery service that provides reliable SMTP servers. Here's how to configure it with the Recovery Validation Agent.

## Step 1: Get Your SendGrid API Key

1. **Sign up for SendGrid** (if you haven't already):
   - Go to https://sendgrid.com/
   - Create a free account (100 emails/day free tier)

2. **Create an API Key**:
   - Log in to SendGrid dashboard
   - Go to **Settings** → **API Keys**
   - Click **Create API Key**
   - Name it (e.g., "Recovery Validation Agent")
   - Select **Full Access** or **Restricted Access** with Mail Send permissions
   - Click **Create & View**
   - **IMPORTANT:** Copy the API key immediately (you won't see it again!)

## Step 2: Configure Your .env File

Add these settings to your `python/src/.env` file:

```bash
# =============================================================================
# Email Configuration - SendGrid
# =============================================================================
USER_EMAIL=your-recipient@example.com

# SendGrid SMTP Configuration
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=SG.your_actual_api_key_here
SMTP_USE_TLS=true
EMAIL_FROM=noreply@yourdomain.com
```

### Important Notes:

1. **SMTP_USERNAME**: Always use the literal string `apikey` (not your actual username)
2. **SMTP_PASSWORD**: Use your SendGrid API key (starts with `SG.`)
3. **EMAIL_FROM**: Must be a verified sender in SendGrid
4. **SMTP_USE_TLS**: Must be `true` for SendGrid

## Step 3: Verify Your Sender Email

SendGrid requires sender verification:

### Option A: Single Sender Verification (Easiest)
1. Go to **Settings** → **Sender Authentication**
2. Click **Verify a Single Sender**
3. Fill in your details
4. Check your email and click the verification link
5. Use this email as `EMAIL_FROM` in your .env

### Option B: Domain Authentication (Recommended for Production)
1. Go to **Settings** → **Sender Authentication**
2. Click **Authenticate Your Domain**
3. Follow the DNS setup instructions
4. Once verified, you can use any email from your domain

## Step 4: Test Your Configuration

### Quick Test with Python SMTP

Create a test file `test_sendgrid.py`:

```python
import smtplib
from email.mime.text import MIMEText

# Your SendGrid credentials
smtp_server = "smtp.sendgrid.net"
smtp_port = 587
username = "apikey"
password = "SG.your_api_key_here"
from_email = "noreply@yourdomain.com"
to_email = "test@example.com"

# Create message
msg = MIMEText("Test email from Recovery Validation Agent")
msg['Subject'] = "SendGrid Test"
msg['From'] = from_email
msg['To'] = to_email

# Send email
try:
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
    print("✅ Email sent successfully!")
except Exception as e:
    print(f"❌ Error: {e}")
```

Run it:
```bash
cd python/src
python test_sendgrid.py
```

### Test with Main Application

```bash
cd python/src
python main.py
```

Enter:
```
I recovered a VM at 192.168.1.100, send report to your-email@example.com
```

Check your email inbox for the validation report!

## Complete .env Example

Here's a complete working example:

```bash
# Recovery Validation Agent Configuration

# =============================================================================
# Email Configuration - SendGrid
# =============================================================================
USER_EMAIL=admin@mycompany.com

# SendGrid SMTP
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SMTP_USE_TLS=true
EMAIL_FROM=noreply@mycompany.com

# =============================================================================
# LLM Configuration
# =============================================================================
LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.2

# =============================================================================
# SSH Credentials
# =============================================================================
SSH_USER=root
SSH_PASSWORD=your_password

# =============================================================================
# Other Settings
# =============================================================================
SEND_EMAIL=true
AUTO_DISCOVER=true
```

## Troubleshooting

### Error: "Authentication failed"
- **Check API Key**: Make sure you copied the entire key (starts with `SG.`)
- **Username**: Must be exactly `apikey` (lowercase)
- **API Key Permissions**: Ensure it has Mail Send permissions

### Error: "Sender address rejected"
- **Verify Sender**: Your `EMAIL_FROM` must be verified in SendGrid
- **Check Domain**: If using domain authentication, ensure DNS is configured

### Error: "Connection refused"
- **Port**: Use port 587 (not 25 or 465)
- **TLS**: Ensure `SMTP_USE_TLS=true`
- **Firewall**: Check if port 587 is open

### Email Not Received
1. **Check SendGrid Activity**:
   - Go to SendGrid dashboard → Activity
   - Look for your email in the activity feed
   - Check for bounces or blocks

2. **Check Spam Folder**: SendGrid emails might go to spam initially

3. **Verify Recipient**: Make sure the recipient email is valid

### Rate Limits
- **Free Tier**: 100 emails/day
- **Paid Plans**: Higher limits available
- Check your SendGrid dashboard for current usage

## SendGrid Dashboard Monitoring

Monitor your emails in real-time:

1. **Activity Feed**: See all sent emails
2. **Statistics**: View delivery rates, opens, clicks
3. **Suppressions**: Check bounced/blocked emails
4. **Alerts**: Set up notifications for issues

## Security Best Practices

1. **Never commit API keys**: Keep .env in .gitignore
2. **Use environment variables**: Don't hardcode credentials
3. **Rotate keys regularly**: Create new API keys periodically
4. **Restrict permissions**: Use minimum required permissions
5. **Monitor usage**: Watch for unusual activity

## Alternative SendGrid Ports

SendGrid supports multiple ports:

| Port | Protocol | Use Case |
|------|----------|----------|
| 587  | TLS      | **Recommended** - Most compatible |
| 465  | SSL      | Legacy systems |
| 25   | Plain    | Not recommended (often blocked) |
| 2525 | TLS      | Alternative if 587 is blocked |

To use port 2525:
```bash
SMTP_PORT=2525
SMTP_USE_TLS=true
```

## Cost Information

- **Free Tier**: 100 emails/day forever
- **Essentials**: $19.95/month - 50,000 emails/month
- **Pro**: $89.95/month - 100,000 emails/month
- **Premier**: Custom pricing

For validation reports, the free tier is usually sufficient for testing and small deployments.

## Support

- **SendGrid Docs**: https://docs.sendgrid.com/
- **SMTP API**: https://docs.sendgrid.com/for-developers/sending-email/getting-started-smtp
- **Support**: https://support.sendgrid.com/

## Quick Reference

```bash
# SendGrid SMTP Settings
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=SG.your_api_key
SMTP_USE_TLS=true
```

**Ready to send emails!** 🚀