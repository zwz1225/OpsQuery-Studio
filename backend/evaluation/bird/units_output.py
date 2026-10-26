"""Explicit development conventions derived from public text and authorized fields.

No answer/reference access, case identifiers, SQL rewrites or result conversions.
"""
from __future__ import annotations

from decimal import Decimal,InvalidOperation
import re
from sqlglot import exp
from evaluation.bird_protocol import validate_agent_input

UNIT_POLICY='public_percentage_units_precision_v2'
OUTPUT_POLICY='participant_action_target_pair_v1'


def precision_contract(public):
    validate_agent_input(public)
    words=dict(zero=0,one=1,two=2,three=3,four=4,five=5,six=6,seven=7,eight=8,nine=9,ten=10,
               eleven=11,twelve=12,thirteen=13,fourteen=14,fifteen=15)
    pattern=r'\b('+ '|'.join(words)+r'|[0-9]{1,2})\s+decimal\s+places?\b'
    requests=[]
    for source in ('question','evidence'):
        for m in list(re.finditer(pattern,public[source],re.I))[:4]:
            value=words.get(m[1].casefold())
            if value is None:value=int(m[1])
            requests.append(dict(source=source,span=[m.start(),m.end()],text=m[0],decimal_places=value))
    values={v['decimal_places'] for v in requests}
    exact=next(iter(values)) if len(values)==1 else None
    negated=bool(re.search(r"\b(?:do not|don't|without|avoid)\s+(?:round(?:ing)?|rounding\s+off)\b",public['question']+'\n'+public['evidence'],re.I))
    supported=exact is not None and 0<=exact<=15 and not negated
    return dict(policy='explicit_public_decimal_places_v1',decimal_places=exact if supported else None,
        enforcement='hard_for_simple_numeric_output' if supported else 'advisory',requests=requests,
        conflict=len(values)>1 or bool(values) and negated,unsupported=bool(values) and exact is not None and not 0<=exact<=15,
        guidance='Implement explicitly requested decimal places in the final SQL numeric output (for example ROUND(numeric_expression, n)). Preserve the requested unit and population; do not round driver results or add scoring tolerance. Ambiguous/complex output ownership is advisory.')


def unit_contract(public):
    validate_agent_input(public)
    question=public['question'];evidence=public['evidence'];text=question+'\n'+evidence
    percent=bool(re.search(r'\b(?:percentage|percent)\b|(?<!\w)%(?!\w)',question,re.I))
    ratio=bool(re.search(r'\b(?:ratio|fraction|proportion)\b',question,re.I))
    fraction_override=bool(re.search(r'\b(?:0\s*(?:to|[-–])\s*1|(?:as|return|report|express(?:ed)?\s+as)\s+(?:an?\s+)?(?:fraction|ratio|proportion))\b',text,re.I))
    exact_formula=bool(re.search(r'\b(?:follow|use|preserve)\s+(?:the\s+)?(?:evidence\s+)?formula\s+exactly\b',text,re.I))
    formula=re.search(r'\b(?:percentage|percent|ratio|fraction|proportion)\s*=\s*([^;\n]+)',evidence,re.I)
    formula_text=formula[1].strip()[:256] if formula else None
    # This flag records an ambiguity rather than claiming to parse arbitrary
    # formulas. Explicit unit overrides and "formula exactly" have precedence.
    unscaled_formula=bool(formula_text and (re.search(r'\bDIVIDE\s*\(|/',formula_text,re.I))
                          and not re.search(r'(?:\*\s*100(?:\.0+)?\b|100(?:\.0+)?\s*\*)',formula_text))
    if fraction_override:
        unit='fraction_0_1';scale=1;basis='explicit_public_fraction_unit'
    elif exact_formula:
        unit='formula_defined';scale=None;basis='explicit_exact_formula_request'
    elif percent:
        unit='percent_0_100';scale=100;basis='question_percentage_output_unit'
    elif ratio:
        unit='fraction_0_1';scale=1;basis='question_ratio_output_unit'
    else:
        unit='unspecified';scale=None;basis='no_explicit_output_unit'
    decimal_requested=bool(re.search(r'\b(?:numeric|decimal)\s+(?:arithmetic|type)|\b(?:as|use|using)\s+(?:numeric|decimal)\b',text,re.I))
    rounding_requested=bool(re.search(r'\b(?:round|rounded|rounding|decimal places)\b',text,re.I))
    numeric=('explicit_decimal' if decimal_requested else 'explicit_rounding' if rounding_requested
             else 'floating_count_ratio' if unit=='percent_0_100' else 'requested_or_source_type')
    return dict(policy=UNIT_POLICY,output_unit=unit,ratio_multiplier=scale,resolution_basis=basis,precision=precision_contract(public),
        formula_excerpt=formula_text,question_formula_scale_conflict=percent and unscaled_formula,
        resolution_is_development_convention=percent and unscaled_formula and not fraction_override and not exact_formula,
        arithmetic_preference=numeric,operation_order_authority='advisory_only',
        guidance='Percentage means a 0-100 numeric output under this visible development convention. An evidence DIVIDE formula without a scale supplies the base ratio; the percentage question supplies *100. Explicit 0-1/fraction requests or an exact-formula instruction override this default. Record conflicts; never consult a reference answer. For unrounded count percentages prefer CAST(conditional_count AS REAL) * 100 / NULLIF(total_count,0), preserving entity grain; DOUBLE PRECISION is also allowed. Scaling before division is a numerical suggestion, never an operation-order rejection. Do not change types, round, or normalize returned results to make comparisons pass.')


def _strip(expression):
    while isinstance(expression,(exp.Paren,exp.Cast)):expression=expression.this
    return expression


def _number(expression):
    expression=_strip(expression)
    if isinstance(expression,exp.Literal) and not expression.is_string:
        try:return Decimal(expression.this)
        except InvalidOperation:pass
    return None


def _count_indicator(expression):
    expression=_strip(expression)
    if isinstance(expression,exp.Count):return True
    if isinstance(expression,exp.Sum) and isinstance(expression.this,exp.Case):
        case=expression.this;branches=case.args.get('ifs',[])
        return bool(branches and all(_number(v.args['true'])==1 for v in branches)
                    and (case.args.get('default') is None or _number(case.args['default'])==0))
    return False


def _scaled_count(expression):
    expression=_strip(expression)
    if _count_indicator(expression):return Decimal(1)
    if isinstance(expression,exp.Mul):
        for literal,other in ((expression.left,expression.right),(expression.right,expression.left)):
            number=_number(literal)
            if number is not None:
                factor=_scaled_count(other)
                if factor is not None:return number*factor
    return None


def count_ratio_scale(expression):
    """Recognize only the arithmetic spine, never 100 in filters/CASE/COUNT args."""
    expression=_strip(expression)
    if isinstance(expression,exp.Div):
        denominator=_strip(expression.right)
        if isinstance(denominator,exp.Nullif) and _number(denominator.expression)==0:denominator=_strip(denominator.this)
        if isinstance(denominator,exp.Count):return _scaled_count(expression.left)
        number=_number(expression.right)
        if number not in (None,0):
            scale=count_ratio_scale(expression.left)
            if scale is not None:return scale/number
    if isinstance(expression,exp.Mul):
        for literal,other in ((expression.left,expression.right),(expression.right,expression.left)):
            number=_number(literal)
            if number is not None:
                scale=count_ratio_scale(other)
                if scale is not None:return scale*number
    return None


def precision_violations(contract,tree):
    precision=contract.get('precision',{})
    if precision.get('enforcement')!='hard_for_simple_numeric_output':return []
    if not isinstance(tree,exp.Select) or len(tree.expressions)!=1:return []
    expression=tree.expressions[0].unalias();observed=None
    # Only an outer result-level ROUND or fixed NUMERIC scale establishes the
    # output precision. ROUND inside SUM/CASE/filter cannot satisfy the request.
    while isinstance(expression,(exp.Paren,exp.Cast)):
        if isinstance(expression,exp.Cast):
            kind=expression.args['to'];params=kind.expressions
            if kind.this==exp.DataType.Type.DECIMAL and len(params)==2:
                value=_number(params[1].this)
                if value is not None and value==int(value):observed=int(value);break
        expression=expression.this
    if observed is None and isinstance(expression,exp.Round):
        value=_number(expression.args.get('decimals')) if expression.args.get('decimals') is not None else Decimal(0)
        if value is not None and value==int(value):observed=int(value)
    # A column/CTE alias or arbitrary scalar function cannot be resolved here;
    # existing catalog validation and public guidance retain precedence.
    numeric=isinstance(expression,(exp.Round,exp.AggFunc,exp.Div,exp.Mul,exp.Add,exp.Sub,exp.Literal)) or observed is not None
    if not numeric:return []
    expected=precision['decimal_places']
    if observed!=expected:
        return [dict(code='requested_decimal_precision',reason='The final simple numeric output must implement the explicit public decimal-place request in SQL. Use PostgreSQL-compatible numeric ROUND or a fixed NUMERIC scale; preserve unit and population.',
                     expected_decimal_places=expected,observed_decimal_places=observed)]
    return []


def unit_violations(public,contract,tree):
    issues=precision_violations(contract,tree)
    # Complex formulas and unresolved output scopes remain advisory.
    # An exact-formula instruction deliberately has no imposed scale.
    if not isinstance(tree,exp.Select) or len(tree.expressions)!=1 or contract['ratio_multiplier'] is None:return issues
    expression=tree.expressions[0].unalias()
    while isinstance(expression,(exp.Paren,exp.Cast,exp.Round)):expression=expression.this
    observed=count_ratio_scale(expression)
    expected=Decimal(contract['ratio_multiplier'])
    if observed is not None and observed!=expected:
        issues.append(dict(code='percentage_output_unit',reason='The simple count ratio does not use the explicitly recorded output unit. Preserve the population and entity grain; apply the recorded scale in SQL, without changing returned results or scoring.',
            output_unit=contract['output_unit'],expected_multiplier=str(expected),observed_multiplier=str(observed),
            resolution_basis=contract['resolution_basis']))
    return issues


def participant_output_contract(public,graph,tables,relations=()):
    validate_agent_input(public)
    question=public['question'];roles=graph.get('relation_role_context',{})
    groups=roles.get('context_output_groups',[]);preferences=roles.get('preferred_actor_relations',[])
    selected={v['id'] for v in graph.get('fields',[])}
    result=dict(policy=OUTPUT_POLICY,required_groups=[],advisory_groups=groups,
        basis='public_action_target_frame_and_unique_authorized_role',
        guidance='Required groups are an explicit development output convention: project the requested participant label and the named action-target title, in that order. Mere filter/context mentions do not mandate projection. Explicit only/exclude instructions take precedence. Do not add contact fields, all columns or other candidate join roles.')
    # Explicit restrictions and aggregations override the optional actor/context
    # convention. A title mentioned only inside a WHERE-like clause is advisory.
    restricted=bool(re.search(r'\bonly\b|\b(?:without|exclude|omit)\b|\bdo not (?:include|return|show)\b',question,re.I))
    action=re.search(r'\b(?:added|cast|submitted|performed|made|posted)\b',question,re.I)
    target=re.search(r'\b(?:to|on|for)\s+(?:(?:the|an?)\s+)?((?:[A-Za-z_]+\s+){0,3})title\b',question,re.I)
    if restricted or not re.match(r'\s*(?:which|who|list)\b',question,re.I) or not action or not target:return result
    if re.search(r'\b(?:where|whose|with|having|when)\b',target[1],re.I) or target.start()<action.end():return result
    if len(groups)!=1 or len(preferences)!=1:return result
    group=groups[0];fields=[group['actor_label'],group['context_label']]
    if not set(fields)<=selected:return result
    owners={tid+'.'+f['name']:(t,f) for tid,t in tables.items() for f in t['fields']}
    if not set(fields)<=set(owners):return result
    actor_table=owners[fields[0]][0]
    words={w.casefold().rstrip('s') for w in re.findall(r'[A-Za-z]+',actor_table['name'])}
    prefix=question[:action.start()]
    if not re.match(r'\s*who\b',prefix,re.I) and not words & {w.casefold().rstrip('s') for w in re.findall(r'[A-Za-z]+',prefix)}:return result
    chosen=next((v for v in roles.get('roles',[]) if v['relation_id']==preferences[0]['relation_id']),None)
    if not chosen or chosen['parent_table']!=actor_table['id']:return result
    # A preferred role in the graph is insufficient without its actual catalog
    # FK and a declared action-to-target FK. Both endpoint keys must be in graph.
    actor_edges=[v for v in relations if v['id']==chosen['relation_id'] and v['left_table']==chosen['parent_table']
                 and v['right_table']==chosen['child_table'] and v['left_field']==chosen.get('parent_field')
                 and v['right_field']==chosen.get('child_field')]
    context_table=owners[fields[1]][0]
    target_edges=[v for v in relations if v['left_table']==context_table['id'] and v['right_table']==chosen['child_table']]
    if len(actor_edges)!=1 or len(target_edges)!=1:return result
    if any(not {v['left_table']+'.'+v['left_field'],v['right_table']+'.'+v['right_field']}<=selected
           for v in actor_edges+target_edges):return result
    result['required_groups']=[dict(fields=fields,mandatory=True,
        authority='versioned_public_action_target_output_convention',relation_id=chosen['relation_id'])]
    return result


def output_violations(contract,tree,refs):
    if not isinstance(tree,exp.Select):return []
    # CTE/subquery outputs with unresolved ownership are advisory, rather than
    # falsely claiming a missing authorized field.
    outputs=[]
    for projection in tree.expressions:
        value=projection.unalias()
        if not isinstance(value,exp.Column) or id(value) not in refs:return []
        table,field=refs[id(value)];outputs.append(table['id']+'.'+field['name'])
    for group in contract['required_groups']:
        required=group['fields']
        missing=[v for v in required if v not in outputs]
        if missing:
            return [dict(code='incomplete_participant_context_output',reason='The visible development output group requires both the requested participant and named action-target title. A field used only in WHERE/JOIN is not projected.',
                         missing_field_ids=missing,required_field_ids=required,authority=group['authority'])]
        if len(outputs)==len(required) and outputs!=required:
            return [dict(code='participant_context_output_order',reason='Project the participant label before the named action-target title under the recorded output convention.',required_field_ids=required)]
    return []
