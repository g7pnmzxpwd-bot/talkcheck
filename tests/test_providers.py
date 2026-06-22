import json
import unittest
from unittest.mock import AsyncMock

import httpx

from datetime import date

from talkcheck.domain import BusinessCertificate, TaxInvoiceDraft
from talkcheck.providers import (
    HttpInvoiceHandoffProvider,
    NtsBusinessRegistryProvider,
    OcrProcessingError,
    RemoteMcpBusinessRegistryProvider,
    _validate_remote_image_url,
)


class NtsBusinessRegistryProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_maps_status_response_to_factual_fields(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.params["serviceKey"], "test-key")
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "b_no": "1018116406",
                            "b_stt": "계속사업자",
                            "b_stt_cd": "01",
                            "tax_type": "부가가치세 일반과세자",
                            "tax_type_cd": "01",
                            "end_dt": "",
                            "invoice_apply_dt": "",
                        }
                    ]
                },
            )

        provider = NtsBusinessRegistryProvider(api_key="test-key", transport=httpx.MockTransport(handler))
        result = await provider.check_status("1018116406")

        self.assertEqual(result["business_status"], "계속사업자")
        self.assertEqual(result["business_status_code"], "01")
        self.assertEqual(result["tax_type"], "부가가치세 일반과세자")

    async def test_maps_certificate_verification_response(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": [{"valid": "01", "valid_msg": "확인"}]})

        provider = NtsBusinessRegistryProvider(api_key="test-key", transport=httpx.MockTransport(handler))
        result = await provider.validate_certificate(
            BusinessCertificate(
                business_number="1018116406",
                opening_date="19950216",
                representative_name="대표자",
            )
        )

        self.assertEqual(result["verification_status"], "01")
        self.assertEqual(result["verification_message"], "확인")


class RemoteImageUrlTest(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_non_https_url(self) -> None:
        with self.assertRaises(OcrProcessingError):
            await _validate_remote_image_url("http://example.com/image.jpg")

    async def test_rejects_loopback_url(self) -> None:
        with self.assertRaises(OcrProcessingError):
            await _validate_remote_image_url("https://127.0.0.1/image.jpg")


class RemoteMcpBusinessRegistryProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_calls_remote_tool_with_one_stateless_request(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            self.assertEqual(payload["method"], "tools/call")
            self.assertEqual(payload["params"]["name"], "check_business_registration")
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": "talkcheck-proxy",
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "official_lookup": {
                                            "business_number": "1018116406",
                                            "business_status": "계속사업자",
                                        }
                                    }
                                ),
                            }
                        ]
                    },
                },
            )

        provider = RemoteMcpBusinessRegistryProvider(
            "https://example.test/mcp",
            transport=httpx.MockTransport(handler),
        )

        result = await provider.check_status("1018116406")

        self.assertEqual(result["business_status"], "계속사업자")

    async def test_returns_official_lookup_from_remote_tool(self) -> None:
        provider = RemoteMcpBusinessRegistryProvider("https://example.test/mcp")
        provider._call_tool = AsyncMock(
            return_value={
                "official_lookup": {
                    "business_number": "1018116406",
                    "business_status": "계속사업자",
                    "business_status_code": "01",
                }
            }
        )

        result = await provider.check_status("1018116406")

        self.assertEqual(result["business_status"], "계속사업자")
        provider._call_tool.assert_awaited_once_with(
            "check_business_registration",
            {"business_number": "1018116406"},
        )


class HttpInvoiceHandoffProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_creates_draft_only_and_returns_opaque_url(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers["Authorization"], "Bearer test-token")
            self.assertIn(b'"requested_action":"create_draft_only"', request.content)
            return httpx.Response(
                201,
                json={
                    "reference_id": "draft-123",
                    "handoff_url": "https://invoice.example.test/confirm/draft-123",
                },
            )

        provider = HttpInvoiceHandoffProvider(
            "https://invoice.example.test/api/drafts",
            "test-token",
            transport=httpx.MockTransport(handler),
        )
        result = await provider.create_handoff(
            TaxInvoiceDraft(
                recipient_business_number="1018116406",
                recipient_name="테스트 거래처",
                supply_date=date(2026, 6, 18),
                item_name="개발 용역",
                supply_amount=1_000_000,
                tax_amount=100_000,
                purpose="청구",
            )
        )

        self.assertEqual(result["handoff_status"], "ready")
        self.assertEqual(result["reference_id"], "draft-123")


if __name__ == "__main__":
    unittest.main()
