"""Form / validation layer for the Step‑3 wizard."""
from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError

from core.models.report import Report, Competitor


class InputWizardForm(forms.Form):
    your_site = forms.URLField(label="Your website URL", required=True)

    # Competitor 1 (required)
    competitor1_site = forms.URLField(label="Competitor 1 website", required=True)
    competitor1_fb = forms.URLField(label="Competitor 1 Facebook", required=False)
    competitor1_ig = forms.URLField(label="Competitor 1 Instagram", required=False)

    # Competitor 2 (optional)
    competitor2_site = forms.URLField(label="Competitor 2 website", required=False)
    competitor2_fb = forms.URLField(label="Competitor 2 Facebook", required=False)
    competitor2_ig = forms.URLField(label="Competitor 2 Instagram", required=False)

    def clean(self):
        cleaned = super().clean()
        # if social links are supplied for competitor 2, ensure site is provided
        if (cleaned.get("competitor2_fb") or cleaned.get("competitor2_ig")) and not cleaned.get("competitor2_site"):
            raise ValidationError("Provide competitor 2 website if you add its social links.")
        return cleaned

    # ————————————————————————————————————————————
    # Persistence helper
    # ————————————————————————————————————————————
    def save(self, brand):
        """Create Report + Competitor rows and return the Report instance."""
        report = Report.objects.create(owner=brand, your_site=self.cleaned_data["your_site"])

        # Competitor 1
        Competitor.objects.create(
            report=report,
            name="Competitor 1",
            website=self.cleaned_data["competitor1_site"],
            facebook_url=self.cleaned_data.get("competitor1_fb", ""),
            instagram_url=self.cleaned_data.get("competitor1_ig", ""),
        )

        # Competitor 2 (optional)
        if self.cleaned_data.get("competitor2_site"):
            Competitor.objects.create(
                report=report,
                name="Competitor 2",
                website=self.cleaned_data["competitor2_site"],
                facebook_url=self.cleaned_data.get("competitor2_fb", ""),
                instagram_url=self.cleaned_data.get("competitor2_ig", ""),
            )

        return report