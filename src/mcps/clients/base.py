from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import Tool

from src.core.config import MCPConfig, TransportType
from src.core.logger import log_execution_time, log_tool_call, mcp_logger


class BaseMCPClient(ABC):
    """MCP 클라이언트 기본 클래스. 서버 연결 및 도구 호출을 관리."""

    def __init__(self) -> None:
        self.sessions: dict[str, ClientSession] = {}
        self.tool_to_server: dict[str, str] = {}
        self.exit_stack = AsyncExitStack()

    @log_execution_time(mcp_logger)
    async def add_server(
        self,
        name: str,
        url: str,
        transport: TransportType = TransportType.SSE,
        headers: dict[str, str] | None = None,
    ) -> None:
        """서버를 추가하고 세션을 등록."""
        conn = await self.exit_stack.enter_async_context(
            streamable_http_client(url, headers=headers or {})
        )
        read, write = conn
        session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await session.initialize()
        self.sessions[name] = session

        # 도구 매핑 업데이트
        tools_resp = await session.list_tools()
        for tool in tools_resp.tools:
            self.tool_to_server[tool.name] = name

        mcp_logger.info(
            "Added MCP server '%s' from %s (transport: %s)",
            name,
            url,
            transport.value,
        )

    async def load_servers_from_config(
        self, config: MCPConfig | dict | str | Path
    ):
        """
        설정에서 모든 서버를 로드하여 연결.

        Args:
            config: MCPConfig 객체, 딕셔너리, JSON 문자열, 또는 JSON 파일 경로

        Examples:
            # JSON 문자열로 로드
            await client.load_servers_from_config('''
            {
              "mcpServers": {
                "math_server": { "url": "http://localhost:8000/sse" }
              }
            }
            ''')

            # 딕셔너리로 로드
            await client.load_servers_from_config({
                "mcpServers": {
                    "math_server": { "url": "http://localhost:8000/sse" }
                }
            })

            # 파일에서 로드
            await client.load_servers_from_config("mcp_config.json")
        """
        # config 타입에 따라 MCPConfig 객체로 변환
        if isinstance(config, MCPConfig):
            mcp_config = config
        elif isinstance(config, dict):
            mcp_config = MCPConfig.from_dict(config)
        elif isinstance(config, Path) or (
            isinstance(config, str) and not config.strip().startswith("{")
        ):
            mcp_config = MCPConfig.from_file(config)
        else:
            mcp_config = MCPConfig.from_json(config)

        mcp_logger.info(
            "Loading %d server(s) from config...", len(mcp_config.servers)
        )

        # 각 서버 연결
        for server in mcp_config.servers:
            await self.add_server(
                name=server.name,
                url=server.url,
                transport=server.transport,
                headers=server.headers,
            )

        mcp_logger.info(
            "Successfully loaded %d server(s). Total tools: %d",
            len(mcp_config.servers),
            len(self.tool_to_server),
        )

    async def get_all_tools(self) -> list[Tool]:
        """모든 연결된 서버로부터 도구 목록을 수집."""
        tools: list[Tool] = []
        for session in self.sessions.values():
            resp = await session.list_tools()
            tools.extend(resp.tools)
        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """도구 이름으로 적절한 서버에 요청을 전달."""
        if (server_name := self.tool_to_server.get(name)) is None:
            raise ValueError(
                f"Tool '{name}' not found in any connected server."
            )
        return await self.sessions[server_name].call_tool(name, arguments)

    @log_tool_call()
    async def execute_tool(
        self, call_count: int, tool_name: str, tool_args: dict[str, Any]
    ) -> Any:
        """툴 호출 실행 (로깅 포함)."""
        return await self.call_tool(tool_name, tool_args)

    @abstractmethod
    async def chat(self, user_input: str, model: str | None = None) -> str:
        """사용자 입력에 대해 LLM과 대화."""
        ...

    async def cleanup(self) -> None:
        """리소스 정리."""
        await self.exit_stack.aclose()

    async def __aenter__(self) -> "BaseMCPClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.cleanup()
