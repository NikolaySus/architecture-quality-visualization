"""Source acquisition. All writes are confined to a new staging directory."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import gdown

from .storage import CATALOG, atomic_json, extract_archive, read_json, safe_target


def request(url, headers=None):
    return urllib.request.urlopen(urllib.request.Request(
        url, headers={"User-Agent": "language-resources/1.0", **(headers or {})}), timeout=60)


def fetch_file(url, destination, previous=None, validators=None):
    headers = {}
    if previous and previous.exists() and validators:
        if validators.get("etag"):
            headers["If-None-Match"] = validators["etag"]
        elif validators.get("last_modified"):
            headers["If-Modified-Since"] = validators["last_modified"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            with request(url, headers) as response, destination.open("wb") as output:
                shutil.copyfileobj(response, output, length=1024 * 1024)
                output.flush()
                expected = response.headers.get("Content-Length")
                if expected and destination.stat().st_size != int(expected):
                    raise OSError(f"Incomplete download: {url}")
                return {"etag": response.headers.get("ETag"),
                        "last_modified": response.headers.get("Last-Modified")}
        except urllib.error.HTTPError as error:
            if error.code == 304 and previous:
                shutil.copyfile(previous, destination)
                return validators
            if error.code < 500 and error.code != 429:
                raise
            if attempt == 2:
                raise
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(attempt + 1)


def github_copy(repo, destination, stage, previous, versions):
    """Resolve a moving branch once, then download its immutable commit archive."""
    with request(f"https://api.github.com/repos/{repo}/commits/HEAD") as response:
        revision = json.load(response)["sha"]
    versions[repo] = revision
    repo_name = repo.split("/")[-1]
    old_directory = previous[0] / "payload" / repo_name if previous else None
    if previous and previous[1].get("versions", {}).get(repo) == revision and old_directory.exists():
        shutil.copytree(old_directory, destination / repo_name)
        return
    archive = stage / (repo_name + ".zip")
    fetch_file(f"https://codeload.github.com/{repo}/zip/{revision}", archive)
    unpacked = stage / (repo_name + "-unpacked")
    extract_archive(archive, unpacked)
    roots = list(unpacked.iterdir())
    if len(roots) != 1 or not roots[0].is_dir():
        raise ValueError(f"Unexpected GitHub archive: {repo}")
    roots[0].rename(destination / repo_name)


def files_named(payload, name):
    return sorted(payload.rglob(name))


def component(name, available, detail=""):
    return {"name": name, "status": "available" if available else "missing", "detail": detail}


def inspect_source(source, payload):
    """Check required components and minimally validate their source format."""
    if source == "ud":
        files = list(payload.rglob("*.conllu"))
        if not files:
            raise ValueError("No CoNLL-U files found")
        result = []
        for corpus in ["syntagrus", "taiga", "gsd", "pud", "poetry"]:
            found = [file for file in files if file.name.startswith(f"ru_{corpus}-ud-")]
            result.append(component(corpus, bool(found)))
        return result
    if source == "ruwordnet":
        files = list(payload.rglob("*.db")) + list(payload.rglob("*.sqlite"))
        if len(files) != 1:
            raise ValueError("Expected one RuWordNet SQLite database")
        with closing(sqlite3.connect(files[0].resolve().as_uri() + "?mode=ro", uri=True)) as connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"sense", "synset"} <= tables:
                raise ValueError("Missing RuWordNet sense/synset tables")
            if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Invalid RuWordNet database")
        return [component("database", True)]
    if source == "framebank":
        names = ["framebank_dict_cx.txt", "framebank_dict_cx_items.txt",
                 "framebank_anno_ex_items.txt", "framebank_anno_ex_circ.txt", "exampleindex.csv"]
        result = [component(name, bool(files_named(payload, name))) for name in names]
        if not any(item["status"] == "available" for item in result[:4]):
            raise ValueError("No FrameBank tables found")
        return result
    if source == "semontocor":
        if not list(payload.rglob("*.svg")):
            raise ValueError("No SemOntoCor SVG graphs found; supported first-stage format is Graphviz SVG")
        return [component("svg_graphs", True)]
    graphs = files_named(payload, "massive_amr.jsonl")
    if not graphs:
        raise ValueError("Missing massive_amr.jsonl")
    with graphs[0].open(encoding="utf-8-sig") as stream:
        first = json.loads(next(stream))
    if "raw_amr" not in first:
        raise ValueError("Invalid MASSIVE-AMR record")
    return [component("graphs", True), component("ru-RU", bool(files_named(payload, "ru-RU.jsonl"))),
            component("en-US", bool(files_named(payload, "en-US.jsonl")))]


def download_framebank_examples(url, destination):
    """Resolve the public Mail.ru link using its public file/dispatcher API."""
    public_key = urllib.parse.urlsplit(url).path.split("/public/", 1)[-1]
    query = urllib.parse.urlencode({"public_key": public_key, "api": "2"})
    with request("https://cloud.mail.ru/api/v2/file?" + query) as response:
        file_info = json.load(response)
    if file_info.get("status") != 200 or file_info["body"].get("type") != "file":
        raise ValueError("Cloud link does not expose a public file; import exampleindex.csv manually")
    with request("https://cloud.mail.ru/api/v2/dispatcher?" + query) as response:
        dispatch = json.load(response)
    server = dispatch["body"]["weblink_get"][0]["url"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    fetch_file(server.rstrip("/") + "/" + urllib.parse.quote(public_key, safe="/"), destination)
    with destination.open("rb") as stream:
        if b"<html" in stream.read(512).lower():
            raise ValueError("Cloud returned an HTML page instead of exampleindex.csv")


def download_source(source, stage, previous=None):
    config = CATALOG[source]
    payload = stage / "payload"
    versions = {}
    issues = []
    http = {}
    for repo in config.get("repositories", []):
        github_copy(repo, payload, stage, previous, versions)
    if source == "ruwordnet":
        old = previous[0] / "payload" / "ruwordnet-2021.db" if previous else None
        validators = previous[1].get("http", {}).get("database") if previous else None
        http["database"] = fetch_file(config["url"], payload / "ruwordnet-2021.db", old, validators)
        versions["release"] = "RuWordNet 2.0 / wrapper 0.0.4"
    elif source == "framebank":
        destination = payload / "exampleindex.csv"
        try:
            download_framebank_examples(config["examples_url"], destination)
        except Exception as error:
            destination.unlink(missing_ok=True)
            issues.append(f"exampleindex.csv: {error}")
            if previous:
                old_examples = files_named(previous[0] / "payload", "exampleindex.csv")
                if old_examples:
                    shutil.copyfile(old_examples[0], destination)
                    issues.append("Previous exampleindex.csv retained; remote update could not be checked")
    elif source == "semontocor":
        # gdown's embedded folder view supports listings beyond Drive's first 50 items.
        entries = gdown.download_folder(config["url"], quiet=True, skip_download=True,
                                        use_cookies=False, timeout=60)
        if not entries:
            raise ValueError("Empty Drive folder listing")
        seen = set()
        cache = stage.parent.parent / "cache" / "drive"
        cache.mkdir(parents=True, exist_ok=True)
        def download_entry(entry):
            path = safe_target(payload, entry.path)
            path.parent.mkdir(parents=True, exist_ok=True)
            cached = safe_target(cache, entry.id)
            validator_path = cached.with_suffix(".json")
            try:
                validators = fetch_file("https://drive.google.com/uc?export=download&id=" + entry.id,
                                        path, cached, read_json(validator_path))
                if path.suffix.lower() == ".svg":
                    if ET.parse(path).getroot().tag != "{http://www.w3.org/2000/svg}svg":
                        raise ValueError("Expected SVG")
            except (urllib.error.HTTPError, ET.ParseError, ValueError):
                downloaded = gdown.download(id=entry.id, output=str(path), quiet=True,
                                            use_cookies=False, timeout=60, retries=2)
                if not downloaded:
                    raise ValueError(f"Drive file could not be downloaded: {entry.path}")
                validators = {}
                if path.suffix.lower() == ".svg":
                    if ET.parse(path).getroot().tag != "{http://www.w3.org/2000/svg}svg":
                        raise ValueError(f"Expected SVG: {entry.path}")
            shutil.copyfile(path, cached)
            atomic_json(validator_path, validators)
        for entry in entries:
            path = safe_target(payload, entry.path)
            if path in seen:
                raise ValueError(f"Duplicate Drive path: {entry.path}")
            seen.add(path)
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(download_entry, entry) for entry in entries]
            try:
                for number, future in enumerate(as_completed(futures), 1):
                    future.result()
                    if number % 100 == 0:
                        print(f"  SemOntoCor {number}/{len(entries)}", flush=True)
            except Exception:
                for future in futures:
                    future.cancel()
                raise
        counts = {}
        for entry in entries:
            parent = str(Path(entry.path).parent)
            counts[parent] = counts.get(parent, 0) + 1
        if any(count == 50 for count in counts.values()):
            issues.append("A folder lists exactly 50 files; verify listing completeness using a manual export")
        versions["drive_file_ids"] = sorted(entry.id for entry in entries)
    elif source == "amr":
        archive = stage / "massive-1.1.tar.gz"
        http["massive"] = fetch_file(config["massive_url"], archive)
        # Retain exactly the original ru/en files and license as source material.
        with tarfile.open(archive) as bundle:
            for item in bundle:
                if Path(item.name).name not in {"ru-RU.jsonl", "en-US.jsonl", "LICENSE"}:
                    continue
                if not item.isfile():
                    raise ValueError(f"Unexpected MASSIVE entry: {item.name}")
                target = safe_target(payload / "MASSIVE-1.1", item.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(item) as reader, target.open("wb") as output:
                    shutil.copyfileobj(reader, output)
        versions["massive"] = "1.1"
    components = inspect_source(source, payload)
    complete = all(item["status"] == "available" for item in components) and not issues
    return {"versions": versions, "components": components, "complete": complete,
            "issues": issues, "http": http, "acquisition": "download"}
