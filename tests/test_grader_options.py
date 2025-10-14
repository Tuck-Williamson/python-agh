from pathlib import Path

import pytest

from agh import agh_data
from agh.agh_data import GraderOptions

@pytest.fixture
def swap_actual_user_defaults():
    swap = False
    if agh_data._USER_DEFAULTS_FILE.exists():
        backup = agh_data._USER_DEFAULTS_FILE.with_suffix(".bak")
        agh_data._USER_DEFAULTS_FILE.rename(backup)

        yield True

        backup.rename(agh_data._USER_DEFAULTS_FILE)
    else:
        yield False


def test_load_user_defaults_with_none(swap_actual_user_defaults):
    udo = GraderOptions.loadUserDefaults()
    assert udo is not None

def test_load_user_defaults_with_file(swap_actual_user_defaults):
    udo = GraderOptions.loadUserDefaults()
    udo.test_editor_command = "test_editor_command"
    udo.saveAsUserDefaults()

    udo2 = GraderOptions.loadUserDefaults()
    assert udo2.test_editor_command == "test_editor_command"

def test_metadata_set(swap_actual_user_defaults, tmp_path: Path):
    udo = GraderOptions.loadUserDefaults()
    udo.setMetadata("test_key", "test_value")
    save_path = tmp_path / "test_user_defaults.json"
    udo.save(save_path)

    udo2 = GraderOptions.load(save_path)
    assert udo2.getMetadata("test_key") == "test_value"

def test_metadata_set_multi_level(swap_actual_user_defaults, tmp_path: Path):
    udo = GraderOptions.loadUserDefaults()
    udo.setMetadata("test_key.bob.sally", 'a').setMetadata("test_key.bob.tom", "b")
    save_path = tmp_path / "test_user_defaults.json"
    udo.save(save_path)

    udo2 = GraderOptions.load(save_path)
    assert udo2.getMetadata("test_key") == dict(bob=dict(sally='a', tom="b"))
    assert udo2.getMetadata("test_key.bob.tom") == "b"
    assert udo2.getMetadata("test_key.bob") == dict(sally='a', tom="b")
