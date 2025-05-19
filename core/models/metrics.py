"""MetricSnapshot records every individual KPI pull so we can rewind history.
Each snapshot stores both the *numeric value* we will chart later and the
*raw JSON* response for auditability / recalculation.
"""
from __future__ import annotations

import uuid
from django.db import models
from django.utils import timezone

# Forward import — avoids circular when running migrations
from core.models.oauth import Brand  # pragma: no cover
from core.models.report import Report  # pragma: no cover

__all__ = ["MetricSnapshot"]


class MetricSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # The report that triggered this pull (nullable so we can reuse for trend jobs)
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="snapshots",
        null=True,
        blank=True,
    )

    # Which brand this metric belongs to (user brand or competitor)
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name="snapshots",
    )

    metric_name = models.CharField(max_length=64)
    value = models.FloatField(null=True, blank=True)
    raw_json = models.JSONField()

    fetched_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["brand", "metric_name", "fetched_at"]),
        ]
        unique_together = (
            "brand",
            "metric_name",
            "fetched_at",
        )

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.brand} | {self.metric_name} @ {self.fetched_at:%Y‑%m‑%d %H:%M}"