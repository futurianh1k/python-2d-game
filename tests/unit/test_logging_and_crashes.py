"""로그 생명주기·회전 정책과 이중 오류 경로 검사.

로그 파일은 실제 UTF-8 파일이며 capsys/caplog는 관찰 도구다. 충돌 테스트에서는
전체 게임을 실행하지 않고 게임 루프/백업 저장만 Mock으로 실패시켜 원래 예외가
보존되는지 검사한다. 회전 임계값은 테스트에서만 축소한다."""

import logging
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pythongame import logging_config


def test_log_file_utf8_levels_and_no_duplicate_handlers(tmp_path, capsys, application_logging):
    """설정을 두 번 호출해도 한글 INFO가 파일/콘솔에 한 번씩만 기록되고 DEBUG는 제외되어야 한다."""
    path = tmp_path / "logs" / "game.log"
    logging_config.configure_logging(path, "INFO")
    logging_config.configure_logging(path, "INFO")
    logger = logging.getLogger("pythongame.test")
    logger.debug("hidden-debug")
    logger.info("한글 저장 완료")
    logging_config.shutdown_logging()
    text = path.read_text(encoding="utf-8")
    assert text.count("한글 저장 완료") == 1
    assert "hidden-debug" not in text
    assert "INFO pythongame.test:" in text
    assert capsys.readouterr().err.count("한글 저장 완료") == 1


def test_rotating_log_keeps_bounded_backups(tmp_path, monkeypatch, application_logging):
    """작은 테스트 임계값으로 실제 회전을 일으켜 백업 개수, 크기, UTF-8 해독과 최신 메시지를 검사한다."""
    monkeypatch.setattr(logging_config, "LOG_MAX_BYTES", 180)
    monkeypatch.setattr(logging_config, "LOG_BACKUP_COUNT", 2)
    path = tmp_path / "game.log"
    logging_config.configure_logging(path, "DEBUG")
    for index in range(20):
        logging.getLogger("pythongame.test").debug("회전 기록 %02d", index)
    logging_config.shutdown_logging()
    files = sorted(tmp_path.glob("game.log*"))
    assert [file.name for file in files] == ["game.log", "game.log.1", "game.log.2"]
    assert all(file.stat().st_size < 240 for file in files)
    assert "19" in path.read_text(encoding="utf-8")
    assert all(file.read_text(encoding="utf-8") for file in files)


@pytest.mark.parametrize("backup_fails", [False, True], ids=["backup-success", "backup-failure"])
@pytest.mark.parametrize("paused", [False, True], ids=["playing", "paused"])
def test_crash_backup_preserves_original_exception_and_play_time(caplog, backup_fails, paused):
    """게임 충돌 후 백업 성공/실패 모두 최초 RuntimeError 객체를 보존해야 한다.

    누적 시간 전달과 개별 traceback 로그를 확인해 실패 원인이 뒤바뀌는 회귀를 막는다."""
    from pythongame.main import Main
    app = Main.__new__(Main)
    original = RuntimeError("original-game-error")
    app._main_loop = Mock(side_effect=original)
    player = object()
    app.scene = SimpleNamespace(game_state=SimpleNamespace(player_state=player), total_time_played_on_character=9876)
    if paused:
        # PausedScene은 누적 시간을 직접 갖지 않고 내부 playing_scene에 보관한다.
        app.scene = SimpleNamespace(game_state=app.scene.game_state, playing_scene=app.scene)
    app.save_file_handler = Mock()
    app.save_file_handler.save_to_file.return_value = "2.json"
    if backup_fails:
        app.save_file_handler.save_to_file.side_effect = OSError("backup-write-error")
    with caplog.at_level(logging.INFO), pytest.raises(RuntimeError) as caught:
        app.main_loop()
    assert caught.value is original
    app.save_file_handler.save_to_file.assert_called_once_with(player, None, 9876)
    assert "Game crashed" in caplog.text and "original-game-error" in caplog.text
    assert ("Crash backup failed" if backup_fails else "Crash backup saved") in caplog.text
    assert any(record.exc_info and record.exc_info[1] is original for record in caplog.records)


@pytest.mark.parametrize("scene", [SimpleNamespace(), SimpleNamespace(game_state=None)])
def test_crash_without_character_does_not_attempt_backup(caplog, scene):
    """메뉴 상태처럼 캐릭터가 없을 때 가짜 백업을 만들지 않고 이유를 로그에 남겨야 한다."""
    from pythongame.main import Main
    app = Main.__new__(Main)
    app._main_loop = Mock(side_effect=ValueError("menu-error"))
    app.scene = scene
    app.save_file_handler = Mock()
    with pytest.raises(ValueError, match="menu-error"):
        app.main_loop()
    app.save_file_handler.save_to_file.assert_not_called()
    assert "no active character" in caplog.text


def test_traceback_is_written_to_log(tmp_path, application_logging):
    """메모리 caplog뿐 아니라 실제 파일에도 ERROR 레벨·예외 타입·traceback이 남는지 검사한다."""
    path = tmp_path / "crash.log"
    logging_config.configure_logging(path)
    try:
        raise RuntimeError("reproducible-crash")
    except RuntimeError:
        logging.getLogger("pythongame.test").exception("Crash captured")
    logging_config.shutdown_logging()
    text = path.read_text(encoding="utf-8")
    assert "ERROR" in text and "Traceback" in text and "RuntimeError: reproducible-crash" in text


def test_failed_log_reconfiguration_keeps_previous_handler(tmp_path, application_logging):
    """새 로그 경로가 잘못됐을 때 기존 핸들러까지 제거되어 진단이 끊기지 않아야 한다."""
    original = tmp_path / "original.log"
    logging_config.configure_logging(original)
    blocked_parent = tmp_path / "not-a-directory"
    blocked_parent.write_text("file", encoding="utf-8")
    with pytest.raises(OSError):
        logging_config.configure_logging(blocked_parent / "game.log")
    logging.getLogger("pythongame.test").info("previous-handler-still-active")
    logging_config.shutdown_logging()
    assert "previous-handler-still-active" in original.read_text(encoding="utf-8")


def test_start_releases_sdl_after_partial_initialization(monkeypatch):
    """Main 생성 중 실패해도 start()의 finally가 SDL을 종료해야 한다.

    게임 생성자만 실패로 교체하고 pygame.init/quit은 실제로 실행해 자원 상태를 관찰한다.
    """
    import pygame
    from pythongame import main

    def fail_constructor(*args):
        pygame.init()
        raise RuntimeError("initialization-failed")

    monkeypatch.setattr(main, "Main", fail_constructor)
    with pytest.raises(RuntimeError, match="initialization-failed"):
        main.start(None, None, None, None, None, False)
    assert not pygame.get_init()
