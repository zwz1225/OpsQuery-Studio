"""BIRD-only read-query policy. Original Gold SQL bytes are never rewritten."""
from __future__ import annotations

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope

from .budgets import BirdFailure

FUNCTIONS=frozenset('COUNT SUM AVG MIN MAX CAST COALESCE NULLIF ROUND FLOOR CEIL ABS GREATEST LEAST CONCAT LOWER UPPER LENGTH SUBSTRING TRIM REPLACE SPLIT_PART EXTRACT TIME_TO_STR DATE_TRUNC TIMESTAMP_TRUNC DATE CURRENT_DATE CURRENT_TIMESTAMP CURRENT_TIME NOW AGE ROW_NUMBER RANK DENSE_RANK LAG LEAD FIRST_VALUE LAST_VALUE PERCENT_RANK CUME_DIST NTILE BOOL_AND BOOL_OR STRING_AGG ARRAY_AGG STDDEV STDDEV_POP STDDEV_SAMP VAR_POP VAR_SAMP CASE IF DATE_DIFF TIME_TO_UNIX TO_TIMESTAMP LEFT RIGHT EXISTS SQRT POWER MOD STR_POSITION'.split())


def validate_sql(sql: str, table_names: set[str]) -> str:
    if not isinstance(sql,str) or not sql.strip() or len(sql.encode())>98304:raise BirdFailure('invalid_sql_input')
    try: statements=[x for x in sqlglot.parse(sql,read='postgres') if x is not None]
    except sqlglot.errors.ParseError:raise BirdFailure('sql_parse_error') from None
    if len(statements)!=1 or not isinstance(statements[0],exp.Query):raise BirdFailure('readonly_query_required')
    tree=statements[0]
    forbidden={'insert','update','delete','merge','create','drop','alter','copy','command','transaction','grant','revoke','into','lock','objectidentifier','parameter','placeholder'}
    if any(n.key in forbidden for n in tree.walk()):raise BirdFailure('forbidden_sql_operation')
    for node in tree.walk():
        if isinstance(node,exp.Dot) and isinstance(node.expression,exp.Func):raise BirdFailure('qualified_function_denied')
        if isinstance(node,exp.Func) and not isinstance(node,(exp.And,exp.Or,exp.Not)):
            name=node.name.upper() if isinstance(node,exp.Anonymous) else node.sql_name()
            if name not in FUNCTIONS:raise BirdFailure('sql_function_denied')
        if isinstance(node,exp.DataType) and node.this==exp.DataType.Type.USERDEFINED:raise BirdFailure('user_type_denied')
    for scope in traverse_scope(tree):
        for source in scope.sources.values():
            if isinstance(source,exp.Table):
                table=source.name if source.this.args.get('quoted') else source.name.lower()
                db=source.args.get('db');schema=source.db if db is not None and db.args.get('quoted') else source.db.lower()
                if source.catalog or schema not in ('','public') or table not in table_names:
                    raise BirdFailure('sql_source_denied')
                if not isinstance(source.this,exp.Identifier):raise BirdFailure('table_function_denied')
    return sql
