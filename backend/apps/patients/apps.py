from django.apps import AppConfig


class PatientsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.patients"
    verbose_name = "Patients"

    def ready(self) -> None:
        from apps.patients import event_handlers  # noqa: F401
