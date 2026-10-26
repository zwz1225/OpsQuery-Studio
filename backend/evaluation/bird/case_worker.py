"""Trusted scorer/broker process; isolated Agent sees only capability-filtered messages."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time
from collections import Counter

from evaluation.bird_protocol import compare_ex_rows,validate_agent_input
from scripts.m2_b_target import load_credentials
from .budgets import Budget,BirdFailure
from .evidence import Evidence,digest_bytes
from .runtime import BirdRuntime,fault
from .manifest import code_binding
from .supervisor import IsolatedAgent,MAX_FRAME
from .diagnostics import Recorder
from .repair import RepairSession,POLICY as REPAIR_POLICY
from .coverage import contract as coverage_contract


def execute(request):
    diagnostic_mode=request['mode']=='diagnostic'
    budget=Budget();gold=request['input'] if diagnostic_mode else request['gold'];db=gold['database_id'];runtime=None;recorder=None
    report={'case_id':gold['case_id'],'database_id':db,'mode':request['mode'],'status':'failed','complete':False,
            'gold_sql_sha256':None if diagnostic_mode else gold['gold_sql_sha256'],'ex_correct':None,'errors':[],'new_model_request_count':0}
    try:
        if request.get('code_sha256')!=code_binding()['sha256']:raise BirdFailure('case_code_binding_mismatch')
        if request['mode'] not in ('gold','live','diagnostic'):raise BirdFailure('unknown_case_mode')
        coverage=request.get('schema_coverage_enabled',False)
        if type(coverage) is not bool or coverage and not diagnostic_mode:raise BirdFailure('schema_coverage_development_only')
        intent_enabled=request.get('intent_candidate_enabled',False)
        if type(intent_enabled) is not bool or intent_enabled and not diagnostic_mode:raise BirdFailure('intent_candidate_development_only')
        semantic_planning=request.get('semantic_planning_enabled',False)
        if type(semantic_planning) is not bool or semantic_planning and (not diagnostic_mode or not intent_enabled):
            raise BirdFailure('query_semantic_planning_development_only_requires_intent')
        output_enabled=request.get('output_contract_enabled',False)
        if type(output_enabled) is not bool or output_enabled and (not diagnostic_mode or not intent_enabled):
            raise BirdFailure('output_contract_development_only')
        condition_relations=request.get('condition_relations_enabled',False)
        relation_output=request.get('relation_output_enabled',False)
        categorical_population=request.get('categorical_population_enabled',False)
        from .demand_relations import validate_options
        validate_options(condition_relations,diagnostic=diagnostic_mode,coverage=coverage,intent=intent_enabled,
                         output=output_enabled,relation_output=relation_output,
                         categorical_population=categorical_population)
        report['schema_selection_policy']=coverage_contract(coverage)
        if not diagnostic_mode and (gold['dialect']!='postgres' or digest_bytes(gold['gold_sql'].encode())!=gold['gold_sql_sha256']):raise BirdFailure('gold_identity_mismatch')
        evidence=Evidence.load(Path(request['data_root']),Path(request['results_dir']));domain=evidence.domain(db)
        credentials=load_credentials(Path(request['credentials_file']),evidence.manifest,evidence.validation['initialization_id'])
        runtime=BirdRuntime(evidence,db,credentials['passwords'][domain['query_role']],receipt=request['receipt'])
        report['source_identity']=runtime.identity.public();report['query_role']=domain['query_role']
        if request['mode']=='gold':
            result=runtime.execute_native(gold['gold_sql'],budget)
            report.update(status='gold_ready',complete=True,result={'complete':result.complete,
                'within_row_limit':len(result.rows)<=100000,'within_payload_limit':result.payload_bytes<=67108864,
                'native_hashable':True,'answer_details':'scorer-only; no answer rows, counts or digests exposed'})
        else:
            public=request['input'];validate_agent_input(public)
            if public['case_id']!=gold['case_id'] or public['database_id']!=db:raise BirdFailure('public_case_source_mismatch')
            from .model import Models,ModelConfig
            from .retrieval import retrieve
            config=ModelConfig(**request['model_config_private']) if 'model_config_private' in request else ModelConfig.load(Path(request['model_config_file']))
            recorder=Recorder((config.api_key,credentials['passwords'][domain['query_role']]))
            repair=RepairSession(runtime,recorder.secrets,public)
            report['sql_repair_policy']=REPAIR_POLICY
            models=Models(config,budget)
            options={}
            if coverage:options['schema_coverage']=True
            if intent_enabled:options['intent_candidate']=True
            if condition_relations:options['condition_relations']=True
            if relation_output:options['relation_output']=True
            if categorical_population:options['categorical_population']=True
            schema=retrieve(runtime,models,Path(request['index_path']),public,**options)
            if condition_relations:
                from .demand_relations import policy as demand_policy
                report['condition_relation_policy']=demand_policy(relation_output,categorical_population)
            intent_contract=None
            if intent_enabled:
                from .intent import policy,canonical_lookup,build_contract,violations,query_semantics_policy
                report['intent_candidate_policy']=policy()
                if semantic_planning:report['query_semantic_planning_policy']=query_semantics_policy()
                report['agent_started']=False
                selection=schema.pop('_intent_selection')
                report['canonical_lookup']={}
                lookup=canonical_lookup(runtime,public,schema['retrieval']['selected_field_ids'],budget,progress=report['canonical_lookup'])
                intent_contract=build_contract(runtime,public,schema['graph'],selection,lookup,
                                               semantic_planning=semantic_planning)
                intent_contract['remaining_sql_execution_rounds']=3-budget.sql_calls
                schema['intent_contract']=intent_contract
                report['intent_contract']=intent_contract
            output_contract=None
            if output_enabled:
                from .output_contract import build_contract as build_output_contract, observation, policy as output_policy
                output_contract=build_output_contract(public,schema['graph'],intent_contract)
                schema['public_output_contract']=output_contract
                report['public_output_contract_policy']=output_policy()
                report['public_output_contract']=recorder._safe(output_contract)
                report['public_output_contract_complete']=report['public_output_contract']==output_contract
                report['public_output_contract_sha256']=digest_bytes(json.dumps(output_contract,ensure_ascii=False,separators=(',',':')).encode('utf-8'))
                report['output_contract_observations']=[]
            # Keep report-only retrieval/SQL diagnostics out of the Agent context.
            recorder.set_retrieval(schema.pop('_report_diagnostics',None))
            report['retrieval']=schema['retrieval'];report['index_sha256']=schema['index_sha256']
            latest=None;latest_sql=None;executions=[];validation_events=[];validated_sql={}
            def handler(operation,message):
                nonlocal latest,latest_sql
                budget.remaining()
                if operation=='chat':
                    sql_round=message.get('sql_round')
                    # Every generation/repair is one of at most 3 attempts per SQL round,
                    # including malformed model JSON that never reaches SQL validation.
                    budget.generation(sql_round)
                    decision=models.chat(message['system'],message['user'])
                    recorder.model_decision(decision,sql_round)
                    if output_enabled and isinstance(decision,dict) and decision.get('action')=='query' and isinstance(decision.get('sql'),str):
                        observed=observation(output_contract,schema['graph'],decision['sql'])
                        report['output_contract_observations'].append(recorder._safe(dict(
                            sql_round=sql_round, sql_sha256=digest_bytes(decision['sql'].encode('utf-8')),
                            diagnostic=observed)))
                    return decision
                if operation=='validate':
                    sql_round=message.get('sql_round');sql=message.get('sql')
                    budget.validation(sql_round)
                    repeated=repair.repeated(sql) if isinstance(sql,str) else None
                    if repeated is not None:
                        failure,feedback=repeated
                        recorder.operation('validate',sql_round,sql,valid=False,error=failure,repair_feedback=feedback)
                        validation_events.append({'sql_round':sql_round,'valid':False,'error':failure.public(),
                            'repair_feedback':feedback,'runtime_validation_performed':False,'database_validation_performed':False})
                        return {'valid':False,'error':failure.public(),'repair_feedback':feedback,'retryable':False}
                    try:
                        result=runtime.execute_native(sql,budget,validate_only=True)
                        if intent_enabled:
                            issues=violations(runtime,public,intent_contract,sql)
                            if issues:
                                failure=BirdFailure('intent_contract_violation')
                                failure._intent_violations=issues
                                raise failure
                        validated_sql[sql_round]=sql
                        recorder.operation('validate',sql_round,sql,valid=True)
                        validation_events.append({'sql_round':message.get('sql_round'),'valid':True});return result
                    except Exception as error:
                        failure=fault(error)
                        feedback=repair.feedback(failure,sql) if isinstance(sql,str) else None
                        if isinstance(sql,str):repair.remember(failure,sql)
                        recorder.operation('validate',sql_round,sql,valid=False,error=failure,repair_feedback=feedback)
                        validation_events.append({'sql_round':sql_round,'valid':False,'error':failure.public(),
                            'repair_feedback':feedback,'runtime_validation_performed':True,
                            'database_validation_performed':getattr(failure,'_repair_statement_prefix',None) is not None or hasattr(failure,'_intent_violations')})
                        return {'valid':False,'error':failure.public(),'repair_feedback':feedback}
                if operation=='sql':
                    budget.sql_call();sql=message.get('sql')
                    if validated_sql.get(message.get('sql_round'))!=sql:raise BirdFailure('unvalidated_sql_tool_call')
                    try:
                        latest=runtime.execute_native(sql,budget);latest_sql=sql
                        recorder.operation('execute',message.get('sql_round'),sql,valid=True)
                        executions.append({'success':True,'diagnostic':latest.diagnostic()})
                        return {'success':True,**latest.preview()}
                    except Exception as error:
                        latest=None;failure=fault(error);recorder.operation('execute',message.get('sql_round'),sql,valid=False,error=failure)
                        executions.append({'success':False,'error':failure.public()})
                        return {'success':False,'error':failure.public()}
                raise BirdFailure('unknown_agent_capability')
            with IsolatedAgent() as agent:
                report['agent_isolation']=agent.isolation
                if intent_enabled:report['agent_started']=True
                decision=agent.run({'mode':'answer','input':public,'schema':schema},handler,budget.started+600)
            report.update(agent_status=decision['status'],agent_trace=decision.get('trace'),executions=executions,validation_events=validation_events,
                first_sql_execution_success=executions[0]['success'] if executions else False,
                final_sql_execution_success=executions[-1]['success'] if executions else False)
            if decision.get('answered') and latest is not None and decision.get('sql')==latest_sql:
                # Gold and complete predicted tuples stay in this trusted process.
                # Gold SQL/results/EX feedback are never returned to the Agent RPC.
                if diagnostic_mode:
                    report.update(status='diagnostic_answered',complete=True,ex_correct=None,
                                  result=latest.diagnostic(),generated_sql=latest_sql)
                else:
                    result=runtime.execute_native(gold['gold_sql'],budget)
                    correct=compare_ex_rows(latest.rows,result.rows,predicted_complete=True,gold_complete=True)
                    report.update(status='scored',complete=True,ex_correct=correct,result=latest.diagnostic(),
                        generated_sql=latest_sql,result_diagnostics={'ordered_rows_match':latest.rows==result.rows,
                            'row_multiset_match':Counter(latest.rows)==Counter(result.rows),
                            'column_count_match':len(latest.columns)==len(result.columns)})
            else:report.update(status=decision['status'],ex_correct=None if diagnostic_mode else False)
        budget.remaining()
    except BaseException as error:
        if isinstance(error,KeyboardInterrupt):failure=BirdFailure('interrupted')
        else:failure=fault(error)
        report.update(status=failure.category,complete=False,ex_correct=False if request['mode']=='live' else None)
        report['errors'].append(failure.public())
    finally:
        if recorder is not None:report['development_diagnostics']=recorder.public()
        if runtime is not None:
            try:runtime.close();runtime.close();report['runtime_closed']=True
            except Exception as error:
                report['errors'].append(fault(error).public())
                report.update(status='runtime_close_failed',complete=False,ex_correct=False if request['mode']=='live' else None)
        report['budget']=budget.public();report['new_model_request_count']=budget.total_attempts
        if request.get('code_sha256')!=code_binding()['sha256']:
            report['errors'].append({'category':'case_code_changed_during_run'})
            report.update(status='case_code_changed_during_run',complete=False,ex_correct=False if request['mode']=='live' else None)
    return report


def main():
    try:
        data=sys.stdin.buffer.readline(MAX_FRAME+1)
        if not data or len(data)>MAX_FRAME or not data.endswith(b'\n'):raise BirdFailure('invalid_worker_frame')
        request=json.loads(data)
        if request.get('mode')=='watchdog_probe':time.sleep(60)
        report=execute(request)
    except BaseException:
        report={'status':'case_worker_failed','complete':False,'errors':[{'category':'case_worker_failed'}]}
    sys.stdout.write(json.dumps(report,ensure_ascii=False,separators=(',',':'))+'\n');sys.stdout.flush()


if __name__=='__main__':main()
