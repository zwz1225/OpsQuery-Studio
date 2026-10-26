"""Observe one frozen embedding client without changing its source or retry budget."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time


def safe_exception(error):
    reason = getattr(error, 'reason', None)
    row = {'exception_type': type(error).__name__,
           'reason_type': type(reason).__name__ if reason is not None else None}
    for name in ('errno', 'verify_code', 'code', 'pos', 'lineno', 'colno'):
        value = getattr(reason if reason is not None else error, name, None)
        if type(value) is int:
            row[name] = value
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', type=Path, required=True)
    parser.add_argument('--model-config-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compare-raw', action='store_true',
                        help='One raw POST control followed by the frozen client (at most 3 HTTP attempts total)')
    args = parser.parse_args()
    backend = args.backend.resolve()
    output = args.output.resolve()
    if output.is_relative_to(backend) or output == args.model_config_file.resolve():
        parser.error('Diagnostic output must be outside the frozen backend and config file')
    if not backend.is_dir() or not args.model_config_file.is_file():
        parser.error('Backend or model config file is missing')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive reservation preserves every earlier diagnostic.
    with output.open('x', encoding='utf-8') as stream:
        stream.write('{"run_status":"running"}\n')
    started = time.monotonic()
    report = dict(stage='M3 E03 isolated embedding transport diagnostic',
                  formal_benchmark=False, paired_experiment=False,
                  input_count=10, maximum_http_attempts=3 if args.compare_raw else 2,
                  exceptions=[], dns_calls=[])
    previous_trace = sys.gettrace()
    original_getaddrinfo = socket.getaddrinfo
    budget = None
    try:
        sys.path.insert(0, str(backend))
        from evaluation.bird import model
        from evaluation.bird.budgets import Budget, BirdFailure
        source = Path(model.__file__).resolve()
        if source != backend / 'evaluation/bird/model.py':
            raise RuntimeError('Unexpected client import')
        report['model_code_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
        report['proxy_configured'] = bool(model.urllib.request.getproxies())
        config = model.ModelConfig.load(args.model_config_file)
        report['expected_embedding_hostname'] = model.urllib.parse.urlsplit(config.embedding_base).hostname
        phase = 'frozen_client'

        def traced_getaddrinfo(host, port, *a, **kw):
            stamp = time.monotonic()
            hostname = str(host)
            if config.api_key in hostname:
                hostname = '<redacted>'
            entry = dict(phase=phase, hostname=hostname, port=port,
                         family=kw.get('family', a[0] if a else 0))
            try:
                rows = original_getaddrinfo(host, port, *a, **kw)
                entry.update(status='complete', address_count=len(rows))
                return rows
            except Exception as error:
                entry.update(status='failed', **safe_exception(error))
                raise
            finally:
                entry['elapsed_seconds'] = round(time.monotonic() - stamp, 3)
                if len(report['dns_calls']) < 32:
                    report['dns_calls'].append(entry)

        socket.getaddrinfo = traced_getaddrinfo
        texts = [f'Authorized schema field embedding probe {i}: description and sample metadata.'
                 for i in range(10)]
        if args.compare_raw:
            phase = 'raw_control'
            report['raw_control'] = dict(http_attempts=1)
            try:
                body = json.dumps(dict(model='text-embedding-v4', input=texts,
                                       dimensions=1024, encoding_format='float'),
                                  ensure_ascii=False, separators=(',', ':')).encode()
                request = model.urllib.request.Request(
                    config.embedding_base.rstrip('/') + '/embeddings', data=body,
                    method='POST', headers={'Authorization': 'Bearer ' + config.api_key,
                                           'Content-Type': 'application/json'})
                with model.urllib.request.urlopen(request, timeout=60) as response:
                    report['raw_control'].update(http_status=response.status,
                        content_type=response.headers.get('Content-Type'))
                    raw = response.read(16*1024*1024+1)
                if len(raw)>16*1024*1024:
                    raise ValueError('Response limit')
                value = json.loads(raw)
                items = value.get('data')
                report['raw_control'].update(status='complete', response_bytes=len(raw),
                    data_count=len(items) if isinstance(items, list) else None)
            except Exception as error:
                report['raw_control'].update(status='failed', failure=safe_exception(error))
        phase = 'frozen_client'
        budget = Budget(wall_seconds=180, total_limit=2, chat_limit=0)
        filename = os.path.normcase(str(source))

        def trace(frame, event, arg):
            if os.path.normcase(os.path.abspath(frame.f_code.co_filename)) != filename:
                return None
            if event == 'exception':
                error = arg[1]
                if isinstance(error, (OSError, json.JSONDecodeError, BirdFailure)):
                    row = safe_exception(error)
                    row.update(function=frame.f_code.co_name, line=frame.f_lineno)
                    if len(report['exceptions']) < 32:
                        report['exceptions'].append(row)
            return trace

        sys.settrace(trace)
        vectors = model.Models(config, budget).embed(texts)
        report.update(run_status='complete', vector_count=len(vectors),
                      dimensions=[len(v) for v in vectors])
    except Exception as error:
        report.update(run_status='failed', failure=safe_exception(error))
        # The known application category is public; arbitrary error strings are private.
        if type(error).__name__ == 'BirdFailure':
            report['failure_category'] = error.category
    finally:
        sys.settrace(previous_trace)
        socket.getaddrinfo = original_getaddrinfo
        if budget is not None:
            report['http_attempts'] = budget.total_attempts
            report['events'] = [{k: event.get(k) for k in
                                ('kind', 'retry', 'status', 'http_status', 'usage')}
                               for event in budget.events]
        report['total_http_attempts'] = (budget.total_attempts if budget is not None else 0) + report.get('raw_control', {}).get('http_attempts', 0)
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
        output.write_text(text, encoding='utf-8')
        print(text, end='')
    return 0 if report['run_status'] == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
