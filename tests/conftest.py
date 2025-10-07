import os
from pathlib import Path
from shutil import copytree

import pytest

victim_dir = Path(__file__).parent / "autoupdate_victim"


@pytest.fixture
def victim_path(tmp_path) -> Path:
    tmp_victim_dir = tmp_path / f"victim-{os.urandom(8).hex()}"
    copytree(victim_dir, tmp_victim_dir)
    return tmp_victim_dir
