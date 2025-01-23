import pytest
from auto_archiver.core import config
from ruamel.yaml.scanner import ScannerError
from ruamel.yaml.comments import CommentedMap

def test_return_default_config_for_nonexistent_file():
    assert config.read_yaml("nonexistent_file.yaml") == config.EMPTY_CONFIG

def test_return_default_config_for_empty_file(tmp_path):
    empty_file = tmp_path / "empty_file.yaml"
    empty_file.write_text("")
    assert config.read_yaml(empty_file) == config.EMPTY_CONFIG

def test_raise_error_on_invalid_yaml(tmp_path):
    invalid_yaml = tmp_path / "invalid_yaml.yaml"
    invalid_yaml.write_text("key: \"value_without_end_quote")
    # make sure it raises ScannerError
    with pytest.raises(ScannerError):
        config.read_yaml(invalid_yaml)

def test_write_yaml(tmp_path):
    yaml_file = tmp_path / "write_yaml.yaml"
    config.store_yaml(config.EMPTY_CONFIG, yaml_file.as_posix())
    assert "steps:\n" in yaml_file.read_text()

def test_round_trip_comments(tmp_path):
    yaml_file = tmp_path / "round_trip_comments.yaml"

    with open(yaml_file, "w") as f:
        f.write("generic_extractor:\n  facebook_cookie: abc # end of line comment\n  subtitles: true\n  # comments: false\n  # livestreams: false\n  list_type:\n    - value1\n    - value2")

    loaded = config.read_yaml(yaml_file)
    # check the comments are preserved
    assert loaded['generic_extractor']['facebook_cookie'] == "abc"
    assert loaded['generic_extractor'].ca.items['facebook_cookie'][2].value == "# end of line comment\n"

    # add some more items to my_settings
    loaded['generic_extractor']['list_type'].append("bellingcat")
    config.store_yaml(loaded, yaml_file.as_posix())

    assert "# comments: false" in yaml_file.read_text()
    assert "facebook_cookie: abc # end of line comment" in yaml_file.read_text()
    assert "abc # end of line comment" in yaml_file.read_text()
    assert "- value2\n  - bellingcat" in yaml_file.read_text()

def test_merge_dicts():
    yaml_dict = config.EMPTY_CONFIG
    yaml_dict['settings'] = CommentedMap(**{
            "key1": ["a"],
            "key2": "old_value",
            "key3": ["a", "b", "c"],
        })

    dotdict = {
        "settings.key1": ["b", "c"],
        "settings.key2": "new_value",
        "settings.key3": ["b", "c", "d"],
    }
    merged = config.merge_dicts(dotdict, yaml_dict)
    assert merged["settings"]["key1"] == ["a", "b", "c"]
    assert merged["settings"]["key2"] == "new_value"
    assert merged["settings"]["key3"] == ["a", "b", "c", "d"]


def test_check_types():
    assert config.is_list_type([]) == True
    assert config.is_list_type(()) == True
    assert config.is_list_type(set()) == True
    assert config.is_list_type({}) == False
    assert config.is_list_type("") == False
    assert config.is_dict_type({}) == True
    assert config.is_dict_type(CommentedMap()) == True
    assert config.is_dict_type([]) == False
    assert config.is_dict_type("") == False

def test_from_dot_notation():
    dotdict = {
        "settings.key1": ["a", "b", "c"],
        "settings.key2": "new_value",
        "settings.key3.key4": "value",
    }
    normal_dict = config.from_dot_notation(dotdict)
    assert normal_dict["settings"]["key1"] == ["a", "b", "c"]
    assert normal_dict["settings"]["key2"] == "new_value"
    assert normal_dict["settings"]["key3"]["key4"] == "value"

def test_to_dot_notation():
    yaml_dict = config.EMPTY_CONFIG
    yaml_dict['settings'] = {
        "key1": ["a", "b", "c"],
        "key2": "new_value",
        "key3": {
            "key4": "value",
        }
    }
    dotdict = config.to_dot_notation(yaml_dict)
    assert dotdict["settings.key1"] == ["a", "b", "c"]
    assert dotdict["settings.key2"] == "new_value"
    assert dotdict["settings.key3.key4"] == "value"