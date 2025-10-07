from __future__ import annotations

import ast
import dataclasses
import difflib
import logging
import re
from enum import Enum
from functools import lru_cache, partial
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError

from gha_tools.github_api import get_github_json

uses_regexp = re.compile(r"(?P<prelude>\buses:\s*)(?P<uses>.+?)$", re.MULTILINE)

log = logging.getLogger(__name__)


class NoVersionsFound(Exception):
    pass


class VersionStrategy(Enum):
    MAJOR = "major"
    SPECIFIC = "specific"


class PinStrategy(Enum):
    NONE = "none"
    THIRD_PARTY = "third_party"
    ALL = "all"


def is_beta_or_rc(ver: str) -> bool:
    if "-beta" in ver:
        return True
    if "-rc" in ver:
        return True
    return False


def try_unquote(val: str) -> str:
    try:  # unquote strings
        if isinstance(parsed_uses := ast.literal_eval(val), str):
            return parsed_uses
    except Exception:
        pass
    return val


@dataclasses.dataclass(frozen=True)
class ActionVersion:
    _data: dict

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def commit_sha(self) -> str:
        return self._data["commit"]["sha"]


@dataclasses.dataclass(frozen=True)
class ActionVersions:
    name: str
    all_version_infos: list[dict]

    @classmethod
    @lru_cache(maxsize=None)
    def from_github(cls, action_name: str) -> ActionVersions:
        log.debug("Fetching versions for %s...", action_name)
        try:
            action_tags = get_github_json(
                f"https://api.github.com/repos/{action_name}/tags",
            )
        except HTTPError as he:
            if he.status == 404:
                log.warning("Action %s (or tags for it) not found.", action_name)
                return cls(name=action_name, all_version_infos=[])
            raise
        return cls(name=action_name, all_version_infos=action_tags)

    @property
    def non_beta_or_rc_versions(self) -> Iterable[ActionVersion]:
        return (
            ActionVersion(version_info)
            for version_info in self.all_version_infos
            if not is_beta_or_rc(version_info["name"])
        )

    def get_latest_version(self) -> ActionVersion:
        for ver in self.non_beta_or_rc_versions:
            return ver
        raise NoVersionsFound("No non-beta/rc versions found")

    def get_major_version_for_action_version(
        self,
        version: ActionVersion,
    ) -> ActionVersion:
        all_versions = {av.name: av for av in self.non_beta_or_rc_versions}
        if version.name.startswith("v"):
            prospective_major_version = version.name.partition(".")[0]
            if major_version := all_versions.get(prospective_major_version):
                return major_version
        raise NoVersionsFound(
            f"Could not determine major version from {version.name!r}; "
            f"none of {set(all_versions)} matched",
        )


@dataclasses.dataclass(frozen=True)
class ActionSpec:
    name: str
    version: str
    qualified: bool = False
    comment: str | None = None

    @classmethod
    def from_string(cls, action_spec: str) -> ActionSpec:
        comment = None
        if "#" in action_spec:
            action_spec, comment = action_spec.split("#", 1)
            action_spec = action_spec.strip()
            comment = comment.strip()
        if "/" not in action_spec:
            action_spec = f"actions/{action_spec}"
            qualified = False
        else:
            qualified = True
        name, version = action_spec.split("@")
        return cls(
            name=name,
            version=version,
            qualified=qualified,
            comment=comment or None,
        )

    def __str__(self) -> str:
        name_part = self.name if self.qualified else self.name.partition("/")[2]
        s = f"{name_part}@{self.version}"
        if self.comment:
            s += f" # {self.comment}"
        return s

    def with_version_and_comment(self, version: str, comment: str | None) -> ActionSpec:
        return dataclasses.replace(self, version=version, comment=comment)

    @property
    def is_first_party(self) -> bool:
        return self.name.startswith("actions/") or self.name.startswith("github/")


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
    pin_strategy: PinStrategy,
) -> str:
    action_name = match.group("uses")
    action_name = try_unquote(action_name)
    if ".github/" in action_name:
        log.debug("Skipping workflow %s", action_name)
        return match.group(0)
    spec = ActionSpec.from_string(action_name)
    try:
        new_version = get_new_version_with_strategy(spec, version_strategy)
    except Exception:
        log.warning("Could not get new version for %s", spec, exc_info=True)
    else:
        pin_to_sha = pin_strategy == PinStrategy.ALL or (
            pin_strategy == PinStrategy.THIRD_PARTY and not spec.is_first_party
        )
        updated_spec = spec.with_version_and_comment(
            version=new_version.commit_sha if pin_to_sha else new_version.name,
            comment=new_version.name if pin_to_sha else spec.comment,
        )
        if spec != updated_spec:
            updates.append(ActionUpdate(spec, updated_spec))
            return f"{match.group('prelude')}{updated_spec}"
    return match.group(0)


def get_new_version_with_strategy(
    spec: ActionSpec,
    version_strategy: VersionStrategy,
) -> ActionVersion:
    versions = ActionVersions.from_github(spec.name)
    new_version = versions.get_latest_version()
    if version_strategy == VersionStrategy.MAJOR:
        try:
            new_version = versions.get_major_version_for_action_version(new_version)
        except NoVersionsFound as nve:
            log.warning("No major version found for %s: %s", spec, nve)
    return new_version


def get_action_updates_for_text(
    content: str,
    *,
    path: Path | None = None,
    version_strategy: VersionStrategy = VersionStrategy.MAJOR,
    pin_strategy: PinStrategy = PinStrategy.NONE,
) -> ActionUpdateResult:
    updates: list[ActionUpdate] = []
    fixer = partial(
        _fixup_use,
        updates=updates,
        version_strategy=version_strategy,
        pin_strategy=pin_strategy,
    )
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
    pin_strategy: PinStrategy = PinStrategy.NONE,
) -> ActionUpdateResult:
    return get_action_updates_for_text(
        path.read_text(),
        path=path,
        version_strategy=version_strategy,
        pin_strategy=pin_strategy,
    )
