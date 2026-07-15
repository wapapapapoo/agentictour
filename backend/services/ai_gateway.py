from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from utils.dify_client import DifyClient, DifyConfigError, DifyResponseError

AUDIT_REQUEST_KEYS = (
    "trigger_type",
    "tour_id",
    "city_adcode",
    "latitude",
    "longitude",
    "location_name",
    "conversation_history",
)
AUDIT_EVIDENCE_OUTPUTS = {
    "itinerary": "itinerary_context",
    "memos": "memo_context",
    "weather": "weather_context",
    "current_time": "current_time",
    "nearby": "nearby_context",
    "route": "route_context",
    "tool_errors": "tool_errors",
    "decision": "decision",
}


@dataclass
class AuditedOutput:
    content: str
    passed: bool
    reason: str | None
    main_response: dict[str, Any]
    audit_response: dict[str, Any]
    audit_count: int
    structured_output: Any = None


class AuditRejectedError(ValueError):
    """Raised when the audit agent rejects generated content."""

    def __init__(self, reason: str | None = None) -> None:
        super().__init__(reason or "AI 回复未通过审核，请调整要求后重试。")


def _output(response: dict[str, Any], *keys: str) -> Any:
    outputs = response.get("data", {}).get("outputs", {})
    if not isinstance(outputs, dict):
        raise DifyResponseError("Dify workflow outputs must be an object")
    for key in keys:
        if key in outputs and outputs[key] is not None:
            return outputs[key]
    return None


def _structured_itinerary(response: dict[str, Any]) -> Any:
    items = _output(response, "itinerary_items", "proposed_itinerary", "plan_json")
    cancelled_ids = _output(response, "cancelled_itinerary_ids")
    if cancelled_ids is None:
        return items
    return {
        "cancelled_itinerary_ids": cancelled_ids,
        "itinerary_items": items or [],
    }


def _audit_context(
    inputs: dict[str, Any], response: dict[str, Any], structured: Any
) -> str:
    request = {
        key: inputs[key]
        for key in AUDIT_REQUEST_KEYS
        if key in inputs and inputs[key] not in (None, "")
    }
    evidence: dict[str, Any] = {}
    for context_key, output_key in AUDIT_EVIDENCE_OUTPUTS.items():
        value = _output(response, output_key)
        if value not in (None, "", [], {}):
            evidence[context_key] = value
    if structured is not None:
        evidence["structured_itinerary"] = structured
    return json.dumps(
        {"request": request, "evidence": evidence}, ensure_ascii=False, default=str
    )


def _audit_inputs(
    *,
    original_input: str,
    review_content: str,
    turn: str,
    inputs: dict[str, Any],
    response: dict[str, Any],
    structured: Any,
) -> dict[str, str]:
    return {
        "input": original_input,
        "ai_readout": review_content,
        "turn": turn,
        "audit_context": _audit_context(inputs, response, structured),
    }


def _main_client() -> DifyClient:
    url = os.getenv("HIKARI_DIFY_URL") or os.getenv("DIFY_URL")
    if not url:
        raise DifyConfigError("HIKARI_DIFY_URL is required for the Hikari workflow")
    return DifyClient(
        api_key=os.getenv("Hikari_key"),
        url=url,
        timeout=float(os.getenv("DIFY_TIMEOUT", "600")),
    )


def _audit_client() -> DifyClient:
    url = os.getenv("CHECK_DIFY_URL") or os.getenv("DIFY_URL")
    if not url:
        raise DifyConfigError("CHECK_DIFY_URL is required for the audit workflow")
    return DifyClient(
        api_key=os.getenv("check_key"),
        url=url,
        timeout=float(os.getenv("DIFY_TIMEOUT", "600")),
    )


def run_hikari_audited(
    *, user: str, inputs: dict[str, Any], original_input: str
) -> AuditedOutput:
    """Run Hikari, correcting once after a failed first audit; audit at most twice."""
    main_response = _main_client().run_workflow(user=user, inputs=inputs)
    raw = _output(main_response, "reply", "answer", "result")
    if raw is None:
        raise DifyResponseError("Hikari workflow did not return reply/answer/result")
    main_content = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
    structured = _structured_itinerary(main_response)
    review_content = main_content
    if structured is not None:
        review_content += "\n结构化行程：" + (
            structured
            if isinstance(structured, str)
            else json.dumps(structured, ensure_ascii=False)
        )

    audit_response = _audit_client().run_workflow(
        user=user,
        inputs=_audit_inputs(
            original_input=original_input,
            review_content=review_content,
            turn="first",
            inputs=inputs,
            response=main_response,
            structured=structured,
        ),
    )
    result = _output(audit_response, "result")
    passed = result is True or (isinstance(result, str) and result.lower() == "true")
    audit_reply = _output(audit_response, "reply")
    if passed:
        return AuditedOutput(
            content=main_content,
            passed=True,
            reason=None,
            main_response=main_response,
            audit_response=audit_response,
            audit_count=1,
            structured_output=structured,
        )

    first_reason = str(audit_reply or "审核未通过")
    correction_inputs = dict(inputs)
    correction_inputs["user_query"] = (
        f"原始输入：{original_input}\n第一次回答审核失败原因：{first_reason}\n"
        "请重新生成符合要求的最终回答。"
    )
    corrected_response = _main_client().run_workflow(
        user=user, inputs=correction_inputs
    )
    corrected_raw = _output(corrected_response, "reply", "answer", "result")
    if corrected_raw is None:
        raise DifyResponseError("corrected Hikari response has no output")
    corrected_content = (
        corrected_raw
        if isinstance(corrected_raw, str)
        else json.dumps(corrected_raw, ensure_ascii=False)
    )
    corrected_structured = _structured_itinerary(corrected_response)
    corrected_review_content = corrected_content
    if corrected_structured is not None:
        corrected_review_content += "\n结构化行程：" + (
            corrected_structured
            if isinstance(corrected_structured, str)
            else json.dumps(corrected_structured, ensure_ascii=False)
        )
    second_audit = _audit_client().run_workflow(
        user=user,
        inputs=_audit_inputs(
            original_input=original_input,
            review_content=corrected_review_content,
            turn="second",
            inputs=correction_inputs,
            response=corrected_response,
            structured=corrected_structured,
        ),
    )
    second_result = _output(second_audit, "result")
    second_passed = second_result is True or (
        isinstance(second_result, str) and second_result.lower() == "true"
    )
    second_reply = _output(second_audit, "reply")
    final_reason = None if second_passed else str(second_reply or "二次审核未通过")
    return AuditedOutput(
        content=corrected_content
        if second_passed
        else (final_reason or "二次审核未通过"),
        passed=second_passed,
        reason=final_reason,
        main_response=corrected_response,
        audit_response=second_audit,
        audit_count=2,
        structured_output=corrected_structured,
    )


# Backward-compatible import name for existing service code.
run_hikari_once_audited = run_hikari_audited
