"""Immutable source snapshots and generation pointers, all below one work directory."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
from datetime import datetime, timezone
import uuid
import zipfile

from filelock import FileLock


MODULE = Path(__file__).resolve().parent
CATALOG = json.loads((MODULE / "sources.json").read_text(encoding="utf-8"))


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def digest_file(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(json_text(value) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def inventory(directory):
    if any(path.is_symlink() or path.is_junction() for path in directory.rglob("*")):
        raise ValueError(f"Snapshot contains links: {directory}")
    return [
        {"path": path.relative_to(directory).as_posix(), "size": path.stat().st_size,
         "sha256": digest_file(path)}
        for path in sorted(directory.rglob("*")) if path.is_file()
    ]


def resolved_path(path):
    value = str(path.resolve())
    # Windows can add the extended-path prefix while another thread creates a parent.
    # Compare the same canonical spelling on both sides of the containment check.
    if os.name == "nt":
        if value.startswith("\\\\?\\UNC\\"):
            value = "\\\\" + value[8:]
        elif value.startswith("\\\\?\\"):
            value = value[4:]
    return Path(value)


def safe_target(directory, name):
    # Backslashes also denote separators in archives produced on Windows.
    relative = Path(name.replace("\\", "/"))
    target = resolved_path(directory / relative)
    if relative.is_absolute() or not target.is_relative_to(resolved_path(directory)):
        raise ValueError(f"Unsafe archive path: {name!r}")
    return target


def extract_archive(archive, destination):
    """Extract ordinary files only. Reject links and entries escaping the destination."""
    destination.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as source:
            for item in source.infolist():
                target = safe_target(destination, item.filename)
                if (item.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError(f"Archive symlink: {item.filename}")
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source.open(item) as reader, target.open("wb") as writer:
                        shutil.copyfileobj(reader, writer)
    elif tarfile.is_tarfile(archive):
        with tarfile.open(archive) as source:
            for item in source:
                target = safe_target(destination, item.name)
                if item.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif item.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source.extractfile(item) as reader, target.open("wb") as writer:
                        shutil.copyfileobj(reader, writer)
                else:
                    raise ValueError(f"Unsupported archive entry: {item.name}")
    else:
        raise ValueError(f"Expected ZIP or TAR archive: {archive}")


class Workspace:
    def __init__(self, root=None):
        self.root = Path(root or os.environ.get("LANGUAGE_RESOURCES_HOME", MODULE / "work")).resolve()

    def lock(self):
        self.root.mkdir(parents=True, exist_ok=True)
        return FileLock(str(self.root / "writer.lock"), timeout=0)

    def staging(self):
        path = self.root / "staging" / uuid.uuid4().hex
        (path / "payload").mkdir(parents=True)
        return path

    def active(self):
        return read_json(self.root / "sources.json", {})

    def snapshot(self, source, snapshot_id=None):
        snapshot_id = snapshot_id or self.active().get(source)
        if not snapshot_id:
            return None
        path = self.root / "snapshots" / source / snapshot_id
        return path, read_json(path / "manifest.json")

    def activate(self, source, stage, metadata):
        files = inventory(stage / "payload")
        if not files:
            raise ValueError(f"Empty source: {source}")
        identity = {"files": files, "versions": metadata.get("versions", {}),
                    "components": metadata["components"], "complete": metadata["complete"]}
        snapshot_id = hashlib.sha256(json_text(identity).encode()).hexdigest()
        previous = self.snapshot(source)
        if previous and all(previous[1].get(key) == value for key, value in identity.items()):
            # Reuse equivalent snapshots also when an earlier identity format was used.
            snapshot_id = previous[1]["id"]
        manifest = {**metadata, "source": source, "id": snapshot_id, "created_at": utc_now(),
                    "files": files, "bytes": sum(item["size"] for item in files),
                    "url": CATALOG[source]["url"], "license": CATALOG[source]["license"]}
        atomic_json(stage / "manifest.json", manifest)
        destination = self.root / "snapshots" / source / snapshot_id
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            stage.rename(destination)
        else:
            if not stage.resolve().is_relative_to((self.root / "staging").resolve()):
                raise ValueError(f"Unexpected staging directory: {stage}")
            shutil.rmtree(stage)
        active = self.active()
        active[source] = snapshot_id
        atomic_json(self.root / "sources.json", active)
        return manifest

    def verify(self, source):
        snapshot = self.snapshot(source)
        if snapshot and inventory(snapshot[0] / "payload") != snapshot[1]["files"]:
            raise ValueError(f"Source snapshot changed on disk: {source}")
        return snapshot

    def generation(self):
        return read_json(self.root / "current.json")

    def database(self, generation=None):
        generation = generation if generation is not None else self.generation()
        return self.root / "warehouse" / generation["database"] if generation else None
