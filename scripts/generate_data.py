"""Write datasets/synthetic and graph/seed.cypher from seed 7."""

from industrial_ai.exporting import write_synthetic
from industrial_ai.paths import repo_root


def main() -> None:
    counts = write_synthetic(repo_root())
    print(
        f"entities {counts['entities']} relationships {counts['relationships']} "
        f"machines {counts['label_Machine']} orders {counts['label_CustomerOrder']}"
    )


if __name__ == "__main__":
    main()
