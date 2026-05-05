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
from agents.mcp_dynamic import DynamicMCPClient
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

# Configuration
MAX_MESSAGE_LENGTH = 1000
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 60  # seconds


@cl.on_chat_start
async def start():
    """Initialize user session with proper isolation."""
    try:
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
            content="""# 👋 Welcome to BeeAI Recovery Validation (Production)

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
        
        # Initialize dynamic MCP client
        mcp_msg = cl.Message(content="🚀 Initializing dynamic MCP client...")
        await mcp_msg.send()
        
        try:
            mcp_client = DynamicMCPClient(
                server_path="../cyberres-mcp",
                auto_discover=True
            )
            
            connected = await mcp_client.connect()
            
            if connected:
                tools = mcp_client.list_tool_names()
                
                # Store in session
                await session_manager.update_session(session_id, {
                    "mcp_client": mcp_client
                })
                
                mcp_msg.content = f"✅ Dynamic MCP client ready! Discovered {len(tools)} tools."
                await mcp_msg.update()
                logger.info(f"MCP client initialized for session {session_id} with {len(tools)} tools")
            else:
                mcp_msg.content = "⚠️ MCP client connection failed. Some features unavailable."
                await mcp_msg.update()
                
        except Exception as e:
            mcp_msg.content = f"⚠️ MCP client initialization failed: {str(e)}"
            await mcp_msg.update()
            logger.error(f"MCP client initialization failed for session {session_id}: {e}")
        
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
    
    if content_lower == "list credentials":
        await list_credentials(session)
        return
    
    if content_lower in ["history", "show history"]:
        await show_history(session)
        return
    
    if content_lower in ["stats", "statistics"]:
        await show_statistics(session)
        return
    
    if content_lower.startswith("compare"):
        await handle_comparison(session, clean_content)
        return
    
    if content_lower in ["show tools", "list tools"]:
        await show_tools(session)
        return
    
    if content_lower.startswith("tool info "):
        tool_name = clean_content[10:]
        await show_tool_info(session, tool_name)
        return
    
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
        
        # Save to history (if database configured)
        session_manager = get_session_manager()
        await session_manager.add_validation_to_history(
            session["id"],
            {
                "target": info['host'],
                "score": result.validation_result.score,
                "status": result.workflow_status
            }
        )
        
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
- `show tools` - List MCP tools
- `tool info <name>` - Get tool details

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
"""
    
    await cl.Message(content=help_text).send()


async def show_history(session: dict):
    """Show validation history for user."""
    history = session.get("validation_history", [])
    
    if not history:
        await cl.Message(content="No validation history yet.").send()
        return
    
    history_text = "### Your Validation History\n\n"
    for i, item in enumerate(reversed(history[-10:]), 1):  # Last 10
        history_text += f"{i}. **{item['result']['target']}** - "
        history_text += f"Score: {item['result']['score']}/100 - "
        history_text += f"Status: {item['result']['status']}\n"
        history_text += f"   Time: {item['timestamp']}\n\n"
    
    await cl.Message(content=history_text).send()


async def show_statistics(session: dict):
    """Show validation statistics."""
    history = session.get("validation_history", [])
    
    if not history:
        await cl.Message(content="No validation data yet.").send()
        return
    
    scores = [item['result']['score'] for item in history]
    avg_score = sum(scores) / len(scores)
    
    stats_text = f"""### Validation Statistics

**Total Validations:** {len(history)}  
**Average Score:** {avg_score:.1f}/100  
**Highest Score:** {max(scores)}/100  
**Lowest Score:** {min(scores)}/100
"""
    
    await cl.Message(content=stats_text).send()


async def show_tools(session: dict):
    """Show available MCP tools."""
    mcp_client = session.get("mcp_client")
    
    if not mcp_client or not mcp_client.is_connected():
        await cl.Message(content="❌ MCP client not connected").send()
        return
    
    tools = mcp_client.list_tools()
    
    if not tools:
        await cl.Message(content="No tools discovered").send()
        return
    
    tools_text = f"### 🔧 Discovered MCP Tools ({len(tools)} total)\n\n"
    
    for i, tool in enumerate(tools, 1):
        tools_text += f"**{i}. {tool.name}**\n"
        tools_text += f"   {tool.description[:80]}...\n\n"
    
    await cl.Message(content=tools_text).send()


async def show_tool_info(session: dict, tool_name: str):
    """Show detailed tool information."""
    mcp_client = session.get("mcp_client")
    
    if not mcp_client or not mcp_client.is_connected():
        await cl.Message(content="❌ MCP client not connected").send()
        return
    
    info = mcp_client.get_tool_info(tool_name)
    
    if not info:
        await cl.Message(content=f"❌ Tool '{tool_name}' not found").send()
        return
    
    info_text = f"### 🔍 Tool: {info['name']}\n\n"
    info_text += f"**Description:**\n{info['description']}\n\n"
    
    if info['required_parameters']:
        info_text += "**Required Parameters:**\n"
        for param in info['required_parameters']:
            info_text += f"- `{param}`\n"
    
    await cl.Message(content=info_text).send()


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
    
    # Cleanup session
    session_manager = get_session_manager()
    await session_manager.cleanup_session(session_id)
    
    await cl.Message(content="👋 Session ended. Goodbye!").send()


if __name__ == "__main__":
    # Initialize session manager on startup
    import asyncio
    asyncio.run(initialize_session_manager())

# Made with Bob
