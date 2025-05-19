"""Models for storing encrypted OAuth tokens and refreshing them on demand."""
from __future__ import annotations
from datetime import timedelta
import requests
from django.conf import settings
from django.db import models
from django.utils import timezone
from fernet_fields import EncryptedTextField

__all__ = [
    "Brand",
    "BrandOAuthToken",
]

class Brand(models.Model):
    """Represents the user’s own brand/workspace."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=128, blank=True)
    website = models.URLField(blank=True, null=True)

    def __str__(self) -> str:
        return self.name or f"Brand<{self.pk}>"


class BrandOAuthToken(models.Model):
    """Encrypted, refreshable token per (brand, provider)."""

    PROVIDER_META = "meta"
    PROVIDER_GA4 = "ga4"
    PROVIDER_SHOPIFY = "shopify"
    PROVIDER_CHOICES = [
        (PROVIDER_META, "Meta (FB/Insta)"),
        (PROVIDER_GA4, "Google Analytics 4"),
        (PROVIDER_SHOPIFY, "Shopify"),
    ]

    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="oauth_tokens")
    provider = models.CharField(max_length=12, choices=PROVIDER_CHOICES)
    access_token = EncryptedTextField()
    refresh_token = EncryptedTextField(blank=True, null=True)
    expires_at = models.DateTimeField()
    scope = models.TextField(blank=True)

    class Meta:
        unique_together = ("brand", "provider")

    def __str__(self):
        return f"{self.brand}:{self.provider}"

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at - timedelta(minutes=5)

    def refresh_if_needed(self):
        if not self.is_expired():
            return  # still valid
        if self.provider == self.PROVIDER_META:
            self._refresh_meta()
        elif self.provider == self.PROVIDER_GA4:
            self._refresh_ga4()
        elif self.provider == self.PROVIDER_SHOPIFY:
            # Shopify tokens do not expire by default – noop
            return
        self.save(update_fields=["access_token", "refresh_token", "expires_at"])

    # ──────────────────────────── provider‑specific flows ─────────────────────────────
    def _refresh_meta(self):
        """Exchange the *long‑lived* token for a new long‑lived token."""
        url = "https://graph.facebook.com/v19.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": settings.META_CLIENT_ID,
            "client_secret": settings.META_CLIENT_SECRET,
            "fb_exchange_token": self.refresh_token,
        }
        data = requests.get(url, params=params, timeout=15).json()
        self.access_token = data["access_token"]
        self.refresh_token = data["access_token"]  # Meta reuses long-lived token
        self.expires_at = timezone.now() + timedelta(seconds=data.get("expires_in", 60 * 60 * 24 * 60))

    def _refresh_ga4(self):
        url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        data = requests.post(url, data=payload, timeout=15).json()
        self.access_token = data["access_token"]
        self.expires_at = timezone.now() + timedelta(seconds=data["expires_in"])
