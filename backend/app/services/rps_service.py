"""
Mock RPS (Real-time Processing System) — simulates the core banking system.

In production this would be an authenticated API call to the bank's core system.
For the prototype, customer records are held in-memory and writes are logged only.

HITL constraint enforced here: write_customer_record() requires a valid
checker_decision_id. This is the only write path and it has no direct call
from the agent pipeline.
"""
import uuid
from datetime import datetime
from loguru import logger

# ── Seed Data ──────────────────────────────────────────────────────────────────
# Pre-seeded customer records (mock RPS store)
_CUSTOMER_RECORDS: dict[str, dict] = {
    "C001": {
        "customer_id": "C001",
        "name": "Priya Sharma",
        "date_of_birth": "1990-03-15",
        "address": "42 Marine Drive, Mumbai, MH 400002",
        "contact_email": "priya.sharma@email.com",
        "contact_phone": "+91-9876543210",
        "account_numbers": ["ACC-001-2345", "ACC-001-6789"],
        "kyc_status": "VERIFIED",
        "created_at": "2018-06-01",
    },
    "C002": {
        "customer_id": "C002",
        "name": "Rahul Verma",
        "date_of_birth": "1985-11-22",
        "address": "15 Park Street, Kolkata, WB 700016",
        "contact_email": "rahul.verma@email.com",
        "contact_phone": "+91-9123456789",
        "account_numbers": ["ACC-002-1111"],
        "kyc_status": "VERIFIED",
        "created_at": "2020-01-10",
    },
}

# Audit log of all write operations (would be DB or event stream in production)
_WRITE_LOG: list[dict] = []


def get_customer(customer_id: str) -> dict | None:
    """Look up a customer record from mock RPS. Returns None if not found."""
    record = _CUSTOMER_RECORDS.get(customer_id)
    logger.debug("RPS lookup | customer_id={} | found={}", customer_id, record is not None)
    return record


def write_customer_record(
    customer_id: str,
    change_type: str,
    new_value: dict,
    checker_decision_id: str,
) -> dict:
    """
    Commit an approved change to the mock RPS.

    IMPORTANT: This function must only be called from the checker approval flow,
    never from the agent pipeline. The checker_decision_id links every write to
    a recorded human decision for full auditability.
    """
    if customer_id not in _CUSTOMER_RECORDS:
        raise ValueError(f"Customer {customer_id} not found in RPS")

    record = _CUSTOMER_RECORDS[customer_id]
    field_map = {
        "LEGAL_NAME": "name",
        "ADDRESS": "address",
        "DOB": "date_of_birth",
        "CONTACT": "contact_email",
    }
    field = field_map.get(change_type)
    if not field:
        raise ValueError(f"Unsupported change type: {change_type}")

    old_value = record.get(field)
    new_field_value = new_value.get(list(new_value.keys())[0])
    record[field] = new_field_value

    write_event = {
        "write_id": str(uuid.uuid4()),
        "customer_id": customer_id,
        "change_type": change_type,
        "field_updated": field,
        "old_value": old_value,
        "new_value": new_field_value,
        "checker_decision_id": checker_decision_id,
        "written_at": datetime.utcnow().isoformat(),
        "status": "SUCCESS",
    }
    _WRITE_LOG.append(write_event)

    logger.info(
        "RPS write | customer={} | field={} | old={} | new={} | decision={}",
        customer_id, field, old_value, new_field_value, checker_decision_id,
    )
    return write_event
