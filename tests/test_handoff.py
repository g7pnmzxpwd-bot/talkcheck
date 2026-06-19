import os
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

from starlette.testclient import TestClient

from talkcheck.domain import TaxInvoiceDraft
from talkcheck.handoff import HandoffStore
from talkcheck.server import handoff_store, mcp


def sample_draft() -> TaxInvoiceDraft:
    return TaxInvoiceDraft(
        recipient_business_number="1018116406",
        recipient_name="테스트 거래처",
        supply_date=date(2026, 6, 19),
        item_name="개발 용역",
        supply_amount=1_000_000,
        tax_amount=100_000,
        purpose="청구",
        recipient_email="billing@example.test",
    )


class HandoffStoreTest(unittest.TestCase):
    def test_returns_an_opaque_url_without_invoice_data(self) -> None:
        store = HandoffStore(
            token_factory=lambda: "opaque-reference",
            now=lambda: datetime(2026, 6, 19, tzinfo=timezone.utc),
        )

        result = store.create(
            sample_draft(),
            {"business_name": "테스트 거래처", "business_status": "계속사업자"},
            "https://invoice.example.test",
        )

        self.assertEqual(result["handoff_url"], "https://invoice.example.test/handoff/opaque-reference")
        self.assertNotIn("1018116406", result["handoff_url"])
        self.assertNotIn("1000000", result["handoff_url"])
        record = store.get("opaque-reference")
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record["issuance_status"], "not_issued")

    def test_prepare_marks_confirmation_ready_without_issuing(self) -> None:
        store = HandoffStore(token_factory=lambda: "opaque-reference")
        store.create(sample_draft(), {}, "https://invoice.example.test")

        result = store.prepare("opaque-reference", sample_draft())

        self.assertEqual(result["handoff_status"], "ready_for_external_confirmation")
        self.assertEqual(result["issuance_status"], "not_issued")


class HandoffApiTest(unittest.TestCase):
    def setUp(self) -> None:
        handoff_store.clear()
        self.client = TestClient(mcp.streamable_http_app())

    def test_root_serves_demo_ui(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("톡체크 · 세금계산서 발행 준비", response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_create_load_update_and_prepare_draft(self) -> None:
        payload = {
            "requested_action": "create_draft_only",
            "draft": sample_draft().to_dict(),
            "business_check": {
                "business_name": "테스트 거래처",
                "representative_name": "홍길동",
                "formatted_business_number": "101-81-16406",
                "official_lookup": {
                    "business_status": "계속사업자",
                    "tax_type": "부가가치세 일반과세자",
                },
                "source": "국세청 사업자등록 상태조회",
            },
        }
        env = {
            "TAX_INVOICE_HANDOFF_MODE": "local",
            "TAX_INVOICE_HANDOFF_API_TOKEN": "test-token",
            "HANDOFF_PUBLIC_BASE_URL": "https://invoice.example.test",
        }
        with patch.dict(os.environ, env):
            created = self.client.post(
                "/api/handoffs",
                headers={"Authorization": "Bearer test-token"},
                json=payload,
            )

        self.assertEqual(created.status_code, 201)
        created_payload = created.json()
        self.assertNotIn("1018116406", created_payload["handoff_url"])
        reference_id = created_payload["reference_id"]

        loaded = self.client.get(f"/api/handoffs/{reference_id}")
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.json()["draft"]["total_amount"], 1_100_000)

        updated_draft = sample_draft().to_dict() | {"supply_amount": 2_000_000, "tax_amount": 200_000}
        updated = self.client.patch(
            f"/api/handoffs/{reference_id}",
            json={"draft": updated_draft},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["draft"]["total_amount"], 2_200_000)

        prepared = self.client.post(
            f"/api/handoffs/{reference_id}/prepare",
            json={"draft": updated_draft},
        )
        self.assertEqual(prepared.status_code, 200)
        self.assertEqual(prepared.json()["handoff_status"], "ready_for_external_confirmation")
        self.assertEqual(prepared.json()["issuance_status"], "not_issued")

    def test_create_requires_local_mode_and_bearer_token(self) -> None:
        payload = {"requested_action": "create_draft_only", "draft": sample_draft().to_dict()}
        with patch.dict(
            os.environ,
            {"TAX_INVOICE_HANDOFF_MODE": "local", "TAX_INVOICE_HANDOFF_API_TOKEN": "test-token"},
        ):
            response = self.client.post("/api/handoffs", json=payload)

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
