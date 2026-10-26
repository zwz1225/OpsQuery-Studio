"""Stream the frozen plain PostgreSQL dump into an offline import inventory."""
from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path
import re

from scripts.m2_b_common import digest_json, require, PreparationError

IDENT = r'(?:"(?:[^"]|"")+"|[a-zA-Z_][a-zA-Z_0-9$]*)'
QUALIFIED = r'public\.(' + IDENT + r')'
MAX_LINE = 8 * 1024 * 1024


def unquote(value: str) -> str:
    return value[1:-1].replace('""','"') if value.startswith('"') else value.lower()


def identifiers(value: str) -> list[str]:
    names = re.findall(IDENT,value)
    require(re.sub(IDENT,'',value).replace(',','').strip()=='',"Unsupported COPY identifier list")
    return [unquote(x) for x in names]


class Statements:
    """Small control-SQL lexer. COPY bodies bypass this lexer completely."""
    def __init__(self):
        self.buffer=[];self.quote=None;self.bytes=0

    def feed(self,line: str) -> list[str]:
        output=[];i=0
        while i<len(line):
            c=line[i]
            if self.quote:
                self.buffer.append(c)
                if c==self.quote:
                    if i+1<len(line) and line[i+1]==c:
                        self.buffer.append(c);i+=1
                    else:self.quote=None
            elif line[i:i+2]=='--':
                break
            elif c in "'\"":
                self.quote=c;self.buffer.append(c)
            elif c==';':
                statement=''.join(self.buffer).strip()
                if statement:output.append(statement+';')
                self.buffer=[];self.bytes=0
            else:
                require(c not in '$\\' and line[i:i+2]!='/*',"Unsupported control-SQL construct")
                self.buffer.append(c)
            i+=1
        self.buffer.append('\n')
        self.bytes+=len(line)
        require(self.bytes<=2*1024*1024,"Control statement is too large")
        return output


def classify(statement: str) -> dict:
    s=' '.join(statement.split())
    patterns=[
        ('session_setting',r'^SET ([a-z_]+) = .+;$','replace_with_controlled_session'),
        ('search_path',r"^SELECT pg_catalog\.set_config\('search_path', '', false\);$",'replace_with_controlled_session'),
        ('create_table',r'^CREATE TABLE '+QUALIFIED+r' \(.+\);$','create_table'),
        ('create_sequence',r'^CREATE SEQUENCE '+QUALIFIED+r' .+;$','create_sequence'),
        ('owner',r'^ALTER TABLE '+QUALIFIED+r' OWNER TO xiaolongli;$','map_to_m2_import_role'),
        ('sequence_owned_by',r'^ALTER SEQUENCE '+QUALIFIED+r' OWNED BY public\..+;$','link_sequence'),
        ('column_default',r'^ALTER TABLE (?:ONLY )?'+QUALIFIED+r' ALTER COLUMN .+ SET DEFAULT nextval\(.+\);$','set_default'),
        ('constraint',r'^ALTER TABLE (?:ONLY )?'+QUALIFIED+r' ADD CONSTRAINT .+ (?:PRIMARY KEY|UNIQUE|FOREIGN KEY|CHECK)\b.+;$','add_constraint'),
        ('index',r'^CREATE UNIQUE INDEX .+ ON '+QUALIFIED+r' USING btree .+;$','create_index'),
        ('sequence_value',r"^SELECT pg_catalog\.setval\('public\.[^']+', [0-9]+, (?:true|false)\);$",'set_sequence_value'),
    ]
    for kind,pattern,action in patterns:
        match=re.fullmatch(pattern,s,re.S)
        if match:
            if kind=='session_setting':
                require(match.group(1) in {'statement_timeout','lock_timeout','idle_in_transaction_session_timeout',
                    'client_encoding','standard_conforming_strings','check_function_bodies','xmloption',
                    'client_min_messages','row_security','default_tablespace','default_table_access_method'},
                    "Unexpected dump session setting")
            return {'kind':kind,'import_action':action,'sql':statement,
                    'sha256':hashlib.sha256(statement.encode('utf-8')).hexdigest()}
    raise PreparationError("Unrecognized dump control statement; controlled import planning stopped")


def scan_dump(path: Path, table_domains: dict[str,str]) -> dict:
    import sqlglot
    from sqlglot import exp
    lexer=Statements();controls=[];tables={};sequences=[];overall=hashlib.sha256();line_number=0
    active=None;copy_hash=None;copy_start=0
    with path.open('rb') as stream:
        while True:
            start=stream.tell();line=stream.readline(MAX_LINE+1)
            if not line:break
            line_number+=1;overall.update(line)
            require(len(line)<=MAX_LINE,"Dump line exceeds inspection limit")
            if active is not None:
                if line.rstrip(b'\r\n')==b'\\.':
                    tables[active].update(copy_bytes_end=start,copy_payload_sha256=copy_hash.hexdigest(),
                                          copy_bytes_start=copy_start)
                    active=None;continue
                require(line.endswith(b'\n'),"COPY data row is incomplete")
                fields=line.rstrip(b'\r\n').split(b'\t')
                require(len(fields)==len(tables[active]['columns']),"COPY row field count differs from DDL")
                for i,value in enumerate(fields):
                    tables[active]['null_counts'][i]+=int(value==b'\\N')
                copy_hash.update(line);tables[active]['row_count']+=1
                continue
            text=line.decode('utf-8')
            require(not text.lstrip().startswith('\\'),"psql meta-command outside COPY is not permitted")
            for statement in lexer.feed(text):
                match=re.fullmatch(r'COPY '+QUALIFIED+r' \((.+)\) FROM stdin;',statement,re.S)
                if match:
                    name=unquote(match.group(1));names=identifiers(match.group(2))
                    require(name in tables and tables[name]['copy_sql'] is None,"Unexpected or repeated COPY table")
                    require(names==[c['name'] for c in tables[name]['columns']],"COPY column order differs from DDL")
                    require(not ''.join(lexer.buffer).strip(),"COPY header has trailing control SQL")
                    tables[name]['copy_sql']=statement
                    active=name;copy_hash=hashlib.sha256();copy_start=stream.tell()
                    continue
                item=classify(statement);controls.append(item)
                if item['kind']=='create_table':
                    tree=sqlglot.parse_one(statement,read='postgres')
                    require(isinstance(tree,exp.Create) and isinstance(tree.this,exp.Schema),"Unsupported table DDL")
                    table=tree.this.this;name=table.name
                    require(name in table_domains and name not in tables,"Unexpected or repeated physical table")
                    columns=[]
                    for col in tree.this.expressions:
                        require(isinstance(col,exp.ColumnDef),"Inline table constraint requires separate review")
                        constraints=col.args.get('constraints') or []
                        columns.append({'name':col.name,'postgres_type':col.kind.sql(dialect='postgres'),
                            'not_null':any(isinstance(x.kind,exp.NotNullColumnConstraint) for x in constraints),
                            'constraints':[x.sql(dialect='postgres') for x in constraints]})
                    require(columns and len({c['name'] for c in columns})==len(columns),"Invalid DDL columns")
                    tables[name]={'name':name,'schema':'public','database_id':table_domains[name],
                        'columns':columns,'create_sql':statement,'copy_sql':None,'row_count':0,
                        'null_counts':[0]*len(columns),'create_sql_sha256':item['sha256']}
                elif item['kind']=='create_sequence':
                    sequences.append(unquote(re.match(r'CREATE SEQUENCE '+QUALIFIED,statement).group(1)))
    require(active is None and not lexer.quote and not ''.join(lexer.buffer).strip(),"Incomplete dump control SQL or COPY block")
    require(set(tables)==set(table_domains),"DDL table set differs from logical domain schema")
    require(all(t['copy_sql'] is not None for t in tables.values()),"Table missing COPY block")
    return {'dump_sha256':overall.hexdigest(),'line_count':line_number,'tables':[tables[n] for n in sorted(tables)],
            'sequences':sequences,'control_statements':controls,'control_statement_counts':dict(Counter(c['kind'] for c in controls)),
            'row_count':sum(t['row_count'] for t in tables.values()),
            'column_count':sum(len(t['columns']) for t in tables.values()),
            'source_identity_scope':'Raw COPY bytes/null/row counts only; no live target or typed-row equality has been verified'}
