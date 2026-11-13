"""Two-job schedule with machine choice, precedence, and a downtime window.

Maintenance, when set, blocks PRESS-220 from time 0 through time 5.
Jobs are contiguous. A job on that machine must start at time 5 or later.
"""

import time
from dataclasses import dataclass

from ortools.sat.python import cp_model


@dataclass(frozen=True)
class Assignment:
    job_id: str
    machine_id: str
    start: int
    end: int


@dataclass(frozen=True)
class ScheduleResult:
    status: str
    makespan: int
    assignments: tuple[Assignment, ...]
    wall_seconds: float

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "makespan": self.makespan,
            "assignments": [row.__dict__ for row in self.assignments],
            "wall_seconds": self.wall_seconds,
        }


def solve_schedule(
    *, maintenance: bool, alternate_available: bool, horizon: int = 20
) -> ScheduleResult:
    started = time.perf_counter()
    machines = ["PRESS-220"]
    if alternate_available:
        machines.append("MILL-110")
    jobs = (("JOB-1", 4), ("JOB-2", 3))
    model = cp_model.CpModel()
    present: dict[tuple[str, str], cp_model.IntVar] = {}
    intervals: dict[str, list[cp_model.IntervalVar]] = {machine: [] for machine in machines}
    job_start: dict[str, cp_model.IntVar] = {}
    job_end: dict[str, cp_model.IntVar] = {}
    for job_id, duration in jobs:
        start = model.new_int_var(0, horizon, f"start_{job_id}")
        end = model.new_int_var(0, horizon, f"end_{job_id}")
        model.add(end == start + duration)
        job_start[job_id] = start
        job_end[job_id] = end
        choices = []
        for machine in machines:
            flag = model.new_bool_var(f"use_{job_id}_{machine}")
            local_start = model.new_int_var(0, horizon, f"ls_{job_id}_{machine}")
            local_end = model.new_int_var(0, horizon, f"le_{job_id}_{machine}")
            interval = model.new_optional_interval_var(
                local_start, duration, local_end, flag, f"iv_{job_id}_{machine}"
            )
            model.add(local_start == start).only_enforce_if(flag)
            model.add(local_end == end).only_enforce_if(flag)
            if maintenance and machine == "PRESS-220":
                model.add(local_start >= 5).only_enforce_if(flag)
            present[job_id, machine] = flag
            intervals[machine].append(interval)
            choices.append(flag)
        model.add_exactly_one(choices)
    for machine, rows in intervals.items():
        model.add_no_overlap(rows)
    model.add(job_start["JOB-2"] >= job_end["JOB-1"])
    makespan = model.new_int_var(0, horizon, "makespan")
    model.add(makespan >= job_end["JOB-2"])
    model.minimize(makespan)
    solver = cp_model.CpSolver()
    status_code = solver.solve(model)
    elapsed = time.perf_counter() - started
    name = solver.status_name(status_code)
    if name not in {"OPTIMAL", "FEASIBLE"}:
        return ScheduleResult(name, 0, (), elapsed)
    assignments: list[Assignment] = []
    for job_id, _duration in jobs:
        for machine in machines:
            if solver.value(present[job_id, machine]) == 1:
                assignments.append(
                    Assignment(
                        job_id,
                        machine,
                        solver.value(job_start[job_id]),
                        solver.value(job_end[job_id]),
                    )
                )
    return ScheduleResult(name, solver.value(makespan), tuple(assignments), elapsed)
