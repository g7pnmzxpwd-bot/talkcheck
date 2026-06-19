"""Short-lived opaque handoff records for the confirmation screen."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from talkcheck.domain import TaxInvoiceDraft


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class _HandoffRecord:
    reference_id: str
    draft: TaxInvoiceDraft
    business_check: dict[str, Any]
    created_at: datetime
    expires_at: datetime
    prepared_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_id": self.reference_id,
            "draft": self.draft.to_dict(),
            "business_check": self.business_check,
            "issuance_status": "not_issued",
            "requires_user_confirmation": True,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "prepared_at": self.prepared_at.isoformat() if self.prepared_at else None,
        }


class HandoffStore:
    def __init__(
        self,
        ttl_seconds: int = 30 * 60,
        token_factory: Callable[[], str] | None = None,
        now: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self.now = now
        self._records: dict[str, _HandoffRecord] = {}

    def clear(self) -> None:
        self._records.clear()

    def create(
        self,
        draft: TaxInvoiceDraft,
        business_check: dict[str, Any],
        public_base_url: str,
    ) -> dict[str, Any]:
        reference_id = self.token_factory()
        created_at = self.now()
        self._records[reference_id] = _HandoffRecord(
            reference_id=reference_id,
            draft=draft,
            business_check=business_check,
            created_at=created_at,
            expires_at=created_at + timedelta(seconds=self.ttl_seconds),
        )
        return {
            "handoff_status": "ready",
            "handoff_url": f"{public_base_url.rstrip('/')}/handoff/{reference_id}",
            "reference_id": reference_id,
        }

    def _active_record(self, reference_id: str) -> _HandoffRecord | None:
        record = self._records.get(reference_id)
        if record and record.expires_at <= self.now():
            del self._records[reference_id]
            return None
        return record

    def get(self, reference_id: str) -> dict[str, Any] | None:
        record = self._active_record(reference_id)
        return record.to_dict() if record else None

    def update(self, reference_id: str, draft: TaxInvoiceDraft) -> dict[str, Any] | None:
        record = self._active_record(reference_id)
        if record is None:
            return None
        record.draft = draft
        return record.to_dict()

    def prepare(self, reference_id: str, draft: TaxInvoiceDraft) -> dict[str, Any]:
        record = self._active_record(reference_id)
        if record is None:
            raise KeyError(reference_id)
        record.draft = draft
        record.prepared_at = self.now()
        return {
            "handoff_status": "ready_for_external_confirmation",
            "issuance_status": "not_issued",
            "requires_user_confirmation": True,
            "reference_id": reference_id,
            "draft": draft.to_dict(),
        }
