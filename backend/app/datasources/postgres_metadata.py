"""Controlled live PostgreSQL source verification and business catalog assembly.

Initial full typed hashes establish the accepted M1 B data version. Each later
operation checks all table contents using a server-side SHA256 multiset guard
in the SAME repeatable-read transaction as its query/profile. No statistics or
row-count-only shortcut is treated as proof of unchanged data.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import json
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from .contracts import CatalogSnapshot, SourceIdentity
from .postgres_config import digest, load_recorded_source, read_record
from .postgres_connections import PostgresConnectionError
from .row_digest import typed_row_hash, multiset_hash
from .values import json_value

BUSINESS_CATALOG_VERSION = "68bc24f95eef81021c03a8d8819b00c43fc04fbaf13fbbf295268ebd857e60c2"
SOURCE_TYPES = {"text": "VARCHAR", "bigint": "BIGINT", "double precision": "DOUBLE",
                "date": "DATE", "timestamp without time zone": "TIMESTAMP"}
PRIVILEGES = ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]


def require(condition, category):
    if not condition:
        raise PostgresConnectionError("source_" + category)


def quote(identifier):
    return '"' + identifier.replace('"', '""') + '"'


class PostgresMetadataProvider:
    def __init__(self, connections, expected_tables, annotations, target, physical_version):
        self.connections = connections
        self.config = connections.config
        self._expected = deepcopy(expected_tables)
        self._annotations = annotations
        self._target = deepcopy(target)
        self._physical_version = physical_version
        self._catalog = None
        self._guards = None
        self.identity = None
        self.verification = None

    @classmethod
    def from_recorded_source(cls, connections, annotations_path: Path):
        recorded = load_recorded_source(connections.config)
        report, sha = read_record(connections.config.validation_report_path, "PG validation evidence")
        require(sha == recorded.validation_report_sha256, "evidence_changed")
        payload, _ = read_record(annotations_path, "Business annotations")
        annotations = CatalogSnapshot(json.dumps({"tables": payload.get("tables", []),
            "relations": payload.get("relations", [])}, ensure_ascii=False, sort_keys=True))
        require(annotations.version == BUSINESS_CATALOG_VERSION, "annotations_changed")
        return cls(connections, report["validation"]["tables"], annotations,
                   report["target"], recorded.physical_schema_version)

    def _table(self, name):
        return quote(self.config.schema) + "." + quote(name)

    def _structure(self, conn):
        schema = self.config.schema
        conn.execute("LOCK TABLE " + ", ".join(self._table(t["name"]) for t in self._expected) + " IN ACCESS SHARE MODE")
        # Scope all catalog discovery to this physical schema, including object
        # kinds the current importer does not support (views, FDW, partitions).
        objects = conn.execute("""SELECT c.relname,c.relkind::text,
            pg_get_userbyid(c.relowner),c.relrowsecurity,c.relforcerowsecurity,
            c.relpersistence::text,c.relispartition
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname=%s AND c.relkind IN ('r','p','v','m','f','S') ORDER BY c.relname""", (schema,)).fetchall()
        expected_objects = sorted((t["name"], "r", "askdata_import", False, False, "p", False) for t in self._expected)
        require(objects == expected_objects, "table_set_owner_or_rls_changed")
        # Hold relation locks until the operation ends, preventing concurrent
        # DDL during metadata/content verification and result consumption.
        require(conn.execute("""SELECT EXISTS(SELECT 1 FROM pg_inherits i
            JOIN pg_class c ON c.oid=i.inhrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s)
            OR EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=%s)
            OR EXISTS(SELECT 1 FROM pg_operator o JOIN pg_namespace n ON n.oid=o.oprnamespace WHERE n.nspname=%s)""",
            (schema, schema, schema)).fetchone() == (False,), "unsupported_inheritance_function_or_operator")
        env = conn.execute("""SELECT current_database(),current_user,
            current_setting('server_version_num')::int,current_setting('server_encoding'),
            current_setting('TimeZone'),d.datcollate,d.datctype,d.datlocprovider::text,
            r.rolcanlogin,r.rolsuper,r.rolcreatedb,r.rolcreaterole,r.rolreplication,r.rolbypassrls,
            pg_has_role(current_user,'askdata_import','MEMBER'),
            (SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname=%s)
            FROM pg_database d, pg_roles r WHERE d.datname=current_database() AND r.rolname=current_user""", (schema,)).fetchone()
        require(env is not None and env[:2] == (self.config.database, self.config.user)
            and 160000 <= env[2] < 170000 and env[3:8] == ("UTF8", "UTC", "C", "C", "c")
            and env[8:] == (True, False, False, False, False, False, False, "askdata_import"), "identity_or_role_changed")
        grants = conn.execute("""SELECT has_database_privilege(current_database(),'CONNECT'),
            has_database_privilege(current_database(),'CREATE'),has_database_privilege(current_database(),'TEMP'),
            has_schema_privilege(%s,'USAGE'),has_schema_privilege(%s,'CREATE'),has_schema_privilege('public','CREATE')""",
            (schema, schema)).fetchone()
        require(grants == (True, False, False, True, False, False), "database_schema_acl_changed")
        actual = []
        for expected in self._expected:
            name = expected["name"]
            rows = conn.execute("""SELECT a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,
                a.attidentity::text,a.attgenerated::text,a.atthasdef,co.collname,cn.nspname
                FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
                JOIN pg_namespace n ON n.oid=c.relnamespace
                LEFT JOIN pg_collation co ON co.oid=a.attcollation
                LEFT JOIN pg_namespace cn ON cn.oid=co.collnamespace
                WHERE n.nspname=%s AND c.relname=%s AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum""", (schema, name)).fetchall()
            columns = [dict(zip(["name", "postgresql_type", "not_null", "identity", "generated", "has_default"], r[:6])) for r in rows]
            require(columns == expected["columns"], "columns_changed")
            require(all(r[6:] == (("default", "pg_catalog") if r[1] == "text" else (None, None)) for r in rows), "column_collation_changed")
            keys = conn.execute("""SELECT a.attname FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
                JOIN pg_namespace n ON n.oid=c.relnamespace
                CROSS JOIN LATERAL unnest(k.conkey) WITH ORDINALITY AS kc(attnum,ord)
                JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=kc.attnum
                WHERE n.nspname=%s AND c.relname=%s AND k.contype='p' ORDER BY kc.ord""", (schema, name)).fetchall()
            primary = [r[0] for r in keys]
            require(primary == expected["primary_key"], "primary_key_changed")
            constraints = conn.execute("""SELECT k.contype::text,k.convalidated,k.condeferrable,k.condeferred
                FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname=%s AND c.relname=%s ORDER BY k.conname""", (schema, name)).fetchall()
            require(constraints == [("p", True, False, False)], "constraints_changed")
            indexes = conn.execute("""SELECT i.indisprimary,i.indisunique,i.indisvalid,i.indisready
                FROM pg_index i JOIN pg_class c ON c.oid=i.indrelid JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname=%s AND c.relname=%s""", (schema, name)).fetchall()
            require(indexes == [(True, True, True, True)], "indexes_changed")
            access = conn.execute("SELECT " + ",".join("has_table_privilege(current_user,%s,%s)" for _ in PRIVILEGES),
                tuple(v for p in PRIVILEGES for v in (self._table(name), p))).fetchone()
            require(access == (True, False, False, False, False, False, False), "table_acl_changed")
            # Table grants alone do not detect column-level write grants.
            column_write = conn.execute("SELECT " + ",".join("has_any_column_privilege(current_user,%s,%s)" for _ in range(3)),
                tuple(v for p in ["INSERT", "UPDATE", "REFERENCES"] for v in (self._table(name), p))).fetchone()
            require(column_write == (False, False, False), "column_acl_changed")
            actual.append({"name": name, "columns": columns, "primary_key": primary})
        require(digest(actual) == self._physical_version, "physical_schema_version_changed")
        return actual

    def _content_guards(self, conn):
        guards = {}
        for table in self._expected:
            require(conn.execute("SELECT COUNT(*) FROM " + self._table(table["name"])).fetchone()[0]
                == table["row_count"], "row_count_changed")
            cols = ",".join(quote(c["name"]) for c in table["columns"])
            # Hash every visible row, including NULLs, and sort row hashes to
            # retain duplicates while ignoring physical/order differences.
            row = conn.execute("SELECT COUNT(*),encode(sha256(convert_to(COALESCE("
                "string_agg(h,'' ORDER BY h COLLATE \"C\"),''),'UTF8')),'hex') FROM "
                "(SELECT encode(sha256(convert_to(ROW(" + cols + ")::text,'UTF8')),'hex') AS h FROM "
                + self._table(table["name"]) + ") AS rows_to_hash").fetchone()
            guards[table["name"]] = list(row)
        return guards

    def _typed_data(self, conn, structure):
        selected = []
        for table, observed in zip(self._expected, structure):
            fields = [{"source_type": SOURCE_TYPES[c["postgresql_type"]]} for c in table["columns"]]
            hashes, count = [], 0
            with conn.cursor(name="askdata_verify_" + uuid4().hex) as cursor:
                cursor.execute("SELECT " + ",".join(quote(c["name"]) for c in table["columns"]) + " FROM " + self._table(table["name"]))
                while batch := cursor.fetchmany(4096):
                    count += len(batch)
                    require(count <= table["row_count"], "row_count_changed")
                    hashes.extend(typed_row_hash(row, fields) for row in batch)
            value = multiset_hash(hashes)
            require(count == table["row_count"] and value == table["typed_row_multiset_sha256"], "typed_data_changed")
            logging.getLogger(__name__).info("postgres_typed_rows_verified table=%s rows=%s", table["name"], count)
            selected.append({**observed, "row_count": count, "typed_row_multiset_sha256": value})
        version = digest({"target": self._target, "tables": selected})
        require(version == self.config.verified_data_version, "data_version_changed")
        return version

    def _assemble_catalog(self, structure):
        tables = self._annotations.tables
        by_name = {t["name"]: t for t in tables}
        require(len(by_name) == len(tables) == len(structure), "annotation_table_set_changed")
        for observed in structure:
            require(observed["name"] in by_name, "annotation_table_missing")
            table = by_name[observed["name"]]
            require(table["id"] == "short_video_ops." + observed["name"] and table["database"] == "short_video_ops", "logical_id_changed")
            require([f["name"] for f in table["fields"]] == [c["name"] for c in observed["columns"]], "annotation_fields_changed")
            require(table["primary_key"] == observed["primary_key"], "annotation_primary_key_changed")
            table["physical_schema"] = self.config.schema
            for field, column in zip(table["fields"], observed["columns"]):
                require(field["source_type"] == SOURCE_TYPES[column["postgresql_type"]], "annotation_type_changed")
                field.update(postgresql_type=column["postgresql_type"], nullable=not column["not_null"])
        fields = {t["id"]: {f["name"] for f in t["fields"]} for t in tables}
        for relation in self._annotations.relations:
            require(relation["left_field"] in fields.get(relation["left_table"], set()) and
                    relation["right_field"] in fields.get(relation["right_table"], set()), "relation_endpoint_changed")
        return CatalogSnapshot(json.dumps({"tables": tables, "relations": self._annotations.relations,
            "backend": "postgresql", "physical_schema": self.config.schema}, ensure_ascii=False, sort_keys=True))

    def verify(self):
        require(self._catalog is None, "already_verified")
        with self.connections.transaction() as conn:
            structure = self._structure(conn)
            version = self._typed_data(conn, structure)
            guards = self._content_guards(conn)
            require(all(guards[t["name"]][0] == t["row_count"] for t in self._expected), "guard_row_count_changed")
            snapshot = str(conn.execute("SELECT pg_current_snapshot()").fetchone()[0])
            catalog = self._assemble_catalog(structure)
        # Publish only after successful transaction exit and connection cleanup.
        self._guards, self._catalog = guards, catalog
        self.identity = SourceIdentity("short_video_ops", self.config.source_id, "postgresql", "postgres",
            "PostgreSQL", self.config.schema, catalog.version, version)
        self.verification = {"live_target_verified": True, "snapshot": snapshot,
            "physical_schema_version": self._physical_version, "data_version": version,
            "catalog_version": catalog.version, "table_count": len(structure),
            "field_count": sum(len(t["columns"]) for t in structure),
            "row_count": sum(t["row_count"] for t in self._expected),
            "relation_count": len(catalog.relations), "full_typed_row_match_count": len(structure),
            "readonly_table_acl_match_count": len(structure),
            "guard_algorithm": "postgres-row-text-sha256-sorted-multiset-v1",
            "guard_version": digest(guards), "tables": structure,
            "database_schema_grants": [True, False, False, True, False, False],
            "readonly_column_acl_match_count": len(structure),
            "scope": "Verified transaction snapshot; every later read rechecks structure/ACL/content."}
        return self

    def load_catalog(self):
        require(self._catalog is not None, "not_verified")
        return self._catalog

    @contextmanager
    def verified_transaction(self):
        self.load_catalog()
        with self.connections.transaction() as conn:
            self._structure(conn)
            require(self._content_guards(conn) == self._guards, "content_changed")
            yield conn

    def profile_table(self, table_id, field_names):
        table = next((t for t in self.load_catalog().tables if t["id"] == table_id), None)
        require(table is not None, "unknown_profile_table")
        fields = {f["name"]: f for f in table["fields"]}
        require(isinstance(field_names, list) and all(isinstance(name, str) and name in fields for name in field_names), "unknown_profile_field")
        output = {}
        with self.verified_transaction() as conn:
            for name in field_names:
                col, sql_table = quote(name), self._table(table["name"])
                samples = conn.execute(f"SELECT DISTINCT {col} FROM {sql_table} WHERE {col} IS NOT NULL ORDER BY {col} LIMIT 5").fetchmany(5)
                if fields[name]["source_type"] in {"BIGINT", "DOUBLE"}:
                    low, high, average = conn.execute(f"SELECT MIN({col}),MAX({col}),AVG({col}) FROM {sql_table}").fetchone()
                    average = round(average, 2) if average is not None else "无"
                    text = f"最小值 {low}，最大值 {high}，平均值 {average}"
                elif fields[name]["source_type"] in {"DATE", "TIMESTAMP"}:
                    low, high = conn.execute(f"SELECT MIN({col}),MAX({col}) FROM {sql_table}").fetchone()
                    text = f"范围 {low} 至 {high}"
                else:
                    count = conn.execute(f"SELECT COUNT(DISTINCT {col}) FROM {sql_table}").fetchone()[0]
                    text = f"约 {count} 个不同值"
                output[name] = {"sample_values": [json_value(row[0]) for row in samples], "profile_text": text}
        return output
