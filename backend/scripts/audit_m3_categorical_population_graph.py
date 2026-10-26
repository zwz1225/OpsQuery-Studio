"""Replay the opt-in categorical condition graph from frozen M3 evidence only.

This is a no-model, no-database review of recorded public input, authorized
catalog evidence, and the source-reviewed customer/yearmonth relation.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
from types import SimpleNamespace as NS

from evaluation.bird.demand_relations import annotate_graph, expand_context
from evaluation.bird.evidence import ACCEPTED_VALIDATION_SHA
from evaluation.bird.intent import checked_tables
from evaluation.bird.relationships import build_graph
from scripts.m2_b_common import BASE, digest_file, digest_json, require, write_new_json
from evaluation.bird.reviewed_relations import REVIEWED_RELATIONS

WORKSPACE = BASE.parents[1]
PAIR_ROOT = WORKSPACE / 'm3_e06_pair80_endpoint_feedback_v2_20261024_r1'
DEFAULT_CAPTURE = PAIR_ROOT / 'candidate/backend/evaluation/results/m3_e06_pair80_candidate_capture_server.json'
DEFAULT_VALIDATION = BASE / 'evaluation/results/m2_b_postgres_validation_server.json'
DEFAULT_IMPORT_SPEC = BASE / 'evaluation/cases/bird_mini_dev/m2_b_import_spec_v1.json'
DEFAULT_PUBLIC_INPUTS = BASE / 'evaluation/cases/bird_mini_dev/m2_pg_v1/inputs/development80.jsonl'
DEFAULT_DEV_SCHEMA = WORKSPACE / 'datasets/bird_mini_dev/extracted/minidev/MINIDEV/dev_tables.json'
DEFAULT_OUTPUT = BASE / 'evaluation/results/m3_categorical_population_graph_local_20261025.json'
EXPECTED_CAPTURE_SHA256 = '2e204fbc10bd9d37bef79caef8bf93a3c45e84b4c9f4def65f37d1960bf0b74c'
EXPECTED_VALIDATION_SHA256 = '221678d07dd0509048ae2563a3a006e3dc033ea474265ac90ceb9723bfa103c6'
EXPECTED_DEV_SCHEMA_SHA256 = '48aa9febe7282d1690f3ed1f222dc040c182df83812ba4e9bee956084d99c8ff'


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def public_inputs(path: Path):
    return {row['case_id']: row for row in
            (json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip())}


def domain_runtime_and_documents(capture, validation, import_spec, dev_schema, receipt):
    db='debit_card_specializing'
    domain=import_spec['query_domains'][db]
    verified=validation['structure']['verified_structure']
    schema=next(x for x in dev_schema if x['db_id']==db)
    original_to_label={}
    for (table_index,original),(label_table_index,label) in zip(
            schema['column_names_original'],schema['column_names']):
        if table_index>=0 and table_index==label_table_index:
            original_to_label[(schema['table_names_original'][table_index].casefold(),original.casefold())]=label
    tables=[];documents=[]
    for table_name in domain['tables']:
        rows=verified['columns'].get(table_name)
        require(isinstance(rows,list) and rows,'Authorized table catalog missing from recorded validation')
        fields=[]
        for name,kind,not_null,*_ in rows:
            label=original_to_label.get((table_name.casefold(),name.casefold()),name)
            role='primary_key' if table_name=='customers' and name=='customerid' else 'field'
            fields.append(dict(name=name,label=label,type=kind,role=role,
                               description=label if label!=name else name))
            documents.append(NS(doc_id=f'{db}.{table_name}.{name}',database_id=db,
                table_id=f'{db}.{table_name}',field_name=name,field_label=label,
                field_type=kind,field_role=role,field_description=label,profile='',samples=[]))
        tables.append(dict(id=f'{db}.{table_name}',name=table_name,label=table_name,
            description='Authorized PostgreSQL table from the recorded M2 validation catalog',
            database=db,physical_schema='public',fields=fields))
    # Replay only profile hints already recorded in the two E06 cases. This is
    # not a new full-index/sample scan; it exercises how recorded hints flow
    # through the source-bound selector and graph builder.
    record1480=next(x for x in capture['cases'] if x['case_id']=='BIRD-PG-1480')
    recorded_hints=[]
    for cid in ('BIRD-PG-1479','BIRD-PG-1480'):
        row=next(x for x in capture['cases'] if x['case_id']==cid)
        context=row.get('development_diagnostics',{}).get('retrieval',{}).get('condition_relation_context',{})
        recorded_hints.extend(context.get('sample_hint_decisions',[]))
        intent=row.get('retrieval',{}).get('intent_selection',{})
        recorded_hints.extend(intent.get('sample_condition_decisions',[]))
    hint_values={}
    for hint in recorded_hints:
        fid=hint.get('field_id');value=hint.get('value')
        if fid in ('debit_card_specializing.customers.segment','debit_card_specializing.customers.currency'):
            hint_values.setdefault(fid,set()).add(value)
    require(hint_values.get('debit_card_specializing.customers.segment')=={'SME'} and
            hint_values.get('debit_card_specializing.customers.currency')=={'CZK'},
            'Recorded SME/CZK profile hints are missing or inconsistent')
    for field_id,values in hint_values.items():
        document=next(d for d in documents if d.doc_id==field_id)
        document.samples=[['text',value] for value in sorted(values)]

    constraint_rows=verified.get('constraints',[])
    relations=[]
    for row in constraint_rows:
        if row.get('table') not in domain['tables'] or 'FOREIGN KEY' not in row.get('sql','').upper():
            continue
        match=re.search(r'FOREIGN KEY\s*\("([^"]+)"\)\s*REFERENCES\s*"(?:[^"]+)"\."([^"]+)"\s*\("([^"]+)"\)',row['sql'],re.I)
        if not match:continue
        child_field,parent_table,parent_field=match.groups()
        relations.append(dict(id=row['name'],left_table=f'{db}.{parent_table}',left_field=parent_field,
            right_table=f'{db}.{row["table"]}',right_field=child_field))
    require(not any({r['left_table'],r['right_table']}==
        {f'{db}.customers',f'{db}.yearmonth'} for r in relations),
        'PostgreSQL appears to declare the reviewed customers/yearmonth relation unexpectedly')

    identity=record1480['source_identity']
    # The E06 capture carries the per-domain source identity on each case.
    runtime=NS(database_id=db,identity=NS(public=lambda:identity),domain={'query_role':domain['query_role']},
        catalog=NS(version=identity['catalog_version'],tables=tables,relations=relations),
        verification=dict(live_target_verified=receipt['live_target_verified'],role=receipt['role'],
            accepted_validation_sha256=receipt['accepted_validation_sha256'],
            authorized_data_version=receipt['authorized_data_version'],
            authorized_catalog_version=receipt['authorized_catalog_version']))
    require(receipt['live_target_verified'] is True and receipt['role']==domain['query_role'],
            'Recorded E06 live source receipt is not verified for the read role')
    require(identity['data_version']==receipt['authorized_data_version'] and
            identity['catalog_version']==receipt['authorized_catalog_version'] and
            receipt['accepted_validation_sha256']==ACCEPTED_VALIDATION_SHA,
            'Recorded relation/source identity binding differs')
    checked_tables(runtime)
    return runtime,documents,domain


def make_graph(runtime,documents,selected,public,trace):
    hits=[]
    for index,score in selected:
        doc=documents[index]
        hits.append(dict(doc_id=doc.doc_id,database_id=doc.database_id,table_id=doc.table_id,
            field_name=doc.field_name,field_label=doc.field_label,field_type=doc.field_type,
            field_description=doc.field_description,field_role=doc.field_role,
            source='condition_relation_coverage' if doc.doc_id in trace['added_field_ids'] else 'recorded_selection',
            score=score))
    graph=build_graph(runtime,hits,public)
    return annotate_graph(runtime,graph,trace)


def audit(capture_path,validation_path,import_path,public_path,dev_schema_path):
    capture=json.loads(capture_path.read_bytes())
    validation=read_json(validation_path);spec=read_json(import_path);dev_schema=read_json(dev_schema_path)
    require(digest_file(capture_path)==EXPECTED_CAPTURE_SHA256,'E06 candidate capture differs from reviewed bytes')
    require(digest_file(validation_path)==EXPECTED_VALIDATION_SHA256,'M2 validation evidence differs from accepted bytes')
    require(digest_file(dev_schema_path)==EXPECTED_DEV_SCHEMA_SHA256,'Development schema evidence differs from accepted bytes')
    require(capture.get('run_status')=='complete' and validation.get('run_status')=='complete'
            and validation.get('target_data_verified') is True,'Recorded source evidence is incomplete')
    inputs=public_inputs(public_path)
    cases={x['case_id']:x for x in capture['cases']}
    receipts={x['database_id']:x for x in capture['source_receipts']}
    runtime,documents,domain=domain_runtime_and_documents(capture,validation,spec,dev_schema,
        receipts['debit_card_specializing'])
    by_id={doc.doc_id:i for i,doc in enumerate(documents)}
    case_results=[]
    for cid in ('BIRD-PG-1480','BIRD-PG-1479'):
        captured=cases[cid];public=inputs[cid]
        require(public['database_id']==runtime.database_id,'Public input source differs')
        recorded_ids=captured['retrieval']['selected_field_ids']
        require(set(recorded_ids)<=set(by_id),'Recorded selected fields are outside authorized catalog')
        selected=[(by_id[fid],next((c['rerank_score'] for c in captured['development_diagnostics']['retrieval']['candidates']
            if c['field_id']==fid and c.get('rerank_score') is not None),0.0)) for fid in recorded_ids]
        intent_count=len(captured['retrieval']['intent_selection']['added_field_ids'])
        plain,plain_trace=expand_context(runtime,documents,selected,public,intent_added_count=intent_count)
        proposed,trace=expand_context(runtime,documents,selected,public,intent_added_count=intent_count,
                                      categorical_population=True)
        before_graph=make_graph(runtime,documents,plain,public,plain_trace)
        candidate_graph=make_graph(runtime,documents,proposed,public,trace)
        graph_ids={field['id'] for field in candidate_graph['fields']}
        require(graph_ids<=set(by_id),'Candidate graph exposed an identifier outside authorized catalog')
        added={documents[i].doc_id for i,_ in proposed}-{documents[i].doc_id for i,_ in selected}
        if cid=='BIRD-PG-1480':
            require(added=={'debit_card_specializing.customers.segment','debit_card_specializing.customers.customerid'},
                    '1480 field closure differs from the reviewed target')
            require(len(candidate_graph['joins'])==1 and
                    candidate_graph['joins'][0]['relation_type']=='reviewed_candidate' and
                    candidate_graph['joins'][0]['declared_foreign_key'] is False and
                    candidate_graph['joins'][0]['join_type'] is None,
                    '1480 relation was not represented as an unprescribed reviewed candidate')
            condition=candidate_graph['condition_relation_context']['admitted_public_conditions']
            require(len(condition)==1 and condition[0]['field_id']=='debit_card_specializing.customers.segment'
                    and condition[0]['value']=='SME' and condition[0]['mandatory'] is False,
                    '1480 public condition hint was not retained as advisory')
        else:
            require(added==set(),'Existing 1479 context changed under the categorical population candidate')
            require(candidate_graph['joins']==before_graph['joins'] and len(candidate_graph['joins'])==1
                    and candidate_graph['joins'][0]['relation_type']=='reviewed_candidate',
                    'Existing 1479 reviewed relation did not remain stable')
        case_results.append(dict(case_id=cid,recorded_selected_field_ids=recorded_ids,
            baseline_added_field_ids=sorted({documents[i].doc_id for i,_ in plain}-{documents[i].doc_id for i,_ in selected}),
            categorical_candidate_added_field_ids=sorted(added),
            baseline_graph=dict(tables=before_graph['tables'],fields=before_graph['fields'],joins=before_graph['joins']),
            candidate_graph=dict(tables=candidate_graph['tables'],fields=candidate_graph['fields'],
                                joins=candidate_graph['joins'],condition_relation_context=candidate_graph['condition_relation_context']),
            unresolved_required_roles=trace['unresolved_required_roles']))
    return dict(stage='M3 public categorical population condition authorized graph replay',run_status='complete',
        formal_benchmark=False,holdout_run=False,new_model_request_count=0,postgresql_connected=False,
        current_live_target_verified=False,source_scope='Recorded E06 live receipt plus accepted M2 source/catalog evidence; no new live verification',
        source_evidence_sha256=dict(capture=digest_file(capture_path),validation=digest_file(validation_path),
            import_spec=digest_file(import_path),public_inputs=digest_file(public_path),dev_schema=digest_file(dev_schema_path)),
        policy_id='bird_public_categorical_population_context_v1',query_role=domain['query_role'],
        source_identity=runtime.identity.public(),relation_candidate=dict(id='debit_card_specializing:customers:yearmonth',
            parent_table='debit_card_specializing.customers',parent_key='customerid',
            child_table='debit_card_specializing.yearmonth',child_key='customerid',
            declared_foreign_key=False,authority='reviewed_source_bound_candidate',
            source_review_sha256=next(r['review_sha256'] for r in REVIEWED_RELATIONS
                if r['source_identity']['logical_database_id']=='debit_card_specializing'),
            observed_orphan_rows=0,observed_null_child_rows=0,join_type=None),
        case_count=len(case_results),cases=case_results,
        checks=dict(recorded_source_binding=True,authorized_catalog_field_ownership=True,
            recorded_profile_hints_replayed=True,full_profile_unique_owner_not_rescanned=True,
            atomic_key_closure=True,existing_1479_preserved=True,
            relation_is_not_declared_fk=True,join_semantics_unprescribed=True,condition_not_mandatory=True,
            model_called=False,database_connected=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,default=DEFAULT_CAPTURE)
    parser.add_argument('--validation-report',type=Path,default=DEFAULT_VALIDATION)
    parser.add_argument('--import-spec',type=Path,default=DEFAULT_IMPORT_SPEC)
    parser.add_argument('--public-inputs',type=Path,default=DEFAULT_PUBLIC_INPUTS)
    parser.add_argument('--dev-schema',type=Path,default=DEFAULT_DEV_SCHEMA)
    parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    args=parser.parse_args()
    report=audit(args.capture,args.validation_report,args.import_spec,args.public_inputs,args.dev_schema)
    write_new_json(args.output,report)
    report['output']=str(args.output.resolve())
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
