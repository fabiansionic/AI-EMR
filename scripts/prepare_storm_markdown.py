#!/usr/bin/env python3
"""Convert Storm JSONL exports into Markdown shards for document ingestion."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "storm" / "aihub_71875"
DEFAULT_OUTPUT = ROOT / "data" / "storm_md" / "aihub_71875"
DEFAULT_MAX_BYTES = 15_000_000
DEFAULT_MAX_RECORDS = 5_000


def slugify(value: str) -> str:
    value = value.removesuffix(".jsonl")
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return value or "records"


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def format_metadata(metadata: dict[str, Any]) -> str:
    lines = []
    for key in sorted(metadata):
        value = metadata[key]
        if value in (None, "", "null"):
            continue
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def format_record(record: dict[str, Any], fallback_id: str) -> str:
    record_id = clean_text(record.get("id") or record.get("qa_id") or fallback_id)
    metadata = record.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    source_file = clean_text(metadata.get("source_file"))
    heading = f"## Document {record_id}"
    if source_file:
        heading = f"{heading} ({source_file})"
    lines = [heading, ""]

    metadata_text = format_metadata(metadata)
    if metadata_text:
        lines.extend([metadata_text, ""])

    if record.get("question") or record.get("answer"):
        question = clean_text(record.get("question"))
        answer = clean_text(record.get("answer"))
        if question:
            lines.extend(["### Question", "", question, ""])
        if answer:
            lines.extend(["### Answer", "", answer, ""])
    else:
        text = clean_text(record.get("text"))
        if text:
            lines.append(text)
            lines.append("")

    lines.extend(["---", "", ""])
    return "\n".join(lines)


class MarkdownShardWriter:
    def __init__(self, output_dir: Path, stem: str, max_bytes: int, max_records: int) -> None:
        self.output_dir = output_dir
        self.stem = stem
        self.max_bytes = max_bytes
        self.max_records = max_records
        self.part = 0
        self.current_path: Path | None = None
        self.current_handle = None
        self.current_bytes = 0
        self.current_records = 0
        self.total_records = 0
        self.paths: list[Path] = []

    def __enter__(self) -> "MarkdownShardWriter":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        if self.current_handle is not None:
            self.current_handle.close()
            self.current_handle = None

    def rotate(self) -> None:
        self.close()
        self.part += 1
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_path = self.output_dir / f"{self.stem}_part-{self.part:04d}.md"
        self.current_handle = self.current_path.open("w", encoding="utf-8")
        self.paths.append(self.current_path)
        self.current_bytes = 0
        self.current_records = 0
        header = f"# {self.stem} part {self.part:04d}\n\n"
        self.current_handle.write(header)
        self.current_bytes += len(header.encode("utf-8"))

    def write(self, text: str) -> None:
        encoded_len = len(text.encode("utf-8"))
        should_rotate = (
            self.current_handle is None
            or self.current_records >= self.max_records
            or (self.current_records > 0 and self.current_bytes + encoded_len > self.max_bytes)
        )
        if should_rotate:
            self.rotate()
        assert self.current_handle is not None
        self.current_handle.write(text)
        self.current_bytes += encoded_len
        self.current_records += 1
        self.total_records += 1


def convert_file(input_path: Path, input_root: Path, output_root: Path, max_bytes: int, max_records: int) -> dict[str, Any]:
    rel = input_path.relative_to(input_root)
    stem = slugify(input_path.name)
    output_dir = output_root / rel.parent / stem
    output_paths: list[Path] = []
    if output_dir.exists():
        for stale_path in output_dir.glob("*.md"):
            stale_path.unlink()

    with MarkdownShardWriter(output_dir, stem, max_bytes, max_records) as writer:
        with input_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                writer.write(format_record(record, f"{stem}_{line_number}"))
        output_paths = writer.paths
        total_records = writer.total_records

    return {
        "input_path": str(rel),
        "output_paths": [str(path.relative_to(output_root)) for path in output_paths],
        "records": total_records,
    }


def convert(input_dir: Path, output_dir: Path, max_bytes: int, max_records: int) -> None:
    input_paths = sorted(input_dir.rglob("*.jsonl"))
    if not input_paths:
        raise SystemExit(f"No JSONL files found under {input_dir}")

    manifest = []
    for input_path in input_paths:
        item = convert_file(input_path, input_dir, output_dir, max_bytes, max_records)
        manifest.append(item)
        print(f"{item['records']:>6} records -> {len(item['output_paths']):>4} md files  {item['input_path']}")

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote Markdown export to {output_dir}")
    print(f"Wrote manifest to {manifest_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--max-records", type=int, default=DEFAULT_MAX_RECORDS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    convert(args.input_dir, args.output_dir, args.max_bytes, args.max_records)


if __name__ == "__main__":
    main()
