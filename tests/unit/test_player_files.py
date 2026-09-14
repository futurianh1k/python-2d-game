import json
import logging

import pytest

from pythongame.player_file import PlayerStateJson, SaveFileError, SaveFileHandler


def test_legacy_optional_fields_and_round_trip(saved_data):
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
    saved_data[field] = value
    with pytest.raises(SaveFileError):
        PlayerStateJson.deserialize(saved_data)


@pytest.mark.parametrize("data", [None, [], {}, {"hero": "MAGE"}])
def test_invalid_root_or_missing_required_fields(data):
    with pytest.raises(SaveFileError):
        PlayerStateJson.deserialize(data)


def test_zero_boundaries_null_slots_and_unknown_future_fields(saved_data):
    saved_data.update(items=[None, ["NOVICE_WAND~~", "초보 마법사"]], talents=[None, 0], future_field="ignored")
    state = PlayerStateJson.deserialize(saved_data)
    assert state.level == 1 and state.money == state.exp == 0
    assert state.items[0] is None and state.talent_tier_choices == [None, 0]


def test_mixed_directory_is_sorted_and_names_are_reserved(save_handler):
    for name in ("10.json", "2.json", "named.json", "README.txt", ".1.json.abc.tmp"):
        (save_handler.directory / name).write_text("{}", encoding="utf-8")
    (save_handler.directory / "20.json").mkdir()
    assert save_handler.list_save_files() == ["2.json", "10.json", "named.json"]
    assert save_handler._generate_filename_for_new_character() == "21.json"


def test_empty_directory_and_existing_directory(tmp_path):
    directory = tmp_path / "nested" / "characters"
    first = SaveFileHandler(directory)
    second = SaveFileHandler(directory)
    assert first.list_save_files() == second.list_save_files() == []
    assert second._generate_filename_for_new_character() == "1.json"


@pytest.mark.parametrize("filename", ["", "../1.json", "..\\1.json", "/tmp/1.json", "C:\\1.json", "file.txt"])
def test_save_names_cannot_escape_directory(save_handler, filename):
    with pytest.raises(SaveFileError):
        save_handler.load_player_state_from_json_file(filename)


def test_invalid_save_logs_path_and_leaves_file_untouched(save_handler, saved_data, caplog):
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
