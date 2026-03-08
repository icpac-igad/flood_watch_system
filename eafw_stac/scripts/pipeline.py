#!/usr/bin/env python3
"""
Modular one-shot pipeline for FloodWatch STAC bootstrap.

This keeps container init predictable by running explicit stages:
1) prepare rasters (clipping)
2) convert static rasters to COG + STAC items
3) load collections/items into STAC API
4) catalog cleanup/sync defaults
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

import click

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lib.settings import ScriptSettings

LOGGER = logging.getLogger("stac_pipeline")
SETTINGS = ScriptSettings()


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _run_step(label: str, argv: list[str]) -> None:
    LOGGER.info("Running step: %s", label)
    LOGGER.debug("Command: %s", " ".join(argv))
    try:
        subprocess.run(argv, check=True)
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(f"{label} failed with exit code {exc.returncode}") from exc


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
def cli(verbose: bool) -> None:
    """STAC bootstrap pipeline."""
    _setup_logging(verbose)


@cli.command("bootstrap")
@click.option("--skip-prepare", is_flag=True, help="Skip raster preparation stage.")
@click.option("--skip-convert", is_flag=True, help="Skip static COG conversion stage.")
@click.option("--skip-ingest", is_flag=True, help="Skip STAC ingest stage.")
@click.option("--skip-sync", is_flag=True, help="Skip catalog sync/cleanup stage.")
@click.option("--api-url", default=SETTINGS.stac_api_url, show_default=True, help="STAC API base URL.")
@click.option(
    "--cmorph-item-file",
    default=str(SETTINGS.cmorph_item_file),
    show_default=True,
    help="CMORPH item file path for catalog sync.",
)
def bootstrap(
    skip_prepare: bool,
    skip_convert: bool,
    skip_ingest: bool,
    skip_sync: bool,
    api_url: str,
    cmorph_item_file: str,
) -> None:
    """Run all bootstrap stages in canonical order."""
    python = sys.executable

    if not skip_prepare:
        _run_step("prepare_rasters", [python, str(SCRIPT_DIR / "prepare_rasters.py")])

    if not skip_convert:
        _run_step("convert_static_cogs", [python, str(SCRIPT_DIR / "convert_static_cogs.py")])

    if not skip_ingest:
        _run_step(
            "ingest_load_all",
            [
                python,
                str(SCRIPT_DIR / "ingest.py"),
                "load-all",
                "--collections-dir",
                str(SETTINGS.collections_dir),
                "--items-dir",
                str(SETTINGS.items_dir),
                "--api-url",
                api_url,
            ],
        )

    if not skip_sync:
        _run_step(
            "catalog_sync_defaults",
            [
                python,
                str(SCRIPT_DIR / "catalog_sync.py"),
                "--api-url",
                api_url,
                "sync-defaults",
                "--cmorph-item-file",
                cmorph_item_file,
            ],
        )

    LOGGER.info("STAC bootstrap pipeline completed.")


@cli.command("audit")
@click.option("--api-url", default=SETTINGS.stac_api_url, show_default=True, help="STAC API base URL.")
def audit(api_url: str) -> None:
    """Run catalog audit only."""
    _run_step(
        "catalog_audit",
        [
            sys.executable,
            str(SCRIPT_DIR / "catalog_sync.py"),
            "--api-url",
            api_url,
            "audit",
        ],
    )


if __name__ == "__main__":
    cli()

