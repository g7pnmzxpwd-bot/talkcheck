"""External provider boundaries for official lookup, OCR, and invoice handoff."""

from __future__ import annotations

import asyncio
import ipaddress
import io
import json
import os
import shutil
import socket
from collections.abc import Callable
from typing import Any, Protocol
from urllib.parse import urljoin, urlparse

import httpx
import pytesseract
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from PIL import Image, UnidentifiedImageError

from talkcheck.domain import BusinessCertificate, TaxInvoiceDraft
from talkcheck.handoff import HandoffStore


class ProviderNotConfigured(RuntimeError):
    """Raised when a provider is intentionally unavailable in the skeleton."""


class ProviderUnavailable(RuntimeError):
    """Raised when a configured upstream provider cannot complete a request."""


class OcrProcessingError(RuntimeError):
    """Raised when a remote image cannot be fetched or processed safely."""


class BusinessRegistryProvider(Protocol):
    async def check_status(self, business_number: str) -> dict[str, Any]: ...

    async def validate_certificate(self, certificate: BusinessCertificate) -> dict[str, Any]: ...


class OcrProvider(Protocol):
    async def extract_text(self, image_url: str) -> str: ...


class InvoiceHandoffProvider(Protocol):
    async def create_handoff(
        self,
        draft: TaxInvoiceDraft,
        business_check: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


class NtsBusinessRegistryProvider:
    """Calls the National Tax Service APIs exposed through data.go.kr."""

    def __init__(
        self,
        api_key: str | None = None,
        status_url: str | None = None,
        validate_url: str | None = None,
        timeout_seconds: float = 15,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv("DATA_GO_KR_API_KEY", "")).strip()
        self.status_url = status_url or os.getenv(
            "NTS_STATUS_API_URL", "https://api.odcloud.kr/api/nts-businessman/v1/status"
        )
        self.validate_url = validate_url or os.getenv(
            "NTS_VALIDATE_API_URL", "https://api.odcloud.kr/api/nts-businessman/v1/validate"
        )
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def _require_api_key(self) -> None:
        if not self.api_key:
            raise ProviderNotConfigured("DATA_GO_KR_API_KEY is not configured")

    async def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_api_key()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, transport=self.transport) as client:
                response = await client.post(url, params={"serviceKey": self.api_key}, json=payload)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailable("국세청 조회를 완료하지 못했습니다.") from exc

    async def check_status(self, business_number: str) -> dict[str, Any]:
        payload = await self._post(self.status_url, {"b_no": [business_number]})
        item = (payload.get("data") or [{}])[0]
        return {
            "business_number": item.get("b_no", business_number),
            "business_status": item.get("b_stt"),
            "business_status_code": item.get("b_stt_cd"),
            "tax_type": item.get("tax_type"),
            "tax_type_code": item.get("tax_type_cd"),
            "closing_date": item.get("end_dt"),
            "invoice_application_date": item.get("invoice_apply_dt"),
        }

    async def validate_certificate(self, certificate: BusinessCertificate) -> dict[str, Any]:
        if not certificate.opening_date or not certificate.representative_name:
            return {
                "verification_status": "not_requested",
                "verification_message": "개업일자와 대표자명이 모두 필요합니다.",
            }

        business = {
            "b_no": certificate.business_number,
            "start_dt": certificate.opening_date,
            "p_nm": certificate.representative_name,
            "p_nm2": certificate.representative_name_2 or "",
            "b_nm": certificate.business_name or "",
            "corp_no": certificate.corporate_number or "",
            "b_sector": certificate.business_sector or "",
            "b_type": certificate.business_type or "",
            "b_adr": certificate.business_address or "",
        }
        payload = await self._post(self.validate_url, {"businesses": [business]})
        item = (payload.get("data") or [{}])[0]
        return {
            "verification_status": item.get("valid"),
            "verification_message": item.get("valid_msg"),
        }


class RemoteMcpBusinessRegistryProvider:
    """Delegates official lookup to a TalkCheck MCP server that owns the API key."""

    def __init__(self, mcp_url: str) -> None:
        self.mcp_url = mcp_url

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            async with streamable_http_client(self.mcp_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments)
        except Exception as exc:
            raise ProviderUnavailable("국세청 조회를 완료하지 못했습니다.") from exc

        for content in result.content:
            text = getattr(content, "text", None)
            if not text:
                continue
            try:
                payload = json.loads(text)
            except ValueError:
                continue
            if isinstance(payload, dict):
                return payload
        raise ProviderUnavailable("국세청 조회 응답을 해석하지 못했습니다.")

    async def check_status(self, business_number: str) -> dict[str, Any]:
        result = await self._call_tool(
            "check_business_registration",
            {"business_number": business_number},
        )
        official_lookup = result.get("official_lookup")
        if not isinstance(official_lookup, dict) or official_lookup.get("status"):
            raise ProviderUnavailable("국세청 조회를 완료하지 못했습니다.")
        return official_lookup

    async def validate_certificate(self, certificate: BusinessCertificate) -> dict[str, Any]:
        if not certificate.opening_date or not certificate.representative_name:
            return {
                "verification_status": "not_requested",
                "verification_message": "개업일자와 대표자명이 모두 필요합니다.",
            }

        labels = (
            ("등록번호", certificate.business_number),
            ("개업연월일", certificate.opening_date),
            ("성명", certificate.representative_name),
            ("상호(법인명)", certificate.business_name),
            ("법인등록번호", certificate.corporate_number),
            ("업태", certificate.business_sector),
            ("종목", certificate.business_type),
            ("사업장 소재지", certificate.business_address),
        )
        ocr_text = "\n".join(f"{label} {value}" for label, value in labels if value)
        result = await self._call_tool(
            "scan_business_certificate",
            {"image_url": "", "ocr_text": ocr_text},
        )
        verification = result.get("certificate_verification")
        if not isinstance(verification, dict):
            raise ProviderUnavailable("사업자등록증 진위확인을 완료하지 못했습니다.")
        return verification


class DisabledOcrProvider:
    async def extract_text(self, image_url: str) -> str:
        del image_url
        raise ProviderNotConfigured("OCR provider is not configured")


def _is_public_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


async def _validate_remote_image_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise OcrProcessingError("이미지는 인증정보가 없는 HTTPS URL이어야 합니다.")

    try:
        literal_ip = ipaddress.ip_address(parsed.hostname)
        addresses = [str(literal_ip)]
    except ValueError:
        try:
            address_info = await asyncio.to_thread(socket.getaddrinfo, parsed.hostname, parsed.port or 443)
            addresses = list({item[4][0] for item in address_info})
        except socket.gaierror as exc:
            raise OcrProcessingError("이미지 호스트를 확인할 수 없습니다.") from exc

    if not addresses or any(not _is_public_ip(address) for address in addresses):
        raise OcrProcessingError("공개 인터넷 이미지 URL만 사용할 수 있습니다.")


class TesseractOcrProvider:
    """Downloads a short-lived image and processes it without persisting the file."""

    def __init__(
        self,
        languages: str | None = None,
        max_image_bytes: int | None = None,
        timeout_seconds: float = 15,
        max_redirects: int = 3,
        ocr_function: Callable[[Image.Image], str] | None = None,
    ) -> None:
        self.languages = languages or os.getenv("OCR_LANGUAGES", "kor+eng")
        self.max_image_bytes = max_image_bytes or int(os.getenv("OCR_MAX_IMAGE_BYTES", "8388608"))
        self.timeout_seconds = timeout_seconds
        self.max_redirects = max_redirects
        self.ocr_function = ocr_function

    async def _download(self, image_url: str) -> bytes:
        current_url = image_url
        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=False) as client:
            for _ in range(self.max_redirects + 1):
                await _validate_remote_image_url(current_url)
                try:
                    async with client.stream("GET", current_url) as response:
                        if response.is_redirect:
                            location = response.headers.get("location")
                            if not location:
                                raise OcrProcessingError("이미지 리디렉션 주소가 없습니다.")
                            current_url = urljoin(current_url, location)
                            continue
                        response.raise_for_status()
                        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                        if not content_type.startswith("image/"):
                            raise OcrProcessingError("이미지 형식의 응답이 아닙니다.")
                        content_length = response.headers.get("content-length")
                        if content_length and int(content_length) > self.max_image_bytes:
                            raise OcrProcessingError("이미지 크기 제한을 초과했습니다.")

                        chunks: list[bytes] = []
                        total = 0
                        async for chunk in response.aiter_bytes():
                            total += len(chunk)
                            if total > self.max_image_bytes:
                                raise OcrProcessingError("이미지 크기 제한을 초과했습니다.")
                            chunks.append(chunk)
                        return b"".join(chunks)
                except httpx.HTTPError as exc:
                    raise OcrProcessingError("이미지를 내려받지 못했습니다.") from exc
        raise OcrProcessingError("이미지 리디렉션 횟수를 초과했습니다.")

    def _run_ocr(self, image_bytes: bytes) -> str:
        try:
            Image.MAX_IMAGE_PIXELS = 20_000_000
            with Image.open(io.BytesIO(image_bytes)) as image:
                image.load()
                converted = image.convert("RGB")
                if self.ocr_function:
                    return self.ocr_function(converted).strip()
                return pytesseract.image_to_string(
                    converted,
                    lang=self.languages,
                    config="--psm 6",
                ).strip()
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
            raise OcrProcessingError("이미지를 해석하지 못했습니다.") from exc
        except pytesseract.TesseractError as exc:
            raise OcrProcessingError("OCR 처리를 완료하지 못했습니다.") from exc

    async def extract_text(self, image_url: str) -> str:
        if not shutil.which("tesseract") and self.ocr_function is None:
            raise ProviderNotConfigured("Tesseract 실행 파일이 설치되지 않았습니다.")
        image_bytes = await self._download(image_url)
        text = await asyncio.to_thread(self._run_ocr, image_bytes)
        if not text:
            raise OcrProcessingError("이미지에서 텍스트를 찾지 못했습니다.")
        return text


class DisabledInvoiceHandoffProvider:
    async def create_handoff(
        self,
        draft: TaxInvoiceDraft,
        business_check: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        del draft
        del business_check
        return {
            "handoff_status": "not_configured",
            "handoff_url": None,
            "message": "전자세금계산서 ASP 연동이 필요합니다.",
        }


class HttpInvoiceHandoffProvider:
    """Creates a draft in a separate confirmation service and returns its opaque URL."""

    def __init__(
        self,
        api_url: str,
        api_token: str,
        timeout_seconds: float = 15,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_url = api_url.strip()
        self.api_token = api_token.strip()
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def create_handoff(
        self,
        draft: TaxInvoiceDraft,
        business_check: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.api_url or not self.api_token:
            raise ProviderNotConfigured("세금계산서 발행확인 백엔드가 설정되지 않았습니다.")
        parsed = urlparse(self.api_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ProviderNotConfigured("발행확인 백엔드는 HTTPS URL이어야 합니다.")

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, transport=self.transport) as client:
                response = await client.post(
                    self.api_url,
                    headers={"Authorization": f"Bearer {self.api_token}"},
                    json={
                        "draft": draft.to_dict(),
                        "business_check": business_check or {},
                        "requested_action": "create_draft_only",
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailable("발행확인 링크를 만들지 못했습니다.") from exc

        handoff_url = str(payload.get("handoff_url") or "")
        handoff_parsed = urlparse(handoff_url)
        if handoff_parsed.scheme != "https" or not handoff_parsed.hostname:
            raise ProviderUnavailable("발행확인 백엔드가 유효한 HTTPS 링크를 반환하지 않았습니다.")
        return {
            "handoff_status": "ready",
            "handoff_url": handoff_url,
            "reference_id": payload.get("reference_id"),
        }


class LocalInvoiceHandoffProvider:
    """Stores a short-lived draft in this process for local end-to-end testing."""

    def __init__(self, store: HandoffStore, public_base_url: str) -> None:
        self.store = store
        self.public_base_url = public_base_url

    async def create_handoff(
        self,
        draft: TaxInvoiceDraft,
        business_check: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.store.create(draft, business_check or {}, self.public_base_url)
