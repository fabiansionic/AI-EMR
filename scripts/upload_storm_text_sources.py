#!/usr/bin/env python3
"""Upload generated AIHub TXT source shards to a Storm bucket."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORM_CONFIG = ROOT / "config" / "storm.json"
DEFAULT_SOURCES_DIR = ROOT / "data" / "storm_txt" / "knowledge-data" / "aihub_71875" / "sources"
DEFAULT_LOG_PATH = ROOT / "data" / "storm_txt" / "knowledge-data" / "aihub_71875" / "upload_results.jsonl"


def load_config(path: Path) -> dict[str, str]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_storm(args: list[str], timeout: int) -> dict[str, Any]:
    result = subprocess.run(
        ["storm", *args, "--json"],
        check=False,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(message)
    return json.loads(result.stdout)


def upload_sources(
    bucket_id: str,
    sources_dir: Path,
    log_path: Path,
    batch_size: int,
    sleep_seconds: float,
    timeout: int,
) -> None:
    paths = sorted(sources_dir.rglob("*.txt"))
    if not paths:
        raise SystemExit(f"No TXT files found under {sources_dir}")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        for index, path in enumerate(paths, start=1):
            batch_number = ((index - 1) // batch_size) + 1
            batch_index = ((index - 1) % batch_size) + 1
            print(f"[batch {batch_number} item {batch_index}/{batch_size}] Uploading {path}")
            item: dict[str, Any] = {
                "batch_number": batch_number,
                "batch_index": batch_index,
                "path": str(path),
            }
            try:
                item["response"] = run_storm(["doc", "upload", bucket_id, str(path)], timeout)
                item["ok"] = True
            except Exception as exc:
                item["ok"] = False
                item["error"] = str(exc)
                log.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
                raise
            log.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
            log.flush()
            if sleep_seconds:
                time.sleep(sleep_seconds)

    print(f"Uploaded {len(paths)} TXT source files to bucket {bucket_id}")
    print(f"Wrote upload log to {log_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storm-config", type=Path, default=DEFAULT_STORM_CONFIG)
    parser.add_argument("--sources-dir", type=Path, default=DEFAULT_SOURCES_DIR)
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--bucket-id")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--timeout", type=int, default=600)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.storm_config)
    bucket_id = args.bucket_id or config.get("primary_bucket_id")
    if not bucket_id:
        raise SystemExit("bucket id is required, either via --bucket-id or config/storm.json.")
    upload_sources(bucket_id, args.sources_dir, args.log_path, args.batch_size, args.sleep_seconds, args.timeout)


if __name__ == "__main__":
    main()
