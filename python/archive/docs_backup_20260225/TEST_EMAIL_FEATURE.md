# Testing Email Feature from main.py

## Quick Test Guide

The email feature is now fully integrated into main.py. Here are different ways to test it:

## Test Scenario 1: Use Email from Natural Language Prompt

```bash
cd python/src
python main.py
```

When prompted, enter:
```
I recovered a VM at 192.168.1.100, send report to myemail@example.com
```

**Expected Result:**
- Agent extracts email: `myemail@example.com`
- Report will be sent to `myemail@example.com` (overrides USER_EMAIL in .env)

---

## Test Scenario 2: Use Default Email from .env

Your .env currently has:
```
USER_EMAIL=admin@example.com
```

```bash
cd python/src
python main.py
```

When prompted, enter (without email):
```
I recovered a VM at 192.168.1.100
```

**Expected Result:**
- Agent uses default email from .env: `admin@example.com`
- Report will be sent to `admin@example.com`

---

## Test Scenario 3: Interactive Email Prompt

First, temporarily comment out USER_EMAIL in .env:
```bash
# USER_EMAIL=admin@example.com
```

Then run:
```bash
cd python/src
python main.py
```

When prompted, enter (without email):
```
I recovered a VM at 192.168.1.100
```

**Expected Result:**
- Agent will ask: "What email address should I send the validation report to?"
- You provide: `test@example.com`
- Report will be sent to `test@example.com`

---

## Test Scenario 4: Multiple Email Formats

Test different ways to specify email in natural language:

```bash
python main.py
```

Try these prompts:
1. `"Validate VM at 192.168.1.100, send report to admin@company.com"`
2. `"Check server 192.168.1.100, email me at ops@example.com"`
3. `"VM at 192.168.1.100, report to devops@company.com"`
4. `"192.168.1.100 VM validation, send to team@example.com"`

**Expected Result:**
- Email should be extracted from all formats
- Agent confirms: "Send a detailed report to [extracted-email]"

---

## Verify Email Configuration

Before testing, verify your SMTP settings in .env:

```bash
SMTP_SERVER=localhost
SMTP_PORT=25
EMAIL_FROM=recovery-validation@cyberres.com
```

### For Local Testing (No Real Email)

If you don't have an SMTP server, you can:

1. **Use Python's debugging SMTP server:**
   ```bash
   # In a separate terminal
   python -m smtpd -n -c DebuggingServer localhost:1025
   ```
   
   Then update .env:
   ```bash
   SMTP_PORT=1025
   ```

2. **Check logs instead:**
   ```bash
   tail -f recovery_validation.log | grep -i email
   ```

---

## Expected Output During Test

When you run main.py with email, you should see:

```
Agent 🤖: Perfect! I have all the information I need.

I will now:
1. Auto-discover resource details
2. Generate a validation plan
3. Execute validation checks
4. Evaluate results
5. Send a detailed report to [your-email@example.com]

Starting validation...
```

Later in the process:
```
📧 Sending report to [your-email@example.com]...
✓ Email report sent successfully
```

---

## Troubleshooting

### Email Not Extracted
If email is not being extracted from your prompt:
- Make sure email format is valid: `user@domain.com`
- Use explicit keywords: "send report to", "email me at"
- Check logs: `grep "Parsed:" recovery_validation.log`

### Email Not Sending
If email fails to send:
1. Check SMTP configuration in .env
2. Verify SMTP server is running
3. Check logs: `grep "email" recovery_validation.log`
4. For testing, use Python's debugging SMTP server (see above)

### Agent Not Asking for Email
If agent doesn't prompt for email when none is provided:
- Verify USER_EMAIL is commented out in .env
- Check that SEND_EMAIL=true in .env
- Review logs for any errors

---

## Quick Command Reference

```bash
# Start main.py
cd python/src
python main.py

# Monitor logs in real-time
tail -f recovery_validation.log

# Search for email-related logs
grep -i email recovery_validation.log

# Start debugging SMTP server (for testing)
python -m smtpd -n -c DebuggingServer localhost:1025
```

---

## Example Test Session

```bash
$ cd python/src
$ python main.py

==================================================================
  🔍 RECOVERY VALIDATION AGENT
  Validate recovered infrastructure resources
==================================================================

Agent 🤖: Welcome to the Recovery Validation Agent!
...
You can provide this information in natural language, for example:
- "I recovered a VM at 192.168.1.100, send report to admin@example.com"
...

You: I recovered a VM at 192.168.1.100, send report to test@mycompany.com

Agent 🤖: Perfect! I have all the information I need.

I will now:
1. Auto-discover resource details
2. Generate a validation plan
3. Execute validation checks
4. Evaluate results
5. Send a detailed report to test@mycompany.com

Starting validation...
```

---

## Notes

- The email feature works with all resource types (VM, Oracle, MongoDB)
- Email can be provided at any point during the conversation
- The system validates email format before accepting it
- All email activity is logged to `recovery_validation.log`

**Ready to test!** Start with Scenario 1 or 2 above.