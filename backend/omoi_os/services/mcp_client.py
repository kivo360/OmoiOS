"""MCP Client Service for agent access to MCP tools.

This service provides a client interface for agents to call MCP tools
on a central server, enabling distributed agent architectures.
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from omoi_os.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MCPToolInfo:
    """Information about an MCP tool."""

    name: str
    description: str
    parameters: Dict[str, Any]


class MCPClientService:
    """Client service for accessing MCP tools on a remote server.

    This enables distributed agents to call MCP tools without direct
    database access - they only need HTTP access to the MCP server.

    Usage:
        client = MCPClientService(mcp_url="http://localhost:18000/mcp/")
        await client.connect()

        # List available tools
        tools = await client.list_tools()

        # Call a tool
        result = await client.call_tool("get_ticket", {"ticket_id": "..."})

        await client.disconnect()
    """

    def __init__(
        self,
        mcp_url: str = "http://localhost:18000/mcp/",
        timeout: float = 30.0,
    ):
        """Initialize MCP client service.

        Args:
            mcp_url: URL of the MCP server (with trailing slash)
            timeout: Request timeout in seconds
        """
        self.mcp_url = mcp_url.rstrip("/") + "/"
        self.timeout = timeout
        self._client = None
        self._tools_cache: Optional[List[MCPToolInfo]] = None

    async def connect(self) -> None:
        """Connect to the MCP server."""
        try:
            from fastmcp import Client

            self._client = Client(self.mcp_url)
            await self._client.__aenter__()
            logger.info(f"Connected to MCP server at {self.mcp_url}")
        except ImportError:
            raise RuntimeError("fastmcp package required for MCP client")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
                logger.info("Disconnected from MCP server")
            except Exception as e:
                logger.warning(f"Error disconnecting from MCP server: {e}")
            finally:
                self._client = None
                self._tools_cache = None

    async def list_tools(self, refresh: bool = False) -> List[MCPToolInfo]:
        """List all available MCP tools.

        Args:
            refresh: Force refresh of cached tools list

        Returns:
            List of MCPToolInfo objects
        """
        if not self._client:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")

        if self._tools_cache and not refresh:
            return self._tools_cache

        tools = await self._client.list_tools()
        self._tools_cache = [
            MCPToolInfo(
                name=tool.name,
                description=tool.description or "",
                parameters=tool.inputSchema if hasattr(tool, "inputSchema") else {},
            )
            for tool in tools
        ]

        logger.info(f"Retrieved {len(self._tools_cache)} tools from MCP server")
        return self._tools_cache

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Call an MCP tool by name.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments as a dictionary

        Returns:
            Tool result as a dictionary
        """
        if not self._client:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")

        try:
            result = await self._client.call_tool(tool_name, arguments)
            logger.debug(f"Called MCP tool {tool_name} successfully")
            return result
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            raise

    def call_tool_sync(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Synchronous wrapper for call_tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments as a dictionary

        Returns:
            Tool result as a dictionary
        """
        return asyncio.get_event_loop().run_until_complete(
            self.call_tool(tool_name, arguments)
        )

    async def get_tool_info(self, tool_name: str) -> Optional[MCPToolInfo]:
        """Get information about a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            MCPToolInfo or None if not found
        """
        tools = await self.list_tools()
        for tool in tools:
            if tool.name == tool_name:
                return tool
        return None

    @property
    def is_connected(self) -> bool:
        """Check if connected to MCP server."""
        return self._client is not None


# Global singleton for shared access
_mcp_client: Optional[MCPClientService] = None


def get_mcp_client(mcp_url: Optional[str] = None) -> MCPClientService:
    """Get or create the global MCP client service.

    Args:
        mcp_url: Optional MCP server URL. If not provided, uses default.

    Returns:
        MCPClientService instance
    """
    global _mcp_client

    if _mcp_client is None:
        from omoi_os.config import get_app_settings

        settings = get_app_settings()

        # Use provided URL or default from settings
        url = mcp_url or f"http://localhost:{settings.server.port}/mcp/"
        _mcp_client = MCPClientService(mcp_url=url)

    return _mcp_client


async def ensure_mcp_connected(mcp_url: Optional[str] = None) -> MCPClientService:
    """Ensure MCP client is connected and return it.

    Args:
        mcp_url: Optional MCP server URL

    Returns:
        Connected MCPClientService instance
    """
    client = get_mcp_client(mcp_url)
    if not client.is_connected:
        await client.connect()
    return client
