"""lab-tools: an MCP server that exposes home-lab checks as tools."""
import socket
import time

import httpx
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("lab-tools")


@mcp.tool()
def check_url(url: str) -> str:
    """Fetch a URL and report the HTTP status and response time."""
    start = time.monotonic()
    try:
        r = httpx.get(url, timeout=5, follow_redirects=True)
        return f"HTTP {r.status_code} in {(time.monotonic() - start) * 1000:.0f} ms"
    except httpx.HTTPError as err:
        return f"failed: {err!r}"


@mcp.tool()
def check_port(host: str, port: int) -> str:
    """Test whether a TCP port on a host accepts connections."""
    try:
        with socket.create_connection((host, port), timeout=3):
            return f"{host}:{port} is open"
    except OSError as err:
        return f"{host}:{port} is closed or unreachable ({err})"


@mcp.tool()
def dns_lookup(name: str) -> str:
    """Resolve a host name to its IP addresses."""
    try:
        return ", ".join(sorted({ai[4][0] for ai in socket.getaddrinfo(name, None)}))
    except OSError as err:
        return f"lookup failed: {err}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8701)
