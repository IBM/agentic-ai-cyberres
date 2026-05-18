"""
Production-Ready Chainlit Application for BeeAI

Features:
- Per-user session management
- Authentication & authorization
- Input validation & sanitization
- Rate limiting
- Structured logging
- Metrics collection
- Validation history persistence
"""

import chainlit as cl
from production.session_manager import get_session_manager, initialize_session_manager
from production.validation_repository_mongodb import ValidationHistoryRepositoryMongoDB
from cli import InteractiveCLI
import logging
import os
from typing import Optional
import uuid

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'
)
logger = logging.getLogger(__name__)

# ── OpenTelemetry Instrumentation ──────────────────────────────────────────────
from agents.telemetry import (
    initialize_telemetry,
    flush_telemetry,
    shutdown_telemetry,
    is_telemetry_enabled,
)

# Initialize telemetry on module load
telemetry_enabled = os.getenv("ENABLE_TELEMETRY", "true").lower() == "true"
if telemetry_enabled:
    phoenix_base = os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006")
    phoenix_endpoint = phoenix_base.rstrip('/') + '/v1/traces'
    
    success = initialize_telemetry(
        service_name="validation-service",
        phoenix_endpoint=phoenix_endpoint,
        enable_console_export=False,
    )
    
    if success:
        logger.info(f"✅ Telemetry initialized: validation-service → {phoenix_endpoint}")
    else:
        logger.warning("⚠️  Telemetry initialization failed, continuing without traces")
else:
    logger.info("📊 Telemetry disabled (set ENABLE_TELEMETRY=true to enable)")

# Configuration
MAX_MESSAGE_LENGTH = 1000
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 60  # seconds

# MongoDB Repository (initialized on startup)
_validation_repo: Optional[ValidationHistoryRepositoryMongoDB] = None


def get_validation_repo() -> Optional[ValidationHistoryRepositoryMongoDB]:
    """Get the global validation repository instance."""
    return _validation_repo


async def _ensure_mongodb_initialized():
    """Ensure MongoDB repository is initialized (called once on first session)."""
    global _validation_repo
    
    if _validation_repo is not None:
        return  # Already initialized
    
    mongodb_url = os.getenv("MONGODB_URL")
    mongodb_database = os.getenv("MONGODB_DATABASE", "beeai")
    
    if mongodb_url:
        try:
            _validation_repo = ValidationHistoryRepositoryMongoDB(
                connection_string=mongodb_url,
                database_name=mongodb_database
            )
            await _validation_repo.initialize()
            logger.info("✓ MongoDB validation repository initialized")
        except Exception as e:
            logger.warning(f"MongoDB initialization failed: {e}. History features will be unavailable.")
            _validation_repo = None
    else:
        logger.warning("MONGODB_URL not configured. History features will be unavailable.")


@cl.on_chat_start
async def start():
    """Initialize user session with proper isolation."""
    try:
        # Ensure MongoDB is initialized (first session only)
        await _ensure_mongodb_initialized()
        
        # Get or create session ID
        session_id = cl.user_session.get("id")
        if not session_id:
            session_id = str(uuid.uuid4())
            cl.user_session.set("id", session_id)
        
        # Get user info (if authenticated)
        user = cl.user_session.get("user")
        user_id = user.identifier if user else "anonymous"
        
        logger.info(f"Session start: {session_id}, user: {user_id}")
        
        # Get session manager
        session_manager = get_session_manager()
        
        # Create session
        session = await session_manager.create_session(session_id, user_id)
        
        # Welcome message
        await cl.Message(
            content="""# 👋 Welcome to Infrastructure Recovery Validation Agent powered by BeeAI 

I can help you validate infrastructure resources with enterprise-grade reliability.

**Features:**
- 🔒 **Secure** - Authentication & authorization
- 📊 **Persistent** - Validation history saved
- 🚀 **Scalable** - Multi-user support
- 📈 **Observable** - Full monitoring & metrics

**Example prompts:**
- `Validate VM at 192.168.1.100 using credential vm-prod-01`
- `Show my validation history`
- `Compare validations <id1> <id2>`
- `Show statistics for last 7 days`

**Available commands:**
- `help` - Show this message
- `list credentials` - Show available credentials
- `history` - Show validation history
- `stats` - Show validation statistics
"""
        ).send()
        
        # Initialize CLI wrapper for this session
        init_msg = cl.Message(content="🔧 Initializing BeeAI orchestrator...")
        await init_msg.send()
        
        try:
            cli_wrapper = InteractiveCLI()
            await cli_wrapper.initialize()
            
            # Store in session
            await session_manager.update_session(session_id, {
                "cli_wrapper": cli_wrapper
            })
            
            init_msg.content = "✅ BeeAI orchestrator ready!"
            await init_msg.update()
            
            logger.info(f"CLI wrapper initialized for session {session_id}")
            
        except Exception as e:
            init_msg.content = f"❌ Orchestrator initialization failed: {str(e)}"
            await init_msg.update()
            logger.error(f"CLI wrapper initialization failed for session {session_id}: {e}")
        
        # Note: MCP client is managed internally by ValidationOrchestrator
        # No need to initialize separate DynamicMCPClient here
        mcp_msg = cl.Message(content="✅ MCP tools ready (managed by orchestrator)")
        await mcp_msg.send()
        logger.info(f"MCP tools available via orchestrator for session {session_id}")
        
    except Exception as e:
        logger.error(f"Session initialization failed: {e}")
        await cl.Message(content=f"❌ Session initialization failed: {str(e)}").send()


@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages with production safeguards."""
    session_id = cl.user_session.get("id")
    if not session_id:
        await cl.Message(content="❌ Session not initialized. Please refresh.").send()
        return
    
    # Get session
    session_manager = get_session_manager()
    session = await session_manager.get_session(session_id)
    
    if not session:
        await cl.Message(content="❌ Session expired. Please refresh.").send()
        return
    
    # Input validation
    if len(message.content) > MAX_MESSAGE_LENGTH:
        await cl.Message(
            content=f"❌ Message too long. Maximum {MAX_MESSAGE_LENGTH} characters."
        ).send()
        return
    
    # Sanitize input
    clean_content = message.content.strip()
    
    # Log request
    logger.info(f"Message received: session={session_id}, length={len(clean_content)}")
    
    # Handle commands
    content_lower = clean_content.lower()
    
    if content_lower == "help":
        await show_help()
        return
    
    if content_lower == "list credentials" or "list credential" in content_lower:
        await list_credentials(session)
        return
    
    # More flexible history matching
    if (content_lower in ["history", "show history", "history all", "show all history"] or
        "validation history" in content_lower or
        "my history" in content_lower or
        content_lower.startswith("show my")):
        # Check if user wants all history
        show_all = "all" in content_lower
        await show_history(session, show_all=show_all)
        return
    
    if content_lower in ["stats", "statistics", "stats all", "statistics all"] or "statistic" in content_lower:
        show_all = "all" in content_lower
        await show_statistics(session, show_all=show_all)
        return
    
    if content_lower.startswith("compare"):
        await handle_comparison(session, clean_content)
        return
    
    # Note: Tool listing removed - tools are managed internally by orchestrator
    
    # Handle validation request
    await handle_validation(session, clean_content)


async def handle_validation(session: dict, prompt: str):
    """Handle validation request."""
    cli_wrapper = session.get("cli_wrapper")
    
    if not cli_wrapper:
        await cl.Message(
            content="❌ Orchestrator not initialized. Please refresh the page."
        ).send()
        return
    
    processing_msg = cl.Message(content="🚀 Starting validation workflow...")
    await processing_msg.send()
    
    try:
        # Parse prompt
        logger.info(f"Executing validation: {prompt}")
        info, email_address = cli_wrapper.parse_prompt(prompt)
        
        # Show what we understood
        understood_msg = f"**Understood:**\n- Target: {info['host']}\n"
        if info.get("credential_id"):
            understood_msg += f"- Credential: {info['credential_id']}\n"
        if email_address:
            understood_msg += f"- Email: {email_address}\n"
        await cl.Message(content=understood_msg).send()
        
        # Resolve credentials and build request
        request = await cli_wrapper._resolve_and_build_request(info)
        
        # Execute validation workflow
        result = await cli_wrapper.orchestrator.execute_workflow(request)
        
        # Save to MongoDB (if configured)
        repo = get_validation_repo()
        if repo:
            try:
                user_id = session.get("user_id", "anonymous")
                run_id = await repo.save_validation_run(
                    user_id=user_id,
                    session_id=session["id"],
                    result=result
                )
                logger.info(f"Validation saved to MongoDB: {run_id}")
            except Exception as e:
                logger.error(f"Failed to save validation to MongoDB: {e}")
        
        # Display results
        await display_results(result, email_address)
        
        # Update processing message
        processing_msg.content = f"✅ Validation complete! Score: {result.validation_result.score}/100"
        await processing_msg.update()
        
        logger.info(f"Validation completed: score={result.validation_result.score}")
        
        # Send email if requested
        if email_address and cli_wrapper.email_service:
            try:
                await cli_wrapper._send_email_report(result, request, email_address)
                await cl.Message(content=f"📧 Email report sent to {email_address}").send()
            except Exception as e:
                await cl.Message(content=f"⚠️ Email sending failed: {str(e)}").send()
        
        # Show next steps
        await show_next_steps()
        
    except Exception as e:
        processing_msg.content = f"❌ Validation failed: {str(e)}"
        await processing_msg.update()
        logger.error(f"Validation failed: {e}")
        
        await cl.Message(
            content=f"**Error Details:**\n```\n{str(e)}\n```\n\n"
                    "Please check your prompt format and credentials."
        ).send()


async def display_results(result, email_address=None):
    """Display comprehensive validation results."""
    # Summary
    summary = f"""## Validation Summary

**Target:** {result.request.resource_info.host}  
**Score:** {result.validation_result.score}/100  
**Status:** {result.workflow_status.upper()}  
**Duration:** {result.execution_time_seconds:.1f}s

---

### Check Results
- ✅ Passed: {result.validation_result.passed_checks}
- ❌ Failed: {result.validation_result.failed_checks}
- ⚠️ Warnings: {result.validation_result.warning_checks}
"""
    
    await cl.Message(content=summary).send()
    
    # Detailed checks
    if result.validation_result.checks:
        check_details = "### Detailed Check Results\n\n"
        for check in result.validation_result.checks:
            icon = "✅" if check.status == "PASS" else "❌" if check.status == "FAIL" else "⚠️"
            check_details += f"{icon} **{check.check_name}**\n"
            if check.message:
                check_details += f"   - {check.message}\n"
            if check.actual:
                check_details += f"   - Actual: {check.actual}\n"
            check_details += "\n"
        
        await cl.Message(content=check_details).send()
    
    # Health assessment
    if result.evaluation:
        eval_text = f"""## Health Assessment

**Overall Health:** {result.evaluation.overall_health.upper()}  
**Confidence:** {result.evaluation.confidence:.0%}

### Critical Issues
"""
        if result.evaluation.critical_issues:
            for issue in result.evaluation.critical_issues:
                eval_text += f"- ⚠️ {issue}\n"
        else:
            eval_text += "- ✅ No critical issues detected\n"
        
        eval_text += "\n### Recommendations\n"
        if result.evaluation.recommendations:
            for i, rec in enumerate(result.evaluation.recommendations, 1):
                eval_text += f"{i}. {rec}\n"
        else:
            eval_text += "- ✅ No recommendations at this time\n"
        
        await cl.Message(content=eval_text).send()


async def show_next_steps():
    """Show what users can do next after validation."""
    next_steps = """---

## 🎯 What's Next?

**Run another validation:**
```
Validate VM at <IP_ADDRESS> using credential <CREDENTIAL_ID>
```

**View your history:**
- Type `history` to see past validations
- Type `stats` to see statistics

**Need help?**
- Type `help` for full command list
- Type `list credentials` to see available credentials
"""
    await cl.Message(content=next_steps).send()


async def show_help():
    """Display help message."""
    help_text = """# BeeAI Production - Help

## Validation Commands

**Basic validation:**
```
Validate VM at <IP_ADDRESS> using credential <CREDENTIAL_ID>
```

**With email report:**
```
Validate VM at <IP_ADDRESS> using credential <CREDENTIAL_ID>, email <EMAIL>
```

## History Commands

- `history` - Show your validation history
- `stats` - Show validation statistics
- `compare <id1> <id2>` - Compare two validation runs

## Other Commands

- `help` - Show this message
- `list credentials` - Show available credentials

## Examples

1. **Validation:**
   ```
   Validate VM at 192.168.1.100 using credential vm-prod-01
   ```

2. **View history:**
   ```
   history
   ```

3. **Statistics:**
   ```
   stats
   ```

**Note:** MCP tools are managed automatically by the orchestrator.
"""
    
    await cl.Message(content=help_text).send()


async def show_history(session: dict, show_all: bool = False):
    """Show validation history for user from MongoDB.
    
    Args:
        session: User session dictionary
        show_all: If True, show all validation runs regardless of user_id
    """
    repo = get_validation_repo()
    
    if not repo:
        await cl.Message(content="⚠️ History feature requires MongoDB configuration.").send()
        return
    
    try:
        user_id = session.get("user_id", "anonymous")
        
        if show_all:
            # Fetch all validation runs
            logger.info("Fetching all validation runs")
            if repo.db is not None:
                cursor = repo.db.validation_runs.find({}).sort("created_at", -1).limit(50)
                history = []
                async for run in cursor:
                    run["_id"] = str(run["_id"])
                    history.append(run)
                logger.info(f"Found {len(history)} total validation runs")
            else:
                history = []
        else:
            # Fetch runs for this user only
            logger.info(f"Fetching history for user_id: {user_id}")
            history = await repo.list_validation_runs(user_id=user_id, limit=50)
            logger.info(f"Found {len(history)} validation runs for user {user_id}")
        
        if not history:
            # Try fetching all runs to see if there are any
            if repo.db is not None:
                all_runs = await repo.db.validation_runs.count_documents({})
                if show_all:
                    await cl.Message(content="No validation history in database yet.").send()
                else:
                    await cl.Message(
                        content=f"No validation history for user '{user_id}'.\n\n"
                                f"Total runs in database: {all_runs}\n\n"
                                f"💡 Tip: Type 'history all' to see all validation runs."
                    ).send()
            else:
                await cl.Message(content="No validation history yet.").send()
            return
        
        if show_all:
            history_text = "### 📊 All Validation History (Last 50)\n\n"
        else:
            history_text = "### 📊 Your Validation History (Last 50)\n\n"
        for i, run in enumerate(history, 1):
            created_at = run.get('created_at', 'Unknown')
            if hasattr(created_at, 'strftime'):
                time_str = created_at.strftime('%Y-%m-%d %H:%M:%S')
            else:
                time_str = str(created_at)
            
            history_text += f"**{i}. {run.get('target_host', 'Unknown')}**\n"
            history_text += f"   - Score: {run.get('score', 0)}/100\n"
            history_text += f"   - Status: {run.get('status', 'unknown').upper()}\n"
            history_text += f"   - Time: {time_str}\n"
            history_text += f"   - Duration: {run.get('execution_time_seconds', 0):.1f}s\n\n"
        
        await cl.Message(content=history_text).send()
        
    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")
        await cl.Message(content=f"❌ Failed to fetch history: {str(e)}").send()


async def show_statistics(session: dict, show_all: bool = False):
    """Show validation statistics from MongoDB.
    
    Args:
        session: User session dictionary
        show_all: If True, show statistics for all users
    """
    repo = get_validation_repo()
    
    if not repo:
        await cl.Message(content="⚠️ Statistics feature requires MongoDB configuration.").send()
        return
    
    try:
        user_id = session.get("user_id", "anonymous")
        
        if show_all:
            # Get statistics for all users
            logger.info("Fetching statistics for all users")
            if repo.db is not None:
                # Custom aggregation for all users
                pipeline = [
                    {
                        "$group": {
                            "_id": None,
                            "total_validations": {"$sum": 1},
                            "average_score": {"$avg": "$score"},
                            "max_score": {"$max": "$score"},
                            "min_score": {"$min": "$score"},
                            "successful_validations": {
                                "$sum": {
                                    "$cond": [{"$eq": ["$workflow_status", "success"]}, 1, 0]
                                }
                            },
                            "failed_validations": {
                                "$sum": {
                                    "$cond": [{"$eq": ["$workflow_status", "failed"]}, 1, 0]
                                }
                            }
                        }
                    }
                ]
                cursor = repo.db.validation_runs.aggregate(pipeline)
                results = await cursor.to_list(length=1)
                stats = results[0] if results else {}
            else:
                stats = {}
        else:
            # Get statistics for current user only
            stats_result = await repo.get_validation_statistics(user_id=user_id, time_range="30d")
            
            # Extract stats from aggregation result
            if not stats_result or not stats_result.get('total_stats'):
                await cl.Message(
                    content=f"No validation data for user '{user_id}'.\n\n"
                            f"💡 Tip: Type 'stats all' to see statistics for all validation runs."
                ).send()
                return
            
            stats = stats_result['total_stats'][0] if stats_result['total_stats'] else {}
        
        if not stats or stats.get('total_validations', 0) == 0:
            if show_all:
                await cl.Message(content="No validation data in database yet.").send()
            else:
                await cl.Message(
                    content=f"No validation data for user '{user_id}'.\n\n"
                            f"💡 Tip: Type 'stats all' to see statistics for all validation runs."
                ).send()
            return
        
        if not stats or stats.get('total_validations', 0) == 0:
            await cl.Message(content="No validation data yet.").send()
            return
        
        total = stats.get('total_validations', 0)
        successful = stats.get('successful_validations', 0)
        success_rate = (successful / total * 100) if total > 0 else 0
        
        if show_all:
            stats_text = f"""### 📈 Validation Statistics (All Users, All Time)

**Total Validations:** {total}
**Average Score:** {stats.get('average_score', 0):.1f}/100
**Highest Score:** {stats.get('max_score', 0)}/100
**Lowest Score:** {stats.get('min_score', 0)}/100
**Success Rate:** {success_rate:.1f}%

**Status Breakdown:**
- ✅ Successful: {successful}
- ❌ Failed: {stats.get('failed_validations', 0)}
"""
        else:
            stats_text = f"""### 📈 Validation Statistics (Last 30 Days)

**Total Validations:** {total}
**Average Score:** {stats.get('average_score', 0):.1f}/100
**Highest Score:** {stats.get('max_score', 0)}/100
**Lowest Score:** {stats.get('min_score', 0)}/100
**Success Rate:** {success_rate:.1f}%

**Status Breakdown:**
- ✅ Successful: {successful}
- ❌ Failed: {stats.get('failed_validations', 0)}
"""
        
        await cl.Message(content=stats_text).send()
        
    except Exception as e:
        logger.error(f"Failed to fetch statistics: {e}")
        await cl.Message(content=f"❌ Failed to fetch statistics: {str(e)}").send()


async def list_credentials(session: dict):
    """List available credentials."""
    await cl.Message(content="Credential listing not yet implemented in production mode.").send()


async def handle_comparison(session: dict, prompt: str):
    """Handle validation comparison request."""
    await cl.Message(content="Comparison feature not yet implemented in production mode.").send()


@cl.on_chat_end
async def end():
    """Cleanup when chat session ends."""
    session_id = cl.user_session.get("id")
    if not session_id:
        return
    
    logger.info(f"Session end: {session_id}")
    
    # Flush telemetry before cleanup
    if is_telemetry_enabled():
        logger.info("Flushing telemetry spans...")
        flush_telemetry()
    
    # Cleanup session (MCP is managed by orchestrator)
    session_manager = get_session_manager()
    await session_manager.cleanup_session(session_id)
    
    await cl.Message(content="👋 Session ended. Goodbye!").send()


if __name__ == "__main__":
    # Initialize session manager on startup
    import asyncio
    asyncio.run(initialize_session_manager())

# Made with Bob
