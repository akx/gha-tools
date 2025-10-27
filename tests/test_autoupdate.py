import re

import pytest
from click.testing import CliRunner

from gha_tools.cli import main


@pytest.fixture(autouse=True, scope="module")
def cache_github_api():
    from gha_tools import github_api

    github_api.cache = {}
    try:
        yield
    finally:
        assert github_api.cache  # did use cache?
        github_api.cache = None


def is_pinned(action: str, content: str) -> re.Match | None:
    pat = rf"^\s+- uses: {action}@[0-9a-f]+\s+# v"
    return re.search(pat, content, flags=re.MULTILINE)


def is_major_tag(action: str, content: str) -> re.Match | None:
    pat = rf"^\s+- uses: {action}@v\d+\s"
    return re.search(pat, content, flags=re.MULTILINE)


def is_specific_tag(action: str, content: str) -> re.Match | None:
    pat = rf"^\s+- uses: {action}@v\d+\.\d+"
    return re.search(pat, content, flags=re.MULTILINE)


def is_tag(action: str, content: str) -> re.Match | None:
    return is_major_tag(action, content) or is_specific_tag(action, content)


def test_autoupdate(victim_path):
    result = CliRunner().invoke(
        main,
        [
            "autoupdate",
            "--diff",
            str(victim_path / "test.yml"),
        ],
    )
    assert result.exit_code == 0
    assert "-      - uses: actions/checkout@v1" in result.output
    assert "+      - uses: actions/checkout@v" in result.output
    assert "-      - uses: actions/setup-python@v1" in result.output
    assert "+      - uses: actions/setup-python@v" in result.output
    assert "beta" not in result.output
    assert "# comment" in result.output  # Comment retained


@pytest.mark.parametrize("pin", ("all", "third_party"))
def test_autoupdate_pin(victim_path, pin):
    test_yml_path = victim_path / "test.yml"
    result = CliRunner().invoke(
        main,
        [
            "autoupdate",
            "--write",
            f"--pin={pin}",
            str(test_yml_path),
        ],
    )
    assert result.exit_code == 0
    content = test_yml_path.read_text()
    for action in (
        "actions/checkout",
        "actions/setup-python",
        "codecov/codecov-action",
    ):
        if pin == "third_party" and "actions/" in action:
            # When pinning only third-party actions,
            # first-party actions are just left as tags
            assert is_tag(action, content)
        else:
            assert is_pinned(action, content)


@pytest.mark.parametrize("pin", (False, True))
def test_autoupdate_specific(victim_path, pin):
    uv_yml_path = victim_path / "uv.yml"
    result = CliRunner().invoke(
        main,
        [
            "autoupdate",
            "--write",
            *(("--pin=all",) if pin else ()),
            "--version-strategy=specific",
            str(uv_yml_path),
        ],
    )
    assert result.exit_code == 0
    content = uv_yml_path.read_text()
    if pin:
        assert is_pinned("astral-sh/setup-uv", content)
    else:
        assert is_specific_tag("astral-sh/setup-uv", content)


def test_separate_version_strategies(victim_path):
    test_yml_path = victim_path / "test.yml"
    result = CliRunner().invoke(
        main,
        [
            "autoupdate",
            "--write",
            "--first-party-version-strategy=major",
            "--third-party-version-strategy=specific",
            str(test_yml_path),
        ],
    )
    assert result.exit_code == 0
    content = test_yml_path.read_text()

    # First-party actions (actions/checkout, actions/setup-python) should use major versions
    assert is_major_tag("actions/checkout", content)
    assert is_major_tag("actions/setup-python", content)
    # Third-party actions (codecov/codecov-action) should use specific versions
    assert is_specific_tag("codecov/codecov-action", content)


def test_custom_first_party_pattern(victim_path):
    test_yml_path = victim_path / "test.yml"
    # Test using a custom pattern that treats codecov as first-party
    result = CliRunner().invoke(
        main,
        [
            "autoupdate",
            "--write",
            "--first-party-version-strategy=major",
            "--third-party-version-strategy=specific",
            "--first-party-pattern=^(actions|github|codecov)/",
            str(test_yml_path),
        ],
    )
    assert result.exit_code == 0
    content = test_yml_path.read_text()

    # All actions should use major versions (since codecov is now first-party)
    for action in (
        "actions/checkout",
        "actions/setup-python",
        "codecov/codecov-action",
    ):
        assert is_major_tag(action, content)


def test_subdirectory_actions(victim_path):
    """Test that actions in subdirectories (e.g., github/codeql-action/upload-sarif) are handled correctly."""
    codeql_yml_path = victim_path / "codeql.yml"
    result = CliRunner().invoke(
        main,
        [
            "autoupdate",
            "--write",
            "--version-strategy=major",
            str(codeql_yml_path),
        ],
    )
    assert result.exit_code == 0
    content = codeql_yml_path.read_text()

    # All codeql-action subdirectory actions should be updated
    for action in (
        "github/codeql-action/init",
        "github/codeql-action/autobuild",
        "github/codeql-action/analyze",
        "github/codeql-action/upload-sarif",
    ):
        assert is_major_tag(action, content)
