#!/usr/bin/env python3
"""Pack entries into a check.bin-like file."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ENTRY_SIZE = 260
DEFAULT_HEADER = (2008, 1, 7)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pack entries into a check.bin-like file.")
    parser.add_argument("input", type=Path, help="Path to entries (text or JSON)")
    parser.add_argument("output", type=Path, help="Output .bin path")
    parser.add_argument(
        "--header",
        nargs=3,
        type=int,
        default=DEFAULT_HEADER,
        metavar=("MAGIC", "VERSION", "FLAGS"),
        help=(
            "Header values (default: 2008 1 7). Count is derived from entries."
        ),
    )
    return parser.parse_args()


def load_entries(path: Path) -> tuple[list[str], list[int] | None]:
    raw = path.read_text(encoding="utf-8")
    stripped = raw.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        payload = json.loads(raw)
        metadata: list[int] | None = None
        if isinstance(payload, dict):
            metadata = payload.get("metadata")
            for key in ("entries", "paths"):
                if key in payload:
                    payload = payload[key]
                    break
        if not isinstance(payload, list):
            raise ValueError("JSON input must be a list or object with entries")
        entries = [str(item) for item in payload]
        if metadata is not None:
            if not isinstance(metadata, list):
                raise ValueError("Metadata must be a list of integers")
            metadata = [int(value) for value in metadata]
    else:
        entries = [line.strip() for line in raw.splitlines() if line.strip()]
        metadata = None

    if not entries:
        raise ValueError("No entries found to pack")
    return entries, metadata


def pack_entries(
    entries: list[str],
    header: tuple[int, int, int],
    metadata: list[int] | None,
) -> bytes:
    header_bytes = b"".join(value.to_bytes(4, "little") for value in header)
    header_bytes += len(entries).to_bytes(4, "little")

    body = bytearray()
    for entry in entries:
        encoded = entry.encode("utf-8")
        if len(encoded) > ENTRY_SIZE:
            raise ValueError(
                f"Entry too long ({len(encoded)} bytes): {entry}")
        body.extend(encoded.ljust(ENTRY_SIZE, b"\x00"))

    if metadata is None:
        metadata = [0] * len(entries)
    if len(metadata) != len(entries):
        raise ValueError(
            f"Metadata count ({len(metadata)}) does not match entries ({len(entries)})"
        )
    trailer = b"".join(value.to_bytes(4, "little") for value in metadata)

    return header_bytes + body + trailer


def main() -> int:
    args = parse_args()
    entries, metadata = load_entries(args.input)
    payload = pack_entries(entries, tuple(args.header), metadata)
    args.output.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
