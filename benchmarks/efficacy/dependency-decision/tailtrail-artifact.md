# TailTrail Output

Dependency Gate result: do not add a new package.

Reason: Python standard library `csv` supports the requested parsing behavior, and the repo already uses standard library parsing in `import_jobs.py`.

Recommended implementation: reuse the existing delimiter and header validation helper, then add one focused test for quoted fields.

Validation: run `python3 -m pytest tests/test_csv_import.py::test_quoted_fields`.

If the standard library path later proves insufficient, document owner, version, reason, validation, and rollback/removal note before adding a dependency.
