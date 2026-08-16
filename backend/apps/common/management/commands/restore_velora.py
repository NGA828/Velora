from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.common.backup import restore_backup


class Command(BaseCommand):
    help = "Restore a verified Velora backup. Stop all web and worker processes first."

    def add_arguments(self, parser):
        parser.add_argument("backup_dir", help="Backup directory containing manifest.json.")
        parser.add_argument(
            "--confirm",
            required=True,
            help='Must be exactly "RESTORE" to acknowledge destructive replacement.',
        )

    def handle(self, *args, **options):
        if options["confirm"] != "RESTORE":
            raise CommandError('Restore cancelled: --confirm must be exactly "RESTORE".')
        try:
            manifest = restore_backup(Path(options["backup_dir"]))
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Restore completed from backup created at {manifest['created_at']}. "
                "Run migrations and application checks before restarting services."
            )
        )
