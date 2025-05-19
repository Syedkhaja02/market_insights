# core/urls.py

from django.urls import path, include
from django.views.generic import TemplateView

from core.views.input import InputFormView, InputWizardView
from core.views.report import ReportDetailView
from core.views.dashboard import DashboardView, DashboardRedirectView
from core.views.oauth import (
    MetaOAuthStartView, MetaOAuthCallbackView,
    GA4OAuthStartView, GA4OAuthCallbackView,
    ShopifyOAuthStartView, ShopifyOAuthCallbackView,
)
from core.views.privacy_and_deletion import (
    PrivacyPolicyView,
    FacebookDataDeletionInstructionsView,
    FacebookDataDeletionCallbackView,
    FacebookDataDeletionCompleteView,
)

urlpatterns = [
    # step flow
    path("", DashboardRedirectView.as_view(), name="home"),
    path("connect/", TemplateView.as_view(template_name="connect_data.html"), name="connect_data"),
    path("input/", InputFormView.as_view(), name="input_form"),
    path("wizard/", InputWizardView.as_view(), name="input_wizard"),
    path("report/queued/", TemplateView.as_view(template_name="report_queued.html"), name="report_queued"),
    path("reports/<uuid:pk>/", ReportDetailView.as_view(), name="report_detail"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),

    # OAuth
    path("oauth/meta/start/", MetaOAuthStartView.as_view(), name="oauth-meta-start"),
    path("oauth/callback/meta/", MetaOAuthCallbackView.as_view(), name="oauth-meta-callback"),
    path("oauth/ga4/start/", GA4OAuthStartView.as_view(), name="oauth-ga4-start"),
    path("oauth/callback/ga4/", GA4OAuthCallbackView.as_view(), name="oauth-ga4-callback"),
    path("oauth/shopify/start/", ShopifyOAuthStartView.as_view(), name="oauth-shopify-start"),
    path("oauth/callback/shopify/", ShopifyOAuthCallbackView.as_view(), name="oauth-shopify-callback"),

    # Privacy & Data Deletion
    path("privacy/", PrivacyPolicyView.as_view(), name="privacy_policy"),
    path("facebook/data-deletion/", FacebookDataDeletionInstructionsView.as_view(), name="facebook_data_deletion"),
    path("facebook/data-deletion-callback/", FacebookDataDeletionCallbackView.as_view(), name="facebook_data_deletion_callback"),
    path("facebook/data-deletion-complete/", FacebookDataDeletionCompleteView.as_view(), name="facebook_data_deletion_complete"),
]
