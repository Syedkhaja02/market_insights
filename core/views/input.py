# core/views/input.py

from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin

from core.forms.input_form import InputWizardForm
from core.models.oauth import Brand
from core.views.oauth import _get_or_create_brand


class InputFormView(LoginRequiredMixin, View):
    """
    Simple form view to collect the two competitor URLs (and optional socials)
    """
    template_name = "input_form.html"

    def get(self, request):
        form = InputWizardForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = InputWizardForm(request.POST)
        if form.is_valid():
            # 1) ensure there's a Brand tied to this user:
            brand = _get_or_create_brand(request)
            # 2) form.save() will create Report + Competitor rows under that Brand
            report = form.save(brand)
            # 3) redirect to the “report queued” page
            return redirect("report_queued")
        return render(request, self.template_name, {"form": form})


class InputWizardView(InputFormView):
    """
    Alias for backward compatibility (if you ever need a separate wizard URL).
    """
    pass
