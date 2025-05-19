import pandas as pd
from django.test import TestCase

from core.models.oauth import Brand
from core.models.report import Report, Competitor
from core.models.metrics import MetricSnapshot
from utils.kpi import build_kpi_dataframe

class KPITest(TestCase):
    def setUp(self):
        # Create brands
        self.catmer = Brand.objects.create(name="CatMer")
        self.comp1 = Brand.objects.create(name="Comp‑A")
        self.report = Report.objects.create(brand=self.catmer)
        Competitor.objects.create(report=self.report, brand=self.comp1)

        # Minimal snapshots
        MetricSnapshot.objects.create(report=self.report, brand=self.catmer,
                                      metric_name="domain_authority", value=45)
        MetricSnapshot.objects.create(report=self.report, brand=self.comp1,
                                      metric_name="domain_authority", value=38)

    def test_dataframe_shape(self):
        df = build_kpi_dataframe(self.report.id)
        self.assertEqual(df.shape[0], len(df))  # rows defined by registry
        self.assertIn("Domain Authority", df["KPI"].tolist())

    def test_values(self):
        df = build_kpi_dataframe(self.report.id)
        da_row = df[df["KPI"] == "Domain Authority"].iloc[0]
        self.assertEqual(da_row["CatMer"], 45)
        self.assertEqual(da_row["Comp‑A"], 38)