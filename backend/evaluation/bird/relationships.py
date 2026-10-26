"""Authorized FK alternatives and public counted-entity grain; no scorer inputs."""
from __future__ import annotations

from copy import deepcopy
import re
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope

from app.retrieval.graph import SchemaGraphBuilder
from scripts.m2_b_common import digest_json


class IntentGraphBuilder(SchemaGraphBuilder):
    def _shortest_path_relations(self,selected_tables,allowed_tables):
        baseline=super()._shortest_path_relations(selected_tables,allowed_tables)
        included=set(selected_tables)
        for r in baseline:included.update((r['left_table'],r['right_table']))
        chosen=list(baseline);keys={(r['left_table'],r['left_field'],r['right_table'],r['right_field']) for r in chosen}
        # Existing bridge paths are retained. Add alternatives only inside this
        # authorized graph, never expand arbitrary new tables via all-FK closure.
        for r in self.relations:
            key=(r['left_table'],r['left_field'],r['right_table'],r['right_field'])
            if len(chosen)>=24:break
            if key not in keys and {r['left_table'],r['right_table']}<=included<=allowed_tables:
                chosen.append(r);keys.add(key)
        return chosen


def role_context(runtime,public,graph):
    from .intent import checked_tables,mentioned,text_input,normalized
    tables=checked_tables(runtime);text=text_input(public);roles=[]
    for join in graph['joins']:
        child=tables[join['right_table']];field=next(f for f in child['fields'] if f['name']==join['right_field'])
        roles.append({'relation_id':join['id'],'parent_table':join['left_table'],'parent_field':join['left_field'],
                      'child_table':join['right_table'],'child_field':join['right_field'],
                      'role_label':field.get('label',field['name']),'role_description':field.get('description','')[:512],
                      'source':'current_authorized_declared_foreign_key','mandatory':False})
    # Numeric predicates identify an action-bearing table without treating their
    # constants as predicates on other same-valued fields.
    numeric_fields=re.findall(r'\b([A-Za-z_]\w*)\s*=\s*[0-9]+\b',public['evidence'])
    condition_tables={tid for tid,t in tables.items() if any(f['name'].casefold() in {v.casefold() for v in numeric_fields} for f in t['fields'])}
    actor_action=bool(re.search(r'\b(?:added|cast|submitted|performed|made|posted)\b',public['question'],re.I))
    preferences=[];groups=[]
    if actor_action:
        for role in roles:
            parent=tables[role['parent_table']]
            labels=[f for f in parent['fields'] if 'name' in f['name'].lower() and mentioned(f,text)]
            if labels and role['child_table'] in condition_tables:
                preferences.append({'relation_id':role['relation_id'],
                    'basis':'public_action_and_condition_owner_to_requested_entity_label','advisory_only':True})
                for table in graph['tables']:
                    for field in tables[table['id']]['fields']:
                        # A title explicitly named as context can disambiguate the
                        # actor. This is a visible development output convention.
                        if normalized(field['name'])=='title' and mentioned(field,text):
                            groups.append({'actor_label':parent['id']+'.'+labels[0]['name'],
                                           'context_label':table['id']+'.'+field['name'],
                                           'policy':'participant_with_named_context_v1','advisory_only':True})
    return {'policy':'authorized_role_alternatives_v1','joins_are_alternatives':True,
            'roles':roles,'preferred_actor_relations':preferences,'context_output_groups':groups,
            'guidance':'Choose the edge matching the requested action. Editor, owner and event participant are different roles; do not AND all alternative edges.'}


def build_graph(runtime,hits,public):
    graph=IntentGraphBuilder(runtime=runtime).build(hits)
    graph['relation_role_context']=role_context(runtime,public,graph)
    graph['graph_version']=digest_json({k:v for k,v in graph.items() if k!='graph_version'})[:12]
    return graph


def grain_contract(runtime,public):
    from .intent import checked_tables,text_input
    text_input(public);tables=checked_tables(runtime)
    if not re.search(r'\b(?:percentage|percent|proportion)\b',public['question'],re.I):return {}
    counted=re.findall(r'\bCOUNT\s*\(\s*(DISTINCT\s+)?(?:[A-Za-z_]\w*\.)?([A-Za-z_]\w*)\s*\)',public['evidence'],re.I)
    candidates=[]
    for distinct,key in counted:
        matches=[(tid,f) for tid,t in tables.items() for f in t['fields'] if f['name'].casefold()==key.casefold()
                 and [v['name'] for v in t['fields'] if v.get('role')=='primary_key']==[f['name']]]
        if len(matches)!=1:continue
        tid,f=matches[0];primary=[v['name'] for v in tables[tid]['fields'] if v.get('role')=='primary_key']
        if primary==[f['name']]:
            entity=re.escape(tables[tid]['name'].rstrip('s')).replace('_',r'[_\s]')+r's?'
            explicit_question=re.search(r'\b(?:distinct|unique|different|deduplicated)\s+(?:qualifying\s+)?'+entity+r'\b',public['question'],re.I)
            once=re.search(r'\beach\s+'+entity+r'\s+(?:only\s+)?once\b',public['question'],re.I)
            joined_rows=re.search(r'\b(?:all\s+joined\s+(?:rows|records)|preserve\s+duplicate\s+(?:rows|records)|per\s+joined\s+row)\b',public['question'],re.I)
            hard=bool(distinct or explicit_question or once) and not joined_rows
            candidates.append({'table_id':tid,'primary_key':f['name'],'policy':'public_explicit_entity_grain_v2',
                'basis':'explicit_count_distinct' if distinct else 'explicit_unique_entity_question' if explicit_question or once else 'counted_identifier_without_unique_grain',
                'enforcement':'hard' if hard else 'advisory',
                'grain':'distinct_entities' if hard else 'joined_rows' if joined_rows else 'unspecified',
                'public_basis':('COUNT(DISTINCT '+key+')' if distinct else (explicit_question or once or joined_rows)[0] if explicit_question or once or joined_rows else 'COUNT('+key+')')[:160],
                'guidance':'A key or nonunique join alone does not establish a distinct population. Preserve explicitly requested row weighting; resolve unclear grain from public input, never reference answers.'})
    unique={}
    for v in candidates:
        key=(v['table_id'],v['primary_key'])
        if key not in unique or v['enforcement']=='hard':unique[key]=v
    return next(iter(unique.values())) if len(unique)==1 else {}


def grain_violations(runtime,grain,tree,refs):
    if not grain or grain.get('enforcement')!='hard':return []
    # Only enforce the simple physical-table scope where ownership and fanout are
    # known. Deduplicated CTEs, semijoins and ambiguous scopes stay advisory.
    tid=grain['table_id'];key=grain['primary_key']
    for scope in traverse_scope(tree):
        expression=scope.expression
        if not isinstance(expression,exp.Select):continue
        risk=False
        has_base=any(isinstance(s,exp.Table) and runtime.database_id+'.'+s.name==tid for s in scope.sources.values())
        if not has_base:continue
        for join in expression.args.get('joins',[]):
            on=join.args.get('on')
            if on is None:continue
            for eq in on.find_all(exp.EQ):
                left,right=refs.get(id(eq.left)),refs.get(id(eq.right))
                if not left or not right:continue
                for base,other in ((left,right),(right,left)):
                    if base[0]['id']!=tid or other[0]['id']==tid:continue
                    primary=[f['name'] for f in other[0]['fields'] if f.get('role')=='primary_key']
                    if primary!=[other[1]['name']]:risk=True
        if not risk:continue
        for aggregate in expression.find_all(exp.AggFunc):
            if aggregate.find_ancestor(exp.Select) is not expression:continue
            if isinstance(aggregate,exp.Count):
                cols=[refs.get(id(c)) for c in aggregate.find_all(exp.Column)]
                counts_key=any(v and v[0]['id']==tid and v[1]['name']==key for v in cols)
                if counts_key and not isinstance(aggregate.this,exp.Distinct):
                    return [{'code':'entity_grain_fanout','reason':'A nonunique joined table may repeat the counted entity. Count distinct qualifying identifiers and distinct total identifiers, or use EXISTS/deduplication before aggregation.',
                             'table_id':tid,'primary_key':key}]
            case=aggregate.find(exp.Case)
            indicator=(case is not None and all(isinstance(i.args.get('true'),exp.Literal) and i.args['true'].this in ('0','1')
                       for i in case.args.get('ifs',[])) and (case.args.get('default') is None or isinstance(case.args['default'],exp.Literal) and case.args['default'].this=='0'))
            if isinstance(aggregate,exp.Sum) and indicator:
                return [{'code':'entity_grain_fanout','reason':'SUM of per-row indicator after a nonunique join weights repeated entities. Preserve the public counted-identifier grain with conditional DISTINCT identifier counts or a semijoin.',
                         'table_id':tid,'primary_key':key}]
    return []
