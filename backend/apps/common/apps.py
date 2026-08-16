import logging

from django.apps import AppConfig
from django.db.backends.signals import connection_created

logger = logging.getLogger(__name__)


def configure_sqlite_connection(sender, connection, **kwargs) -> None:
    if connection.vendor != "sqlite":
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys = ON;")
            cursor.execute("PRAGMA busy_timeout = 20000;")
            if connection.settings_dict.get("NAME") != ":memory:":
                cursor.execute("PRAGMA journal_mode = WAL;")
                cursor.execute("PRAGMA synchronous = NORMAL;")
    except Exception:
        logger.exception("Unable to configure SQLite connection pragmas")


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"
    verbose_name = "Common"

    def ready(self) -> None:
        connection_created.connect(
            configure_sqlite_connection,
            dispatch_uid="velora.configure_sqlite_connection",
        )
