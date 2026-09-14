"""새 Python 프로세스가 필요한 CLI 경계 검사.

대규모 게임 시나리오를 문자열 코드로 실행하던 기존 구조와 달리, 프로세스는
import 부작용·도움말·실패 종료 코드·영속 로그 확인에만 사용한다.
stdout/stderr와 returncode를 함께 판정하며 무한 대기는 20초 timeout으로 막는다."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.process


@pytest.fixture
def run_process(tmp_path):
    """같은 Python/SDL 환경의 하위 프로세스를 프로젝트 밖에서 실행한다.

    실행 파일 경로와 PYTHONPATH는 명시하고 stdout/stderr를 보존해 실패 원인을 출력할 수 있다."""
    def execute(*args):
        return subprocess.run(
            [sys.executable, "-W", "error", *args], cwd=tmp_path,
            env=dict(os.environ, PYTHONPATH=str(PROJECT_ROOT)),
            text=True, capture_output=True, timeout=20,
        )
    return execute


def test_importing_entry_points_has_no_pygame_side_effects(run_process):
    """import만 수행했을 때 pygame 자체가 로드되지 않는지 새 프로세스에서 확인한다."""
    result = run_process("-c", "import run, map_editor, sys; assert 'pygame' not in sys.modules")
    assert result.returncode == 0, result.stderr
    assert result.stdout == result.stderr == ""


@pytest.mark.parametrize("script", ["run.py", "map_editor.py"])
def test_cli_help_works_outside_project(run_process, script):
    """두 실행기의 --help가 리소스/GUI 초기화 없이 종료 코드 0으로 끝나야 한다."""
    result = run_process(str(PROJECT_ROOT / script), "--help")
    assert result.returncode == 0, result.stderr
    assert "--log-file" in result.stdout and "--map" in result.stdout


def test_missing_save_has_nonzero_exit_and_durable_error_log(run_process, tmp_path):
    """존재하지 않는 저장 파일을 요청해 실제 실패 종료와 파일 로그를 검증한다.

    오류 traceback과 종료 로그가 함께 남고 비어 있는 캐릭터가 비상 저장되지 않아야 한다."""
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
    """기존 데이터 출력 도구의 종료 코드와 비어 있지 않은 출력을 회귀 검사한다."""
    result = run_process(str(PROJECT_ROOT / script))
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()
