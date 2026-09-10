"""All SQL the ETL issues, expressed in Python.

``SQL.tables`` holds DDL for every relation, each paired with a TableSpec so the
DDL and the schema validator share one source of truth. ``SQL.queries`` holds the
runtime statements: ODS load, fact build, validation, health, refresh.
"""
