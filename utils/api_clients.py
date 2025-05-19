"""
Centralised thin-wrapper clients for all external APIs used in Market Insights.

Each client exposes one or two small helper methods that return **plain Python
dicts** with *only* the fields the rest of the code relies on. All low-level
HTTP, auth, paging, retry & error-handling is hidden here so the rest of the
codebase stays clean.

Environment variables expected
──────────────────────────────
MOZ_API_TOKEN                    – OR –  MOZ_ACCESS_ID / MOZ_SECRET
SERPSTACK_API_KEY
DATAFORSEO_B64_CREDENTIALS       (base64("login:password"))
TWITTER_BEARER
MENTION_ACCESS_TOKEN             (OAuth token)
SOCIALBLADE_CLIENT_ID
SOCIALBLADE_TOKEN
GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET   (user OAuth – GA4 & GBP)
GOOGLE_CREDENTIALS                          (svc-acct JSON for GBP optional)
"""

from __future__ import annotations
import os, json, base64, logging, datetime as dt
from typing import Dict, Any, List, Optional

import requests

log = logging.getLogger(__name__)
TIMEOUT = 15


# ─────────────────────────────  shared HTTP helpers ──────────────────────────
def _get(url: str, **kw) -> Dict[str, Any]:
    r = requests.get(url, timeout=TIMEOUT, **kw)
    _raise_for_status(r)
    return r.json()


def _post(url: str, **kw) -> Dict[str, Any]:
    r = requests.post(url, timeout=TIMEOUT, **kw)
    _raise_for_status(r)
    return r.json()


def _raise_for_status(r: requests.Response) -> None:
    try:
        r.raise_for_status()
    except requests.HTTPError as exc:
        log.error("API call failed %s → %s – %s", r.request.method, r.url, r.text[:500])
        raise exc


# ═════════════════════════════  MOZ  ════════════════════════════════════════
class MozClient:
    """Moz Links API v2 (https://moz.com/products/api/links-api)"""

    BASE = "https://lsapi.seomoz.com/v2"

    def __init__(self) -> None:
        self.token = os.getenv("MOZ_API_TOKEN")
        self.access_id = os.getenv("MOZ_ACCESS_ID")
        self.secret = os.getenv("MOZ_SECRET")
        if not (self.token or (self.access_id and self.secret)):
            raise RuntimeError("Configure MOZ_API_TOKEN *or* MOZ_ACCESS_ID / MOZ_SECRET")

    # auth helper ------------------------------------------------------------
    def _auth(self) -> dict:
        if self.token:
            return {"headers": {"x-moz-token": self.token}}
        return {"auth": (self.access_id, self.secret)}

    # endpoints --------------------------------------------------------------
    def domain_authority(self, domain: str) -> int:
        url = f"{self.BASE}/url_metrics"
        payload = {"targets": [domain], "metrics": ["domain_authority"]}
        data = _post(url, json=payload, **self._auth())
        # response shape: {"results":[{"target":"example.com","domain_authority":42.1}]}
        try:
            return int(round(data["results"][0]["domain_authority"]))
        except (KeyError, IndexError):
            raise RuntimeError(f"Unexpected Moz response: {data}")

    def backlinks(self, domain: str) -> int:
        url = f"{self.BASE}/links"
        params = {"target": domain, "limit": 1, "filter": "external"}
        data = _get(url, params=params, **self._auth())
        # response shape: {"total_count":12345,"links":[...]}
        return int(data.get("total_count", 0))


# ═════════════════════════════  SERPSTACK  ══════════════════════════════════
class SerpstackClient:
    BASE = "https://api.serpstack.com/search"

    def __init__(self) -> None:
        self.key = os.getenv("SERPSTACK_API_KEY")
        if not self.key:
            raise RuntimeError("SERPSTACK_API_KEY not set")

    def serp_features(self, query: str, *, gl: str = "us") -> Dict[str, bool]:
        """Return presence of featured-snippet & local-pack for **query**."""
        params = {
            "access_key": self.key,
            "query": query,
            "gl": gl,
            "output": "json",
        }
        data = _get(self.BASE, params=params)
        answer_box = data.get("answer_box") or {}
        has_snippet = bool(answer_box.get("type") == "snippet" or data.get("featured_snippets"))
        has_local_pack = bool(data.get("local_results"))
        return {"featured_snippet": has_snippet, "local_pack": has_local_pack}


# ═════════════════════════════  DATAFORSEO  ═════════════════════════════════
class DataForSEOClient:
    ENDPOINT = (
        "https://api.dataforseo.com/v3/dataforseo_labs/"
        "google/bulk_traffic_estimation/live"
    )

    def __init__(self) -> None:
        cred_b64 = os.getenv("DATAFORSEO_B64_CREDENTIALS")
        if not cred_b64:
            raise RuntimeError("DATAFORSEO_B64_CREDENTIALS (base64 login:pass) missing")
        self.headers = {"Authorization": f"Basic {cred_b64}"}

    def traffic_estimate(
        self,
        domains: List[str] | str,
        *,
        location_code: int = 2840,
        language_code: str = "en"
    ) -> Dict[str, Dict[str, Any]]:
        if isinstance(domains, str):
            domains = [domains]

        payload = [
            {
                "target": d,
                "location_code": location_code,
                "language_code": language_code,
                "item_types": ["organic", "paid"],
            }
            for d in domains
        ]
        data = _post(self.ENDPOINT, json=payload, headers=self.headers)
        try:
            results = data["tasks"][0]["result"]
        except (KeyError, IndexError):
            raise RuntimeError(f"Unexpected DataForSEO response: {data}")

        mapped = {item["target"]: item for item in results}
        # If only one domain requested ⇒ return its metrics directly
        if len(domains) == 1:
            return mapped[domains[0]]
        return mapped


# ═════════════════════════════  TWITTER  ════════════════════════════════════
class TwitterClient:
    BASE = "https://api.twitter.com/2/users/by/username"

    def __init__(self) -> None:
        self.token = os.getenv("TWITTER_BEARER")
        if not self.token:
            raise RuntimeError("TWITTER_BEARER missing")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def public_metrics(self, handle: str) -> Dict[str, Any]:
        handle = handle.lstrip("@")
        url = f"{self.BASE}/{handle}"
        params = {"user.fields": "public_metrics"}
        data = _get(url, headers=self.headers, params=params)
        return data["data"]["public_metrics"]


# ═════════════════════════════  MENTION  ════════════════════════════════════
class MentionClient:
    BASE = "https://api.mention.net/api"

    def __init__(self) -> None:
        self.token = os.getenv("MENTION_ACCESS_TOKEN")
        self.version = "1.21"
        if not self.token:
            raise RuntimeError("MENTION_ACCESS_TOKEN missing")

    def brand_mentions(
        self,
        account_id: str,
        alert_id: str,
        *,
        since_days: int = 7
    ) -> Dict[str, Any]:
        """
        Returns volume + %-positive for the last *since_days* days.
        Caller is responsible for storing account_id / alert_id.
        """
        since = (dt.datetime.utcnow() - dt.timedelta(days=since_days)).isoformat(timespec="seconds") + "Z"
        url = (
            f"{self.BASE}/accounts/{account_id}/alerts/{alert_id}/mentions"
            f"?since={since}"
        )
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept-Version": self.version,
        }
        data = _get(url, headers=headers)
        mentions = data.get("mentions", [])
        volume = len(mentions)
        positive = sum(1 for m in mentions if m.get("tone") == 1)
        pct_positive = round((positive / volume) * 100, 1) if volume else 0.0
        return {"volume": volume, "sentiment_pct": pct_positive}


# ═════════════════════════════  SOCIAL BLADE  ═══════════════════════════════
class SocialBladeClient:
    BASE = "https://business.socialblade.com/api/v1"

    def __init__(self) -> None:
        cid = os.getenv("SOCIALBLADE_CLIENT_ID")
        token = os.getenv("SOCIALBLADE_TOKEN")
        if not (cid and token):
            raise RuntimeError("Set SOCIALBLADE_CLIENT_ID & SOCIALBLADE_TOKEN")
        self.params = {"clientid": cid, "token": token}

    # instagram --------------------------------------------------------------
    def instagram_stats(self, username: str) -> Dict[str, Any]:
        url = f"{self.BASE}/instagram/{username.lstrip('@')}"
        data = _get(url, params=self.params)
        return self._simplify_instagram(data)

    # backwards-compat alias
    instagram_profile = instagram_stats

    # facebook ---------------------------------------------------------------
    def facebook_stats(self, page: str) -> Dict[str, Any]:
        url = f"{self.BASE}/facebook/{page}"
        data = _get(url, params=self.params)
        return self._simplify_facebook(data)

    # helpers ---------------------------------------------------------------
    @staticmethod
    def _simplify_instagram(raw: Dict[str, Any]) -> Dict[str, Any]:
        try:
            stats = raw["data"]["statistics"]["total"]
        except KeyError:
            return {}
        return {
            "followers": stats.get("followers"),
            "growth_30d": stats.get("followers_30_days"),
        }

    @staticmethod
    def _simplify_facebook(raw: Dict[str, Any]) -> Dict[str, Any]:
        try:
            stats = raw["data"]["statistics"]["total"]
        except KeyError:
            return {}
        return {"followers": stats.get("followers")}


# ═════════════════════════════  GA4 (Analytics Data API)  ═══════════════════
class GA4Client:
    API_URL = "https://analyticsdata.googleapis.com/v1/properties/{prop}:runReport"

    def __init__(self, brand):
        from core.models.oauth import BrandOAuthToken  # local import
        token_obj = BrandOAuthToken.objects.filter(brand=brand, provider="ga4").first()
        if not token_obj:
            raise RuntimeError("Brand has no GA4 token")
        token_obj.refresh_if_needed()
        self.access_token = token_obj.access_token
        if not getattr(brand, "ga4_property_id", None):
            raise RuntimeError("brand.ga4_property_id not set")
        self.property_id = str(brand.ga4_property_id)

    def summary(self) -> Dict[str, Any]:
        body = {
            "dateRanges": [{"startDate": "30daysAgo", "endDate": "yesterday"}],
            "metrics": [
                {"name": "sessions"},
                {"name": "totalUsers"},
                {"name": "ecommercePurchases"},
            ],
        }
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = self.API_URL.format(prop=self.property_id)
        data = _post(url, json=body, headers=headers)
        try:
            row = data["rows"][0]["metricValues"]
            sessions = int(row[0]["value"])
            users = int(row[1]["value"])
            purchases = int(row[2]["value"])
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected GA4 response: {data}") from e
        conv_rate = round((purchases / sessions) * 100, 2) if sessions else 0.0
        return {
            "sessions": sessions,
            "users": users,
            "purchases": purchases,
            "conversion_rate": conv_rate,
        }


# ═════════════════════════════  META (IG Insights)  ═════════════════════════
class MetaInsightsClient:
    GRAPH = "https://graph.facebook.com/v19.0"

    def __init__(self, brand):
        from core.models.oauth import BrandOAuthToken
        tok = BrandOAuthToken.objects.filter(brand=brand, provider="meta").first()
        if not tok:
            raise RuntimeError("Brand has no Meta token")
        self.token = tok.access_token
        if not getattr(brand, "instagram_business_id", None):
            raise RuntimeError("brand.instagram_business_id not set")
        self.ig_id = brand.instagram_business_id

    def instagram_insights(self) -> Dict[str, Any]:
        url = f"{self.GRAPH}/{self.ig_id}/insights"
        params = {
            "metric": "reach",
            "period": "days_28",
            "access_token": self.token,
        }
        data = _get(url, params=params)
        try:
            reach_entry = next(
                item for item in data["data"] if item["name"] == "reach"
            )
            reach = reach_entry["values"][-1]["value"]
            return {"reach": reach}
        except (KeyError, StopIteration, IndexError):
            return {}


# ═════════════════════════════  GBP (Reviews)  ══════════════════════════════
class GBPClient:
    REVIEWS_ENDPOINT = "https://mybusiness.googleapis.com/v4/accounts/{acct}/locations/{loc}/reviews"

    def __init__(self, brand):
        creds_path = os.getenv("GOOGLE_CREDENTIALS")
        if not creds_path:
            raise RuntimeError("GOOGLE_CREDENTIALS path missing")
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import AuthorizedSession
        except ImportError as exc:
            raise RuntimeError(
                "google-auth not installed; add to requirements.txt"
            ) from exc
        scopes = ["https://www.googleapis.com/auth/business.manage"]
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
        self.session = AuthorizedSession(creds)
        if "/" not in brand.gbp_location_id:
            raise RuntimeError("brand.gbp_location_id must be 'accountId/locationId'")
        self.account_id, self.location_id = brand.gbp_location_id.split("/", 1)

    def reviews(self) -> Dict[str, Any]:
        url = self.REVIEWS_ENDPOINT.format(acct=self.account_id, loc=self.location_id)
        data = self.session.get(url, timeout=TIMEOUT).json()
        avg = data.get("averageRating")
        cnt = data.get("totalReviewCount")
        if avg is None or cnt is None:
            # fallback: derive from individual reviews list
            reviews = data.get("reviews", [])
            cnt = len(reviews)
            if cnt:
                score = sum(int(rv.get("starRating", "ZERO")[0]) for rv in reviews)
                avg = round(score / cnt, 2)
        return {"rating": avg, "count": cnt}
    
class ShopifyClient:
    """
    Lightweight wrapper around Shopify Admin REST API.
    Requires brand.shopify_shop = "<my-shop>.myshopify.com"
    and a BrandOAuthToken(provider="shopify") with access_token.
    """

    def __init__(self, brand):
        from core.models.oauth import BrandOAuthToken
        token_obj = BrandOAuthToken.objects.filter(
            brand=brand, provider=BrandOAuthToken.PROVIDER_SHOPIFY
        ).first()
        if not token_obj:
            raise RuntimeError("No Shopify token for this brand")
        self.token = token_obj.access_token
        self.shop = brand.shopify_shop
        if not self.shop:
            raise RuntimeError("brand.shopify_shop not set")

    def sales_summary(self) -> Dict[str, Any]:
        """
        Fetches all orders (status=any) in the last 30 days,
        sums total_price to compute revenue and AOV.
        """
        # Use 2024-01 API version; adjust as needed
        endpoint = f"https://{self.shop}/admin/api/2024-01/orders.json"
        params = {
            "status": "any",
            "created_at_min": (requests.utils.datetime.datetime.utcnow()
                               - requests.utils.datetime.timedelta(days=30)
                               ).isoformat() + "Z",
            "fields": "total_price"
        }
        headers = {"X-Shopify-Access-Token": self.token}
        data = _get(endpoint, headers=headers, params=params)

        orders = data.get("orders", [])
        total_revenue = sum(float(o.get("total_price", 0)) for o in orders)
        count = len(orders)
        aov = (total_revenue / count) if count else 0.0

        return {"revenue": round(total_revenue, 2), "aov": round(aov, 2)}