"""Deterministic evidence reconciliation for Korean business workflows."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Any

from talkcheck.business_number import (
    format_business_number,
    is_valid_business_number,
    normalize_business_number,
)


_SUPPORTED_INTENTS = {"verify_only", "prepare_invoice"}
_UNAVAILABLE_STATUSES = {"not_configured", "temporarily_unavailable"}


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def _canonical_text(value: str | None) -> str | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    normalized = unicodedata.normalize("NFKC", cleaned).casefold()
    return re.sub(r"[^0-9a-z가-힣]", "", normalized)


def _same_text(left: str | None, right: str | None) -> bool:
    left_value = _canonical_text(left)
    right_value = _canonical_text(right)
    return bool(left_value and right_value and left_value == right_value)


def _field(
    key: str,
    label: str,
    status: str,
    message: str,
    *,
    claimed: str | None = None,
    extracted: str | None = None,
    official: str | None = None,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "field": key,
        "label": label,
        "status": status,
        "claimed": _clean(claimed),
        "extracted": _clean(extracted),
        "official": _clean(official),
        "sources": sources or [],
        "message": message,
    }


def _identity_field(
    key: str,
    label: str,
    claimed: str | None,
    extracted: str | None,
    certificate_bundle_verified: bool,
) -> dict[str, Any]:
    claimed = _clean(claimed)
    extracted = _clean(extracted)
    sources = []
    if claimed:
        sources.append("user_input")
    if extracted:
        sources.append("certificate_extraction")

    if claimed and extracted and not _same_text(claimed, extracted):
        return _field(
            key,
            label,
            "conflict",
            f"{label}의 사용자 입력값과 증명서 추출값이 다릅니다.",
            claimed=claimed,
            extracted=extracted,
            sources=sources,
        )
    if extracted and certificate_bundle_verified:
        return _field(
            key,
            label,
            "verified",
            "국세청 증명서 진위확인에 제출된 정보 묶음 안에서 확인되었습니다.",
            claimed=claimed,
            extracted=extracted,
            official=extracted,
            sources=[*sources, "nts_certificate_validation"],
        )
    if claimed and extracted:
        return _field(
            key,
            label,
            "consistent",
            "입력값과 증명서 추출값이 일치하지만 공식 진위확인은 완료되지 않았습니다.",
            claimed=claimed,
            extracted=extracted,
            sources=sources,
        )
    if extracted:
        return _field(
            key,
            label,
            "extracted",
            "증명서에서 추출했으며 사용자의 확인이 필요합니다.",
            extracted=extracted,
            sources=sources,
        )
    if claimed:
        return _field(
            key,
            label,
            "needs_confirmation",
            "사용자가 입력한 값이며 국세청 상태조회로는 이 항목을 확인할 수 없습니다.",
            claimed=claimed,
            sources=sources,
        )
    return _field(key, label, "missing", f"{label} 정보가 제공되지 않았습니다.")


def _certificate_state(certificate_verification: dict[str, Any] | None) -> tuple[bool, bool]:
    verification_status = str((certificate_verification or {}).get("verification_status") or "")
    if verification_status == "01":
        return True, False
    unavailable = verification_status in _UNAVAILABLE_STATUSES
    not_requested = verification_status in {"", "not_requested"}
    return False, not unavailable and not not_requested


def build_evidence_report(
    *,
    business_number: str,
    official_lookup: dict[str, Any] | None,
    certificate_verification: dict[str, Any] | None = None,
    claimed_business_name: str | None = None,
    claimed_representative_name: str | None = None,
    certificate_business_number: str | None = None,
    certificate_business_name: str | None = None,
    certificate_representative_name: str | None = None,
    certificate_opening_date: str | None = None,
    intent: str = "verify_only",
) -> dict[str, Any]:
    """Build a factual report without risk scoring or a business recommendation."""
    if intent not in _SUPPORTED_INTENTS:
        raise ValueError("intent는 'verify_only' 또는 'prepare_invoice'여야 합니다.")

    normalized_number = normalize_business_number(business_number)
    extracted_number = (
        normalize_business_number(certificate_business_number)
        if certificate_business_number
        else None
    )
    checksum_valid = is_valid_business_number(normalized_number)
    lookup = official_lookup if isinstance(official_lookup, dict) else {}
    lookup_available = bool(lookup.get("business_status"))
    bundle_verified, bundle_conflict = _certificate_state(certificate_verification)
    results: list[dict[str, Any]] = []

    number_sources = ["workflow_input"]
    if extracted_number:
        number_sources.append("certificate_extraction")
    if lookup_available:
        number_sources.append("nts_status_lookup")

    if not checksum_valid:
        number_result = _field(
            "business_number",
            "사업자등록번호",
            "invalid",
            "입력한 번호의 형식 또는 검증번호가 올바르지 않습니다.",
            claimed=normalized_number,
            extracted=extracted_number,
            sources=number_sources,
        )
    elif extracted_number and normalized_number != extracted_number:
        number_result = _field(
            "business_number",
            "사업자등록번호",
            "conflict",
            "입력한 번호와 증명서에서 추출한 번호가 다릅니다.",
            claimed=format_business_number(normalized_number),
            extracted=format_business_number(extracted_number),
            sources=number_sources,
        )
    elif lookup_available:
        number_result = _field(
            "business_number",
            "사업자등록번호",
            "verified",
            "국세청 상태조회에서 이 번호의 현재 상태가 반환되었습니다.",
            claimed=format_business_number(normalized_number),
            extracted=format_business_number(extracted_number) if extracted_number else None,
            official=format_business_number(normalized_number),
            sources=number_sources,
        )
    else:
        number_result = _field(
            "business_number",
            "사업자등록번호",
            "unavailable",
            "번호 자체 검증은 통과했지만 국세청 상태조회가 완료되지 않았습니다.",
            claimed=format_business_number(normalized_number),
            extracted=format_business_number(extracted_number) if extracted_number else None,
            sources=number_sources,
        )
    results.append(number_result)

    results.append(
        _identity_field(
            "business_name",
            "상호",
            claimed_business_name,
            certificate_business_name,
            bundle_verified,
        )
    )
    results.append(
        _identity_field(
            "representative_name",
            "대표자명",
            claimed_representative_name,
            certificate_representative_name,
            bundle_verified,
        )
    )

    opening_date = _clean(certificate_opening_date)
    if opening_date and bundle_verified:
        results.append(
            _field(
                "opening_date",
                "개업일자",
                "verified",
                "국세청 증명서 진위확인에 제출된 정보 묶음 안에서 확인되었습니다.",
                extracted=opening_date,
                official=opening_date,
                sources=["certificate_extraction", "nts_certificate_validation"],
            )
        )
    elif opening_date:
        results.append(
            _field(
                "opening_date",
                "개업일자",
                "extracted",
                "증명서에서 추출했지만 공식 진위확인은 완료되지 않았습니다.",
                extracted=opening_date,
                sources=["certificate_extraction"],
            )
        )
    else:
        results.append(_field("opening_date", "개업일자", "missing", "개업일자가 제공되지 않았습니다."))

    for key, label, value in (
        ("business_status", "사업자 상태", lookup.get("business_status")),
        ("tax_type", "과세 유형", lookup.get("tax_type")),
    ):
        if lookup_available and value:
            results.append(
                _field(
                    key,
                    label,
                    "verified",
                    "국세청 사업자등록 상태조회에서 반환된 공식 정보입니다.",
                    official=str(value),
                    sources=["nts_status_lookup"],
                )
            )
        else:
            results.append(
                _field(
                    key,
                    label,
                    "unavailable",
                    "국세청 상태조회에서 이 항목을 확인하지 못했습니다.",
                    sources=["nts_status_lookup"],
                )
            )

    certificate_supplied = any(
        (
            certificate_business_number,
            certificate_business_name,
            certificate_representative_name,
            certificate_opening_date,
        )
    )
    if certificate_supplied:
        verification_status = str((certificate_verification or {}).get("verification_status") or "")
        if bundle_verified:
            results.append(
                _field(
                    "certificate_bundle",
                    "증명서 정보 묶음",
                    "verified",
                    "증명서 정보 묶음이 국세청 진위확인을 통과했습니다.",
                    official="확인",
                    sources=["nts_certificate_validation"],
                )
            )
        elif bundle_conflict:
            results.append(
                _field(
                    "certificate_bundle",
                    "증명서 정보 묶음",
                    "conflict",
                    "국세청 진위확인에서 증명서 정보 묶음이 일치하지 않았습니다. 어떤 필드가 다른지는 응답만으로 특정할 수 없습니다.",
                    sources=["nts_certificate_validation"],
                )
            )
        elif verification_status in _UNAVAILABLE_STATUSES:
            results.append(
                _field(
                    "certificate_bundle",
                    "증명서 정보 묶음",
                    "unavailable",
                    "국세청 증명서 진위확인을 완료하지 못했습니다.",
                    sources=["nts_certificate_validation"],
                )
            )

    conflicts = [item for item in results if item["status"] == "conflict"]
    missing_fields: list[str] = []
    if intent == "prepare_invoice" and not _clean(claimed_business_name):
        missing_fields.append("claimed_business_name")

    validation_incomplete = bool(
        certificate_business_number
        and not bundle_verified
        and not bundle_conflict
        and not (
            (certificate_verification or {}).get("verification_status") in _UNAVAILABLE_STATUSES
        )
        and (not certificate_opening_date or not certificate_representative_name)
    )
    if validation_incomplete:
        if not certificate_opening_date:
            missing_fields.append("certificate_opening_date")
        if not certificate_representative_name:
            missing_fields.append("certificate_representative_name")

    questions: list[str] = []
    for item in conflicts:
        if item["field"] == "business_number":
            questions.append("입력한 사업자등록번호와 증명서의 번호 중 어느 것이 맞는지 원본을 확인해 주세요.")
        elif item["field"] in {"business_name", "representative_name"}:
            questions.append(
                f"사용자 입력({item['label']}: {item['claimed']})과 "
                f"증명서 추출({item['label']}: {item['extracted']}) 중 어느 값이 맞나요?"
            )
        elif item["field"] == "certificate_bundle":
            questions.append("증명서 원본의 사업자등록번호·개업일자·대표자명·상호를 다시 확인해 주세요.")
    if "claimed_business_name" in missing_fields:
        questions.append("세금계산서 초안에 사용할 공급받는자 상호는 무엇인가요?")
    if "certificate_opening_date" in missing_fields:
        questions.append("증명서에 적힌 개업일자 8자리를 확인해 주세요.")
    if "certificate_representative_name" in missing_fields:
        questions.append("증명서에 적힌 대표자명을 확인해 주세요.")

    official_status = str(lookup.get("business_status") or "")
    official_status_code = str(lookup.get("business_status_code") or "")
    active_business = official_status_code == "01" or "계속사업자" in official_status

    if not checksum_valid:
        workflow_status = "invalid_business_number"
        next_action = "correct_business_number"
        questions.append("사업자등록번호 10자리를 원본에서 다시 확인해 주세요.")
    elif conflicts:
        workflow_status = "needs_clarification"
        next_action = "resolve_conflicts"
    elif not lookup_available:
        workflow_status = "official_lookup_unavailable"
        next_action = "retry_official_lookup"
        questions.append("국세청 공식 조회를 다시 시도할까요?")
    elif not active_business:
        workflow_status = "official_status_requires_review"
        next_action = "review_official_status"
        questions.append(f"국세청의 현재 사업자 상태가 '{official_status}'입니다. 이 상태를 확인했나요?")
    elif missing_fields:
        workflow_status = "needs_clarification"
        next_action = "collect_missing_fields"
    elif intent == "prepare_invoice":
        workflow_status = "ready_for_draft"
        next_action = "prepare_invoice_draft"
    else:
        workflow_status = "verification_complete"
        next_action = "present_verified_facts"

    counts = Counter(item["status"] for item in results)
    return {
        "workflow_status": workflow_status,
        "intent": intent,
        "business_number": normalized_number,
        "formatted_business_number": format_business_number(normalized_number),
        "official_lookup": official_lookup,
        "certificate_verification": certificate_verification,
        "field_results": results,
        "conflicts": conflicts,
        "missing_fields": missing_fields,
        "clarifying_questions": list(dict.fromkeys(questions)),
        "summary": {
            "officially_verified": counts["verified"],
            "cross_source_consistent": counts["consistent"],
            "conflicts": counts["conflict"],
            "needs_confirmation": counts["needs_confirmation"] + counts["extracted"],
            "missing": counts["missing"],
            "official_lookup_available": lookup_available,
            "certificate_bundle_verified": bundle_verified,
        },
        "next_action": next_action,
        "can_prepare_invoice_draft": workflow_status == "ready_for_draft",
        "guardrails": {
            "risk_score_provided": False,
            "business_recommendation_provided": False,
            "invoice_issued": False,
            "user_confirmation_required_before_issuance": True,
        },
        "data_handling": {
            "reasoning_runtime": "Codex or ChatGPT host; no OpenAI API key required by TalkCheck",
            "official_source": "National Tax Service business status and certificate validation",
            "downloaded_image_storage": "TalkCheck processes downloaded images in memory and does not persist them",
            "host_data_handling_note": "The host's separate upload and retention policies may still apply",
            "handoff_ttl_minutes": 30,
        },
    }
