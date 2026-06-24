#!/usr/bin/env python3
"""Convert AIHub 71875 ZIP archives into Storm-friendly JSONL files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "aihub" / "09.필수의료_의학지식_데이터"
DEFAULT_OUTPUT = ROOT / "data" / "storm" / "aihub_71875"

SOURCE_META = {
    "TS_국문_기타.zip": ("sources/kr_misc.jsonl", "Korean", "miscellaneous"),
    "TS_국문_온라인_의료_정보_제공_사이트.zip": ("sources/kr_online_medical_sites.jsonl", "Korean", "online_medical_site"),
    "TS_국문_의학_교과서.zip": ("sources/kr_medical_textbooks.jsonl", "Korean", "medical_textbook"),
    "TS_국문_학술_논문_및_저널.zip": ("sources/kr_journals.jsonl", "Korean", "academic_journal"),
    "TS_국문_학회_가이드라인.zip": ("sources/kr_society_guidelines.jsonl", "Korean", "society_guideline"),
    "TS_영문_국제기관_가이드라인.zip": ("sources/en_international_guidelines.jsonl", "English", "international_guideline"),
    "TS_영문_온라인_의료_정보_제공_사이트.zip": ("sources/en_online_medical_sites.jsonl", "English", "online_medical_site"),
    "TS_영문_학술_논문_및_저널.zip": ("sources/en_journals.jsonl", "English", "academic_journal"),
}

DEPARTMENT_BY_ARCHIVE = {
    "내과": ("internal_medicine", 17),
    "산부인과": ("obgyn", 14),
    "소아청소년과": ("pediatrics", 15),
    "응급의학과": ("emergency_medicine", 16),
}

Q_TYPE_LABELS = {
    1: "case_multiple_choice",
    2: "short_answer",
    3: "descriptive_answer",
}


def write_jsonl(path: Path, records) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            output.write("\n")
            count += 1
    return count


def source_records(zip_path: Path):
    _, language, source_category = SOURCE_META[zip_path.name]
    with ZipFile(zip_path) as archive:
        for name in sorted(n for n in archive.namelist() if n.endswith(".json")):
            with archive.open(name) as handle:
                item = json.load(handle)

            yield {
                "id": item["c_id"],
                "text": item.get("content", ""),
                "metadata": {
                    "dataset": "AIHub 71875",
                    "dataset_title": "필수의료 의학지식 데이터",
                    "record_type": "source",
                    "language": language,
                    "source_category": source_category,
                    "source_archive": zip_path.name,
                    "source_file": name.lstrip("/"),
                    "domain_code": item.get("domain"),
                    "source_code": item.get("source"),
                    "source_spec": item.get("source_spec"),
                    "creation_year": item.get("creation_year"),
                },
            }


def infer_department(zip_path: Path) -> tuple[str, int]:
    for korean_name, department in DEPARTMENT_BY_ARCHIVE.items():
        if korean_name in zip_path.name:
            return department
    raise ValueError(f"Could not infer department from {zip_path}")


def qa_records(zip_path: Path, split: str):
    department_name, expected_domain = infer_department(zip_path)
    with ZipFile(zip_path) as archive:
        for name in sorted(n for n in archive.namelist() if n.endswith(".json")):
            with archive.open(name) as handle:
                item = json.load(handle)

            q_type = item.get("q_type")
            yield {
                "id": f"qa_{item['qa_id']}",
                "question": item.get("question", ""),
                "answer": item.get("answer", ""),
                "text": f"Question: {item.get('question', '')}\nAnswer: {item.get('answer', '')}",
                "metadata": {
                    "dataset": "AIHub 71875",
                    "dataset_title": "필수의료 의학지식 데이터",
                    "record_type": "qa",
                    "split": split,
                    "department": department_name,
                    "source_archive": zip_path.name,
                    "source_file": name.lstrip("/"),
                    "qa_id": item.get("qa_id"),
                    "domain_code": item.get("domain"),
                    "expected_domain_code": expected_domain,
                    "q_type": q_type,
                    "q_type_label": Q_TYPE_LABELS.get(q_type, "unknown"),
                },
            }


def convert(input_dir: Path, output_dir: Path) -> None:
    source_dir = input_dir / "3.개방데이터" / "1.데이터" / "Training" / "01.원천데이터"
    train_label_dir = input_dir / "3.개방데이터" / "1.데이터" / "Training" / "02.라벨링데이터"
    val_label_dir = input_dir / "3.개방데이터" / "1.데이터" / "Validation" / "02.라벨링데이터"

    manifest = []

    for zip_path in sorted(source_dir.glob("*.zip")):
        target_rel = SOURCE_META[zip_path.name][0]
        target = output_dir / target_rel
        count = write_jsonl(target, source_records(zip_path))
        manifest.append({"path": target_rel, "records": count, "kind": "source"})

    for split, label_dir in (("training", train_label_dir), ("validation", val_label_dir)):
        for zip_path in sorted(label_dir.glob("*.zip")):
            department_name, _ = infer_department(zip_path)
            target_rel = f"qa/{split}_{department_name}.jsonl"
            target = output_dir / target_rel
            count = write_jsonl(target, qa_records(zip_path, split))
            manifest.append({"path": target_rel, "records": count, "kind": "qa", "split": split})

    write_jsonl(output_dir / "manifest.jsonl", manifest)

    print(f"Wrote Storm JSONL export to {output_dir}")
    for item in manifest:
        print(f"{item['records']:>6} {item['kind']:<6} {item['path']}")


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

