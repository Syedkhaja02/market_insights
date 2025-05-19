import pytest, json, importlib
from django.urls import reverse
from django.utils import timezone

from core.models.oauth import BrandOAuthToken

pytestmark = pytest.mark.django_db


class DummyResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def patch_requests(monkeypatch, payload):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **kw: DummyResp(payload))
    monkeypatch.setattr(requests, "post", lambda *a, **kw: DummyResp(payload))


def test_meta_callback_creates_token(client, django_user_model, monkeypatch):
    user = django_user_model.objects.create_user("u", "u@example.com", "pw")
    client.force_login(user)
    patch_requests(
        monkeypatch,
        {
            "access_token": "TEST_ACCESS_TOKEN",
            "expires_in": 3600,
        },
    )
    resp = client.get(
        reverse("oauth-meta-callback"),
        {"code": "dummy", "state": str(user.pk)},
        follow=True,
    )
    assert resp.status_code == 200
    assert BrandOAuthToken.objects.filter(brand__user=user, provider="meta").exists()