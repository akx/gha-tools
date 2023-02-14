from __future__ import annotations

import ast
import dataclasses
import difflib
import logging
import re
from enum import Enum
from functools import lru_cache, partial
from pathlib import Path

from gha_tools.github_api import get_github_json

uses_regexp = re.compile(r"(?P<prelude>\s*uses:\s*)(?P<uses>.+?)$", re.MULTILINE)

log = logging.getLogger(__name__)


class VersionStrategy(Enum):
    MAJOR = "major"
    SPECIFIC = "specific"


@dataclasses.dataclass(frozen=True)
class ActionVersions:
    name: str
    version_infos: list[dict]

    @classmethod
    @lru_cache(maxsize=None)
    def from_github(cls, action_name: str) -> ActionVersions:
        log.debug("Fetching versions for %s...", action_name)
        action_tags = get_github_json(
            f"https://api.github.com/repos/{action_name}/tags",
        )
        return cls(name=action_name, version_infos=action_tags)

    @property
    def latest_version(self) -> str:
        return self.version_infos[0]["name"]

    @property
    def version_names(self) -> list[str]:
        return [version_info["name"] for version_info in self.version_infos]

    @property
    def latest_major_version(self) -> str:
        version_names = self.version_names
        latest_version = self.latest_version
        if latest_version.startswith("v"):
            prospective_major_version = latest_version.partition(".")[0]
            if prospective_major_version in version_names:
                return prospective_major_version
        return latest_version


@dataclasses.dataclass(frozen=True)
class ActionSpec:
    name: str
    version: str
    qualified: bool = False

    @classmethod
    def from_string(cls, action_spec: str) -> ActionSpec:
        if "/" not in action_spec:
            action_spec = f"actions/{action_spec}"
            qualified = False
        else:
            qualified = True
        name, version = action_spec.split("@")
        return cls(name=name, version=version, qualified=qualified)

    def __str__(self) -> str:
        if self.qualified:
            return f"{self.name}@{self.version}"
        return f"{self.name.partition('/')[2]}@{self.version}"

    def with_version(self, version: str) -> ActionSpec:
        return dataclasses.replace(self, version=version)


@dataclasses.dataclass(frozen=True)
class ActionUpdate:
    old_spec: ActionSpec
    new_spec: ActionSpec


@dataclasses.dataclass(frozen=True)
class ActionUpdateResult:
    path: Path | None
    old_content: str
    new_content: str
    changes: list[ActionUpdate]

    def print_diff(self, file=None) -> None:
        name = str(self.path or "")
        for diff_line in difflib.unified_diff(
            self.old_content.splitlines(keepends=True),
            self.new_content.splitlines(keepends=True),
            fromfile=name,
            tofile=name,
        ):
            print(diff_line, end="", file=file)

    def write(self) -> None:
        if self.path is None:
            raise ValueError("Cannot write to None path.")
        self.path.write_text(self.new_content)


def _fixup_use(
    match: re.Match,
    *,
    updates: list[ActionUpdate],
    version_strategy: VersionStrategy,
) -> str:
    action_name = match.group("uses")
    try:  # unquote strings
        if isinstance(parsed_uses := ast.literal_eval(action_name), str):
            action_name = parsed_uses
    except Exception:
        pass
    spec = ActionSpec.from_string(action_name)
    new_version = get_new_version_with_strategy(spec, version_strategy)
    updated_spec = spec.with_version(new_version)
    if spec != updated_spec:
        updates.append(ActionUpdate(spec, updated_spec))
        return f"{match.group('prelude')}{updated_spec}"
    return match.group(0)


def get_new_version_with_strategy(
    spec: ActionSpec,
    version_strategy: VersionStrategy,
) -> str:
    versions = ActionVersions.from_github(spec.name)
    if version_strategy == VersionStrategy.MAJOR:
        return versions.latest_major_version
    if version_strategy == VersionStrategy.SPECIFIC:
        return versions.latest_version
    raise ValueError(f"Unknown version strategy: {version_strategy}")


def get_action_updates_for_text(
    content: str,
    *,
    path: Path | None = None,
    version_strategy: VersionStrategy = VersionStrategy.MAJOR,
) -> ActionUpdateResult:
    updates: list[ActionUpdate] = []
    fixer = partial(_fixup_use, updates=updates, version_strategy=version_strategy)
    new_content = uses_regexp.sub(fixer, content)
    return ActionUpdateResult(
        path=path,
        old_content=content,
        new_content=new_content,
        changes=updates,
    )


def get_action_updates_for_path(
    path: Path,
    *,
    version_strategy: VersionStrategy = VersionStrategy.MAJOR,
) -> ActionUpdateResult:
    return get_action_updates_for_text(
        path.read_text(),
        path=path,
        version_strategy=version_strategy,
    )
