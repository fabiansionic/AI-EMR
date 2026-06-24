#!/usr/bin/env python3
"""Native AIHub downloader that mirrors aihubshell's public HTTP flow."""

from __future__ import annotations

import argparse
import os
import re
import sys
import tarfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data" / "aihub"
DEFAULT_ENV_FILE = ROOT / ".env"
BASE_URL = "https://api.aihub.or.kr"
API_VERSION = "0.6"


def load_env(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def api_key() -> str:
    key = os.environ.get("AIHUB_API_KEY") or os.environ.get("AIHUB_APIKEY")
    if not key:
        raise SystemExit("AIHUB_API_KEY or AIHUB_APIKEY is required.")
    return key


def read_text(url: str) -> str:
    try:
        with urlopen(url) as response:
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if body:
            return body
        raise SystemExit(f"HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise SystemExit(f"Network error: {exc.reason}") from exc


def list_dataset(dataset_key: str | None) -> None:
    if dataset_key:
        url = f"{BASE_URL}/info/{dataset_key}.do"
    else:
        url = f"{BASE_URL}/info/dataset.do"
    print(read_text(url))


def download_dataset(dataset_key: str, file_keys: str, data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    tar_path = data_dir / "download.tar"
    url = f"{BASE_URL}/down/{API_VERSION}/{dataset_key}.do?fileSn={file_keys}"
    headers = {"apikey": api_key()}

    print(f"Downloading dataset {dataset_key} to {tar_path}")
    request = Request(url, headers=headers)

    try:
        with urlopen(request) as response, tar_path.open("wb") as output:
            status = getattr(response, "status", None)
            if status != 200:
                body = response.read().decode("utf-8", errors="replace")
                raise SystemExit(f"Download failed with HTTP {status}: {body}")

            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        tar_path.unlink(missing_ok=True)
        raise SystemExit(f"Download failed with HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        tar_path.unlink(missing_ok=True)
        raise SystemExit(f"Network error: {exc.reason}") from exc

    print("Extracting download.tar")
    with tarfile.open(tar_path) as archive:
        safe_extract(archive, data_dir)

    print("Merging split zip parts")
    merge_parts(data_dir)
    tar_path.unlink(missing_ok=True)
    print("Done")


PART_RE = re.compile(r"^(?P<prefix>.+)\.part(?P<offset>\d+)$")


def safe_extract(archive: tarfile.TarFile, data_dir: Path) -> None:
    base = data_dir.resolve()
    for member in archive.getmembers():
        target = (data_dir / member.name).resolve()
        if not str(target).startswith(str(base) + os.sep):
            raise SystemExit(f"Refusing unsafe tar member: {member.name}")
    archive.extractall(data_dir)


def merge_parts(data_dir: Path) -> None:
    groups: dict[Path, list[tuple[int, Path]]] = {}

    for path in data_dir.rglob("*.part*"):
        match = PART_RE.match(path.name)
        if not match:
            continue

        target = path.with_name(match.group("prefix"))
        groups.setdefault(target, []).append((int(match.group("offset")), path))

    for target, parts in groups.items():
        parts.sort(key=lambda item: item[0])
        print(f"Merging {target.relative_to(data_dir)}")
        with target.open("wb") as output:
            for _, part_path in parts:
                with part_path.open("rb") as source:
                    while True:
                        chunk = source.read(1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)

        for _, part_path in parts:
            part_path.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List datasets or files")
    list_parser.add_argument("dataset_key", nargs="?")

    download_parser = subparsers.add_parser("download", help="Download dataset")
    download_parser.add_argument("dataset_key")
    download_parser.add_argument("file_keys", nargs="?", default="all")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_env(args.env_file)

    if args.command == "list":
        list_dataset(args.dataset_key)
    elif args.command == "download":
        download_dataset(args.dataset_key, args.file_keys, args.data_dir)
    else:
        raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
