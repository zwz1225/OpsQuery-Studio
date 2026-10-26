"""Independent structural expectations derived from the approved dump specification."""
from __future__ import annotations

import re

from scripts.m2_b_common import digest_json, require
from scripts.m2_b_dump import IDENT, unquote
from scripts.m2_b_target import TYPE_NAMES, quote, table_sql, object_inventory, require_no_executable_objects


def canonical(sql: str) -> str:
    import sqlglot
    from sqlglot import exp
    tree = sqlglot.parse_one(sql, read='postgres')
    # Metadata quoting is presentation; preserve identifier case/content exactly.
    for ident in tree.find_all(exp.Identifier): ident.set('quoted', True)
    return tree.sql(dialect='postgres')


def expectations(manifest: dict) -> dict:
    import sqlglot
    from sqlglot import exp
    constraints = {}; indexes = {}; defaults = {}; primary = {}; ownership = {}; values = {}
    for table in manifest['dump']['tables']:
        tree = sqlglot.parse_one(table['create_sql'], read='postgres')
        for col in tree.this.expressions:
            for constraint in col.args.get('constraints') or []:
                if isinstance(constraint.kind, exp.DefaultColumnConstraint):
                    defaults[(table['name'], col.name)] = canonical(constraint.kind.this.sql(dialect='postgres'))
    for item in manifest['dump']['control_statements']:
        kind = item['kind']; text = item['sql']
        if kind == 'constraint':
            tree = sqlglot.parse_one(text, read='postgres'); table = tree.this.name
            constraint = tree.args['actions'][0].expressions[0]; name = constraint.name
            definition = constraint.expressions[0]
            constraints[(table, name)] = canonical(text)
            if isinstance(definition, exp.PrimaryKey):
                columns = [x.name for x in definition.expressions]; primary[table] = columns
                indexes[name] = canonical('CREATE UNIQUE INDEX '+quote(name)+' ON '+table_sql(table)+' USING btree ('+', '.join(quote(x) for x in columns)+')')
            else: require(isinstance(definition, exp.ForeignKey), 'Unexpected constraint kind')
        elif kind == 'index':
            tree = sqlglot.parse_one(text, read='postgres'); indexes[tree.this.name] = canonical(text)
        elif kind == 'column_default':
            tree = sqlglot.parse_one(text, read='postgres'); col = tree.args['actions'][0]
            defaults[(tree.this.name, col.name)] = canonical(col.args['default'].sql(dialect='postgres'))
        elif kind == 'sequence_owned_by':
            match = re.fullmatch(r'ALTER SEQUENCE public\.('+IDENT+r') OWNED BY public\.('+IDENT+r')\.('+IDENT+r');', text)
            require(match, 'Unsupported sequence ownership')
            sequence, table, column = [unquote(x) for x in match.groups()]; ownership[sequence] = (table, column)
        elif kind == 'sequence_value':
            match = re.fullmatch(r"SELECT pg_catalog\.setval\('public\.([^']+)', ([0-9]+), (true|false)\);", text)
            require(match, 'Unsupported sequence value')
            values[match[1]] = (int(match[2]), match[3] == 'true')
        elif kind == 'create_sequence':
            normalized = ' '.join(text.split())
            require(re.fullmatch(r'CREATE SEQUENCE public\.'+IDENT+r' START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;', normalized), 'Unsupported sequence definition')
    require(set(ownership) == set(values) == set(manifest['dump']['sequences']), 'Sequence expectations incomplete')
    return {'constraints': constraints, 'indexes': indexes, 'defaults': defaults, 'primary': primary,
            'ownership': ownership, 'values': values}


def verify_structure(conn, manifest: dict) -> dict:
    expected = expectations(manifest); owner = manifest['target']['import_role']
    # pg_get_* must qualify public references, independently of session visibility.
    conn.execute('SET LOCAL search_path TO pg_catalog')
    require_no_executable_objects(conn)
    expected_objects = sorted([(t['name'], 'r') for t in manifest['dump']['tables']] +
        [(s, 'S') for s in manifest['dump']['sequences']] + [(i, 'i') for i in expected['indexes']])
    require(object_inventory(conn) == expected_objects, 'Target relation/index/sequence set differs')
    columns = {}; constraints = {}; indexes = {}; sequences = {}
    for table in manifest['dump']['tables']:
        name = table['name']
        state = conn.execute("""SELECT pg_get_userbyid(c.relowner),c.relrowsecurity,c.relforcerowsecurity,c.relpersistence,
            c.relkind::text,c.relispartition FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relname=%s""", (name,)).fetchone()
        require(state == (owner, False, False, 'p', 'r', False), 'Unexpected table owner/RLS/kind: '+name)
        rows = conn.execute("""SELECT a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,
            a.attidentity::text,a.attgenerated::text,pg_get_expr(d.adbin,d.adrelid)
            FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace
            LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
            WHERE n.nspname='public' AND c.relname=%s AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum""", (name,)).fetchall()
        observed = [(r[0], r[1], r[2], r[3], r[4], canonical(r[5]) if r[5] is not None else None) for r in rows]
        wanted = [(c['name'], TYPE_NAMES[c['postgres_type']], c['not_null'] or c['name'] in expected['primary'].get(name, []),
                   '', '', expected['defaults'].get((name, c['name']))) for c in table['columns']]
        require(observed == wanted, 'Columns/defaults/order/nullability differ: '+name)
        columns[name] = observed
    rows = conn.execute("""SELECT c.relname,k.conname,pg_get_constraintdef(k.oid),k.convalidated,
        k.condeferrable,k.condeferred,k.contype::text FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY 1,2""").fetchall()
    for table, name, definition, validated, deferrable, deferred, kind in rows:
        require(validated and not deferrable and not deferred and kind in ('p', 'f'), 'Constraint flags differ')
        constraints[(table, name)] = canonical('ALTER TABLE ONLY '+table_sql(table)+' ADD CONSTRAINT '+quote(name)+' '+definition)
    require(constraints == expected['constraints'], 'Constraint definitions differ')
    rows = conn.execute("""SELECT i.relname,pg_get_indexdef(i.oid),x.indisvalid,x.indisready,
        pg_get_userbyid(i.relowner) FROM pg_index x JOIN pg_class i ON i.oid=x.indexrelid
        JOIN pg_namespace n ON n.oid=i.relnamespace WHERE n.nspname='public' ORDER BY 1""").fetchall()
    for name, definition, valid, ready, index_owner in rows:
        require(valid and ready and index_owner == owner, 'Index validity/owner differs')
        indexes[name] = canonical(definition)
    require(indexes == expected['indexes'], 'Index definitions differ')
    for name in manifest['dump']['sequences']:
        spec = conn.execute("""SELECT format_type(s.seqtypid,NULL),s.seqstart,s.seqincrement,s.seqmax,s.seqmin,
            s.seqcache,s.seqcycle,pg_get_userbyid(c.relowner) FROM pg_sequence s JOIN pg_class c ON c.oid=s.seqrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname=%s""", (name,)).fetchone()
        require(spec == ('bigint', 1, 1, 9223372036854775807, 1, 1, False, owner), 'Sequence specification differs: '+name)
        link = conn.execute("""SELECT t.relname,a.attname,d.deptype::text FROM pg_depend d
            JOIN pg_class s ON s.oid=d.objid JOIN pg_namespace n ON n.oid=s.relnamespace
            JOIN pg_class t ON t.oid=d.refobjid JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=d.refobjsubid
            WHERE d.classid='pg_class'::regclass AND d.refclassid='pg_class'::regclass
            AND n.nspname='public' AND s.relname=%s AND s.relkind='S' AND d.deptype='a'""", (name,)).fetchall()
        require(link == [(*expected['ownership'][name], 'a')], 'Sequence ownership link differs: '+name)
        value = conn.execute('SELECT last_value,is_called FROM '+table_sql(name)).fetchone()
        require(value == expected['values'][name], 'Sequence current value differs: '+name)
        sequences[name] = {'definition': list(spec), 'ownership': list(link[0]), 'value': list(value)}
    structure = {'columns': columns, 'constraints': [{'table': k[0], 'name': k[1], 'sql': v} for k, v in sorted(constraints.items())],
                 'indexes': indexes, 'sequences': sequences}
    return {'status': 'passed', 'catalog_version': digest_json(structure),
            'table_count': len(columns), 'column_count': sum(len(v) for v in columns.values()),
            'constraint_count': len(constraints), 'index_count': len(indexes), 'sequence_count': len(sequences),
            'verified_structure': structure}
