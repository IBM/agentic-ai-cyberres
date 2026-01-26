"""
Copyright contributors to the agentic-ai-cyberres project
"""

"""Application settings using Pydantic and dotenv.

This module loads environment variables from a `.env` file (if present)
and exposes a `Settings` object. By default, it will bind the MCP
server to all interfaces on port 8000 and use the `streamable-http`
transport, but these values can be overridden via environment
variables. The path to a JSON secrets file can also be customized.
"""

from pydantic import BaseModel
from dotenv import load_dotenv
import os

# Load environment variables from a .env file if present
load_dotenv()


class Settings(BaseModel):
    """Configuration values for the MCP server.

    Attributes
    ----------
    host : str
        Host address to bind the MCP server to. Defaults to `0.0.0.0`.
    port : int
        Port number for the MCP server. Defaults to 8000.
    transport : str
        Transport mechanism used by FastMCP. Defaults to
        ``streamable-http`` which exposes an HTTP endpoint.
    secrets_file : str
        Path to a JSON file containing credentials or connection
        information for infrastructure components. Defaults to
        ``secrets.json``.
    oracle_home : str
        Default Oracle home path for configuration files. Defaults to
        ``/u01/app/oracle/product/19c/dbhome_1``.
    oracle_listener_ora : str
        Path to Oracle listener.ora file. Defaults to
        ``{oracle_home}/network/admin/listener.ora``.
    oracle_tnsnames_ora : str
        Path to Oracle tnsnames.ora file. Defaults to
        ``{oracle_home}/network/admin/tnsnames.ora``.
    """

    host: str = os.getenv("MCP_HOST", "0.0.0.0")
    port: int = int(os.getenv("MCP_PORT", "8000"))
    transport: str = os.getenv("MCP_TRANSPORT", "streamable-http")
    secrets_file: str = os.getenv("SECRETS_FILE", "secrets.json")
    oracle_home: str = os.getenv("ORACLE_HOME", "/u01/app/oracle/product/19c/dbhome_1")
    oracle_listener_ora: str = os.getenv("ORACLE_LISTENER_ORA", "{oracle_home}/network/admin/listener.ora").format(oracle_home=oracle_home)
    oracle_tnsnames_ora: str = os.getenv("ORACLE_TNSNAMES_ORA", "{oracle_home}/network/admin/tnsnames.ora").format(oracle_home=oracle_home)


# Expose a singleton settings object for convenient import
SETTINGS = Settings()