"""Opt-in development candidate grounded only in public input and authorized metadata.

No scorer imports, case-ID rules, SQL rewriting or result-score normalization.
"""
from __future__ import annotations

import hashlib
import json
import re

from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope

from evaluation.bird_protocol import validate_agent_input
from .budgets import BirdFailure
from .coverage import terms
from .repair import parsed, quote

POLICY = 'bird_public_intent_candidate_v4'
MAX_ADDITIONS = 8
MAX_FIELDS = 20
MAX_PROBES = 4
QUERY_SEMANTICS_POLICY = 'bird_public_query_semantics_prompt_v2'

QUERY_SEMANTICS_GUIDANCE = [
    'Plan grain, measure, aggregate, then rank. For a population\'s peak month or other period/category of an additive measure, aggregate qualifying rows at that grain using SUM before ranking, even without the word total. Never replace a group total with the highest source row. Preserve population/date filters. Respect explicit averages, rates and formulas; do not sum nonadditive measures. For individual-record extrema, rank records without grouping.',
    'Project only requested attributes in question order, including follow-up requests. Ranking/filter/join helpers are not outputs unless requested. Preserve field ownership, explicit exclusions, and required NULLS LAST.'
]


def query_semantics_policy():
    return {'policy_id': QUERY_SEMANTICS_POLICY, 'development_candidate': True,
            'scope': 'advisory_prompt_only', 'hard_rejection': False,
            'sql_rewriting': False, 'scoring_policy_changed': False,
            'guidance_sha256': hashlib.sha256('\n'.join(QUERY_SEMANTICS_GUIDANCE).encode('utf-8')).hexdigest()}


def policy():
    return {'policy_id': POLICY, 'development_candidate': True, 'formal_protocol_override': False,
            'input_source': 'original_question_official_evidence_authorized_catalog_and_profiles',
            'baseline_preserved': True, 'max_fields': MAX_FIELDS, 'max_added_fields': MAX_ADDITIONS,
            'coverage_scope': 'authorized_catalog_exact_evidence_roles_groups_or_sample_matches',
            'max_related_hops': 2, 'join_source': 'declared_foreign_keys_only',
            'canonical_lookup_max_pairs': MAX_PROBES, 'canonical_lookup_sql_tool_calls': 1,
            'lookup_consumes_existing_sql_budget': True, 'numeric_policy': 'floating_count_ratio_order_advisory_v3',
            'unit_policy':'public_percentage_units_precision_v2',
            'output_group_policy':'participant_action_target_pair_v1',
            'predicate_policy':'public_condition_roles_conflicts_v3',
            'profile_match_authority':'retrieval_hint_only_never_mandatory_predicate',
            'relation_policy':'authorized_alternatives_with_role_metadata_v1',
            'grain_policy':'public_explicit_entity_grain_v2',
            'native_ex_unchanged': True}


def checked_tables(runtime):
    db = runtime.database_id
    tables = {t['id']: t for t in runtime.catalog.tables}
    if any(t.get('database') != db or tid != db + '.' + t['name']
           or t.get('physical_schema', 'public') != 'public' for tid, t in tables.items()):
        raise BirdFailure('intent_catalog_source_mismatch')
    for r in runtime.catalog.relations:
        if any(r.get(s + '_table') not in tables or not any(f['name'] == r.get(s + '_field')
               for f in tables[r[s + '_table']]['fields']) for s in ('left', 'right')):
            raise BirdFailure('intent_relation_source_mismatch')
    return tables


def text_input(public):
    validate_agent_input(public)
    return public['question'] + '\n' + public['evidence']


def normalized(text):
    return re.sub(r'[^a-z0-9]', '', text.casefold())


def mentioned(field, text):
    """Identifier/label boundary matching; no substring matches inside other words."""
    name = field['name']
    if re.search(r'(?<![\w])' + re.escape(name) + r'(?![\w])', text, re.I): return True
    spaced = name.replace('_', ' ')
    if spaced != name and re.search(r'(?<!\w)' + re.escape(spaced) + r'(?!\w)', text, re.I): return True
    label = field.get('label', '')
    # Multiword labels are useful; bare generic words are too ambiguous to expand tables.
    return len(label.split()) >= 2 and bool(re.search(r'(?<!\w)' + re.escape(label) + r'(?!\w)', text, re.I))


def name_groups(table):
    fields = table['fields']; groups = []
    for f in fields:
        label = f.get('label', '').lower()
        if 'first name' not in label and not re.search(r'first_?name', f['name'], re.I): continue
        last = [g for g in fields if (g.get('label', '').lower() == label.replace('first name', 'last name')
                or g['name'].lower() == re.sub('first', 'last', f['name'].lower())) and g['name'] != f['name']]
        if not last: continue
        roots = [re.sub(r'\d+$', '', g['name']) for g in (f, last[0])]
        group = [g['name'] for g in fields if re.sub(r'\d+$', '', g['name']) in roots]
        groups.append(sorted(set(group), key=lambda n: (re.search(r'\d+$', n).group() if re.search(r'\d+$', n) else '', roots.index(re.sub(r'\d+$', '', n)))))
    return [list(g) for g in dict.fromkeys(tuple(g) for g in groups)]


def sample_values(document):
    result = []
    try: truncations = json.loads(document.profile).get('sample_truncated', []) if document.profile else []
    except (ValueError, TypeError, AttributeError): return []
    for index, sample in enumerate(document.samples):
        if index < len(truncations) and truncations[index]: continue
        if isinstance(sample, list) and len(sample) == 2 and sample[0] == 'text' and isinstance(sample[1], str):
            result.append(sample[1])
    return result


def sample_conditions(documents, public):
    # Samples can suggest coverage, never mandate a predicate. Only unique uppercase
    # category codes are eligible: names, formula numbers and duplicated codes are not.
    tokens = {w.casefold() for w in re.findall(r'[\w]+', text_input(public))}
    tokens |= {w[:-1] for w in tokens if w.endswith('s') and len(w) > 2}
    result = [];owners={}
    for d in documents:
        for value in sample_values(d):owners.setdefault(value.casefold(),set()).add(d.doc_id)
    for d in documents:
        for value in sample_values(d):
            role_text=d.field_name+' '+d.field_label
            categorical=bool(re.search(r'\b(?:segment|category|status|type|currency|class)\b',role_text.replace('_',' '),re.I))
            identifier=bool(re.search(r'(?:^|[_\s])(?:id|name|date)(?:$|[_\s])',role_text,re.I)) or d.field_role=='primary_key'
            if categorical and not identifier and re.fullmatch(r'[A-Z]{2,12}',value) and len(owners[value.casefold()])==1 and value.casefold() in tokens:
                result.append({'field_id': d.doc_id, 'table_id': d.table_id, 'field': d.field_name,
                               'value': value, 'basis': 'unique_category_sample_code_matches_public_token',
                               'authority':'coverage_hint_only','mandatory':False})
    return result


def public_condition_evidence(public):
    """Bounded public bindings with roles; incompatible values never imply AND.

    This small grammar does not resolve arbitrary English or repair evidence.
    Different numerator/denominator values are legitimate separate scopes.
    """
    text_input(public);text=public['evidence']
    result={'policy':'public_condition_roles_conflicts_v3','conditions':[],'conflicts':[],
            'guidance':'Keep numerator, denominator and population roles separate. Conflicting bindings are advisory; do not require their conjunction or guess which is correct.'}
    if re.search(r'\b(?:or|not|except|example|e\.g|might|may|possibly|either)\b',text,re.I):return result
    literal=r"'((?:[^'\r\n]|''){1,64})'"
    pattern=r'(?<![\w.])(?:(?P<table>[A-Za-z_]\w*)\.)?(?P<field>[A-Za-z_]\w*)\s*=\s*'+literal
    bindings=[]
    for m in list(re.finditer(pattern,text))[:32]:
        # Parse only open function frames preceding this public equality. Quote
        # contents cannot supply parentheses/commas or fake scope markers.
        prefix=re.sub(r"'(?:[^']|'')*'",lambda x:' '*len(x[0]),text[:m.start()])
        stack=[]
        for token in re.finditer(r'([A-Za-z_]\w*)\s*\(|([(),])',prefix):
            if token[1]:stack.append([token[1].upper(),0])
            elif token[2]=='(':stack.append(['',0])
            elif token[2]==')' and stack:stack.pop()
            elif token[2]==',' and stack:stack[-1][1]+=1
        division=next((v for v in reversed(stack) if v[0]=='DIVIDE'),None)
        aggregate=any(v[0] in ('SUM','COUNT','AVG','MIN','MAX') for v in stack)
        if aggregate:role=('numerator_condition' if division[1]==0 else 'denominator_condition') if division else 'aggregate_condition'
        else:
            clause=prefix.rsplit(';',1)[-1]
            role='population_filter' if re.search(r'\b(?:where|having|when)\b',clause,re.I) else 'definition'
        bindings.append({'table':m['table'],'field':m['field'],'value':m[3].replace("''", "'"),
                         'basis':'explicit_evidence_equality','role':role,'evidence_span':[m.start(),m.end()]})
    groups={}
    for item in bindings:groups.setdefault(((item['table'] or '').casefold(),item['field'].casefold()),[]).append(item)
    conflicting=set()
    for key,items in groups.items():
        values={v['value'].casefold() for v in items}
        if len(values)<2:continue
        # Separate numerator and denominator predicates are not contradictory.
        # Repeated differing values in one role, or a definition inconsistent
        # with a formula, lack authority for a mandatory conjunction.
        roles={v['role'] for v in items}
        separate=roles<={'numerator_condition','denominator_condition'} and len(roles)==2 and all(
            len({v['value'].casefold() for v in items if v['role']==role})==1 for role in roles)
        if separate:continue
        conflicting.add(key)
        result['conflicts'].append({'table':items[0]['table'],'field':items[0]['field'],
            'values':list(dict.fromkeys(v['value'] for v in items)),
            'roles':list(dict.fromkeys(v['role'] for v in items)),
            'evidence_spans':[v['evidence_span'] for v in items],
            'kind':'incompatible_or_ambiguous_same_field_bindings','resolution':'advisory_no_mandatory_conjunction'})
    result['conditions']=[v for v in bindings if ((v['table'] or '').casefold(),v['field'].casefold()) not in conflicting]
    return result


def public_equalities(public):
    return public_condition_evidence(public)['conditions']


def bound_public_conditions(runtime,public,selected_ids,lookup):
    tables=checked_tables(runtime);result=[]
    for equality in public_equalities(public):
        owners=[(tid,f) for tid,t in tables.items() for f in t['fields'] if f['name'].casefold()==equality['field'].casefold()
                and (not equality['table'] or t['name'].casefold()==equality['table'].casefold())]
        if len(owners)!=1:continue
        tid,f=owners[0];fid=tid+'.'+f['name']
        if fid not in selected_ids:continue
        value=equality['value']
        canonical=[m for m in lookup['matches'] if m['table_id']==tid and m['field']==f['name'] and m['requested']==value
                   and m['resolution']=='unique_database_lower_match']
        if canonical:value=canonical[0]['values'][0]
        item={'table_id':tid,'field_id':fid,'field':f['name'],'value':value,'basis':equality['basis'],
              'authority':'unique_public_field_value_binding','mandatory':True,'evidence_role':equality['role']}
        previous=next((v for v in result if (v['table_id'],v['field'],v['value'])==(tid,f['name'],value)),None)
        if previous is None:result.append(item)
        elif equality['role']!=previous['evidence_role']:
            previous['evidence_roles']=list(dict.fromkeys(previous.get('evidence_roles',[previous['evidence_role']])+[equality['role']]))
    return result[:8]


def expand_fields(runtime, documents, selected, public, *, diagnose_rejections=False):
    """Retain baseline, append bounded justified fields; join keys remain separately marked."""
    text = text_input(public); tables = checked_tables(runtime)
    if public['database_id'] != runtime.database_id: raise BirdFailure('intent_public_source_mismatch')
    by_id = {d.doc_id: (i, d) for i, d in enumerate(documents)}
    authorized = {tid + '.' + f['name'] for tid, t in tables.items() for f in t['fields']}
    if set(by_id) != authorized or any(d.database_id != runtime.database_id or d.doc_id != d.table_id + '.' + d.field_name
                                      for d in documents): raise BirdFailure('intent_index_source_mismatch')
    chosen = list(selected); ids = {documents[i].doc_id for i, _ in selected}
    anchors = {documents[i].table_id for i, _ in selected}
    # Permit at most two real FK edges from a baseline anchor. An empty baseline
    # may seed exact public metadata references, not arbitrary high-scoring tables.
    reachable = set(anchors)
    for _ in range(2):
        current = set(reachable)
        for r in runtime.catalog.relations:
            if r['left_table'] in current or r['right_table'] in current:
                reachable.update((r['left_table'], r['right_table']))
    proposals = {}; conditions = sample_conditions(documents, public)
    named_tables = {tid for tid,t in tables.items() if terms(t['name']) & terms(text)}
    mentions = {tid:[f for f in t['fields'] if mentioned(f,text)] for tid,t in tables.items()}
    owners = {}
    for tid,t in tables.items():
        for f in t['fields']:owners.setdefault(f['name'],set()).add(tid)
    seeded = {tid for tid,fields in mentions.items() for f in fields
              if len(owners[f['name']]) == 1 and (len(f['name'])>3 or '_' in f['name'])}
    def propose(tid, name, reason, priority):
        fid = tid + '.' + name
        if fid not in ids and fid in by_id and (fid not in proposals or priority > proposals[fid]['priority']):
            proposals[fid] = {'field_id': fid, 'reason': reason, 'priority': priority,
                              'table_id': tid, 'basis': 'public_input_and_authorized_metadata'}
    for tid, table in tables.items():
        if anchors and tid not in reachable: continue
        for f in mentions[tid]:
            shared=len(owners[f['name']])>1
            if shared:
                # Bare ID/type/amount must not seed every same-named field. Prefer
                # the entity explicitly named in public text or a distinctive field
                # already naming its table. FK reachability alone is insufficient.
                family=terms(f['name'].replace('_id',''))
                owner_matches=bool(family & terms(table['name'])) if f['name'].endswith('_id') else False
                if tid not in named_tables and tid not in seeded and not owner_matches: continue
            propose(tid, f['name'], 'explicit_public_identifier_or_label', 4)
        for group in name_groups(table):
            if 'full name' in text.lower() and (any(tid + '.' + n in ids for n in group)
                    or any(mentioned(f, text) for f in table['fields'] if f['name'] in group)):
                for name in group: propose(tid, name, 'complete_authorized_name_group', 5)
    hint_decisions=[]
    for item in conditions:
        tid=item['table_id']
        condition_scope=(tid in anchors or tid in seeded or tid in named_tables)
        hint_decisions.append(dict(item,condition_scope=condition_scope,
            reachable=tid in reachable or not anchors,
            gate_reasons=([] if condition_scope else ['condition_owner_outside_anchor_seed_or_named_scope'])+
                ([] if tid in reachable or not anchors else ['no_declared_fk_path_within_two_hops'])))
        if condition_scope and (tid in reachable or not anchors):
            propose(item['table_id'], item['field'], 'public_token_matches_stored_profile_value', 4)
    for fid, item in sorted(proposals.items(), key=lambda kv: (-kv[1]['priority'], kv[0])):
        admitted = len(chosen) < MAX_FIELDS and len(chosen) - len(selected) < MAX_ADDITIONS
        item['selected'] = admitted
        item['selection_reason'] = item['reason'] if admitted else 'intent_field_cap'
        if admitted:
            i, _ = by_id[fid]; chosen.append((i, 0.0)); ids.add(fid)
    result={'policy': policy(), 'baseline_field_ids': [documents[i].doc_id for i, _ in selected],
                    'added_field_ids': [documents[i].doc_id for i, _ in chosen[len(selected):]],
                    'decisions': list(proposals.values()),
                    'sample_condition_candidates': [c for c in conditions if c['field_id'] in ids]}
    if diagnose_rejections:
        result['sample_condition_decisions']=[dict(c,selected=c['field_id'] in ids) for c in hint_decisions]
    return chosen,result


def literal_requests(public, tables, selected_ids):
    """At most four text equality probes, drawn from explicit assignments or quoted names."""
    text = text_input(public); out = []
    assignments = public_equalities(public)
    quoted = re.findall(r"(?<!\w)'((?:[^'\r\n]|(?<=\w)'(?=\w)){2,64})'(?!\w)", public['question'])
    for tid, t in sorted(tables.items()):
        for f in t['fields']:
            if tid + '.' + f['name'] not in selected_ids or f['type'] not in ('text', 'character varying'): continue
            owners=lambda name:[(otid,of['name']) for otid,ot in tables.items() for of in ot['fields'] if of['name'].casefold()==name.casefold()]
            values = [a['value'] for a in assignments if a['field'].casefold() == f['name'].casefold()
                      and (a['table'] and a['table'].casefold()==t['name'].casefold() or not a['table'] and len(owners(a['field']))==1)]
            if ('name' in f['name'].lower() or 'name' in f.get('label', '').lower()) and mentioned(f, text):
                # Scope quoted entity names to their explicit evidence mapping.
                for value in quoted:
                    pattern="'"+re.escape(value)+r"'\s+is\s+(?:an?\s+)?([A-Za-z_][\w ]{0,40}?)(?:[;,.]|$)"
                    mapping=re.search(pattern,public['evidence'],re.I)
                    if mapping:
                        if normalized(mapping[1]) in (normalized(f['name']),normalized(f.get('label',''))):values.append(value)
                    else:
                        candidates=[(otid,of['name']) for otid,ot in tables.items() for of in ot['fields']
                                    if otid+'.'+of['name'] in selected_ids and 'name' in of['name'].lower() and mentioned(of,text)]
                        if len(candidates)==1:values.append(value)
            for value in values:
                item = {'table_id': tid, 'table': t['name'], 'field': f['name'], 'requested': value}
                if item not in out: out.append(item)
    return out[:MAX_PROBES]


def canonical_lookup(runtime, public, selected_ids, budget, *, progress=None):
    tables = checked_tables(runtime); text_input(public)
    if public['database_id'] != runtime.database_id: raise BirdFailure('intent_public_source_mismatch')
    probes = literal_requests(public, tables, set(selected_ids))
    record = progress if progress is not None else {}
    record.update({'policy': POLICY, 'source_identity': runtime.identity.public(), 'probe_count': len(probes),
                   'sql_tool_calls': 0, 'executed': False, 'matches': [], 'max_values_per_probe': 3})
    if not probes: return record
    # Native executor validates this generated read-only SQL and uses its existing
    # verified transaction, role, timeout, payload cap and clean-pool lifecycle.
    pieces = []
    for i, probe in enumerate(probes):
        literal = exp.Literal.string(probe['requested']).sql(dialect='postgres')
        column = quote(probe['field'])
        pieces.append('(SELECT ' + str(i) + ' AS probe_id,' + column + ' AS canonical_value FROM "public".'
                      + quote(probe['table']) + ' WHERE LOWER(' + column + ') = LOWER(' + literal + ')'
                      + ' GROUP BY ' + column + ' ORDER BY ' + column + ' ASC NULLS LAST LIMIT 3)')
    sql = ' UNION ALL '.join(pieces)
    record['sql']=sql
    record['sql_sha256'] = hashlib.sha256(sql.encode()).hexdigest()
    budget.sql_call(); record['sql_tool_calls'] = 1
    result = runtime.execute_native(sql, budget)
    record['executed'] = True
    for i, probe in enumerate(probes):
        values = sorted({r[1] for r in result.rows if r[0] == i})
        if any(not isinstance(v, str) or len(v) > 64 for v in values): raise BirdFailure('canonical_value_limit')
        record['matches'].append({**probe, 'values': values,
                                  'resolution': 'unique_database_lower_match' if len(values) == 1 else 'not_found' if not values else 'ambiguous'})
    return record


def build_contract(runtime, public, graph, selection, lookup, *, semantic_planning=False):
    if type(semantic_planning) is not bool:
        raise BirdFailure('query_semantic_planning_flag_invalid')
    text = text_input(public); tables = checked_tables(runtime)
    from .units_output import unit_contract,participant_output_contract
    units=unit_contract(public)
    selected = {f['id'] for f in graph['fields']}
    groups = []
    for tid, table in tables.items():
        for names in name_groups(table):
            if 'full name' in text.lower() and all(tid + '.' + n in selected for n in names):
                groups.append({'table_id': tid, 'fields': names,
                               'output_group': len(names) > 2 and any(tid + '.' + n in selection['baseline_field_ids'] for n in names)})
    ordinal = re.search(r'\b([1-9][0-9]{0,3})(?:st|nd|rd|th)\s+(highest|lowest|largest|smallest)\b', text, re.I)
    top = re.search(r'\btop\s+([1-9][0-9]{0,3})\b', public['question'], re.I)
    percentage = bool(re.search(r'\b(?:percent|percentage)\b', public['question'], re.I))
    quantity_difference = bool(re.search(r'^\s*(?:is it true|are there)\b', public['question'], re.I)
                               and re.search(r'\bhow (?:many|much) more\b',public['question'],re.I)
                               and '=' in public['evidence'] and re.search(r'\s-\s',public['evidence']))
    output_phrase=re.split(r'\b(?:that|which|where|for)\b',public['question'],maxsplit=1,flags=re.I)[0]
    identifier_candidates=[]
    explicit_output_attribute=bool(re.search(r'\b(?:names?|addresses|emails?|dates?|amounts?|balances?|columns|fields|attributes|details)\b',output_phrase,re.I))
    if re.match(r'\s*list\s+(?:all\b|the\b)',output_phrase,re.I) and not explicit_output_attribute:
        for tid,table in tables.items():
            keys=[f for f in table['fields'] if f.get('role')=='primary_key']
            if len(keys)!=1 or tid+'.'+keys[0]['name'] not in selected:continue
            entity_words=terms(keys[0].get('label','').replace('identifier','').replace(' id',''))
            explicit_attributes=any(f.get('role')!='primary_key' and mentioned(f,output_phrase) for f in table['fields'])
            if entity_words and entity_words<=terms(output_phrase) and not explicit_attributes:
                identifier_candidates.append({'table_id':tid,'field':keys[0]['name']})
    from .relationships import grain_contract
    result = {'policy': policy(), 'name_groups': groups,
            'public_evidence':public_condition_evidence(public),
            'required_profile_conditions':bound_public_conditions(runtime,public,selected,lookup),
            'profile_coverage_hints':selection['sample_condition_candidates'],
            'entity_grain':grain_contract(runtime,public),
            'relation_role_context':graph.get('relation_role_context',{}),
            'output_units':units,
            'participant_output':participant_output_contract(public,graph,tables,runtime.catalog.relations),
            'ordinal_rank': int(ordinal[1]) if ordinal else None,
            'ordinal_descending': ordinal[2].lower() in ('highest','largest') if ordinal else None,
            'explicit_top_n': int(top[1]) if top else None,
            'quantity_difference_scalar':quantity_difference,
            'entity_identifier_output':identifier_candidates[0] if len(identifier_candidates)==1 else None,
            'percentage_real_arithmetic': percentage and units['arithmetic_preference']=='floating_count_ratio',
            'canonical_values': lookup['matches'],
            'guidance': [
                'For ranked nonmissing values, write NULLS LAST explicitly on nullable ORDER BY expressions, including ABS and aggregates. Preserve any explicit request to rank missing values first.',
                'Preserve Top-N size, ordinal offset, direction, ties and requested output order; do not add arbitrary tie-breakers.',
                'Project exactly the requested attributes. For a list of entity instances without requested attributes, prefer that entity primary key; do not SELECT table.*. This is an explicit development output convention, not an inferred reference answer.',
                'For full names, keep first/last fields together and include all numbered person slots requested, in slot order. Do not add email/contact fields.',
                'Cover every business population and condition from question/evidence. A difference calculation returns the requested signed difference, not ABS or an extra Yes/No column unless requested.',
                'Profile samples are coverage hints, never new mandatory filters. Do not turn names, table/role nouns or arithmetic constants into equality predicates. Required conditions below bind a specific public evidence field and value; preserve that ownership.',
                'Inspect entity_grain.enforcement and its public_basis. Only an explicit distinct-entity request mandates deduplication. A primary key or one-to-many join alone is advisory: preserve requested joined-row weighting and state unresolved grain; do not invent DISTINCT or choose reference answers.',
                'Join edges in relation_role_context are alternatives. Select the participant matching the question action, not an editor/owner merely because it is the first shortest path. Context output groups use the explicit development convention to include the named related entity title/name alongside the requested actor label; they are not reference-answer hints.',
                'If quantity_difference_scalar is true, the evidence provides the quantity formula for an independent yes/no comparison: return only that signed numeric difference, whose sign also answers the comparison. If entity_identifier_output is supplied, the explicit entity-list development convention requests that primary identifier alone.',
                'Foreign keys store identifiers, not human names. Join the authorized referenced entity and filter its name field. Name fields on different tables are not assumed interchangeable.',
                'Canonical values below come from bounded case-insensitive equality lookups. Use a unique stored spelling without removing/changing conditions; not_found and ambiguous are not permission to guess.',
                'Use output_units for scale/type decisions and participant_output for projection groups. These are versioned public development conventions with explicit overrides and ambiguity records, not hidden reference requirements. For count percentages, prefer a REAL or DOUBLE PRECISION numerator scaled before division; operation order alone never triggers rejection. Preserve explicit fraction, exact-formula, decimal and rounding requests. Native EX has no tolerance.',
                'Missing schema is a reason to clarify only after checking the supplied authorized field groups and declared FK paths. Explain the specific missing field or ambiguity.'
            ]}
    if semantic_planning:
        result['query_semantic_planning_policy'] = query_semantics_policy()
        result['query_semantic_planning_guidance'] = list(QUERY_SEMANTICS_GUIDANCE)
    return result


def bindings(tree, tables):
    by_name = {t['name']: t for t in tables.values()}; resolved = {}
    for scope in traverse_scope(tree):
        refs = {alias: by_name[source.name] for alias, source in scope.sources.items()
                if isinstance(source, exp.Table) and not source.catalog and source.db in ('', 'public') and source.name in by_name}
        for column in scope.columns:
            if column.table:
                t = refs.get(column.table)
                matches = [t] if t and any(f['name'] == column.name for f in t['fields']) else []
            else:
                matches = [t for t in refs.values() if any(f['name'] == column.name for f in t['fields'])]
            if len(matches) == 1: resolved[id(column)] = (matches[0], next(f for f in matches[0]['fields'] if f['name'] == column.name))
    return resolved


def violations(runtime, public, contract, sql):
    """Conservative checks; uncertain meaning is advisory, never fabricated SQL evidence."""
    tree = parsed(sql)
    if tree is None: return []  # Existing SQL parser/security errors retain precedence.
    tables = checked_tables(runtime); refs = bindings(tree, tables); issues = []
    def add(code, reason, **kw):
        item = {'code': code, 'reason': reason, **kw}
        if item not in issues: issues.append(item)
    def resolved(column): return refs.get(id(column))
    text = text_input(public)
    missing_first = bool(re.search(r'(?:null|missing)(?:\s+\w+){0,3}\s+first', text, re.I))
    for select in tree.find_all(exp.Select):
        ordering = select.args.get('order')
        if ordering and not missing_first:
            for ordered in ordering.expressions:
                expression = ordered.this
                # Resolve projection aliases and numeric ORDER BY ordinals.
                if isinstance(expression, exp.Column) and not expression.table:
                    alias = next((p.this for p in select.expressions if isinstance(p, exp.Alias) and p.alias == expression.name), None)
                    if alias is not None: expression = alias
                if isinstance(expression, exp.Literal) and not expression.is_string and expression.this.isdigit():
                    n = int(expression.this)
                    if 1 <= n <= len(select.expressions): expression = select.expressions[n-1]
                cols = list(expression.find_all(exp.Column))
                nullable = not isinstance(expression, exp.Count) and any(resolved(c) and resolved(c)[1].get('nullable', True) for c in cols)
                if nullable and ordered.args.get('nulls_first') is True:
                    add('nullable_order_nulls_first', 'Rank nonmissing values first: use explicit NULLS LAST on this nullable ordering expression.', expression=expression.sql(dialect='postgres')[:256])
        if any(isinstance(p, exp.Star) or isinstance(p, exp.Column) and isinstance(p.this, exp.Star) for p in select.expressions):
            if not re.search(r'\ball\s+(?:columns|fields|attributes|details)\b', public['question'], re.I):
                add('unrequested_projection_star', 'Choose the requested output attributes explicitly; a list of entities defaults to their primary identifiers under this development convention.')
    if isinstance(tree, exp.Select) and contract['ordinal_rank']:
        limit = tree.args.get('limit'); offset = tree.args.get('offset')
        n = contract['ordinal_rank']
        if not tree.args.get('order') and not any(tree.find_all(exp.Window)):
            add('ordinal_missing_order', 'An ordinal rank requires an explicit ordering or ranking window.')
        if tree.args.get('order'):
            first=tree.args['order'].expressions[0]
            if bool(first.args.get('desc')) != contract['ordinal_descending']:
                add('ordinal_direction','Preserve the highest/lowest direction stated in the requested ordinal.')
        if limit and isinstance(limit.expression, exp.Literal) and limit.expression.this == '1':
            actual = int(offset.expression.this) if offset and isinstance(offset.expression, exp.Literal) and offset.expression.this.isdigit() else 0
            if actual != n-1: add('ordinal_offset', 'The requested ordinal requires OFFSET rank minus one with LIMIT 1.', expected_offset=n-1)
        elif not any(isinstance(w.this, (exp.RowNumber, exp.Rank, exp.DenseRank)) for w in tree.find_all(exp.Window)):
            add('ordinal_topn', 'Implement the requested ordinal with LIMIT 1/OFFSET or an explicit ranking window.')
    if isinstance(tree, exp.Select) and contract.get('explicit_top_n') and not any(tree.find_all(exp.Window)):
        limit=tree.args.get('limit');n=contract['explicit_top_n']
        if not limit or not isinstance(limit.expression,exp.Literal) or limit.expression.this != str(n):
            add('topn_size','Preserve the explicit Top-N result size from the original question.',requested_limit=n)
    used_tables={t['id'] for scope in traverse_scope(tree) for source in scope.sources.values()
                 if isinstance(source,exp.Table) and not source.catalog and source.db in ('','public')
                 for t in tables.values() if t['name']==source.name}
    if isinstance(tree, exp.Select):
        outputcols = {(t['id'], f['name']) for p in tree.expressions for c in p.find_all(exp.Column)
                      if (pair := resolved(c)) for t, f in [pair]}
        for group in contract['name_groups']:
            required = {(group['table_id'], n) for n in group['fields']}
            if group['output_group'] and required & outputcols and not required <= outputcols:
                add('incomplete_output_name_group', 'Include every requested numbered first/last-name slot, in slot order.', fields=group['fields'])
        if contract.get('quantity_difference_scalar'):
            if len(tree.expressions)!=1:
                add('difference_output_shape','Return the signed quantity from the evidence formula as one numeric output expression, without an additional explanatory Yes/No column.')
            if any(a.find(exp.Sub) is not None for a in tree.find_all(exp.Abs)):
                add('difference_sign','Do not wrap the signed difference specified by the evidence in ABS.')
        identifier=contract.get('entity_identifier_output')
        if identifier:
            expected={(identifier['table_id'],identifier['field'])}
            if outputcols and (outputcols != expected or len(tree.expressions)!=1 or any(tree.expressions[0].find_all(exp.AggFunc))):
                add('entity_identifier_projection','Under the explicit development convention, an entity list without requested attributes projects its primary identifier alone.',**identifier)
    for condition in contract['required_profile_conditions']:
        if condition.get('mandatory') is not True or condition.get('authority')!='unique_public_field_value_binding':continue
        if condition['table_id'] not in used_tables: continue
        found = False
        def owns(column):
            pair=resolved(column) if isinstance(column,exp.Column) else None
            return bool(pair and pair[0]['id']==condition['table_id'] and pair[1]['name']==condition['field'])
        for equality in tree.find_all(exp.EQ):
            c, literal = equality.left, equality.right
            if isinstance(literal, exp.Column): c, literal = literal, c
            pair = resolved(c) if isinstance(c, exp.Column) else None
            if pair and pair[0]['id'] == condition['table_id'] and pair[1]['name'] == condition['field'] and isinstance(literal, exp.Literal) and literal.is_string and literal.this.casefold() == condition['value'].casefold():
                if equality.find_ancestor(exp.Where, exp.Having, exp.Filter, exp.Case, exp.Join): found = True
            if isinstance(c,(exp.Lower,exp.Upper)) and owns(c.this) and isinstance(literal,exp.Literal) and literal.is_string and condition['value'].isascii():
                expected=condition['value'].lower() if isinstance(c,exp.Lower) else condition['value'].upper()
                if literal.this==expected and equality.find_ancestor(exp.Where,exp.Having,exp.Filter,exp.Case,exp.Join):found=True
        for inclusion in tree.find_all(exp.In):
            if owns(inclusion.this) and len(inclusion.expressions)==1:
                literal=inclusion.expressions[0]
                if isinstance(literal,exp.Literal) and literal.is_string and literal.this==condition['value'] and inclusion.find_ancestor(exp.Where,exp.Having,exp.Filter,exp.Case,exp.Join):found=True
        if not found: add('missing_population_condition', 'An explicit public field/value condition is absent. Preserve its uniquely bound owning field; samples alone do not require predicates.', field_id=condition['field_id'], value=condition['value'])
    for match in contract['canonical_values']:
        if match['resolution'] != 'unique_database_lower_match': continue
        expected = match['values'][0]
        for equality in tree.find_all(exp.EQ):
            c, literal = equality.left, equality.right
            if isinstance(literal, exp.Column): c, literal = literal, c
            pair = resolved(c) if isinstance(c, exp.Column) else None
            if pair and pair[0]['id'] == match['table_id'] and pair[1]['name'] == match['field'] and isinstance(literal, exp.Literal) and literal.is_string and literal.this.casefold() == expected.casefold() and literal.this != expected:
                add('noncanonical_literal', 'Use the unique stored literal spelling for this case-sensitive equality.', field=match['field'], canonical=expected)
    # Only flag a foreign-key/name comparison when the public request explicitly
    # identifies the referenced entity name. UUIDs/numeric/text IDs stay valid.
    for equality in tree.find_all(exp.EQ):
        c, literal = equality.left, equality.right
        if isinstance(literal, exp.Column): c, literal = literal, c
        pair = resolved(c) if isinstance(c, exp.Column) else None
        if not pair or not isinstance(literal, exp.Literal) or not literal.is_string: continue
        t, f = pair
        for relation in runtime.catalog.relations:
            if relation['right_table'] != t['id'] or relation['right_field'] != f['name']: continue
            parent = tables[relation['left_table']]
            for field in parent['fields']:
                if 'name' not in field['name'].lower() or not mentioned(field, text): continue
                if literal.this in public['question'] and re.search(r"'" + re.escape(literal.this) + r"'", public['question']):
                    if re.search(r"\b(?:id|identifier|code)\s*(?:=|is|of|:)?\s*'" + re.escape(literal.this) + "'", public['question'], re.I): continue
                    add('name_compared_to_foreign_key', 'Join the authorized named entity; its foreign key stores an identifier, not the requested human name.', key=t['id']+'.'+f['name'], name_field=parent['id']+'.'+field['name'])
    if contract['percentage_real_arithmetic'] and any(tree.find_all(exp.Div)):
        float_casts = [c for div in tree.find_all(exp.Div) for c in div.this.find_all(exp.Cast)
                       if str(c.args.get('to')).upper() in ('FLOAT', 'REAL', 'DOUBLE')
                       and not any(c.this.find_all(exp.Div))]
        # Candidate convention is advisory on complex expressions; reject the
        # common count-ratio decimal path only when no floating operand exists.
        if any(tree.find_all(exp.Count)) and not float_casts:
            add('percentage_numeric_path', 'Development numeric policy requires a REAL or DOUBLE PRECISION numerator before scaling/division; avoid a decimal literal or final-only cast unless explicitly requested. Native EX has no tolerance.')
        # A different multiplication/division order alone does not establish a
        # wrong native result. Keep formula/type guidance in the contract; never
        # reject or rewrite a query solely to enforce a preferred evaluation order.
    from .relationships import grain_violations
    for item in grain_violations(runtime,contract.get('entity_grain',{}),tree,refs):
        add(item.pop('code'),item.pop('reason'),**item)
    from .units_output import unit_violations,output_violations
    for item in unit_violations(public,contract['output_units'],tree)+output_violations(contract['participant_output'],tree,refs):
        add(item.pop('code'),item.pop('reason'),**item)
    return issues[:8]
