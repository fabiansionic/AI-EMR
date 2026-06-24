#!/usr/bin/env python3
"""Upload AIHub source JSONL files to the configured Fabian Storm bucket."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORM_CONFIG = ROOT / "config" / "storm.json"
DEFAULT_SOURCES_DIR = ROOT / "data" / "storm" / "knowledge-data" / "aihub_71875" / "sources"


def load_config(path: Path) -> dict[str, str]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_storm(args: list[str], timeout: int = 300) -> dict:
    result = subprocess.run(
        ["storm", *args, "--json"],
        check=False,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise SystemExit(f"storm {' '.join(args)} failed: {message}")
    return json.loads(result.stdout)


def upload_sources(bucket_id: str, sources_dir: Path, sleep_seconds: float) -> None:
    paths = sorted(sources_dir.glob("*.jsonl"))
    if not paths:
        raise SystemExit(f"No source JSONL files found under {sources_dir}")

    for path in paths:
        print(f"Uploading {path}")
        response = run_storm(["doc", "upload", bucket_id, str(path)])
        print(json.dumps(response, ensure_ascii=False))
        if sleep_seconds:
            time.sleep(sleep_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storm-config", type=Path, default=DEFAULT_STORM_CONFIG)
    parser.add_argument("--sources-dir", type=Path, default=DEFAULT_SOURCES_DIR)
    parser.add_argument("--bucket-id")
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.storm_config)
    bucket_id = args.bucket_id or config.get("primary_bucket_id")
    if not bucket_id:
        raise SystemExit("bucket id is required, either via --bucket-id or config/storm.json.")
    upload_sources(bucket_id, args.sources_dir, args.sleep_seconds)


if __name__ == "__main__":
    main()
