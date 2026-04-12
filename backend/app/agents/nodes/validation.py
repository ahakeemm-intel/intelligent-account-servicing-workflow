"""
Validation Agent Node

Validates intake fields against the mock RPS before any document processing.
Checks:
  - Customer exists in RPS
  - Old value matches the current RPS record
  - Change type is supported
"""
from loguru import logger
from app.agents.state import RequestState
from app.services import rps_service


def validation_agent(state: RequestState) -> RequestState:
    logger.info("validation_agent | request={} | customer={}", state["request_id"], state["customer_id"])

    errors: list[str] = []
    rps_record = rps_service.get_customer(state["customer_id"])

    if rps_record is None:
        errors.append(f"Customer '{state['customer_id']}' not found in RPS")
        return {**state, "rps_record": None, "validation_errors": errors, "pipeline_errors": errors}

    # Validate old value matches current RPS record for LEGAL_NAME
    if state["change_type"] == "LEGAL_NAME":
        old_name = state["old_value"].get("name", "").strip().lower()
        rps_name = rps_record.get("name", "").strip().lower()
        if old_name != rps_name:
            errors.append(
                f"Old name '{state['old_value'].get('name')}' does not match RPS record '{rps_record.get('name')}'"
            )

    supported_types = {"LEGAL_NAME", "ADDRESS", "DOB", "CONTACT"}
    if state["change_type"] not in supported_types:
        errors.append(f"Unsupported change type: {state['change_type']}")

    if errors:
        logger.warning("validation_agent | FAILED | errors={}", errors)
    else:
        logger.info("validation_agent | PASSED | customer={}", state["customer_id"])

    return {
        **state,
        "rps_record": rps_record,
        "validation_errors": errors,
        "pipeline_errors": state.get("pipeline_errors", []) + errors,
    }
