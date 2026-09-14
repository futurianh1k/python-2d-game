import errno
import hashlib
import json
import logging

import pytest

from pythongame import json_files


def test_utf8_round_trip_and_success_log(tmp_path, caplog):
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
    path = tmp_path / "bad.json"
    if contents is not None:
        path.write_bytes(contents)
    with pytest.raises(error):
        json_files.read_json(path)
    assert any(record.levelno == logging.ERROR and record.exc_info for record in caplog.records)
    assert str(path) in caplog.text


@pytest.mark.parametrize("stage", ["create", "serialize", "flush", "replace"])
def test_failed_write_preserves_original_hash_and_cleans_temp(tmp_path, monkeypatch, caplog, stage):
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
    with pytest.raises(error):
        json_files.write_json_atomic(tmp_path / "new.json", data)
    assert list(tmp_path.iterdir()) == []


def test_successful_overwrite_replaces_complete_file(tmp_path):
    path = tmp_path / "save.json"
    json_files.write_json_atomic(path, {"old": True})
    json_files.write_json_atomic(path, {"new": [1, 2, 3]})
    assert json_files.read_json(path) == {"new": [1, 2, 3]}
    assert list(tmp_path.iterdir()) == [path]
