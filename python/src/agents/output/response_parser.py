"""Parser for BeeAI agent responses."""

import logging
import re
import json
from typing import Any, List, Optional, Dict
from datetime import datetime

from .models import ThoughtStep, ReasoningChain
from .framework_sanitizer import FrameworkSanitizer

logger = logging.getLogger(__name__)


class AgentResponseParser:
    """Parses BeeAI agent responses into structured reasoning chains."""
    
    # Regex patterns for extracting reasoning components
    THOUGHT_PATTERN = re.compile(r"Thought:\s*(.+?)(?=\n(?:Action:|Observation:|Final Answer:)|$)", re.DOTALL)
    ACTION_PATTERN = re.compile(r"Action:\s*(\w+)", re.IGNORECASE)
    ACTION_INPUT_PATTERN = re.compile(r"Action Input:\s*(\{.+?\})", re.DOTALL)
    OBSERVATION_PATTERN = re.compile(r"Observation:\s*(.+?)(?=\nThought:|$)", re.DOTALL)
    FINAL_ANSWER_PATTERN = re.compile(r"Final Answer:\s*(.+?)$", re.DOTALL)
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.sanitizer = FrameworkSanitizer()
    
    def parse(
        self,
        response: Any,
        agent_name: str = "Unknown",
        phase: str = "",
        start_time: Optional[datetime] = None
    ) -> ReasoningChain:
        """
        Parse agent response into structured reasoning chain.
        
        Args:
            response: Raw response from BeeAI agent
            agent_name: Name of the agent that produced response
            phase: Current workflow phase
            start_time: When execution started (for timing)
        
        Returns:
            Structured ReasoningChain object
        """
        self.logger.debug(f"Parsing response from {agent_name}, type: {type(response)}")
        
        try:
            # Extract text content from response
            response_text = self._extract_text(response)
            
            # Parse reasoning steps
            steps = self._parse_steps(response_text)
            
            # Extract final answer
            final_answer = self._extract_final_answer(response_text)
            
            # Calculate execution time
            execution_time_ms = 0
            if start_time:
                execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Determine model used
            model_used = self._extract_model_info(response)
            
            return ReasoningChain(
                steps=steps,
                final_answer=final_answer,
                total_steps=len(steps),
                execution_time_ms=execution_time_ms,
                model_used=model_used,
                agent_name=agent_name,
                phase=phase,
                success=True
            )
        
        except Exception as e:
            self.logger.error(f"Failed to parse response: {e}", exc_info=True)
            return ReasoningChain(
                steps=[],
                final_answer=str(response),
                total_steps=0,
                execution_time_ms=0,
                model_used="unknown",
                agent_name=agent_name,
                phase=phase,
                success=False,
                error_message=str(e)
            )
    
    def _extract_text(self, response: Any) -> str:
        """
        Extract text content from various response formats.
        
        Handles:
        - List of message objects
        - Single message object
        - Dictionary with content/text/output keys
        - Plain string
        
        Based on the existing _extract_response_text() in llm_aggregator.py
        """
        if isinstance(response, str):
            return response
        
        if isinstance(response, list):
            # Try to find message with Final Answer
            for msg in reversed(response):
                content = self._get_message_content(msg)
                if content and "Final Answer:" in content:
                    return content
            
            # Fall back to last message
            if response:
                return self._get_message_content(response[-1])
        
        if isinstance(response, dict):
            return response.get('content') or response.get('text') or response.get('output', '')
        
        # Try common attribute names
        for attr in ['content', 'text', 'output', 'message']:
            if hasattr(response, attr):
                value = getattr(response, attr)
                if isinstance(value, str):
                    return value
                # Handle list of message objects (BeeAI response format)
                elif isinstance(value, list) and value:
                    # Try to extract content from list of messages
                    for msg in reversed(value):
                        content = self._get_message_content(msg)
                        if content and content.strip():
                            return content
        
        # Last resort
        return str(response)
    
    def _get_message_content(self, msg: Any) -> str:
        """Extract content from a message object."""
        if isinstance(msg, str):
            return msg
        
        if isinstance(msg, dict):
            return msg.get('content') or msg.get('text') or msg.get('output', '')
        
        for attr in ['content', 'text', 'output']:
            if hasattr(msg, attr):
                value = getattr(msg, attr)
                if isinstance(value, str):
                    return value
        
        return str(msg)
    
    def _parse_steps(self, text: str) -> List[ThoughtStep]:
        """Parse individual reasoning steps from text."""
        steps = []
        step_number = 1
        
        # Split text into potential step sections
        sections = re.split(r'\n(?=Thought:)', text)
        
        for section in sections:
            if not section.strip():
                continue
            
            # Extract components
            thought_match = self.THOUGHT_PATTERN.search(section)
            action_match = self.ACTION_PATTERN.search(section)
            action_input_match = self.ACTION_INPUT_PATTERN.search(section)
            observation_match = self.OBSERVATION_PATTERN.search(section)
            
            if thought_match:
                thought = thought_match.group(1).strip()
                action = action_match.group(1) if action_match else None
                action_input = None
                
                if action_input_match:
                    try:
                        action_input = json.loads(action_input_match.group(1))
                    except json.JSONDecodeError:
                        action_input = {"raw": action_input_match.group(1)}
                
                observation = observation_match.group(1).strip() if observation_match else None
                
                steps.append(ThoughtStep(
                    step_number=step_number,
                    thought=thought,
                    action=action,
                    action_input=action_input,
                    observation=observation
                ))
                step_number += 1
        
        return steps
    
    def _extract_final_answer(self, text: str) -> str:
        """Extract final answer from response text."""
        match = self.FINAL_ANSWER_PATTERN.search(text)
        if match:
            return match.group(1).strip()
        
        # If no explicit Final Answer marker, use last observation or full text
        observation_matches = list(self.OBSERVATION_PATTERN.finditer(text))
        if observation_matches:
            return observation_matches[-1].group(1).strip()
        
        return text.strip()
    
    def _extract_model_info(self, response: Any) -> str:
        """Extract model information from response."""
        # Try to find model info in response metadata
        if isinstance(response, dict):
            return response.get('model', 'unknown')
        
        if hasattr(response, 'model'):
            return str(response.model)
        
        return "unknown"
    
    def extract_simple_text(self, response: Any) -> str:
        """
        Extract and sanitize text for simple console output.
        
        This is a simplified version that just gets the text and removes
        framework markers, suitable for "Agent: message" format.
        
        Args:
            response: Raw response from BeeAI agent
        
        Returns:
            Clean text without framework markers
        """
        text = self._extract_text(response)
        return self.sanitizer.sanitize(text)

# Made with Bob
