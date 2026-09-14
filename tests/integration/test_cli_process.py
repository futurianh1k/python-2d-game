import os
from pathlib import Path
import subprocess
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.process


@pytest.fixture
def run_process(tmp_path):
    def execute(*args):
        return subprocess.run(
            [sys.executable, "-W", "error", *args], cwd=tmp_path,
            env=dict(os.environ, PYTHONPATH=str(PROJECT_ROOT)),
            text=True, capture_output=True, timeout=20,
        )
    return execute


def test_importing_entry_points_has_no_pygame_side_effects(run_process):
    result = run_process("-c", "import run, map_editor, sys; assert 'pygame' not in sys.modules")
    assert result.returncode == 0, result.stderr
    assert result.stdout == result.stderr == ""


@pytest.mark.parametrize("script", ["run.py", "map_editor.py"])
def test_cli_help_works_outside_project(run_process, script):
    result = run_process(str(PROJECT_ROOT / script), "--help")
    assert result.returncode == 0, result.stderr
    assert "--log-file" in result.stdout and "--map" in result.stdout


def test_missing_save_has_nonzero_exit_and_durable_error_log(run_process, tmp_path):
    result = run_process(str(PROJECT_ROOT / "run.py"), "--disable-fullscreen", "--file", "missing.json",
                         "--log-file", "logs/game.log")
    assert result.returncode == 1
    log = (tmp_path / "logs/game.log").read_text(encoding="utf-8")
    assert "ERROR pythongame.json_files" in log
    assert "FileNotFoundError" in log and "Traceback" in log
    assert "Game stopped" in log
    assert list((tmp_path / "saved_characters").iterdir()) == []


@pytest.mark.parametrize("script", ["print_abilities.py", "print_consumables.py", "print_enemies.py", "print_items.py", "print_loot.py"])
def test_data_utilities_exit_successfully(run_process, script):
    result = run_process(str(PROJECT_ROOT / script))
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()
