"""Application services with no scoring, recommendation, or automatic issuance."""

from __future__ import annotations

import asyncio
import re
from datetime import date, datetime, timezone
from typing import Any, Literal

from talkcheck.business_number import (
    find_business_number,
    format_business_number,
    is_valid_business_number,
    normalize_business_number,
)
from talkcheck.domain import BusinessCertificate, TaxInvoiceDraft
from talkcheck.evidence import build_evidence_report
from talkcheck.providers import (
    BusinessRegistryProvider,
    InvoiceHandoffProvider,
    OcrProcessingError,
    OcrProvider,
    ProviderNotConfigured,
    ProviderUnavailable,
)


def _checked_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_labeled_value(text: str, labels: tuple[str, ...]) -> str | None:
    for line in text.splitlines():
        normalized = re.sub(r"\s+", " ", line).strip()
        for label in labels:
            if normalized.startswith(label):
                value = normalized[len(label) :].lstrip(" :：")
                return value or None
    return None


def parse_certificate_text(text: str) -> BusinessCertificate | None:
    business_number = find_business_number(text)
    if not business_number:
        return None

    opening_date_raw = _extract_labeled_value(text, ("개업연월일", "개업일자"))
    opening_date = None
    if opening_date_raw:
        digits = "".join(character for character in opening_date_raw if character.isdigit())
        if len(digits) >= 8:
            opening_date = digits[:8]

    return BusinessCertificate(
        business_number=business_number,
        opening_date=opening_date,
        representative_name=_extract_labeled_value(text, ("성명", "대표자", "대표자명")),
        business_name=_extract_labeled_value(text, ("상호(법인명)", "상호", "법인명")),
        corporate_number=_extract_labeled_value(text, ("법인등록번호",)),
        business_sector=_extract_labeled_value(text, ("업태",)),
        business_type=_extract_labeled_value(text, ("종목",)),
        business_address=_extract_labeled_value(text, ("사업장 소재지", "사업장소재지")),
    )


def build_tax_invoice_draft(
    recipient_business_number: str,
    recipient_name: str,
    supply_date: str,
    item_name: str,
    supply_amount: int,
    tax_amount: int,
    purpose: str,
    recipient_email: str | None = None,
) -> TaxInvoiceDraft:
    normalized = normalize_business_number(recipient_business_number)
    if not is_valid_business_number(normalized):
        raise ValueError("유효한 공급받는자 사업자등록번호가 필요합니다.")
    if not recipient_name.strip() or not item_name.strip():
        raise ValueError("공급받는자 상호와 품목명은 필수입니다.")
    if supply_amount < 0 or tax_amount < 0:
        raise ValueError("공급가액과 세액은 0 이상이어야 합니다.")
    if purpose not in {"청구", "영수"}:
        raise ValueError("purpose는 '청구' 또는 '영수'여야 합니다.")
    if recipient_email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", recipient_email):
        raise ValueError("recipient_email 형식이 올바르지 않습니다.")

    try:
        parsed_date = date.fromisoformat(supply_date)
    except ValueError as exc:
        raise ValueError("supply_date는 YYYY-MM-DD 형식이어야 합니다.") from exc

    return TaxInvoiceDraft(
        recipient_business_number=normalized,
        recipient_name=recipient_name.strip(),
        supply_date=parsed_date,
        item_name=item_name.strip(),
        supply_amount=supply_amount,
        tax_amount=tax_amount,
        purpose=purpose,
        recipient_email=recipient_email,
    )


class BusinessCheckService:
    def __init__(self, registry: BusinessRegistryProvider, ocr: OcrProvider) -> None:
        self.registry = registry
        self.ocr = ocr

    async def check_number(self, business_number: str) -> dict[str, Any]:
        normalized = normalize_business_number(business_number)
        format_valid = len(normalized) == 10
        checksum_valid = is_valid_business_number(normalized) if format_valid else False
        result: dict[str, Any] = {
            "input": business_number,
            "business_number": normalized,
            "formatted_business_number": format_business_number(normalized),
            "format_valid": format_valid,
            "checksum_valid": checksum_valid,
            "official_lookup": None,
            "checked_at": _checked_at(),
            "source": "국세청 사업자등록 상태조회",
        }
        if not checksum_valid:
            return result

        try:
            result["official_lookup"] = await self.registry.check_status(normalized)
        except ProviderNotConfigured as exc:
            result["official_lookup"] = {"status": "not_configured", "message": str(exc)}
        except ProviderUnavailable as exc:
            result["official_lookup"] = {"status": "temporarily_unavailable", "message": str(exc)}
        return result

    async def scan_certificate(self, image_url: str, ocr_text: str | None = None) -> dict[str, Any]:
        if not image_url and not ocr_text:
            raise ValueError("image_url 또는 ocr_text 중 하나는 필요합니다.")

        text = ocr_text
        if text is None:
            try:
                text = await self.ocr.extract_text(image_url)
            except ProviderNotConfigured as exc:
                return {
                    "processing_status": "ocr_not_configured",
                    "message": str(exc),
                    "checked_at": _checked_at(),
                }
            except OcrProcessingError as exc:
                return {
                    "processing_status": "ocr_failed",
                    "message": str(exc),
                    "checked_at": _checked_at(),
                }

        certificate = parse_certificate_text(text)
        if certificate is None:
            return {
                "processing_status": "business_number_not_found",
                "extracted": None,
                "checked_at": _checked_at(),
            }

        async def verify_certificate() -> dict[str, Any]:
            if not is_valid_business_number(certificate.business_number):
                return {
                    "verification_status": "not_requested",
                    "verification_message": "유효한 사업자등록번호가 필요합니다.",
                }
            try:
                return await self.registry.validate_certificate(certificate)
            except ProviderNotConfigured as exc:
                return {"status": "not_configured", "message": str(exc)}
            except ProviderUnavailable as exc:
                return {"status": "temporarily_unavailable", "message": str(exc)}

        business_check, certificate_verification = await asyncio.gather(
            self.check_number(certificate.business_number),
            verify_certificate(),
        )
        evidence_report = build_evidence_report(
            business_number=certificate.business_number,
            official_lookup=business_check["official_lookup"],
            certificate_verification=certificate_verification,
            certificate_business_number=certificate.business_number,
            certificate_business_name=certificate.business_name,
            certificate_representative_name=certificate.representative_name,
            certificate_opening_date=certificate.opening_date,
        )
        return {
            "processing_status": "extracted",
            "extracted": certificate.to_dict(),
            "business_check": business_check,
            "certificate_verification": certificate_verification,
            "evidence_report": evidence_report,
            "checked_at": _checked_at(),
        }

    async def reconcile_evidence(
        self,
        business_number: str,
        claimed_business_name: str | None = None,
        claimed_representative_name: str | None = None,
        certificate_business_number: str | None = None,
        certificate_business_name: str | None = None,
        certificate_representative_name: str | None = None,
        certificate_opening_date: str | None = None,
        intent: Literal["verify_only", "prepare_invoice"] = "verify_only",
    ) -> dict[str, Any]:
        certificate = (
            BusinessCertificate(
                business_number=normalize_business_number(certificate_business_number),
                business_name=certificate_business_name,
                representative_name=certificate_representative_name,
                opening_date=certificate_opening_date,
            )
            if certificate_business_number
            else None
        )

        async def verify_certificate() -> dict[str, Any]:
            if certificate is None:
                return {
                    "verification_status": "not_requested",
                    "verification_message": "증명서 정보가 제공되지 않았습니다.",
                }
            if not is_valid_business_number(certificate.business_number):
                return {
                    "verification_status": "not_requested",
                    "verification_message": "유효한 증명서 사업자등록번호가 필요합니다.",
                }
            try:
                return await self.registry.validate_certificate(certificate)
            except ProviderNotConfigured as exc:
                return {"verification_status": "not_configured", "message": str(exc)}
            except ProviderUnavailable as exc:
                return {"verification_status": "temporarily_unavailable", "message": str(exc)}

        business_check, certificate_verification = await asyncio.gather(
            self.check_number(business_number),
            verify_certificate(),
        )
        report = build_evidence_report(
            business_number=business_number,
            official_lookup=business_check["official_lookup"],
            certificate_verification=certificate_verification,
            claimed_business_name=claimed_business_name,
            claimed_representative_name=claimed_representative_name,
            certificate_business_number=certificate_business_number,
            certificate_business_name=certificate_business_name,
            certificate_representative_name=certificate_representative_name,
            certificate_opening_date=certificate_opening_date,
            intent=intent,
        )
        report["source"] = business_check["source"]
        report["checked_at"] = business_check["checked_at"]
        return report


class TaxInvoiceService:
    def __init__(self, handoff: InvoiceHandoffProvider) -> None:
        self.handoff = handoff

    async def prepare_handoff(
        self,
        recipient_business_number: str,
        recipient_name: str,
        supply_date: str,
        item_name: str,
        supply_amount: int,
        tax_amount: int,
        purpose: str,
        recipient_email: str | None = None,
        business_check: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        draft = build_tax_invoice_draft(
            recipient_business_number=recipient_business_number,
            recipient_name=recipient_name,
            supply_date=supply_date,
            item_name=item_name,
            supply_amount=supply_amount,
            tax_amount=tax_amount,
            purpose=purpose,
            recipient_email=recipient_email,
        )
        try:
            handoff = await self.handoff.create_handoff(draft, business_check)
        except ProviderNotConfigured as exc:
            handoff = {"handoff_status": "not_configured", "handoff_url": None, "message": str(exc)}
        except ProviderUnavailable as exc:
            handoff = {
                "handoff_status": "temporarily_unavailable",
                "handoff_url": None,
                "message": str(exc),
            }

        return {
            "draft": draft.to_dict(),
            "issuance_status": "not_issued",
            "requires_user_confirmation": True,
            "business_check": business_check,
            "handoff": handoff,
        }
