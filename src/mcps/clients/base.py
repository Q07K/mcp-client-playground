from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TypeVar

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import Tool

from src.core.config import MCPConfig, TransportType
from src.core.logger import log_execution_time, log_tool_call, mcp_logger

# 제네릭 타입: 각 LLM의 메시지/도구/응답 타입
TMessage = TypeVar("TMessage")
TTool = TypeVar("TTool")
TResponse = TypeVar("TResponse")


@dataclass
class ToolCallInfo:
    """도구 호출 정보를 담는 데이터 클래스."""

    name: str
    arguments: dict[str, Any]
    call_id: str | None = None  # OpenAI용


@dataclass
class ReActStep:
    """ReAct 단계 정보."""

    thought: str | None
    tool_call: ToolCallInfo | None


REACT_SYSTEM_PROMPT = """You are a helpful assistant that follows the ReAct pattern.
For each step, you MUST:
1. Think: Reason about what to do next based on the current state
2. Act: Call exactly ONE tool if needed
3. Observe: Process the tool result before deciding next action

Always explain your reasoning before taking an action.
Call only ONE tool at a time, then wait for the result before proceeding."""


class BaseMCPClient(ABC, Generic[TMessage, TTool, TResponse]):
    """MCP 클라이언트 기본 클래스. 서버 연결, 도구 호출, ReAct 루프를 관리."""

    DEFAULT_MODEL: str = ""

    def __init__(self) -> None:
        self.sessions: dict[str, ClientSession] = {}
        self.tool_to_server: dict[str, str] = {}
        self.exit_stack = AsyncExitStack()

    # ========== MCP 서버 관리 ==========

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
        """설정에서 모든 서버를 로드하여 연결."""
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

    # ========== 추상 메서드: 구현체에서 오버라이드 ==========

    @abstractmethod
    def _convert_tools(self, tools: list[Tool]) -> list[TTool]:
        """MCP 도구를 LLM 형식으로 변환."""
        ...

    @abstractmethod
    def _create_initial_messages(self, user_input: str) -> list[TMessage]:
        """초기 메시지 리스트 생성 (시스템 프롬프트 + 사용자 입력)."""
        ...

    @abstractmethod
    def _send_message(
        self,
        model: str,
        messages: list[TMessage],
        tools: list[TTool] | None,
    ) -> TResponse:
        """LLM에 메시지 전송."""
        ...

    @abstractmethod
    def _parse_response(self, response: TResponse) -> ReActStep:
        """응답에서 Thought와 Tool Call 정보 추출."""
        ...

    @abstractmethod
    def _append_assistant_message(
        self, messages: list[TMessage], response: TResponse
    ) -> None:
        """어시스턴트 응답을 메시지 리스트에 추가."""
        ...

    @abstractmethod
    def _append_tool_result(
        self,
        messages: list[TMessage],
        tool_call: ToolCallInfo,
        result: Any,
    ) -> None:
        """도구 실행 결과를 메시지 리스트에 추가."""
        ...

    @abstractmethod
    def _get_final_response(self, response: TResponse) -> str:
        """최종 응답 텍스트 추출."""
        ...

    # ========== ReAct 루프 (공통 로직) ==========

    @log_execution_time(logger=mcp_logger)
    async def chat(self, user_input: str, model: str | None = None) -> str:
        """ReAct 패턴으로 대화하며 필요시 도구 호출."""
        model = model or self.DEFAULT_MODEL
        mcp_tools = await self.get_all_tools()
        llm_tools = self._convert_tools(mcp_tools) if mcp_tools else None

        messages = self._create_initial_messages(user_input)
        response = self._send_message(model, messages, llm_tools)

        # ReAct 루프: Thought → Action → Observation
        call_count = 0
        while True:
            step = self._parse_response(response)

            if step.tool_call is None:
                break

            if step.thought:
                mcp_logger.info(
                    "[Thought %d] %s", call_count + 1, step.thought
                )

            self._append_assistant_message(messages, response)

            # Action: 단일 도구 호출
            tc = step.tool_call
            call_count += 1
            mcp_logger.info(
                "[Action %d] %s(%s)", call_count, tc.name, tc.arguments
            )

            # Observation: 도구 실행 결과
            result = await self.execute_tool(call_count, tc.name, tc.arguments)
            mcp_logger.info("[Observation %d] %s", call_count, result.content)

            self._append_tool_result(messages, tc, result)
            response = self._send_message(model, messages, llm_tools)

        return self._get_final_response(response)

    # ========== 리소스 관리 ==========

    async def cleanup(self) -> None:
        """리소스 정리."""
        await self.exit_stack.aclose()

    async def __aenter__(self) -> "BaseMCPClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.cleanup()
