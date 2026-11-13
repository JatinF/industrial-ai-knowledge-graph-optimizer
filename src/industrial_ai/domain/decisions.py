"""Decision status is separate from the solver status.

OPTIMAL means the model proved a best point. It does not mean the customer
received every unit on time. Shortfall is a variable, so a proved optimum can
still leave demand unmet.
"""

from typing import Literal

DecisionStatus = Literal[
    "REQUIRES_APPROVAL",
    "BLOCKED",
    "INFEASIBLE",
    "SOLVER_STOPPED",
    "APPROVED",
    "REJECTED",
    "EXECUTED",
]


class FlowError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def decision_status_for(solver_status: str, violations: list[str]) -> DecisionStatus:
    if solver_status in {"OPTIMAL", "FEASIBLE"} and not violations:
        return "REQUIRES_APPROVAL"
    if solver_status in {"OPTIMAL", "FEASIBLE"}:
        return "BLOCKED"
    if solver_status == "INFEASIBLE":
        return "INFEASIBLE"
    return "SOLVER_STOPPED"
