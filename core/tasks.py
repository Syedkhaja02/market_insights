from __future__ import annotations
import logging
from typing import Any, Dict, List
from datetime import timedelta

from celery import shared_task, chain, group
from django.utils import timezone
from django.db import transaction

from core.models.oauth import Brand
from core.models.metrics import MetricSnapshot
from core.models.report import Report, Competitor
from utils.api_clients import (
    MozClient,
    SerpstackClient,
    DataForSEOClient,
    TwitterClient,
    MentionClient,
    SocialBladeClient,
    GA4Client,
    MetaInsightsClient,
    GBPClient,
    ShopifyClient,
)

logger = logging.getLogger(__name__)


def _store_snapshot(
    *,
    report: Report | None,
    brand: Brand,
    metric: str,
    value: float | None,
    raw: Dict[str, Any] | None = None,
) -> None:
    """
    Helper to create a MetricSnapshot for a given report & brand.
    """
    MetricSnapshot.objects.create(
        report=report,
        brand=brand,
        metric_name=metric,
        value=value,
        raw_json=raw or {},
        fetched_at=timezone.now(),
    )


@shared_task(name="fetch_public_metrics")
def fetch_public_metrics(report_id: str, brand_id: str) -> None:
    """
    Pull public metrics (SEO, social counts, traffic estimates, mentions) for a brand.
    """
    report = Report.objects.filter(id=report_id).first()
    brand = Brand.objects.get(id=brand_id)

    moz = MozClient()
    serp = SerpstackClient()
    dfs = DataForSEOClient()
    tw = TwitterClient()
    men = MentionClient()
    sb = SocialBladeClient()

    # 1) Domain Authority & Backlinks (Moz)
    da = moz.domain_authority(brand.website)
    _store_snapshot(report=report, brand=brand, metric="domain_authority", value=da, raw=None)
    bl = moz.backlinks(brand.website)
    _store_snapshot(report=report, brand=brand, metric="backlinks", value=bl, raw=None)

    # 2) SERP features (featured snippet & local pack)
    serp_data = serp.serp_features(brand.name or brand.website)
    _store_snapshot(report=report, brand=brand, metric="serp_featured_snippet", value=int(serp_data["featured_snippet"]), raw=serp_data)
    _store_snapshot(report=report, brand=brand, metric="serp_local_pack", value=int(serp_data["local_pack"]), raw=serp_data)

    # 3) Traffic Estimates (DataForSEO)
    traffic = dfs.traffic_estimate(brand.website)
    _store_snapshot(report=report, brand=brand, metric="est_organic_visits", value=traffic.get("organic"), raw=traffic)
    _store_snapshot(report=report, brand=brand, metric="est_paid_visits", value=traffic.get("paid"), raw=traffic)

    # 4) Twitter followers
    if brand.twitter:
        tw_data = tw.public_metrics(brand.twitter)
        _store_snapshot(report=report, brand=brand, metric="twitter_followers", value=tw_data.get("followers_count"), raw=tw_data)

    # 5) SocialBlade Instagram & Facebook
    if brand.instagram:
        ig_data = sb.instagram_stats(brand.instagram)
        _store_snapshot(report=report, brand=brand, metric="instagram_followers", value=ig_data.get("followers"), raw=ig_data)
        _store_snapshot(report=report, brand=brand, metric="instagram_growth_30d", value=ig_data.get("growth_30d"), raw=ig_data)
    if brand.facebook_page:
        fb_data = sb.facebook_stats(brand.facebook_page)
        _store_snapshot(report=report, brand=brand, metric="facebook_followers", value=fb_data.get("followers"), raw=fb_data)

    # 6) Mention.com sentiment & volume
    if getattr(brand, "mention_account_id", None) and getattr(brand, "mention_alert_id", None):
        men_data = men.brand_mentions(brand.mention_account_id, brand.mention_alert_id)
        _store_snapshot(report=report, brand=brand, metric="mentions_volume", value=men_data["volume"], raw=men_data)
        _store_snapshot(report=report, brand=brand, metric="mentions_sentiment", value=men_data["sentiment_pct"], raw=men_data)


@shared_task(name="fetch_private_metrics")
def fetch_private_metrics(report_id: str, brand_id: str) -> None:
    """
    Pull private metrics (GA4, IG reach, GBP reviews, Shopify) for a brand.
    """
    report = Report.objects.filter(id=report_id).first()
    brand = Brand.objects.get(id=brand_id)

    # GA4 analytics
    ga4 = GA4Client(brand)
    ga4_data = ga4.summary()
    for key, val in ga4_data.items():
        _store_snapshot(report=report, brand=brand, metric=f"ga4_{key}", value=val, raw=ga4_data)

    # Instagram Business insights
    if getattr(brand, "instagram_business_id", None):
        meta = MetaInsightsClient(brand)
        ig_ins = meta.instagram_insights()
        _store_snapshot(report=report, brand=brand, metric="ig_reach", value=ig_ins.get("reach"), raw=ig_ins)

    # Google Business Profile reviews
    if getattr(brand, "gbp_location_id", None):
        gbp = GBPClient(brand)
        gbp_data = gbp.reviews()
        _store_snapshot(report=report, brand=brand, metric="gbp_avg_rating", value=gbp_data.get("rating"), raw=gbp_data)
        _store_snapshot(report=report, brand=brand, metric="gbp_review_count", value=gbp_data.get("count"), raw=gbp_data)

    # Shopify sales
    if getattr(brand, "shopify_shop", None):
        shop = ShopifyClient(brand)
        shop_data = shop.sales_summary()
        _store_snapshot(report=report, brand=brand, metric="shopify_rev", value=shop_data.get("revenue"), raw=shop_data)
        _store_snapshot(report=report, brand=brand, metric="shopify_aov", value=shop_data.get("aov"), raw=shop_data)


@shared_task(name="start_report_generation")
def start_report_generation(report_id: str) -> str:
    """
    Orchestrates the end-to-end workflow: public metrics → private metrics → PDF → AI insight.
    """
    report = Report.objects.get(id=report_id)
    brand = report.owner

    # Build public jobs for brand + competitors
    public_jobs: List = [fetch_public_metrics.s(report_id, brand.id)]
    for comp in report.competitors.all():
        public_jobs.append(fetch_public_metrics.s(report_id, comp.brand.id))

    workflow = chain(
        group(public_jobs),
        fetch_private_metrics.s(report_id, brand.id),
        # finalise_report and generate_ai_insight are imported lazily below
        finalise_report.s(report_id),
        generate_ai_insight.s(report_id),
    )
    workflow.apply_async()

    report.status = Report.Status.COLLECTING
    report.save(update_fields=["status"])
    return report.id


# Avoid circular import; import at module end
from core.tasks import finalise_report, generate_ai_insight  # noqa: E402
