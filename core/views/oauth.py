from __future__ import annotations
import hmac
import hashlib,  uuid
import requests
from datetime import timedelta
from urllib.parse import urlencode
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from core.models.oauth import Brand, BrandOAuthToken

# Decorator to require login on class-based views
login_req = method_decorator(login_required, name="dispatch")


def _get_or_create_brand(request: HttpRequest) -> Brand:
    """
    Find or create a Brand tied to the current user.
    """
    brand, _ = Brand.objects.get_or_create(
        user=request.user,
        defaults={"name": request.user.username}
    )
    return brand


# ─────────────────────────────────────────────────────────────────────────────
# Meta (Facebook / Instagram) OAuth
# ─────────────────────────────────────────────────────────────────────────────
@login_req
class MetaOAuthStartView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        # Build redirect URI for callback
        redirect_uri = request.build_absolute_uri(reverse("oauth-meta-callback"))
        params = {
            "client_id": settings.META_APP_ID,
            "redirect_uri": redirect_uri,
            "state": str(request.user.pk),
            "scope": "pages_show_list,instagram_basic,instagram_manage_insights,business_management",
            "response_type": "code",
        }
        auth_url = f"https://www.facebook.com/v19.0/dialog/oauth?{urlencode(params)}"
        return redirect(auth_url)


@login_req
class MetaOAuthCallbackView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        # Handle denial or errors
        if "error" in request.GET:
            return HttpResponseBadRequest(request.GET.get("error_description", "OAuth error"))
        code = request.GET.get("code")
        if not code:
            return HttpResponseBadRequest("Missing `code` param")

        # 1) Exchange code for short-lived user token
        redirect_uri = request.build_absolute_uri(reverse("oauth-meta-callback"))
        token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
        params = {
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "redirect_uri": redirect_uri,
            "code": code,
        }
        short_data = requests.get(token_url, params=params, timeout=15).json()

        # 2) Exchange short-lived for long-lived token
        long_params = {
            **params,
            "grant_type": "fb_exchange_token",
            "fb_exchange_token": short_data.get("access_token"),
        }
        long_data = requests.get(token_url, params=long_params, timeout=15).json()

        # 3) Save token and setup Brand
        brand = _get_or_create_brand(request)
        BrandOAuthToken.objects.update_or_create(
            brand=brand,
            provider=BrandOAuthToken.PROVIDER_META,
            defaults={
                "access_token": long_data["access_token"],
                "refresh_token": long_data["access_token"],  # Meta long-lived token
                "expires_at": timezone.now() + timedelta(seconds=long_data.get("expires_in", 0)),
                "scope": params["scope"],
            },
        )
        return redirect("dashboard")


# ─────────────────────────────────────────────────────────────────────────────
# Google Analytics 4 OAuth
# ─────────────────────────────────────────────────────────────────────────────
@login_req
class GA4OAuthStartView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        redirect_uri = request.build_absolute_uri(reverse("oauth-ga4-callback"))
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/analytics.readonly",
            "access_type": "offline",
            "prompt": "consent",
            "state": str(request.user.pk),
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        return redirect(auth_url)


@login_req
class GA4OAuthCallbackView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        if request.GET.get("error"):
            return HttpResponseBadRequest(request.GET.get("error_description", "OAuth error"))
        code = request.GET.get("code")
        if not code:
            return HttpResponseBadRequest("Missing `code` param")

        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": request.build_absolute_uri(reverse("oauth-ga4-callback")),
            "grant_type": "authorization_code",
        }
        data = requests.post(token_url, data=payload, timeout=15).json()

        brand = _get_or_create_brand(request)
        BrandOAuthToken.objects.update_or_create(
            brand=brand,
            provider=BrandOAuthToken.PROVIDER_GA4,
            defaults={
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_at": timezone.now() + timedelta(seconds=data.get("expires_in", 0)),
                "scope": "",  # GA4 scope is implicit
            },
        )
        return redirect("dashboard")


# ─────────────────────────────────────────────────────────────────────────────
# Shopify OAuth
# ─────────────────────────────────────────────────────────────────────────────
@login_req
class ShopifyOAuthStartView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        shop = request.GET.get("shop")
        if not shop:
            return HttpResponseBadRequest("Missing ?shop= parameter")
        redirect_uri = request.build_absolute_uri(reverse("oauth-shopify-callback"))
        params = {
            "client_id": settings.SHOPIFY_API_KEY,
            "scope": "read_orders,read_products,read_analytics",
            "redirect_uri": redirect_uri,
            "state": str(request.user.pk),
        }
        auth_url = f"https://{shop}/admin/oauth/authorize?{urlencode(params)}"
        return redirect(auth_url)


@login_req
class ShopifyOAuthCallbackView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        shop = request.GET.get("shop")
        code = request.GET.get("code")
        hmac_param = request.GET.get("hmac")
        if not all([shop, code, hmac_param]):
            return HttpResponseBadRequest("Missing required OAuth params")

        # Validate HMAC
        query_params = request.GET.dict()
        query_params.pop("hmac")
        message = "&".join(sorted(f"{k}={v}" for k, v in query_params.items()))
        calculated = hmac.new(
            settings.SHOPIFY_API_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(calculated, hmac_param):
            return HttpResponseBadRequest("HMAC validation failed")

        # Exchange for access token
        token_url = f"https://{shop}/admin/oauth/access_token"
        payload = {
            "client_id": settings.SHOPIFY_API_KEY,
            "client_secret": settings.SHOPIFY_API_SECRET,
            "code": code,
        }
        data = requests.post(token_url, json=payload, timeout=15).json()

        brand = _get_or_create_brand(request)
        BrandOAuthToken.objects.update_or_create(
            brand=brand,
            provider=BrandOAuthToken.PROVIDER_SHOPIFY,
            defaults={
                "access_token": data.get("access_token"),
                "refresh_token": None,
                "expires_at": timezone.now() + timedelta(days=3650),
                "scope": data.get("scope", ""),
            },
        )
        # Save shop domain on brand for later API calls
        brand.shopify_shop = shop
        brand.save(update_fields=["shopify_shop"])

        return redirect("dashboard")
# ─────────────────────────────────────────────────────────────────────────────
# Facebook Data Deletion Callback + Status Page
# ─────────────────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class FacebookDataDeletionView(View):
    """
    Facebook will POST here when a user requests data deletion.
    You must respond with exactly:
      { url: '<status_url>', confirmation_code: '<code>' }
    (unquoted keys, or FB will reject it).
    """
    def post(self, request: HttpRequest) -> HttpResponse:
        signed_request = request.POST.get("signed_request")
        if not signed_request:
            return HttpResponseBadRequest("Missing signed_request")

        # -- decode and verify signed_request (HMAC SHA256) --
        encoded_sig, payload = signed_request.split(".", 1)
        sig = encoded_sig.replace("-", "+").replace("_", "/") + "=" * ((4 - len(encoded_sig) % 4) % 4)
        expected = hmac.new(
            settings.META_APP_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).digest()
        if not hmac.compare_digest(base64.b64decode(sig), expected):
            return HttpResponseBadRequest("Invalid signature")

        data = json.loads(base64.b64decode(payload + "=="))
        fb_user_id = data.get("user_id")
        if not fb_user_id:
            return HttpResponseBadRequest("Missing user_id")

        # TODO: enqueue background job to delete all data for fb_user_id

        # Build the URL for the status page
        code = uuid.uuid4().hex
        status_path = reverse("facebook-deletion-status")
        status_url = request.build_absolute_uri(f"{status_path}?code={code}")

        # Facebook requires unquoted JSON keys in this exact format:
        resp = HttpResponse(f"{{ url: '{status_url}', confirmation_code: '{code}' }}",
                            content_type="application/json")
        return resp


class FacebookDeletionStatusView(View):
    """
    Renders a simple HTML page confirming receipt of the deletion request.
    """
    def get(self, request: HttpRequest) -> HttpResponse:
        code = request.GET.get("code", "")
        return render(request, "facebook_deletion_status.html", {"code": code})
