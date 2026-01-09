"""
Standalone script to run the Odoo MCP server 
Uses the same approach as in the official MCP SDK examples
"""
import sys
import os
import asyncio
import anyio
import logging
import datetime

from mcp.server.stdio import stdio_server
from mcp.server.lowlevel import Server
import mcp.types as types

from src.mcp_server import mcp  # FastMCP instance from our code

## we want to run mcp server on http
import contextlib
from collections.abc import AsyncIterator

from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send



def setup_logging():
    """Set up logging to both console and file"""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"mcp_server_{timestamp}.log")
    
    # Configure logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Format for both handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


def main() -> int:
    """
    Run the MCP server based on the official examples
    """
    logger = setup_logging()
    
    try:
        logger.info("=== ODOO MCP SERVER STARTING ===")
        logger.info(f"Python version: {sys.version}")
        logger.info("Environment variables:")
        for key, value in os.environ.items():
            if key.startswith("ODOO_"):
                if key == "ODOO_PASSWORD":
                    logger.info(f"  {key}: ***hidden***")
                else:
                    logger.info(f"  {key}: {value}")
        
        logger.info(f"MCP object type: {type(mcp)}")
        
        # Run server in stdio mode like the official examples
        async def arun():
            logger.info("Starting Odoo MCP server with stdio transport...")
            async with stdio_server() as streams:
                logger.info("Stdio server initialized, running MCP server...")
                await mcp._mcp_server.run(
                    streams[0], streams[1], mcp._mcp_server.create_initialization_options()
                )
                
        # Run server
        anyio.run(arun)
        logger.info("MCP server stopped normally")
        
        
        
        
        ## Run on HTTP
            # Create the session manager with true stateless mode
        # session_manager = StreamableHTTPSessionManager(
        #     app=mcp._mcp_server,
        #     event_store=None,
        #     json_response=False,  ### you want json response or not 
        #     stateless=False
        # )
        # async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
        #     await session_manager.handle_request(scope, receive, send)


        # @contextlib.asynccontextmanager
        # async def lifespan(app: Starlette) -> AsyncIterator[None]:
        #     """Context manager for session manager."""
        #     async with session_manager.run():
        #         logger.info("Application started with StreamableHTTP session manager!")
        #         try:
        #             yield
        #         finally:
        #             logger.info("Application shutting down...")

        # # Create an ASGI application using the transport
        # starlette_app = Starlette(
        #     debug=True,
        #     routes=[
        #         Mount("/mcp", app=handle_streamable_http),
        #     ],
        #     lifespan=lifespan,
        # )

        # # Wrap ASGI application with CORS middleware to expose Mcp-Session-Id header
        # # for browser-based clients (ensures 500 errors get proper CORS headers)
        # starlette_app = CORSMiddleware(
        #     starlette_app,
        #     allow_origins=["*"],  # Allow all origins - adjust as needed for production
        #     allow_methods=["GET", "POST", "DELETE"],  # MCP streamable HTTP methods
        #     expose_headers=["Mcp-Session-Id"],
        # )

        # import uvicorn
        # uvicorn.run(starlette_app, host="127.0.0.1", port=8000)
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 