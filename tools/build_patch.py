"""Generate the release BPS from two local ROMs. Neither ROM is distributed."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bps import apply_bps, encode_number
from casino_patcher import ROM_SIZE, SOURCE_SHA256, TARGET_SHA256


def create_patch(source: bytes, target: bytes) -> bytes:
    if len(source) != len(target):
        raise ValueError("Este generador requiere dos archivos del mismo tamaño")
    patch = bytearray(b"BPS1" + encode_number(len(source)) + encode_number(len(target)) + encode_number(0))
    offset = 0
    # Compare chunks first: scanning every byte of an unchanged 128 MiB ROM is wasteful.
    block_size = 65536
    pending_start = 0
    pending_kind = 0

    def emit(start: int, end: int, kind: int) -> None:
        if end > start:
            patch.extend(encode_number(((end - start - 1) << 2) | kind))
            if kind == 1:
                patch.extend(target[start:end])

    while offset < len(target):
        end = min(offset + block_size, len(target))
        if source[offset:end] == target[offset:end]:
            if pending_kind == 1:
                emit(pending_start, offset, 1)
                pending_start, pending_kind = offset, 0
            offset = end
            continue
        while offset < end:
            kind = int(source[offset] != target[offset])
            if kind != pending_kind:
                emit(pending_start, offset, pending_kind)
                pending_start, pending_kind = offset, kind
            offset += 1
    emit(pending_start, len(target), pending_kind)
    patch.extend(struct.pack("<II", zlib.crc32(source), zlib.crc32(target)))
    patch.extend(struct.pack("<I", zlib.crc32(patch)))
    return bytes(patch)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("restored", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source, target = args.original.read_bytes(), args.restored.read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        parser.error("La ROM original no coincide con la versión compatible")
    if hashlib.sha256(target).hexdigest() != TARGET_SHA256:
        parser.error("La ROM restaurada no coincide con la versión probada")
    patch = create_patch(source, target)
    if apply_bps(source, patch, max_size=ROM_SIZE) != target:
        raise RuntimeError("La verificación del parche ha fallado")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.write(patch)
    print(f"Parche generado y verificado: {len(patch)} bytes")
    print(f"SHA-256 BPS: {hashlib.sha256(patch).hexdigest()}")


if __name__ == "__main__":
    main()
