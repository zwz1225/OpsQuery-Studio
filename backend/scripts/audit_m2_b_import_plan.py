"""Audit approved import definitions and every typed source row without PostgreSQL."""
from __future__ import annotations

import argparse

from scripts.m2_b_structure import expectations
from scripts.m2_b_target import arguments, journal, load_inputs, protected_paths
from scripts.m2_b_typed_rows import POLICY, source_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); arguments(parser); args = parser.parse_args()
    with journal(args.output, 'M2 B offline full typed source audit', protected=protected_paths(args)) as report:
        manifest, dump, evidence = load_inputs(args.preparation_dir, args.data_root)
        expected = expectations(manifest)
        report.update(target=manifest['target'], source_evidence_sha256=evidence, typed_digest_policy=POLICY, tables=[])
        for i, table in enumerate(manifest['dump']['tables'], 1):
            report['tables'].append({'name': table['name'], 'database_id': table['database_id'], **source_rows(dump, table)})
            print(f"source typed [{i}/75] {table['name']}: rows={table['row_count']}", flush=True)
        report.update(run_status='complete', summary={'source_table_count': len(report['tables']),
            'source_row_count': sum(t['row_count'] for t in report['tables']),
            'source_column_count': manifest['dump']['column_count'], 'expected_constraint_count': len(expected['constraints']),
            'expected_index_count': len(expected['indexes']), 'expected_sequence_count': len(expected['values'])},
            verification_scope='Real source bytes and typed parsing only; no target, role, import or Gold verification')
    raise SystemExit(0 if report['run_status'] == 'complete' else 1)


if __name__ == '__main__': main()
