import re

import pytest
from click.testing import CliRunner

from gha_tools.cli import main


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


def test_autoupdate_pin(victim_path):
    test_yml_path = victim_path / "test.yml"
    result = CliRunner().invoke(
        main,
        [
            "autoupdate",
            "--write",
            "--pin",
            str(test_yml_path),
        ],
    )
    assert result.exit_code == 0
    content = test_yml_path.read_text()
    for action in ("actions/checkout", "actions/setup-python"):
        assert re.search(
            rf"^\s+- uses: {action}@[0-9a-f]+\s+# v",
            content,
            flags=re.MULTILINE,
        )


@pytest.mark.parametrize("pin", (False, True))
def test_autoupdate_major(victim_path, pin):
    uv_yml_path = victim_path / "uv.yml"
    result = CliRunner().invoke(
        main,
        [
            "autoupdate",
            "--write",
            *(("--pin",) if pin else ()),
            "--version-strategy=specific",
            str(uv_yml_path),
        ],
    )
    assert result.exit_code == 0
    content = uv_yml_path.read_text()
    assert re.search(r"(@|# )v\d+\.\d+", content)
