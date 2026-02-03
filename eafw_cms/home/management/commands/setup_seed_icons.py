"""
Management command to copy seed icons to the media directory.

This ensures vector tile icons are available in the media folder
for MapLibre to load.

Usage:
    python manage.py setup_seed_icons
"""
import os
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Copy seed icons to media directory for MapLibre"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing icons",
        )

    def handle(self, *args, **options):
        force = options["force"]

        # Source: baked into Docker image at /home/app/docker/cms/seed/icons
        # or during development at docker/cms/seed/icons
        seed_icons_paths = [
            Path("/home/app/docker/cms/seed/icons"),  # Docker container path
            Path(settings.BASE_DIR) / "docker" / "cms" / "seed" / "icons",  # Dev path
        ]

        seed_icons_dir = None
        for path in seed_icons_paths:
            if path.exists():
                seed_icons_dir = path
                break

        if not seed_icons_dir:
            self.stdout.write(
                self.style.ERROR(
                    f"Seed icons directory not found. Checked: {seed_icons_paths}"
                )
            )
            return

        # Destination: media/vector_tile_icons
        media_root = Path(settings.MEDIA_ROOT)
        dest_dir = media_root / "vector_tile_icons"

        self.stdout.write(f"Source: {seed_icons_dir}")
        self.stdout.write(f"Destination: {dest_dir}")

        # Create destination directory
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Copy icons
        copied = 0
        skipped = 0
        for icon_file in seed_icons_dir.glob("*"):
            if icon_file.is_file():
                dest_file = dest_dir / icon_file.name
                if dest_file.exists() and not force:
                    skipped += 1
                    self.stdout.write(f"  Skipped (exists): {icon_file.name}")
                else:
                    shutil.copy2(icon_file, dest_file)
                    copied += 1
                    self.stdout.write(f"  Copied: {icon_file.name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Icons setup complete. Copied: {copied}, Skipped: {skipped}"
            )
        )

        # Verify icons exist
        expected_icons = ["emergency.png", "alarm.png", "warning.png", "normal.png"]
        missing = []
        for icon in expected_icons:
            if not (dest_dir / icon).exists():
                missing.append(icon)

        if missing:
            self.stdout.write(
                self.style.WARNING(f"Missing icons: {', '.join(missing)}")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("All required icons present")
            )
