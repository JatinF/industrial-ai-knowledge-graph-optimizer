"""The SQL migration names the same tables the store creates."""

import re

from industrial_ai.paths import repo_root
from industrial_ai.storage.relational import metadata


def test_migration_tables_match_the_store() -> None:
    sql = (repo_root() / "db" / "migrations" / "001_operational.sql").read_text(encoding="utf-8")
    names = set(re.findall(r"CREATE TABLE (\w+)", sql))
    assert names == set(metadata.tables)
