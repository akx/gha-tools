from __future__ import annotations

import logging
from pathlib import Path

import click

from gha_tools.action_updater import (
    PinStrategy,
    VersionStrategy,
    get_action_updates_for_path,
)

yaml_extensions = (".yml", ".yaml")

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


@main.command(
    help="Update action versions.",
    context_settings={
        # This is a bit of a hack, but hey...
        "token_normalize_func": lambda x: x.replace("third-party", "third_party"),
    },
)
@click.argument("files", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option("--diff/--no-diff", default=False, help="Print diff.")
@click.option("--write/--no-write", default=False, help="Write changes.")
@click.option(
    "--version-strategy",
    "-s",
    type=click.Choice(VersionStrategy, case_sensitive=False),
    help="Version strategy to use.",
    default=VersionStrategy.MAJOR.value,
)
@click.option(
    "--pin-strategy",
    "--pin",
    type=click.Choice(PinStrategy, case_sensitive=False),
    help="Pinning strategy to use.",
    default=PinStrategy.NONE.value,
)
def autoupdate(
    *,
    files: list[Path],
    diff: bool,
    write: bool,
    version_strategy: VersionStrategy,
    pin_strategy: PinStrategy,
) -> None:
    actual_files = list(find_files(files))

    if not actual_files:
        raise click.UsageError("No files or directories specified.")

    for file in actual_files:
        log.info(f"Updating {file}...")
        result = get_action_updates_for_path(
            file,
            version_strategy=version_strategy,
            pin_strategy=pin_strategy,
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


def find_files(files: list[Path]):
    for file in files:
        if file.is_dir():
            for ext in yaml_extensions:
                yield from file.rglob(f"*{ext}")
        elif file.is_file() and file.suffix in yaml_extensions:
            yield file
        else:
            click.echo(f"Skipping {file} because it is not a YAML file.", err=True)
