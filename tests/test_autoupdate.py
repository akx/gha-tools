
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
