"""MCP Tool Registry Service for server discovery and tool registration."""

from typing import Any, Dict, List, Optional

from jsonschema import Draft7Validator, ValidationError

from omoi_os.models.mcp_server import MCPServer, MCPTool
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now


class RegistrationResult:
    """Result of server registration."""

    def __init__(
        self,
        server_id: str,
        registered_count: int,
        rejected_count: int,
        registered_tools: List[MCPTool],
        rejected_tools: List[Dict[str, Any]],
    ):
        self.server_id = server_id
        self.registered_count = registered_count
        self.rejected_count = rejected_count
        self.registered_tools = registered_tools
        self.rejected_tools = rejected_tools


class MCPRegistryService:
    """
    Central registry for all MCP server tools with schema validation.
    
    REQ-MCP-REG-001: Server Discovery
    REQ-MCP-REG-002: Schema Validation
    REQ-MCP-REG-003: Version Compatibility
    """

    def __init__(self, db: DatabaseService):
        """
        Initialize MCP registry service.

        Args:
            db: DatabaseService instance
        """
        self.db = db
        self.version_matrix: Dict[str, Dict[str, List[str]]] = {}  # server_id -> tool_name -> versions

    def register_server(
        self,
        server_id: str,
        version: str,
        capabilities: List[str],
        tools: List[Dict[str, Any]],
        connection_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RegistrationResult:
        """
        Register MCP server and validate all tools.

        Args:
            server_id: Unique server identifier
            version: Server version
            capabilities: List of server capabilities
            tools: List of tool definitions with name and schema
            metadata: Optional server metadata

        Returns:
            RegistrationResult with registered and rejected tools
        """
        with self.db.get_session() as session:
            # Create or update server entry
            server = session.query(MCPServer).filter_by(server_id=server_id).first()
            if server:
                server.version = version
                server.capabilities = capabilities
                server.last_heartbeat = utc_now()
                server.status = "active"
                if connection_url:
                    server.connection_url = connection_url
                if metadata:
                    server.server_metadata = metadata
            else:
                server = MCPServer(
                    server_id=server_id,
                    version=version,
                    capabilities=capabilities,
                    connection_url=connection_url,
                    server_metadata=metadata or {},
                )
                session.add(server)

            session.flush()

            # Validate and register each tool
            registered_tools = []
            rejected_tools = []

            for tool_data in tools:
                try:
                    # Validate tool schema
                    if not self._validate_tool_schema(tool_data):
                        rejected_tools.append(
                            {
                                "tool_name": tool_data.get("name", "unknown"),
                                "reason": "Invalid JSON schema",
                                "errors": self._get_schema_errors(tool_data),
                            }
                        )
                        continue

                    tool_name = tool_data["name"]
                    tool_version = tool_data.get("version")

                    # Check version compatibility
                    if not self._check_version_compatibility(server_id, tool_name, tool_version):
                        rejected_tools.append(
                            {
                                "tool_name": tool_name,
                                "reason": "Version incompatibility",
                                "version": tool_version,
                            }
                        )
                        # Disable but don't reject
                        tool_data["enabled"] = False
                    else:
                        tool_data["enabled"] = True

                    # Create or update tool
                    existing_tool = (
                        session.query(MCPTool)
                        .filter_by(server_id=server_id, tool_name=tool_name)
                        .first()
                    )
                    if existing_tool:
                        existing_tool.schema = tool_data["schema"]
                        existing_tool.version = tool_version
                        existing_tool.enabled = tool_data.get("enabled", True)
                        registered_tools.append(existing_tool)
                    else:
                        tool = MCPTool(
                            server_id=server_id,
                            tool_name=tool_name,
                            schema=tool_data["schema"],
                            version=tool_version,
                            enabled=tool_data.get("enabled", True),
                        )
                        session.add(tool)
                        registered_tools.append(tool)

                except Exception as e:
                    rejected_tools.append(
                        {
                            "tool_name": tool_data.get("name", "unknown"),
                            "reason": str(e),
                        }
                    )

            session.commit()
            
            # Access all attributes while session is still active, then expunge
            for tool in registered_tools:
                # Force load of all attributes
                _ = tool.id
                _ = tool.server_id
                _ = tool.tool_name
                _ = tool.version
                _ = tool.enabled
                session.expunge(tool)

            return RegistrationResult(
                server_id=server_id,
                registered_count=len(registered_tools),
                rejected_count=len(rejected_tools),
                registered_tools=registered_tools,
                rejected_tools=rejected_tools,
            )

    def _validate_tool_schema(self, tool_data: Dict[str, Any]) -> bool:
        """
        Validate tool JSON schema structure.

        Args:
            tool_data: Tool definition dict

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["name", "schema"]
        if not all(field in tool_data for field in required_fields):
            return False

        # Validate JSON Schema format
        try:
            Draft7Validator.check_schema(tool_data["schema"])
        except ValidationError:
            return False

        return True

    def _get_schema_errors(self, tool_data: Dict[str, Any]) -> List[str]:
        """
        Get detailed schema validation errors.

        Args:
            tool_data: Tool definition dict

        Returns:
            List of error messages
        """
        errors = []
        try:
            validator = Draft7Validator(tool_data.get("schema", {}))
            for error in validator.iter_errors({}):
                errors.append(error.message)
        except Exception as e:
            errors.append(str(e))
        return errors

    def _check_version_compatibility(
        self, server_id: str, tool_name: str, tool_version: Optional[str]
    ) -> bool:
        """
        Check if tool version is compatible with orchestrator.

        Args:
            server_id: Server identifier
            tool_name: Tool name
            tool_version: Tool version string

        Returns:
            True if compatible, False otherwise
        """
        if tool_version is None:
            return True  # No version specified, assume compatible

        # Check against compatibility matrix
        if server_id in self.version_matrix:
            if tool_name in self.version_matrix[server_id]:
                compatible_versions = self.version_matrix[server_id][tool_name]
                return tool_version in compatible_versions

        # Default: allow if no matrix defined
        return True

    def list_tools(
        self, server_id: Optional[str] = None, enabled_only: bool = True
    ) -> List[MCPTool]:
        """
        List registered tools, optionally filtered by server.

        Args:
            server_id: Optional server ID filter
            enabled_only: Only return enabled tools

        Returns:
            List of MCPTool objects
        """
        with self.db.get_session() as session:
            query = session.query(MCPTool)
            if server_id:
                query = query.filter(MCPTool.server_id == server_id)
            if enabled_only:
                query = query.filter(MCPTool.enabled == True)
            tools = list(query.all())
            # Access all attributes while session is active, then expunge
            for tool in tools:
                _ = tool.id
                _ = tool.server_id
                _ = tool.tool_name
                _ = tool.schema
                _ = tool.version
                _ = tool.enabled
                _ = tool.registered_at
                session.expunge(tool)
            return tools

    def get_tool(self, server_id: str, tool_name: str) -> Optional[MCPTool]:
        """
        Get specific tool by server and name.

        Args:
            server_id: Server identifier
            tool_name: Tool name

        Returns:
            MCPTool or None if not found
        """
        with self.db.get_session() as session:
            tool = (
                session.query(MCPTool)
                .filter_by(server_id=server_id, tool_name=tool_name)
                .first()
            )
            if tool:
                # Access all attributes while session is active
                _ = tool.id
                _ = tool.server_id
                _ = tool.tool_name
                _ = tool.schema
                _ = tool.version
                _ = tool.enabled
                _ = tool.registered_at
                session.expunge(tool)
            return tool

    def list_servers(self, status: Optional[str] = None) -> List[MCPServer]:
        """
        List registered MCP servers.

        Args:
            status: Optional status filter (active, inactive, etc.)

        Returns:
            List of MCPServer objects
        """
        with self.db.get_session() as session:
            query = session.query(MCPServer)
            if status:
                query = query.filter(MCPServer.status == status)
            servers = list(query.all())
            # Access all attributes while session is active, then expunge
            for server in servers:
                _ = server.server_id
                _ = server.version
                _ = server.capabilities
                _ = server.connected_at
                _ = server.last_heartbeat
                _ = server.status
                _ = server.connection_url
                _ = server.server_metadata
                session.expunge(server)
            return servers

    def get_server(self, server_id: str) -> Optional[MCPServer]:
        """
        Get specific server by ID.

        Args:
            server_id: Server identifier

        Returns:
            MCPServer or None if not found
        """
        with self.db.get_session() as session:
            server = session.query(MCPServer).filter_by(server_id=server_id).first()
            if server:
                # Access all attributes while session is active
                _ = server.server_id
                _ = server.version
                _ = server.capabilities
                _ = server.connected_at
                _ = server.last_heartbeat
                _ = server.status
                _ = server.connection_url
                _ = server.server_metadata
                session.expunge(server)
            return server

    def update_server_heartbeat(self, server_id: str) -> None:
        """
        Update server heartbeat timestamp.

        Args:
            server_id: Server identifier
        """
        with self.db.get_session() as session:
            server = session.query(MCPServer).filter_by(server_id=server_id).first()
            if server:
                server.last_heartbeat = utc_now()
                session.commit()

