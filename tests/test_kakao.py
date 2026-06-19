import json
import unittest
from typing import Any
from unittest.mock import patch

from starlette.testclient import TestClient

from talkcheck.kakao import KakaoConversationStore, KakaoSkillAdapter
from talkcheck.server import mcp


class FakeBusinessService:
    def __init__(self) -> None:
        self.lookups: list[str] = []
        self.images: list[str] = []

    async def check_number(self, business_number: str) -> dict[str, Any]:
        self.lookups.append(business_number)
        return {
            "business_number": "1018116406",
            "formatted_business_number": "101-81-16406",
            "checksum_valid": True,
            "official_lookup": {
                "business_status": "계속사업자",
                "tax_type": "부가가치세 일반과세자",
            },
        }

    async def scan_certificate(self, image_url: str) -> dict[str, Any]:
        self.images.append(image_url)
        return {
            "processing_status": "extracted",
            "extracted": {
                "business_number": "1018116406",
                "business_name": "카카오",
                "representative_name": "정신아",
            },
            "business_check": {
                "business_number": "1018116406",
                "formatted_business_number": "101-81-16406",
                "checksum_valid": True,
                "official_lookup": {"business_status": "계속사업자"},
            },
        }


class FakeInvoiceService:
    def __init__(self) -> None:
        self.request: dict[str, Any] | None = None

    async def prepare_handoff(self, **request: Any) -> dict[str, Any]:
        self.request = request
        return {
            "draft": {
                "recipient_name": request["recipient_name"],
                "item_name": request["item_name"],
                "total_amount": request["supply_amount"] + request["tax_amount"],
            },
            "issuance_status": "not_issued",
            "handoff": {"handoff_url": "https://invoice.example.test/handoff/opaque"},
        }


class NotConfiguredBusinessService(FakeBusinessService):
    async def check_number(self, business_number: str) -> dict[str, Any]:
        result = await super().check_number(business_number)
        result["official_lookup"] = {"status": "not_configured"}
        return result


def payload(
    utterance: str,
    *,
    action: str | None = None,
    extra: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    client_extra = {"talkcheck_action": action, **(extra or {})} if action else None
    return {
        "userRequest": {
            "utterance": utterance,
            "user": {"id": "user-1", "type": "botUserKey"},
        },
        "action": {"clientExtra": client_extra, "params": params or {}},
    }


class KakaoSkillAdapterTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.business = FakeBusinessService()
        self.invoice = FakeInvoiceService()
        self.adapter = KakaoSkillAdapter(
            self.business,
            self.invoice,
            KakaoConversationStore(),
        )

    async def test_number_is_confirmed_before_lookup(self) -> None:
        response = await self.adapter.handle(payload("101-81-16406"))

        self.assertEqual(self.business.lookups, [])
        reply = response["template"]["quickReplies"][0]
        self.assertEqual(reply["extra"]["talkcheck_action"], "lookup_business")
        self.assertEqual(reply["extra"]["business_number"], "1018116406")

    async def test_lookup_returns_fact_card_and_invoice_action(self) -> None:
        response = await self.adapter.handle(
            payload(
                "사업자 조회하기",
                action="lookup_business",
                extra={"business_number": "1018116406"},
            )
        )

        card = response["template"]["outputs"][0]["textCard"]
        self.assertIn("계속사업자", card["description"])
        self.assertNotIn("안전", card["title"])
        self.assertEqual(
            response["template"]["quickReplies"][0]["extra"]["talkcheck_action"],
            "start_invoice",
        )

    async def test_lookup_does_not_expose_internal_not_configured_status(self) -> None:
        adapter = KakaoSkillAdapter(NotConfiguredBusinessService(), self.invoice)

        response = await adapter.handle(
            payload(
                "사업자 조회하기",
                action="lookup_business",
                extra={"business_number": "1018116406"},
            )
        )

        description = response["template"]["outputs"][0]["textCard"]["description"]
        self.assertIn("국세청 조회 연결 필요", description)
        self.assertNotIn("not_configured", description)

    async def test_secure_image_is_scanned_after_consent(self) -> None:
        secure = json.dumps(
            {
                "privacyAgreement": "Y",
                "imageQuantity": "1",
                "secureUrls": "List(https://secure.kakaocdn.test/certificate.jpg)",
            }
        )
        response = await self.adapter.handle(
            payload("등록증 사진", params={"secureimage": secure})
        )

        self.assertEqual(
            self.business.images,
            ["https://secure.kakaocdn.test/certificate.jpg"],
        )
        card = response["template"]["outputs"][0]["textCard"]
        self.assertIn("카카오", card["description"])

    async def test_secure_image_is_not_scanned_without_consent(self) -> None:
        secure = json.dumps(
            {
                "privacyAgreement": "N",
                "imageQuantity": "1",
                "secureUrls": "List(https://secure.kakaocdn.test/certificate.jpg)",
            }
        )
        response = await self.adapter.handle(
            payload("등록증 사진", params={"secureimage": secure})
        )

        self.assertEqual(self.business.images, [])
        text = response["template"]["outputs"][0]["simpleText"]["text"]
        self.assertIn("동의", text)

    async def test_collects_invoice_fields_and_returns_handoff_link(self) -> None:
        await self.adapter.handle(
            payload(
                "사업자 조회하기",
                action="lookup_business",
                extra={"business_number": "1018116406"},
            )
        )
        await self.adapter.handle(payload("준비", action="start_invoice"))
        await self.adapter.handle(payload("카카오"))
        await self.adapter.handle(payload("디자인 용역"))
        await self.adapter.handle(payload("100만원"))
        await self.adapter.handle(payload("2026-06-19"))
        await self.adapter.handle(payload("billing@example.test"))
        response = await self.adapter.handle(payload("청구"))

        assert self.invoice.request is not None
        self.assertEqual(self.invoice.request["supply_amount"], 1_000_000)
        self.assertEqual(self.invoice.request["tax_amount"], 100_000)
        card = response["template"]["outputs"][0]["textCard"]
        self.assertEqual(card["buttons"][0]["webLinkUrl"], "https://invoice.example.test/handoff/opaque")
        self.assertIn("아직 발행되지 않았어요", card["description"])

    async def test_pdf_is_deferred(self) -> None:
        response = await self.adapter.handle(payload("사업자등록증 PDF 올릴게"))

        text = response["template"]["outputs"][0]["simpleText"]["text"]
        self.assertIn("사진", text)
        self.assertIn("사업자번호", text)


class KakaoSkillRouteTest(unittest.TestCase):
    def test_health_check(self) -> None:
        client = TestClient(mcp.streamable_http_app())

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_accepts_kakao_skill_payload(self) -> None:
        adapter = KakaoSkillAdapter(FakeBusinessService(), FakeInvoiceService())
        client = TestClient(mcp.streamable_http_app())

        with patch("talkcheck.server.kakao_adapter", adapter):
            response = client.post("/kakao/skill", json=payload("101-81-16406"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], "2.0")
        self.assertEqual(response.headers["cache-control"], "no-store")


if __name__ == "__main__":
    unittest.main()
