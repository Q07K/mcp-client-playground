"""An example MCP server with basic arithmetic operations."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP()


@mcp.tool()
def add(a: int | float, b: int | float) -> int | float:
    """Add two numbers."""
    return a + b


@mcp.tool()
def multiply(a: int | float, b: int | float) -> int | float:
    """Multiply two numbers."""
    return a * b


@mcp.tool()
def divide(a: int | float, b: int | float) -> float:
    """Divide two numbers."""
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b


@mcp.tool()
def subtract(a: int | float, b: int | float) -> int | float:
    """Subtract two numbers."""
    return a - b


if __name__ == "__main__":
    mcp.run("sse")
