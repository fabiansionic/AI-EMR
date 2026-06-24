#!/usr/bin/env python3
"""Convert AIHub 566 TXT/JSON voice-data files into STORM-ready TXT files."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "aihub" / "voice-data" / "aihub_566"
DEFAULT_OUTPUT = ROOT / "data" / "storm_txt" / "voice-data" / "aihub_566"

AUDIO_SUFFIXES = {".m4a", ".wav"}


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def iter_json_lines(payload: Any) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    info_items = payload.get("info") if isinstance(payload, dict) else None
    if not isinstance(info_items, list):
        return lines

    for info in info_items:
        if not isinstance(info, dict):
            continue
        for annotation in info.get("annotations") or []:
            if not isinstance(annotation, dict):
                continue
            for line in annotation.get("lines") or []:
                if isinstance(line, dict):
                    lines.append(line)
    return lines


def json_to_text(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    lines = [f"# {path.stem}", "", f"source_json: {path.name}", ""]

    if isinstance(payload, dict):
        dataset = payload.get("dataset")
        if isinstance(dataset, dict):
            lines.append("## Dataset")
            for key in ("identifier", "name", "src_path", "label_path", "category", "type"):
                value = clean(dataset.get(key))
                if value:
                    lines.append(f"{key}: {value}")
            lines.append("")

        info_items = payload.get("info")
        if isinstance(info_items, list):
            lines.append("## Records")
            for info in info_items:
                if not isinstance(info, dict):
                    continue
                for key in ("id", "filename", "title", "mediatype", "medianame", "category", "date", "size"):
                    value = clean(info.get(key))
                    if value:
                        lines.append(f"{key}: {value}")
                lines.append("")

    sentence_lines = iter_json_lines(payload)
    if sentence_lines:
        lines.append("## Transcript")
        for item in sentence_lines:
            speaker = item.get("speaker") if isinstance(item.get("speaker"), dict) else {}
            speaker_bits = [
                clean(speaker.get("id")),
                clean(speaker.get("sex")),
                clean(speaker.get("age")),
            ]
            speaker_label = " / ".join(bit for bit in speaker_bits if bit)
            text = clean(item.get("norm_text") or item.get("text"))
            speech_act = clean(item.get("speechAct"))
            prefix = f"[{speaker_label}]" if speaker_label else "[speaker]"
            if text:
                lines.append(f"{prefix} {text}")
            if speech_act:
                lines.append(f"speechAct: {speech_act}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def convert(input_dir: Path, output_dir: Path) -> None:
    input_paths = [
        path
        for path in sorted(input_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() not in AUDIO_SUFFIXES and path.name != ".gitkeep"
    ]
    txt_paths = [path for path in input_paths if path.suffix.lower() == ".txt"]
    json_paths = [path for path in input_paths if path.suffix.lower() == ".json"]

    if not txt_paths and not json_paths:
        raise SystemExit(f"No TXT or JSON files found under {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []

    for path in txt_paths:
        rel = path.relative_to(input_dir)
        target = output_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        manifest.append({"input_path": str(rel), "output_path": str(target.relative_to(output_dir)), "kind": "txt"})

    for path in json_paths:
        rel = path.relative_to(input_dir)
        target = (output_dir / rel).with_suffix(".txt")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json_to_text(path), encoding="utf-8")
        manifest.append({"input_path": str(rel), "output_path": str(target.relative_to(output_dir)), "kind": "json"})

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(manifest)} voice TXT files to {output_dir}")
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
