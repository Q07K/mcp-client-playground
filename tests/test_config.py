"""MCP 설정 파싱 테스트 모듈."""

import pytest

from src.core.config import MCPConfig, TransportType


class TestMCPConfig:
    """MCP 설정 파싱 테스트"""

    def test_from_dict(self):
        """딕셔너리에서 설정 로드 테스트"""
        # Arrange
        config_dict = {
            "mcpServers": {
                "math_server": {
                    "url": "http://localhost:8000/sse",
                    "headers": {"Authorization": "Bearer token"},
                    "timeout": 60,
                },
                "weather_server": {
                    "url": "http://localhost:8001/sse",
                },
            }
        }

        # Act
        config = MCPConfig.from_dict(config_dict)

        # Assert
        assert len(config.servers) == 2
        math_server = next(
            s for s in config.servers if s.name == "math_server"
        )
        assert math_server.url == "http://localhost:8000/sse"
        assert math_server.headers == {"Authorization": "Bearer token"}
        assert math_server.timeout == 60

        weather_server = next(
            s for s in config.servers if s.name == "weather_server"
        )
        assert weather_server.url == "http://localhost:8001/sse"
        assert weather_server.headers == {}
        assert weather_server.timeout == 30  # default

    def test_from_json(self):
        """JSON 문자열에서 설정 로드 테스트"""
        # Arrange
        json_str = """
        {
          "mcpServers": {
            "test_server": {
              "url": "http://localhost:9000/sse"
            }
          }
        }
        """

        # Act
        config = MCPConfig.from_json(json_str)

        # Assert
        assert len(config.servers) == 1
        assert config.servers[0].name == "test_server"
        assert config.servers[0].url == "http://localhost:9000/sse"

    def test_transport_type_sse(self):
        """SSE transport 타입 테스트"""
        # Arrange
        config_dict = {
            "mcpServers": {
                "sse_server": {
                    "url": "http://localhost:8000/sse",
                    "transport": "sse",
                }
            }
        }

        # Act
        config = MCPConfig.from_dict(config_dict)

        # Assert
        assert config.servers[0].transport == TransportType.SSE

    def test_transport_type_http(self):
        """HTTP transport 타입 테스트"""
        # Arrange
        config_dict = {
            "mcpServers": {
                "http_server": {
                    "url": "http://localhost:8000/mcp",
                    "transport": "http",
                }
            }
        }

        # Act
        config = MCPConfig.from_dict(config_dict)

        # Assert
        assert config.servers[0].transport == TransportType.HTTP

    def test_transport_type_default(self):
        """transport 미지정 시 기본값(SSE) 테스트"""
        # Arrange
        config_dict = {
            "mcpServers": {
                "default_server": {
                    "url": "http://localhost:8000/sse",
                }
            }
        }

        # Act
        config = MCPConfig.from_dict(config_dict)

        # Assert
        assert config.servers[0].transport == TransportType.SSE

    def test_transport_type_invalid_fallback(self):
        """잘못된 transport 타입 시 SSE로 fallback 테스트"""
        # Arrange
        config_dict = {
            "mcpServers": {
                "invalid_server": {
                    "url": "http://localhost:8000/sse",
                    "transport": "invalid_transport",
                }
            }
        }

        # Act
        config = MCPConfig.from_dict(config_dict)

        # Assert
        assert config.servers[0].transport == TransportType.SSE

    def test_from_file(self, tmp_path):
        """파일에서 설정 로드 테스트"""
        # Arrange
        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(
            """
        {
          "mcpServers": {
            "file_server": {
              "url": "http://localhost:7000/sse",
              "timeout": 120
            }
          }
        }
        """,
            encoding="utf-8",
        )

        # Act
        config = MCPConfig.from_file(config_file)

        # Assert
        assert len(config.servers) == 1
        assert config.servers[0].name == "file_server"
        assert config.servers[0].timeout == 120

    def test_from_file_not_found(self):
        """존재하지 않는 파일 로드 테스트"""
        # Act & Assert
        with pytest.raises(FileNotFoundError):
            MCPConfig.from_file("non_existent_file.json")

    def test_empty_config(self):
        """빈 설정 테스트"""
        # Act
        config = MCPConfig.from_dict({})

        # Assert
        assert len(config.servers) == 0

    def test_empty_mcp_servers(self):
        """빈 mcpServers 테스트"""
        # Act
        config = MCPConfig.from_dict({"mcpServers": {}})

        # Assert
        assert len(config.servers) == 0
