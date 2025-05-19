"""Models for competitor capture and report generation queue."""
from __future__ import annotations
import uuid
from django.db import models
from django.utils import timezone

from .oauth import Brand  # one Brand per logged‑in workspace

class Report(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("ready", "Ready"),
        ("error", "Error"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(Brand, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default="queued")
    ai_insight = models.TextField(blank=True, default="")

    # main site (our brand)
    your_site = models.URLField()

    # JSON blob where Celery drops raw metrics / KPI table once compiled
    data = models.JSONField(default=dict, blank=True)

    # PDF path (filled when WeasyPrint export finishes)
    pdf_path = models.FilePathField(path="reports", match=r".*\.pdf$", null=True, blank=True)

    def __str__(self):
        return f"Report {self.pk} ({self.get_status_display()})"


class Competitor(models.Model):
    """Up‑to‑two competitor rows attached to a Report."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(Report, related_name="competitors", on_delete=models.CASCADE)

    name = models.CharField(max_length=120, default="Competitor")
    website = models.URLField()
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_handle = models.CharField(max_length=60, blank=True)

    def __str__(self):
        return self.website