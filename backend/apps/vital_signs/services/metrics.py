from apps.vital_signs.models import VitalMetric

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


def compute_stability_score(
    *, assessed_count: int, critical_count: int
) -> tuple[int | None, int | None]:
    if assessed_count <= 0:
        return None, None
    bounded_critical = min(max(critical_count, 0), assessed_count)
    stability = round((assessed_count - bounded_critical) * 100 / assessed_count)
    return stability, 100 - stability


def ensure_standard_vital_metrics() -> list[VitalMetric]:
    metrics: list[VitalMetric] = []
    for spec in STANDARD_VITAL_METRICS:
        metric = VitalMetric.objects.filter(code=spec["code"]).first()
        if metric is None:
            if VitalMetric.objects.filter(name=spec["name"]).exists():
                continue
            metric = VitalMetric.objects.create(**spec)
        else:
            updates: list[str] = []
            if metric.display_order == 100 and spec["display_order"] != 100:
                metric.display_order = spec["display_order"]
                updates.append("display_order")
            if (
                spec["code"] == "WT"
                and metric.contributes_to_assessment
                and spec["contributes_to_assessment"] is False
            ):
                metric.contributes_to_assessment = False
                updates.append("contributes_to_assessment")
            if not metric.description:
                metric.description = spec["description"]
                updates.append("description")
            if updates:
                metric.save(update_fields=[*updates, "updated_at"])
        if metric is not None:
            metrics.append(metric)
    return metrics
