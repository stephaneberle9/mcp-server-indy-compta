"""Basic smoke tests for the MCP tools."""

from unittest.mock import AsyncMock

import pytest
from indy_compta.client import IndyClient

from mcp_server_indy_compta.mcp_server import (
    create_invoice_draft,
    find_matching_invoices,
    find_matching_receipts,
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
    upload_receipt,
)


@pytest.fixture
def mock_client(mocker):
    client = AsyncMock(spec=IndyClient)
    mocker.patch("mcp_server_indy_compta.mcp_server._client", return_value=client)
    return client


async def test_get_transaction_filters(mock_client):
    mock_client.get_transaction_filters.return_value = {
        "accounts": [],
        "categories": [],
    }
    result = await get_transaction_filters()
    assert result == {"accounts": [], "categories": []}
    mock_client.get_transaction_filters.assert_called_once()


async def test_list_transactions_defaults(mock_client):
    mock_client.list_transactions.return_value = {"results": [], "count": 0}
    result = await list_transactions()
    assert "results" in result
    mock_client.list_transactions.assert_called_once_with(
        page=1,
        search="",
        account_or_from=None,
        start_date=None,
        end_date=None,
        transaction_type=None,
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


async def test_upload_receipt(mock_client, tmp_path):
    receipt = tmp_path / "invoice.pdf"
    receipt.write_bytes(b"%PDF-1.4 fake")
    mock_client.upload_receipt.return_value = {"receipt": {"_id": "r1"}}
    result = await upload_receipt("tx-123", str(receipt))
    args, kwargs = mock_client.upload_receipt.call_args
    assert args[0] == "tx-123"
    assert args[1] == receipt.resolve()  # validated, resolved Path passed through
    assert kwargs == {"filename": None, "content_type": None}
    assert "receipt" in result


async def test_upload_receipt_rejects_missing_file(mock_client, tmp_path):
    with pytest.raises(FileNotFoundError):
        await upload_receipt("tx-123", str(tmp_path / "nope.pdf"))
    mock_client.upload_receipt.assert_not_called()


async def test_upload_receipt_rejects_bad_extension(mock_client, tmp_path):
    secret = tmp_path / "id_rsa"
    secret.write_text("PRIVATE KEY")
    with pytest.raises(ValueError, match="Unsupported receipt file type"):
        await upload_receipt("tx-123", str(secret))
    mock_client.upload_receipt.assert_not_called()


async def test_upload_receipt_rejects_oversized_file(
    mock_client, tmp_path, monkeypatch
):
    monkeypatch.setattr("mcp_server_indy_compta.mcp_server._MAX_RECEIPT_BYTES", 4)
    receipt = tmp_path / "big.pdf"
    receipt.write_bytes(b"more than four bytes")
    with pytest.raises(ValueError, match="exceeds"):
        await upload_receipt("tx-123", str(receipt))
    mock_client.upload_receipt.assert_not_called()


async def test_find_matching_receipts(mock_client):
    mock_client.find_matching_receipts.return_value = {
        "receipts": [],
        "transactions": [],
    }
    result = await find_matching_receipts(["tx-123"])
    mock_client.find_matching_receipts.assert_called_once_with(["tx-123"])
    assert "receipts" in result


async def test_find_matching_invoices(mock_client):
    mock_client.find_matching_invoices.return_value = {
        "invoices": [],
        "transactions": [],
    }
    result = await find_matching_invoices(["tx-123"])
    mock_client.find_matching_invoices.assert_called_once_with(["tx-123"])
    assert "invoices" in result


async def test_get_client_suggestions(mock_client):
    mock_client.get_client_suggestions.return_value = [{"id": "c1", "name": "ACME"}]
    result = await get_client_suggestions()
    assert len(result) == 1


async def test_list_clients_defaults(mock_client):
    mock_client.list_clients.return_value = {"results": []}
    await list_clients()
    mock_client.list_clients.assert_called_once_with(search="", current_page=1)


async def test_list_products(mock_client):
    mock_client.list_products.return_value = {"products": []}
    result = await list_products()
    assert "products" in result


async def test_list_invoice_drafts_defaults(mock_client):
    mock_client.list_invoice_drafts.return_value = {"drafts": []}
    await list_invoice_drafts()
    mock_client.list_invoice_drafts.assert_called_once_with(start=0, limit=20)


async def test_list_invoices_defaults(mock_client):
    mock_client.list_invoices.return_value = {"invoices": []}
    await list_invoices()
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


# Every IndyClient method the tools delegate to. The mock-based tests above can't
# catch a rename on the lib side (e.g. upload_invoice -> upload_receipt), so this
# guards the tool-to-client contract against the real class.
CLIENT_METHODS = [
    "get_transaction_filters",
    "list_transactions",
    "list_all_transactions",
    "list_pending_transactions",
    "get_receipts_for_transaction",
    "upload_receipt",
    "find_matching_receipts",
    "find_matching_invoices",
    "get_client_suggestions",
    "list_clients",
    "list_products",
    "list_invoice_drafts",
    "list_invoices",
    "create_invoice_draft",
]


@pytest.mark.parametrize("method_name", CLIENT_METHODS)
def test_indy_client_exposes_method(method_name):
    assert callable(getattr(IndyClient, method_name, None)), (
        f"IndyClient is missing method '{method_name}' that an MCP tool depends on"
    )


# Public IndyClient methods that are intentionally not surfaced as MCP tools
# (e.g. auth/lifecycle plumbing). Add a method here only with a reason.
UNWRAPPED_CLIENT_METHODS: set[str] = set()


def test_no_unwrapped_client_methods():
    """Fail if IndyClient grows a public method that no MCP tool covers.

    The reverse of test_indy_client_exposes_method: that one catches renames and
    removals; this one catches new API methods landing in the lib without a tool.
    """
    import inspect

    public = {
        name
        for name, _ in inspect.getmembers(IndyClient, predicate=callable)
        if not name.startswith("_")
    }
    uncovered = public - set(CLIENT_METHODS) - UNWRAPPED_CLIENT_METHODS
    assert not uncovered, (
        f"IndyClient exposes public method(s) {sorted(uncovered)} with no MCP tool. "
        "Add a tool, or list them in UNWRAPPED_CLIENT_METHODS with a reason."
    )
