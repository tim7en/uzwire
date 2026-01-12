from __future__ import annotations

from dataclasses import dataclass
from datetime import date


FEATURE_CSV_IMPORT = "csv_import"
FEATURE_DAILY_STRATEGY = "daily_strategy"
FEATURE_HIGH_FREQUENCY = "high_frequency"


@dataclass(frozen=True)
class Plan:
    code: str
    name: str


PLAN_FREE = Plan(code="free", name="Free")
PLAN_PRO = Plan(code="pro", name="Pro")
PLAN_COMMERCIAL = Plan(code="commercial", name="Commercial")


PLAN_FEATURES: dict[str, set[str]] = {
    PLAN_FREE.code: set(),
    PLAN_PRO.code: {FEATURE_DAILY_STRATEGY},
    PLAN_COMMERCIAL.code: {FEATURE_DAILY_STRATEGY, FEATURE_HIGH_FREQUENCY},
}


def plan_has_feature(plan_code: str, feature: str) -> bool:
    return feature in PLAN_FEATURES.get(plan_code, set())


def is_active(paid_until: date | None) -> bool:
    if not paid_until:
        return False
    return paid_until >= date.today()
