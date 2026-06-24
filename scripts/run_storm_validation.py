#!/usr/bin/env python3
"""Run a small Storm RAG validation pass against AIHub 71875 QA JSONL."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QA_DIR = ROOT / "data" / "storm" / "knowledge-data" / "aihub_71875" / "qa"
DEFAULT_OUTPUT = ROOT / "data" / "storm" / "knowledge-data" / "aihub_71875" / "validation_results.jsonl"
DEFAULT_STORM_CONFIG = ROOT / "config" / "storm.json"


def iter_validation_items(qa_dir: Path, limit_per_file: int):
    for path in sorted(qa_dir.glob("validation_*.jsonl")):
        emitted = 0
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if emitted >= limit_per_file:
                    break
                item = json.loads(line)
                yield path.name, item
                emitted += 1


def load_storm_config(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def storm_chat(agent_id: str, question: str, timeout: int) -> tuple[str, object]:
    result = subprocess.run(
        ["storm", "chat", agent_id, question, "--json"],
        check=False,
        text=True,
        capture_output=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        return "", {"error": result.stderr.strip() or result.stdout.strip()}

    raw = result.stdout.strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw, raw

    answer = extract_answer(parsed)
    return answer, parsed


def extract_answer(payload: object) -> str:
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict):
        return json.dumps(payload, ensure_ascii=False)

    candidates = [
        payload.get("answer"),
        payload.get("message"),
        payload.get("content"),
        payload.get("text"),
        payload.get("data", {}).get("chat", {}).get("answer")
        if isinstance(payload.get("data"), dict) and isinstance(payload.get("data", {}).get("chat"), dict)
        else None,
        payload.get("data", {}).get("answer") if isinstance(payload.get("data"), dict) else None,
        payload.get("data", {}).get("message") if isinstance(payload.get("data"), dict) else None,
        payload.get("data", {}).get("content") if isinstance(payload.get("data"), dict) else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, str):
            return candidate

    return json.dumps(payload, ensure_ascii=False)


def normalize(value: str) -> str:
    return " ".join(value.lower().split())


def compare(expected: str, actual: str) -> dict[str, bool]:
    expected_norm = normalize(expected)
    actual_norm = normalize(actual)
    return {
        "exact_match": expected_norm == actual_norm,
        "expected_in_actual": bool(expected_norm and expected_norm in actual_norm),
        "actual_in_expected": bool(actual_norm and actual_norm in expected_norm),
    }


def response_bucket_ids(raw: object) -> list[str]:
    if not isinstance(raw, dict):
        return []
    chat = raw.get("data", {}).get("chat") if isinstance(raw.get("data"), dict) else None
    buckets = chat.get("buckets", []) if isinstance(chat, dict) else []
    return [bucket.get("id") for bucket in buckets if isinstance(bucket, dict) and bucket.get("id")]


def run(
    agent_id: str,
    qa_dir: Path,
    output_path: Path,
    limit_per_file: int,
    timeout: int,
    sleep_seconds: float,
    expected_bucket_id: str | None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    matched = 0

    with output_path.open("w", encoding="utf-8") as output:
        for source_file, item in iter_validation_items(qa_dir, limit_per_file):
            total += 1
            answer, raw = storm_chat(agent_id, item["question"], timeout)
            bucket_ids = response_bucket_ids(raw)
            if expected_bucket_id and bucket_ids and expected_bucket_id not in bucket_ids:
                raise SystemExit(
                    f"Storm response used unexpected bucket(s): {bucket_ids}. "
                    f"Expected bucket: {expected_bucket_id}."
                )
            checks = compare(item["answer"], answer)
            matched += int(checks["exact_match"] or checks["expected_in_actual"] or checks["actual_in_expected"])
            record = {
                "source_file": source_file,
                "qa_id": item["metadata"]["qa_id"],
                "department": item["metadata"]["department"],
                "q_type_label": item["metadata"]["q_type_label"],
                "question": item["question"],
                "expected_answer": item["answer"],
                "storm_answer": answer,
                "checks": checks,
                "raw_response": raw,
            }
            output.write(json.dumps(record, ensure_ascii=False))
            output.write("\n")
            print(f"{total:>3} {source_file} qa_id={record['qa_id']} match={checks}")
            if sleep_seconds:
                time.sleep(sleep_seconds)

    print(f"Wrote {total} validation results to {output_path}")
    print(f"Simple lexical matches: {matched}/{total}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("agent_id", nargs="?")
    parser.add_argument("--storm-config", type=Path, default=DEFAULT_STORM_CONFIG)
    parser.add_argument("--expected-bucket-id")
    parser.add_argument("--qa-dir", type=Path, default=DEFAULT_QA_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit-per-file", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--sleep-seconds", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_storm_config(args.storm_config)
    agent_id = args.agent_id or config.get("agent_id")
    expected_bucket_id = args.expected_bucket_id or config.get("primary_bucket_id")
    if not agent_id:
        raise SystemExit("agent_id is required, either as an argument or in config/storm.json.")
    run(agent_id, args.qa_dir, args.output, args.limit_per_file, args.timeout, args.sleep_seconds, expected_bucket_id)


if __name__ == "__main__":
    main()
