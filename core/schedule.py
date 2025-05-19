"""Central place to register Celery beat entries."""
from __future__ import annotations
from datetime import timedelta
from celery.schedules import crontab

def register(celery_app):
    # Run every Monday at 03:00 UTC
    celery_app.conf.beat_schedule.update({
        "weekly_metric_refresh": {
            "task": "core.tasks.refresh_all_reports",
            "schedule": crontab(hour=3, minute=0, day_of_week="mon"),
        },
    })