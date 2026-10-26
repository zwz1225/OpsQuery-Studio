"""Prepare new independent M3 E02 baseline/candidate directories; no secrets read."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

if __package__:
    from . import m3_e02_pair_common as c
else:
    import m3_e02_pair_common as c


def prepare(args):
    bundle_root=args.bundle_root.resolve();source=args.source_backend.resolve();root=args.workspace.resolve()
    manifest=c.bundle(bundle_root);payload=manifest['payload']
    c.require(not root.exists(),'Choose a new workspace; preserve all existing attempts')
    c.require(not root.is_relative_to(source) and not root.is_relative_to(bundle_root)
        and not source.is_relative_to(root) and not bundle_root.is_relative_to(root),'Workspace overlaps project or bundle')
    c.require(source.is_dir(),'Source backend directory does not exist')
    data=(args.data_root or source/'data/external/bird_mini_dev').resolve()
    model=(args.model_config_file or source/'.env').resolve()
    credentials=(args.credentials_file or Path.home()/'.local/share/askdata/m2_bird_credentials.json').resolve()
    c.require(data.is_dir(),'BIRD data-root directory is missing; supply --data-root')
    c.require(model.is_file() and credentials.is_file(),'Existing model configuration or M2 credentials file is missing')
    c.require(not any(p.is_relative_to(root) or root.is_relative_to(p) for p in (data,model,credentials)),'Shared input overlaps new workspace')
    parent=root.parent
    c.require(parent.is_dir(),'Workspace parent must already exist')
    free=shutil.disk_usage(parent).free
    c.require(free>=2*1024**3,'Fewer than 2 GiB free on workspace filesystem')
    root.mkdir()  # Exclusive creation: no overlays, deletions or credential copies.
    status=dict(stage='M3 E02 pair24 directory preparation',started_at=c.now(),run_status='running',
        bundle_id=manifest['bundle_id'],new_model_request_count=0,postgresql_connected=False,errors=[])
    c.write_new(root/'preparation.json',status)
    try:
        (root/'control').mkdir()
        for name,value in payload['controllers'].items():
            c.copy_new(bundle_root/'control'/name,root/'control'/name,value)
        c.copy_new(bundle_root/'bundle_manifest.json',root/'control/bundle_manifest.json',c.sha(bundle_root/'bundle_manifest.json'))
        for side in c.SIDES:
            base=c.side_base(root,side)
            for name,entry in payload['sides'][side]['assets'].items():
                c.copy_new(c.safe(bundle_root,entry['bundle_path']),c.safe(base,name),entry['sha256'])
            for name in ('m3_e02_pair_common.py','m3_e02_pair_side.py'):
                c.copy_new(bundle_root/'control'/name,base/'scripts'/name,payload['controllers'][name])
            c.write_new(base/'m3_context.json',dict(side=side,workspace=str(root),bundle_id=manifest['bundle_id']))
        c.write_new(root/'workspace.json',dict(schema='m3_e02_pair24_workspace_v1',bundle_id=manifest['bundle_id'],
            manifest_sha256=c.sha(root/'control/bundle_manifest.json'),data_root=str(data),
            source_backend=str(source),model_config_file=str(model),credentials_file=str(credentials),
            prepared_at=c.now(),secrets_copied=False))
        status['workspace_sha256']=c.sha(root/'workspace.json');c.checkpoint(root/'preparation.json',status)
        c.workspace(root)
        status.update(run_status='complete',prepared_side_count=2,baseline_code_files=96,candidate_code_files=98,
            free_bytes_before=free,secrets_read=False,secrets_copied=False,data_copied=False,
            live_target_verified=False,model_configuration_verified=False,
            next_step='Run the separate Linux check-only command before starting generation')
    except BaseException as error:
        status.update(run_status='failed',errors=[dict(type=type(error).__name__,
            message=str(error) if isinstance(error,c.PairError) else 'Preparation failed; raw details omitted')])
        raise
    finally:
        status['finished_at']=c.now();c.checkpoint(root/'preparation.json',status)
    return status


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle-root',type=Path,required=True)
    p.add_argument('--source-backend',type=Path,required=True)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--data-root',type=Path)
    p.add_argument('--model-config-file',type=Path)
    p.add_argument('--credentials-file',type=Path)
    return p


def main():
    args=parser().parse_args()
    try:
        result=prepare(args)
        print('Prepared pair workspace: '+str(args.workspace.resolve()))
        print('run_status='+result['run_status']+'; model_calls=0; database_connected=false')
    except (Exception,KeyboardInterrupt) as error:
        print(str(error) if isinstance(error,c.PairError) else 'Preparation failed; preserve any created directory and inspect preparation.json',file=sys.stderr)
        raise SystemExit(1)


if __name__=='__main__':main()
