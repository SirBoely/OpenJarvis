from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Mapping


@dataclass(frozen=True)
class EvidenceRecord:
    source: str
    domain: str
    observed_at: datetime
    payload: Mapping[str, Any]
    confidence: float = 1.0

    def age_seconds(self, now: datetime | None = None) -> float:
        now = now or datetime.now(timezone.utc)
        observed = self.observed_at
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        return max(0.0, (now - observed).total_seconds())


class EvidenceRegistry:
    """Normalizes multi-source evidence and fails closed on stale/missing critical domains."""

    DEFAULT_MAX_AGE_SECONDS = {
        "github": 3600,
        "supabase": 900,
        "shopify": 900,
        "pmo": 3600,
        "finance": 3600,
        "compliance": 86400,
    }

    def __init__(self, max_age_seconds: Mapping[str, int] | None = None) -> None:
        self.max_age_seconds = dict(self.DEFAULT_MAX_AGE_SECONDS)
        if max_age_seconds:
            self.max_age_seconds.update({k: int(v) for k, v in max_age_seconds.items()})
        self._records: Dict[str, EvidenceRecord] = {}

    def put(self, record: EvidenceRecord) -> None:
        self._records[record.domain] = record

    def get(self, domain: str) -> EvidenceRecord | None:
        return self._records.get(domain)

    def readiness(self, required_domains: Iterable[str], now: datetime | None = None) -> Dict[str, Any]:
        missing: list[str] = []
        stale: list[str] = []
        low_confidence: list[str] = []
        for domain in required_domains:
            record = self._records.get(domain)
            if record is None:
                missing.append(domain)
                continue
            max_age = self.max_age_seconds.get(domain, 3600)
            if record.age_seconds(now) > max_age:
                stale.append(domain)
            if float(record.confidence) < 0.8:
                low_confidence.append(domain)
        gate = "PASS" if not (missing or stale or low_confidence) else "BLOCK"
        return {
            "gate": gate,
            "missing": missing,
            "stale": stale,
            "low_confidence": low_confidence,
            "available": sorted(self._records),
        }


class ContextPackBuilder:
    """Builds a compact executive context pack from normalized evidence."""

    def build(self, registry: EvidenceRegistry) -> Dict[str, Any]:
        def payload(domain: str) -> Mapping[str, Any]:
            record = registry.get(domain)
            return record.payload if record else {}

        shopify = payload("shopify")
        finance = payload("finance")
        github = payload("github")
        supabase = payload("supabase")
        compliance = payload("compliance")
        pmo = payload("pmo")

        return {
            "capital": {
                "margin_pct": float(finance.get("margin_pct", shopify.get("margin_pct", 0.0))),
                "cash_buffer_months": float(finance.get("cash_buffer_months", 0.0)),
            },
            "engineering": {
                "data_quality": float(supabase.get("data_quality", pmo.get("data_quality", 0.0))),
                "ci_pass_rate": float(github.get("ci_pass_rate", 0.0)),
            },
            "trust": {
                "compliance_coverage": float(compliance.get("coverage", 0.0)),
                "critical_risks": int(compliance.get("critical_risks", 0)),
            },
            "commerce": dict(shopify),
            "pmo": dict(pmo),
        }
