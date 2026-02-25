"""
Basic test to verify BeeAI framework installation and functionality.
"""

import asyncio
import logging
from beeai_framework.agents import BaseAgent
from beeai_framework.memory import SlidingMemory
from beeai_framework.tools import Tool, ToolOutput, StringToolOutput

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Create a simple test tool
class GreetingTool(Tool):
    """Simple greeting tool for testing."""
    
    name = "greeting"
    description = "Greet a person by name"
    
    async def run(self, name: str) -> ToolOutput:
        """Run the greeting tool."""
        greeting = f"Hello, {name}! Welcome to BeeAI framework."
        return StringToolOutput(value=greeting)


async def test_beeai_basic():
    """Test basic BeeAI functionality."""
    
    logger.info("=" * 60)
    logger.info("Testing BeeAI Framework Installation")
    logger.info("=" * 60)
    
    # Test 1: Import modules
    logger.info("\n1. Testing module imports...")
    try:
        from beeai_framework import agents, tools, memory
        logger.info("✓ Successfully imported beeai_framework modules")
        logger.info(f"  - Agents: {agents.__name__}")
        logger.info(f"  - Tools: {tools.__name__}")
        logger.info(f"  - Memory: {memory.__name__}")
    except Exception as e:
        logger.error(f"✗ Failed to import modules: {e}")
        return False
    
    # Test 2: Create memory
    logger.info("\n2. Testing memory creation...")
    try:
        memory_instance = SlidingMemory(max_messages=10)
        logger.info(f"✓ Created SlidingMemory with max_messages=10")
        logger.info(f"  - Type: {type(memory_instance).__name__}")
    except Exception as e:
        logger.error(f"✗ Failed to create memory: {e}")
        return False
    
    # Test 3: Create tool
    logger.info("\n3. Testing tool creation...")
    try:
        greeting_tool = GreetingTool()
        logger.info(f"✓ Created GreetingTool")
        logger.info(f"  - Name: {greeting_tool.name}")
        logger.info(f"  - Description: {greeting_tool.description}")
        
        # Test tool execution
        result = await greeting_tool.run(name="BeeAI User")
        logger.info(f"  - Test execution: {result.value}")
    except Exception as e:
        logger.error(f"✗ Failed to create/run tool: {e}")
        return False
    
    # Test 4: Explore agent types
    logger.info("\n4. Exploring available agent types...")
    try:
        from beeai_framework.agents import BaseAgent
        logger.info(f"✓ BaseAgent available")
        logger.info(f"  - Module: {BaseAgent.__module__}")
        
        # Check for other agent types
        try:
            from beeai_framework.agents import Agent
            logger.info(f"  - Agent class available")
        except ImportError:
            logger.info(f"  - Agent class not found (using BaseAgent)")
    except Exception as e:
        logger.error(f"✗ Failed to explore agents: {e}")
        return False
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ All basic tests passed!")
    logger.info("=" * 60)
    
    return True


async def test_agent_creation():
    """Test creating a simple agent."""
    
    logger.info("\n" + "=" * 60)
    logger.info("Testing Agent Creation")
    logger.info("=" * 60)
    
    try:
        # Note: We'll need to check the actual BeeAI API
        # This is a placeholder to understand the structure
        logger.info("\nChecking BeeAI agent creation API...")
        
        from beeai_framework.agents import BaseAgent
        
        # Inspect BaseAgent
        logger.info(f"BaseAgent methods: {[m for m in dir(BaseAgent) if not m.startswith('_')]}")
        
    except Exception as e:
        logger.error(f"Error during agent creation test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run basic tests
    success = asyncio.run(test_beeai_basic())
    
    if success:
        # Run agent creation test
        asyncio.run(test_agent_creation())

# Made with Bob
