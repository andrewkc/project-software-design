"""Private demo backups; verification restores to an isolated temporary database."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import uuid


FILES = ("database.dump", "media.tar.gz")
MAX_MEDIA_FILES = 10000
MAX_MEDIA_BYTES = 500 * 1024 * 1024
MODEL = "media/ml_models/demand-seed-42.joblib"
MODEL_REPORT = "media/ml_models/demand-seed-42.json"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_member(member):
    path = PurePosixPath(member.name)
    if (not member.name or member.name.startswith("/") or "\\" in member.name
            or not path.parts or path.parts[0] != "media" or ".." in path.parts
            or not (member.isfile() or member.isdir())):
        raise ValueError("Unsafe or unsupported media archive member")
    if member.size < 0 or member.size > MAX_MEDIA_BYTES:
        raise ValueError("Media file exceeds snapshot limit")
    return str(path)


def inspect_media(archive):
    """Validate archive members and the trained model without extracting."""
    hashes = {}
    total = 0
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle:
            name = _safe_member(member)
            if member.isdir():
                continue
            if name in hashes or len(hashes) >= MAX_MEDIA_FILES:
                raise ValueError("Duplicate or excessive media entries")
            total += member.size
            if total > MAX_MEDIA_BYTES:
                raise ValueError("Media archive exceeds snapshot limit")
            content = bundle.extractfile(member)
            if content is None:
                raise ValueError("Media file cannot be read")
            digest = hashlib.sha256()
            for chunk in iter(lambda: content.read(1024 * 1024), b""):
                digest.update(chunk)
            hashes[name] = digest.hexdigest()
        if MODEL not in hashes or MODEL_REPORT not in hashes:
            raise ValueError("Trained model and report are required")
        report_member = bundle.getmember(MODEL_REPORT)
        if report_member.size > 1024 * 1024:
            raise ValueError("Model report is too large")
        report = json.load(bundle.extractfile(report_member))
    if not isinstance(report, dict):
        raise ValueError("Model report is invalid")
    if report.get("artifact") != PurePosixPath(MODEL).name or report.get("artifact_sha256") != hashes[MODEL]:
        raise ValueError("Model does not match its training report")
    return hashes


def load_snapshot(folder):
    root = Path(folder).resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("format") != "bodesmart-snapshot-v1":
        raise ValueError("Snapshot manifest has an unsupported format")
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != set(FILES):
        raise ValueError("Snapshot manifest is incomplete")
    for name in FILES:
        spec = files[name]
        if (not isinstance(spec, dict) or type(spec.get("bytes")) is not int
                or spec["bytes"] <= 0 or not re.fullmatch(r"[0-9a-f]{64}", str(spec.get("sha256", "")))):
            raise ValueError("Snapshot file metadata is invalid")
        path = root / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size != spec["bytes"] or sha256(path) != spec["sha256"]:
            raise ValueError(f"Snapshot file failed integrity check: {name}")
    hashes = inspect_media(root / "media.tar.gz")
    if manifest.get("media_hashes") != hashes:
        raise ValueError("Snapshot media manifest differs from archive")
    return root, manifest


def _docker(compose, service, arguments, input_path=None, output_path=None):
    command = ["docker", "compose", "-f", str(compose), "exec", "-T", service, *arguments]
    source = open(input_path, "rb") if input_path else None
    try:
        if output_path:
            with open(output_path, "wb") as target:
                return subprocess.run(command, stdin=source or subprocess.DEVNULL,
                                      stdout=target, stderr=subprocess.PIPE, check=True)
        return subprocess.run(command, stdin=source or subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    finally:
        if source:
            source.close()


def backup(compose, output):
    root = Path(output).resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    _docker(compose, "db", ["sh", "-c", 'exec pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"'],
            output_path=root / "database.dump")
    _docker(compose, "web", ["tar", "-czf", "-", "-C", "/app/backend", "media"],
            output_path=root / "media.tar.gz")
    hashes = inspect_media(root / "media.tar.gz")
    manifest = {"format": "bodesmart-snapshot-v1",
                "files": {name: {"bytes": (root / name).stat().st_size, "sha256": sha256(root / name)}
                          for name in FILES}, "media_hashes": hashes}
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(root / "manifest.json", 0o600)
    return root


def _restore_db(compose, dump, target):
    if not re.fullmatch(r"(?:verify|restored)_[a-z0-9_]{8,48}", target):
        raise ValueError("Restore target must be a new verify_ or restored_ database")
    created = False
    try:
        _docker(compose, "db", ["sh", "-c", 'createdb -U "$POSTGRES_USER" "$1"', "sh", target])
        created = True
        _docker(compose, "db", ["sh", "-c", 'exec pg_restore --exit-on-error --no-owner --no-acl -U "$POSTGRES_USER" -d "$1"', "sh", target], input_path=dump)
        result = _docker(compose, "db", ["sh", "-c",
            'psql -U "$POSTGRES_USER" -d "$1" -At -c "SELECT (SELECT COUNT(*) FROM core_store), (SELECT COUNT(*) FROM core_user), (SELECT COUNT(*) FROM core_lot)"',
            "sh", target])
        counts = [int(item) for item in result.stdout.decode().strip().split("|")]
        if len(counts) != 3 or min(counts) < 1:
            raise ValueError("Restored demo is missing stores, users or lots")
        return counts
    except Exception:
        if created:
            _docker(compose, "db", ["sh", "-c", 'dropdb -U "$POSTGRES_USER" --if-exists "$1"', "sh", target])
        raise


def verify(compose, folder):
    root, manifest = load_snapshot(folder)
    target = "verify_" + uuid.uuid4().hex[:16]
    created = False
    try:
        counts = _restore_db(compose, root / "database.dump", target)
        created = True
        return {"database_restored": True, "stores": counts[0], "users": counts[1],
                "lots": counts[2], "media_files": len(manifest["media_hashes"])}
    finally:
        if created:
            _docker(compose, "db", ["sh", "-c", 'dropdb -U "$POSTGRES_USER" --if-exists "$1"', "sh", target])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("backup", "verify"))
    parser.add_argument("folder")
    parser.add_argument("--compose", default="compose.production.yaml")
    args = parser.parse_args()
    if args.action == "backup":
        print(f"Snapshot saved to {backup(args.compose, args.folder)}")
    else:
        print(json.dumps(verify(args.compose, args.folder), sort_keys=True))


if __name__ == "__main__":
    main()
