# core/forms/input_form.py
from __future__ import annotations
from django import forms
from django.core.exceptions import ValidationError
from core.models.report import Report, Competitor

class InputWizardForm(forms.Form):
    your_site = forms.URLField(label="Your website URL", required=True)

    competitor1_site = forms.URLField(label="Competitor 1 Website", required=True)
    competitor1_fb = forms.URLField(label="Competitor 1 Facebook", required=False)
    competitor1_ig = forms.URLField(label="Competitor 1 Instagram", required=False)

    competitor2_site = forms.URLField(label="Competitor 2 Website", required=False)
    competitor2_fb = forms.URLField(label="Competitor 2 Facebook", required=False)
    competitor2_ig = forms.URLField(label="Competitor 2 Instagram", required=False)

    def clean(self):
        cleaned = super().clean()
        if (cleaned.get("competitor2_fb") or cleaned.get("competitor2_ig")) and not cleaned.get("competitor2_site"):
            raise ValidationError("Provide competitor 2 website if you add its social links.")
        return cleaned

    def save(self, brand):
        report = Report.objects.create(owner=brand, your_site=self.cleaned_data["your_site"])

        Competitor.objects.create(
            report=report,
            name="Competitor 1",
            website=self.cleaned_data["competitor1_site"],
            facebook_url=self.cleaned_data.get("competitor1_fb", ""),
            instagram_url=self.cleaned_data.get("competitor1_ig", "")
        )

        if self.cleaned_data.get("competitor2_site"):
            Competitor.objects.create(
                report=report,
                name="Competitor 2",
                website=self.cleaned_data["competitor2_site"],
                facebook_url=self.cleaned_data.get("competitor2_fb", ""),
                instagram_url=self.cleaned_data.get("competitor2_ig", "")
            )

        return report
