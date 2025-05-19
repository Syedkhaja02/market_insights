"""KPI calculation helper.

Usage:
    from utils.kpi import build_kpi_dataframe
    df = build_kpi_dataframe(report_id)
"""
from __future__ import annotations
import math
from datetime import date
from typing import Dict, Any

import pandas as pd
from django.db.models import Max, QuerySet, F
from core.models.metrics import MetricSnapshot
from core.models.report import Report, Competitor

# ---------------------------------------------------------------------------
# 1. KPI registry – one entry per KPI row in the PDF template.
# ---------------------------------------------------------------------------

class KPI:
    """Represents one KPI def: metric_name -> callable aggregator -> display units."""

    def __init__(self, key: str, label: str, func):
        self.key = key          # raw metric_name in MetricSnapshot
        self.label = label      # label that will be displayed in the table
        self.func = func        # callable(Series) -> value

    def compute(self, series: pd.Series) -> Any:
        try:
            return self.func(series)
        except Exception:
            return math.nan


_REGISTRY: list[KPI] = [
    KPI("domain_authority", "Domain Authority", lambda s: s.max()),
    KPI("total_backlinks", "Total Backlinks", lambda s: s.max()),
    KPI("estimated_org_visits", "Estimated Organic Visits", lambda s: s.mean()),
    KPI("estimated_paid_visits", "Estimated Paid Visits", lambda s: s.mean()),
    KPI("twitter_followers", "Twitter Followers", lambda s: s.max()),
    KPI("twitter_engagement_rate", "Tweet Engagement %", lambda s: round(s.mean(), 2)),
    KPI("ig_followers", "Instagram Followers", lambda s: s.max()),
    KPI("ig_reach", "IG Reach (30d)", lambda s: s.mean()),
    KPI("ga_sessions", "GA4 Sessions (30d)", lambda s: s.sum()),
    KPI("ga_purchases", "Purchases (30d)", lambda s: s.sum()),
    KPI("ga_conversion_rate", "Conversion Rate %", lambda s: round(s.mean(), 2)),
    KPI("avg_rating", "Google Rating", lambda s: round(s.max(), 2)),
    KPI("review_count", "Review Count", lambda s: s.max()),
    KPI("shopify_revenue", "Revenue (30d)", lambda s: s.sum()),
    KPI("shopify_aov", "Average Order Value", lambda s: round(s.mean(), 2)),
]


# ---------------------------------------------------------------------------
# 2. Public API – build_kpi_dataframe
# ---------------------------------------------------------------------------

def build_kpi_dataframe(report_id: int) -> pd.DataFrame:
    """Return a DataFrame with rows=KPIs and columns=[label, brand, competitor1, competitor2]."""

    report: Report = Report.objects.select_related("brand").get(id=report_id)
    brands = [report.brand] + list(report.competitors.order_by("id"))

    # Pull latest snapshot per metric per brand within the report's pull window.
    qs: QuerySet = (
        MetricSnapshot.objects
        .filter(report_id=report_id)
        .values("brand_id", "metric_name")
        .annotate(latest_pk=Max("id"))
    )

    latest_ids = [row["latest_pk"] for row in qs]
    latest_snaps = MetricSnapshot.objects.filter(id__in=latest_ids)

    # Build a DataFrame keyed by (brand, metric_name)
    df_raw = (
        pd.DataFrame.from_records(latest_snaps.values("brand_id", "metric_name", "value"))
        .pivot(index="metric_name", columns="brand_id", values="value")
    )

    # Create final dataframe
    data = []
    for kpi in _REGISTRY:
        row = [kpi.label]
        metric = df_raw.loc[kpi.key] if kpi.key in df_raw.index else pd.Series(dtype=float)
        for brand in brands:
            val = kpi.compute(metric.get(brand.id, pd.NA)) if not metric.empty else pd.NA
            row.append(val)
        data.append(row)

    columns = ["KPI"] + [b.name for b in brands]
    return pd.DataFrame(data, columns=columns)