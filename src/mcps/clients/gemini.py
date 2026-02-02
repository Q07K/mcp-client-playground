from typing import Any

from google import genai
from google.genai import types
from google.genai.chats import Chat
from mcp.types import Tool

from src.core.settings import settings

from .base import REACT_SYSTEM_PROMPT, BaseMCPClient, ReActStep, ToolCallInfo

# Gemini 타입 정의
GeminiMessage = types.Content
GeminiTool = types.Tool
GeminiResponse = types.GenerateContentResponse


class GeminiMCPClient(
    BaseMCPClient[GeminiMessage, GeminiTool, GeminiResponse]
):
    """Gemini API를 사용하는 MCP 클라이언트."""

    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__()

        self._client = genai.Client(api_key=api_key or settings.gemini_api_key)
        self._chat: Chat | None = None
        self._pending_user_input: str = ""
        self._pending_tool_response: types.Part | None = None

    def _convert_tools(self, tools: list[Tool]) -> list[GeminiTool]:
        """MCP 도구를 Gemini 형식으로 변환."""
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name=tool.name,
                        description=tool.description,
                        parameters=tool.inputSchema,
                    )
                    for tool in tools
                ]
            )
        ]

    def _create_initial_messages(self, user_input: str) -> list[GeminiMessage]:
        """초기 메시지 생성 (Gemini는 chat 객체 생성)."""
        # Gemini는 chat 기반이므로 빈 리스트 반환, chat 객체는 _send_message에서 관리
        return []

    def _send_message(
        self,
        model: str,
        messages: list[GeminiMessage],
        tools: list[GeminiTool] | None,
    ) -> GeminiResponse:
        """Gemini API 호출."""
        # 첫 호출 시 chat 객체 생성
        if self._chat is None:
            self._chat = self._client.chats.create(
                model=model,
                config={
                    "tools": tools,
                    "system_instruction": REACT_SYSTEM_PROMPT,
                },
            )
            # messages[-1]은 user input (첫 호출에서만)
            return self._chat.send_message(message=self._pending_user_input)

        # 후속 호출은 도구 결과 전송
        return self._chat.send_message(message=self._pending_tool_response)

    def _parse_response(self, response: GeminiResponse) -> ReActStep:
        """응답에서 Thought와 Tool Call 추출."""
        parts = response.candidates[0].content.parts

        thought_parts = [p.text for p in parts if p.text]
        fc_parts = [p.function_call for p in parts if p.function_call]

        thought = " ".join(thought_parts) if thought_parts else None

        if not fc_parts:
            return ReActStep(thought=thought, tool_call=None)

        fc = fc_parts[0]
        return ReActStep(
            thought=thought,
            tool_call=ToolCallInfo(name=fc.name, arguments=dict(fc.args)),
        )

    def _append_assistant_message(
        self,
        messages: list[GeminiMessage],
        response: GeminiResponse,
    ) -> None:
        """Gemini는 chat 객체가 히스토리 관리하므로 별도 처리 불필요."""
        pass

    def _append_tool_result(
        self,
        messages: list[GeminiMessage],
        tool_call: ToolCallInfo,
        result: Any,
    ) -> None:
        """도구 결과를 pending으로 저장."""
        self._pending_tool_response = types.Part.from_function_response(
            name=tool_call.name, response={"result": result.content}
        )

    def _get_final_response(self, response: GeminiResponse) -> str:
        """최종 응답 추출."""
        self._chat = None  # chat 객체 초기화
        return response.text

    async def chat(self, user_input: str, model: str | None = None) -> str:
        """ReAct 패턴으로 대화 (Gemini용 오버라이드)."""
        self._pending_user_input = user_input
        return await super().chat(user_input, model)


if __name__ == "__main__":
    import asyncio

    from src.core.logger import mcp_logger
    from src.core.settings import settings

    async def main() -> None:
        async with GeminiMCPClient() as client:
            await client.load_servers_from_config(settings.mcp_servers_path)
            response = await client.chat(
                "What is 15 multiplied by 3, then divided by 5?"
            )
            mcp_logger.info("Final response: %s", response)

    asyncio.run(main())
