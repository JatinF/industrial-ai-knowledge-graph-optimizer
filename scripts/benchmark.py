"""Record an in-process benchmark JSON file."""

from industrial_ai.bench import run_benchmark, write_report
from industrial_ai.paths import repo_root


def main() -> None:
    report = run_benchmark()
    destination = repo_root() / "benchmarks" / "latest.json"
    write_report(destination, report)
    print(
        "event_to_plan_p95_seconds "
        f"{report['event_to_plan_p95_seconds']:.6f} "
        f"target_met {report['event_to_plan_target_met']} "
        f"invalid_executed_plans {report['invalid_executed_plans']}"
    )


if __name__ == "__main__":
    main()
