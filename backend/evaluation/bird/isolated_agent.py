"""Standalone Agent process. stdlib only; no project imports, credentials or Gold.

Copied into a private empty directory and launched with -I -S. seccomp denies
all new filesystem opens, networking, process creation and process reads.
Landlock is an additional filesystem layer when supported by the host kernel.
All model/SQL capabilities are broker RPCs, never direct connections.
"""
import ctypes
import errno
import json
import os
from pathlib import Path
import platform
import resource
import socket
import sys
import sysconfig

FRAME_LIMIT=1048576
SYSTEM=('You answer the original English database question using the supplied official evidence and authorized PostgreSQL schema. '
        'Use PostgreSQL syntax and public schema; quote identifiers containing spaces, punctuation or mixed case. '
        'Do not change the question semantics after a SQL error. Return one JSON object: '
        '{"action":"query","sql":"one SELECT/WITH query"} or '
        '{"action":"clarify","reason":"missing information"}. '
        'There is no metric catalog, memory, answer lookup, other database, or filesystem tool. '
        'Samples are typed display values and may be truncated, never expected answers.')


def emit(value):
    sys.stdout.write(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n');sys.stdout.flush()


def receive():
    line=sys.stdin.buffer.readline(FRAME_LIMIT+1)
    if not line or len(line)>FRAME_LIMIT or not line.endswith(b'\n'):raise RuntimeError('invalid_frame')
    return json.loads(line)


def additional_landlock(libc,number):
    create,add,restrict=[number(n) for n in ('landlock_create_ruleset','landlock_add_rule','landlock_restrict_self')]
    abi=libc.syscall(ctypes.c_long(create),ctypes.c_void_p(0),ctypes.c_size_t(0),ctypes.c_uint(1))
    if abi<1:raise RuntimeError('landlock_unavailable')
    class Ruleset(ctypes.Structure):_fields_=[('handled_access_fs',ctypes.c_uint64)]
    class Beneath(ctypes.Structure):
        _pack_=1
        _fields_=[('allowed_access',ctypes.c_uint64),('parent_fd',ctypes.c_int32)]
    handled=(1<<13)-1
    if abi>=2:handled|=1<<13
    if abi>=3:handled|=1<<14
    rules=Ruleset(handled)
    rulesfd=libc.syscall(ctypes.c_long(create),ctypes.byref(rules),ctypes.c_size_t(ctypes.sizeof(rules)),ctypes.c_uint(0))
    if rulesfd<0:raise RuntimeError('landlock_create_failed')
    directories={Path(sysconfig.get_path('stdlib')).resolve(),Path(__file__).resolve().parent}
    try:
        for path in directories:
            fd=os.open(path,os.O_PATH|os.O_CLOEXEC)
            try:
                rule=Beneath((1<<2)|(1<<3),fd)
                if libc.syscall(ctypes.c_long(add),ctypes.c_int(rulesfd),ctypes.c_uint(1),ctypes.byref(rule),ctypes.c_uint(0))!=0:
                    raise RuntimeError('landlock_rule_failed')
            finally:os.close(fd)
        if libc.prctl(38,1,0,0,0)!=0:raise RuntimeError('no_new_privileges_failed')
        if libc.syscall(ctypes.c_long(restrict),ctypes.c_int(rulesfd),ctypes.c_uint(0))!=0:raise RuntimeError('landlock_restrict_failed')
    finally:os.close(rulesfd)
    return abi


def sandbox():
    if sys.platform!='linux' or platform.machine()!='x86_64':raise RuntimeError('linux_x86_64_isolation_required')
    libc=ctypes.CDLL(None,use_errno=True);libc.syscall.restype=ctypes.c_long
    try:sec=ctypes.CDLL('libseccomp.so.2',use_errno=True)
    except OSError:raise RuntimeError('seccomp_library_unavailable') from None
    sec.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p];sec.seccomp_syscall_resolve_name.restype=ctypes.c_int
    def number(name):
        value=sec.seccomp_syscall_resolve_name(name.encode())
        if value<0:raise RuntimeError('isolation_syscall_unavailable')
        return value
    class Version(ctypes.Structure):_fields_=[('major',ctypes.c_uint),('minor',ctypes.c_uint),('micro',ctypes.c_uint)]
    sec.seccomp_version.restype=ctypes.POINTER(Version)
    v=sec.seccomp_version().contents;library_version=f'{v.major}.{v.minor}.{v.micro}'
    if libc.prctl(38,1,0,0,0)!=0:raise RuntimeError('no_new_privileges_failed')
    # The Agent needs only already-open pipes after bootstrap. Mandatory seccomp
    # denies new file opens even on kernels where optional Landlock is disabled.
    # No filesystem permission is relaxed if this extra layer is unavailable.
    try:abi=additional_landlock(libc,number)
    except (RuntimeError,OSError):abi=None
    sec.seccomp_init.argtypes=[ctypes.c_uint32];sec.seccomp_init.restype=ctypes.c_void_p
    sec.seccomp_rule_add.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint]
    sec.seccomp_load.argtypes=[ctypes.c_void_p];sec.seccomp_release.argtypes=[ctypes.c_void_p]
    ctx=sec.seccomp_init(0x7fff0000)
    if not ctx:raise RuntimeError('seccomp_init_failed')
    denied=('socket socketpair connect bind listen accept accept4 execve execveat fork vfork clone clone3 '
        'ptrace process_vm_readv process_vm_writev pidfd_getfd pidfd_open pidfd_send_signal kill tkill tgkill '
        'mount umount2 pivot_root chroot unshare setns bpf userfaultfd io_uring_setup open_by_handle_at '
        'open openat openat2 creat truncate ftruncate unlink unlinkat rename renameat renameat2 mkdir mkdirat rmdir '
        'link linkat symlink symlinkat mknod mknodat chmod fchmod fchmodat chown lchown fchown fchownat '
        'utime utimes utimensat stat lstat newfstatat statx access faccessat faccessat2 readlink readlinkat '
        'getdents getdents64 setxattr lsetxattr fsetxattr removexattr lremovexattr fremovexattr').split()
    try:
        for name in denied:
            nr=number(name)
            if sec.seccomp_rule_add(ctx,0x00050000|errno.EPERM,nr,0)!=0:raise RuntimeError('seccomp_rule_failed')
        if sec.seccomp_load(ctx)!=0:raise RuntimeError('seccomp_load_failed')
    finally:sec.seccomp_release(ctx)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
    resource.setrlimit(resource.RLIMIT_NOFILE,(64,64))
    return {'filesystem':'seccomp_deny_all_new_file_opens','additional_landlock_abi':abi,'network_and_process':'seccomp',
            'seccomp_library_version':library_version,'kernel':platform.release(),
            'project_read_access':False,'environment_credentials':False,'direct_database_access':False}


def rpc(operation,**payload):
    emit({'event':'rpc','operation':operation,**payload});result=receive()
    if not result.get('ok'):raise RuntimeError(result.get('category','broker_rejected'))
    return result['result']


def probe(request):
    blocked=[]
    for path in request['paths']:
        try:
            with open(path,'rb') as stream:stream.read(1)
            blocked.append(False)
        except PermissionError:blocked.append(True)
        except OSError:blocked.append(False)  # nonexistent paths do not prove isolation
    network=False;process=False
    try:socket.socket()
    except PermissionError:network=True
    try:os.fork()
    except PermissionError:process=True
    return {'read_denials':blocked,'network_socket_denied':network,'process_creation_denied':process,
            'secret_environment_absent':not any(k in os.environ for k in ('LLM_API_KEY','PG_PASSWORD','M2_PG_ADMIN_PASSWORD'))}


def answer(context):
    payload=context['input']
    if set(payload)!={'case_id','database_id','dialect','question','evidence'} or payload['dialect']!='postgres':raise RuntimeError('invalid_public_input')
    observations=[];trace=[]
    system=SYSTEM
    if context['schema'].get('intent_contract'):
        system += (' This development run includes an explicit public-intent contract. Apply its output, NULL ranking, '
                   'population, name/ID and numeric conventions before your first SQL. The contract is grounded in '
                   'public input and authorized metadata, not reference answers. Do not add explanatory result columns '
                   'unless requested. For clarification, identify the specific missing field or ambiguity.')
        if context['schema']['intent_contract'].get('query_semantic_planning_guidance'):
            system += (' Apply query_semantic_planning_guidance before SQL: resolve aggregation grain and requested outputs; '
                       'preserve public constraints.')
    rounds=3
    if context['schema'].get('intent_contract'):
        rounds=context['schema']['intent_contract'].get('remaining_sql_execution_rounds',3)
        if type(rounds) is not int or not 1<=rounds<=3:raise RuntimeError('invalid_sql_round_budget')
    for sql_round in range(1,rounds+1):
        error=None
        for attempt in range(1,4):
            body={'input':payload,'schema':context['schema'],'observations':observations,'validation_error':error}
            decision=rpc('chat',system=system,user=json.dumps(body,ensure_ascii=False),sql_round=sql_round)
            if not isinstance(decision,dict):error='Expected a JSON object';continue
            if decision.get('action')=='clarify':return {'status':'clarification','answered':False,'trace':trace}
            if decision.get('action')!='query' or not isinstance(decision.get('sql'),str):error='Expected query action with sql';continue
            validation=rpc('validate',sql=decision['sql'],sql_round=sql_round)
            trace.append({'sql_round':sql_round,'validation_attempt':attempt,'valid':validation.get('valid')})
            if validation.get('retryable') is False:
                return {'status':'repeated_sql','answered':False,'trace':trace}
            if validation.get('valid'):
                result=rpc('sql',sql=decision['sql'],sql_round=sql_round)
                if result.get('success'):return {'status':'answered','answered':True,'sql':decision['sql'],'trace':trace}
                observations.append({'sql':decision['sql'],'error':result.get('error')});break
            error=validation.get('error')
            if validation.get('repair_feedback') is not None:
                error={**(error if isinstance(error,dict) else {}),'repair_feedback':validation['repair_feedback']}
        else:return {'status':'validation_failed','answered':False,'trace':trace}
    return {'status':'sql_failed','answered':False,'trace':trace}


def build_documents(context):
    if set(context)!={'mode','database_id','tables','profiles'}:raise RuntimeError('invalid_index_input')
    database=context['database_id'];output=[]
    for table in context['tables']:
        if table['database']!=database or table['id']!=database+'.'+table['name']:raise RuntimeError('index_domain_mismatch')
        for field in table['fields']:
            provided=context['profiles'][table['id']][field['name']]
            profile={k:provided[k] for k in ('row_count','null_count','samples','sample_truncated')}
            text=' | '.join([database,table['name'],field['name'],field['label'],field['type'],field['description'],
                field['value_description'],json.dumps(profile,ensure_ascii=False)])
            output.append({'doc_id':table['id']+'.'+field['name'],'database_id':database,'table_id':table['id'],
                'table_label':table['label'],'field_name':field['name'],'field_label':field['label'],'field_type':field['type'],
                'field_description':field['description'],'field_role':field['role'],'aliases':[],'samples':profile['samples'],
                'profile':json.dumps(profile,ensure_ascii=False),'semantic_text':text,'relation_ids':[]})
    return output


def main():
    try:
        protection=sandbox();emit({'event':'ready','isolation':protection})
        request=receive()
        if request.get('mode')=='probe':result=probe(request)
        elif request.get('mode')=='index':result=build_documents(request)
        else:result=answer(request)
        emit({'event':'done','result':result})
    except BaseException as error:
        controlled={'seccomp_library_unavailable','linux_x86_64_isolation_required','isolation_syscall_unavailable',
            'landlock_unavailable','landlock_create_failed','landlock_rule_failed','landlock_restrict_failed',
            'no_new_privileges_failed','seccomp_init_failed','seccomp_rule_failed','seccomp_load_failed'}
        category=str(error) if isinstance(error,RuntimeError) and str(error) in controlled else 'isolated_worker_failed'
        emit({'event':'failed','category':category});raise SystemExit(1)


if __name__=='__main__':main()
