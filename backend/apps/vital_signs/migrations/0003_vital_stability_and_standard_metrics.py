from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


STANDARD_VITAL_METRICS = (
    {
        "code": "TEMP",
        "name": "Body temperature",
        "unit": "°C",
        "decimal_places": 1,
        "display_order": 10,
        "contributes_to_assessment": True,
        "description": "Core body temperature. Primary vital sign.",
    },
    {
        "code": "PULSE",
        "name": "Pulse",
        "unit": "bpm",
        "decimal_places": 0,
        "display_order": 20,
        "contributes_to_assessment": True,
        "description": "Heart beats per minute at rest.",
    },
    {
        "code": "RR",
        "name": "Respiration rate",
        "unit": "breaths/min",
        "decimal_places": 0,
        "display_order": 30,
        "contributes_to_assessment": True,
        "description": "Breaths taken per minute at rest.",
    },
    {
        "code": "SBP",
        "name": "Systolic blood pressure",
        "unit": "mmHg",
        "decimal_places": 0,
        "display_order": 40,
        "contributes_to_assessment": True,
        "description": "Arterial pressure during a heartbeat.",
    },
    {
        "code": "DBP",
        "name": "Diastolic blood pressure",
        "unit": "mmHg",
        "decimal_places": 0,
        "display_order": 50,
        "contributes_to_assessment": True,
        "description": "Arterial pressure between heartbeats.",
    },
    {
        "code": "WT",
        "name": "Body weight",
        "unit": "kg",
        "decimal_places": 1,
        "display_order": 60,
        "contributes_to_assessment": False,
        "description": (
            "Current body weight. Recorded for trending; not scored unless a rule is configured."
        ),
    },
)


def seed_standard_vital_metrics(apps, schema_editor):
    VitalMetric = apps.get_model("vital_signs", "VitalMetric")
    for spec in STANDARD_VITAL_METRICS:
        if VitalMetric.objects.filter(code=spec["code"]).exists():
            continue
        if VitalMetric.objects.filter(name=spec["name"]).exists():
            continue
        VitalMetric.objects.create(**spec)


def unseed_standard_vital_metrics(apps, schema_editor):
    VitalMetric = apps.get_model("vital_signs", "VitalMetric")
    codes = [spec["code"] for spec in STANDARD_VITAL_METRICS]
    VitalMetric.objects.filter(code__in=codes, observed_values__isnull=True, rules__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("vital_signs", "0002_vitalobservation_vitalvalue_vitalruleevaluation_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="vitalmetric",
            name="contributes_to_assessment",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "When false, the measurement is stored (for example body weight) "
                    "but incomplete rule coverage does not mark the observation Unassessed."
                ),
            ),
        ),
        migrations.AddField(
            model_name="vitalmetric",
            name="display_order",
            field=models.PositiveSmallIntegerField(default=100),
        ),
        migrations.AlterModelOptions(
            name="vitalmetric",
            options={"ordering": ["display_order", "name"]},
        ),
        migrations.AlterModelOptions(
            name="vitalvalue",
            options={"ordering": ["metric__display_order", "metric__name"]},
        ),
        migrations.AddField(
            model_name="vitalobservation",
            name="assessed_metric_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="vitalobservation",
            name="critical_metric_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="vitalobservation",
            name="criticality_percent",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[MinValueValidator(0), MaxValueValidator(100)],
            ),
        ),
        migrations.AddField(
            model_name="vitalobservation",
            name="stability_percent",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[MinValueValidator(0), MaxValueValidator(100)],
            ),
        ),
        migrations.RunPython(seed_standard_vital_metrics, unseed_standard_vital_metrics),
    ]
