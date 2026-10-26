"""One independently indexed E06 development24 baseline/candidate pair."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

if __package__:
    from . import m3_e06_pair24_common as c
else:
    import m3_e06_pair24_common as c


def _parent_death(parent):
    # No model secrets enter arguments. A killed driver must not leave its direct
    # generation/replay process running as an untracked command.
    import ctypes
    if ctypes.CDLL(None).prctl(1,signal.SIGKILL,0,0,0)!=0 or os.getppid()!=parent:
        os._exit(125)


def child(root,side,module,options,log,report=None,output=None,phase=None):
    c.workspace(root)
    command=[sys.executable,'-E','-s','-u','-m',module,*map(str,options)]
    if report is not None:
        report['phase']=phase;c.checkpoint(output,report)
    print('Starting '+(phase or side+'_'+module),flush=True)
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('xb') as stream:
        parent=os.getpid()
        process=subprocess.Popen(command,cwd=c.side_base(root,side),stdout=stream,stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,start_new_session=True,preexec_fn=lambda:_parent_death(parent))
        try:code=process.wait()
        except BaseException:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            process.wait();raise
    if report is not None:
        report.setdefault('child_exit_codes',{})[phase]=code;c.checkpoint(output,report)
    c.require(code==0,(phase or module)+' failed; inspect '+str(log))


def side_check(root,side,mode,target,*,capture=None,native=None,native_only=False,report=None,output=None,phase=None):
    options=['--mode',mode,'--output',target]
    if capture is not None:options+=['--capture',capture]
    if native is not None:options+=['--native',native]
    if native_only:options+=['--native-only']
    child(root,side,'scripts.m3_e06_pair24_side',options,target.with_suffix('.log'),report,output,phase)
    result=c.read(target);c.require(result['run_status']=='complete','Side checker did not complete')
    return result['result']


def capture_path(root,side):
    return c.side_base(root,side)/'evaluation/results'/('m3_e06_pair24_'+side+'_capture_server.json')


def native_path(root,side,recovery):
    directory=c.side_base(root,side)/'evaluation/results'
    primary=directory/('m3_e06_pair24_'+side+'_native_server.json')
    if not primary.exists():return primary,False
    try:complete=c.read(primary).get('run_status')=='complete'
    except (ValueError,OSError):complete=False
    if complete:return primary,True
    c.require(recovery,'Preserve failed native report; use --replay-only after checking the failure')
    retry=directory/('m3_e06_pair24_'+side+'_native_recovery1_server.json')
    if retry.exists():
        try:complete=c.read(retry).get('run_status')=='complete'
        except (ValueError,OSError):complete=False
        c.require(complete,'Native recovery already consumed; preserve evidence and stop')
        return retry,True
    return retry,False


def _generation_options(row,root,side):
    base=c.side_base(root,side)
    options=['--data-root',row['data_root'],'--results-dir',base/'evaluation/results',
        '--credentials-file',row['credentials_file'],'--model-config-file',row['model_config_file'],
        '--case-list',base/c.CASE_LIST,'--index-root',base/'data/m3_indexes',
        '--schema-coverage','--intent-candidate','--condition-relations','--save-snapshot','--output',capture_path(root,side)]
    return options


def failed_generation_evidence(root,payload):
    result={}
    for side in c.SIDES:
        path=capture_path(root,side)
        if not path.is_file():continue
        try:row=c.read(path)
        except (ValueError,OSError):continue
        if (row.get('code_binding',{}).get('files')!=payload['sides'][side]['code_files']
            or row.get('transport_policy')!=payload['transport_policy']):continue
        result[side]=dict(path=str(path),sha256=c.sha(path),run_status=row.get('run_status'),
            new_model_request_count=row.get('new_model_request_count'),
            recorded_case_count=len(row.get('cases',[])),
            completed_index_count=len(row.get('index_builds',[])),
            preparation_attempts=row.get('preparation_attempts',[]))
    return result


def execute(args):
    model_smoke=getattr(args,'model_probe',False)
    root=args.workspace.resolve();row,payload=c.workspace(root)
    c.require(c.read(root/'preparation.json')['run_status']=='complete','Workspace preparation did not complete')
    c.require(c.sha(Path(__file__))==payload['controllers']['run_m3_e06_pair24.py'],'Driver bytes differ from prepared controller')
    c.require(sys.platform=='linux','Pair checks/execution require the Linux PostgreSQL host')
    output=args.output.resolve() if args.output else root/'reports'/(
        'e06_pair24_preflight_server.json' if args.check_only else 'e06_pair24_native_recovery_server.json' if args.replay_only
        else 'e06_pair24_transport_model_probe_server.json' if model_smoke else 'e06_pair24_server.json')
    c.require(output.suffix=='.json' and output.is_relative_to(root/'reports') and not output.exists(),'Choose a new JSON report within workspace/reports')
    c.require(args.check_only or args.replay_only or not (root/'attempt').exists(),'This workspace already has a generation attempt; do not generate again')
    if args.replay_only:
        c.require((root/'attempt/reservation.json').is_file(),'No registered pair attempt to replay')
        c.require(c.read(root/'attempt/reservation.json')['bundle_id']==row['bundle_id'],'Attempt belongs to another bundle')
        c.require(not (root/'attempt/native_recovery.json').exists(),'Native recovery already reserved; preserve prior evidence')
    report=dict(stage='M3 E06 independent-index same-round development24 paired workflow',run_status='running',started_at=c.now(),
        bundle_id=row['bundle_id'],selected_case_ids=payload['case_ids'],check_only=args.check_only,replay_only=args.replay_only,model_probe=model_smoke,
        formal_benchmark=False,holdout_run=False,development24=True,
        new_model_request_count=0,errors=[],
        report_paths={},usage_scope='Generation/index and native reports separately own usage; failed native attempts remain separate evidence')
    c.write_new(output,report)
    try:
        with c.exclusive(root):
            probe_dir=root/'reports'/(output.stem+'_checks')
            probes={}
            for side in c.SIDES:
                probes[side]=side_check(root,side,'probe',probe_dir/(side+'_probe.json'),native_only=args.replay_only,
                    report=report,output=output,phase=side+'_static_preflight')
            left,right=(probes[s] for s in c.SIDES)
            a={k:v for k,v in left['code_binding'].items() if k not in ('files','sha256')}
            b={k:v for k,v in right['code_binding'].items() if k not in ('files','sha256')}
            c.require(a==b,'Baseline/candidate interpreter, dependencies or kernel differ')
            c.require(left['model_configuration']==right['model_configuration']==payload['model_configuration']
                and left['source_binding']==right['source_binding']==payload['source_binding'],'Pair public configuration differs')
            dependency=left['transport_dependency_binding']
            c.require(dependency==right['transport_dependency_binding'],'Pair DNS tool binary/version differs')
            report.update(static_preflight_passed=True,side_probes=probes,live_readiness_verified=False,
                transport_policy=payload['transport_policy'],generation_reserved=False)
            if not args.replay_only:
                report['phase']='process_dns_https_readiness';c.checkpoint(output,report)
                readiness={}
                for side in c.SIDES:
                    readiness[side]=side_check(root,side,'connection',probe_dir/(side+'_connection.json'),
                        report=report,output=output,phase=side+'_process_dns_https_readiness')
                report['dns_readiness']=dict(passed=all(r.get('passed') is True for r in readiness.values()),sides=readiness)
                c.checkpoint(output,report)
                c.require(report['dns_readiness']['passed'],
                    'Explicit DNS/HTTPS readiness failed before generation reservation; zero model calls; preserve report')
                c.require(all(r['binding']==dependency for r in readiness.values()),'Preflight dependency changed')
            lock_path=root/'transport_dependency_lock.json'
            if lock_path.exists():
                lock=c.read(lock_path)
                c.require(lock['bundle_id']==row['bundle_id'] and lock['binding']==dependency,'Locked DNS dependency changed')
            else:
                c.require(not args.replay_only,'Native recovery requires the original dependency lock')
                c.write_new(lock_path,dict(bundle_id=row['bundle_id'],binding=dependency,recorded_at=c.now()))
            report['transport_dependency_binding']=dependency
            report['preflight_passed']=True
            if args.check_only:
                report.update(run_status='complete',phase='preflight_with_process_dns_https',new_model_request_count=0)
                return report
            if model_smoke:
                report['new_model_request_count']=None
                result=side_check(root,'baseline','model-probe',probe_dir/'model_probe.json',
                    report=report,output=output,phase='shared_transport_embedding_probe')
                report.update(model_probe_result=result,new_model_request_count=result['new_model_request_count'])
                c.require(result.get('passed') is True and result['transport_dependency_binding']==dependency,
                    'Bounded shared transport embedding probe failed; preserve report and attempt')
                report.update(run_status='complete',phase='transport_model_probe_complete')
                c.checkpoint(output,report)
                c.write_new(root/'transport_model_probe_receipt.json',dict(bundle_id=row['bundle_id'],
                    binding=dependency,model_configuration=payload['model_configuration'],
                    report_path=str(output),child_report_path=str(probe_dir/'model_probe.json'),
                    child_report_sha256=c.sha(probe_dir/'model_probe.json'),passed=True))
                return report
            if not args.check_only:
                if args.replay_only:
                    c.write_new(root/'attempt/native_recovery.json',dict(bundle_id=row['bundle_id'],reserved_at=c.now(),generation_allowed=False))
                else:
                    receipt=c.read(root/'transport_model_probe_receipt.json')
                    c.require(receipt.get('passed') is True and receipt['bundle_id']==row['bundle_id']
                        and receipt['binding']==dependency and receipt['model_configuration']==payload['model_configuration'],
                        'Successful current shared transport model probe is required before generation')
                    # The controller updates its own final timestamp after writing
                    # a smoke receipt, so bind the immutable child probe bytes.
                    child_probe=Path(receipt['child_report_path'])
                    c.require(child_probe.is_relative_to(root/'reports') and c.sha(child_probe)==receipt['child_report_sha256'],
                        'Transport model probe evidence changed')
                    (root/'attempt').mkdir()
                    c.write_new(root/'attempt/reservation.json',dict(bundle_id=row['bundle_id'],reserved_at=c.now(),
                        maximum_generated_cases=48,baseline_generations=1,candidate_generations=1,automatic_generation_resume=False,
                        baseline_index_builds=1,candidate_index_builds=1,shared_index_copy=False))
            report['generation_reserved']=True;c.checkpoint(output,report)
            private=c.private_stats(row) if not args.replay_only else None
            captures={}
            for side in c.SIDES:
                path=capture_path(root,side)
                if not args.replay_only:
                    c.require(not path.exists(),'Capture already exists; generation is not resumable')
                    report['new_model_request_count']=None
                    child(root,side,'evaluation.bird.diagnostic_runner',_generation_options(row,root,side),
                        root/'reports/logs'/(side+'_generation.log'),report,output,side+'_generation')
                c.require(path.is_file(),'Both complete captures are required for replay-only; no generation will be resumed')
                checked=side_check(root,side,'capture',probe_dir/(side+'_capture_check.json'),capture=path,
                    report=report,output=output,phase=side+'_capture_integrity')
                captures[side]=c.read(path)
                report['report_paths'][side+'_capture']=dict(path=str(path),sha256=checked['capture_sha256'])
                if private is not None:c.require(c.private_stats(row)==private,'Private input file changed during generation')
            # Both sides have finished generation before either new Gold replay.
            report['both_captures_complete_before_gold_replay']=True
            natives={}
            for side in c.SIDES:
                path,reused=native_path(root,side,args.replay_only)
                source=capture_path(root,side);source_sha=c.sha(source)
                if not reused:
                    options=['--data-root',row['data_root'],'--results-dir',c.side_base(root,side)/'evaluation/results',
                        '--credentials-file',row['credentials_file'],'--source-report',source,
                        '--source-sha256',source_sha,'--output',path]
                    child(root,side,'scripts.rescore_m2_intent_candidate',options,
                        root/'reports/logs'/(side+'_native'+('_recovery1' if args.replay_only else '')+'.log'),
                        report,output,side+'_native_replay')
                checked=side_check(root,side,'native',probe_dir/(side+'_native_check.json'),capture=source,native=path,
                    report=report,output=output,phase=side+'_native_integrity')
                c.require(c.sha(source)==source_sha,'Capture changed during native replay')
                natives[side]=c.read(path)
                report['report_paths'][side+'_native']=dict(path=str(path),sha256=checked['native_sha256'],reused=reused)
            result=c.compare_pair(payload,captures,natives)
            result_path=root/'reports'/('e06_pair24_comparison_recovery_server.json' if args.replay_only else 'e06_pair24_comparison_server.json')
            c.write_new(result_path,dict(stage='M3 E06 fixed development24 comparison',run_status='complete',bundle_id=row['bundle_id'],
                source_reports=report['report_paths'],**result))
            report.update(run_status='complete',phase='complete',comparison_report=str(result_path),comparison_sha256=c.sha(result_path),
                summary={k:v for k,v in result.items() if k not in ('cases','by_database')},
                current_command_model_requests=0 if args.replay_only else None,
                generation_model_http={s:dict(case_calls=captures[s]['summary']['case_model_http_attempts'],
                    shared_index_calls=captures[s]['summary']['shared_index_http_attempts']) for s in c.SIDES},
                new_model_request_count=0 if args.replay_only else None)
            values=[v for info in report['generation_model_http'].values() for v in info.values()]
            if not args.replay_only and all(type(v) is int for v in values):report['new_model_request_count']=sum(values)
            c.workspace(root)
            return report
    except (Exception,KeyboardInterrupt) as error:
        report.update(run_status='failed',errors=[dict(type=type(error).__name__,
            message=str(error) if isinstance(error,c.PairError) else 'Workflow failed; raw credential/driver details omitted')])
        if report.get('generation_reserved') and not args.replay_only:
            report['generation_failure_evidence']=failed_generation_evidence(root,payload)
            # A killed child without a readable budget remains unknown, never zero.
            values=[v.get('new_model_request_count') for v in report['generation_failure_evidence'].values()]
            started=sum(k.endswith('_generation') for k in report.get('child_exit_codes',{}))
            if len(values)==started and values and all(type(v) is int for v in values):
                report['new_model_request_count']=sum(values)
        return report
    finally:
        report['finished_at']=c.now();c.checkpoint(output,report)


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--output',type=Path)
    modes=p.add_mutually_exclusive_group()
    modes.add_argument('--check-only',action='store_true')
    modes.add_argument('--replay-only',action='store_true',help='At most one native-only recovery; both captures must already be complete')
    modes.add_argument('--model-probe',action='store_true',help='One bounded 10-input embedding connection smoke; no questions or SQL')
    return p


def main():
    try:
        report=execute(parser().parse_args())
        print(json.dumps({k:report.get(k) for k in ('run_status','phase','comparison_report','summary','errors')},ensure_ascii=False,indent=2))
        raise SystemExit(0 if report['run_status']=='complete' else 1)
    except (Exception,KeyboardInterrupt) as error:
        print(str(error) if isinstance(error,c.PairError) else 'Pair command failed; preserve existing reports',file=sys.stderr)
        raise SystemExit(1)


if __name__=='__main__':main()
