import logging
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pythongame import logging_config


def test_log_file_utf8_levels_and_no_duplicate_handlers(tmp_path, capsys, application_logging):
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
def test_crash_backup_preserves_original_exception_and_play_time(caplog, backup_fails):
    from pythongame.main import Main
    app = Main.__new__(Main)
    original = RuntimeError("original-game-error")
    app._main_loop = Mock(side_effect=original)
    player = object()
    app.scene = SimpleNamespace(game_state=SimpleNamespace(player_state=player), total_time_played_on_character=9876)
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
    path = tmp_path / "crash.log"
    logging_config.configure_logging(path)
    try:
        raise RuntimeError("reproducible-crash")
    except RuntimeError:
        logging.getLogger("pythongame.test").exception("Crash captured")
    logging_config.shutdown_logging()
    text = path.read_text(encoding="utf-8")
    assert "ERROR" in text and "Traceback" in text and "RuntimeError: reproducible-crash" in text
