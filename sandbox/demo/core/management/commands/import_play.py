from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from demo.core.importers import PlayImporter
from django.core.management.base import BaseCommand, CommandError

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    """
    Command to import a play text file into the database.
    """

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            "input_file_path", type=str, help="Path to the play text file"
        )
        parser.add_argument(
            "--title",
            type=str,
            help="Title of the play",
        )
        parser.add_argument(
            "--output-fixture",
            type=str,
            help=(
                "Output fixture file path (if provided, generates fixture instead of "
                "saving to database)"
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse without saving to database",
        )

    def handle(self, *args, **options):  # noqa: ARG002
        if not options.get("title"):
            msg = "Title is required"
            raise CommandError(msg)
        importer = PlayImporter(
            input_file_path=Path(options["input_file_path"]),
            title=options.get("title"),
            output_fixture_path=options.get("output_fixture"),
            dry_run=options.get("dry_run", False),
        )
        if options.get("output_fixture"):
            importer.generate_fixture(Path(options["output_fixture"]))
            self.stdout.write(
                self.style.SUCCESS(f"Fixture generated: {options['output_fixture']}")
            )
            return
        try:
            play, created = importer.run()
        except Exception as e:
            raise CommandError(str(e)) from e
        if options.get("dry_run", False):
            self.stdout.write(self.style.SUCCESS("Dry run completed successfully"))
        else:  # noqa: PLR5501
            if created:
                self.stdout.write(self.style.SUCCESS(f"New play created: {play.title}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Play updated: {play.title}"))
