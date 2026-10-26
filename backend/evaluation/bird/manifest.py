"""Source-scoped run/cache bindings, including executable prompts and dependencies."""
from importlib.metadata import version
import json
from pathlib import Path
import platform

from scripts.m2_b_common import BASE,PROTOCOL_SHA256,digest_file,digest_json,require
from .evidence import ACCEPTED_VALIDATION_SHA,DATA_VERSION,CATALOG_VERSION


def seccomp_version():
    if platform.system()!='Linux':return None
    import ctypes
    try:
        library=ctypes.CDLL('libseccomp.so.2')
        class Version(ctypes.Structure):_fields_=[('major',ctypes.c_uint),('minor',ctypes.c_uint),('micro',ctypes.c_uint)]
        library.seccomp_version.restype=ctypes.POINTER(Version);v=library.seccomp_version().contents
        return f'{v.major}.{v.minor}.{v.micro}'
    except OSError:return None


def code_binding():
    paths=list((BASE/'evaluation/bird').glob('*.py'))
    paths += [BASE/'evaluation/bird_protocol.py',BASE/'evaluation/run_bird_benchmark.py',BASE/'scripts/check_m2_c_bird_runtime.py']
    paths += [BASE/'scripts'/name for name in ('m2_b_common.py','m2_b_dump.py','m2_b_structure.py','m2_b_target.py','m2_b_typed_rows.py')]
    # Imported application library code is also frozen; no application source is replaced.
    paths += list((BASE/'app').rglob('*.py'))
    payload={'files':{str(p.relative_to(BASE)).replace('\\','/'):digest_file(p) for p in sorted(paths)},
        'dependencies':{n:version(n) for n in ('psycopg','psycopg-pool','sqlglot')},
        'python':platform.python_version(),'system':platform.system(),'kernel':platform.release(),'machine':platform.machine(),
        'seccomp_library_version':seccomp_version()}
    return {'sha256':digest_json(payload),**payload}


def source_binding(evidence):
    return {'protocol_sha256':PROTOCOL_SHA256,'accepted_validation_sha256':ACCEPTED_VALIDATION_SHA,
            'accepted_global_data_version':DATA_VERSION,'accepted_global_catalog_version':CATALOG_VERSION,
            'physical_database':evidence.manifest['target']['database'],'physical_schema':'public',
            'query_roles':evidence.manifest['target']['query_roles'],'budgets':evidence.protocol['budgets'],
            'scoring_policy':evidence.protocol['scoring']['policy_id'],
            'payload_sizing_policy':'bird_native_tagged_utf8_payload_v1'}


def require_runtime_report(path,evidence):
    row=json.loads(path.read_bytes())
    require(row.get('stage')=='M2 C domain runtime, profiles, budgets and isolation' and row.get('run_status')=='complete'
        and row.get('runtime_verified') is True and row.get('target_data_verified') is True and row.get('agent_isolation_verified') is True
        and row.get('budget_enforcement_verified') is True and row.get('pools_closed') is True and not row.get('errors'),
        'Successful M2 C runtime/isolation report is required')
    require(row.get('source_binding')==source_binding(evidence) and row.get('code_binding')==code_binding(),
            'Runtime report belongs to another source/code/dependency version')
    require({d['database_id'] for d in row.get('domains',[])}==set(evidence.manifest['query_domains']) and len(row['domains'])==11,
            'Runtime report does not cover all domains')
    isolation=row.get('isolation',{});probes=isolation.get('probes',{})
    require(isolation.get('passed') is True and probes.get('read_denials')==[True]*4 and all(probes.get(k) is True for k in
        ('network_socket_denied','process_creation_denied','secret_environment_absent')),'Runtime report lacks actual isolation denial probes')
    require(row.get('hard_process_timeout_probe',{}).get('passed') is True
        and row['hard_process_timeout_probe'].get('formal_case_timeout_seconds')==600,'Runtime report lacks hard timeout evidence')
    require(len(row.get('budget_counter_probes',[]))==7 and all(x.get('passed') is True for x in row['budget_counter_probes']),
            'Runtime report has failed budget probes')
    from .evidence import DATA_VERSION
    for domain in row['domains']:
        db=domain['database_id'];role=evidence.domain(db)['query_role'];identity=domain.get('source_identity',{});verification=domain.get('verification',{})
        typed={t['name']:t['target'] for t in evidence.validation['tables'] if t['database_id']==db}
        data_version=digest_json({'accepted_data_version':DATA_VERSION,'database_id':db,'tables':typed,'digest_policy':'m2_copy_native_typed_multiset_v1'})
        require(domain.get('role')==role==verification.get('role') and identity.get('logical_database_id')==db
            and identity.get('source_id')=='bird_mini_dev_postgres_'+db and identity.get('backend')=='postgresql'
            and identity.get('dialect')=='postgres' and identity.get('prompt_dialect')=='PostgreSQL' and identity.get('physical_schema')=='public'
            and identity.get('data_version')==data_version==verification.get('authorized_data_version')
            and identity.get('catalog_version')==verification.get('authorized_catalog_version')
            and verification.get('accepted_validation_sha256')==ACCEPTED_VALIDATION_SHA
            and all(domain.get(k) is True for k in ('native_duplicate_names_preserved','cross_domain_sql_denied','cross_domain_profile_denied')),
            'Runtime domain binding differs: '+db)
    return row


def require_gold_report(path,evidence,runtime_report):
    row=json.loads(path.read_bytes())
    require(row.get('stage')=='M2 C BIRD external benchmark' and row.get('mode')=='gold'
        and row.get('run_status')=='complete' and row.get('gold110_ready') is True and not row.get('errors'),
        'Complete successful original Gold110 readiness report is required before live')
    require(row.get('source_binding')==source_binding(evidence) and row.get('code_binding')==code_binding()
        and row.get('runtime_report_sha256')==digest_file(runtime_report),'Gold readiness has a conflicting source/code/runtime')
    cases=row.get('cases',[])
    from .evidence import scorer_gold
    expected=scorer_gold()
    require(len(cases)==110 and {c['case_id'] for c in cases}==set(expected), 'Gold readiness omitted or duplicated cases')
    domain_ids={d['database_id']:d['source_identity'] for d in require_runtime_report(runtime_report,evidence)['domains']}
    require(all(c.get('status')=='gold_ready' and c.get('mode')=='gold' and c.get('complete') is True and not c.get('errors')
        and c.get('gold_sql_sha256')==expected[c['case_id']]['gold_sql_sha256']
        and c.get('database_id')==expected[c['case_id']]['database_id'] and c.get('source_identity')==domain_ids[c['database_id']]
        and c.get('runtime_closed') is True and c.get('new_model_request_count')==0
        and all(c.get('result',{}).get(k) is True for k in ('complete','within_row_limit','within_payload_limit','native_hashable'))
        for c in cases),'Gold readiness contains failed/incomplete cases or conflicting source identities')
    return row
