"""파일 저장의 정상·오류 계약과 로그를 검증한다.

운영 파일시스템 전체를 모의하지 않는다. 실제 tmp_path 파일을 만들고, 실패시킬
한 단계만 monkeypatch한다. 디스크 용량을 실제로 고갈시키는 대신 ENOSPC를
주입하며, 원본 SHA-256·남은 파일 목록·예외 객체·로그 레벨을 함께 검사한다."""

import errno
import hashlib
import json
import logging

import pytest

from pythongame import json_files


def test_utf8_round_trip_and_success_log(tmp_path, caplog):
    """유니코드 내용/중첩 JSON의 실제 저장·읽기와 INFO/DEBUG 로그를 검사한다.

    경로는 기록하지만 저장 데이터 본문은 로그에 노출하지 않아야 한다."""
    path = tmp_path / "한글 저장.json"
    data = {"name": "마법사 🧙", "items": [None, {"value": 0}], "enabled": True}
    with caplog.at_level(logging.DEBUG):
        json_files.write_json_atomic(path, data)
        assert json_files.read_json(path) == data
    assert "마법사" in path.read_text(encoding="utf-8")
    assert path.read_bytes().endswith(b"\n")
    assert any(record.levelno == logging.INFO and "Saved JSON" in record.message for record in caplog.records)
    assert "Loaded JSON" in caplog.text
    assert "마법사" not in caplog.text  # Payload contents are not logged.
    assert list(tmp_path.glob("*.tmp")) == []


@pytest.mark.parametrize("contents,error", [
    (None, FileNotFoundError), (b'{"unfinished":', json.JSONDecodeError),
    (b'\xff\xfe', UnicodeDecodeError),
], ids=["missing", "truncated", "invalid-utf8"])
def test_read_failures_keep_original_exception_and_log(tmp_path, caplog, contents, error):
    """없음/깨진 JSON/잘못된 UTF-8을 구분하고 원래 예외 타입과 traceback 로그를 검사한다."""
    path = tmp_path / "bad.json"
    if contents is not None:
        path.write_bytes(contents)
    with pytest.raises(error):
        json_files.read_json(path)
    assert any(record.levelno == logging.ERROR and record.exc_info for record in caplog.records)
    assert str(path) in caplog.text


@pytest.mark.parametrize("stage", ["create", "serialize", "flush", "replace"])
def test_failed_write_preserves_original_hash_and_cleans_temp(tmp_path, monkeypatch, caplog, stage):
    """생성/직렬화/fsync/replace 실패를 한 단계씩 주입해 원본 SHA-256이 유지되는지 검사한다.

    예외 객체의 동일성, 임시 파일 제거, 실패 로그와 성공 로그 부재를 함께 확인한다."""
    path = tmp_path / "save.json"
    path.write_bytes(b'{"previous": "untouched"}\n')
    previous_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    failure = OSError(errno.ENOSPC, "simulated disk full")

    def fail(*args, **kwargs):
        if stage == "serialize":
            args[1].write('{"partial":')
        raise failure

    targets = {
        "create": (json_files.tempfile, "NamedTemporaryFile"),
        "serialize": (json_files.json, "dump"),
        "flush": (json_files.os, "fsync"),
        "replace": (json_files.os, "replace"),
    }
    monkeypatch.setattr(*targets[stage], fail)
    with pytest.raises(OSError) as caught:
        json_files.write_json_atomic(path, {"new": 1})
    assert caught.value is failure
    assert hashlib.sha256(path.read_bytes()).hexdigest() == previous_hash
    assert sorted(file.name for file in tmp_path.iterdir()) == ["save.json"]
    assert "Failed to write JSON" in caplog.text
    assert "Saved JSON" not in caplog.text


@pytest.mark.parametrize("data,error", [({"bad": object()}, TypeError), ({"bad": float('nan')}, ValueError)])
def test_unserializable_data_does_not_create_destination(tmp_path, data, error):
    """지원하지 않는 Python 객체와 NaN이 빈 파일이나 임시 파일을 남기지 않아야 한다."""
    with pytest.raises(error):
        json_files.write_json_atomic(tmp_path / "new.json", data)
    assert list(tmp_path.iterdir()) == []


def test_successful_overwrite_replaces_complete_file(tmp_path):
    """정상 덮어쓰기에서는 새 JSON 전체만 남고 불필요한 파일이 생기지 않아야 한다."""
    path = tmp_path / "save.json"
    json_files.write_json_atomic(path, {"old": True})
    json_files.write_json_atomic(path, {"new": [1, 2, 3]})
    assert json_files.read_json(path) == {"new": [1, 2, 3]}
    assert list(tmp_path.iterdir()) == [path]


def test_cleanup_failure_does_not_mask_serialization_error(tmp_path, monkeypatch, caplog):
    """쓰기 실패에 임시 파일 정리 실패까지 겹쳐도 최초 예외를 보존해야 한다.

    정리에 실패한 파일은 tmp_path 안에 남으며 경고가 그 위치를 알려준다.
    권한을 실제로 바꾸지 않고 unlink만 실패시켜 OS/사용자 권한에 독립적으로 검사한다.
    """
    from pathlib import Path
    original_unlink = Path.unlink

    def fail_temporary_unlink(path, *args, **kwargs):
        if path.suffix == ".tmp":
            raise PermissionError("simulated cleanup denied")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_temporary_unlink)
    with pytest.raises(TypeError):
        json_files.write_json_atomic(tmp_path / "new.json", {"bad": object()})
    assert "Could not remove temporary JSON file" in caplog.text
    assert not (tmp_path / "new.json").exists()
    assert len(list(tmp_path.glob("*.tmp"))) == 1
