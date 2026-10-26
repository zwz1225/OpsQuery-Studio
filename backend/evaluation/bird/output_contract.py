"""Opt-in public output hints and passive SQL observations, never scoring rules.

Inputs are the original public request, its already selected authorized graph and
existing public-intent groups. No runtime, files, samples, answers or model calls.
This is a small output-request grammar, not an English semantic parser.
"""
from __future__ import annotations

import json
import re

from sqlglot import exp

from evaluation.bird_protocol import validate_agent_input
from .repair import parsed

POLICY = 'bird_public_output_contract_v1'
MAX_ITEMS = 8
MAX_BYTES = 12288
MAX_INPUT_CHARS = 24000


def policy():
    return dict(policy_id=POLICY, development_only=True, default_enabled=False,
                input_source='original_question_official_evidence_selected_authorized_graph',
                enforcement='prompt_and_report_only', new_model_calls=0,
                new_sql_calls=0, hard_rejection=False, sql_rewrite=False,
                result_conversion=False, max_items=MAX_ITEMS, max_utf8_bytes=MAX_BYTES)


def _norm(text):
    text = re.sub(r"['’]s\b", '', text.casefold())
    text = re.sub(r'\bmailing\b', 'mail', text)
    text = re.sub(r'[^a-z0-9]+', ' ', text).strip()
    words = text.split()
    words = [w[:-1] if w in ('names', 'types', 'schools', 'cards', 'members', 'fields', 'codes') else w for w in words]
    while words and words[0] in ('the', 'a', 'an', 'all', 'only'):
        words.pop(0)
    return ''.join(words)


def _source(public, source, start, end):
    return dict(source=source, span=[start, end], text=public[source][start:end])


def _fields(public, graph):
    db = public['database_id']
    if graph.get('database') != db:
        raise ValueError('Output graph belongs to another database')
    fields = graph.get('fields', [])
    result = {}
    for field in fields:
        tid, name = field.get('table_id'), field.get('name')
        if not isinstance(tid, str) or not tid.startswith(db + '.') or not isinstance(name, str) or field.get('id') != tid + '.' + name:
            raise ValueError('Output graph contains a foreign or malformed field')
        if field['id'] in result:
            raise ValueError('Output graph contains duplicate fields')
        result[field['id']] = field
    identity = graph.get('source_identity', {})
    if identity and (identity.get('logical_database_id') != db or identity.get('physical_schema') != 'public'):
        raise ValueError('Output graph source identity differs')
    return result


def _matches(phrase, fields):
    wanted = _norm(phrase)
    if not wanted:
        return []
    matches = []
    for fid, field in fields.items():
        forms = [field['name'], field.get('label', '')]
        description = field.get('description', '')
        if len(description) <= 160:
            forms.append(description)
        table = field['table_id'].split('.', 1)[1]
        # An entity-labelled name field is an alternative, never a preferred table.
        if _norm(field['name']) in ('name', _norm(table)):
            forms.append(table.rstrip('s') + ' name')
        if wanted in {_norm(v) for v in forms if v}:
            matches.append(fid)
    return matches


def _public_definitions(public, fields):
    evidence = public['evidence']
    groups, formulae, synonyms = [], [], []
    for match in re.finditer(r'([^;\n=]{1,120}?)\s+refers?\s+to\s+([^;\n]{1,300})', evidence, re.I):
        parts = [v.strip().strip('`"') for v in re.split(r',|\band\b', match[2], flags=re.I)]
        bound = [_matches(part, fields) for part in parts]
        if len(parts) >= 2:
            complete = all(len(v) == 1 for v in bound)
            groups.append(dict(term=_norm(match[1]),
                               field_ids=[v[0] for v in bound] if complete else [],
                               binding_complete=complete,
                               mention=_source(public, 'evidence', match.start(), match.end())))
    for match in re.finditer(r'([^;\n=]{1,160}?)\s*=\s*([^;\n]{1,1024})', evidence):
        if not re.search(r'[/+*]|\b(?:DIVIDE|SUM|COUNT|AVG)\s*\(', match[2], re.I):
            continue
        quoted = re.findall(r'[`"]([^`"]+)[`"]', match[2])
        refs = [_matches(v, fields) for v in quoted]
        if not quoted:
            names = list(dict.fromkeys(f['name'] for f in fields.values()))
            refs = [_matches(name, fields) for name in names
                    if re.search(r'(?<![\w])' + re.escape(name) + r'(?![\w])', match[2], re.I)]
        unique = list(dict.fromkeys(v[0] for v in refs if len(v) == 1))
        formulae.append(dict(term=_norm(match[1]), text=match[2], field_ids=unique,
            binding_complete=bool(refs) and all(len(v) == 1 for v in refs),
            mention=_source(public, 'evidence', match.start(), match.end())))
    for match in re.finditer(r'([^;.\n]{1,100}?)\s+and\s+([^;.\n]{1,100}?)\s+are\s+synonyms\b', evidence, re.I):
        synonyms.append(dict(terms=[match[1].strip(), match[2].strip()],
                             mention=_source(public, 'evidence', match.start(), match.end())))
    return groups, formulae, synonyms


def _requests(public):
    text = public['question']
    pattern = r'(?:^|[?!;.]\s*|,\s*)(?:please\s+)?(?:what\s+(?:is|are|was|were)\s+|which\s+|lists?\s+|indicate\s+|give\s+|provide\s+|show\s+|mention\s+|state\s+|name\s+)'
    for request in re.finditer(pattern, text, re.I):
        start = request.end()
        tail = text[start:]
        stop = re.search(r'[?!;.]|\b(?:in|for|of|from|at|whose|that|which|with|who|by|where|when|among|under|having|recorded|published|located|serving)\b|,\s*(?:not|without|except)|\b(?:except|excluding|without|do not|but not)\b', tail, re.I)
        end = start + (stop.start() if stop else len(tail))
        phrase = text[start:end]
        for part in re.finditer(r'[^,]+?(?=\s+and\s+|,|$)', phrase, re.I):
            a, z = start + part.start(), start + part.end()
            value = text[a:z].strip()
            value = re.sub(r'^and\s+', '', value, flags=re.I)
            if not value:
                continue
            a = text.find(value, a, z)
            yield value, _source(public, 'question', a, a + len(value))


def _bind(phrase, fields, definitions, existing):
    groups, formulae, synonyms = definitions
    wanted = _norm(phrase)
    group_matches = [group for group in groups if group['term'] == wanted]
    formula_matches = [formula for formula in formulae if formula['term'] == wanted]
    definitions_differ = len({tuple(g['field_ids']) for g in group_matches}) > 1 or len({f['text'] for f in formula_matches}) > 1
    if definitions_differ or group_matches and formula_matches:
        return dict(kind='unresolved', field_ids=[], binding_complete=False,
                    authority='conflicting_public_definitions',
                    evidence=[v['mention'] for v in (group_matches + formula_matches)[:4]])
    if group_matches and not all(group['binding_complete'] for group in group_matches):
        return dict(kind='unresolved', field_ids=[], binding_complete=False,
                    authority='incomplete_public_definition',
                    evidence=[group['mention'] for group in group_matches[:4]])
    if group_matches:
        group = group_matches[0]
        return dict(kind='field_group', field_ids=group['field_ids'], binding_complete=True,
                    authority='explicit_public_definition', evidence=[group['mention']])
    if formula_matches:
        formula = formula_matches[0]
        return dict(kind='formula', field_ids=formula['field_ids'], formula_text=formula['text'],
                    binding_complete=formula['binding_complete'], authority='explicit_public_formula',
                    evidence=[formula['mention']])
    if wanted in ('fullname', 'fullnames'):
        name_groups = [dict(field_ids=[g['table_id'] + '.' + n for n in g['fields']])
                       for g in existing.get('name_groups', [])]
        valid = [g for g in name_groups if set(g['field_ids']) <= set(fields)]
        if len(valid) == 1:
            return dict(kind='field_group', field_ids=valid[0]['field_ids'], binding_complete=True,
                        authority='existing_public_name_group', evidence=[])
    # A postal/mailing synonym is usable only when supplied by the public evidence.
    for synonym in synonyms:
        for term in synonym['terms']:
            if _norm(term) and _norm(term) in wanted:
                alternatives = [fid for other in synonym['terms'] for fid in _matches(other, fields)]
                alternatives = list(dict.fromkeys(alternatives))
                if len(alternatives) == 1:
                    return dict(kind='field', field_ids=alternatives, binding_complete=True,
                        authority='explicit_public_synonym', evidence=[synonym['mention']])
    matches = _matches(phrase, fields)
    return dict(kind='field' if len(matches) == 1 else 'alternatives' if matches else 'unresolved',
                field_ids=matches, binding_complete=len(matches) == 1,
                authority='selected_authorized_name_or_label', evidence=[])


def build_contract(public, graph, existing_intent=None):
    validate_agent_input(public)
    fields = _fields(public, graph)
    result = dict(policy=policy(), items=[], ambiguities=[], parse_complete=False,
        guidance='Read this advisory list together with the original question and existing public-intent groups. '
        'Preserve the requested output order and computed outputs across sentences. Fields mentioned only as filters '
        'or ORDER BY helpers are not extra projections. Explicit only/exclude instructions and existing name/participant '
        'groups take precedence over incomplete parsing. Unresolved bindings are not permission to invent columns. '
        'Do not change filters, joins, numeric paths or returned values merely to satisfy this list.')
    if sum(len(public[k]) for k in ('question', 'evidence')) > MAX_INPUT_CHARS:
        result['ambiguities'].append('input_outside_bounded_grammar')
        return result
    definitions = _public_definitions(public, fields)
    existing = existing_intent or {}
    for phrase, mention in _requests(public):
        if len(phrase) > 192 or len(result['items']) == MAX_ITEMS:
            result['ambiguities'].append('output_request_limit')
            break
        binding = _bind(phrase, fields, definitions, existing)
        item = dict(ordinal=len(result['items']) + 1, public_request=mention, **binding)
        candidate = dict(result, items=result['items'] + [item])
        if len(json.dumps(candidate, ensure_ascii=False).encode('utf-8')) > MAX_BYTES - 512:
            result['ambiguities'].append('output_contract_byte_limit')
            break
        result['items'].append(item)
        if not binding['binding_complete']:
            result['ambiguities'].append('ambiguous_or_unresolved_output_binding')
    if re.search(r'\bonly\b|\b(?:exclude|except|without|omit)\b|\bdo not\b', public['question'], re.I):
        result['ambiguities'].append('explicit_restriction_preserved_in_original_request')
    if re.search(r'^\s*(?:rank\b|did\b|is\b|are\b)', public['question'], re.I):
        result['ambiguities'].append('rank_or_boolean_shape_not_inferred')
    result['ambiguities'] = list(dict.fromkeys(result['ambiguities']))
    result['parse_complete'] = bool(result['items']) and not result['ambiguities']
    return result


def observe(contract, graph, sql):
    """Describe projections only. No validity decision, correction, SQL or budget calls."""
    result = dict(policy_id=POLICY, report_only=True, status='not_evaluated', issues=[])
    tree = parsed(sql)
    if tree is None:
        result['reason'] = 'unparseable_or_unsupported_sql'
        return result
    if not isinstance(tree, exp.Select) or tree.args.get('with_') or len(list(tree.find_all(exp.Select))) != 1 or tree.find(exp.Star) or tree.find(exp.Window):
        result['reason'] = 'complex_projection_ownership'
        return result
    fields = {f['id']: f for f in graph['fields']}
    by_table = {}
    for field in fields.values():
        by_table.setdefault(field['table_id'].split('.', 1)[1], []).append(field)
    aliases = {}
    for table in tree.find_all(exp.Table):
        if table.catalog or table.db not in ('', 'public') or table.name not in by_table:
            result['reason'] = 'unresolved_or_foreign_sql_source'
            return result
        aliases[table.alias_or_name] = by_table[table.name]
    def resolve(column):
        pool = aliases.get(column.table, []) if column.table else [f for fs in aliases.values() for f in fs]
        matches = [f['id'] for f in pool if f['name'] == column.name]
        return matches[0] if len(matches) == 1 else None
    projections = []
    for expression in tree.expressions:
        value = expression.unalias()
        columns = list(value.find_all(exp.Column))
        refs = [resolve(c) for c in columns]
        if any(v is None for v in refs):
            result['reason'] = 'unresolved_projection_field'
            return result
        projections.append(dict(field_ids=set(refs), simple=isinstance(value, exp.Column)))
    positions = []
    for item in contract['items']:
        expected = item['field_ids']
        if not item['binding_complete']:
            if item['kind']=='alternatives':
                found=[i for i,p in enumerate(projections) if p['simple'] and p['field_ids'] and p['field_ids']<=set(expected)]
                if len(found)==1:
                    positions.append(found[0])
            continue
        if item['kind'] == 'formula':
            found = [i for i, p in enumerate(projections) if not p['simple'] and set(expected) <= p['field_ids']]
            groups = [found]
        else:
            groups = [[i for i, p in enumerate(projections) if p['simple'] and p['field_ids'] == {fid}] for fid in expected]
        # A concatenation/expression might own these fields; report uncertainty.
        if any(not group for group in groups) and any(not p['simple'] and p['field_ids'] & set(expected) for p in projections) and item['kind'] != 'formula':
            result['reason'] = 'complex_projection_ownership'
            result['issues'] = []
            return result
        if any(not group for group in groups):
            result['issues'].append(dict(code='requested_output_not_observed', ordinal=item['ordinal'],
                                         expected_field_ids=expected, role=item['kind']))
        else:
            positions.extend(group[0] for group in groups)
    if positions != sorted(positions):
        result['issues'].append(dict(code='requested_output_order_differs', observed_positions=positions))
    if contract['parse_complete'] and not result['issues'] and positions and len(set(positions)) < len(projections):
        result['issues'].append(dict(code='additional_projection_observed', projection_count=len(projections)))
    result['status'] = 'observed' if contract['items'] else 'not_applicable'
    result['meaning'] = 'Projection hints only; does not establish SQL correctness, filter coverage or native EX.'
    return result


def observation(contract, graph, sql):
    """An observer error must never change validation, execution or retry decisions."""
    try:
        return observe(contract, graph, sql)
    except Exception:
        return dict(policy_id=POLICY, report_only=True, status='not_evaluated', reason='output_observation_unavailable', issues=[])
