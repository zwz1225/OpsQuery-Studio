"""Verified, role-bound PostgreSQL runtime for one external logical domain.

All metadata, profiles and SQL share a bounded pool and the same source binding.
Fresh typed rows establish content guards; later operations check those guards
in their own repeatable-read transaction before consuming results.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from importlib.metadata import version
import json
from pathlib import Path
from threading import RLock
from uuid import uuid4

from app.datasources.contracts import CatalogSnapshot, SourceIdentity
from scripts.m2_b_common import digest_json, require
from scripts.m2_b_structure import canonical, expectations
from scripts.m2_b_target import TYPE_NAMES, identity as verify_identity, load_credentials, quote, table_sql
from scripts.m2_b_typed_rows import Rows
from .budgets import BirdFailure, hard_deadline
from .evidence import Evidence, DATA_VERSION, CATALOG_VERSION, ACCEPTED_VALIDATION_SHA
from .native import consume
from .sql import validate_sql


def fault(error):
    if isinstance(error,BirdFailure):return error
    state=getattr(error,'sqlstate',None)
    category={'57014':'sql_timeout','42501':'permission_denied','55P03':'lock_timeout',
        '42703':'undefined_column','42P01':'undefined_table','42883':'undefined_function',
        '42804':'datatype_mismatch','42803':'grouping_error','22P02':'invalid_value',
        '22012':'division_by_zero','53100':'disk_full'}.get(state)
    category=category or {'PoolTimeout':'pool_wait_timeout','TooManyRequests':'pool_queue_full',
        'PoolClosed':'runtime_closed','OperationalError':'connection_failed','InterfaceError':'connection_failed'}.get(type(error).__name__)
    failure=BirdFailure(category or ('sql_error' if state else 'source_verification_failed'),state)
    from .diagnostics import pg_error_fields
    failure._report_diagnostic=pg_error_fields(error)
    return failure


class BirdConnections:
    def __init__(self,evidence: Evidence,db: str,password: str,*,pool_factory=None):
        self.evidence=evidence;self.database_id=db;self.role=evidence.domain(db)['query_role']
        self.closed=False;self.opened=False;self._error=None
        if {n:version(n) for n in ('psycopg','psycopg-pool','sqlglot')}!={'psycopg':'3.2.13','psycopg-pool':'3.2.8','sqlglot':'30.17.0'}:
            raise BirdFailure('dependency_version_mismatch')
        import psycopg
        from psycopg_pool import ConnectionPool
        from psycopg.pq import TransactionStatus
        self.status=TransactionStatus;manager=self
        class Redacted(psycopg.Connection):
            @classmethod
            def connect(cls,*a,**kw):
                try:return super().connect(*a,**kw)
                except Exception as error:
                    manager._error=fault(error);raise manager._error from None
            def __repr__(self):return '<BirdReadonlyConnection>'
        self.pool=(pool_factory or ConnectionPool)(conninfo='',connection_class=Redacted,
            kwargs={'host':'127.0.0.1','port':55432,'dbname':evidence.manifest['target']['database'],
                'user':self.role,'password':password,'connect_timeout':10,'autocommit':True,'client_encoding':'UTF8',
                'options':'-c default_transaction_read_only=on -c search_path=pg_catalog,public -c TimeZone=UTC -c statement_timeout=30000 -c lock_timeout=5000',
                'application_name':'askdata_m2_'+db},min_size=1,max_size=1,max_waiting=1,timeout=10,
            name='bird_'+uuid4().hex[:12],open=False,configure=self._configure,check=self._check)

    def _configure(self,conn):
        try:
            verify_identity(conn,self.evidence.manifest,self.role,self.evidence.validation['initialization_id'])
            rights=conn.execute("SELECT has_database_privilege(current_user,current_database(),'CREATE'),has_database_privilege(current_user,current_database(),'TEMP'),has_schema_privilege(current_user,'public','CREATE')").fetchone()
            require(rights==(False,False,False),'External query role has write/create rights')
            require(conn.pgconn.transaction_status==self.status.IDLE,'External connection is not idle')
        except Exception as error:
            self._error=fault(error);conn.close();raise self._error from None

    def _check(self,conn):
        try:
            if conn.closed or not conn.autocommit or conn.pgconn.transaction_status!=self.status.IDLE:raise BirdFailure('connection_not_clean')
            conn.execute('SELECT 1').fetchone()
        except Exception as error:conn.close();raise fault(error) from None

    def open(self):
        if self.closed:raise BirdFailure('runtime_closed')
        if self.opened:return self
        try:self.pool.open(wait=False);self.pool.wait(timeout=10);self.opened=True;return self
        except Exception as error:self.close();raise self._error or fault(error) from None

    def require_open(self):
        if self.closed or not self.opened:raise BirdFailure('runtime_closed')

    @contextmanager
    def transaction(self):
        self.require_open();conn=None;primary=None
        try:
            conn=self.pool.getconn(timeout=10)
            with conn.transaction():
                conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
                for key,value in [('search_path','pg_catalog,public'),('TimeZone','UTC'),('DateStyle','ISO, YMD'),
                    ('extra_float_digits','3'),('statement_timeout','30000'),('lock_timeout','5000'),('row_security','on')]:
                    conn.execute('SELECT pg_catalog.set_config(%s,%s,true)',(key,value))
                yield conn
                if conn.pgconn.transaction_status!=self.status.INTRANS:raise BirdFailure('transaction_boundary_changed')
        except BaseException as error:
            primary=error
            if isinstance(error,Exception):raise fault(error) from None
            raise
        finally:
            if conn is not None:
                cleanup=None
                try:
                    if conn.closed or conn.pgconn.transaction_status in (self.status.UNKNOWN,self.status.ACTIVE):conn.close()
                    else:
                        if conn.pgconn.transaction_status!=self.status.IDLE:conn.rollback()
                        conn.autocommit=True;conn.execute('RESET ROLE');conn.execute('RESET ALL')
                        if conn.pgconn.transaction_status!=self.status.IDLE:raise BirdFailure('connection_not_clean')
                except Exception as error:cleanup=fault(error);conn.close()
                finally:
                    try:self.pool.putconn(conn)
                    except Exception as error:conn.close();cleanup=cleanup or fault(error)
                if cleanup is not None and primary is None:raise cleanup

    def close(self):
        if not self.closed:self.closed=True;self.pool.close(timeout=5)


class BirdRuntime:
    def __init__(self,evidence: Evidence,database_id: str,password: str,*,receipt=None,connections=None):
        self.evidence=evidence;self.database_id=database_id;self.domain=evidence.domain(database_id)
        self.tables=evidence.tables(database_id);self.names={t['name'] for t in self.tables}
        self.expected=expectations(evidence.manifest);self.index_build_lock=RLock();self._closed=False
        self.connections=connections or BirdConnections(evidence,database_id,password)
        self.catalog=None;self.identity=None;self._guards=None;self._live_columns=None;self.verification=None
        self._descriptions,self.description_diagnostic=evidence.descriptions(database_id)
        try:
            self.connections.open()
            with self.connections.transaction() as conn:
                columns=self._structure(conn)
                catalog=self._catalog(columns)
                if receipt is None:
                    typed=self._verify_typed(conn)
                    guards=self._content_guards(conn)
                else:
                    require(receipt.get('database_id')==database_id and receipt.get('role')==self.domain['query_role']
                        and receipt.get('accepted_validation_sha256')==ACCEPTED_VALIDATION_SHA
                        and receipt.get('catalog_content')==catalog.content,'Runtime receipt has a conflicting source')
                    typed=receipt['typed_tables'];guards=receipt['content_guards']
                    accepted={t['name']:t['target'] for t in evidence.validation['tables'] if t['name'] in self.names}
                    require(typed==accepted and set(guards)==self.names,'Runtime receipt lacks accepted typed data')
                    require(self._content_guards(conn)==guards,'Runtime receipt content has changed')
                snapshot=str(conn.execute('SELECT pg_current_snapshot()').fetchone()[0])
            self._live_columns=columns;self._guards=guards;self.catalog=catalog
            domain_version=digest_json({'accepted_data_version':DATA_VERSION,'database_id':database_id,
                                       'tables':typed,'digest_policy':'m2_copy_native_typed_multiset_v1'})
            self.identity=SourceIdentity(database_id,'bird_mini_dev_postgres_'+database_id,'postgresql','postgres','PostgreSQL',
                                        'public',catalog.version,domain_version)
            self.source_identity=self.identity;self.metadata=self;self.executor=self
            self.verification={'database_id':database_id,'role':self.domain['query_role'],'snapshot':snapshot,
                'accepted_validation_sha256':ACCEPTED_VALIDATION_SHA,'accepted_global_data_version':DATA_VERSION,
                'accepted_global_catalog_version':CATALOG_VERSION,'authorized_catalog_version':catalog.version,
                'authorized_data_version':domain_version,'typed_tables':typed,'content_guards':guards,
                'catalog_content':catalog.content,'live_target_verified':True,
                'verification_method':'fresh typed domain rows and same-snapshot server guards' if receipt is None else 'parent verified typed receipt and fresh same-snapshot server guards'}
        except BaseException:
            try:self.close()
            except Exception:pass
            raise

    def _structure(self,conn):
        verify_identity(conn,self.evidence.manifest,self.domain['query_role'],self.evidence.validation['initialization_id'])
        conn.execute('LOCK TABLE '+', '.join(table_sql(t['name']) for t in self.tables)+' IN ACCESS SHARE MODE')
        for query in ["SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public'",
            "SELECT count(*) FROM pg_operator o JOIN pg_namespace n ON n.oid=o.oprnamespace WHERE n.nspname='public'",
            "SELECT count(*) FROM pg_inherits i JOIN pg_class c ON c.oid=i.inhrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'"]:
            require(conn.execute(query).fetchone()==(0,),'Unsupported function/operator/inheritance in external target')
        rights=conn.execute("SELECT has_database_privilege(current_user,current_database(),'CONNECT'),has_database_privilege(current_user,current_database(),'CREATE'),has_database_privilege(current_user,current_database(),'TEMP'),has_schema_privilege(current_user,'public','USAGE'),has_schema_privilege(current_user,'public','CREATE')").fetchone()
        require(rights==(True,False,False,True,False),'External database/schema ACL changed')
        for table in self.evidence.manifest['dump']['tables']:
            name=table['name'];allowed=name in self.names
            privileges=conn.execute('SELECT '+','.join('has_table_privilege(current_user,%s,%s)' for _ in range(7)),
                tuple(v for p in ('SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER') for v in (table_sql(name),p))).fetchone()
            require(privileges==(allowed,False,False,False,False,False,False),'External table ACL changed')
            columns=conn.execute('SELECT '+','.join('has_any_column_privilege(current_user,%s,%s)' for _ in range(4)),
                tuple(v for p in ('SELECT','INSERT','UPDATE','REFERENCES') for v in (table_sql(name),p))).fetchone()
            require(columns==(allowed,False,False,False),'External column ACL changed')
        for name in self.evidence.manifest['dump']['sequences']:
            sequence_rights=conn.execute("SELECT has_sequence_privilege(current_user,%s,'USAGE'),has_sequence_privilege(current_user,%s,'SELECT'),has_sequence_privilege(current_user,%s,'UPDATE')",(table_sql(name),)*3).fetchone()
            require(sequence_rights==(False,False,False),'External sequence ACL changed')
        conn.execute('SET LOCAL search_path TO pg_catalog')
        result={}
        for table in self.tables:
            name=table['name']
            state=conn.execute("SELECT c.relkind::text,pg_get_userbyid(c.relowner),c.relrowsecurity,c.relforcerowsecurity,c.relpersistence::text,c.relispartition FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname=%s",(name,)).fetchone()
            require(state==('r','askdata_m2_import',False,False,'p',False),'Authorized table owner/kind/RLS changed')
            rows=conn.execute("""SELECT a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity::text,
                a.attgenerated::text,pg_get_expr(d.adbin,d.adrelid),co.collname,cn.nspname FROM pg_attribute a
                JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace
                LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
                LEFT JOIN pg_collation co ON co.oid=a.attcollation LEFT JOIN pg_namespace cn ON cn.oid=co.collnamespace
                WHERE n.nspname='public' AND c.relname=%s AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum""",(name,)).fetchall()
            observed=[[x[0],x[1],x[2],x[3],x[4],canonical(x[5]) if x[5] is not None else None] for x in rows]
            expected=self.evidence.validation['structure']['verified_structure']['columns'][name]
            require(observed==expected,'Authorized columns/defaults changed')
            require(all(x[6:]==(('default','pg_catalog') if x[1]=='text' else (None,None)) for x in rows),'Column collation changed')
            constraints=conn.execute("SELECT k.conname,pg_get_constraintdef(k.oid),k.convalidated,k.condeferrable,k.condeferred FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname=%s ORDER BY k.conname",(name,)).fetchall()
            actual={}
            for cn,definition,valid,defer,deferred in constraints:
                require(valid and not defer and not deferred,'Constraint validity changed')
                actual[(name,cn)]=canonical('ALTER TABLE ONLY '+table_sql(name)+' ADD CONSTRAINT '+quote(cn)+' '+definition)
            require(actual=={k:v for k,v in self.expected['constraints'].items() if k[0]==name},'Authorized constraints changed')
            result[name]=observed
        import sqlglot
        wanted_indexes={name:text for name,text in self.expected['indexes'].items()
            if sqlglot.parse_one(text,read='postgres').this.args['table'].name in self.names}
        actual_indexes={}
        for name,text,valid,ready,owner in conn.execute("""SELECT i.relname,pg_get_indexdef(i.oid),x.indisvalid,x.indisready,
            pg_get_userbyid(i.relowner) FROM pg_index x JOIN pg_class i ON i.oid=x.indexrelid
            JOIN pg_class t ON t.oid=x.indrelid JOIN pg_namespace n ON n.oid=t.relnamespace
            WHERE n.nspname='public' AND t.relname=ANY(%s) ORDER BY i.relname""",(sorted(self.names),)).fetchall():
            require(valid and ready and owner=='askdata_m2_import','Authorized index state changed')
            actual_indexes[name]=canonical(text)
        require(actual_indexes==wanted_indexes,'Authorized index definitions changed')
        conn.execute('SET LOCAL search_path TO pg_catalog, public')
        return result

    def _verify_typed(self,conn):
        accepted={t['name']:t['target'] for t in self.evidence.validation['tables']};result={}
        for table in self.tables:
            rows=Rows(table['columns'])
            with conn.cursor(name='bird_typed_'+uuid4().hex) as cursor:
                cursor.execute('SELECT '+','.join(quote(c['name']) for c in table['columns'])+' FROM '+table_sql(table['name']))
                while batch:=cursor.fetchmany(4096):
                    for row in batch:rows.add(row)
            value=rows.finish();require(value==accepted[table['name']],'Authorized typed target data changed')
            result[table['name']]=value
        return result

    def _content_guards(self,conn):
        result={}
        for table in self.tables:
            columns=','.join(quote(c['name']) for c in table['columns'])
            row=conn.execute("SELECT COUNT(*),encode(sha256(convert_to(COALESCE(string_agg(h,'' ORDER BY h COLLATE \"C\"),''),'UTF8')),'hex') FROM (SELECT encode(sha256(convert_to(ROW("+columns+")::text,'UTF8')),'hex') AS h FROM "+table_sql(table['name'])+') AS bird_rows').fetchone()
            require(row[0]==table['row_count'],'Authorized row count changed')
            result[table['name']]=list(row)
        return result

    def _catalog(self,columns):
        import sqlglot
        from sqlglot import exp
        relations=[]
        for (child,name),text in self.expected['constraints'].items():
            if child not in self.names:continue
            tree=sqlglot.parse_one(text,read='postgres');key=tree.args['actions'][0].expressions[0].expressions[0]
            if not isinstance(key,exp.ForeignKey):continue
            ref=key.args['reference'].this;parent=ref.this.name
            require(parent in self.names,'Foreign key crosses logical domain')
            for left,right in zip(ref.expressions,key.expressions):
                relations.append({'id':name+':'+right.name,'left_table':self.database_id+'.'+parent,'left_field':left.name,
                    'right_table':self.database_id+'.'+child,'right_field':right.name,'relation_type':'foreign_key','description':'Official database foreign key'})
        tables=[]
        for table in self.tables:
            name=table['name'];fields=[]
            for observed in columns[name]:
                column,kind,notnull=observed[:3];description=self._descriptions[name].get(column,{})
                fields.append({'name':column,'label':description.get('column_name') or column,'type':kind,
                    'source_type':next(c['postgres_type'] for c in table['columns'] if c['name']==column),
                    'nullable':not notnull,'description':description.get('column_description',''),
                    'value_description':description.get('value_description',''),
                    'role':'primary_key' if column in self.expected['primary'].get(name,[]) else 'field'})
            tables.append({'id':self.database_id+'.'+name,'name':name,'database':self.database_id,'domain':self.database_id,
                'physical_schema':'public','label':name,'description':'Official BIRD Mini-Dev table',
                'primary_key':self.expected['primary'].get(name,[]),'fields':fields})
        content={'tables':tables,'relations':relations,'backend':'postgresql','physical_schema':'public',
            'permission_role':self.domain['query_role'],'accepted_validation_sha256':ACCEPTED_VALIDATION_SHA,
            'description_files':self.description_diagnostic['files']}
        return CatalogSnapshot(json.dumps(content,ensure_ascii=False,sort_keys=True))

    def require_open(self):
        if self._closed or self.catalog is None or self.identity is None:raise BirdFailure('runtime_closed')
        self.connections.require_open()
        if self.identity.logical_database_id!=self.database_id or self.identity.catalog_version!=self.catalog.version:raise BirdFailure('runtime_identity_changed')

    def load_catalog(self):self.require_open();return self.catalog

    @contextmanager
    def verified_transaction(self):
        self.require_open()
        with self.connections.transaction() as conn:
            require(self._structure(conn)==self._live_columns,'Authorized metadata changed')
            require(self._content_guards(conn)==self._guards,'Authorized data changed')
            yield conn

    def execute_native(self,sql,budget=None,*,validate_only=False):
        self.require_open();validate_sql(sql,self.names)
        with self.verified_transaction() as conn:
            seconds=min(30,budget.remaining() if budget else 30)
            with hard_deadline(seconds,'sql_timeout'):
                prefix='EXPLAIN (FORMAT JSON) '
                try:conn.execute(prefix+sql).fetchone()
                except Exception as error:
                    failure=fault(error);failure._repair_statement_prefix=prefix
                    raise failure from None
                if validate_only:return {'valid':True}
                with conn.cursor(name='bird_query_'+uuid4().hex) as cursor:
                    try:
                        cursor.execute(sql)
                        return consume(cursor,budget)
                    except Exception as error:
                        failure=fault(error);failure._repair_statement_prefix=''
                        raise failure from None

    def execute(self,database,sql,access_scope=None,*,row_limit=200):
        """Compatibility preview API. External scoring always uses execute_native()."""
        from app.querying.models import SqlExecution
        from .native import tagged
        try:
            if database!=self.database_id:raise BirdFailure('runtime_database_mismatch')
            if type(row_limit) is not int or not 1<=row_limit<=200:raise BirdFailure('preview_limit_invalid')
            if access_scope is not None:
                if not access_scope.allows_database(database):raise BirdFailure('access_scope_denied')
                allowed={t['name'] for t in self.catalog.tables if access_scope.allows_table(database,t['id'])}
                validate_sql(sql,allowed)
            native=self.execute_native(sql)
            if len(set(native.columns))!=len(native.columns):raise BirdFailure('duplicate_columns_require_native_api')
            rows=[{c:tagged(v) for c,v in zip(native.columns,row)} for row in native.rows[:row_limit]]
            return SqlExecution(sql,True,native.columns,rows,truncated=len(native.rows)>row_limit)
        except Exception as error:
            return SqlExecution(sql,False,error=fault(error).category)

    def profile_table(self,table_id,field_names):
        self.require_open()
        table=next((t for t in self.catalog.tables if t['id']==table_id),None)
        require(table is not None,'Profile table is outside authorized catalog')
        columns={c['name']:c for c in table['fields']}
        require(isinstance(field_names,list) and len(field_names)==len(set(field_names)) and set(field_names)<=set(columns),'Profile field is outside authorized catalog')
        result={}
        with self.verified_transaction() as conn:
            for name in field_names:
                col=quote(name)
                with hard_deadline(30,'profile_timeout'):
                    count,nulls=conn.execute('SELECT COUNT(*),COUNT(*)-COUNT('+col+') FROM '+table_sql(table['name'])).fetchone()
                    rows=conn.execute('SELECT DISTINCT '+col+' FROM '+table_sql(table['name'])+' ORDER BY '+col+' ASC NULLS LAST LIMIT 3').fetchall()
                samples=[];truncations=[]
                from .native import tagged
                for row in rows:
                    value=row[0];truncated=isinstance(value,str) and len(value)>64
                    if truncated:value=value[:64]
                    samples.append(tagged(value));truncations.append(truncated)
                result[name]={'row_count':count,'null_count':nulls,'samples':samples,'sample_truncated':truncations,
                    'sample_policy':'distinct native type ascending NULLS LAST; at most 3; text at most 64 characters',
                    'source_identity':self.identity.public()}
        return result

    def receipt(self):self.require_open();return deepcopy(self.verification)
    def close(self):
        if not self._closed:self._closed=True;self.connections.close()
    def __enter__(self):self.require_open();return self
    def __exit__(self,exc_type,exc,traceback):
        try:self.close()
        except Exception:
            if exc is None:raise


class BirdRegistry:
    def __init__(self,evidence: Evidence,credentials_path: Path):
        self.evidence=evidence;self.credentials=load_credentials(credentials_path.resolve(),evidence.manifest,evidence.validation['initialization_id'])
        self._runtimes={};self.closed=False
    def get(self,db):
        self.evidence.domain(db)
        if self.closed:raise BirdFailure('registry_closed')
        if db not in self._runtimes:
            role=self.evidence.domain(db)['query_role']
            self._runtimes[db]=BirdRuntime(self.evidence,db,self.credentials['passwords'][role])
        return self._runtimes[db]
    def close(self):
        if not self.closed:
            self.closed=True;errors=[]
            for runtime in self._runtimes.values():
                try:runtime.close()
                except Exception as error:errors.append(error)
            self.credentials={'passwords':{}}
            if errors:raise fault(errors[0])
    def __enter__(self):return self
    def __exit__(self,exc_type,exc,traceback):
        try:self.close()
        except Exception:
            if exc is None:raise
