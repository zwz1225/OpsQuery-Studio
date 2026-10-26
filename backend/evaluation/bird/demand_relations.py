"""Opt-in, bounded public demand coverage and separately authorized relation evidence.

No SQL execution, answers, case-ID branching, predicate enforcement or data repair.
Frozen key statistics are evidence only; current verified source binding is mandatory.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
import re

from .budgets import BirdFailure
from .intent import checked_tables, mentioned, sample_conditions, sample_values, text_input
from .evidence import ACCEPTED_VALIDATION_SHA
from .reviewed_relations import REVIEWED_RELATIONS

MAX_FIELDS = 20
MAX_ADDITIONS = 8
MAX_HOPS = 2
MAX_DEMANDS = 32


def policy(relation_output=False, categorical_population=False):
    return dict(policy_id='bird_public_categorical_population_context_v1' if categorical_population else
        'bird_public_relation_output_context_v1' if relation_output else 'bird_public_condition_relation_context_v1', development_candidate=True,
        formal_protocol_override=False, baseline_preserved=True, max_fields=MAX_FIELDS,
        max_intent_additions=MAX_ADDITIONS, max_hops=MAX_HOPS,
        authority='declared_fk_or_separately_reviewed_source_bound_candidate',
        samples_are_predicates=False, automatic_join_type=None, sql_rewriting=False,
        numeric_policy_changed=False, native_ex_unchanged=True)


def validate_options(enabled, *, diagnostic, coverage, intent, output, relation_output=False,
                     categorical_population=False):
    if (type(enabled) is not bool or type(relation_output) is not bool or type(categorical_population) is not bool or
            relation_output and (not enabled or not output) or
            categorical_population and (not enabled or relation_output or output) or
            enabled and (not diagnostic or not coverage or not intent or output and not relation_output)):
        raise BirdFailure('condition_relations_development_only_requires_coverage_intent_without_output_contract')


def _binding_reason(runtime, row):
    observed = runtime.identity.public()
    v = getattr(runtime, 'verification', None) or {}
    if observed != row['source_identity']: return 'source_identity_mismatch'
    if runtime.catalog.version != observed.get('catalog_version'): return 'catalog_version_mismatch'
    if runtime.domain.get('query_role') != row['query_role']: return 'query_role_mismatch'
    if not (v.get('live_target_verified') is True
            and v.get('role') == row['query_role']
            and v.get('accepted_validation_sha256') == ACCEPTED_VALIDATION_SHA
            and v.get('authorized_data_version') == observed['data_version']
            and v.get('authorized_catalog_version') == observed['catalog_version']):
        return 'current_verified_source_binding_missing'
    return None


def relation_candidates(runtime, reviewed=None):
    """Preserve unique-key groups and distinguish evidence from declared constraints."""
    require_open=getattr(runtime,'require_open',None)
    if callable(require_open):require_open()
    tables = checked_tables(runtime)
    result = []
    for row in REVIEWED_RELATIONS if reviewed is None else reviewed:
        if row['source_identity']['logical_database_id'] != runtime.database_id: continue
        item = deepcopy(row)
        item.update(eligible=False, limited_eligible=False, source_bound=False, database_constraint_created=False,
                    live_key_statistics_recomputed=False)
        pt, ct = row['parent_table'], row['child_table']
        pkeys, ckeys = row['parent_fields'], row['child_fields']
        fields = {tid: {f['name']: f for f in t['fields']} for tid, t in tables.items()}
        # Check authorization before consuming any sample or structural assertion.
        if (pt not in tables or ct not in tables or not pkeys or len(pkeys) != len(ckeys)
                or len(pkeys) != len(set(pkeys)) or len(ckeys) != len(set(ckeys))
                or any(k not in fields[pt] for k in pkeys) or any(k not in fields[ct] for k in ckeys)):
            reason = 'unauthorized_relation_endpoint'
        else:
            reason = _binding_reason(runtime, row)
            item['source_bound'] = reason is None
            if reason is None:
                types = [fields[pt][k]['type'].lower() for k in pkeys]
                compatible = types == row['key_types'] == [fields[ct][k]['type'].lower() for k in ckeys]
                reason = ('incompatible_key_types' if not compatible else
                    'whole_parent_key_not_unique' if pkeys not in row['unique_keys'] or not row['observed_parent_unique'] else
                    'incomplete_child_key_coverage' if row['orphan_rows'] or row['null_child_rows']
                        or row['child_nonnull_rows'] <= 0 or row['matching_child_rows'] != row['child_nonnull_rows'] else
                    'ownership_not_reviewed' if not row.get('ownership_basis') else None)
        item['decision_reason'] = reason or 'eligible_reviewed_candidate_not_declared_fk'
        item['eligible'] = reason is None
        item['limited_eligible'] = (reason == 'incomplete_child_key_coverage' and item['source_bound']
            and compatible and pkeys in row['unique_keys'] and row['observed_parent_unique']
            and bool(row.get('ownership_basis')) and bool(row.get('source_review_sha256'))
            and bool(row.get('sqlite_source_sha256'))
            and row['child_nonnull_rows'] > 0 and row['matching_child_rows'] > 0)
        result.append(item)
    return result


def demands(runtime, documents, public, selected_ids):
    """Small public grammar, with exact original spans and unresolved ownership.

    Payment-in-code and explicit currency requests are supported. Generic code
    occurrences, negation, examples, alternatives and role ambiguity stay advisory.
    """
    text_input(public)
    tables = checked_tables(runtime)
    if public['database_id'] != runtime.database_id: raise BirdFailure('demand_public_source_mismatch')
    authorized = {tid+'.'+f['name'] for tid,t in tables.items() for f in t['fields']}
    by_id = {d.doc_id:d for d in documents}
    if (len(by_id) != len(documents) or set(by_id) != authorized or
            any(d.database_id != runtime.database_id or d.doc_id != d.table_id+'.'+d.field_name
                or d.table_id not in tables for d in documents)):
        raise BirdFailure('demand_index_source_mismatch')
    if not selected_ids <= authorized: raise BirdFailure('demand_selection_source_mismatch')
    hints = sample_conditions(documents, public)
    records = []
    for hint in hints:
        records.append(dict(kind='sample_hint', field_id=hint['field_id'], value=hint['value'],
            authority='advisory_only', mandatory=False, selected=hint['field_id'] in selected_ids,
            decision_reason='already_selected' if hint['field_id'] in selected_ids else 'not_selected_by_prior_policy'))
    requirements = []
    # Output/evidence groups are observable even if all their fields are present:
    # later connectivity diagnostics can still identify missing keys.
    for source in ('question','evidence'):
        text=public[source]
        for tid, table in tables.items():
            for field in table['fields']:
                if not mentioned(field,text): continue
                match=re.search(r'(?<!\w)'+re.escape(field['name'])+r'(?!\w)',text,re.I)
                if match is None:
                    label=field.get('label','')
                    match=re.search(r'(?<!\w)'+re.escape(label)+r'(?!\w)',text,re.I) if label else None
                if match is None: continue
                fid=tid+'.'+field['name']
                requirements.append(dict(role='output_or_schema_reference' if source=='question' else 'evidence_field_group',
                    source=source, span=list(match.span()), text=match[0], candidate_field_ids=[fid],
                    ownership='public_metadata_reference', selected=fid in selected_ids, admission_requested=False))
    currency_documents=[d for d in documents if d.field_name.casefold()=='currency'
                        or d.field_label.casefold()=='currency']
    for source in ('question','evidence'):
        text=public[source]
        grammar=r'\b(?:(?:paid|paying|payments?|billed|charged|denominated)\s+in|currency\s*(?:is|=|:)?)\s*[\'"]?([A-Za-z]{3})\b'
        for match in re.finditer(grammar,text,re.I):
            code=match[1].upper()
            owners=[d.doc_id for d in currency_documents if code in sample_values(d)]
            # Conservative whole-input guard: do not convert negative/example or
            # disjunctive references into a newly asserted business predicate.
            uncertain=bool(re.search(r'\b(?:not|except|excluding|without|or|example|might|may|possibly)\b',text,re.I))
            raw_hint_ids={h['field_id'] for h in hints if h['value']==code}
            reason=('uncertain_public_condition' if uncertain else
                    'ambiguous_or_unmatched_currency_owner' if len(owners)!=1 else
                    'sample_owner_not_unique' if owners[0] not in raw_hint_ids else None)
            requirements.append(dict(role='payment_currency_condition',source=source,span=list(match.span()),
                text=match[0],value=code,candidate_field_ids=owners,ownership='unique_authorized_currency_sample_owner'
                if reason is None else 'unresolved', admission_requested=reason is None,
                decision_reason=reason, mandatory=False, authority='public_role_plus_profile_coverage_hint'))
    if len({r['value'] for r in requirements if r['role']=='payment_currency_condition'})>1:
        for r in requirements:
            if r['role']=='payment_currency_condition':
                r.update(admission_requested=False,decision_reason='multiple_public_currency_values',ownership='unresolved')
    return dict(requirements=requirements[:MAX_DEMANDS], requirements_complete=len(requirements)<=MAX_DEMANDS,
                omitted_requirement_count=max(0,len(requirements)-MAX_DEMANDS),
                sample_hint_decisions=records[:MAX_DEMANDS],sample_hints_complete=len(records)<=MAX_DEMANDS)


def _edges(runtime, candidates):
    edges=[]
    for r in runtime.catalog.relations:
        edges.append(dict(id=r['id'],parent_table=r['left_table'],child_table=r['right_table'],
            parent_fields=[r['left_field']],child_fields=[r['right_field']],
            authority='declared_foreign_key', declared_foreign_key=True))
    declared={(e['parent_table'],tuple(e['parent_fields']),e['child_table'],tuple(e['child_fields'])) for e in edges}
    edges.extend(r for r in candidates if r['eligible'] and
        (r['parent_table'],tuple(r['parent_fields']),r['child_table'],tuple(r['child_fields'])) not in declared)
    return edges


def _paths(anchors, target, edges):
    if anchors == {target}: return [[]]
    paths={}
    for start in sorted(anchors-{target}):
        queue=deque([(start,[],{start})])
        while queue:
            node,path,visited=queue.popleft()
            if len(path)>=MAX_HOPS: continue
            for edge in edges:
                ends={edge['parent_table'],edge['child_table']}
                if node not in ends: continue
                other=next(iter(ends-{node}),None)
                if other is None or other in visited: continue
                next_path=path+[edge]
                if other==target: paths[tuple(e['id'] for e in next_path)]=next_path
                else: queue.append((other,next_path,visited|{other}))
    if not paths:return []
    # Different valid role paths remain ambiguous, even if one is shorter.
    return list(paths.values())[:2]


def expand_context(runtime, documents, selected, public, *, intent_added_count=0, reviewed=None,
                   relation_output=False, categorical_population=False):
    """Atomically add a supported condition field and all needed join-key ends."""
    chosen=list(selected);ids={documents[i].doc_id for i,_ in chosen}
    record=demands(runtime,documents,public,ids)
    candidates=relation_candidates(runtime,reviewed)
    record.update(policy=policy(relation_output,categorical_population),relation_candidates=candidates,decisions=[],added_field_ids=[],
                  admitted_relations=[],unresolved_required_roles=[])
    by_id={d.doc_id:i for i,d in enumerate(documents)}
    edges=_edges(runtime,candidates)
    anchors={documents[i].table_id for i,_ in selected}
    if not record['requirements_complete']:
        record['unresolved_required_roles'].append('requirement_diagnostic_limit')
        return chosen,record
    used=0
    for requirement in record['requirements']:
        if requirement['role']!='payment_currency_condition':continue
        decision=dict(requirement,selected=False,added_field_ids=[],relation_ids=[])
        record['decisions'].append(decision)
        if not requirement['admission_requested']:
            record['unresolved_required_roles'].append(requirement['decision_reason']);continue
        fid=requirement['candidate_field_ids'][0];owner=fid.rsplit('.',1)[0]
        paths=_paths(anchors,owner,edges)
        if len(paths)!=1:
            decision['decision_reason']='ambiguous_relation_paths' if paths else 'no_authorized_reviewed_path_within_hop_limit'
        else:
            path=paths[0];required=[fid]
            for edge in path:
                for side in ('parent','child'):
                    required.extend(edge[side+'_table']+'.'+k for k in edge[side+'_fields'])
            missing=list(dict.fromkeys(f for f in required if f not in ids))
            reason=('context_field_cap' if len(chosen)+len(missing)>MAX_FIELDS else
                    'intent_addition_cap' if intent_added_count+used+len(missing)>MAX_ADDITIONS else None)
            decision['decision_reason']=reason or 'condition_and_keys_admitted_atomically'
            if reason is None:
                for field_id in missing: chosen.append((by_id[field_id],0.0));ids.add(field_id)
                used+=len(missing)
                decision.update(selected=True,added_field_ids=missing,relation_ids=[e['id'] for e in path])
                record['added_field_ids'].extend(missing)
                for edge in path:
                    if edge['id'] not in {e['id'] for e in record['admitted_relations']}:
                        record['admitted_relations'].append(edge)
        if not decision['selected']:record['unresolved_required_roles'].append(decision['decision_reason'])
    if categorical_population:
        used += _admit_categorical_population(runtime, documents, chosen, ids, public, record,
                                               edges, anchors, intent_added_count+used)
    if relation_output:
        _admit_public_output_relation(runtime, documents, chosen, ids, public, record,
                                      candidates, intent_added_count+used)
    # Retain old gate outcomes even when the new policy resolves them. These are
    # diagnostic claims about the preceding selected context, not threshold scores.
    for hint in record['sample_hint_decisions']:
        hint['selected_after_context']=hint['field_id'] in ids
    selected_tables={documents[i].table_id for i,_ in chosen}
    record['missing_relation_key_groups']=[]
    for row in candidates:
        if {row['parent_table'],row['child_table']}<=selected_tables:
            missing=[row[s+'_table']+'.'+k for s in ('parent','child') for k in row[s+'_fields']
                     if row[s+'_table']+'.'+k not in ids]
            if missing:record['missing_relation_key_groups'].append(dict(relation_id=row['id'],
                missing_field_ids=missing,reason=row['decision_reason'],automatic_completion=False))
    return chosen,record


def _admit_categorical_population(runtime, documents, chosen, ids, public, record,
                                  edges, anchors, already_used):
    """Close a public entity-category condition through one verified relation.

    The unique profile sample proposes a field owner. It never creates a WHERE
    clause, prescribes JOIN semantics, or overrides the relation/source guards.
    """
    question=public['question']
    hints=[]
    tables=checked_tables(runtime)
    for hint in record['sample_hint_decisions']:
        field_id=hint['field_id'];owner=field_id.rsplit('.',1)[0]
        if owner not in tables or owner in anchors or hint['selected']:continue
        field_name=field_id.rsplit('.',1)[1]
        field=next((f for f in tables[owner]['fields'] if f['name']==field_name),None)
        if field is None or not re.search(r'\b(?:segment|category|class|type)\b',
                (field['name']+' '+field.get('label','')).replace('_',' '),re.I):continue
        table_name=tables[owner]['name']
        entity_forms={table_name,table_name[:-1] if table_name.endswith('s') else table_name}
        pattern=r'(?<!\w)'+re.escape(hint['value'])+r'\s+(?:'+ '|'.join(re.escape(v) for v in sorted(entity_forms))+r')(?!\w)'
        match=re.search(pattern,question,re.I)
        if match:hints.append((hint,match))
    if not hints:return 0
    uncertain=bool(re.search(r'\b(?:not|without|except|excluding|or|either|example|possibly|maybe)\b',question,re.I))
    by_id={d.doc_id:i for i,d in enumerate(documents)}
    used=0
    for hint,match in hints:
        fid=hint['field_id'];owner=fid.rsplit('.',1)[0]
        decision=dict(role='public_categorical_population_condition',source='question',
            span=list(match.span()),text=match[0],value=hint['value'],candidate_field_ids=[fid],
            authority='public_entity_role_plus_unique_authorized_profile_owner',mandatory=False,
            selected=False,added_field_ids=[],relation_ids=[])
        record['decisions'].append(decision)
        if uncertain or len(hints)!=1:
            decision['decision_reason']='uncertain_or_ambiguous_public_population';continue
        paths=_paths(anchors,owner,edges)
        if len(paths)!=1:
            decision['decision_reason']='ambiguous_relation_paths' if paths else 'no_authorized_reviewed_path_within_hop_limit'
        else:
            path=paths[0];required=[fid]
            for edge in path:
                for side in ('parent','child'):
                    required.extend(edge[side+'_table']+'.'+key for key in edge[side+'_fields'])
            missing=list(dict.fromkeys(field_id for field_id in required if field_id not in ids))
            reason=('unauthorized_relation_endpoint' if any(field_id not in by_id for field_id in missing) else
                    'context_field_cap' if len(chosen)+len(missing)>MAX_FIELDS else
                    'intent_addition_cap' if already_used+used+len(missing)>MAX_ADDITIONS else None)
            decision['decision_reason']=reason or 'public_population_and_keys_admitted_atomically'
            if reason is None:
                for field_id in missing:chosen.append((by_id[field_id],0.0));ids.add(field_id)
                used+=len(missing)
                decision.update(selected=True,added_field_ids=missing,relation_ids=[edge['id'] for edge in path])
                record['added_field_ids'].extend(missing)
                for edge in path:
                    if edge['id'] not in {row['id'] for row in record['admitted_relations']}:
                        record['admitted_relations'].append(edge)
        if not decision['selected']:record['unresolved_required_roles'].append(decision['decision_reason'])
    return used


def _admit_public_output_relation(runtime, documents, chosen, ids, public, record, candidates, used):
    """Close a uniquely supported output/filter path within the existing 20 slots."""
    from .output_contract import build_contract
    tables=checked_tables(runtime)
    graph={'database':runtime.database_id,'source_identity':runtime.identity.public(),
           'fields':[dict(id=tid+'.'+f['name'],table_id=tid,name=f['name'],
                          label=f.get('label',''),description=f.get('description',''))
                     for tid,t in tables.items() for f in t['fields']]}
    contract=build_contract(public,graph)
    groups=[v for v in contract['items'] if v['kind']=='field_group' and v['binding_complete']
            and len(v['field_ids'])>=2]
    filters=[dict(field_id=h['field_id'],value=h['value'],authority='selected_profile_sample')
             for h in record['sample_hint_decisions'] if h['selected']
             and h['field_id'] in ids and h['value'].casefold() in public['question'].casefold()]
    for match in re.finditer(r'([^;\n]{1,80}?)\s+refers?\s+to\s+(?:the\s+)?([A-Za-z_]\w*)',public['evidence'],re.I):
        token=match[1].strip();name=match[2]
        if not re.fullmatch(r'[A-Za-z][A-Za-z ]{1,40}',token) or not re.search(
                r'(?<!\w)'+re.escape(token)+r'(?!\w)',public['question'],re.I):continue
        matches=[fid for fid in ids if documents[next(i for i,d in enumerate(documents) if d.doc_id==fid)].field_name.casefold()==name.casefold()]
        if len(matches)==1 and not any(matches[0] in g['field_ids'] for g in groups):
            filters.append(dict(field_id=matches[0],value=token,authority='explicit_public_evidence',
                                evidence_span=[match.start(),match.end()]))
    filters=list({(v['field_id'],v['value'].casefold()):v for v in filters}.values())
    decision=dict(role='public_output_relation',selected=False,output_field_ids=[],
                  filter_field_ids=[],added_field_ids=[],evicted_fields=[],relation_ids=[])
    record['decisions'].append(decision)
    if (len(groups)!=1 or not contract['parse_complete'] or len(filters)!=1 or
            re.search(r'\b(?:not|without|except|excluding)\b',public['question'],re.I)):
        decision['decision_reason']='unresolved_output_group_or_filter';return
    outputs=groups[0]['field_ids'];filter_id=filters[0]['field_id']
    output_tables={v.rsplit('.',1)[0] for v in outputs};filter_table=filter_id.rsplit('.',1)[0]
    decision.update(output_field_ids=outputs,filter_field_ids=[filter_id],
                    public_output_evidence=groups[0]['evidence'],public_filter_evidence=filters[0])
    if len(output_tables)!=1 or filter_table in output_tables or not set(outputs)<=(ids):
        decision['decision_reason']='ambiguous_or_unselected_output_owner';return
    candidates_here=[r for r in candidates if r['limited_eligible'] and
                     {r['parent_table'],r['child_table']}==output_tables|{filter_table}]
    if len(candidates_here)!=1:
        decision['decision_reason']='ambiguous_or_unreviewed_relation';return
    row=candidates_here[0]
    required=[row[s+'_table']+'.'+k for s in ('parent','child') for k in row[s+'_fields']]
    missing=list(dict.fromkeys(v for v in required if v not in ids))
    by_id={d.doc_id:i for i,d in enumerate(documents)}
    if any(v not in by_id for v in missing):
        decision['decision_reason']='unauthorized_relation_endpoint';return
    if used+len(missing)>MAX_ADDITIONS:
        decision['decision_reason']='intent_addition_cap';return
    # Preserve every explicit public field mention as well as the output and filter.
    protected=set(outputs+[filter_id]+required)
    protected.update(v for r in record['requirements'] for v in r['candidate_field_ids'])
    need=max(0,len(chosen)+len(missing)-MAX_FIELDS)
    removable=[(position,index,score) for position,(index,score) in enumerate(chosen)
               if documents[index].doc_id not in protected and score>0]
    removable.sort(key=lambda v:(v[2],-v[0],documents[v[1]].doc_id))
    if len(removable)<need:
        decision['decision_reason']='context_field_cap';return
    evict={position for position,_,_ in removable[:need]}
    decision['evicted_fields']=[dict(field_id=documents[index].doc_id,score=score,
                                    reason='lower_ranked_nonpublic_field_for_reviewed_keys')
                                for position,index,score in removable[:need]]
    chosen[:]=[pair for position,pair in enumerate(chosen) if position not in evict]
    ids.difference_update(v['field_id'] for v in decision['evicted_fields'])
    for fid in missing:chosen.append((by_id[fid],0.0));ids.add(fid)
    record['added_field_ids'].extend(missing)
    record['admitted_relations'].append(row)
    decision.update(selected=True,added_field_ids=missing,relation_ids=[row['id']],
                    decision_reason='reviewed_incomplete_candidate_keys_admitted')


def annotate_graph(runtime, graph, context):
    """Append only admitted candidate edges; declared FK builder stays unchanged."""
    graph=deepcopy(graph)
    existing={(r['left_table'],r['left_field'],r['right_table'],r['right_field']) for r in graph['joins']}
    for row in context['admitted_relations']:
        for left,right in zip(row['parent_fields'],row['child_fields']):
            key=(row['parent_table'],left,row['child_table'],right)
            if key in existing:continue
            graph['joins'].append(dict(id=row['id']+':'+left,left_table=row['parent_table'],left_field=left,
                right_table=row['child_table'],right_field=right,
                left_table_name=row['parent_table'].split('.')[-1],right_table_name=row['child_table'].split('.')[-1],
                relation_type='foreign_key' if row['declared_foreign_key'] else 'reviewed_candidate',
                authority=row['authority'],declared_foreign_key=row['declared_foreign_key'],
                key_group=dict(parent_fields=row['parent_fields'],child_fields=row['child_fields']),
                join_type=None,mandatory=False,
                description=('Source-reviewed incomplete equality candidate; '+str(row['orphan_rows'])+
                    ' child orphan rows, not a PostgreSQL FK. Choose join/population semantics from public input.')
                    if row.get('limited_eligible') else
                    'Candidate equality from reviewed source-bound key coverage; not a declared FK. Choose join/population semantics from public input.'
                    if not row['declared_foreign_key'] else 'Authorized declared foreign key'))
            existing.add(key)
    graph['condition_relation_context']=dict(policy=context['policy'],
        admitted_public_conditions=[dict(field_id=d['candidate_field_ids'][0],value=d['value'],
            role=d['role'],public_source=d['source'],public_span=d['span'],
            authority=d.get('authority','public_payment_role_plus_unique_authorized_profile_owner'),mandatory=False)
            for d in context['decisions'] if d['selected'] and d['role'] in
                ('payment_currency_condition','public_categorical_population_condition')],
        public_output_relation=[dict(output_field_ids=d['output_field_ids'],filter_field_ids=d['filter_field_ids'],
            filter_evidence=d['public_filter_evidence'],orphan_rows=next(
                r['orphan_rows'] for r in context['admitted_relations'] if r['id'] in d['relation_ids']),
            authority='frozen_source_reviewed_incomplete_candidate',mandatory=False)
            for d in context['decisions'] if d['selected'] and d['role']=='public_output_relation'],
        unresolved_required_roles=context['unresolved_required_roles'],
        guidance='Cover the public condition using its owning field. Profile matches alone never mandate predicates. Candidate equalities are alternatives, not database constraints; no join type is prescribed. Clarify unresolved ownership/connectivity instead of silently discarding a condition.')
    from scripts.m2_b_common import digest_json
    graph['graph_version']=digest_json({k:v for k,v in graph.items() if k!='graph_version'})[:12]
    return graph
