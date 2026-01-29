import sys
import os
import asyncio
import anyio
import logging
import datetime

# from mcp.server.stdio import stdio_server
# from mcp.server.lowlevel import Server
# import mcp.types as types


## our main server:
from src.mcp_server import mcp

## we want to run mcp server on http
import contextlib
from collections.abc import AsyncIterator

# from mcp.server.lowlevel import Server
# from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
# from starlette.applications import Starlette
# from starlette.middleware.cors import CORSMiddleware
# from starlette.routing import Mount
# from starlette.types import Receive, Scope, Send

if __name__ == "__main__":
    mcp.run(transport="sse")