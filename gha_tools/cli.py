from __future__ import annotations

import logging
from pathlib import Path

import click

from gha_tools.action_updater import VersionStrategy, get_action_updates_for_path

log = logging.getLogger(__name__)


@click.group()
@click.option("--debug/--no-debug", default=False, help="Enable debug logging.")
def main(
    *,
    debug: bool,
):
    logging.basicConfig(
        format="%(message)s",
        level=(logging.DEBUG if debug else logging.INFO),
    )


@main.command(help="Update action versions.")
@click.argument("files", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option("--diff/--no-diff", default=False, help="Print diff.")
@click.option("--write/--no-write", default=False, help="Write changes.")
@click.option(
    "--version-strategy",
    "-s",
    type=click.Choice([vs.value for vs in VersionStrategy]),
    help="Version strategy to use.",
    default=VersionStrategy.MAJOR.value,
)
def autoupdate(
    *,
    files: list[Path],
    diff: bool,
    write: bool,
    version_strategy: str,
) -> None:
    version_strategy = VersionStrategy(version_strategy)
    actual_files = []
    for file in files:
        if file.is_dir():
            actual_files.extend(file.rglob("*.yml"))
        elif file.is_file() and file.suffix == ".yml":
            actual_files.append(file)
        else:
            click.echo(f"Skipping {file} because it is not a YAML file.", err=True)

    if not actual_files:
        raise click.UsageError("No files or directories specified.")

    for file in actual_files:
        log.info(f"Updating {file}...")
        result = get_action_updates_for_path(
            file,
            version_strategy=version_strategy,
        )
        if not result.changes:
            log.info(f"  No changes to {file}.")
            continue
        if diff:
            result.print_diff()
        else:
            for change in result.changes:
                log.info(f"  Update {change.old_spec} -> {change.new_spec}")
        if write:
            result.write()
            log.info("  => Updated %s.", file)
