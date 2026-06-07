import logging
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.prompts import Message

from .indy_client import IndyClientProvider

logger = logging.getLogger(__name__)

mcp = FastMCP("Indy.fr Accounting")

_provider = IndyClientProvider()

# Receipt uploads egress file bytes to Indy, and the path is model-controlled, so
# constrain what upload_receipt will read: real receipt formats only, under a sane
# size cap. This stops a prompt-injected model from shipping arbitrary local files
# (keys, credentials) before the bytes leave the machine.
_ALLOWED_RECEIPT_SUFFIXES = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".heic"})
_MAX_RECEIPT_BYTES = 25 * 1024 * 1024  # 25 MB


def _validated_receipt_path(file_path: str) -> Path:
    path = Path(file_path).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError(f"Not a regular file: {file_path}")
    if path.suffix.lower() not in _ALLOWED_RECEIPT_SUFFIXES:
        allowed = ", ".join(sorted(_ALLOWED_RECEIPT_SUFFIXES))
        raise ValueError(
            f"Unsupported receipt file type '{path.suffix}'. Allowed: {allowed}."
        )
    size = path.stat().st_size
    if size > _MAX_RECEIPT_BYTES:
        raise ValueError(
            f"Receipt file is {size} bytes, exceeds the {_MAX_RECEIPT_BYTES}-byte limit."
        )
    return path


def _client():
    """Return the singleton IndyClient. Browser auth is deferred until the first API call."""
    return _provider.get_client()


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


@mcp.tool(
    name="get_transaction_filters",
    description=(
        "Return filter metadata for transactions: available date ranges, bank accounts, "
        "and transaction categories. Call this before constructing list_transactions queries "
        "to discover valid filter values."
    ),
)
async def get_transaction_filters() -> dict[str, Any]:
    return await _client().get_transaction_filters()


@mcp.tool(
    name="list_transactions",
    description=(
        "Return a paginated list of Indy.fr transactions (30 per page). "
        "Use get_transaction_filters to discover valid filter values. "
        "Parameters: page (1-based), search (free text), account_or_from (bank account filter), "
        "start_date / end_date (ISO 8601 date strings, e.g. '2024-01-01'), "
        "transaction_type (income / expense / transfer — check get_transaction_filters for exact values)."
    ),
)
async def list_transactions(
    page: int = 1,
    search: str = "",
    account_or_from: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    transaction_type: str | None = None,
) -> dict[str, Any]:
    return await _client().list_transactions(
        page=page,
        search=search,
        account_or_from=account_or_from,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type,
    )


@mcp.tool(
    name="list_all_transactions",
    description=(
        "Fetch ALL transactions across all pages and return them as a flat list. "
        "Accepts the same filters as list_transactions (except page). "
        "Warning: may return large amounts of data — prefer list_transactions with pagination "
        "unless a complete dataset is required."
    ),
)
async def list_all_transactions(
    search: str = "",
    account_or_from: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    transaction_type: str | None = None,
) -> list[dict[str, Any]]:
    return await _client().list_all_transactions(
        search=search,
        account_or_from=account_or_from,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type,
    )


@mcp.tool(
    name="list_pending_transactions",
    description="Return pending and upcoming (not yet booked) transactions from Indy.fr.",
)
async def list_pending_transactions() -> dict[str, Any]:
    return await _client().list_pending_transactions()


@mcp.tool(
    name="get_receipts_for_transaction",
    description="Return all receipt or invoice documents already attached to a given transaction.",
)
async def get_receipts_for_transaction(transaction_id: str) -> dict[str, Any]:
    return await _client().get_receipts_for_transaction(transaction_id)


@mcp.tool(
    name="upload_receipt",
    description=(
        "Upload a receipt or expense document (PDF or image) from disk and attach it to a "
        "transaction. Note: only receipts can be uploaded — invoices are created with "
        "create_invoice_draft, not uploaded. "
        "Parameters: transaction_id (target transaction), file_path (path to the document on "
        "this machine), filename (optional override for the name sent to Indy), "
        "content_type (optional MIME type; inferred from the extension when omitted). "
        "Indy runs OCR on the upload and returns the new receipt with extracted fields "
        "(description, amount, date) under 'receiptData'."
    ),
)
async def upload_receipt(
    transaction_id: str,
    file_path: str,
    filename: str | None = None,
    content_type: str | None = None,
) -> dict[str, Any]:
    path = _validated_receipt_path(file_path)
    return await _client().upload_receipt(
        transaction_id,
        path,
        filename=filename,
        content_type=content_type,
    )


@mcp.tool(
    name="find_matching_receipts",
    description=(
        "Find already-uploaded but unattached receipts that could match the given transactions, "
        "so they can be linked instead of re-uploaded. "
        "Parameters: transaction_ids (list of transaction ids to find matches for). "
        "Returns 'receipts' (candidate receipt objects) and 'transactions' (the transactions a "
        "match was found for); both empty when nothing matches."
    ),
)
async def find_matching_receipts(transaction_ids: list[str]) -> dict[str, Any]:
    return await _client().find_matching_receipts(transaction_ids)


@mcp.tool(
    name="find_matching_invoices",
    description=(
        "Find finalized billing invoices that could match the given transactions, so an issued "
        "invoice can be reconciled with an incoming payment. The sales counterpart to "
        "find_matching_receipts. "
        "Parameters: transaction_ids (list of transaction ids to find matches for). "
        "Returns 'invoices' (candidate invoice objects) and 'transactions' (the transactions a "
        "match was found for); both empty when nothing matches."
    ),
)
async def find_matching_invoices(transaction_ids: list[str]) -> dict[str, Any]:
    return await _client().find_matching_invoices(transaction_ids)


# ---------------------------------------------------------------------------
# Clients & products
# ---------------------------------------------------------------------------


@mcp.tool(
    name="get_client_suggestions",
    description="Return the full unfiltered list of billing clients registered in Indy.fr.",
)
async def get_client_suggestions() -> list[dict[str, Any]]:
    return await _client().get_client_suggestions()


@mcp.tool(
    name="list_clients",
    description=(
        "Search billing clients in Indy.fr with pagination. "
        "Parameters: search (free-text filter), current_page (1-based)."
    ),
)
async def list_clients(
    search: str = "",
    current_page: int = 1,
) -> dict[str, Any]:
    return await _client().list_clients(search=search, current_page=current_page)


@mcp.tool(
    name="list_products",
    description="Return all saved products and services from the Indy.fr product library.",
)
async def list_products() -> dict[str, Any]:
    return await _client().list_products()


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------


@mcp.tool(
    name="list_invoice_drafts",
    description=(
        "Return a paginated list of invoice drafts from Indy.fr. "
        "Parameters: start (0-based offset), limit (number of results, default 20)."
    ),
)
async def list_invoice_drafts(
    start: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    return await _client().list_invoice_drafts(start=start, limit=limit)


@mcp.tool(
    name="list_invoices",
    description=(
        "Return a paginated list of finalized invoices from Indy.fr. "
        "Parameters: status (e.g. 'paid', 'pending', 'overdue' — omit for all), "
        "start (0-based offset), limit (number of results, default 20)."
    ),
)
async def list_invoices(
    status: str | None = None,
    start: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    return await _client().list_invoices(status=status, start=start, limit=limit)


@mcp.tool(
    name="create_invoice_draft",
    description=(
        "Create a new invoice draft in Indy.fr. "
        "Parameters: title (invoice title), client_id (use list_clients to look up), "
        "products (list of line items — each dict with at minimum 'name' and 'unit_price_cents'), "
        "iban / bic (optional payment details), payment_delay_days (default 0), "
        "payment_delay_reference ('ON_RECEIPT' or 'END_OF_MONTH' etc.), "
        "introduction_text / other_payment_conditions (optional free-text fields)."
    ),
)
async def create_invoice_draft(
    title: str,
    client_id: str,
    products: list[dict[str, Any]],
    iban: str | None = None,
    bic: str | None = None,
    payment_delay_days: int = 0,
    payment_delay_reference: str = "ON_RECEIPT",
    introduction_text: str | None = None,
    other_payment_conditions: str | None = None,
) -> dict[str, Any]:
    return await _client().create_invoice_draft(
        title=title,
        client_id=client_id,
        products=products,
        iban=iban,
        bic=bic,
        payment_delay_days=payment_delay_days,
        payment_delay_reference=payment_delay_reference,
        introduction_text=introduction_text,
        other_payment_conditions=other_payment_conditions,
    )


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt(
    name="monthly_expense_summary",
    description=(
        "Generate a monthly expense summary report. "
        "Fetches all expense transactions for the given month and presents them "
        "grouped by category with totals."
    ),
)
def monthly_expense_summary(year: int, month: int) -> list[Message]:
    """Prompt the assistant to produce a categorised monthly expense report.

    Args:
        year: The calendar year (e.g. 2024).
        month: The month number (1–12).
    """
    start = f"{year:04d}-{month:02d}-01"
    # Last day heuristic: use the first day of the next month minus one day
    next_month = month % 12 + 1
    next_year = year + (1 if month == 12 else 0)
    end = f"{next_year:04d}-{next_month:02d}-01"

    return [
        Message(
            f"Please produce a monthly expense summary for {year}-{month:02d}.\n\n"
            f"Steps:\n"
            f"1. Call `list_all_transactions` with transaction_type='expense', "
            f"start_date='{start}', end_date='{end}'.\n"
            f"2. Group the results by category.\n"
            f"3. Calculate the total amount per category and an overall total.\n"
            f"4. Present the report as a markdown table with columns: "
            f"Category | Number of transactions | Total (€).\n"
            f"5. Highlight the top 3 spending categories.\n"
            f"6. Note any transactions without a category that may need review."
        )
    ]


@mcp.prompt(
    name="create_invoice_workflow",
    description=(
        "Step-by-step workflow to create an invoice draft for a client. "
        "Looks up the client by name and guides through building the invoice."
    ),
)
def create_invoice_workflow(
    client_name: str, service_description: str, amount_euros: float
) -> list[Message]:
    """Prompt the assistant to create an invoice draft interactively.

    Args:
        client_name: Name (or partial name) of the billing client.
        service_description: Description of the service or product to invoice.
        amount_euros: The amount to invoice in euros (excluding VAT).
    """
    amount_cents = int(amount_euros * 100)
    return [
        Message(
            f"Please create an invoice draft for '{client_name}' for the service "
            f"'{service_description}' at €{amount_euros:.2f} (excl. VAT).\n\n"
            f"Steps:\n"
            f"1. Call `list_clients` with search='{client_name}' to find the client. "
            f"If multiple matches are returned, ask me which one to use.\n"
            f"2. Call `list_products` to check if '{service_description}' already exists "
            f"as a saved product. If so, reuse its unit price.\n"
            f"3. Call `create_invoice_draft` with:\n"
            f"   - title: an appropriate invoice title\n"
            f"   - client_id: the ID from step 1\n"
            f"   - products: [{{'name': '{service_description}', 'unit_price_cents': {amount_cents}}}]\n"
            f"4. Confirm the draft was created and show me the draft ID and any next steps "
            f"to finalise and send it."
        )
    ]


@mcp.prompt(
    name="cash_flow_analysis",
    description=(
        "Analyse income vs. expenses for a given date range to give a cash-flow overview. "
        "Compares total income and total expenses and calculates the net balance."
    ),
)
def cash_flow_analysis(start_date: str, end_date: str) -> list[Message]:
    """Prompt the assistant to run a cash-flow analysis over a date range.

    Args:
        start_date: Start of the period in ISO 8601 format (e.g. '2024-01-01').
        end_date: End of the period in ISO 8601 format (e.g. '2024-03-31').
    """
    return [
        Message(
            f"Please analyse cash flow for the period {start_date} to {end_date}.\n\n"
            f"Steps:\n"
            f"1. Call `list_all_transactions` with transaction_type='income', "
            f"start_date='{start_date}', end_date='{end_date}' → sum all amounts for total income.\n"
            f"2. Call `list_all_transactions` with transaction_type='expense', "
            f"start_date='{start_date}', end_date='{end_date}' → sum all amounts for total expenses.\n"
            f"3. Also call `list_pending_transactions` to show upcoming cash movements.\n"
            f"4. Present a summary:\n"
            f"   - Total income (€)\n"
            f"   - Total expenses (€)\n"
            f"   - Net cash flow (€)\n"
            f"   - Pending income and pending expenses from step 3\n"
            f"5. Flag any unusually large individual transactions (top 5 by amount in each direction)."
        )
    ]


@mcp.prompt(
    name="unreceipted_transactions",
    description=(
        "Find expense transactions that have no receipt or invoice attached. "
        "Useful for bookkeeping hygiene checks before a VAT or tax deadline."
    ),
)
def unreceipted_transactions(start_date: str, end_date: str) -> list[Message]:
    """Prompt the assistant to identify expense transactions missing receipts.

    Args:
        start_date: Start of the period in ISO 8601 format (e.g. '2024-01-01').
        end_date: End of the period in ISO 8601 format (e.g. '2024-12-31').
    """
    return [
        Message(
            f"Please find all expense transactions between {start_date} and {end_date} "
            f"that have no receipt or invoice attached.\n\n"
            f"Steps:\n"
            f"1. Call `list_all_transactions` with transaction_type='expense', "
            f"start_date='{start_date}', end_date='{end_date}'.\n"
            f"2. For each transaction, call `get_receipts_for_transaction` with its ID.\n"
            f"3. Collect all transactions where the receipts list is empty.\n"
            f"4. Present the results as a markdown table: "
            f"Date | Description | Amount (€) | Category.\n"
            f"5. State the total number and combined value of transactions missing receipts.\n"
            f"6. Suggest which ones are most urgent to resolve based on amount."
        ),
        Message(
            "I'll work through the transactions systematically and report back once "
            "I have identified all the ones missing receipts.",
            role="assistant",
        ),
    ]
