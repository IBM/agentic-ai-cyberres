"""Plugin package exposing attach functions for each tool module.

Each module defines an ``attach(app)`` function which registers
tool functions on the FastMCP app instance. Importing this
package makes it easy to access submodules via package exports.
"""
from . import net, vms_validator, oracle_db, mongo_db 

__all__ = ["net", "vms_validator", "oracle_db", "mongo_db"]