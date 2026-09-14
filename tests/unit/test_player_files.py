"""캐릭터 JSON의 구조·하위 호환·파일 목록 정책 검사.

정상 입력 fixture에서 한 필드만 바꾸어 오류 원인을 분리한다. 값/타입 동치분할과
정수의 0/-1 경계를 사용하며 bool이 int처럼 취급되는 Python 특성도 다룬다.
원자적 파일 교체 자체는 test_json_files에서, 실제 캐릭터 복원은 통합 TC에서 검증한다."""

import json
import logging

import pytest

from pythongame.player_file import PlayerStateJson, SaveFileError, SaveFileHandler


def test_legacy_optional_fields_and_round_trip(saved_data):
    """구형 선택 필드 누락은 기본값으로 복원되며 다시 직렬화해 읽을 수 있어야 한다."""
    for field in ("talents", "total_time_played", "active_quests", "completed_quests"):
        saved_data.pop(field)
    restored = PlayerStateJson.deserialize(saved_data)
    assert restored.talent_tier_choices == []
    assert restored.total_time_played_on_character == 0
    assert restored.active_quests == restored.completed_quests == []
    assert PlayerStateJson.deserialize(PlayerStateJson.serialize(restored)).hero_id == "MAGE"


@pytest.mark.parametrize("field,value", [
    ("hero", "UNKNOWN"), ("hero", []), ("level", 0), ("level", True), ("level", 1.5),
    ("exp", -1), ("money", -1), ("total_time_played", "12"),
    ("consumables", []), ("consumables", {"0": []}), ("consumables", {"1": ["UNKNOWN"]}),
    ("items", {}), ("items", [["only-one"]]), ("items", [[1, "name"]]),
    ("enabled_portals", []), ("enabled_portals", {"UNKNOWN": "UNKNOWN"}),
    ("talents", "0"), ("talents", [-1]), ("talents", [True]),
    ("active_quests", ["UNKNOWN"]), ("completed_quests", "MAIN_RETRIEVE_KEY"),
])
def test_invalid_field_types_and_boundaries(saved_data, field, value):
    """한 필드씩 잘못된 값/타입을 넣어 구조 검증 실패의 원인을 분리한다."""
    saved_data[field] = value
    with pytest.raises(SaveFileError):
        PlayerStateJson.deserialize(saved_data)


@pytest.mark.parametrize("data", [None, [], {}, {"hero": "MAGE"}])
def test_invalid_root_or_missing_required_fields(data):
    """JSON 문법은 유효해도 캐릭터 객체/필수 필드가 아니면 SaveFileError로 거부한다."""
    with pytest.raises(SaveFileError):
        PlayerStateJson.deserialize(data)


def test_zero_boundaries_null_slots_and_unknown_future_fields(saved_data):
    """정상 최소값, 비어 있는 슬롯(None), 새 버전의 추가 필드는 허용해야 한다."""
    saved_data.update(items=[None, ["NOVICE_WAND~~", "초보 마법사"]], talents=[None, 0], future_field="ignored")
    state = PlayerStateJson.deserialize(saved_data)
    assert state.level == 1 and state.money == state.exp == 0
    assert state.items[0] is None and state.talent_tier_choices == [None, 0]


def test_mixed_directory_is_sorted_and_names_are_reserved(save_handler):
    """메모/임시파일/동명 디렉터리가 있어도 목록과 다음 저장 번호를 안전하게 결정해야 한다."""
    for name in ("10.json", "2.json", "named.json", "README.txt", ".1.json.abc.tmp"):
        (save_handler.directory / name).write_text("{}", encoding="utf-8")
    (save_handler.directory / "20.json").mkdir()
    assert save_handler.list_save_files() == ["2.json", "10.json", "named.json"]
    assert save_handler._generate_filename_for_new_character() == "21.json"


def test_empty_directory_and_existing_directory(tmp_path):
    """중첩 저장 디렉터리 생성과 이미 존재하는 경로 재사용이 모두 가능해야 한다."""
    directory = tmp_path / "nested" / "characters"
    first = SaveFileHandler(directory)
    second = SaveFileHandler(directory)
    assert first.list_save_files() == second.list_save_files() == []
    assert second._generate_filename_for_new_character() == "1.json"


@pytest.mark.parametrize("filename", ["", "../1.json", "..\\1.json", "/tmp/1.json", "C:\\1.json", "file.txt"])
def test_save_names_cannot_escape_directory(save_handler, filename):
    """POSIX/Windows 상대 탈출·절대 경로·확장자 오류를 실제 읽기 전에 거부해야 한다."""
    with pytest.raises(SaveFileError):
        save_handler.load_player_state_from_json_file(filename)


def test_invalid_save_logs_path_and_leaves_file_untouched(save_handler, saved_data, caplog):
    """잘못된 hero를 가진 저장 파일의 바이트를 보존하고 경로만 오류 로그에 남겨야 한다."""
    saved_data["hero"] = "PRIVATE_PAYLOAD_SENTINEL"
    path = save_handler.directory / "1.json"
    path.write_text(json.dumps(saved_data), encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(SaveFileError):
        save_handler.load_player_state_from_json_file("1.json")
    assert path.read_bytes() == before
    assert "Invalid save structure" in caplog.text
    assert str(path) in caplog.text
    assert "PRIVATE_PAYLOAD_SENTINEL" not in caplog.text


def test_save_success_and_failed_validation_do_not_overwrite(save_handler, saved_data, caplog):
    """정상 파일을 만든 뒤 잘못된 상태로 저장하면 기존 파일 바이트가 그대로 남아야 한다."""
    state = PlayerStateJson.deserialize(saved_data)
    with caplog.at_level(logging.INFO):
        save_handler._save_player_state_to_json_file(state, "1.json")
    path = save_handler.directory / "1.json"
    before = path.read_bytes()
    assert save_handler.load_player_state_from_json_file("1.json").hero_id == "MAGE"
    state.level = 0
    with pytest.raises(SaveFileError):
        save_handler._save_player_state_to_json_file(state, "1.json")
    assert path.read_bytes() == before
    assert "Saved JSON" in caplog.text


def test_symlink_save_is_not_followed(save_handler, tmp_path):
    """외부 파일을 가리키는 링크는 메뉴 후보에서 제외하고 직접 로드도 거부한다.

    실제 링크 생성 권한이 없는 Windows 환경에서는 이 OS 의존 케이스만 건너뛴다.
    링크를 제거하거나 외부 파일에 쓰지 않으며 원본 내용도 함께 검사한다.
    """
    outside = tmp_path / "outside.json"
    outside.write_text('external-data', encoding="utf-8")
    link = save_handler.directory / "1.json"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Symbolic links unavailable: {exc}")
    assert save_handler.list_save_files() == []
    with pytest.raises(SaveFileError, match="symbolic link"):
        save_handler.load_player_state_from_json_file("1.json")
    assert outside.read_text(encoding="utf-8") == 'external-data'
