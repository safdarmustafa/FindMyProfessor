from pathlib import Path

import pytest

from app.cv.storage import (
    cv_file_exists,
    read_cv_bytes,
    resolve_storage_path,
    safe_filename,
    save_cv_bytes,
)


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


# ---------------------------------------------------------------------------
# Local-disk backend (default: SUPABASE_CV_BUCKET unset) — persistence
# reference, attachment retrieval, and missing-object handling.
# ---------------------------------------------------------------------------

def test_read_cv_bytes_local_disk_returns_saved_content(tmp_path, monkeypatch):
    from app.cv import storage

    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path)
    relative, _path = save_cv_bytes("profile-a", "resume.pdf", b"cv content")
    assert read_cv_bytes(relative) == b"cv content"


def test_read_cv_bytes_local_disk_missing_object_raises(tmp_path, monkeypatch):
    from app.cv import storage

    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path)
    with pytest.raises(FileNotFoundError):
        read_cv_bytes("profile-a/nonexistent-cv/resume.pdf")


def test_cv_file_exists_local_disk(tmp_path, monkeypatch):
    from app.cv import storage

    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path)
    relative, _path = save_cv_bytes("profile-a", "resume.pdf", b"cv content")
    assert cv_file_exists(relative) is True
    assert cv_file_exists("profile-a/nonexistent-cv/resume.pdf") is False
    assert cv_file_exists("") is False


# ---------------------------------------------------------------------------
# Supabase Storage backend (SUPABASE_CV_BUCKET configured) — same contract,
# backed by a fake bucket standing in for storage3's SyncBucketProxy so
# these tests never touch a real Supabase project. This is the path used
# once the bucket is provisioned in production (see final report for the
# manual dashboard steps).
# ---------------------------------------------------------------------------

class _FakeStorageBucket:
    """Stands in for storage3's SyncBucketProxy (.upload/.download/.list)."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.uploads: list[tuple[str, dict]] = []

    def upload(self, path, file, file_options=None):
        self.objects[path] = file
        self.uploads.append((path, file_options or {}))
        return {"path": path}

    def download(self, path, options=None, query_params=None):
        if path not in self.objects:
            raise Exception(f"Object not found: {path}")
        return self.objects[path]

    def list(self, path=None, options=None):
        prefix = f"{path}/" if path else ""
        names = set()
        for key in self.objects:
            if key.startswith(prefix):
                names.add(key[len(prefix):].split("/", 1)[0])
        return [{"name": name} for name in names]


@pytest.fixture
def fake_supabase_bucket(monkeypatch):
    from app.cv import storage

    monkeypatch.setattr(storage, "SUPABASE_CV_BUCKET", "cv-uploads")
    fake = _FakeStorageBucket()
    monkeypatch.setattr(storage, "_bucket", lambda: fake)
    return fake


def test_save_cv_bytes_uploads_to_supabase_storage_when_bucket_configured(
    fake_supabase_bucket, tmp_path, monkeypatch
):
    from app.cv import storage

    # Local disk must not be touched at all when the bucket backend is active.
    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path / "unused")

    relative, local_path = save_cv_bytes("profile-b", "My CV.pdf", b"pdf bytes")

    assert local_path is None
    assert relative in fake_supabase_bucket.objects
    assert fake_supabase_bucket.objects[relative] == b"pdf bytes"
    assert not (tmp_path / "unused").exists()


def test_read_cv_bytes_supabase_storage_returns_uploaded_content(fake_supabase_bucket):
    relative, _ = save_cv_bytes("profile-b", "cv.pdf", b"hello from storage")
    assert read_cv_bytes(relative) == b"hello from storage"


def test_read_cv_bytes_supabase_storage_missing_object_raises(fake_supabase_bucket):
    with pytest.raises(FileNotFoundError):
        read_cv_bytes("profile-b/missing-cv/cv.pdf")


def test_cv_file_exists_supabase_storage(fake_supabase_bucket):
    relative, _ = save_cv_bytes("profile-b", "cv.pdf", b"content")
    assert cv_file_exists(relative) is True
    assert cv_file_exists("profile-b/missing-cv/cv.pdf") is False
