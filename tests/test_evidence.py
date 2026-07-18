import unittest
from typing import Any

from talkcheck.domain import BusinessCertificate
from talkcheck.evidence import build_evidence_report
from talkcheck.services import BusinessCheckService


class FakeRegistry:
    async def check_status(self, business_number: str) -> dict[str, Any]:
        return {
            "business_number": business_number,
            "business_status": "계속사업자",
            "business_status_code": "01",
            "tax_type": "부가가치세 일반과세자",
        }

    async def validate_certificate(self, certificate: BusinessCertificate) -> dict[str, Any]:
        self.certificate = certificate
        return {"verification_status": "01", "verification_message": "확인"}


class FakeOcr:
    async def extract_text(self, image_url: str) -> str:
        del image_url
        return ""


class EvidenceReportTest(unittest.TestCase):
    def test_marks_matching_certificate_bundle_as_verified(self) -> None:
        report = build_evidence_report(
            business_number="101-81-16406",
            claimed_business_name="카카오",
            claimed_representative_name="정신아",
            certificate_business_number="1018116406",
            certificate_business_name="카카오",
            certificate_representative_name="정신아",
            certificate_opening_date="19950216",
            official_lookup={
                "business_status": "계속사업자",
                "business_status_code": "01",
                "tax_type": "부가가치세 일반과세자",
            },
            certificate_verification={"verification_status": "01"},
            intent="prepare_invoice",
        )

        self.assertEqual(report["workflow_status"], "ready_for_draft")
        self.assertTrue(report["can_prepare_invoice_draft"])
        self.assertEqual(report["summary"]["conflicts"], 0)
        name = next(item for item in report["field_results"] if item["field"] == "business_name")
        self.assertEqual(name["status"], "verified")
        self.assertIn("nts_certificate_validation", name["sources"])

    def test_surfaces_exact_name_conflict_and_question(self) -> None:
        report = build_evidence_report(
            business_number="101-81-16406",
            claimed_business_name="모노랩",
            certificate_business_number="101-81-16406",
            certificate_business_name="모노랩 스튜디오",
            certificate_representative_name="김민수",
            certificate_opening_date="20200101",
            official_lookup={
                "business_status": "계속사업자",
                "business_status_code": "01",
                "tax_type": "부가가치세 일반과세자",
            },
            certificate_verification={"verification_status": "01"},
            intent="prepare_invoice",
        )

        self.assertEqual(report["workflow_status"], "needs_clarification")
        self.assertEqual(report["next_action"], "resolve_conflicts")
        self.assertEqual(report["summary"]["conflicts"], 1)
        self.assertEqual(
            report["clarifying_questions"][0],
            "사용자 입력(상호: 모노랩)과 증명서 추출(상호: 모노랩 스튜디오) 중 어느 값이 맞나요?",
        )
        self.assertNotIn("score", report)
        self.assertNotIn("recommendation", report)

    def test_does_not_count_unregistered_notice_as_verified_tax_type(self) -> None:
        report = build_evidence_report(
            business_number="123-45-67891",
            official_lookup={
                "business_status": "",
                "business_status_code": "",
                "tax_type": "국세청에 등록되지 않은 사업자등록번호입니다.",
                "tax_type_code": "",
            },
        )

        tax_type = next(item for item in report["field_results"] if item["field"] == "tax_type")
        self.assertEqual(report["workflow_status"], "official_lookup_unavailable")
        self.assertFalse(report["summary"]["official_lookup_available"])
        self.assertEqual(report["summary"]["officially_verified"], 0)
        self.assertEqual(tax_type["status"], "unavailable")
        self.assertIsNone(tax_type["official"])

    def test_labels_name_as_user_confirmation_when_no_certificate_exists(self) -> None:
        report = build_evidence_report(
            business_number="101-81-16406",
            claimed_business_name="카카오",
            official_lookup={
                "business_status": "계속사업자",
                "business_status_code": "01",
                "tax_type": "부가가치세 일반과세자",
            },
            intent="prepare_invoice",
        )

        name = next(item for item in report["field_results"] if item["field"] == "business_name")
        self.assertEqual(report["workflow_status"], "ready_for_draft")
        self.assertEqual(name["status"], "needs_confirmation")
        self.assertIn("상태조회로는", name["message"])

    def test_blocks_invalid_number_before_official_result(self) -> None:
        report = build_evidence_report(
            business_number="123-45-67890",
            official_lookup=None,
            intent="verify_only",
        )

        self.assertEqual(report["workflow_status"], "invalid_business_number")
        self.assertFalse(report["can_prepare_invoice_draft"])
        self.assertIn("10자리", report["clarifying_questions"][0])

    def test_marks_failed_certificate_bundle_as_a_non_specific_conflict(self) -> None:
        report = build_evidence_report(
            business_number="101-81-16406",
            claimed_business_name="카카오",
            certificate_business_number="101-81-16406",
            certificate_business_name="카카오",
            certificate_representative_name="정신아",
            certificate_opening_date="19950216",
            official_lookup={
                "business_status": "계속사업자",
                "business_status_code": "01",
                "tax_type": "부가가치세 일반과세자",
            },
            certificate_verification={"verification_status": "02"},
        )

        self.assertEqual(report["workflow_status"], "needs_clarification")
        bundle = next(
            item for item in report["field_results"] if item["field"] == "certificate_bundle"
        )
        self.assertEqual(bundle["status"], "conflict")
        self.assertIn("특정할 수 없습니다", bundle["message"])


class EvidenceServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_reconciles_status_and_certificate_in_parallel_workflow(self) -> None:
        registry = FakeRegistry()
        service = BusinessCheckService(registry, FakeOcr())

        report = await service.reconcile_evidence(
            business_number="101-81-16406",
            claimed_business_name="카카오",
            claimed_representative_name="정신아",
            certificate_business_number="101-81-16406",
            certificate_business_name="카카오",
            certificate_representative_name="정신아",
            certificate_opening_date="19950216",
            intent="prepare_invoice",
        )

        self.assertEqual(report["workflow_status"], "ready_for_draft")
        self.assertEqual(registry.certificate.opening_date, "19950216")
        self.assertEqual(report["source"], "국세청 사업자등록 상태조회")


if __name__ == "__main__":
    unittest.main()
