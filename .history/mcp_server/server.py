from mcp.server.fastmcp import FastMCP

mcp = FastMCP("DAA MCP Server", host="0.0.0.0", port=8000)


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@mcp.tool()
def greet(name: str) -> str:
    """Greet a person by name."""
    return f"Hello, {name}!"


@mcp.resource("data://info")
def get_info() -> str:
    """Return basic server info."""
    return "DAA MCP Server is running."


if __name__ == "__main__":
    mcp.run(transport="sse")
