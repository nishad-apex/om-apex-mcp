"""
Om Apex MCP Server

A Model Context Protocol server providing persistent memory for Om Apex Holdings
across all Claude interfaces (Chat, Cowork, Claude Code).

Author: Nishad Tambe
Started: January 19, 2026
"""

import logging
import traceback
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .storage import StorageBackend, LocalStorage
from .tools import ToolModule
from .tools.helpers import init_storage
from .tools import context, tasks, progress, documents, calendar

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("om-apex-mcp")


def create_server(backend: Optional[StorageBackend] = None) -> Server:
    """Create and configure the MCP server with given storage backend.

    Args:
        backend: Storage backend to use. Defaults to LocalStorage if None.

    Returns:
        Configured MCP Server instance.
    """
    if backend is None:
        backend = LocalStorage()
    init_storage(backend)

    server = Server("om-apex-mcp")

    # Register all tool modules
    _task_mod = tasks.register()
    _progress_mod = progress.register()
    _documents_mod = documents.register()
    _calendar_mod = calendar.register()

    # Build global tool lists for get_full_context response
    _all_reading = (
        context.READING + _task_mod.reading_tools
        + _progress_mod.reading_tools + _documents_mod.reading_tools
        + _calendar_mod.reading_tools
    )
    _all_writing = (
        context.WRITING + _task_mod.writing_tools
        + _progress_mod.writing_tools + _documents_mod.writing_tools
        + _calendar_mod.writing_tools
    )

    _context_mod = context.register(_all_reading, _all_writing)

    modules: list[ToolModule] = [_context_mod, _task_mod, _progress_mod, _documents_mod, _calendar_mod]

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """Return list of available tools."""
        return [tool for m in modules for tool in m.tools]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Dispatch tool calls to the appropriate module.

        Wraps all tool execution in try/except to prevent server crashes.
        Errors are logged and returned as error messages rather than exceptions.
        """
        try:
            for m in modules:
                result = await m.handler(name, arguments)
                if result is not None:
                    return result
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        except Exception as e:
            # Log the full traceback for debugging
            logger.exception(f"Tool '{name}' failed with error: {e}")

            # Return a user-friendly error message instead of crashing
            error_type = type(e).__name__
            error_msg = str(e)

            # Provide context-specific hints for common errors
            hint = ""
            if "FileNotFoundError" in error_type or "No such file" in error_msg:
                hint = " (Check if the path exists or Google Drive is synced)"
            elif "Permission" in error_msg:
                hint = " (Check file permissions)"
            elif "Connection" in error_msg or "timeout" in error_msg.lower():
                hint = " (Check network connectivity to Supabase/Google Drive)"
            elif "JSONDecodeError" in error_type:
                hint = " (Data file may be corrupted)"

            return [TextContent(
                type="text",
                text=f"Error in {name}: {error_type}: {error_msg}{hint}\n\n"
                     f"The server is still running. You can try again or check the logs for details."
            )]

    return server


# =============================================================================
# Main Entry Point (stdio transport — local Claude Desktop)
# =============================================================================

async def run():
    """Run the MCP server via stdio transport."""
    logger.info("Starting Om Apex MCP Server (stdio)...")
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Main entry point."""
    import asyncio
    asyncio.run(run())


if __name__ == "__main__":
    main()
