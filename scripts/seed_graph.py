"""Refresh the catalog export. This does not contact Neo4j."""

import os

from industrial_ai.exporting import write_synthetic
from industrial_ai.paths import repo_root
from industrial_ai.runtime_gates import gate


def main() -> None:
    counts = write_synthetic(repo_root())
    neo4j = gate(os.environ.get("NEO4J_URI"))
    print(
        f"seed export entities {counts['entities']} relationships {counts['relationships']} "
        f"neo4j {neo4j}"
    )


if __name__ == "__main__":
    main()
