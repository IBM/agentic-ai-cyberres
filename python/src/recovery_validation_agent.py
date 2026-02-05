#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Main orchestrator for recovery validation agent."""

import asyncio
import logging
import time
from typing import Optional
from datetime import datetime

from models import (
    ValidationRequest,
    ValidationReport,
    ResourceValidationResult,
    CredentialSource
)
from credentials import get_credential_manager
from mcp_client import mcp_client_context, MCPClientError
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
        
        # Get email config
        email_config = self.credential_manager.get_email_config()
        self.email_service = EmailService(
            smtp_server=email_config["smtp_server"],
            smtp_port=int(email_config["smtp_port"]),
            from_address=email_config["from_address"]
        )
        self.default_email_recipient = email_config["recipient"]
    
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
                
                # Create validation request
                validation_request = ValidationRequest(
                    resource_info=resource_info,
                    credential_source=CredentialSource.USER_PROVIDED,
                    auto_discover=True,
                    send_email=True,
                    email_recipient=self.default_email_recipient
                )
                
                reader.write(
                    "Agent 🤖",
                    f"Perfect! I have all the information I need.\n\n"
                    f"I will now:\n"
                    f"1. Auto-discover resource details\n"
                    f"2. Generate a validation plan\n"
                    f"3. Execute validation checks\n"
                    f"4. Evaluate results\n"
                    f"5. Send a detailed report to {self.default_email_recipient or 'you'}\n\n"
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
            # Get MCP server URL
            mcp_server_url = self.credential_manager.get_mcp_server_url()
            write_progress(f"Connecting to MCP server at {mcp_server_url}...")
            
            async with mcp_client_context(mcp_server_url) as mcp_client:
                write_progress("✓ Connected to MCP server")
                
                # Auto-discovery
                if validation_request.auto_discover:
                    write_progress(f"🔍 Discovering {validation_request.resource_info.resource_type.value} details...")
                    discovery = ResourceDiscovery(mcp_client)
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
                executor = ValidationExecutor(mcp_client)
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
            raise
    
    async def run_interactive(self, reader):
        """Run agent in interactive mode.
        
        Args:
            reader: Console reader for user interaction
        """
        try:
            # Gather information
            validation_request = await self.gather_information_interactive(reader)
            
            if not validation_request:
                return
            
            # Run validation
            report = await self.run_validation(validation_request, reader)
            
            # Ask if user wants to validate another resource
            reader.write(
                "Agent 🤖",
                "\nWould you like to validate another resource? (yes/no)"
            )
            
        except KeyboardInterrupt:
            reader.write("Agent 🤖", "\nValidation interrupted by user.")
        except Exception as e:
            logger.error(f"Interactive mode error: {e}", exc_info=True)
            reader.write("Error ❌", f"An error occurred: {e}")

# Made with Bob
