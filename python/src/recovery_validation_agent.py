#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Main orchestrator for recovery validation agent."""

import asyncio
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime

from models import (
    ValidationRequest,
    ValidationReport,
    ResourceValidationResult,
    CredentialSource,
    ResourceType
)
from credentials import get_credential_manager
from mcp_stdio_client import MCPStdioClient, MCPClientError
from discovery import ResourceDiscovery
from planner import ValidationPlanner
from executor import ValidationExecutor
from evaluator import ResultEvaluator
from report_generator import ReportGenerator
from email_service import EmailService
from conversation import ConversationHandler

logger = logging.getLogger(__name__)


class RecoveryValidationAgent:
    """Main orchestrator for recovery validation."""
    
    def __init__(self):
        """Initialize recovery validation agent."""
        self.credential_manager = get_credential_manager()
        self.conversation_handler = ConversationHandler()
        self.planner = ValidationPlanner()
        self.evaluator = ResultEvaluator()
        self.report_generator = ReportGenerator()
        self.mcp_client: Optional[MCPStdioClient] = None
        
        # Get email config
        email_config = self.credential_manager.get_email_config()
        self.email_service = EmailService(
            smtp_server=email_config["smtp_server"],
            smtp_port=int(email_config["smtp_port"]),
            from_address=email_config["from_address"],
            smtp_username=email_config.get("smtp_username"),
            smtp_password=email_config.get("smtp_password"),
            use_tls=email_config.get("use_tls", False)
        )
        self.default_email_recipient = email_config["recipient"]
    
    async def connect_mcp(self) -> None:
        """Connect to MCP server and discover available tools."""
        if self.mcp_client is not None:
            logger.warning("MCP client already connected")
            return
        
        logger.info("Connecting to MCP server...")
        
        # Get the absolute path to the MCP server directory
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        mcp_server_dir = os.path.join(current_dir, "..", "cyberres-mcp")
        mcp_server_dir = os.path.abspath(mcp_server_dir)
        
        # Use the same command as Claude Desktop config with stdio transport
        self.mcp_client = MCPStdioClient(
            server_command="uv",
            server_args=["--directory", mcp_server_dir, "run", "cyberres-mcp"],
            server_env={"MCP_TRANSPORT": "stdio"}  # Force stdio transport
        )
        
        await self.mcp_client.connect()
        logger.info(f"✓ Connected to MCP server, discovered {len(self.mcp_client.get_available_tools())} tools")
    
    async def disconnect_mcp(self) -> None:
        """Disconnect from MCP server."""
        if self.mcp_client is not None:
            await self.mcp_client.disconnect()
            self.mcp_client = None
            logger.info("Disconnected from MCP server")
    
    async def gather_information_interactive(self, reader) -> Optional[ValidationRequest]:
        """Gather resource information through interactive conversation.
        
        Args:
            reader: Console reader for user interaction
        
        Returns:
            ValidationRequest or None if cancelled
        """
        # Show initial prompt
        reader.write("Agent 🤖", self.conversation_handler.get_initial_prompt())
        
        collected_info = {}
        resource_type = None
        
        # Get initial input
        async for prompt_data in reader:
            user_input = prompt_data["prompt"]
            
            if user_input.lower() in ["exit", "quit", "cancel"]:
                reader.write("Agent 🤖", "Validation cancelled.")
                return None
            
            # Parse initial input
            if resource_type is None:
                parsed = await self.conversation_handler.parse_initial_input(user_input)
                resource_type = parsed.get("resource_type")
                host = parsed.get("host")
                
                if not resource_type or not host:
                    reader.write(
                        "Agent 🤖",
                        "I couldn't determine the resource type or host. Please specify:\n"
                        "- Resource type: VM, Oracle, or MongoDB\n"
                        "- Host: IP address or hostname"
                    )
                    continue
                
                collected_info["host"] = host
                collected_info["resource_type"] = resource_type
                
                reader.write(
                    "Agent 🤖",
                    f"Great! I'll help you validate a {resource_type.value.upper()} at {host}.\n\n"
                    f"Now I need some additional information:\n" +
                    "\n".join(f"- {q}" for q in self.conversation_handler.get_follow_up_questions(resource_type))
                )
                continue
            
            # Parse credentials and additional info
            creds = await self.conversation_handler.parse_credentials(user_input, resource_type)
            collected_info.update(creds)
            
            # Check for missing fields
            missing = self.conversation_handler.get_missing_fields(resource_type, collected_info)
            
            if missing:
                # Try to fill from environment
                env_creds = self.credential_manager.merge_with_user_provided(
                    resource_type.value,
                    collected_info,
                    collected_info.get("host")
                )
                collected_info.update(env_creds)
                
                # Check again
                missing = self.conversation_handler.get_missing_fields(resource_type, collected_info)
                
                if missing:
                    reader.write(
                        "Agent 🤖",
                        self.conversation_handler.format_missing_fields_message(missing) +
                        "\n\nPlease provide the missing information."
                    )
                    continue
            
            # All information collected
            try:
                resource_info = self.conversation_handler.build_resource_info(
                    resource_type,
                    collected_info
                )
                
                # Determine email recipient: use user-provided email or fall back to default
                email_recipient = collected_info.get("email_recipient") or self.default_email_recipient
                
                # Ask for email if not provided and not in environment
                if not email_recipient:
                    reader.write(
                        "Agent 🤖",
                        "What email address should I send the validation report to?"
                    )
                    continue
                
                # Create validation request
                validation_request = ValidationRequest(
                    resource_info=resource_info,
                    credential_source=CredentialSource.USER_PROVIDED,
                    auto_discover=True,
                    send_email=True,
                    email_recipient=email_recipient
                )
                
                reader.write(
                    "Agent 🤖",
                    f"Perfect! I have all the information I need.\n\n"
                    f"I will now:\n"
                    f"1. Auto-discover resource details\n"
                    f"2. Generate a validation plan\n"
                    f"3. Execute validation checks\n"
                    f"4. Evaluate results\n"
                    f"5. Send a detailed report to {email_recipient}\n\n"
                    f"Starting validation..."
                )
                
                return validation_request
                
            except Exception as e:
                reader.write("Agent 🤖", f"Error building request: {e}\nPlease try again.")
                continue
        
        return None
    
    async def run_validation(
        self,
        validation_request: ValidationRequest,
        reader=None
    ) -> ValidationReport:
        """Run complete validation workflow.
        
        Args:
            validation_request: Validation request
            reader: Optional console reader for progress updates
        
        Returns:
            ValidationReport
        """
        start_time = time.time()
        
        def write_progress(message: str):
            """Write progress message."""
            if reader:
                reader.write("Agent 🤖", message)
            logger.info(message)
        
        try:
            # Connect to MCP server if not already connected
            if self.mcp_client is None:
                write_progress("Connecting to MCP server...")
                await self.connect_mcp()
            
            write_progress(f"✓ Connected to MCP server ({len(self.mcp_client.get_available_tools())} tools available)")
            
            # Auto-discovery
            if validation_request.auto_discover:
                write_progress(f"🔍 Discovering {validation_request.resource_info.resource_type.value} details...")
                discovery = ResourceDiscovery(self.mcp_client)
                discovery_info = await discovery.discover(validation_request.resource_info)
                
                if discovery_info.get("errors"):
                    write_progress(f"⚠ Discovery warnings: {len(discovery_info['errors'])} issues found")
                else:
                    write_progress("✓ Discovery completed successfully")
            else:
                discovery_info = None
            
            # Generate validation plan
            write_progress("📋 Generating validation plan...")
            plan = self.planner.generate_plan(validation_request.resource_info)
            write_progress(f"✓ Validation plan created with {len(plan)} steps")
            
            # Execute validation
            write_progress(f"🔧 Executing validation ({len(plan)} checks)...")
            executor = ValidationExecutor(self.mcp_client)
            results = await executor.execute_plan(plan)
            
            summary = executor.get_execution_summary(results)
            write_progress(
                f"✓ Validation completed: {summary['successful_steps']}/{summary['total_steps']} checks passed"
            )
            
            # Evaluate results
            write_progress("📊 Evaluating results against acceptance criteria...")
            validation_result = self.evaluator.evaluate(
                validation_request.resource_info.resource_type,
                results,
                validation_request.custom_acceptance_criteria
            )
            
            # Add discovery info to result
            if discovery_info:
                validation_result.discovery_info = discovery_info
            
            write_progress(
                f"✓ Evaluation complete: {validation_result.overall_status.value} "
                f"(Score: {validation_result.score}/100)"
            )
            
            # Generate recommendations
            write_progress("💡 Generating recommendations...")
            report = ValidationReport(
                request=validation_request,
                result=validation_result
            )
            report.recommendations = self.report_generator.generate_recommendations(report)
            write_progress(f"✓ Generated {len(report.recommendations)} recommendations")
            
            # Send email if requested
            if validation_request.send_email and validation_request.email_recipient:
                write_progress(f"📧 Sending report to {validation_request.email_recipient}...")
                email_sent = self.email_service.send_validation_report(
                    report,
                    validation_request.email_recipient
                )
                if email_sent:
                    write_progress("✓ Email report sent successfully")
                else:
                    write_progress("⚠ Failed to send email report")
            
            # Display summary
            write_progress("\n" + "=" * 60)
            write_progress("VALIDATION SUMMARY")
            write_progress("=" * 60)
            write_progress(report.to_summary())
            write_progress("=" * 60)
            
            execution_time = time.time() - start_time
            logger.info("=" * 70)
            logger.info(f"🎭 orchestrator_agent - Workflow completed in {execution_time:.2f}s")
            logger.info("=" * 70)
            write_progress(f"\n✓ Total execution time: {execution_time:.2f} seconds")
            
            return report
                
        except MCPClientError as e:
            error_msg = f"MCP client error: {e}"
            logger.error(error_msg)
            if reader:
                reader.write("Error ❌", error_msg)
            raise
        except Exception as e:
            error_msg = f"Validation error: {e}"
            logger.error(error_msg, exc_info=True)
            if reader:
                reader.write("Error ❌", error_msg)
    async def run_mcp_centric_validation(
        self,
        ssh_creds: Dict[str, str],
        reader=None,
        email_recipient: Optional[str] = None
    ) -> ValidationReport:
        """Run MCP-centric validation workflow with LLM-driven tool selection.
        
        This is the new workflow that follows MCP best practices:
        1. User provides only hostname + SSH credentials
        2. Agent discovers OS and applications automatically
        3. LLM intelligently selects appropriate validation tools
        4. Agent runs validations and generates report
        
        Args:
            ssh_creds: SSH credentials (hostname, username, password/key)
            reader: Optional console reader for progress updates
        
        Returns:
            ValidationReport
        """
        from llm_tool_selector import LLMToolSelector
        
        start_time = time.time()
        
        def write_progress(message: str):
            """Write progress message."""
            if reader:
                reader.write("Agent 🤖", message)
            logger.info(message)
        
        try:
            # Log orchestration start
            logger.info("=" * 70)
            logger.info("🎭 ORCHESTRATED VALIDATION WORKFLOW STARTING")
            logger.info("=" * 70)
            logger.info(f"🎭 orchestrator_agent - Coordinating multi-agent validation workflow")
            logger.info(f"🎭 orchestrator_agent - Target: {ssh_creds['hostname']}")
            
            # Connect to MCP server if not already connected
            if self.mcp_client is None:
                write_progress("Connecting to MCP server...")
                await self.connect_mcp()
            
            write_progress(f"✓ Connected to MCP server ({len(self.mcp_client.get_available_tools())} tools available)")
            
            # Step 1: Discover OS
            logger.info("🎭 discovery_agent - Phase 1: OS Discovery")
            write_progress(f"🔍 Discovering operating system on {ssh_creds['hostname']}...")
            try:
                # Map parameters correctly for MCP tools
                mcp_params = {
                    "host": ssh_creds["hostname"],
                    "ssh_user": ssh_creds["username"],
                    "ssh_password": ssh_creds.get("password"),
                    "ssh_key_path": ssh_creds.get("ssh_key_path"),
                    "ssh_port": ssh_creds.get("ssh_port", 22)
                }
                
                os_result = await self.mcp_client.call_tool("discover_os_only", mcp_params)
                
                # Extract OS info from result
                if isinstance(os_result, dict) and "data" in os_result:
                    os_info = os_result["data"]
                elif isinstance(os_result, dict):
                    os_info = os_result
                else:
                    os_info = {}
                
                dist = os_info.get('distribution', 'Unknown')
                version = os_info.get('version', '')
                write_progress(f"✓ Detected: {dist} {version}")
            except Exception as e:
                logger.error(f"OS discovery failed: {e}")
                os_info = {"error": str(e)}
                write_progress(f"⚠ OS discovery failed: {e}")
            
            # Step 2: Discover applications
            logger.info("🎭 discovery_agent - Phase 2: Application Discovery")
            write_progress("🔍 Discovering applications and services...")
            try:
                apps_result = await self.mcp_client.call_tool("discover_applications", mcp_params)
                
                # Extract applications from MCP result
                # MCP tools return: {"ok": true, "data": {...}} or {"ok": false, "error": "..."}
                discovered_apps = []
                
                if isinstance(apps_result, dict):
                    # Check if it's a successful MCP response
                    if apps_result.get("ok") and "data" in apps_result:
                        data = apps_result["data"]
                        discovered_apps = data.get("applications", [])
                        logger.info(f"Successfully discovered {len(discovered_apps)} applications")
                    # Check if it's already unwrapped data
                    elif "applications" in apps_result:
                        discovered_apps = apps_result.get("applications", [])
                        logger.info(f"Found {len(discovered_apps)} applications in unwrapped response")
                    # Check for error response
                    elif not apps_result.get("ok", True):
                        error_msg = apps_result.get("error", "Unknown error")
                        logger.warning(f"Application discovery returned error: {error_msg}")
                        write_progress(f"⚠ Application discovery error: {error_msg}")
                
                if discovered_apps:
                    write_progress(f"✓ Found {len(discovered_apps)} applications:")
                    for app in discovered_apps[:5]:  # Show first 5
                        confidence = app.get("confidence", "unknown")
                        version = app.get("version", "unknown version")
                        write_progress(f"  - {app.get('name', 'unknown')} {version} (confidence: {confidence})")
                    if len(discovered_apps) > 5:
                        write_progress(f"  ... and {len(discovered_apps) - 5} more")
                else:
                    write_progress("⚠ No applications discovered")
                    logger.warning("Application discovery returned no applications")
            except Exception as e:
                logger.error(f"Application discovery failed: {e}", exc_info=True)
                discovered_apps = []
                write_progress(f"⚠ Application discovery failed: {e}")
            
            # Step 3: Get tool descriptions from MCP
            logger.info("🎭 classification_agent - Phase 3: Tool Classification")
            write_progress("📋 Getting tool descriptions from MCP server...")
            try:
                tools_list = await self.mcp_client.list_tools()
                available_tools = [
                    {
                        "name": tool.name,
                        "description": tool.description or "No description available",
                        "parameters": tool.inputSchema.get("properties", {}) if hasattr(tool, 'inputSchema') else {}
                    }
                    for tool in tools_list
                ]
                write_progress(f"✓ Retrieved {len(available_tools)} tool descriptions")
            except Exception as e:
                logger.error(f"Failed to get tool descriptions: {e}")
                # Fallback to tool names only
                available_tools = [
                    {"name": name, "description": "No description", "parameters": {}}
                    for name in self.mcp_client.get_available_tools()
                ]
            
            # Step 4: Gather available credentials
            logger.info("🎭 classification_agent - Phase 4: Credential Analysis")
            write_progress("🔑 Checking available credentials...")
            available_credentials = {"ssh": ssh_creds}
            
            # Try to get app-specific credentials
            for app in discovered_apps:
                app_name = app.get("name", "").lower().split()[0]
                try:
                    app_creds = self.credential_manager.get_credentials(
                        resource_type=f"db_{app_name}",
                        hostname=ssh_creds["hostname"]
                    )
                    if app_creds:
                        available_credentials[f"{app_name}_db"] = app_creds
                        write_progress(f"  ✓ Found {app_name} database credentials")
                except Exception:
                    pass  # No credentials available for this app
            
            # Step 5: LLM-driven tool selection
            logger.info("🎭 classification_agent - Phase 5: LLM-Driven Tool Selection")
            write_progress("🤖 Using LLM to select validation tools...")
            llm_selector = LLMToolSelector()
            validation_goal = f"Validate infrastructure and applications on {ssh_creds['hostname']}"
            
            selected_tools, summary = await llm_selector.select_tools(
                discovered_apps=discovered_apps,
                available_tools=available_tools,
                available_credentials=available_credentials,
                validation_goal=validation_goal
            )
            
            write_progress(f"✓ LLM selected {len(selected_tools)} tools:")
            write_progress(f"  - Can execute: {summary.tools_can_execute}")
            write_progress(f"  - Blocked by credentials: {summary.tools_blocked_by_credentials}")
            write_progress(f"  - Recommendation: {summary.recommendation}")
            
            # Step 6: Run validations (only executable tools)
            logger.info("🎭 validation_agent - Phase 6: Executing Validations")
            executable_tools = [t for t in selected_tools if t.can_execute]
            write_progress(f"⚡ Running {len(executable_tools)} validations...")
            validation_results = []
            
            for i, tool_selection in enumerate(executable_tools, 1):
                try:
                    write_progress(f"  [{i}/{len(executable_tools)}] {tool_selection.tool_name}")
                    write_progress(f"    Reason: {tool_selection.reasoning}")
                    
                    result = await self.mcp_client.call_tool(
                        tool_selection.tool_name,
                        tool_selection.parameters
                    )
                    validation_results.append({
                        "tool": tool_selection.tool_name,
                        "priority": tool_selection.priority,
                        "reasoning": tool_selection.reasoning,
                        "result": result,
                        "status": "success"
                    })
                    write_progress(f"    ✓ Success")
                except Exception as e:
                    logger.error(f"Validation {tool_selection.tool_name} failed: {e}")
                    validation_results.append({
                        "tool": tool_selection.tool_name,
                        "priority": tool_selection.priority,
                        "reasoning": tool_selection.reasoning,
                        "error": str(e),
                        "status": "failed"
                    })
                    write_progress(f"    ✗ Failed: {str(e)[:100]}")
            
            # Log skipped tools
            skipped_tools = [t for t in selected_tools if not t.can_execute]
            if skipped_tools:
                write_progress(f"\n⏭️  Skipped {len(skipped_tools)} tools (missing credentials):")
                for tool in skipped_tools[:3]:  # Show first 3
                    write_progress(f"  - {tool.tool_name}: {tool.reasoning}")
                if len(skipped_tools) > 3:
                    write_progress(f"  ... and {len(skipped_tools) - 3} more")
            
            successful = len([r for r in validation_results if r["status"] == "success"])
            logger.info(f"🎭 validation_agent - Validations complete: {successful}/{len(validation_results)} successful")
            write_progress(f"✓ Validations completed: {successful}/{len(validation_results)} successful")
            
            # Step 7: Generate comprehensive report using AI-powered reporting agent
            logger.info("🎭 report_generation_agent - Phase 7: AI-Powered Report Generation")
            write_progress("📊 Generating comprehensive validation report...")
            
            # Create a simplified validation report
            from models import ValidationReport, ResourceValidationResult, ValidationStatus, CheckResult
            
            # Determine overall status
            if successful == len(validation_results):
                overall_status = ValidationStatus.PASS
            elif successful == 0:
                overall_status = ValidationStatus.FAIL
            else:
                overall_status = ValidationStatus.WARNING
            
            # Calculate score
            score = int((successful / len(validation_results)) * 100) if validation_results else 0
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Convert validation results to CheckResult format
            checks = []
            for i, val_result in enumerate(validation_results):
                check_status = ValidationStatus.PASS if val_result["status"] == "success" else ValidationStatus.FAIL
                checks.append(CheckResult(
                    check_id=f"check_{i+1}",
                    check_name=val_result["tool"],
                    status=check_status,
                    message=val_result.get("reasoning", ""),
                    details=val_result.get("result") if val_result["status"] == "success" else {"error": val_result.get("error")}
                ))
            
            # Create validation result with all required fields
            validation_result = ResourceValidationResult(
                resource_type=ResourceType.VM,
                resource_host=ssh_creds["hostname"],
                overall_status=overall_status,
                score=score,
                checks=checks,
                execution_time_seconds=execution_time,
                discovery_info={
                    "os": os_info,
                    "applications": discovered_apps,
                    "tool_selection": {
                        "total_tools": len(selected_tools),
                        "executable_tools": len(executable_tools),
                        "skipped_tools": len(skipped_tools),
                        "llm_recommendation": summary.recommendation
                    },
                    "validation_results": validation_results
                }
            )
            
            # Create validation request (for report)
            from models import ValidationRequest, VMResourceInfo, CredentialSource
            validation_request = ValidationRequest(
                resource_info=VMResourceInfo(
                    resource_type=ResourceType.VM,
                    host=ssh_creds["hostname"],
                    ssh_user=ssh_creds["username"]
                ),
                credential_source=CredentialSource.USER_PROVIDED,
                auto_discover=True,
                send_email=bool(email_recipient),
                email_recipient=email_recipient
            )
            
            report = ValidationReport(
                request=validation_request,
                result=validation_result
            )
            
            # Store the detailed report for email
            detailed_report_text = None
            
            # Try to use AI-powered reporting agent if available
            try:
                from agents.reporting_agent import ReportingAgent
                from feature_flags import FeatureFlags
                
                # Check if AI reporting is enabled
                feature_flags = FeatureFlags()
                if feature_flags.is_enabled("ai_reporting"):
                    write_progress("💡 Using AI-powered report generation...")
                    logger.info("🎭 report_generation_agent - AI reporting enabled")
                    
                    reporting_agent = ReportingAgent()
                    
                    # Convert discovered apps to WorkloadDiscoveryResult format
                    from models import WorkloadDiscoveryResult, ApplicationDetection
                    
                    # Helper function to convert confidence to float
                    def convert_confidence(conf_value):
                        """Convert confidence value to float, handling string values."""
                        if isinstance(conf_value, (int, float)):
                            return float(conf_value)
                        if isinstance(conf_value, str):
                            # Map string confidence levels to numeric values
                            confidence_map = {
                                'critical': 0.95, 'highest': 0.95,
                                'high': 0.8,
                                'medium': 0.6, 'normal': 0.6,
                                'low': 0.4,
                                'lowest': 0.2, 'info': 0.2
                            }
                            return confidence_map.get(conf_value.lower().strip(), 0.5)
                        return 0.5  # Default fallback
                    
                    discovery_result = WorkloadDiscoveryResult(
                        host=ssh_creds["hostname"],
                        applications=[
                            ApplicationDetection(
                                name=app.get("name", "unknown"),
                                version=app.get("version"),
                                confidence=convert_confidence(app.get("confidence", 0.5)),
                                detection_method=app.get("detection_method", "signature"),
                                evidence=app.get("evidence", {})
                            )
                            for app in discovered_apps
                        ]
                    )
                    
                    # Generate AI-powered report
                    detailed_report = await reporting_agent.generate_report(
                        validation_result=validation_result,
                        discovery_result=discovery_result,
                        classification=None,
                        evaluation=None,
                        format="markdown"
                    )
                    
                    write_progress("✓ AI-powered report generated successfully")
                    logger.info("🎭 report_generation_agent - Report generation complete")
                    
                    # Store detailed report for email
                    detailed_report_text = detailed_report
                    
                    # Display the detailed report
                    write_progress("\n" + "=" * 60)
                    write_progress("COMPREHENSIVE VALIDATION REPORT")
                    write_progress("=" * 60)
                    write_progress(detailed_report)
                else:
                    logger.info("🎭 report_generation_agent - AI reporting disabled, using template")
                    write_progress("💡 Generating recommendations (AI reporting disabled)...")
                    report.recommendations = self.report_generator.generate_recommendations(report)
                    
                    # Display basic summary when AI reporting is disabled
                    write_progress("\n" + "=" * 60)
                    write_progress("VALIDATION SUMMARY")
                    write_progress("=" * 60)
                    write_progress(f"Hostname: {ssh_creds['hostname']}")
                    write_progress(f"OS: {os_info.get('distribution', 'Unknown')} {os_info.get('version', '')}")
                    write_progress(f"Applications: {len(discovered_apps)}")
                    write_progress(f"Validations: {successful}/{len(validation_results)} passed")
                    write_progress(f"Overall Status: {overall_status.value}")
                    
            except Exception as e:
                import traceback
                logger.error(f"🎭 report_generation_agent - Full error traceback:")
                logger.error(traceback.format_exc())
                logger.warning(f"🎭 report_generation_agent - AI reporting failed: {e}, falling back to template")
                write_progress(f"⚠ AI reporting unavailable, using template-based report")
                report.recommendations = self.report_generator.generate_recommendations(report)
                
                # Display basic summary on fallback
                write_progress("\n" + "=" * 60)
                write_progress("VALIDATION SUMMARY")
                write_progress("=" * 60)
                write_progress(f"Hostname: {ssh_creds['hostname']}")
                write_progress(f"OS: {os_info.get('distribution', 'Unknown')} {os_info.get('version', '')}")
                write_progress(f"Applications: {len(discovered_apps)}")
                write_progress(f"Validations: {successful}/{len(validation_results)} passed")
                write_progress(f"Overall Status: {overall_status.value}")
                write_progress("=" * 60)
            
            execution_time = time.time() - start_time
            write_progress(f"\n✓ Total execution time: {execution_time:.2f} seconds")
            
            # Send email if requested
            if email_recipient:
                write_progress(f"\n📧 Sending report to {email_recipient}...")
                try:
                    # Send detailed report if available, otherwise use basic template
                    if detailed_report_text:
                        email_sent = self.email_service.send_detailed_report(
                            detailed_report_text,
                            recipient=email_recipient,
                            subject=f"Recovery Validation Report - {ssh_creds['hostname']} - {overall_status.value}",
                            resource_host=ssh_creds['hostname']
                        )
                    else:
                        email_sent = self.email_service.send_validation_report(
                            report,
                            email_recipient
                        )
                    if email_sent:
                        write_progress("✓ Email report sent successfully")
                        logger.info(f"Email report sent to {email_recipient}")
                    else:
                        write_progress("⚠ Failed to send email report")
                        logger.warning(f"Failed to send email to {email_recipient}")
                except Exception as e:
                    write_progress(f"⚠ Email error: {e}")
                    logger.error(f"Error sending email: {e}")
            
            return report
            
        except MCPClientError as e:
            error_msg = f"MCP client error: {e}"
            logger.error(error_msg)
            if reader:
                reader.write("Error ❌", error_msg)
            raise
        except Exception as e:
            error_msg = f"Validation error: {e}"
            logger.error(error_msg, exc_info=True)
            if reader:
                reader.write("Error ❌", error_msg)
            raise

            raise
    
    async def run_interactive(self, reader):
        """Run agent in interactive mode using MCP-centric workflow.
        
        Args:
            reader: Console reader for user interaction
        """
        try:
            # Connect to MCP server at startup
            await self.connect_mcp()
            
            # Show initial prompt
            reader.write("Agent 🤖", self.conversation_handler.get_initial_prompt())
            
            # Get user input
            async for prompt_data in reader:
                user_input = prompt_data["prompt"]
                
                if user_input.lower() in ["exit", "quit", "cancel", "no"]:
                    reader.write("Agent 🤖", "Validation cancelled. Goodbye! 👋")
                    break
                
                # Parse input to extract hostname, email, and credentials
                parsed = await self.conversation_handler.parse_initial_input(user_input)
                host = parsed.get("host")
                email_recipient = parsed.get("email_recipient")
                
                # Use email from input or fall back to default
                if not email_recipient:
                    email_recipient = self.default_email_recipient
                
                if not host:
                    reader.write(
                        "Agent 🤖",
                        "I couldn't find a hostname or IP address. Please provide:\n"
                        "- IP address or hostname of the resource\n"
                        "Example: 'I recovered a VM at 192.168.1.100'"
                    )
                    continue
                
                # Ask for SSH credentials
                reader.write(
                    "Agent 🤖",
                    f"Great! I'll validate the resource at {host}.\n\n"
                    f"Please provide SSH credentials:\n"
                    f"- SSH username\n"
                    f"- SSH password (or I can check environment variables)"
                )
                
                # Get credentials
                async for cred_prompt in reader:
                    cred_input = cred_prompt["prompt"]
                    
                    if cred_input.lower() in ["exit", "quit", "cancel"]:
                        reader.write("Agent 🤖", "Validation cancelled.")
                        return
                    
                    # Parse credentials
                    creds = await self.conversation_handler.parse_credentials(
                        cred_input,
                        ResourceType.VM
                    )
                    
                    ssh_username = creds.get("ssh_user")
                    ssh_password = creds.get("ssh_password")
                    
                    # Try to get from environment if not provided
                    if not ssh_username or not ssh_password:
                        env_creds = self.credential_manager.merge_with_user_provided(
                            "vm",
                            {"ssh_user": ssh_username, "ssh_password": ssh_password},
                            host
                        )
                        ssh_username = ssh_username or env_creds.get("ssh_user")
                        ssh_password = ssh_password or env_creds.get("ssh_password")
                    
                    if not ssh_username or not ssh_password:
                        reader.write(
                            "Agent 🤖",
                            "I still need SSH credentials. Please provide:\n"
                            "- Username and password\n"
                            "Example: 'username: root, password: mypassword'"
                        )
                        continue
                    
                    # Build SSH credentials dict
                    ssh_creds = {
                        "hostname": host,
                        "username": ssh_username,
                        "password": ssh_password
                    }
                    
                    # Build confirmation message
                    confirmation_msg = (
                        f"Perfect! I have all the information I need.\n\n"
                        f"I will now:\n"
                        f"1. Discover the operating system\n"
                        f"2. Discover all applications (including Oracle, MongoDB, etc.)\n"
                        f"3. Select appropriate validation tools\n"
                        f"4. Run comprehensive validations\n"
                        f"5. Generate a detailed report\n"
                    )
                    
                    if email_recipient:
                        confirmation_msg += f"6. Send report to {email_recipient}\n"
                    
                    confirmation_msg += "\nStarting validation..."
                    
                    reader.write("Agent 🤖", confirmation_msg)
                    
                    # Run MCP-centric validation with email
                    report = await self.run_mcp_centric_validation(ssh_creds, reader, email_recipient)
                    
                    # Ask if user wants to validate another resource
                    reader.write(
                        "Agent 🤖",
                        "\nWould you like to validate another resource? (yes/no)"
                    )
                    
                    # Wait for response
                    async for response_prompt in reader:
                        response = response_prompt["prompt"].lower()
                        if response in ["yes", "y"]:
                            reader.write("Agent 🤖", self.conversation_handler.get_initial_prompt())
                            break
                        else:
                            reader.write("Agent 🤖", "Goodbye! 👋")
                            return
                    
                    break  # Exit credential loop
                
                break  # Exit main loop after validation
            
        except KeyboardInterrupt:
            reader.write("Agent 🤖", "\nValidation interrupted by user.")
        except Exception as e:
            logger.error(f"Interactive mode error: {e}", exc_info=True)
            reader.write("Error ❌", f"An error occurred: {e}")
        finally:
            # Always disconnect from MCP server
            await self.disconnect_mcp()

# Made with Bob
