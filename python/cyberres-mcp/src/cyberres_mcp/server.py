
#
# Copyright contributors to the agentic-ai-cyberres project
#
from __future__ import annotations
from fastmcp import FastMCP
import os
import json
import logging
import re
from .settings import SETTINGS
from .plugins import vms_validator, oracle_db, mongo_db, net, workload_discovery


def create_app() -> FastMCP:
    """Create and configure a FastMCP instance with tools and resources."""
    # basic structured logging setup
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    class SensitiveDataFilter(logging.Filter):
        """Redact sensitive values in log records.

        - Mask keys named like password, token, secret, key, authorization
        - Scrub URIs with user:pass@ to user:***@ form
        """

        _sensitive_key_re = re.compile(r"(pass(word)?|token|secret|key|authorization|auth|pwd)", re.IGNORECASE)
        _uri_creds_re = re.compile(r"(://[^/\s:@]+:)([^@\s]+)(@)")

        def _scrub_value(self, value: str) -> str:
            masked = self._uri_creds_re.sub(r"\1***\3", value)
            # mask long opaque tokens (>=24 word-ish chars)
            masked = re.sub(r"([A-Za-z0-9_-]{24,})", "***", masked)
            return masked

        def filter(self, record: logging.LogRecord) -> bool:
            # Scrub message string
            if isinstance(record.msg, str):
                record.msg = self._scrub_value(record.msg)
            # Scrub extras in record.__dict__
            for k, v in list(record.__dict__.items()):
                if isinstance(v, str):
                    record.__dict__[k] = self._scrub_value(v)
                elif isinstance(v, dict):
                    safe = {}
                    for dk, dv in v.items():
                        if self._sensitive_key_re.search(str(dk)):
                            safe[dk] = "***"
                        elif isinstance(dv, str):
                            safe[dk] = self._scrub_value(dv)
                        else:
                            safe[dk] = dv
                    record.__dict__[k] = safe
            return True

    logger = logging.getLogger("mcp.server")
    logger.addFilter(SensitiveDataFilter())

    # load secrets file if present
    secrets = {}
    secrets_path = os.path.join(os.path.dirname(__file__), SETTINGS.secrets_file)
    try:
        if os.path.exists(secrets_path):
            with open(secrets_path, "r", encoding="utf-8") as fh:
                secrets = json.load(fh)
            logger.info("Loaded secrets file", extra={"path": secrets_path, "keys": list(secrets.keys())})
        else:
            logger.info("No secrets file found", extra={"path": secrets_path})
    except Exception as e:
        logger.warning("Failed to load secrets file", extra={"path": secrets_path, "error": str(e)})

    app = FastMCP(
        "Recovery_Validation_MCP",
        instructions=(
            "Validates recovered infrastructure resources including Linux VMs, "
            "Oracle databases, and MongoDB clusters. Exposes tools to check "
            "network connectivity, OS health, database connectivity, and "
            "replica status."
        ),
    )

    # Add health check tool
    @app.tool()
    def server_health() -> dict:
        """Check MCP server health and list available capabilities.
        
        Returns server status, version, and counts of available tools,
        resources, and prompts. Useful for verifying server connectivity
        and discovering capabilities.
        
        Example:
            >>> server_health()
            {
                "ok": true,
                "status": "healthy",
                "version": "0.1.0",
                "plugins": ["network", "vm_linux", "oracle_db", "mongodb"],
                "capabilities": {
                    "tools": 13,
                    "resources": 3,
                    "prompts": 3
                }
            }
        """
        from .plugins.utils import ok
        
        return ok({
            "status": "healthy",
            "version": "0.1.0",
            "plugins": ["network", "vm_linux", "oracle_db", "mongodb", "workload_discovery"],
            "capabilities": {
                "tools": 21,
                "resources": 3,
                "prompts": 3
            },
            "description": "Recovery validation MCP server for infrastructure health checks and workload discovery. Includes tools for OS detection and application discovery."
        })

    # Add tools to access resources and prompts
    @app.tool()
    def list_resources() -> dict:
        """List all available acceptance criteria resources.
        
        Returns a list of available resource URIs and their descriptions.
        These resources define acceptance criteria for validation.
        """
        from .plugins.utils import ok
        
        return ok({
            "resources": [
                {
                    "uri": "resource://acceptance/vm-core",
                    "name": "VM Core Acceptance Criteria",
                    "description": "Defines thresholds for Linux VM health validation including filesystem usage, memory, and required services"
                },
                {
                    "uri": "resource://acceptance/db-oracle",
                    "name": "Oracle Database Acceptance Criteria",
                    "description": "Defines criteria for Oracle database validation including tablespace usage and connection requirements"
                },
                {
                    "uri": "resource://acceptance/db-mongo",
                    "name": "MongoDB Acceptance Criteria",
                    "description": "Defines criteria for MongoDB cluster validation including replica set health and replication lag"
                }
            ]
        })
    
    @app.tool()
    def get_resource(resource_uri: str) -> dict:
        """Get the content of a specific acceptance criteria resource.
        
        Args:
            resource_uri: The URI of the resource (e.g., "resource://acceptance/vm-core")
        
        Returns:
            The resource content as JSON
        """
        from .plugins.utils import ok, err
        
        resource_map = {
            "resource://acceptance/vm-core": "vm-core.json",
            "resource://acceptance/db-oracle": "db-oracle.json",
            "resource://acceptance/db-mongo": "db-mongo.json"
        }
        
        if resource_uri not in resource_map:
            return err(f"Unknown resource: {resource_uri}", code="RESOURCE_NOT_FOUND")
        
        filename = resource_map[resource_uri]
        try:
            filepath = os.path.join(resource_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = json.load(f)
            return ok({
                "uri": resource_uri,
                "content": content
            })
        except FileNotFoundError:
            return err(f"Resource file not found: {filename}", code="FILE_NOT_FOUND")
        except Exception as e:
            return err(f"Failed to load resource: {str(e)}", code="RESOURCE_ERROR")
    
    @app.tool()
    def list_prompts() -> dict:
        """List all available prompt templates.
        
        Returns a list of available prompts and their descriptions.
        These prompts guide AI assistants in performing complex validation workflows.
        """
        from .plugins.utils import ok
        
        return ok({
            "prompts": [
                {
                    "name": "planner",
                    "description": "Creates structured validation plans with phases, steps, and time estimates"
                },
                {
                    "name": "evaluator",
                    "description": "Evaluates validation results against acceptance criteria and provides pass/fail assessment"
                },
                {
                    "name": "summarizer",
                    "description": "Generates executive summaries of validation results with key findings and recommendations"
                }
            ]
        })
    
    @app.tool()
    def get_prompt(prompt_name: str) -> dict:
        """Get the content of a specific prompt template.
        
        Args:
            prompt_name: The name of the prompt (e.g., "planner", "evaluator", "summarizer")
        
        Returns:
            The prompt template content
        """
        from .plugins.utils import ok, err
        
        valid_prompts = ["planner", "evaluator", "summarizer"]
        
        if prompt_name not in valid_prompts:
            return err(f"Unknown prompt: {prompt_name}. Valid prompts: {', '.join(valid_prompts)}", code="PROMPT_NOT_FOUND")
        
        try:
            filepath = os.path.join(prompt_dir, f"{prompt_name}.md")
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            return ok({
                "name": prompt_name,
                "content": content
            })
        except FileNotFoundError:
            return err(f"Prompt file not found: {prompt_name}.md", code="FILE_NOT_FOUND")
        except Exception as e:
            return err(f"Failed to load prompt: {str(e)}", code="PROMPT_ERROR")

    # Attach plugin tool functions. Each plugin exposes its own attach() with @app.tool decorations.
    net.attach(app)
    vms_validator.attach(app)
    oracle_db.attach(app)
    mongo_db.attach(app)
    workload_discovery.attach(app)

    # Register acceptance profile resources. These JSON files define threshold values.
    resource_dir = os.path.join(os.path.dirname(__file__), "resources", "acceptance")

    @app.resource("resource://acceptance/vm-core")
    def acceptance_vm_core() -> str:
        try:
            with open(os.path.join(resource_dir, "vm-core.json"), "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("Acceptance profile vm-core.json not found", extra={"path": os.path.join(resource_dir, "vm-core.json")})
            return "{}"
        except Exception as e:
            logger.error("Failed to load vm-core.json", extra={"error": str(e)})
            return "{}"

    @app.resource("resource://acceptance/db-oracle")
    def acceptance_db_oracle() -> str:
        try:
            with open(os.path.join(resource_dir, "db-oracle.json"), "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("Acceptance profile db-oracle.json not found", extra={"path": os.path.join(resource_dir, "db-oracle.json")})
            return "{}"
        except Exception as e:
            logger.error("Failed to load db-oracle.json", extra={"error": str(e)})
            return "{}"

    @app.resource("resource://acceptance/db-mongo")
    def acceptance_db_mongo() -> str:
        try:
            with open(os.path.join(resource_dir, "db-mongo.json"), "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("Acceptance profile db-mongo.json not found", extra={"path": os.path.join(resource_dir, "db-mongo.json")})
            return "{}"
        except Exception as e:
            logger.error("Failed to load db-mongo.json", extra={"error": str(e)})
            return "{}"

    # Register prompts used by orchestrating agents
    prompt_dir = os.path.join(os.path.dirname(__file__), "prompts")

    @app.prompt("planner")
    def planner_prompt() -> str:
        try:
            with open(os.path.join(prompt_dir, "planner.md"), "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("Prompt planner.md not found", extra={"path": os.path.join(prompt_dir, "planner.md")})
            return ""
        except Exception as e:
            logger.error("Failed to load planner.md", extra={"error": str(e)})
            return ""

    @app.prompt("evaluator")
    def evaluator_prompt() -> str:
        try:
            with open(os.path.join(prompt_dir, "evaluator.md"), "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("Prompt evaluator.md not found", extra={"path": os.path.join(prompt_dir, "evaluator.md")})
            return ""
        except Exception as e:
            logger.error("Failed to load evaluator.md", extra={"error": str(e)})
            return ""

    @app.prompt("summarizer")
    def summarizer_prompt() -> str:
        try:
            with open(os.path.join(prompt_dir, "summarizer.md"), "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("Prompt summarizer.md not found", extra={"path": os.path.join(prompt_dir, "summarizer.md")})
            return ""
        except Exception as e:
            logger.error("Failed to load summarizer.md", extra={"error": str(e)})
            return ""

    return app


def main() -> None:
    """Entry point for running the MCP server."""
    app = create_app()
    
    # stdio transport doesn't use host/port
    if SETTINGS.transport == "stdio":
        app.run(transport="stdio")
    else:
        # HTTP transports need host and port
        app.run(transport=SETTINGS.transport, host=SETTINGS.host, port=SETTINGS.port)


if __name__ == "__main__":
    main()