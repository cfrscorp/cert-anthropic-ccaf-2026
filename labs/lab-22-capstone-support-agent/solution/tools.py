"""Capstone reference — the four MCP-style customer-support tools.

Scenario 1 (Customer Support Resolution Agent) gives the agent four backend
tools: ``get_customer``, ``lookup_order``, ``process_refund`` and
``escalate_to_human``. This module is SELF-CONTAINED (the capstone does not
import other labs) and pulls together three exam ideas:

* **Task Statement 2.1 — disambiguating tool descriptions.** ``get_customer`` and
  ``lookup_order`` accept similar-looking identifiers, so each :data:`TOOLS`
  entry states its input format, an example query, edge-case behaviour, and an
  explicit "use this when … not when …" boundary that points at its sibling.
  Minimal descriptions ("Retrieves customer information") are exactly what
  Sample Question 2 warns against.
* **Task Statement 2.2 — structured error responses.** :func:`make_error`
  returns ``{"isError", "errorCategory", "isRetryable", "message"}`` so the agent
  can retry a *transient* failure but explain a *business* one instead of
  hammering it. A generic "operation failed" string cannot carry that decision.
* **Empty vs. failure.** A ``lookup_order`` that matches nothing returns a valid
  ``{"found": False}`` result (not an error); a real access failure is an error
  object. Confusing the two is the anti-pattern behind Task Statement 5.3.

Backends are dependency-injected so tests stay deterministic. ``backends`` is a
mapping that may hold data (``customers``, ``orders``) and/or per-tool callable
overrides (``backends["lookup_order"] = fn``) — the override lets a test inject a
transient-then-success sequence without touching this module.

Imported module — carries docstrings, exempt from the PEP 723 / argparse
script conventions.
"""

from __future__ import annotations

from typing import Any, Callable

__all__ = [
    "TOOLS",
    "TOOL_NAMES",
    "CATEGORIES",
    "make_error",
    "execute_tool",
    "default_backends",
]

TOOL_NAMES: tuple[str, ...] = (
    "get_customer",
    "lookup_order",
    "process_refund",
    "escalate_to_human",
)

# The four structured-error categories from Task Statement 2.2. Only transient
# failures are retryable; retrying the others re-runs identical input and fails
# the same way, so the agent must communicate instead of retry.
CATEGORIES: tuple[str, ...] = ("transient", "validation", "business", "permission")
_RETRYABLE: dict[str, bool] = {
    "transient": True,
    "validation": False,
    "business": False,
    "permission": False,
}


# --------------------------------------------------------------------------- #
# Tool schemas with disambiguating descriptions (Task Statement 2.1)
# --------------------------------------------------------------------------- #
TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_customer",
        "description": (
            "Look up a customer's ACCOUNT PROFILE and VERIFY their identity: "
            "returns a verified customer_id, name, email, and account standing. "
            "This is the identity-verification step every account-specific action "
            "depends on.\n\n"
            "Input: {\"customer_id\": \"CUST-<digits>\"} (e.g. \"CUST-40912\"), or "
            "{\"email\": \"person@example.com\"}, or {\"name\": \"Jane Doe\"}. It "
            "does NOT accept an order number.\n\n"
            "Example query: \"Who is account CUST-40912?\" or \"Find the account "
            "for jane@example.com.\"\n\n"
            "Edge cases: if an email or name matches more than one account it "
            "returns match_count>1 with the candidates and verified=false — ask "
            "the customer for their customer_id rather than guessing. A no-match "
            "lookup returns match_count=0 (a valid empty result, not an error).\n\n"
            "Use this when you need to know WHO the customer is or must verify "
            "identity before an order or refund action; do NOT use it to fetch a "
            "specific order's status (use lookup_order)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "CUST-<digits> identifier."},
                "email": {"type": "string", "description": "Account email address."},
                "name": {"type": "string", "description": "Customer full name (may be ambiguous)."},
            },
        },
    },
    {
        "name": "lookup_order",
        "description": (
            "Retrieve a single ORDER's status and contents: status, order total, "
            "tracking number, delivery estimate, line items, and the owning "
            "customer_id.\n\n"
            "Input: {\"order_id\": \"ORD-<digits>\"} (e.g. \"ORD-88213\"). Accepts "
            "an order number ONLY; it does not accept a customer_id or email.\n\n"
            "Example query: \"Where is order ORD-88213 and has it shipped?\"\n\n"
            "Edge cases: an order number that does not exist returns "
            "{\"found\": false} (a valid empty result, not an error). A cancelled "
            "order still returns its record with status \"cancelled\".\n\n"
            "Use this when the question is about a SPECIFIC order's status or "
            "shipment; do NOT use it to look up the customer's profile (use "
            "get_customer). This tool acts on a specific account, so it is blocked "
            "until get_customer has verified the customer."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "ORD-<digits> identifier."},
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "process_refund",
        "description": (
            "Issue a refund against a verified customer's order. Returns a "
            "refund_id and confirmation on success.\n\n"
            "Input: {\"order_id\": \"ORD-<digits>\", \"amount\": <number>, "
            "\"reason\": \"<text>\"}. The amount is in dollars.\n\n"
            "Boundaries: refunds are auto-approved only up to a policy ceiling "
            "($500 by default). A larger refund is blocked and redirected to human "
            "escalation by a programmatic guardrail — do not attempt to split a "
            "refund to stay under the ceiling. An order that is not eligible "
            "(e.g. already refunded) returns a business error explaining why; that "
            "is NOT retryable, so relay the explanation to the customer.\n\n"
            "Use this only after get_customer has verified the customer AND you "
            "have confirmed the order details with lookup_order."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order to refund (ORD-<digits>)."},
                "amount": {"type": "number", "description": "Refund amount in dollars."},
                "reason": {"type": "string", "description": "Why the refund is being issued."},
            },
            "required": ["order_id", "amount"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": (
            "Hand the case to a human support agent with a structured summary. "
            "Returns an escalation ticket id.\n\n"
            "Input: {\"customer_id\": \"…\", \"root_cause\": \"…\", "
            "\"refund_amount\": <number|null>, \"recommended_action\": \"…\"}. The "
            "human who picks this up cannot see the chat transcript, so include "
            "every fact they need to act.\n\n"
            "Use this when the customer explicitly asks for a human, when policy is "
            "silent/ambiguous on their request, when you cannot make meaningful "
            "progress, or when a guardrail has blocked the action you needed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "root_cause": {"type": "string"},
                "refund_amount": {"type": ["number", "null"]},
                "recommended_action": {"type": "string"},
                "reason": {"type": "string"},
            },
        },
    },
]


# --------------------------------------------------------------------------- #
# Structured errors (Task Statement 2.2)
# --------------------------------------------------------------------------- #
def make_error(category: str, message: str, *, retryable: bool | None = None) -> dict[str, Any]:
    """Build an MCP-style structured error object.

    Returns ``{"isError": True, "errorCategory": category, "isRetryable": bool,
    "message": message}``. ``isRetryable`` defaults to the category default
    (only ``transient`` is retryable) but can be overridden. Raises
    ``ValueError`` for an unknown category or an empty message.
    """
    if category not in _RETRYABLE:
        raise ValueError(f"unknown errorCategory {category!r}; expected {CATEGORIES}")
    if not message or not message.strip():
        raise ValueError("error message must be a non-empty human-readable string")
    resolved = _RETRYABLE[category] if retryable is None else bool(retryable)
    return {
        "isError": True,
        "errorCategory": category,
        "isRetryable": resolved,
        "message": message,
    }


# --------------------------------------------------------------------------- #
# Default in-memory backends (used by scenarios.json / demos)
# --------------------------------------------------------------------------- #
def default_backends() -> dict[str, Any]:
    """Return a fresh set of sample backends for demos and scenario runs."""
    return {
        "customers": [
            {
                "customer_id": "CUST-40912",
                "name": "Jane Rivera",
                "email": "jane.rivera@example.com",
                "account_standing": "good",
            },
            # Two "Sam Taylor" accounts on purpose: a name lookup is ambiguous.
            {
                "customer_id": "CUST-10001",
                "name": "Sam Taylor",
                "email": "sam.taylor@example.com",
                "account_standing": "good",
            },
            {
                "customer_id": "CUST-10002",
                "name": "Sam Taylor",
                "email": "s.taylor@example.com",
                "account_standing": "good",
            },
        ],
        "orders": {
            "ORD-88213": {
                "order_id": "ORD-88213",
                "customer_id": "CUST-40912",
                "status": "shipped",
                "order_total": "$129.99",
                "tracking_number": "1Z999AA10123456784",
                "delivery_estimate": "2026-07-05",
                "refund_eligible": True,
                "_internal_warehouse_notes": "aisle 7 bin 42",  # trimmed away downstream
            },
            "ORD-55100": {
                "order_id": "ORD-55100",
                "customer_id": "CUST-40912",
                "status": "delivered",
                "order_total": "$412.00",
                "refund_eligible": True,
            },
            "ORD-99999": {
                "order_id": "ORD-99999",
                "customer_id": "CUST-40912",
                "status": "refunded",
                "order_total": "$60.00",
                "refund_eligible": False,
                "refund_block_reason": "already refunded on 2026-06-20",
            },
        },
        "refunds": [],
    }


# --------------------------------------------------------------------------- #
# Tool dispatch
# --------------------------------------------------------------------------- #
_ORDER_KEEP = (
    "order_id",
    "customer_id",
    "status",
    "order_total",
    "tracking_number",
    "delivery_estimate",
    "refund_eligible",
)


def _orders_get(backends: dict[str, Any], order_id: str) -> dict[str, Any] | None:
    orders = backends.get("orders", {})
    if isinstance(orders, dict):
        return orders.get(order_id)
    for order in orders:  # list form
        if order.get("order_id") == order_id:
            return order
    return None


def _match_customers(customers: list[dict], tool_input: dict) -> list[dict]:
    cid = tool_input.get("customer_id")
    email = tool_input.get("email")
    name = tool_input.get("name")
    if cid:
        return [c for c in customers if c.get("customer_id") == cid]
    if email:
        return [c for c in customers if c.get("email", "").lower() == email.lower()]
    if name:
        return [c for c in customers if c.get("name", "").lower() == name.lower()]
    return []


def _get_customer(tool_input: dict, backends: dict) -> dict[str, Any]:
    if not (tool_input.get("customer_id") or tool_input.get("email") or tool_input.get("name")):
        return make_error("validation", "Provide a customer_id, email, or name to look up a customer.")
    matches = _match_customers(backends.get("customers", []), tool_input)
    if not matches:
        return {"match_count": 0, "matches": [], "verified": False,
                "message": "No account matched those details."}
    if len(matches) > 1:
        return {
            "match_count": len(matches),
            "matches": [{"customer_id": c["customer_id"], "email": c.get("email")} for c in matches],
            "verified": False,
            "message": "Multiple accounts matched; ask the customer for their customer_id to disambiguate.",
        }
    c = matches[0]
    return {
        "match_count": 1,
        "verified": True,
        "customer_id": c["customer_id"],
        "name": c.get("name"),
        "email": c.get("email"),
        "account_standing": c.get("account_standing", "good"),
    }


def _lookup_order(tool_input: dict, backends: dict) -> dict[str, Any]:
    order_id = tool_input.get("order_id")
    if not order_id:
        return make_error("validation", "lookup_order requires an 'order_id' like 'ORD-88213'.")
    order = _orders_get(backends, order_id)
    if order is None:
        # Valid empty result — NOT an error (Task Statement 5.3).
        return {"found": False, "order_id": order_id, "message": "No order matched that number."}
    trimmed = {k: order[k] for k in _ORDER_KEEP if k in order}
    return {"found": True, **trimmed}


def _process_refund(tool_input: dict, backends: dict) -> dict[str, Any]:
    amount = tool_input.get("amount", tool_input.get("refund_amount"))
    if amount is None:
        return make_error("validation", "process_refund requires an 'amount' in dollars.")
    order_id = tool_input.get("order_id")
    order = _orders_get(backends, order_id) if order_id else None
    if order is not None and order.get("refund_eligible") is False:
        reason = order.get("refund_block_reason", "the order is not eligible for a refund")
        return make_error("business", f"Refund declined for {order_id}: {reason}.")
    refunds = backends.setdefault("refunds", []) if isinstance(backends, dict) else []
    refund_id = f"REF-{order_id or 'NA'}-{len(refunds) + 1}"
    refunds.append({"refund_id": refund_id, "order_id": order_id, "amount": amount})
    return {"status": "refunded", "amount": amount, "order_id": order_id, "refund_id": refund_id}


def _escalate_to_human(tool_input: dict, backends: dict) -> dict[str, Any]:
    tickets = backends.setdefault("tickets", []) if isinstance(backends, dict) else []
    ticket_id = f"TICKET-{len(tickets) + 1}"
    tickets.append(ticket_id)
    return {"status": "escalated", "ticket_id": ticket_id, **tool_input}


_DISPATCH: dict[str, Callable[[dict, dict], dict]] = {
    "get_customer": _get_customer,
    "lookup_order": _lookup_order,
    "process_refund": _process_refund,
    "escalate_to_human": _escalate_to_human,
}


def execute_tool(name: str, tool_input: dict[str, Any], backends: dict[str, Any]) -> dict[str, Any]:
    """Execute one tool call and return its result (success or structured error).

    A per-tool callable in ``backends`` (e.g. ``backends["lookup_order"]``)
    overrides the default data-driven implementation — tests use this to inject a
    transient failure followed by a success. An exception raised by any backend
    is caught and reported as a *transient* error so the agent can retry it.
    """
    override = backends.get(name) if isinstance(backends, dict) else None
    try:
        if callable(override):
            return override(tool_input)
        impl = _DISPATCH.get(name)
        if impl is None:
            return make_error("validation", f"Unknown tool {name!r}.")
        return impl(tool_input, backends)
    except Exception as exc:  # a backend blew up — surface it as retryable
        return make_error("transient", f"{name} backend error: {exc}")
