import asyncio
import sys
from typing import AsyncGenerator
from colorama import Fore, Style, init

init(autoreset=True)

class ConsoleReader:
    def __init__(self, fallback: str = None, input_prompt: str = "User 👤 : ", allow_empty: bool = False):
        self.fallback = fallback
        self.input_prompt = input_prompt
        self.allow_empty = allow_empty
        self.is_active = True

    def write(self, role: str, data: str):
        role_colored = f"{Fore.RED}{Style.BRIGHT}{role}{Style.RESET_ALL}" if role else ""
        print(f"{role_colored} {data}")

    async def prompt(self) -> str:
        async for prompt in self:
            return prompt

    async def ask_single_question(self, query_message: str) -> str:
        print(f"{Fore.CYAN}{Style.BRIGHT}{query_message}{Style.RESET_ALL}", end="")
        answer = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
        return answer.strip()

    def close(self):
        self.is_active = False

    def __aiter__(self) -> AsyncGenerator[str, None]:
        return self._prompt_generator()

    async def _prompt_generator(self) -> AsyncGenerator[str, None]:
        print(f"{Style.DIM}Interactive session has started. To escape, input 'q' and submit.{Style.RESET_ALL}")
        iteration = 1
        while self.is_active:
            print(f"{Fore.CYAN}{Style.BRIGHT}{self.input_prompt}{Style.RESET_ALL}", end="", flush=True)
            prompt = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            prompt = prompt.strip()
            if prompt == "q":
                break
            if not prompt:
                prompt = self.fallback or ""
            if not self.allow_empty and not prompt.strip():
                print("Error: Empty prompt is not allowed. Please try again.")
                continue
            yield prompt
            iteration += 1
