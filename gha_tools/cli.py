from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import cast

import click

from gha_tools.action_updater import (
    ActionUpdateConfig,
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
        "token_normalize_func": lambda x: x.replace(
            "third-party",
            "third_party",
        ).replace("first-party", "first_party"),
    },
)
@click.argument("files", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option("--diff/--no-diff", default=False, help="Print diff.")
@click.option("--write/--no-write", default=False, help="Write changes.")
@click.option(
    "--version-strategy",
    "-s",
    type=click.Choice(VersionStrategy, case_sensitive=False),
    help="Version strategy to use for both first-party and third-party actions.",
    default=None,
)
@click.option(
    "--first-party-version-strategy",
    type=click.Choice(VersionStrategy, case_sensitive=False),
    help="Version strategy to use for first-party actions.",
    default=None,
)
@click.option(
    "--third-party-version-strategy",
    type=click.Choice(VersionStrategy, case_sensitive=False),
    help="Version strategy to use for third-party actions.",
    default=None,
)
@click.option(
    "--pin-strategy",
    "--pin",
    type=click.Choice(PinStrategy, case_sensitive=False),
    help="Pinning strategy to use.",
    default=PinStrategy.NONE.value,
)
@click.option(
    "--first-party-pattern",
    type=str,
    help="Regular expression pattern to match first-party actions (default: %(default)s).",
    default=r"^(actions|github)/",
)
def autoupdate(
    *,
    files: list[Path],
    diff: bool,
    write: bool,
    version_strategy: VersionStrategy | None,
    first_party_version_strategy: VersionStrategy | None,
    third_party_version_strategy: VersionStrategy | None,
    pin_strategy: PinStrategy,
    first_party_pattern: str,
) -> None:
    actual_files = list(find_files(files))

    if not actual_files:
        raise click.UsageError("No files or directories specified.")

    config = ActionUpdateConfig(
        first_party_version_strategy=cast(
            VersionStrategy,
            first_party_version_strategy or version_strategy or VersionStrategy.MAJOR,
        ),
        third_party_version_strategy=cast(
            VersionStrategy,
            third_party_version_strategy or version_strategy or VersionStrategy.MAJOR,
        ),
        pin_strategy=pin_strategy,
        first_party_pattern=re.compile(first_party_pattern),
    )

    for file in actual_files:
        log.info(f"Updating {file}...")
        result = get_action_updates_for_path(file, config=config)
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
