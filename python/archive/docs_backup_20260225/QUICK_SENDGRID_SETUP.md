# Quick SendGrid Setup - Fix Email Connection Error

## Current Issue

```
Error sending email: [Errno 61] Connection refused
```

This means `localhost:25` doesn't have an SMTP server running.

## Solution: Configure SendGrid

### Step 1: Get SendGrid API Key (5 minutes)

1. Go to https://sendgrid.com/
2. Sign up for free account (100 emails/day)
3. Go to **Settings** → **API Keys**
4. Click **Create API Key**
5. Name it: "Recovery Validation"
6. Select **Full Access**
7. Click **Create & View**
8. **COPY THE KEY** (starts with `SG.`)

### Step 2: Update Your .env File

Replace the email section in `python/src/.env`:

```bash
# =============================================================================
# Email Configuration - SendGrid
# =============================================================================
USER_EMAIL=himanshu.sharma27@ibm.com

# SendGrid SMTP Configuration
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=SG.paste_your_api_key_here
SMTP_USE_TLS=true
EMAIL_FROM=noreply@yourdomain.com
```

**Important:**
- `SMTP_USERNAME` must be exactly `apikey` (not your email)
- `SMTP_PASSWORD` is your SendGrid API key (starts with `SG.`)
- `EMAIL_FROM` must be verified in SendGrid (see Step 3)

### Step 3: Verify Sender Email

SendGrid requires sender verification:

1. Go to SendGrid → **Settings** → **Sender Authentication**
2. Click **Verify a Single Sender**
3. Fill in your details:
   - From Name: Recovery Validation
   - From Email: noreply@yourdomain.com (or your email)
   - Reply To: your-email@example.com
4. Check your email and click verification link
5. Use this verified email as `EMAIL_FROM` in .env

### Step 4: Test

```bash
cd python/src
python main.py
```

Input:
```
I recovered a VM at 9.11.68.243 and send an email to himanshu.sharma27@ibm.com
```

You should see:
```
📧 Sending report to himanshu.sharma27@ibm.com...
✓ Email report sent successfully
```

## Alternative: Use Gmail (If You Don't Want SendGrid)

If you prefer Gmail:

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
EMAIL_FROM=your-email@gmail.com
```

**Note:** You need to create an App Password in Gmail:
1. Go to Google Account → Security
2. Enable 2-Step Verification
3. Go to App Passwords
4. Generate password for "Mail"
5. Use that password (not your regular password)

## Troubleshooting

### Still Getting Connection Refused?

Check your .env file:
```bash
cat python/src/.env | grep SMTP
```

Should show:
```
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=SG.xxxxx...
SMTP_USE_TLS=true
```

### Authentication Failed?

- Verify `SMTP_USERNAME=apikey` (exactly)
- Check API key is complete (starts with `SG.`)
- Ensure no extra spaces in .env

### Sender Address Rejected?

- Verify your sender email in SendGrid dashboard
- Use the exact email you verified as `EMAIL_FROM`

## Quick Test Script

Create `test_email.py`:

```python
import smtplib
from email.mime.text import MIMEText

msg = MIMEText("Test from Recovery Validation Agent")
msg['Subject'] = "Test Email"
msg['From'] = "noreply@yourdomain.com"  # Your verified email
msg['To'] = "himanshu.sharma27@ibm.com"

try:
    with smtplib.SMTP("smtp.sendgrid.net", 587) as server:
        server.starttls()
        server.login("apikey", "SG.your_api_key_here")
        server.send_message(msg)
    print("✅ Email sent!")
except Exception as e:
    print(f"❌ Error: {e}")
```

Run:
```bash
python test_email.py
```

## Summary

**The email functionality is working!** You just need to configure a real SMTP server (SendGrid recommended).

**Current Status:**
- ✅ Email extraction from user input: WORKING
- ✅ Email sending logic: WORKING
- ❌ SMTP server: NOT CONFIGURED (localhost:25 doesn't exist)

**Next Step:** Configure SendGrid (5 minutes) and test again!