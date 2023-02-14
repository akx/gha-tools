from pathlib import Path

from click.testing import CliRunner

from gha_tools.cli import main


def test_autoupdate():
    runner = CliRunner()
    victim_dir = Path(__file__).parent / "autoupdate_victim"
    result = runner.invoke(
        main,
        [
            "autoupdate",
            "--diff",
            str(victim_dir),
        ],
    )
    assert result.exit_code == 0
    assert "-      - uses: actions/checkout@v1" in result.output
    assert "+      - uses: actions/checkout@v" in result.output
    assert "-      - uses: actions/setup-python@v1" in result.output
    assert "+      - uses: actions/setup-python@v" in result.output
