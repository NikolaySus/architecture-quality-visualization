"""Public operations shared by the CLI and the read-only status view."""

from pathlib import Path
import shutil
import tarfile
import traceback
import zipfile

from .downloads import download_source, inspect_source
from .storage import CATALOG, atomic_json, extract_archive, read_json, utc_now
from .warehouse import input_signature, rebuild


def record_attempt(workspace, source, value):
    path = workspace.root / "attempts.json"
    attempts = read_json(path, {})
    attempts[source] = {"at": utc_now(), **value}
    atomic_json(path, attempts)


def download(workspace, sources=None):
    selected = list(sources or CATALOG)
    unknown = set(selected) - CATALOG.keys()
    if unknown:
        raise ValueError(f"Unknown sources: {sorted(unknown)}")
    outcomes = {}
    with workspace.lock():
        for source in selected:
            print(f"Download {source}", flush=True)
            stage = workspace.staging()
            try:
                previous = workspace.verify(source)
                metadata = download_source(source, stage, previous)
                manifest = workspace.activate(source, stage, metadata)
                result = {"status": "ok" if manifest["complete"] else "partial",
                          "snapshot": manifest["id"], "bytes": manifest["bytes"],
                          "issues": manifest["issues"], "components": manifest["components"]}
            except Exception as error:
                result = {"status": "error", "error": str(error), "staging": str(stage)}
                atomic_json(stage / "error.json", {"traceback": traceback.format_exc()})
            record_attempt(workspace, source, result)
            outcomes[source] = result
            print(f"  {source}: {result['status']}", flush=True)
    return outcomes


def import_local(workspace, source, path, complete=False):
    if source not in CATALOG:
        raise ValueError(f"Unknown source: {source}")
    path = Path(path).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    if workspace.root.is_relative_to(path):
        raise ValueError("Import directory cannot contain the work directory")
    with workspace.lock():
        stage = workspace.staging()
        payload = stage / "payload"
        previous = None
        try:
            if path.is_symlink() or path.is_junction():
                raise ValueError("Import links are unsupported")
            if path.is_dir():
                if any(item.is_symlink() or item.is_junction() for item in path.rglob("*")):
                    raise ValueError("Import directory contains links")
                shutil.copytree(path, payload, dirs_exist_ok=True)
            elif zipfile.is_zipfile(path) or tarfile.is_tarfile(path):
                extract_archive(path, payload)
            else:
                if source == "framebank" and path.name == "exampleindex.csv":
                    previous = workspace.verify(source)
                    if previous:
                        shutil.copytree(previous[0] / "payload", payload, dirs_exist_ok=True)
                        for old_examples in payload.rglob("exampleindex.csv"):
                            old_examples.unlink()
                shutil.copyfile(path, payload / path.name)
            components = inspect_source(source, payload)
            issues = [] if complete else ["Completeness of a manual export has not been asserted; use --complete after verification"]
            manifest = workspace.activate(source, stage, {
                "versions": {**(previous[1].get("versions", {}) if previous else {}),
                             "manual": "content-addressed"}, "components": components,
                "complete": complete and all(item["status"] == "available" for item in components),
                "issues": issues, "acquisition": "manual", "imported_from": str(path),
                "base_snapshot": previous[1]["id"] if previous else None})
            record_attempt(workspace, source, {"status": "ok" if manifest["complete"] else "partial"})
            return {"source": source, "snapshot": manifest["id"], "complete": manifest["complete"],
                    "components": components}
        except Exception as error:
            record_attempt(workspace, source, {"status": "error", "error": str(error), "staging": str(stage)})
            raise


def sync(workspace, sources=None, force=False):
    outcomes = download(workspace, sources)
    generation = rebuild(workspace, force)
    return {"downloads": outcomes, "generation": generation}


def status(workspace):
    generation = workspace.generation()
    active = workspace.active()
    attempts = read_json(workspace.root / "attempts.json", {})
    rows = []
    for source, config in CATALOG.items():
        snapshot = workspace.snapshot(source, active[source]) if source in active else None
        manifest = snapshot[1] if snapshot else {}
        rows.append({"source": source, "title": config["title"], "available": bool(snapshot),
                     "complete": manifest.get("complete", False), "snapshot": manifest.get("id"),
                     "bytes": manifest.get("bytes", 0), "created_at": manifest.get("created_at"),
                     "components": manifest.get("components", []), "issues": manifest.get("issues", []),
                     "last_attempt": attempts.get(source),
                     "warehouse_snapshot": generation["inputs"]["snapshots"].get(source) if generation else None})
    signature, _ = input_signature(workspace, active)
    stale = not generation or generation["signature"] != signature or not workspace.database(generation).exists()
    return {"sources": rows, "generation": generation, "stale": stale,
            "last_build": read_json(workspace.root / "build.json")}
