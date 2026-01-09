"""
run_sse_server.py - Run Odoo MCP Server with SSE Transport
"""
import sys
import os
import logging
import datetime
import contextlib
from collections.abc import AsyncIterator

from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import Response
import uvicorn

from src.mcp_server import mcp  # Your FastMCP instance


def setup_logging():
    """Set up logging to console and file"""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"mcp_sse_server_{timestamp}.log")
    
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


logger = setup_logging()


def main() -> int:
    """Run MCP server with SSE transport"""
    
    try:
        logger.info("=== ODOO MCP SERVER (SSE) STARTING ===")
        logger.info(f"Python version: {sys.version}")
        
        # Log Odoo environment variables
        for key, value in os.environ.items():
            if key.startswith("ODOO_"):
                if key == "ODOO_PASSWORD":
                    logger.info(f"  {key}: ***hidden***")
                else:
                    logger.info(f"  {key}: {value}")
        
        # Create SSE transport
        sse_transport = SseServerTransport("/messages/")
        
        # SSE endpoint handler
        async def handle_sse(request: Request) -> Response:
            """Handle SSE connections from clients"""
            logger.info(f"🔗 New SSE connection from {request.client}")
            
            async with sse_transport.connect_sse(
                request.scope,
                request.receive,
                request._send
            ) as streams:
                logger.info("SSE stream connected, running MCP server...")
                await mcp._mcp_server.run(
                    streams[0],
                    streams[1],
                    mcp._mcp_server.create_initialization_options()
                )
            
            return Response()
        
        # Message endpoint handler (client → server)
        async def handle_messages(request: Request) -> Response:
            """Handle incoming messages from client"""
            logger.debug("📨 Received message from client")
            await sse_transport.handle_post_message(
                request.scope,
                request.receive,
                request._send
            )
            return Response()
        
        # Lifespan context manager
        @contextlib.asynccontextmanager
        async def lifespan(app: Starlette) -> AsyncIterator[None]:
            logger.info("🚀 SSE Server starting...")
            logger.info("📡 SSE endpoint: http://127.0.0.1:8000/sse")
            logger.info("📬 Messages endpoint: http://127.0.0.1:8000/messages/")
            yield
            logger.info("👋 SSE Server shutting down...")
        
        # Create Starlette app
        app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse),                            # SSE stream
                Route("/messages/", endpoint=handle_messages, methods=["POST"]), # Messages
            ],
            lifespan=lifespan,
        )
        
        # Add CORS middleware
        app = CORSMiddleware(
            app,
            allow_origins=["*"],
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )
        
        # Run server
        logger.info("Starting Uvicorn server...")
        uvicorn.run(app, host="127.0.0.1", port=8000)
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())