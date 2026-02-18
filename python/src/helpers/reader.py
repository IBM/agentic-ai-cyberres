
#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Console reader with color-coded interactive input handling.

This module provides an interactive console reader similar to the TypeScript
implementation, with fallback support.
"""

import sys
from typing import Optional, Iterator, Dict, Any
from dataclasses import dataclass


@dataclass
class ConsoleInput:
    """Represents input from the console."""
    prompt: str
    iteration: int


class ConsoleReader:
    """Interactive console reader with prompts.
    
    This class provides a synchronous iterator for reading user input from
    the console with prompts and fallback support.
    """
    
    def __init__(
        self,
        fallback: Optional[str] = None,
        input_label: str = "User 👤 : ",
        allow_empty: bool = False
    ):
        """Initialize the console reader.
        
        Args:
            fallback: Default prompt to use when user enters empty input.
            input_label: The prompt label shown to the user.
            allow_empty: Whether to allow empty prompts.
        """
        self.fallback = fallback or ""
        self.input_label = input_label
        self.allow_empty = allow_empty
        self._is_active = True
    
    def write(self, role: str, data: str) -> None:
        """Write output to the console.
        
        Args:
            role: The role label (e.g., "Agent 🤖").
            data: The data to output.
        """
        role_str = f"{role} " if role else ""
        output = f"{role_str}{data}\n"
        sys.stdout.write(output)
        sys.stdout.flush()
    
    def close(self) -> None:
        """Close the reader and stop input."""
        self._is_active = False
    
    def __iter__(self) -> Iterator[ConsoleInput]:
        """Iterate over console input."""
        return self._iter()
    
    def _iter(self) -> Iterator[ConsoleInput]:
        """Internal iterator implementation."""
        if not self._is_active:
            return
        
        # Print session start message
        sys.stdout.write("Interactive session has started. To escape, input 'q' and submit.\n")
        sys.stdout.flush()
        
        iteration = 1
        while self._is_active:
            try:
                prompt = input(self.input_label)
            except (EOFError, KeyboardInterrupt):
                break
            
            if prompt.strip() == "q":
                break
            
            if not prompt.strip():
                prompt = self.fallback
            
            if not self.allow_empty and not prompt.strip():
                sys.stdout.write("Error: Empty prompt is not allowed. Please try again.\n")
                sys.stdout.flush()
                continue
            
            yield ConsoleInput(prompt=prompt, iteration=iteration)
            iteration += 1


def create_console_reader(
    fallback: Optional[str] = None,
    input_label: str = "User 👤 : ",
    allow_empty: bool = False
) -> ConsoleReader:
    """Create a console reader instance.
    
    Args:
        fallback: Default prompt when user enters empty input.
        input_label: The prompt label shown to the user.
        allow_empty: Whether to allow empty prompts.
    
    Returns:
        A ConsoleReader instance.
    """
    return ConsoleReader(
        fallback=fallback,
        input_label=input_label,
        allow_empty=allow_empty
    )


# Alias for compatibility
createConsoleReader = create_console_reader

