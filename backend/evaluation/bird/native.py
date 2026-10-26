"""Complete native tuple results; JSON encodings below measure bytes/preview only."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
import hashlib
import json

from .budgets import BirdFailure

PAYLOAD_POLICY='bird_native_tagged_utf8_payload_v1'


def tagged(value):
    if value is None: return ['null']
    if type(value) is bool: return ['bool',value]
    if type(value) is int: return ['int',str(value)]
    if type(value) is float: return ['float',value.hex()]
    if isinstance(value,Decimal): return ['decimal',str(value)]
    if isinstance(value,str): return ['text',value]
    if isinstance(value,bytes): return ['bytes',value.hex()]
    if isinstance(value,(datetime,date,time)): return [type(value).__name__,value.isoformat()]
    if isinstance(value,tuple): return ['tuple',[tagged(x) for x in value]]
    raise BirdFailure('unsupported_native_result_type')


def encoded(value) -> bytes:
    return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')


@dataclass
class NativeResult:
    columns: list[str]
    rows: list[tuple]
    payload_bytes: int
    complete: bool = True

    def diagnostic(self):
        digest = hashlib.sha256()
        types = set()
        for row in self.rows:
            digest.update(encoded([tagged(v) for v in row])+b'\n')
            types.update(type(v).__name__ for v in row)
        return {'complete':self.complete,'row_count':len(self.rows),'column_count':len(self.columns),
                'payload_bytes':self.payload_bytes,'payload_sizing_policy':PAYLOAD_POLICY,'native_types':sorted(types),
                'ordered_native_diagnostic_sha256':digest.hexdigest()}

    def preview(self):
        rows=[];size=0
        for row in self.rows[:200]:
            value=[tagged(v) for v in row];n=len(encoded(value))
            if size+n>65536:break
            size+=n;rows.append(value)
        return {'columns':self.columns,'rows':rows,'preview_only':True,
                'preview_truncated':len(rows)<len(self.rows),'complete_result_row_count':len(self.rows)}


def consume(cursor, budget=None, *, row_limit=100000, byte_limit=67108864) -> NativeResult:
    columns=None;size=0;rows=[]
    while True:
        if budget:budget.remaining()
        batch=cursor.fetchmany(min(2048,row_limit+1-len(rows)))
        if columns is None:
            columns=[c.name for c in cursor.description or []]
            size=len(encoded({'columns':columns}))
            if size>byte_limit:raise BirdFailure('result_payload_limit')
        if not batch:break
        for row in batch:
            if len(rows)>=row_limit:raise BirdFailure('result_row_limit')
            row=tuple(row)
            if len(row)!=len(columns):raise BirdFailure('result_column_count_mismatch')
            try:hash(row)
            except (TypeError,ValueError):raise BirdFailure('unsupported_native_result_type') from None
            size+=len(encoded([tagged(v) for v in row]))+1
            if size>byte_limit:raise BirdFailure('result_payload_limit')
            rows.append(row)
    return NativeResult(columns,rows,size)
