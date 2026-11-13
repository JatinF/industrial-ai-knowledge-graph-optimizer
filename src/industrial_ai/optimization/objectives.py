"""Integer objective used by the allocation model.

The illustrative weights 1000*U + 10*L + 3*T + 2*C are not copied in as a
universal business policy. This module states the coefficients the solver
actually uses, in integer cost-units per unit of product:

- unmet demand: 1000
- late fulfillment: 10
- one shipped unit: the route cost (3 in the hand scenario)
- one produced unit: the plant cost (3 at PLANT-A, 2 at PLANT-B)

Unmet demand dominates lateness. Lateness dominates a single shipment or a
single unit of production at these plant costs. The tests lock that order.
"""

UNMET_PENALTY = 1000
LATE_PENALTY = 10

# The starter model in the specification uses a different unmet weight.
STARTER_UNMET_PENALTY = 100
STARTER_COST_A = 3
STARTER_COST_B = 2
