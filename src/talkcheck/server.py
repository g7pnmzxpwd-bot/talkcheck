"""Business verification MCP entry point."""

from __future__ import annotations

import asyncio
import os
import secrets
import shutil
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response

from talkcheck.handoff import HandoffStore
from talkcheck.kakao import KakaoSkillAdapter, text_response
from talkcheck.providers import (
    DisabledInvoiceHandoffProvider,
    DisabledOcrProvider,
    HttpInvoiceHandoffProvider,
    LocalInvoiceHandoffProvider,
    NtsBusinessRegistryProvider,
    RemoteMcpBusinessRegistryProvider,
    TesseractOcrProvider,
)
from talkcheck.services import BusinessCheckService, TaxInvoiceService, build_tax_invoice_draft


mcp = FastMCP(
    "Business Verification Assistant",
    instructions=(
        "Return official business registration facts and prepare tax invoice handoff data. "
        "Never score, recommend, guarantee safety, or issue a tax invoice automatically."
    ),
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8000")),
    stateless_http=True,
    json_response=True,
)

ocr_provider = (
    TesseractOcrProvider()
    if os.getenv("OCR_PROVIDER", "tesseract").lower() == "tesseract" and shutil.which("tesseract")
    else DisabledOcrProvider()
)

nts_registry = NtsBusinessRegistryProvider()
registry_provider = (
    nts_registry
    if nts_registry.api_key
    else RemoteMcpBusinessRegistryProvider(
        os.getenv("NTS_FALLBACK_MCP_URL", "https://risk.moodwave.kr/talkcheck/mcp")
    )
)
business_service = BusinessCheckService(
    registry=registry_provider,
    ocr=ocr_provider,
)
handoff_api_url = os.getenv("TAX_INVOICE_HANDOFF_API_URL", "").strip()
handoff_api_token = os.getenv("TAX_INVOICE_HANDOFF_API_TOKEN", "").strip()
handoff_mode = os.getenv("TAX_INVOICE_HANDOFF_MODE", "").strip().lower()
handoff_public_base_url = os.getenv("RENDER_EXTERNAL_URL", "").strip() or os.getenv(
    "HANDOFF_PUBLIC_BASE_URL", ""
).strip() or (
    f"http://127.0.0.1:{os.getenv('PORT', '8000')}"
)
handoff_store = HandoffStore()
invoice_handoff_provider = (
    HttpInvoiceHandoffProvider(handoff_api_url, handoff_api_token)
    if handoff_api_url and handoff_api_token
    else LocalInvoiceHandoffProvider(handoff_store, handoff_public_base_url)
    if handoff_mode == "local"
    else DisabledInvoiceHandoffProvider()
)
invoice_service = TaxInvoiceService(handoff=invoice_handoff_provider)
kakao_adapter = KakaoSkillAdapter(business_service, invoice_service)
handoff_ui_dist = Path(
    os.getenv(
        "HANDOFF_UI_DIST",
        str(Path(__file__).resolve().parents[2] / "handoff-ui" / "dist"),
    )
)
playmcp_tool_timeout_seconds = float(os.getenv("PLAYMCP_TOOL_TIMEOUT_SECONDS", "2.8"))


async def _run_playmcp_tool(awaitable):
    try:
        return await asyncio.wait_for(awaitable, timeout=playmcp_tool_timeout_seconds)
    except TimeoutError as exc:
        raise RuntimeError(
            "The business verification request could not complete within 3 seconds. Please retry."
        ) from exc


@mcp.tool(
    title="Check Korean business registration",
    description=(
        "Validates a Korean business registration number and returns its current official "
        "National Tax Service status and tax type. Use this for factual verification only; "
        "it does not score or recommend a business."
    ),
    annotations=ToolAnnotations(
        title="Check Korean business registration",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def check_business_registration(business_number: str) -> dict[str, Any]:
    """Check the format and current official NTS status of a Korean business number."""
    return await _run_playmcp_tool(business_service.check_number(business_number))


@mcp.tool(
    title="Scan Korean business certificate",
    description=(
        "Extracts fields from a Korean business registration certificate using a public "
        "HTTPS image URL or OCR text, then verifies the extracted facts against official "
        "National Tax Service data without making a risk judgment."
    ),
    annotations=ToolAnnotations(
        title="Scan Korean business certificate",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def scan_business_certificate(image_url: str = "", ocr_text: str | None = None) -> dict[str, Any]:
    """Extract a Korean business certificate and return official facts without a risk judgment.

    Use image_url when the host can pass the uploaded image URL. During development,
    ocr_text may contain text already extracted by the host model or an OCR service.
    """
    return await _run_playmcp_tool(
        business_service.scan_certificate(image_url=image_url, ocr_text=ocr_text)
    )


@mcp.tool(
    title="Prepare tax invoice confirmation",
    description=(
        "Validates recipient details and creates a standard Korean tax invoice draft for "
        "an external confirmation screen. This tool never issues or transmits a tax invoice "
        "and always requires explicit user confirmation."
    ),
    annotations=ToolAnnotations(
        title="Prepare tax invoice confirmation",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def prepare_tax_invoice_handoff(
    recipient_business_number: str,
    recipient_name: str,
    supply_date: str,
    item_name: str,
    supply_amount: int,
    tax_amount: int,
    purpose: str,
    recipient_email: str | None = None,
    recipient_representative_name: str | None = None,
) -> dict[str, Any]:
    """Prepare a standard tax invoice draft for an external confirmation screen.

    This tool never issues or transmits a tax invoice. All monetary and tax fields
    must be provided by the user and confirmed in the external ASP flow.
    """
    async def prepare() -> dict[str, Any]:
        business_check = await business_service.check_number(recipient_business_number)
        business_check["business_name"] = recipient_name.strip()
        business_check["representative_name"] = (
            recipient_representative_name.strip() if recipient_representative_name else None
        )
        return await invoice_service.prepare_handoff(
            recipient_business_number=recipient_business_number,
            recipient_name=recipient_name,
            supply_date=supply_date,
            item_name=item_name,
            supply_amount=supply_amount,
            tax_amount=tax_amount,
            purpose=purpose,
            recipient_email=recipient_email,
            business_check=business_check,
        )

    return await _run_playmcp_tool(prepare())


def _draft_from_payload(payload: dict[str, Any]):
    return build_tax_invoice_draft(
        recipient_business_number=str(payload["recipient_business_number"]),
        recipient_name=str(payload["recipient_name"]),
        supply_date=str(payload["supply_date"]),
        item_name=str(payload["item_name"]),
        supply_amount=int(payload["supply_amount"]),
        tax_amount=int(payload["tax_amount"]),
        purpose=str(payload["purpose"]),
        recipient_email=str(payload["recipient_email"]) if payload.get("recipient_email") else None,
    )


def _no_store_json(payload: dict[str, Any], status_code: int = 200) -> JSONResponse:
    return JSONResponse(payload, status_code=status_code, headers={"Cache-Control": "no-store"})


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> Response:
    del request
    return _no_store_json({"status": "ok"})


@mcp.custom_route("/kakao/skill", methods=["POST"])
async def kakao_skill(request: Request) -> Response:
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise ValueError
    except (ValueError, TypeError):
        return _no_store_json(text_response("요청을 읽지 못했어요. 다시 시도해주세요."), 400)

    try:
        response = await asyncio.wait_for(kakao_adapter.handle(payload), timeout=4.5)
    except TimeoutError:
        response = text_response("확인이 조금 지연되고 있어요. 잠시 후 다시 시도해주세요.")
    return _no_store_json(response)


@mcp.custom_route("/api/handoffs", methods=["POST"])
async def create_handoff(request: Request) -> Response:
    if os.getenv("TAX_INVOICE_HANDOFF_MODE", "").strip().lower() != "local":
        return _no_store_json({"message": "local handoff mode is disabled"}, 503)
    expected_token = os.getenv("TAX_INVOICE_HANDOFF_API_TOKEN", "").strip()
    supplied_token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not expected_token:
        return _no_store_json({"message": "handoff API token is not configured"}, 503)
    if not supplied_token or not secrets.compare_digest(supplied_token, expected_token):
        return _no_store_json({"message": "unauthorized"}, 401)

    try:
        payload = await request.json()
        if payload.get("requested_action") != "create_draft_only":
            raise ValueError("requested_action must be create_draft_only")
        draft = _draft_from_payload(payload["draft"])
        business_check = payload.get("business_check") or {}
        if not isinstance(business_check, dict):
            raise ValueError("business_check must be an object")
    except (KeyError, TypeError, ValueError) as exc:
        return _no_store_json({"message": str(exc)}, 400)

    result = handoff_store.create(draft, business_check, handoff_public_base_url)
    return _no_store_json(result, 201)


@mcp.custom_route("/api/handoffs/{reference_id}", methods=["GET"])
async def get_handoff(request: Request) -> Response:
    record = handoff_store.get(request.path_params["reference_id"])
    if record is None:
        return _no_store_json({"message": "handoff not found or expired"}, 404)
    return _no_store_json(record)


@mcp.custom_route("/api/handoffs/{reference_id}", methods=["PATCH"])
async def update_handoff(request: Request) -> Response:
    try:
        payload = await request.json()
        draft = _draft_from_payload(payload["draft"])
    except (KeyError, TypeError, ValueError) as exc:
        return _no_store_json({"message": str(exc)}, 400)

    record = handoff_store.update(request.path_params["reference_id"], draft)
    if record is None:
        return _no_store_json({"message": "handoff not found or expired"}, 404)
    return _no_store_json(record)


@mcp.custom_route("/api/handoffs/{reference_id}/prepare", methods=["POST"])
async def prepare_handoff(request: Request) -> Response:
    try:
        payload = await request.json()
        draft = _draft_from_payload(payload["draft"])
        result = handoff_store.prepare(request.path_params["reference_id"], draft)
    except KeyError:
        return _no_store_json({"message": "handoff not found or expired"}, 404)
    except (TypeError, ValueError) as exc:
        return _no_store_json({"message": str(exc)}, 400)
    return _no_store_json(result)


@mcp.custom_route("/handoff/{reference_id}", methods=["GET"], include_in_schema=False)
async def handoff_page(request: Request) -> Response:
    del request
    index_file = handoff_ui_dist / "index.html"
    if not index_file.is_file():
        return _no_store_json({"message": "handoff UI is not built"}, 503)
    return FileResponse(index_file, headers={"Cache-Control": "no-store"})


@mcp.custom_route("/", methods=["GET"], include_in_schema=False)
async def demo_page(request: Request) -> Response:
    return await handoff_page(request)


@mcp.custom_route("/assets/{asset_path:path}", methods=["GET"], include_in_schema=False)
async def handoff_asset(request: Request) -> Response:
    assets_root = (handoff_ui_dist / "assets").resolve()
    asset_file = (assets_root / request.path_params["asset_path"]).resolve()
    if assets_root not in asset_file.parents or not asset_file.is_file():
        return _no_store_json({"message": "asset not found"}, 404)
    return FileResponse(asset_file, headers={"Cache-Control": "public, max-age=31536000, immutable"})


def main() -> None:
    try:
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
