"""
Odoo Inventory MCP Server

This module provides comprehensive MCP server for Odoo Inventory Management.

Author: Dhruv Panchal
"""

import json
from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from fastmcp import FastMCP, Context
from contextlib import asynccontextmanager
from typing import AsyncIterator
from dataclasses import dataclass

from src.odoo_client import OdooClient, get_odoo_client
from src.inventory_mcp_tools import register_mcp_tools


@dataclass
class AppContext:
    """Application context for the MCP server"""

    odoo: OdooClient


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """
    Application lifespan for initialization and cleanup
    """
    # Initialize Odoo client on startup
    odoo_client = get_odoo_client()

    try:
        yield AppContext(odoo=odoo_client)
    finally:
        # No cleanup needed for Odoo client
        pass


# Create MCP server
mcp = FastMCP(
    "Odoo Inventory MCP Server",
    lifespan=app_lifespan,
)

register_mcp_tools(mcp)


if __name__ == "__main__":
    mcp.run(transport="sse", port=8000)