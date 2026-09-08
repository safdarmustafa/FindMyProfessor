from pathlib import Path

import pytest

from app.cv.storage import resolve_storage_path, save_cv_bytes, safe_filename


def test_safe_filename_strips_paths():
    assert ".." not in safe_filename("../../etc/passwd.pdf")
    assert safe_filename("../../etc/passwd.pdf") == "passwd.pdf"


def test_resolve_storage_rejects_traversal(tmp_path, monkeypatch):
    from app.cv import storage

    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path)
    with pytest.raises(ValueError):
        storage.resolve_storage_path("../secret.txt")


def test_save_cv_bytes_uses_safe_path(tmp_path, monkeypatch):
    from app.cv import storage

    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path)
    relative, path = save_cv_bytes("profile-id", "../evil.txt", b"hello")
    assert path.exists()
    assert path.read_bytes() == b"hello"
    assert ".." not in relative
    resolved = resolve_storage_path(relative)
    assert resolved == path
