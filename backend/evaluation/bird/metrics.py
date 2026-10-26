"""Frozen-denominator summaries. Missing/failed cases are never filtered out."""
from collections import Counter


def percentile(values,p):
    if not values:return None
    values=sorted(values);position=(len(values)-1)*p;left=int(position);fraction=position-left
    return round(values[left]*(1-fraction)+values[min(left+1,len(values)-1)]*fraction,3)


def summarize(cases,metadata,mode):
    def group(rows):
        n=len(rows);complete=sum(c.get('complete') is True for c in rows)
        correct=sum(c.get('ex_correct') is True and c.get('complete') is True and c.get('status')=='scored' and not c.get('errors') for c in rows)
        data={'case_count':n,'complete_result_count':complete,'status_counts':dict(Counter(c['status'] for c in rows))}
        if mode=='live':
            data.update(primary_denominator=n,ex_pass_count=correct,primary_ex=correct/n if n else None,
                ex_given_complete_results=correct/complete if complete else None,
                first_sql_execution_success_count=sum(c.get('first_sql_execution_success') is True for c in rows),
                final_sql_execution_success_count=sum(c.get('final_sql_execution_success') is True for c in rows),
                clarification_rate=sum(c.get('status')=='clarification' for c in rows)/n if n else None)
        else:data['gold_ready_count']=sum(c.get('status')=='gold_ready' and c.get('complete') is True for c in rows)
        return data
    output=group(cases)
    elapsed=[c['case_wall_seconds'] for c in cases if 'case_wall_seconds' in c]
    output['latency_seconds']={'p50':percentile(elapsed,.5),'p95':percentile(elapsed,.95),'measured_count':len(elapsed)}
    output['by_database']={db:group([c for c in cases if c['database_id']==db]) for db in sorted({c['database_id'] for c in cases})}
    output['by_difficulty']={d:group([c for c in cases if metadata[c['case_id']]['difficulty']==d]) for d in ('simple','moderate','challenging')}
    return output
