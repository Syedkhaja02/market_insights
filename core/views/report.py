# core/views/report.py

from __future__ import annotations
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

from core.models.report import Report
from utils.kpi import build_kpi_dataframe

class ReportDetailView(LoginRequiredMixin, View):
    """
    Renders the HTML report or serves the PDF for download/inline.
    """
    def get(self, request, pk: str):
        report = get_object_or_404(Report, pk=pk, owner__user=request.user)
        fmt = request.GET.get("format", "html")
        if fmt == "pdf":
            if not report.pdf_path:
                return HttpResponse("PDF not generated", status=404)
            with open(report.pdf_path, "rb") as fh:
                resp = HttpResponse(fh.read(), content_type="application/pdf")
                resp["Content-Disposition"] = f"inline; filename=report-{pk}.pdf"
                return resp

        # HTML view
        kpi_frame = build_kpi_dataframe(report.id)
        return render(request, "report.html", {"report": report, "kpi_frame": kpi_frame})
