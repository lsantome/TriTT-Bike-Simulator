"""Escritor mínimo de archivos .fit (mensajes 'record') para probar el lector de FIT."""
from __future__ import annotations

import struct

FIT_EPOCH_OFFSET = 631065600  # s entre 1970-01-01 y 1989-12-31 (época FIT)
_CRC = [0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
        0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400]


def crc16(data: bytes, crc: int = 0) -> int:
    for b in data:
        tmp = _CRC[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC[b & 0xF]
        tmp = _CRC[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC[(b >> 4) & 0xF]
    return crc


def build_fit(records, with_gps: bool = True) -> bytes:
    """records: iterable de dicts con t (epoch unix, s), lat, lon (grados), alt (m),
    speed (m/s), power (W), dist (m)."""
    fields = [(253, 4, 0x86), (0, 4, 0x85), (1, 4, 0x85), (2, 2, 0x84),
              (5, 4, 0x86), (6, 2, 0x84), (7, 2, 0x84)]
    if not with_gps:
        fields = [f for f in fields if f[0] not in (0, 1)]
    body = bytearray()
    body += struct.pack("<BBBHB", 0x40, 0, 0, 20, len(fields))
    for num, size, base in fields:
        body += struct.pack("<BBB", num, size, base)
    k = 2 ** 31 / 180.0
    for r in records:
        vals = [int(round(r["t"])) - FIT_EPOCH_OFFSET]
        fmt = "<BI"
        if with_gps:
            vals += [int(round(r["lat"] * k)), int(round(r["lon"] * k))]
            fmt += "ii"
        vals += [int(round((r["alt"] + 500.0) * 5.0)), int(round(r["dist"] * 100.0)),
                 int(round(r["speed"] * 1000.0)), int(round(r["power"]))]
        fmt += "HIHH"
        body += struct.pack(fmt, 0x00, *vals)
    header = struct.pack("<BBHI4s", 14, 0x20, 2132, len(body), b".FIT")
    header += struct.pack("<H", crc16(header))
    out = header + bytes(body)
    return out + struct.pack("<H", crc16(out))
