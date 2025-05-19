# core/views/privacy_and_deletion.py
from __future__ import annotations
import hmac
import hashlib
import base64
import json

from django.conf import settings
from django.http import (
    HttpRequest, HttpResponse, HttpResponseBadRequest, JsonResponse
)
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, View


class PrivacyPolicyView(TemplateView):
    template_name = "privacy_policy.html"


class FacebookDataDeletionInstructionsView(TemplateView):
    template_name = "facebook_data_deletion_instructions.html"


@method_decorator(csrf_exempt, name="dispatch")
class FacebookDataDeletionCallbackView(View):
    def post(self, request: HttpRequest) -> HttpResponse:
        signed_request = request.POST.get("signed_request")
        if not signed_request:
            return HttpResponseBadRequest("Missing signed_request parameter.")

        try:
            encoded_sig, payload = signed_request.split(".", 1)
            sig = base64.urlsafe_b64decode(encoded_sig + "==")
            data = json.loads(base64.urlsafe_b64decode(payload + "=="))
        except Exception:
            return HttpResponseBadRequest("Invalid signed_request.")

        expected = hmac.new(
            settings.META_APP_SECRET.encode(),
            msg=payload.encode(),
            digestmod=hashlib.sha256
        ).digest()
        if not hmac.compare_digest(sig, expected):
            return HttpResponseBadRequest("Invalid signature.")

        user_id = data.get("user_id")
        deletion_request_id = user_id
        completion_url = request.build_absolute_uri(
            f"{reverse('facebook_data_deletion_complete')}?deletion_request_id={deletion_request_id}"
        )

        return JsonResponse({"url": completion_url})


@method_decorator(csrf_exempt, name="dispatch")
class FacebookDataDeletionCompleteView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        # Here you'd check if deletion_request_id is processed.
        return JsonResponse({"status": "complete"})
