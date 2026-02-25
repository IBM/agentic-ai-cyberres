# Email Configuration Guide

## Overview

The Recovery Validation Agent now supports flexible email configuration, allowing users to specify email recipients in multiple ways. Reports can be sent to any email address provided by the user at runtime, with optional fallback to environment variables.

## Configuration Methods

### 1. Environment Variable (Default/Fallback)

Set a default email recipient in your `.env` file:

```bash
USER_EMAIL=admin@example.com
SMTP_SERVER=localhost
SMTP_PORT=25
EMAIL_FROM=recovery-validation@cyberres.com
```

**Note:** If `USER_EMAIL` is not set and no email is provided at runtime, the agent will prompt the user for an email address.

### 2. Natural Language Prompt

Include the email address directly in your validation request:

```bash
# Interactive mode
"I recovered a VM at 192.168.1.100, send report to admin@example.com"
"Validate Oracle database on db-server.example.com, email me at dba@company.com"
"MongoDB cluster at mongo1.local, report to ops@example.com"

# Production demo
python production_demo.py "Check the web server at web-server-01, send report to admin@example.com"
```

### 3. Command-Line Flag

Use the `--email` flag when running the production demo:

```bash
python production_demo.py "Validate app-server-01" --email ops@company.com
```

### 4. Interactive Prompt

When running in interactive mode, if no email is provided and `USER_EMAIL` is not set, the agent will ask:

```
Agent 🤖: What email address should I send the validation report to?
You: admin@example.com
```

## Priority Order

The system uses the following priority order for determining the email recipient:

1. **User-provided email in prompt** (highest priority)
2. **Command-line flag** (`--email`)
3. **Environment variable** (`USER_EMAIL`)
4. **Interactive prompt** (if none of the above are available)

## SMTP Configuration

Configure your SMTP server in the `.env` file:

```bash
# Basic SMTP (no authentication)
SMTP_SERVER=localhost
SMTP_PORT=25
EMAIL_FROM=recovery-validation@cyberres.com

# Authenticated SMTP (optional)
SMTP_USERNAME=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SMTP_USE_TLS=true
```

### Common SMTP Configurations

#### SendGrid (Recommended)
```bash
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=apikey
SMTP_PASSWORD=SG.your_sendgrid_api_key_here
EMAIL_FROM=noreply@yourdomain.com
```
**Note:** See `SENDGRID_SETUP.md` for detailed setup instructions.

#### Gmail
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

#### Office 365
```bash
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your_email@company.com
SMTP_PASSWORD=your_password
```

#### AWS SES
```bash
SMTP_SERVER=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your_ses_username
SMTP_PASSWORD=your_ses_password
```

## Usage Examples

### Example 1: Interactive Mode with Email in Prompt

```bash
python main.py
```

```
Agent 🤖: Welcome to the Recovery Validation Agent!
...
You: I recovered a VM at 192.168.1.100, send report to admin@example.com

Agent 🤖: Perfect! I have all the information I need.
I will now:
1. Auto-discover resource details
2. Generate a validation plan
3. Execute validation checks
4. Evaluate results
5. Send a detailed report to admin@example.com
```

### Example 2: Production Demo with Email Flag

```bash
python production_demo.py "Validate Oracle database at db-server-01" --email dba@company.com
```

### Example 3: Using Environment Variable

```bash
# Set in .env
USER_EMAIL=ops@example.com

# Run without specifying email
python main.py
```

The report will automatically be sent to `ops@example.com`.

### Example 4: Email Extracted from Natural Language

```bash
python production_demo.py "Check MongoDB at mongo-cluster-01, email results to devops@company.com"
```

The system will automatically extract `devops@company.com` from the prompt.

## Email Report Format

The validation report is sent in both plain text and HTML formats:

- **Subject:** `Recovery Validation Report - [RESOURCE_TYPE] - [STATUS]`
- **From:** Configured `EMAIL_FROM` address
- **To:** User-provided or configured email address
- **Content:** 
  - Plain text summary
  - HTML formatted detailed report with:
    - Validation results
    - Check details
    - Recommendations
    - Metrics and statistics

## Disabling Email Reports

To disable email reports:

1. **Environment variable:**
   ```bash
   SEND_EMAIL=false
   ```

2. **In code:**
   ```python
   validation_request = ValidationRequest(
       resource_info=resource_info,
       send_email=False
   )
   ```

## Troubleshooting

### Email Not Sending

1. **Check SMTP configuration:**
   ```bash
   # Test SMTP connection
   telnet smtp.example.com 25
   ```

2. **Verify credentials:**
   - Ensure `SMTP_USERNAME` and `SMTP_PASSWORD` are correct
   - For Gmail, use an App Password instead of your regular password

3. **Check firewall:**
   - Ensure outbound connections to SMTP port are allowed

4. **Review logs:**
   ```bash
   tail -f recovery_validation.log | grep -i email
   ```

### Email Address Not Detected

If the email address is not being extracted from your prompt:

1. **Use explicit keywords:**
   ```
   "...send report to admin@example.com"
   "...email me at admin@example.com"
   ```

2. **Use the --email flag:**
   ```bash
   python production_demo.py "..." --email admin@example.com
   ```

3. **Set USER_EMAIL in .env:**
   ```bash
   USER_EMAIL=admin@example.com
   ```

## Security Considerations

1. **Never commit credentials:**
   - Keep `.env` file in `.gitignore`
   - Use environment variables or secrets management

2. **Use App Passwords:**
   - For Gmail and similar services, use app-specific passwords

3. **Enable TLS:**
   - Always use `SMTP_USE_TLS=true` for production

4. **Validate email addresses:**
   - The system validates email format using regex
   - Invalid emails will be rejected

## API Reference

### EmailService Class

```python
from email_service import EmailService

# Initialize
email_service = EmailService(
    smtp_server="smtp.example.com",
    smtp_port=587,
    from_address="noreply@example.com"
)

# Send validation report
success = email_service.send_validation_report(
    report=validation_report,
    recipient="admin@example.com",
    include_text=True
)

# Send simple email
success = email_service.send_simple_email(
    recipient="admin@example.com",
    subject="Test Email",
    body="<h1>Hello</h1>",
    is_html=True
)
```

### ConversationHandler

The `ConversationHandler` automatically extracts email addresses from user input:

```python
from conversation import ConversationHandler

handler = ConversationHandler()
parsed = await handler.parse_initial_input(
    "Validate VM at 192.168.1.100, send to admin@example.com"
)
# parsed["email_recipient"] = "admin@example.com"
```

## Support

For issues or questions:
1. Check the logs: `recovery_validation.log`
2. Review this guide
3. Contact your system administrator

---

**Last Updated:** 2026-02-25
**Version:** 1.0.0