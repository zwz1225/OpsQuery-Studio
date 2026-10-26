"""Trusted source binding. Agent workers never import this module or read these files."""
from __future__ import annotations

import csv
from dataclasses import dataclass
import io
import json
from pathlib import Path

from scripts.m2_b_common import (BASE, PROTOCOL_DIR, PROTOCOL_SHA256, APPROVED_IMPORT_SPEC,
    digest_file, digest_json, load_protocol, require, require_import_spec)

ACCEPTED_VALIDATION_SHA = '221678d07dd0509048ae2563a3a006e3dc033ea474265ac90ceb9723bfa103c6'
DATA_VERSION = 'a8fbe7c8a393d3e61f2880ed75f177b17f8914265bc6a6e16744f632951c6641'
CATALOG_VERSION = 'f81bd94d4a761e3720855b8eba4b4a1b6dda0d2a3629ffb8002e987285e66636'
DEFAULT_RESULTS = BASE/'evaluation/results'
DEFAULT_DATA = BASE/'data/external/bird_mini_dev'


@dataclass(frozen=True)
class Evidence:
    manifest: dict
    validation: dict
    protocol: dict
    data_root: Path

    @classmethod
    def load(cls, data_root: Path = DEFAULT_DATA, results: Path = DEFAULT_RESULTS):
        protocol, target = load_protocol()
        manifest_path = BASE/'evaluation/cases/bird_mini_dev/m2_b_import_spec_v1.json'
        manifest = json.loads(manifest_path.read_bytes()); require_import_spec(manifest)
        vp = results/'m2_b_postgres_validation_server.json'
        require(digest_file(vp) == ACCEPTED_VALIDATION_SHA, 'M2 validation evidence differs from accepted report')
        validation = json.loads(vp.read_bytes())
        require(validation.get('run_status') == 'complete' and validation.get('target_data_verified') is True
            and not validation.get('errors') and validation.get('target') == target == manifest['target'], 'M2 target is not verified')
        require(validation.get('protocol_sha256') == PROTOCOL_SHA256 and validation.get('import_spec_sha256') == APPROVED_IMPORT_SPEC,
                'M2 protocol/source identity differs')
        require(validation.get('verified_data_version') == DATA_VERSION and validation.get('verified_catalog_version') == CATALOG_VERSION,
                'M2 accepted versions differ')
        require(digest_json(validation['structure']['verified_structure']) == CATALOG_VERSION, 'M2 catalog evidence digest differs')
        for kind, name in [('initialization', 'm2_b_postgres_initialization_server.json'), ('import', 'm2_b_postgres_import_server.json')]:
            path = results/name; row = json.loads(path.read_bytes())
            require(digest_file(path) == validation[kind+'_report_sha256'] and row.get('run_status') == 'complete'
                and row.get('initialization_id') == validation['initialization_id'] and row.get('target') == target
                and not row.get('errors'), 'M2 prerequisite evidence differs: '+kind)
        return cls(manifest, validation, protocol, data_root.resolve())

    def domain(self, database_id: str) -> dict:
        require(database_id in self.manifest['query_domains'], 'Unknown external database_id; fallback is forbidden')
        return self.manifest['query_domains'][database_id]

    def tables(self, database_id: str) -> list[dict]:
        allowed = set(self.domain(database_id)['tables'])
        return [t for t in self.manifest['dump']['tables'] if t['name'] in allowed]

    def descriptions(self, database_id: str) -> tuple[dict, dict]:
        tables = self.tables(database_id); names = {t['name']:t for t in tables}
        found = {}; diagnostic = {'database_id': database_id, 'files': [], 'unmatched_columns': []}
        for item in self.manifest['sources']:
            if item['kind'] != 'column_description': continue
            relative = Path(item['relative_to_data_root'])
            if relative.parts[-3] != database_id: continue
            name = relative.stem.lower(); require(name in names, 'Description table escapes authorized domain')
            path = (self.data_root/relative).resolve()
            require(path.is_relative_to(self.data_root) and digest_file(path) == item['sha256'], 'Official description changed')
            raw = path.read_bytes()
            try: text = raw.decode('utf-8-sig'); encoding = 'utf-8-sig'
            except UnicodeDecodeError: text = raw.decode('cp1252'); encoding = 'cp1252'
            mapping = {}; columns = {c['name'] for c in names[name]['columns']}
            for row in csv.DictReader(io.StringIO(text)):
                original = row.get('original_column_name') or ''
                candidates = [c for c in columns if c == original]
                if not candidates: candidates = [c for c in columns if c.strip().lower() == original.strip().lower()]
                require(len(candidates) <= 1, 'Ambiguous official column description')
                if not candidates:
                    diagnostic['unmatched_columns'].append({'table': name, 'original_column': original}); continue
                column = candidates[0]; require(column not in mapping, 'Repeated official column description')
                mapping[column] = {k: str(row.get(k) or '').strip() for k in
                    ('column_name', 'column_description', 'value_description')}
            found[name] = mapping
            diagnostic['files'].append({'table': name, 'sha256': item['sha256'], 'encoding': encoding,
                                        'mapped_column_count': len(mapping)})
        require(set(found) == set(names), 'Missing authorized table description file')
        return found, diagnostic


def public_cases(split: str) -> list[dict]:
    from evaluation.bird_protocol import validate_agent_input
    require(split in {'smoke8','development80','holdout30'}, 'Unknown frozen split')
    load_protocol()
    rows = [json.loads(line) for line in (PROTOCOL_DIR/'inputs'/f'{split}.jsonl').read_text(encoding='utf-8').splitlines()]
    for row in rows: validate_agent_input(row)
    require(len(rows) == {'smoke8':8,'development80':80,'holdout30':30}[split], 'Frozen split count differs')
    return rows


def scorer_gold() -> dict[str, dict]:
    """Scorer-only API. Neither retrieval nor isolated Agent imports it."""
    load_protocol()
    rows = [json.loads(line) for line in (PROTOCOL_DIR/'scorer/gold110.jsonl').read_text(encoding='utf-8').splitlines()]
    require(len(rows) == 110 and len({r['case_id'] for r in rows}) == 110, 'Gold110 identity differs')
    for row in rows:
        require(digest_bytes(row['gold_sql'].encode()) == row['gold_sql_sha256'], 'Selected Gold SQL differs')
    return {r['case_id']:r for r in rows}


def digest_bytes(value: bytes) -> str:
    import hashlib
    return hashlib.sha256(value).hexdigest()
