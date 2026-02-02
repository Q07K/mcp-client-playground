"""테스트 공통 fixtures 및 Mock 클래스."""

from dataclasses import dataclass


@dataclass
class MockToolResult:
    """Mock tool result"""

    content: str


@dataclass
class MockTool:
    """Mock MCP tool"""

    name: str
    description: str
    inputSchema: dict
