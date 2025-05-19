from django.views.generic import TemplateView, FormView, RedirectView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .forms import InputForm

class DashboardRedirectView(RedirectView):
    pattern_name = 'connect_data'

class ConnectDataView(LoginRequiredMixin, TemplateView):
    template_name = 'connect_data.html'

    # real OAuth URLs for Meta/Google will redirect back here with ?code=...
    # Stub logic – in next sprint we exchange the code for tokens
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class InputFormView(LoginRequiredMixin, FormView):
    template_name = 'input_form.html'
    form_class    = InputForm
    success_url   = reverse_lazy('home')  # will redirect to report once implemented

    def form_valid(self, form):
        # TODO: trigger Celery tasks to fetch metrics & create report
        # tasks.generate_report.delay(self.request.user.id, form.cleaned_data)
        return super().form_valid(form)