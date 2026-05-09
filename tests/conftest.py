import pytest
from unittest.mock import AsyncMock, patch

from indy_compta import IndyClient


@pytest.fixture
def mock_indy_client():
    """Return an AsyncMock that stands in for IndyClient."""
    return AsyncMock(spec=IndyClient)


@pytest.fixture
def patched_client(mock_indy_client):
    """Patch _client so all MCP tools use the mock client."""
    with patch(
        "mcp_server_indy_compta.mcp_server._client",
        return_value=mock_indy_client,
    ):
        yield mock_indy_client
