"""Indy.fr accounting MCP server."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mcp_server_indy_compta")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
