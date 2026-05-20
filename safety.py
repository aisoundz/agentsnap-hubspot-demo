"""Safety layer: spend caps + audit log.

Two enforcement points:
  - Per-transaction limit: any single write over the limit returns an
    awaiting_confirmation response with a confirmation_id. The agent
    (or user) must call confirm_action(confirmation_id) to execute it.
  - Daily limit: running total of confirmed writes per day. If a write
    would push the day over the limit, it's blocked outright.

Audit logging is append-only JSONL. Every state-changing action — invoice
creation, claim opening, refund, confirmation — appends one line.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

import config

# In-memory state. In production this would be Postgres (see Phase 3 ADR).
_pending_confirmations: dict[str, dict[str, Any]] = {}
_daily_spend: dict[str, float] = {}  # keyed by ISO date

AUDIT_LOG_PATH = Path(__file__).parent / "audit_log.jsonl"


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


def audit(action: str, **fields: Any) -> None:
    """Append an audit event to the JSONL log."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "agency_id": config.AGENCY_ID,
        **fields,
    }
    try:
        with AUDIT_LOG_PATH.open("a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        # Audit log is best-effort. If the disk is unwritable, don't fail the
        # action — log it to stderr instead. In production this would be a
        # database write.
        import sys

        print(f"[audit-fallback] {json.dumps(record)}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Spend cap enforcement
# ---------------------------------------------------------------------------


def check_spend_cap(amount: float) -> dict[str, Any] | None:
    """Check whether an amount is allowed under the spend caps.

    Returns None if the action can proceed. Returns a response dict if the
    action needs confirmation or should be blocked.
    """
    today = date.today().isoformat()
    spent_today = _daily_spend.get(today, 0.0)

    if spent_today + amount > config.DAILY_LIMIT:
        audit(
            "spend_cap_daily_blocked",
            amount=amount,
            spent_today=spent_today,
            daily_limit=config.DAILY_LIMIT,
        )
        return {
            "status": "blocked",
            "reason": "daily_limit_exceeded",
            "message": (
                f"This action would push today's total spend over the daily limit of "
                f"${config.DAILY_LIMIT:,.2f}. Already authorized today: ${spent_today:,.2f}. "
                f"Action amount: ${amount:,.2f}. The action was not performed."
            ),
            "spent_today": spent_today,
            "daily_limit": config.DAILY_LIMIT,
        }

    if amount > config.PER_TRANSACTION_LIMIT:
        # Action needs explicit confirmation
        confirmation_id = f"conf_{uuid.uuid4().hex[:12]}"
        return {
            "status": "awaiting_confirmation",
            "confirmation_id": confirmation_id,
            "amount": amount,
            "per_transaction_limit": config.PER_TRANSACTION_LIMIT,
            "message": (
                f"This action is for ${amount:,.2f}, which is above the per-transaction "
                f"safety limit of ${config.PER_TRANSACTION_LIMIT:,.2f}. "
                f"Show the user this amount and ask for confirmation before proceeding. "
                f"If they confirm, call confirm_action with confirmation_id='{confirmation_id}'."
            ),
        }

    return None  # under limits — proceed


def hold_for_confirmation(
    confirmation_id: str,
    action_callable: Callable[[], Any],
    amount: float,
    description: str,
) -> None:
    """Store a pending action that will be executed when the user confirms."""
    _pending_confirmations[confirmation_id] = {
        "callable": action_callable,
        "amount": amount,
        "description": description,
        "created_at": time.time(),
    }
    audit(
        "confirmation_held",
        confirmation_id=confirmation_id,
        amount=amount,
        description=description,
    )


def execute_confirmation(confirmation_id: str) -> dict[str, Any]:
    """Execute a held action by confirmation_id. Increment daily spend."""
    pending = _pending_confirmations.pop(confirmation_id, None)
    if pending is None:
        return {
            "status": "error",
            "message": (
                f"No pending action found for confirmation_id='{confirmation_id}'. "
                "It may have already been confirmed, or it may have expired."
            ),
        }

    # Hard timeout: 10 minutes
    if time.time() - pending["created_at"] > 600:
        return {
            "status": "error",
            "message": (
                f"Confirmation {confirmation_id} expired (older than 10 minutes). "
                "Re-create the action to receive a new confirmation_id."
            ),
        }

    result = pending["callable"]()

    today = date.today().isoformat()
    _daily_spend[today] = _daily_spend.get(today, 0.0) + pending["amount"]

    audit(
        "confirmation_executed",
        confirmation_id=confirmation_id,
        amount=pending["amount"],
        description=pending["description"],
        new_daily_total=_daily_spend[today],
    )

    return {"status": "confirmed", "result": result}


def record_uncapped_spend(amount: float) -> None:
    """Record spend for an action that didn't require confirmation. Keeps the
    daily counter accurate even for small amounts."""
    today = date.today().isoformat()
    _daily_spend[today] = _daily_spend.get(today, 0.0) + amount


def get_daily_spend() -> dict[str, Any]:
    today = date.today().isoformat()
    return {
        "date": today,
        "spent": _daily_spend.get(today, 0.0),
        "limit": config.DAILY_LIMIT,
        "remaining": config.DAILY_LIMIT - _daily_spend.get(today, 0.0),
    }
