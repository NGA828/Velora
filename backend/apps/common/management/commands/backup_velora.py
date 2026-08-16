from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.common.backup import create_backup


class Command(BaseCommand):
    help = "Create a checksummed SQLite and protected-media backup."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default="backups",
            help="Parent directory where a timestamped backup is created.",
        )

    def handle(self, *args, **options):
        try:
            backup_dir = create_backup(Path(options["output_dir"]))
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Backup created: {backup_dir}"))
