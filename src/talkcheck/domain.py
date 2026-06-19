"""Domain values shared by TalkCheck services and MCP tools."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class BusinessCertificate:
    business_number: str
    opening_date: str | None = None
    representative_name: str | None = None
    representative_name_2: str | None = None
    business_name: str | None = None
    corporate_number: str | None = None
    business_sector: str | None = None
    business_type: str | None = None
    business_address: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaxInvoiceDraft:
    recipient_business_number: str
    recipient_name: str
    supply_date: date
    item_name: str
    supply_amount: int
    tax_amount: int
    purpose: str
    recipient_email: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["supply_date"] = self.supply_date.isoformat()
        result["total_amount"] = self.supply_amount + self.tax_amount
        result["issue_type"] = "정발행"
        return result

