import json
from typing import Any

from mcp.types import Tool
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam
from openai.types.chat.chat_completion import ChatCompletion

from .base import REACT_SYSTEM_PROMPT, BaseMCPClient, ReActStep, ToolCallInfo


class OpenAIMCPClient(
    BaseMCPClient[
        ChatCompletionMessageParam,
        ChatCompletionToolParam,
        ChatCompletion,
    ]
):
    """OpenAI API를 사용하는 MCP 클라이언트."""

    DEFAULT_MODEL = "gpt-4o"

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__()
        from src.core.settings import settings

        self._client = OpenAI(api_key=api_key or settings.openai_api_key)

    def _convert_tools(self, tools: list[Tool]) -> list[ChatCompletionToolParam]:
        """MCP 도구를 OpenAI 형식으로 변환."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                },
            }
            for tool in tools
        ]

    def _create_initial_messages(
        self, user_input: str
    ) -> list[ChatCompletionMessageParam]:
        """초기 메시지 생성."""
        return [
            {"role": "system", "content": REACT_SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ]

    def _send_message(
        self,
        model: str,
        messages: list[ChatCompletionMessageParam],
        tools: list[ChatCompletionToolParam] | None,
    ) -> ChatCompletion:
        """OpenAI API 호출."""
        return self._client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools or None,
            parallel_tool_calls=False if tools else None,
        )

    def _parse_response(self, response: ChatCompletion) -> ReActStep:
        """응답에서 Thought와 Tool Call 추출."""
        message = response.choices[0].message
        thought = message.content

        if not message.tool_calls:
            return ReActStep(thought=thought, tool_call=None)

        tc = message.tool_calls[0]
        return ReActStep(
            thought=thought,
            tool_call=ToolCallInfo(
                name=tc.function.name,
                arguments=json.loads(tc.function.arguments),
                call_id=tc.id,
            ),
        )

    def _append_assistant_message(
        self,
        messages: list[ChatCompletionMessageParam],
        response: ChatCompletion,
    ) -> None:
        """어시스턴트 메시지 추가."""
        messages.append(response.choices[0].message)  # type: ignore

    def _append_tool_result(
        self,
        messages: list[ChatCompletionMessageParam],
        tool_call: ToolCallInfo,
        result: Any,
    ) -> None:
        """도구 결과 메시지 추가."""
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.call_id or "",
                "content": str(result.content),
            }
        )

    def _get_final_response(self, response: ChatCompletion) -> str:
        """최종 응답 추출."""
        return response.choices[0].message.content or ""


if __name__ == "__main__":
    import asyncio

    from src.core.logger import mcp_logger
    from src.core.settings import settings

    async def main() -> None:
        async with OpenAIMCPClient() as client:
            await client.load_servers_from_config(settings.mcp_servers_path)
            response = await client.chat(
                "What is 15 multiplied by 3, then divided by 5?"
            )
            mcp_logger.info("Final response: %s", response)

    asyncio.run(main())
