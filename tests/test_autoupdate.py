import re

from click.testing import CliRunner

from gha_tools.cli import main


def test_autoupdate(victim_path):
    result = CliRunner().invoke(
        main,
        [
            "autoupdate",
            "--diff",
            str(victim_path),
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
    result = CliRunner().invoke(
        main,
        [
            "autoupdate",
            "--write",
            "--pin",
            str(victim_path),
        ],
    )
    assert result.exit_code == 0
    content = (victim_path / "victim.yml").read_text()
    for action in ("actions/checkout", "actions/setup-python"):
        assert re.search(
            rf"^\s+- uses: {action}@[0-9a-f]+\s+# v",
            content,
            flags=re.MULTILINE,
        )
