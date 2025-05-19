from django.db import models
from django.contrib.auth import get_user_model
from cryptography.fernet import Fernet
from django.conf import settings

User = get_user_model()

class Brand(models.Model):
    user      = models.ForeignKey(User, on_delete=models.CASCADE)
    name      = models.CharField(max_length=100)
    website   = models.URLField()
    instagram = models.CharField(max_length=100, blank=True)
    facebook  = models.CharField(max_length=100, blank=True)
    twitter   = models.CharField(max_length=100, blank=True)

    # encrypted OAuth refresh tokens (JSON blobs)
    meta_token   = models.BinaryField(null=True, blank=True)
    google_token = models.BinaryField(null=True, blank=True)
    shopify_token = models.BinaryField(null=True, blank=True)

    def _encrypt(self, raw: str) -> bytes:
        key = settings.SECRET_KEY[:32].encode()
        return Fernet(key).encrypt(raw.encode())

    def _decrypt(self, blob: bytes) -> str:
        key = settings.SECRET_KEY[:32].encode()
        return Fernet(key).decrypt(blob).decode()

class MetricSnapshot(models.Model):
    brand        = models.ForeignKey(Brand, on_delete=models.CASCADE)
    metric_name  = models.CharField(max_length=120)
    value        = models.CharField(max_length=120)
    captured_at  = models.DateTimeField(auto_now_add=True)

class Report(models.Model):
    brand         = models.ForeignKey(Brand, on_delete=models.CASCADE)
    html          = models.TextField()
    pdf           = models.FileField(upload_to='reports/')
    generated_at  = models.DateTimeField(auto_now_add=True)