"""Adversarial snapshot checks before a Docker restore is attempted."""

import hashlib
import io
import json
import tarfile

import pytest

from scripts import demo_snapshot as snapshot


def media_entries(model=b"trained-model", report=None):
    report = report if report is not None else json.dumps({
        "artifact": "demand-seed-42.joblib",
        "artifact_sha256": hashlib.sha256(model).hexdigest(),
    }).encode()
    return [(snapshot.MODEL, model), (snapshot.MODEL_REPORT, report),
            ("media/photos/product.jpg", b"photo bytes")]


def make_archive(path, entries):
    with tarfile.open(path, "w:gz") as archive:
        for name, content in entries:
            info = tarfile.TarInfo(name)
            if isinstance(content, tuple):
                info.type, info.linkname = content
                archive.addfile(info)
            else:
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))


@pytest.fixture
def valid_snapshot(tmp_path):
    dump = tmp_path / "database.dump"
    dump.write_bytes(b"PGDMP version and data")
    archive = tmp_path / "media.tar.gz"
    make_archive(archive, media_entries())
    manifest = {"format": "bodesmart-snapshot-v1", "files": {
        name: {"bytes": (tmp_path / name).stat().st_size, "sha256": snapshot.sha256(tmp_path / name)}
        for name in snapshot.FILES}, "media_hashes": snapshot.inspect_media(archive)}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


BAD_PATHS = [
    "", "/", "/media/a", "../media/a", "media/../a", "media/a/../../b",
    "other/a", "Media/a", "media\\a", "\\media\\a", "media/C:\\a",
    "media/..", "media/../../etc", "media/a\\b", "media\\..\\a",
    "media/./../a", "media/a/../../b", "media/a/../../../etc", "media/a\\..\\b",
    "/tmp/media/a", "C:/media/a", "media/a/b/../../../c",
]


@pytest.mark.parametrize("name", BAD_PATHS)
def test_unsafe_archive_paths_are_rejected(name):
    with pytest.raises(ValueError):
        snapshot._safe_member(tarfile.TarInfo(name))


@pytest.mark.parametrize("member_type", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE])
def test_links_and_devices_are_rejected(member_type):
    info = tarfile.TarInfo("media/ml_models/unsafe")
    info.type = member_type
    with pytest.raises(ValueError):
        snapshot._safe_member(info)


BAD_TARGETS = [
    "", "postgres", "dessof", "template0", "template1", "verify", "verify_",
    "restored", "restored_", "verify_x", "restored_x", "verify_1234567",
    "restored_1234567", "verify_UPPERCASE", "restored_UPPERCASE",
    "verify_abc-defgh", "verify_abc defgh", "verify_abc;dropdb",
    "verify_abcdefgh/other", "verify_abcdefgh\\other", "verify_abcdefgh\n",
    "verify_" + "a" * 49, "restored_" + "a" * 49,
    "production_abcdefgh", "verify_ábcd1234",
]


@pytest.mark.parametrize("target", BAD_TARGETS)
def test_restore_never_accepts_existing_or_unsafe_target(valid_snapshot, target, monkeypatch):
    monkeypatch.setattr(snapshot, "_docker", lambda *args, **kwargs: pytest.fail("Docker must not run"))
    with pytest.raises(ValueError):
        snapshot._restore_db("compose.test.yaml", valid_snapshot / "database.dump", target)


def bad_manifest_changes():
    cases = []
    cases += [("format", value) for value in [None, "", "v1", "bodesmart-snapshot-v2", 1, []]]
    cases += [("files", value) for value in [None, "", [], 1, {}, {"database.dump": {}}]]
    cases += [("size", value) for value in [None, "", 0, -1, True, False, 1.2, [], {}, 1, 10]]
    cases += [("hash", value) for value in [None, "", "a", "x" * 64, "A" * 64,
              "a" * 63, "a" * 65, 0, []]]
    cases += [("media_hashes", value) for value in [None, "", [], {}, {snapshot.MODEL: "wrong"}]]
    return cases


@pytest.mark.parametrize("field,value", bad_manifest_changes())
def test_tampered_manifest_fails_before_restore(valid_snapshot, field, value, monkeypatch):
    path = valid_snapshot / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if field == "size":
        data["files"]["database.dump"]["bytes"] = value
    elif field == "hash":
        data["files"]["database.dump"]["sha256"] = value
    else:
        data[field] = value
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(snapshot, "_docker", lambda *args, **kwargs: pytest.fail("Docker must not run"))
    with pytest.raises((ValueError, TypeError)):
        snapshot.verify("compose.test.yaml", valid_snapshot)


def bad_archive_cases():
    good = media_entries()
    wrong_report = json.dumps({"artifact": "other.joblib", "artifact_sha256": "0" * 64}).encode()
    return [
        [], good[1:], good[:1], good[::2],
        [(snapshot.MODEL, b"tampered"), *good[1:]],
        [(snapshot.MODEL, good[0][1]), (snapshot.MODEL_REPORT, wrong_report)],
        [(snapshot.MODEL, good[0][1]), (snapshot.MODEL_REPORT, b"not-json")],
        [(snapshot.MODEL, good[0][1]), (snapshot.MODEL_REPORT, b"[]")],
        [*good, good[0]], [*good, good[1]],
        [*good, ("../outside", b"escape")],
        [*good, ("media/../outside", b"escape")],
        [*good, ("media/bad\\name", b"escape")],
        [*good, ("media/link", (tarfile.SYMTYPE, "/etc/passwd"))],
        [*good, ("media/hardlink", (tarfile.LNKTYPE, snapshot.MODEL))],
    ]


@pytest.mark.parametrize("entries", bad_archive_cases())
def test_bad_media_archive_fails_integrity_check(tmp_path, entries):
    archive = tmp_path / "media.tar.gz"
    make_archive(archive, entries)
    with pytest.raises((ValueError, KeyError)):
        snapshot.inspect_media(archive)


def test_valid_snapshot_includes_model_and_photo(valid_snapshot):
    root, manifest = snapshot.load_snapshot(valid_snapshot)
    assert root == valid_snapshot
    assert snapshot.MODEL in manifest["media_hashes"]
    assert "media/photos/product.jpg" in manifest["media_hashes"]


def test_changed_dump_is_detected(valid_snapshot):
    with (valid_snapshot / "database.dump").open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ValueError):
        snapshot.load_snapshot(valid_snapshot)


def test_missing_manifest_is_detected(valid_snapshot):
    (valid_snapshot / "manifest.json").unlink()
    with pytest.raises(FileNotFoundError):
        snapshot.load_snapshot(valid_snapshot)
