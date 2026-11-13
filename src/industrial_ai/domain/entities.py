"""Identifiers used by the hand-checkable network.

PRESS-220 contributes 6 units of PRODUCT-A capacity at PLANT-A. BACKUP-A2
contributes the other 2. Together they are the plant capacity of 8. MILL-110
is an alternate work center for the two-job schedule and does not add
PRODUCT-A allocation capacity.
"""

PRESS = "PRESS-220"
BACKUP = "BACKUP-A2"
ALTERNATE = "MILL-110"
PLANT_B_PRESS = "PRESS-B1"
OVEN = "OVEN-001"
PLANT_A = "PLANT-A"
PLANT_B = "PLANT-B"
PLANT_C = "PLANT-C"
LINE_A = "LINE-A1"
PRODUCT_A = "PRODUCT-A"
PRODUCT_B = "PRODUCT-B"
MATERIAL = "SEAL-KIT-220"
SUPPLIER = "SUP-001"
WAREHOUSE = "WH-NORTH"
LOT = "LOT-1001"
ORDER = "CO-2001"
OTHER_ORDER = "CO-2002"
ROUTE = "ROUTE-01"
PRODUCTION_ORDER = "PO-1001"
FAILURE = "FAIL-001"
SENSOR = "SYN-SENSOR-220"
MES = "synthetic-mes"
IOT = "synthetic-iot"

PLANNER_ID = "SYN-USER-PLANNER"
OPERATOR_ID = "SYN-USER-OPERATOR"
PLANNER_TOKEN = "lab-planner"
OPERATOR_TOKEN = "lab-operator"
