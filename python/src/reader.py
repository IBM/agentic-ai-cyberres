#
# Copyright contributors to the agentic-ai-cyberres project
#
from typing import Optional, AsyncGenerator, Dict, Any
from colorama import Fore, Style, init

init()

class ConsoleReader:
    def __init__(self, fallback: Optional[str] = None, input_prompt: str = "User 👤 : ", allow_empty: bool = False):
        self.fallback = fallback
        self.input_prompt = input_prompt
        self.allow_empty = allow_empty
        self.is_active = True
    
    def write(self, role: str, data: str):
        colored_role = f"{Fore.RED}{Style.BRIGHT}{role}{Style.RESET_ALL}" if role else ""
        print(f"{colored_role} {data}")
    
    async def prompt(self) -> str:
        async for data in self:
            return data["prompt"]
        return ""
    
    async def ask_single_question(self, query_message: str) -> str:
        print(f"{Fore.CYAN}{Style.BRIGHT}{query_message}{Style.RESET_ALL}", end="")
        answer = input().strip()
        return answer
    
    def close(self):
        self.is_active = False
    
    async def __aiter__(self):
        print(f"{Style.DIM}Interactive session has started. To escape, input 'q' and submit.{Style.RESET_ALL}")
        
        iteration = 1
        while self.is_active:
            try:
                prompt = await self.ask_single_question(self.input_prompt)
                
                if prompt == "q":
                    break
                if not prompt.strip():
                    prompt = self.fallback or ""
                if not self.allow_empty and not prompt.strip():
                    print("Error: Empty prompt is not allowed. Please try again.")
                    iteration -= 1
                    continue
                
                yield {"prompt": prompt, "iteration": iteration}
                iteration += 1
                
            except (EOFError, KeyboardInterrupt):
                break

def create_console_reader(fallback: Optional[str] = None, input_prompt: str = "User 👤 : ", allow_empty: bool = False) -> ConsoleReader:
    return ConsoleReader(fallback=fallback, input_prompt=input_prompt, allow_empty=allow_empty)