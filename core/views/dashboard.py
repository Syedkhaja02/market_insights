# core/views/dashboard.py

from __future__ import annotations
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, RedirectView
from utils.kpi import build_kpi_dataframe as compute_kpi_frame
from utils.trends import pct_delta
from core.models.oauth import Brand
from core.models.metrics import MetricSnapshot

class DashboardRedirectView(RedirectView):
    """
    If a user hits “/” and has no report yet, send them to ConnectData.
    """
    pattern_name = "connect_data"

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Shows the KPI dashboard for each Brand the user owns.
    """
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # all Brand workspaces owned by this user
        brands = Brand.objects.filter(user=self.request.user)

        rows: list[dict] = []
        for brand in brands:
            # Build current vs previous KPI frames
            current = compute_kpi_frame(brand.latest_report.id)
            prev_report = getattr(brand.latest_report, "previous", None)
            prev_df = compute_kpi_frame(prev_report.id) if prev_report else None

            # Pick four flagship metrics
            flagship = [
                ("Domain Authority", "domain_authority"),
                ("Sessions", "sessions"),
                ("IG Reach", "ig_reach"),
                ("Conv Rate", "conversion_rate"),
            ]
            cells = []
            for label, key in flagship:
                new_val = current.loc[key, brand.name]
                arrow, pct = "→", 0.0
                if prev_df is not None and key in prev_df.index:
                    old_val = prev_df.loc[key, brand.name]
                    arrow, pct = pct_delta(new_val, old_val)
                cells.append({
                    "label": label,
                    "value": new_val,
                    "arrow": arrow,
                    "pct": pct,
                })

            rows.append({
                "brand": brand.name,
                "cells": cells,
                "report": brand.latest_report,
            })

        ctx["rows"] = rows
        return ctx
