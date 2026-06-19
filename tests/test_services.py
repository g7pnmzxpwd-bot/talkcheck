import unittest
from typing import Any

from talkcheck.domain import BusinessCertificate, TaxInvoiceDraft
from talkcheck.services import BusinessCheckService, TaxInvoiceService, parse_certificate_text


class FakeRegistry:
    async def check_status(self, business_number: str) -> dict[str, Any]:
        return {
            "business_number": business_number,
            "business_status": "계속사업자",
            "tax_type": "부가가치세 일반과세자",
        }

    async def validate_certificate(self, certificate: BusinessCertificate) -> dict[str, Any]:
        return {"verification_status": "01", "verification_message": "확인"}


class FakeOcr:
    async def extract_text(self, image_url: str) -> str:
        self.image_url = image_url
        return """등록번호 101-81-16406
상호(법인명) 카카오
성명 정신아
개업연월일 19950216
사업장 소재지 제주특별자치도"""


class FakeHandoff:
    async def create_handoff(
        self,
        draft: TaxInvoiceDraft,
        business_check: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.business_check = business_check
        return {"handoff_status": "ready", "handoff_url": "https://example.test/confirm/opaque-id"}


class BusinessCheckServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_number_lookup_returns_facts_without_score(self) -> None:
        service = BusinessCheckService(FakeRegistry(), FakeOcr())
        result = await service.check_number("101-81-16406")

        self.assertTrue(result["checksum_valid"])
        self.assertEqual(result["official_lookup"]["business_status"], "계속사업자")
        self.assertNotIn("score", result)
        self.assertNotIn("recommendation", result)

    async def test_scans_certificate_and_validates_it(self) -> None:
        service = BusinessCheckService(FakeRegistry(), FakeOcr())
        result = await service.scan_certificate("https://example.test/certificate.jpg")

        self.assertEqual(result["extracted"]["business_number"], "1018116406")
        self.assertEqual(result["certificate_verification"]["verification_status"], "01")

    def test_parses_basic_certificate_fields(self) -> None:
        certificate = parse_certificate_text(
            "등록번호 101-81-16406\n상호(법인명) 카카오\n성명 정신아\n개업연월일 19950216"
        )
        self.assertIsNotNone(certificate)
        assert certificate is not None
        self.assertEqual(certificate.business_name, "카카오")
        self.assertEqual(certificate.opening_date, "19950216")


class TaxInvoiceServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_prepares_handoff_without_issuing(self) -> None:
        handoff = FakeHandoff()
        service = TaxInvoiceService(handoff)
        business_check = {"business_status": "계속사업자"}
        result = await service.prepare_handoff(
            recipient_business_number="101-81-16406",
            recipient_name="카카오",
            supply_date="2026-06-18",
            item_name="개발 용역",
            supply_amount=1_000_000,
            tax_amount=100_000,
            purpose="청구",
            recipient_email="billing@example.test",
            business_check=business_check,
        )

        self.assertEqual(result["draft"]["total_amount"], 1_100_000)
        self.assertEqual(result["issuance_status"], "not_issued")
        self.assertTrue(result["requires_user_confirmation"])
        self.assertEqual(handoff.business_check, business_check)


if __name__ == "__main__":
    unittest.main()
