"""Table schemas for the synthetic Hanbit Insurance & Capital data. Single source of truth:
the generator, Terraform tag map and access matrix all derive from SCHEMAS."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Sensitivity = Literal["none", "pii", "health", "credit", "financial"]

REGIONS = ["Seoul", "Busan", "Incheon", "Daegu", "Daejeon", "Gwangju", "Ulsan", "Jeju"]
DOMAINS = ["underwriting", "claims", "lending", "finance", "risk_fraud", "marketing"]


@dataclass(frozen=True)
class Column:
    name: str
    type: str  # Snowflake type
    sensitivity: Sensitivity = "none"


def _c(name: str, type_: str, s: Sensitivity = "none") -> Column:
    return Column(name, type_, s)


SCHEMAS: dict[str, list[Column]] = {
    "underwriting": [
        _c("policy_id", "VARCHAR"), _c("customer_id", "VARCHAR"),
        _c("customer_name", "VARCHAR", "pii"), _c("rrn", "VARCHAR", "pii"),
        _c("phone", "VARCHAR", "pii"), _c("address", "VARCHAR", "pii"),
        _c("region", "VARCHAR"), _c("product", "VARCHAR"),
        _c("annual_premium", "NUMBER(12,0)"), _c("start_date", "DATE"),
    ],
    "claims": [
        _c("claim_id", "VARCHAR"), _c("policy_id", "VARCHAR"), _c("customer_id", "VARCHAR"),
        _c("region", "VARCHAR"), _c("diagnosis_code", "VARCHAR", "health"),
        _c("claim_note", "VARCHAR", "health"), _c("claim_amount", "NUMBER(12,0)"),
        _c("status", "VARCHAR"), _c("filed_date", "DATE"),
    ],
    "lending": [
        _c("loan_id", "VARCHAR"), _c("customer_id", "VARCHAR"),
        _c("customer_name", "VARCHAR", "pii"), _c("rrn", "VARCHAR", "pii"),
        _c("branch", "VARCHAR"), _c("region", "VARCHAR"),
        _c("credit_score", "NUMBER(4,0)", "credit"), _c("annual_income", "NUMBER(14,0)", "credit"),
        _c("loan_amount", "NUMBER(14,0)"), _c("status", "VARCHAR"),
    ],
    "finance": [
        _c("entry_id", "VARCHAR"), _c("account_code", "VARCHAR"), _c("region", "VARCHAR"),
        _c("amount", "NUMBER(16,0)", "financial"), _c("posted_date", "DATE"),
    ],
    "risk_fraud": [
        _c("flag_id", "VARCHAR"), _c("claim_id", "VARCHAR"), _c("customer_id", "VARCHAR"),
        _c("score", "NUMBER(5,2)"), _c("flag_reason", "VARCHAR"),
    ],
    "marketing": [
        _c("segment_id", "VARCHAR"), _c("customer_id", "VARCHAR"), _c("region", "VARCHAR"),
        _c("age_band", "VARCHAR"), _c("campaign", "VARCHAR"), _c("converted", "BOOLEAN"),
    ],
}
