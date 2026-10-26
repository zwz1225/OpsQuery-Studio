"""Versioned, exact typed row multiset hashes for COPY text and Psycopg native rows.

This is import integrity evidence, independent from frozen M2 EX scoring.
REAL is normalized to IEEE binary32, TIMESTAMPTZ to the UTC instant.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import math
from pathlib import Path
import re
import struct

from scripts.m2_b_common import require
from scripts.m2_b_dump import MAX_LINE

POLICY = 'm2_copy_native_typed_multiset_v1'
ESCAPES = {ord('b'): 8, ord('f'): 12, ord('n'): 10, ord('r'): 13, ord('t'): 9, ord('v'): 11}


def decode_copy(value: bytes) -> str | None:
    if value == b'\\N': return None
    if b'\\' not in value: return value.decode('utf-8')
    out = bytearray(); i = 0
    while i < len(value):
        ch = value[i]; i += 1
        if ch != 92:
            out.append(ch); continue
        require(i < len(value), 'Truncated COPY escape')
        ch = value[i]; i += 1
        if ch in ESCAPES: out.append(ESCAPES[ch])
        elif 48 <= ch <= 55:
            digits = bytes([ch])
            while i < len(value) and len(digits) < 3 and 48 <= value[i] <= 55:
                digits += bytes([value[i]]); i += 1
            out.append(int(digits, 8) & 255)
        elif ch == ord('x'):
            digits = b''
            while i < len(value) and len(digits) < 2 and value[i] in b'0123456789abcdefABCDEF':
                digits += bytes([value[i]]); i += 1
            if digits: out.append(int(digits, 16))
            else: out.append(ch)
        else: out.append(ch)
    return bytes(out).decode('utf-8')


def source_value(raw: bytes, kind: str):
    value = decode_copy(raw)
    if value is None: return None
    if kind == 'TEXT': return value
    if kind == 'BIGINT': return int(value)
    if kind == 'REAL': return struct.unpack('!f', struct.pack('!f', float(value)))[0]
    if kind == 'DATE': return date.fromisoformat(value)
    if kind == 'TIMESTAMPTZ':
        # PostgreSQL dumps may emit +08 rather than +08:00. Python 3.10's
        # fromisoformat accepts fewer ISO variants than the server's Python 3.11.
        value = re.sub(r'([+-][0-9]{2})$', r'\1:00', value)
        value = re.sub(r'(\.[0-9]{1,5})(?=[+-])', lambda m: m[0]+'0'*(7-len(m[0])), value)
        parsed = datetime.fromisoformat(value)
        require(parsed.tzinfo is not None, 'Source timestamptz must include offset')
        return parsed
    require(False, 'Unsupported source type')


def row_hash(row, columns: list[dict]) -> bytes:
    require(len(row) == len(columns), 'Typed row has wrong number of columns')
    content = bytearray(b'M2T1')
    for value, column in zip(row, columns):
        kind = column['postgres_type']
        if value is None:
            content += b'N'; continue
        if kind == 'TEXT':
            require(isinstance(value, str), 'Target text type differs'); encoded = value.encode('utf-8'); tag = b'T'
        elif kind == 'BIGINT':
            require(type(value) is int and -(2**63) <= value < 2**63, 'Target bigint type/range differs')
            encoded = struct.pack('!q', value); tag = b'I'
        elif kind == 'REAL':
            require(type(value) is float, 'Target REAL type differs')
            # NaN bit payload is not portable through text COPY; canonical SQL NaN is one value.
            encoded = bytes.fromhex('7fc00000') if math.isnan(value) else struct.pack('!f', value)
            tag = b'F'
        elif kind == 'DATE':
            require(type(value) is date, 'Target DATE type differs'); encoded = value.isoformat().encode(); tag = b'D'
        elif kind == 'TIMESTAMPTZ':
            require(isinstance(value, datetime) and value.tzinfo is not None, 'Target timestamptz type differs')
            encoded = value.astimezone(timezone.utc).isoformat(timespec='microseconds').encode(); tag = b'Z'
        else:
            require(False, 'Unsupported typed row column')
        content += tag + struct.pack('!I', len(encoded)) + encoded
    return hashlib.sha256(content).digest()


class Rows:
    """Retains 32 digest bytes per row plus list overhead, never original rows."""
    def __init__(self, columns: list[dict]):
        self.columns = columns; self.hashes = []; self.null_counts = [0]*len(columns)

    def add(self, row) -> None:
        self.hashes.append(row_hash(row, self.columns))
        for i, value in enumerate(row): self.null_counts[i] += int(value is None)

    def finish(self) -> dict:
        self.hashes.sort()
        digest = hashlib.sha256(POLICY.encode()+b'\0')
        for h in self.hashes: digest.update(h)
        return {'row_count': len(self.hashes), 'null_counts': self.null_counts,
                'typed_row_multiset_sha256': digest.hexdigest(), 'typed_digest_policy': POLICY}


def source_rows(path: Path, table: dict) -> dict:
    rows = Rows(table['columns']); payload = hashlib.sha256()
    with path.open('rb') as stream:
        stream.seek(table['copy_bytes_start']); end = table['copy_bytes_end']
        while stream.tell() < end:
            line = stream.readline(min(MAX_LINE+1, end-stream.tell()))
            require(line and line.endswith(b'\n') and len(line) <= MAX_LINE, 'Invalid source COPY row boundary')
            payload.update(line)
            # Remove the line ending only; a trailing data CR is represented by COPY escape.
            line = line[:-1]
            if line.endswith(b'\r'): line = line[:-1]
            values = line.split(b'\t')
            require(len(values) == len(table['columns']), 'Source COPY field count differs')
            rows.add(tuple(source_value(v, c['postgres_type']) for v, c in zip(values, table['columns'])))
        require(stream.tell() == end and stream.readline() in (b'\\.\n', b'\\.\r\n'), 'Source COPY terminator differs')
    result = rows.finish()
    require(payload.hexdigest() == table['copy_payload_sha256'], 'Source COPY payload changed')
    require(result['row_count'] == table['row_count'] and result['null_counts'] == table['null_counts'], 'Source COPY statistics differ')
    return result
