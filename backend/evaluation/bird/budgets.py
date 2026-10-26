"""Shared per-case counters and monotonic deadlines. Retries consume the same counters."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import signal
import time
from scripts.m2_b_common import PreparationError


class BirdFailure(PreparationError):
    def __init__(self, category: str, sqlstate=None):
        self.category = category
        self.sqlstate = sqlstate if isinstance(sqlstate, str) and len(sqlstate) == 5 and sqlstate.isalnum() else None
        super().__init__(category)
    def public(self): return {'category': self.category, 'sqlstate': self.sqlstate}


@dataclass
class Budget:
    wall_seconds: float = 600
    total_limit: int = 16
    chat_limit: int = 10
    started: float = field(default_factory=time.monotonic)
    total_attempts: int = 0
    chat_attempts: int = 0
    sql_calls: int = 0
    validation_attempts: dict = field(default_factory=dict)
    generation_attempts: dict = field(default_factory=dict)
    events: list = field(default_factory=list)

    def remaining(self) -> float:
        seconds = self.wall_seconds-(time.monotonic()-self.started)
        if seconds <= 0: raise BirdFailure('case_wall_timeout')
        return seconds

    def model_attempt(self, kind: str, *, retry: int = 0, prompt: bytes = b'') -> float:
        self.remaining()
        if kind not in {'chat','embedding','rerank'}: raise BirdFailure('unknown_model_operation')
        if retry not in (0,1): raise BirdFailure('transport_retry_limit')
        if len(prompt) > 98304: raise BirdFailure('prompt_byte_limit')
        if self.total_attempts >= self.total_limit: raise BirdFailure('model_attempt_limit')
        if kind == 'chat' and self.chat_attempts >= self.chat_limit: raise BirdFailure('chat_attempt_limit')
        self.total_attempts += 1; self.chat_attempts += int(kind == 'chat')
        self.events.append({'kind':kind,'retry':retry,'usage':None,'returned_model':None})
        return min(180.0, self.remaining())

    def sql_call(self):
        self.remaining()
        if self.sql_calls >= 3: raise BirdFailure('sql_tool_call_limit')
        self.sql_calls += 1

    def validation(self, sql_round: int):
        self.remaining()
        if type(sql_round) is not int or not 1 <= sql_round <= 3: raise BirdFailure('invalid_sql_round')
        n = self.validation_attempts.get(sql_round,0)
        if n >= 3: raise BirdFailure('validation_attempt_limit')
        self.validation_attempts[sql_round] = n+1

    def generation(self,sql_round: int):
        self.remaining()
        if type(sql_round) is not int or not 1<=sql_round<=3:raise BirdFailure('invalid_sql_round')
        n=self.generation_attempts.get(sql_round,0)
        if n>=3:raise BirdFailure('generation_attempt_limit')
        self.generation_attempts[sql_round]=n+1

    def public(self):
        return {'model_http_attempts':self.total_attempts,'chat_http_attempts':self.chat_attempts,
                'sql_tool_calls':self.sql_calls,'validation_attempts':self.validation_attempts,'generation_attempts':self.generation_attempts,
                'model_events':self.events,'elapsed_seconds':round(time.monotonic()-self.started,3)}


@contextmanager
def hard_deadline(seconds: float, category: str):
    """Linux main-thread deadline, including DNS, response bodies and client fetches."""
    if not hasattr(signal,'setitimer'): raise BirdFailure('linux_deadline_unavailable')
    old = signal.getsignal(signal.SIGALRM)
    def expired(*args): raise BirdFailure(category)
    signal.signal(signal.SIGALRM,expired)
    previous = signal.setitimer(signal.ITIMER_REAL,max(.001,seconds))
    try: yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0); signal.signal(signal.SIGALRM,old)
        if previous[0]: signal.setitimer(signal.ITIMER_REAL,*previous)
