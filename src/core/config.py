"""
MCP 서버 설정 스키마 모듈.
SSE 및 HTTP 방식의 MCP 서버 연결 설정을 정의.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from src.core.logger import mcp_logger


class TransportType(str, Enum):
    """MCP Transport 타입"""

    SSE = "sse"
    HTTP = "http"


@dataclass
class MCPServerConfig:
    """단일 MCP 서버 설정"""

    name: str
    url: str
    transport: TransportType = TransportType.SSE
    headers: dict[str, str] = field(default_factory=dict)
    timeout: int = 30


@dataclass
class MCPConfig:
    """전체 MCP 설정"""

    servers: list[MCPServerConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCPConfig":
        """딕셔너리에서 설정 로드"""
        servers = []
        mcp_servers = data.get("mcpServers", {})

        for name, config in mcp_servers.items():
            # transport 타입 파싱 (기본값: sse)
            transport_str = config.get("transport", "sse").lower()
            try:
                transport = TransportType(transport_str)
            except ValueError:
                mcp_logger.warning(
                    f"Unknown transport '{transport_str}' for {name}, "
                    f"falling back to 'sse'"
                )
                transport = TransportType.SSE

            server = MCPServerConfig(
                name=name,
                url=config.get("url", ""),
                transport=transport,
                headers=config.get("headers", {}),
                timeout=config.get("timeout", 30),
            )
            servers.append(server)
            mcp_logger.debug(
                f"Loaded server config: {name} -> {server.url} ({transport.value})"
            )

        return cls(servers=servers)

    @classmethod
    def from_json(cls, json_str: str) -> "MCPConfig":
        """JSON 문자열에서 설정 로드"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, file_path: str | Path) -> "MCPConfig":
        """JSON 파일에서 설정 로드"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        mcp_logger.info(f"Loaded config from file: {file_path}")
        return cls.from_dict(data)


# SSE 및 HTTP 서버 설정 예시 JSON 템플릿
CONFIG_EXAMPLE = """
{
  "mcpServers": {
    "math_server": {
      "url": "http://localhost:8000/sse",
      "transport": "sse",
      "headers": {},
      "timeout": 30
    },
    "weather_server": {
      "url": "http://localhost:8001/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      },
      "timeout": 60
    },
    "http_api_server": {
      "url": "http://localhost:8002/mcp",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      },
      "timeout": 30
    }
  }
}
"""

__all__ = [
    "TransportType",
    "MCPServerConfig",
    "MCPConfig",
    "CONFIG_EXAMPLE",
]
