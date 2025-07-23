class FrameworkError(Exception):
    @staticmethod
    def ensure(error):
        if isinstance(error, FrameworkError):
            return error
        return FrameworkError(str(error))

class TokenMemory:
    def __init__(self, llm=None):
        self.llm = llm

class OpenMeteoTool:
    name = "OpenMeteoTool"
    def __init__(self):
        pass

class DuckDuckGoSearchTool:
    name = "DuckDuckGoSearchTool"
    def __init__(self):
        pass

class BeeAgent:
    def __init__(self, llm=None, memory=None, tools=None):
        self.llm = llm
        self.memory = memory
        self.tools = tools or []

    async def run(self, input_data, execution=None):
        # Improved stub implementation of run method to simulate tool updates
        class Response:
            def __init__(self, tools, input_data):
                self.tools = tools
                self.input_data = input_data
                self.result = type("Result", (), {"text": "Simulated response from BeeAgent"})()

            async def observe(self):
                # Emit a thought update
                yield {"key": "thought", "value": "The user wants a list of commonly used enterprise applications on Linux, MacOS, Docker, and to check if any are running on this system."}

                # Emit tool updates with structured inputs in exact order as TypeScript
                tool_order = [
                    "FindRunningProcesses",
                    "MongoDBDataValidator",
                    "FindWhatsRunningByPorts",
                    "SendEmail",
                    "OpenMeteoTool",
                    "DuckDuckGoSearchTool",
                ]

                # Map tool names to tool instances
                tool_map = {tool.name if hasattr(tool, "name") else "UnknownTool": tool for tool in self.tools}

                for tool_name in tool_order:
                    if tool_name in tool_map:
                        yield {"key": "tool_name", "value": tool_name}

                        if tool_name == "FindRunningProcesses":
                            tool_input = {"min": 0}
                        elif tool_name == "MongoDBDataValidator":
                            tool_input = {"argument": "mongodb"}
                        elif tool_name == "FindWhatsRunningByPorts":
                            tool_input = {"min": 0, "max": 65535}
                        elif tool_name == "SendEmail":
                            tool_input = {"argument": "Validation results summary"}
                        else:
                            tool_input = {}

                        yield {"key": "tool_input", "value": tool_input}

                # Final result
                yield {"key": "info", "value": "All tools processed."}

        return Response(self.tools, input_data)
