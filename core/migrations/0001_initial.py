# Generated by Django 5.0.14 on 2025-05-15 07:04

import django.db.models.deletion
import django.utils.timezone
import fernet_fields.fields
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Brand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=128)),
                ('website', models.URLField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('status', models.CharField(choices=[('queued', 'Queued'), ('running', 'Running'), ('ready', 'Ready'), ('error', 'Error')], default='queued', max_length=8)),
                ('ai_insight', models.TextField(blank=True, default='')),
                ('your_site', models.URLField()),
                ('data', models.JSONField(blank=True, default=dict)),
                ('pdf_path', models.FilePathField(blank=True, match='.*\\.pdf$', null=True, path='reports')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.brand')),
            ],
        ),
        migrations.CreateModel(
            name='Competitor',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(default='Competitor', max_length=120)),
                ('website', models.URLField()),
                ('facebook_url', models.URLField(blank=True)),
                ('instagram_url', models.URLField(blank=True)),
                ('twitter_handle', models.CharField(blank=True, max_length=60)),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='competitors', to='core.report')),
            ],
        ),
        migrations.CreateModel(
            name='BrandOAuthToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(choices=[('meta', 'Meta (FB/Insta)'), ('ga4', 'Google Analytics 4'), ('shopify', 'Shopify')], max_length=12)),
                ('access_token', fernet_fields.fields.EncryptedTextField()),
                ('refresh_token', fernet_fields.fields.EncryptedTextField(blank=True, null=True)),
                ('expires_at', models.DateTimeField()),
                ('scope', models.TextField(blank=True)),
                ('brand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='oauth_tokens', to='core.brand')),
            ],
            options={
                'unique_together': {('brand', 'provider')},
            },
        ),
        migrations.CreateModel(
            name='MetricSnapshot',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('metric_name', models.CharField(max_length=64)),
                ('value', models.FloatField(blank=True, null=True)),
                ('raw_json', models.JSONField()),
                ('fetched_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('brand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='snapshots', to='core.brand')),
                ('report', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='snapshots', to='core.report')),
            ],
            options={
                'indexes': [models.Index(fields=['brand', 'metric_name', 'fetched_at'], name='core_metric_brand_i_fc16ed_idx')],
                'unique_together': {('brand', 'metric_name', 'fetched_at')},
            },
        ),
    ]
