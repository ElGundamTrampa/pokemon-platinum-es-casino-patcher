"""Small BPS1 reader. Format: byuu's public-domain BPS specification."""
from __future__ import annotations

import struct
import zlib


class PatchError(ValueError):
    """A patch or its input failed validation."""


def encode_number(value: int) -> bytes:
    if value < 0:
        raise ValueError("El entero BPS no puede ser negativo")
    result = bytearray()
    while True:
        digit = value & 0x7F
        value >>= 7
        if value == 0:
            result.append(digit | 0x80)
            return bytes(result)
        result.append(digit)
        value -= 1


def apply_bps(source: bytes, patch: bytes, *, max_size: int) -> bytes:
    if len(patch) < 19 or patch[:4] != b"BPS1":
        raise PatchError("El parche BPS no es válido")
    source_crc, target_crc, patch_crc = struct.unpack_from("<III", patch, len(patch) - 12)
    if zlib.crc32(patch[:-4]) != patch_crc:
        raise PatchError("El parche está dañado (CRC32)")
    if zlib.crc32(source) != source_crc:
        raise PatchError("La ROM no coincide con el origen del parche")
    cursor = 4
    limit = len(patch) - 12

    def number() -> int:
        nonlocal cursor
        result, shift = 0, 1
        for _ in range(10):
            if cursor >= limit:
                raise PatchError("El parche está truncado")
            digit = patch[cursor]
            cursor += 1
            result += (digit & 0x7F) * shift
            if digit & 0x80:
                return result
            shift <<= 7
            result += shift
        raise PatchError("Entero BPS demasiado grande")

    source_size, target_size, metadata_size = number(), number(), number()
    if source_size != len(source) or not 0 < target_size <= max_size:
        raise PatchError("El tamaño de la ROM no corresponde al parche")
    if cursor + metadata_size > limit:
        raise PatchError("Metadatos BPS truncados")
    cursor += metadata_size
    output = bytearray()
    source_offset = target_offset = 0
    while cursor < limit:
        action = number()
        kind, length = action & 3, (action >> 2) + 1
        if len(output) + length > target_size:
            raise PatchError("El parche excede el tamaño de salida")
        if kind == 0:
            start = len(output)
            if start + length > len(source):
                raise PatchError("Lectura fuera de la ROM")
            output.extend(source[start:start + length])
        elif kind == 1:
            if cursor + length > limit:
                raise PatchError("Datos BPS truncados")
            output.extend(patch[cursor:cursor + length])
            cursor += length
        else:
            relative = number()
            delta = -(relative >> 1) if relative & 1 else relative >> 1
            if kind == 2:
                source_offset += delta
                if source_offset < 0 or source_offset + length > len(source):
                    raise PatchError("Copia fuera de la ROM")
                output.extend(source[source_offset:source_offset + length])
                source_offset += length
            else:
                target_offset += delta
                if not 0 <= target_offset < len(output):
                    raise PatchError("Copia de salida BPS inválida")
                # Overlap is permitted: each byte becomes available as it is written.
                for _ in range(length):
                    output.append(output[target_offset])
                    target_offset += 1
    if len(output) != target_size or zlib.crc32(output) != target_crc:
        raise PatchError("La ROM restaurada no supera la comprobación de integridad")
    return bytes(output)
