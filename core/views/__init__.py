# core/views/__init__.py

from core.views.connect import ConnectDataView
from core.views.dashboard import DashboardView, DashboardRedirectView
from core.views.input import InputFormView, InputWizardView
from core.views.oauth import (
    MetaOAuthStartView, MetaOAuthCallbackView,
    GA4OAuthStartView, GA4OAuthCallbackView,
    ShopifyOAuthStartView, ShopifyOAuthCallbackView,
    FacebookDataDeletionView, FacebookDeletionStatusView,
)
from core.views.report import ReportDetailView
