# Email Fix Plan

## Issues Identified

1. **Email not being sent** - The orchestrated workflow doesn't send emails
2. **Report displayed twice** - Report shown in both reporting agent and main workflow
3. **Template used instead of LLM** - "Simple case" detection bypasses AI report generation

## Root Causes

### Issue 1: Email Not Sent
- `run_mcp_centric_validation()` doesn't accept email_recipient parameter
- `run_interactive()` doesn't extract email from user input
- No email sending logic after report generation in orchestrated workflow

### Issue 2: Duplicate Report
- Line 691: `write_progress(detailed_report)` displays full report
- Line 725-726: Additional score/summary displayed after report
- Both outputs appear in logs

### Issue 3: Template vs LLM
- `reporting_agent.py` line 302: `_is_simple_report()` detects "simple cases"
- When all checks pass and there are few checks, it skips LLM
- Line 303: "Simple report detected - using template (no LLM needed)"

## Fixes to Apply

### Fix 1: Add Email Support to Orchestrated Workflow

**File:** `recovery_validation_agent.py`

**Changes:**
1. Update `run_mcp_centric_validation()` signature to accept `email_recipient`
2. Update `run_interactive()` to extract email from parsed input
3. Add email sending logic after report generation (around line 730)
4. Update validation request to include email settings (line 620)

**Code locations:**
- Line 345: Add `email_recipient` parameter
- Line 612-621: Update ValidationRequest with email settings
- Line 730: Add email sending after report generation
- Line 770: Extract email from parsed input
- Line 847: Pass email to validation function

### Fix 2: Remove Duplicate Report Display

**File:** `recovery_validation_agent.py`

**Changes:**
1. Remove duplicate score/summary display (lines 725-726)
2. Keep only the comprehensive report display (line 691)

**Code locations:**
- Line 725-726: Remove `write_progress(f"Score: {score}/100")` and separator

### Fix 3: Disable "Simple Case" Detection for AI Reports

**File:** `agents/reporting_agent.py`

**Changes:**
1. Disable smart_llm_usage feature flag check
2. Always use LLM when AI reporting is enabled
3. Or adjust `_is_simple_report()` logic to be less aggressive

**Code locations:**
- Line 301-304: Comment out or modify simple case detection
- Alternative: Line 398: Make `_is_simple_report()` return False

## Implementation Order

1. **Fix 3 first** - Ensure LLM is used for reports
2. **Fix 2 second** - Clean up duplicate output
3. **Fix 1 last** - Add email functionality

This order ensures we see proper reports before adding email.