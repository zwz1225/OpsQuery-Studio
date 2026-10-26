"""Development candidate: bounded intent coverage inside already anchored tables."""
from __future__ import annotations

import math
import re

from evaluation.bird_protocol import validate_agent_input
from .budgets import BirdFailure

POLICY = 'bird_authorized_schema_coverage_v1'
BASELINE_POLICY = 'bird_rerank_055_top20_v1'
THRESHOLD = .55
FLOOR = .50
MAX_FIELDS = 20
MAX_ADDITIONS = 4


def contract(enabled=False):
    return {'policy_id': POLICY if enabled else BASELINE_POLICY,
            'threshold': THRESHOLD, 'max_fields': MAX_FIELDS,
            'coverage_enabled': enabled, 'coverage_floor': FLOOR if enabled else None,
            'max_coverage_fields': MAX_ADDITIONS if enabled else 0,
            'coverage_scope': 'existing_rrf_candidates_in_baseline_selected_tables' if enabled else None,
            'intent_source': 'original_question_and_official_evidence' if enabled else None,
            'metadata_match': 'native_field_name_or_official_field_label' if enabled else None,
            'coverage_gain': 'intent_terms_not_yet_covered_in_same_table' if enabled else None,
            'formal_protocol_override': False, 'development_candidate': enabled}


def terms(text):
    # English public inputs and official labels only. No samples or question-bank terms.
    stop = {'a','an','the','of','for','in','on','and','or','to','is','are','was','were','be',
            'what','which','who','how','with','from','by','as','at','that','this','it','its',
            'their','all','list','show','give','get','indicate','name','names','id','ids'}
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    return {w[:-1] if len(w)>4 and w.endswith('s') and not w.endswith('ss') else w
            for w in re.findall(r'[a-z]+', text.lower()) if len(w)>2 and w not in stop}


def select_fields(documents, candidates, scores, public_input, *, enabled=False):
    validate_agent_input(public_input)
    ranked=[]
    for position, score in scores.items():
        if type(position) is not int or not 0<=position<len(candidates) or type(score) not in (int,float) or not math.isfinite(score) or not 0<=score<=1:
            raise BirdFailure('invalid_schema_rerank_score')
        ranked.append((candidates[position], score))
    ranked.sort(key=lambda pair:pair[1], reverse=True)
    # Reject foreign candidates even when their score would not select them.
    for index in candidates:
        d=documents[index]
        if d.database_id!=public_input['database_id'] or not d.table_id.startswith(d.database_id+'.') or d.doc_id!=d.table_id+'.'+d.field_name:
            raise BirdFailure('coverage_source_mismatch')
    baseline=[pair for pair in ranked if pair[1]>=THRESHOLD][:MAX_FIELDS]
    selected=list(baseline);base_indices={i for i,_ in baseline}
    anchored={documents[i].table_id for i,_ in baseline}
    intent=terms(public_input['question']+'\n'+public_input['evidence'])
    covered_terms={table:set() for table in anchored}
    for index,_ in baseline:
        d=documents[index]
        covered_terms[d.table_id].update(intent & terms(d.field_name+' '+d.field_label))
    details={}
    by_index=dict(ranked)
    for index in candidates:
        score=by_index.get(index)
        details[index]={'selection_reason':'selected' if index in base_indices else
                        'rerank_not_returned' if score is None else
                        'below_threshold' if score<THRESHOLD else 'beyond_top20',
                        'matched_intent_terms':[]}
    if enabled:
        additions=0
        for index,score in ranked:
            if index in base_indices or score>=THRESHOLD:continue
            d=documents[index];matched=sorted(intent & terms(d.field_name+' '+d.field_label))
            gain=sorted(set(matched)-covered_terms.get(d.table_id,set()))
            item=details[index];item.update(matched_intent_terms=matched,uncovered_intent_terms=gain)
            reason=('below_coverage_floor' if score<FLOOR else
                    'coverage_table_not_anchored' if d.table_id not in anchored else
                    'coverage_no_intent_match' if not matched else
                    'coverage_intent_already_covered' if not gain else
                    'coverage_total_field_cap' if len(selected)>=MAX_FIELDS else
                    'coverage_addition_cap' if additions>=MAX_ADDITIONS else 'selected_coverage')
            item['selection_reason']=reason
            if reason=='selected_coverage':
                selected.append((index,score));additions+=1
                covered_terms[d.table_id].update(matched)
    return selected, {'policy':contract(enabled),
        'baseline_field_ids':[documents[i].doc_id for i,_ in baseline],
        'anchored_table_ids':sorted(anchored),
        'coverage_field_ids':[documents[i].doc_id for i,_ in selected if i not in base_indices],
        'candidate_decisions':details}
