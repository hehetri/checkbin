#!/usr/bin/env python3
"""Extract entries from a check.bin-like file."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ENTRY_SIZE = 260
DEFAULT_HEADER = (2008, 1, 7)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract entries from a check.bin-like file.")
    parser.add_argument("input", type=Path, help="Path to the .bin file")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output path for JSON (defaults to stdout)",
    )
    return parser.parse_args()


def parse_entries(data: bytes) -> dict:
    if len(data) < 16:
        raise ValueError("File too small to contain header")

    header = [int.from_bytes(data[i:i + 4], "little") for i in range(0, 16, 4)]
    count = header[3]

    expected_size = 16 + count * ENTRY_SIZE + count * 4
    if len(data) != expected_size:
        raise ValueError(
            f"Unexpected file size: {len(data)} bytes (expected {expected_size})")

    entries: list[str] = []
    for idx in range(count):
        start = 16 + idx * ENTRY_SIZE
        chunk = data[start:start + ENTRY_SIZE]
        text = chunk.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
        entries.append(text)

    trailer_start = 16 + count * ENTRY_SIZE
    trailer = data[trailer_start:]
    if len(trailer) != count * 4:
        raise ValueError(
            f"Unexpected trailer size: {len(trailer)} bytes (expected {count * 4})"
        )
    metadata = [
        int.from_bytes(trailer[i:i + 4], "little")
        for i in range(0, len(trailer), 4)
    ]

    return {
        "header": {
            "magic": header[0],
            "version": header[1],
            "flags": header[2],
            "count": header[3],
        },
        "entries": entries,
        "metadata": metadata,
    }


def main() -> int:
    args = parse_args()
    data = args.input.read_bytes()
    payload = parse_entries(data)

    output = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        sys.stdout.write(output + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
