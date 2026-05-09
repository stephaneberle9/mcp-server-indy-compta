"""Basic smoke tests for the MCP tools."""

import pytest
from unittest.mock import AsyncMock, patch

from mcp_server_indy_compta.mcp_server import (
    create_invoice_draft,
    get_client_suggestions,
    get_receipts_for_transaction,
    get_transaction_filters,
    list_all_transactions,
    list_clients,
    list_invoice_drafts,
    list_invoices,
    list_pending_transactions,
    list_products,
    list_transactions,
)


@pytest.fixture
def mock_client(mocker):
    client = AsyncMock()
    mocker.patch("mcp_server_indy_compta.mcp_server._client", return_value=client)
    return client


async def test_get_transaction_filters(mock_client):
    mock_client.get_transaction_filters.return_value = {"accounts": [], "categories": []}
    result = await get_transaction_filters()
    assert result == {"accounts": [], "categories": []}
    mock_client.get_transaction_filters.assert_called_once()


async def test_list_transactions_defaults(mock_client):
    mock_client.list_transactions.return_value = {"results": [], "count": 0}
    result = await list_transactions()
    assert "results" in result
    mock_client.list_transactions.assert_called_once_with(
        page=1, search="", account_or_from=None,
        start_date=None, end_date=None, transaction_type=None,
    )


async def test_list_all_transactions(mock_client):
    mock_client.list_all_transactions.return_value = []
    result = await list_all_transactions()
    assert result == []


async def test_list_pending_transactions(mock_client):
    mock_client.list_pending_transactions.return_value = {"results": []}
    result = await list_pending_transactions()
    assert "results" in result


async def test_get_receipts_for_transaction(mock_client):
    mock_client.get_receipts_for_transaction.return_value = {"receipts": []}
    result = await get_receipts_for_transaction("tx-123")
    mock_client.get_receipts_for_transaction.assert_called_once_with("tx-123")
    assert "receipts" in result


async def test_get_client_suggestions(mock_client):
    mock_client.get_client_suggestions.return_value = [{"id": "c1", "name": "ACME"}]
    result = await get_client_suggestions()
    assert len(result) == 1


async def test_list_clients_defaults(mock_client):
    mock_client.list_clients.return_value = {"results": []}
    result = await list_clients()
    mock_client.list_clients.assert_called_once_with(search="", current_page=1)


async def test_list_products(mock_client):
    mock_client.list_products.return_value = {"products": []}
    result = await list_products()
    assert "products" in result


async def test_list_invoice_drafts_defaults(mock_client):
    mock_client.list_invoice_drafts.return_value = {"drafts": []}
    result = await list_invoice_drafts()
    mock_client.list_invoice_drafts.assert_called_once_with(start=0, limit=20)


async def test_list_invoices_defaults(mock_client):
    mock_client.list_invoices.return_value = {"invoices": []}
    result = await list_invoices()
    mock_client.list_invoices.assert_called_once_with(status=None, start=0, limit=20)


async def test_create_invoice_draft(mock_client):
    mock_client.create_invoice_draft.return_value = {"id": "draft-1"}
    result = await create_invoice_draft(
        title="Invoice #1",
        client_id="c1",
        products=[{"name": "Consulting", "unit_price_cents": 10000}],
    )
    assert result == {"id": "draft-1"}
    mock_client.create_invoice_draft.assert_called_once()
