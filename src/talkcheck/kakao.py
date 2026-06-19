"""Kakao Channel skill adapter for TalkCheck's guided chat flow."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

from talkcheck.business_number import (
    find_business_number,
    format_business_number,
    is_valid_business_number,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _quick_reply(label: str, message: str, action: str, **extra: Any) -> dict[str, Any]:
    return {
        "label": label,
        "action": "message",
        "messageText": message,
        "extra": {"talkcheck_action": action, **extra},
    }


def text_response(text: str, quick_replies: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    template: dict[str, Any] = {"outputs": [{"simpleText": {"text": text}}]}
    if quick_replies:
        template["quickReplies"] = quick_replies
    return {"version": "2.0", "template": template}


def _card_response(
    title: str,
    description: str,
    quick_replies: list[dict[str, Any]] | None = None,
    web_link: str | None = None,
) -> dict[str, Any]:
    card: dict[str, Any] = {"title": title, "description": description}
    if web_link:
        card["buttons"] = [
            {"action": "webLink", "label": "발행 화면 열기", "webLinkUrl": web_link}
        ]
    template: dict[str, Any] = {"outputs": [{"textCard": card}]}
    if quick_replies:
        template["quickReplies"] = quick_replies
    return {"version": "2.0", "template": template}


@dataclass
class _Conversation:
    expires_at: datetime
    business_number: str | None = None
    business_name: str | None = None
    business_check: dict[str, Any] | None = None
    invoice_step: str | None = None
    invoice: dict[str, Any] = field(default_factory=dict)


class KakaoConversationStore:
    def __init__(
        self,
        ttl_seconds: int = 30 * 60,
        now: Callable[[], datetime] = _now,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.now = now
        self._conversations: dict[str, _Conversation] = {}

    def get(self, user_id: str) -> _Conversation:
        conversation = self._conversations.get(user_id)
        current = self.now()
        if conversation is None or conversation.expires_at <= current:
            conversation = _Conversation(
                expires_at=current + timedelta(seconds=self.ttl_seconds)
            )
            self._conversations[user_id] = conversation
        else:
            conversation.expires_at = current + timedelta(seconds=self.ttl_seconds)
        return conversation

def _secure_image_url(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    action = payload.get("action") or {}
    params = action.get("params") or {}
    raw = params.get("secureimage")
    if raw is None:
        for detail in (action.get("detailParams") or {}).values():
            value = detail.get("value") if isinstance(detail, dict) else None
            if value and "secureUrls" in str(value):
                raw = value
                break
    if raw is None:
        return None, None

    try:
        secure_image = raw if isinstance(raw, dict) else json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None, "등록증 이미지 정보를 읽지 못했어요. 다시 보내주세요."

    if secure_image.get("privacyAgreement") != "Y":
        return None, "등록증 확인에는 이미지 제공 동의가 필요해요."

    urls = secure_image.get("secureUrls")
    if isinstance(urls, list):
        return (str(urls[0]), None) if urls else (None, "등록증 이미지가 없어요.")
    if isinstance(urls, str):
        match = re.fullmatch(r"List\((.+)\)", urls.strip())
        return (match.group(1) if match else urls.strip()), None
    return None, "등록증 이미지가 없어요."


def _parse_amount(value: str) -> int | None:
    normalized = value.replace(",", "").strip()
    match = re.fullmatch(r"(\d+)\s*만원?", normalized)
    if match:
        return int(match.group(1)) * 10_000
    match = re.fullmatch(r"(\d+)\s*원?", normalized)
    if match:
        return int(match.group(1))
    return None


def _parse_date(value: str) -> str | None:
    if value.strip() == "오늘":
        return date.today().isoformat()
    digits = re.sub(r"\D", "", value)
    if len(digits) != 8:
        return None
    try:
        return date(int(digits[:4]), int(digits[4:6]), int(digits[6:])).isoformat()
    except ValueError:
        return None


def _official_status(official: dict[str, Any]) -> str:
    business_status = official.get("business_status")
    if business_status:
        return str(business_status)
    return {
        "not_configured": "국세청 조회 연결 필요",
        "error": "국세청 조회 실패",
    }.get(str(official.get("status") or ""), "조회 결과 없음")


class KakaoSkillAdapter:
    def __init__(
        self,
        business_service: Any,
        invoice_service: Any,
        conversations: KakaoConversationStore | None = None,
    ) -> None:
        self.business_service = business_service
        self.invoice_service = invoice_service
        self.conversations = conversations or KakaoConversationStore()

    async def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_request = payload.get("userRequest") or {}
        user = user_request.get("user") or {}
        user_id = str(user.get("id") or "")
        utterance = str(user_request.get("utterance") or "").strip()
        extra = (payload.get("action") or {}).get("clientExtra") or {}
        action = str(extra.get("talkcheck_action") or "")
        conversation = self.conversations.get(user_id) if user_id else None

        if utterance == "취소":
            if conversation:
                conversation.invoice_step = None
                conversation.invoice.clear()
            return text_response(
                "세금계산서 준비를 취소했어요. 사업자 확인 결과는 잠시 유지할게요.",
                self._menu_replies(),
            )

        if action == "lookup_business":
            return await self._lookup_business(str(extra.get("business_number") or ""), conversation)
        if action == "start_invoice":
            return self._start_invoice(conversation)
        if action == "reset_business":
            if conversation:
                conversation.business_number = None
                conversation.business_name = None
                conversation.business_check = None
            return text_response("확인할 사업자번호 10자리를 보내주세요.")
        if action == "ask_business_number":
            return text_response("확인할 사업자번호 10자리를 보내주세요.")
        if action == "ask_certificate_image":
            return text_response(
                "등록증 사진 보내기 블록에서 개인정보 제공에 동의한 뒤 사진을 선택해주세요. 이미지는 저장하지 않고 확인에만 사용해요."
            )
        if action == "dismiss":
            return text_response("알겠어요. 필요할 때 다시 번호를 보내주세요.", self._menu_replies())

        image_url, image_error = _secure_image_url(payload)
        if image_error:
            return text_response(image_error, self._menu_replies())
        if image_url:
            return await self._scan_image(image_url, conversation)

        if conversation and conversation.invoice_step:
            return await self._continue_invoice(conversation, utterance)

        if "pdf" in utterance.lower():
            return text_response(
                "PDF 등록증은 아직 채팅에서 바로 읽을 수 없어요. 사진으로 보내거나 사업자번호를 입력해주세요.",
                self._menu_replies(),
            )

        business_number = find_business_number(utterance)
        if "세금계산서" in utterance or "계산서 발행" in utterance:
            if business_number:
                if not is_valid_business_number(business_number):
                    return text_response("사업자번호 체크섬이 맞지 않아요. 번호를 다시 확인해주세요.")
                if conversation:
                    conversation.business_number = business_number
                    conversation.business_name = None
                    conversation.business_check = None
                return text_response(
                    f"{format_business_number(business_number)} 사업자를 먼저 확인할까요?",
                    [
                        _quick_reply(
                            "확인하고 준비",
                            "사업자 확인 후 세금계산서 준비",
                            "lookup_business",
                            business_number=business_number,
                        )
                    ],
                )
            if conversation and conversation.business_number:
                name = conversation.business_name or format_business_number(conversation.business_number)
                return text_response(
                    f"방금 확인한 {name}(으)로 세금계산서 초안을 준비할까요?",
                    [
                        _quick_reply("맞아요", "이 사업자로 세금계산서 준비", "start_invoice"),
                        _quick_reply("다른 업체", "다른 사업자 조회", "reset_business"),
                    ],
                )
            return text_response(
                "좋아요. 먼저 공급받는자의 사업자번호를 보내거나 등록증 사진을 올려주세요.",
                self._menu_replies(),
            )

        if business_number:
            if not is_valid_business_number(business_number):
                return text_response("사업자번호 체크섬이 맞지 않아요. 번호를 다시 확인해주세요.")
            return text_response(
                f"사업자번호 {format_business_number(business_number)}을 확인할까요?",
                [
                    _quick_reply(
                        "조회하기",
                        "사업자 조회하기",
                        "lookup_business",
                        business_number=business_number,
                    ),
                    _quick_reply("나중에", "나중에 확인", "dismiss"),
                ],
            )

        if "등록증" in utterance or "사진" in utterance:
            return text_response(
                "등록증 사진 보내기 블록에서 개인정보 제공에 동의한 뒤 사진을 선택해주세요. 이미지는 저장하지 않고 확인에만 사용해요."
            )

        return text_response(
            "사업자번호 10자리를 보내거나 등록증 사진을 올려주세요. ‘세금계산서 준비’라고 말해도 돼요.",
            self._menu_replies(),
        )

    def _menu_replies(self) -> list[dict[str, Any]]:
        return [
            _quick_reply("사업자번호 조회", "사업자번호 조회", "ask_business_number"),
            _quick_reply("등록증 사진", "등록증 사진 확인", "ask_certificate_image"),
            _quick_reply("계산서 준비", "세금계산서 준비", "ask_invoice"),
        ]

    async def _lookup_business(
        self,
        business_number: str,
        conversation: _Conversation | None,
    ) -> dict[str, Any]:
        result = await self.business_service.check_number(business_number)
        if not result.get("checksum_valid"):
            return text_response("사업자번호 체크섬이 맞지 않아요. 번호를 다시 확인해주세요.")

        if conversation:
            conversation.business_number = result["business_number"]
            conversation.business_check = result
        official = result.get("official_lookup") or {}
        status = _official_status(official)
        tax_type = official.get("tax_type") or "과세유형 정보 없음"
        return _card_response(
            "사업자 확인 결과",
            f"사업자번호 {result['formatted_business_number']}\n상태 {status}\n과세유형 {tax_type}\n\n이 결과는 안전 여부를 판단하지 않아요.",
            [
                _quick_reply("계산서 준비", "이 사업자로 세금계산서 준비", "start_invoice"),
                _quick_reply("다른 사업자", "다른 사업자 조회", "reset_business"),
            ],
        )

    async def _scan_image(
        self,
        image_url: str,
        conversation: _Conversation | None,
    ) -> dict[str, Any]:
        result = await self.business_service.scan_certificate(image_url=image_url)
        extracted = result.get("extracted") or {}
        if result.get("processing_status") != "extracted" or not extracted:
            message = result.get("message") or "등록증에서 사업자번호를 찾지 못했어요. 선명한 사진으로 다시 보내주세요."
            return text_response(message, self._menu_replies())

        business_check = result.get("business_check") or {}
        if conversation:
            conversation.business_number = extracted.get("business_number")
            conversation.business_name = extracted.get("business_name")
            conversation.business_check = business_check
        official = business_check.get("official_lookup") or {}
        status = _official_status(official)
        name = extracted.get("business_name") or "상호 미인식"
        number = business_check.get("formatted_business_number") or format_business_number(
            str(extracted.get("business_number") or "")
        )
        return _card_response(
            "등록증 확인 결과",
            f"상호 {name}\n사업자번호 {number}\n상태 {status}\n\n원본 이미지는 저장하지 않아요.",
            [
                _quick_reply("계산서 준비", "이 사업자로 세금계산서 준비", "start_invoice"),
                _quick_reply("다시 확인", "등록증 사진 확인", "ask_certificate_image"),
            ],
        )

    def _start_invoice(self, conversation: _Conversation | None) -> dict[str, Any]:
        if conversation is None or not conversation.business_number:
            return text_response("먼저 공급받는자의 사업자번호를 확인해주세요.", self._menu_replies())
        conversation.invoice.clear()
        if conversation.business_name:
            conversation.invoice["recipient_name"] = conversation.business_name
            conversation.invoice_step = "item_name"
            prompt = f"공급받는자는 {conversation.business_name}입니다. 품목명을 입력해주세요."
        else:
            conversation.invoice_step = "recipient_name"
            prompt = "공급받는자 상호를 입력해주세요."
        return text_response(prompt, [_quick_reply("취소", "취소", "cancel")])

    async def _continue_invoice(
        self,
        conversation: _Conversation,
        utterance: str,
    ) -> dict[str, Any]:
        if not utterance:
            return text_response("내용을 입력해주세요.")
        step = conversation.invoice_step
        if step == "recipient_name":
            conversation.invoice["recipient_name"] = utterance
            conversation.invoice_step = "item_name"
            return text_response("품목명을 입력해주세요.", [_quick_reply("취소", "취소", "cancel")])
        if step == "item_name":
            conversation.invoice["item_name"] = utterance
            conversation.invoice_step = "supply_amount"
            return text_response(
                "공급가액을 입력해주세요. 예: 1000000원 또는 100만원",
                [_quick_reply("취소", "취소", "cancel")],
            )
        if step == "supply_amount":
            amount = _parse_amount(utterance)
            if amount is None or amount <= 0:
                return text_response("공급가액을 숫자로 입력해주세요. 예: 1000000원")
            conversation.invoice["supply_amount"] = amount
            conversation.invoice_step = "supply_date"
            return text_response(
                "작성일을 입력해주세요. 예: 2026-06-19 또는 오늘",
                [_quick_reply("취소", "취소", "cancel")],
            )
        if step == "supply_date":
            supply_date = _parse_date(utterance)
            if supply_date is None:
                return text_response("작성일을 YYYY-MM-DD 형식으로 입력해주세요.")
            conversation.invoice["supply_date"] = supply_date
            conversation.invoice_step = "recipient_email"
            return text_response(
                "받는 사람 이메일을 입력해주세요. 없으면 ‘없음’이라고 보내주세요.",
                [_quick_reply("없음", "없음", "skip_email"), _quick_reply("취소", "취소", "cancel")],
            )
        if step == "recipient_email":
            if utterance not in {"없음", "건너뛰기"}:
                if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", utterance):
                    return text_response("이메일 형식을 확인해주세요. 예: billing@example.com")
                conversation.invoice["recipient_email"] = utterance
            conversation.invoice_step = "purpose"
            return text_response(
                "대금을 아직 받지 않았다면 청구, 이미 받았다면 영수를 선택해주세요.",
                [
                    _quick_reply("청구", "청구", "purpose_charge"),
                    _quick_reply("영수", "영수", "purpose_receipt"),
                    _quick_reply("취소", "취소", "cancel"),
                ],
            )
        if step == "purpose":
            purpose = "청구" if "청구" in utterance else "영수" if "영수" in utterance else None
            if purpose is None:
                return text_response("청구 또는 영수를 선택해주세요.")
            supply_amount = int(conversation.invoice["supply_amount"])
            result = await self.invoice_service.prepare_handoff(
                recipient_business_number=conversation.business_number,
                recipient_name=conversation.invoice["recipient_name"],
                supply_date=conversation.invoice["supply_date"],
                item_name=conversation.invoice["item_name"],
                supply_amount=supply_amount,
                tax_amount=supply_amount // 10,
                purpose=purpose,
                recipient_email=conversation.invoice.get("recipient_email"),
                business_check=conversation.business_check,
            )
            conversation.invoice_step = None
            handoff = result.get("handoff") or {}
            handoff_url = handoff.get("handoff_url")
            draft = result["draft"]
            description = (
                f"공급받는자 {draft['recipient_name']}\n"
                f"품목 {draft['item_name']}\n"
                f"합계 {draft['total_amount']:,}원\n\n"
                "아직 발행되지 않았어요. 금액과 세액은 확인 화면에서 수정할 수 있습니다."
            )
            if not handoff_url:
                description += "\n현재 발행 확인 링크는 연결되지 않았습니다."
            return _card_response(
                "세금계산서 초안 준비 완료",
                description,
                [_quick_reply("다른 사업자", "다른 사업자 조회", "reset_business")],
                web_link=handoff_url,
            )
        return text_response("세금계산서 준비 상태를 찾지 못했어요. 처음부터 다시 시작해주세요.")
