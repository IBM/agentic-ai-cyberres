#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Main entry point for recovery validation agent."""

import os
import asyncio
import logging
from reader import create_console_reader
from recovery_validation_agent import RecoveryValidationAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('recovery_validation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main entry point for recovery validation agent."""
    logger.info("Starting Recovery Validation Agent")
    
    # Create console reader
    reader = create_console_reader(
        fallback="I want to validate a recovered VM at 192.168.1.100"
    )
    
    # Create agent
    agent = RecoveryValidationAgent()
    
    # Display welcome banner
    print("\n" + "=" * 70)
    print("  🔍 RECOVERY VALIDATION AGENT")
    print("  Validate recovered infrastructure resources")
    print("=" * 70 + "\n")
    
    # Run in interactive mode
    try:
        await agent.run_interactive(reader)
    except KeyboardInterrupt:
        logger.info("Agent interrupted by user")
        print("\n\nGoodbye! 👋")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        print("Check recovery_validation.log for details.")
    
    logger.info("Recovery Validation Agent stopped")


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
