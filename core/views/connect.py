# core/views/connect.py

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class ConnectDataView(LoginRequiredMixin, TemplateView):
    template_name = "connect_data.html"

    # Stubbed GET handler; in future you’ll swap in real OAuth callbacks here
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
