"""Bounded JSON pipes and hard process deadlines. No inherited credentials/DB fds."""
from __future__ import annotations

import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from .budgets import BirdFailure

MAX_FRAME=1048576


class Channel:
    def __init__(self,process):self.process=process;self.buffer=b''
    def send(self,value,deadline=None):
        data=json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()+b'\n'
        if len(data)>MAX_FRAME:raise BirdFailure('ipc_payload_limit')
        deadline=deadline or time.monotonic()+15;view=memoryview(data);fd=self.process.stdin.fileno()
        os.set_blocking(fd,False)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(fd,selectors.EVENT_WRITE)
                while view:
                    seconds=deadline-time.monotonic()
                    if seconds<=0 or not selector.select(seconds):raise BirdFailure('case_wall_timeout')
                    try:sent=os.write(fd,view[:65536])
                    except BlockingIOError:continue
                    if not sent:raise BirdFailure('worker_pipe_closed')
                    view=view[sent:]
        finally:os.set_blocking(fd,True)
    def receive(self,deadline):
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout,selectors.EVENT_READ)
            while b'\n' not in self.buffer:
                seconds=deadline-time.monotonic()
                if seconds<=0 or not selector.select(seconds):raise BirdFailure('case_wall_timeout')
                block=os.read(self.process.stdout.fileno(),65536)
                if not block:raise BirdFailure('worker_exited')
                self.buffer+=block
                if len(self.buffer)>MAX_FRAME:raise BirdFailure('ipc_payload_limit')
        line,self.buffer=self.buffer.split(b'\n',1)
        try:return json.loads(line)
        except (ValueError,UnicodeDecodeError):raise BirdFailure('invalid_worker_frame') from None


class IsolatedAgent:
    def __init__(self):
        if sys.platform!='linux':raise BirdFailure('linux_isolation_required')
        self.directory=tempfile.TemporaryDirectory(prefix='askdata_bird_agent_')
        self.process=None
        try:
            target=Path(self.directory.name)/'agent.py';shutil.copyfile(Path(__file__).with_name('isolated_agent.py'),target)
            self.process=subprocess.Popen([sys.executable,'-I','-S',str(target)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,cwd=self.directory.name,env={'LANG':'C.UTF-8','TZ':'UTC'},close_fds=True,bufsize=0)
            self.channel=Channel(self.process)
            ready=self.channel.receive(time.monotonic()+15)
            if ready.get('event')!='ready':raise BirdFailure(ready.get('category','agent_isolation_unavailable'))
            self.isolation=ready['isolation']
        except BaseException:self.close();raise
    def run(self,context,handler,deadline):
        self.channel.send(context,deadline)
        while True:
            response=self.channel.receive(deadline)
            if response.get('event')=='done':return response['result']
            if response.get('event')!='rpc':raise BirdFailure('isolated_worker_failed')
            operation=response.get('operation')
            if operation not in {'chat','validate','sql'}:raise BirdFailure('unknown_agent_capability')
            result=handler(operation,response)
            self.channel.send({'ok':True,'result':result},deadline)
    def close(self):
        if self.process is not None:
            if self.process.poll() is None:self.process.kill()
            self.process.wait(timeout=5)
            for stream in (self.process.stdin,self.process.stdout):
                if stream:stream.close()
            self.process=None
        self.directory.cleanup()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()


def isolation_probe(paths):
    with IsolatedAgent() as agent:
        result=agent.run({'mode':'probe','paths':[str(p) for p in paths]},lambda *args:None,time.monotonic()+15)
        if not all(result.get('read_denials',[])) or len(result.get('read_denials',[]))!=len(paths) or not all(result.get(k) is True for k in
                ('network_socket_denied','process_creation_denied','secret_environment_absent')):
            raise BirdFailure('isolation_probe_failed')
        return {'isolation':agent.isolation,'probes':result,'passed':True}


def run_case_process(request,*,seconds=600):
    """Trusted scorer/broker child; its isolated Agent inherits this process group."""
    if sys.platform!='linux':raise BirdFailure('linux_supervisor_required')
    if not 0<seconds<=600:raise BirdFailure('invalid_supervisor_timeout')
    deadline=time.monotonic()+seconds;completed=False
    command=[sys.executable,'-m','evaluation.bird.case_worker']
    trusted_environment={'LANG':'C.UTF-8','TZ':'UTC'}
    if os.getenv('LD_LIBRARY_PATH'):trusted_environment['LD_LIBRARY_PATH']=os.environ['LD_LIBRARY_PATH']
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
        cwd=Path(__file__).resolve().parents[2],env=trusted_environment,
        start_new_session=True,close_fds=True,bufsize=0)
    try:
        channel=Channel(process);channel.send(request,deadline)
        result=channel.receive(deadline)
        try:process.wait(timeout=max(.001,min(5,deadline-time.monotonic())))
        except subprocess.TimeoutExpired:raise BirdFailure('case_wall_timeout') from None
        completed=True
        if process.returncode!=0:raise BirdFailure('case_worker_failed')
        return result
    finally:
        # Owned session only. Kills the case and any surviving Agent descendants.
        if not completed:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        process.wait(timeout=5)
        for stream in (process.stdin,process.stdout):
            if stream:stream.close()
