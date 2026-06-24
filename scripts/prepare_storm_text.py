#!/usr/bin/env python3
"""Copy generated AIHub Markdown shards into TXT files accepted by Storm."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "storm_md" / "aihub_71875"
DEFAULT_OUTPUT = ROOT / "data" / "storm_txt" / "knowledge-data" / "aihub_71875"


def convert(input_dir: Path, output_dir: Path) -> None:
    paths = sorted(input_dir.rglob("*.md"))
    if not paths:
        raise SystemExit(f"No Markdown files found under {input_dir}")

    if output_dir.exists():
        for stale_path in output_dir.rglob("*.txt"):
            stale_path.unlink()

    manifest = []
    for path in paths:
        rel = path.relative_to(input_dir)
        target = (output_dir / rel).with_suffix(".txt")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        manifest.append(
            {
                "input_path": str(rel),
                "output_path": str(target.relative_to(output_dir)),
                "bytes": target.stat().st_size,
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(manifest)} TXT files to {output_dir}")
    print(f"Wrote manifest to {manifest_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    convert(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()
