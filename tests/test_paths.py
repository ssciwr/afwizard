from afwizard.paths import *

import os
import platform
import pytest
import tempfile


def test_paths(monkeypatch, tmp_path):
    # An absolute path is preserved
    abspath = os.path.abspath(__file__)
    assert abspath == locate_file(abspath)

    # Check that a file in the current working directory is picked up correctly
    with tempfile.NamedTemporaryFile(dir=os.getcwd()) as tmp_file:
        assert os.path.join(os.getcwd(), tmp_file.name) == locate_file(tmp_file.name)

    # Check that XDG paths are correctly recognized
    if platform.system() in ["Linux", "Darwin"]:
        monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path))
        abspath = os.path.join(tmp_path, "somefile.txt")
        open(abspath, "w").close()
        assert abspath == locate_file("somefile.txt")

    # Check that we always find the data provided by the package
    assert os.path.exists(locate_file("500k_NZ20_Westport.laz"))


def test_set_data_directory(tmp_path, monkeypatch):
    # Create a test file in tmp_path
    abspath = os.path.join(tmp_path, "somefile.txt")
    open(abspath, "w").close()

    # Trying to locate it should fail
    with pytest.raises(FileNotFoundError):
        locate_file("somefile.txt")

    # Unless we specifically set the directory
    set_data_directory(tmp_path)
    assert abspath == locate_file("somefile.txt")

    # Set to some path that does not exist
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        set_data_directory("random")

    # If we are allowed to, create it
    set_data_directory("random", create_dir=True)


def test_load_schema():
    # Accessing non-existent schemas raises
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistentone.json")

    # Returned paths are always absolute
    assert isinstance(load_schema("filter.json"), dict)


def test_within_temporary_workspace():
    cwd = os.getcwd()

    with within_temporary_workspace():
        assert cwd != os.getcwd()

    assert cwd == os.getcwd()
