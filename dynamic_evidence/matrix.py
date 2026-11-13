"""Frozen development/held-out synthetic case parameters.

The runtime reads these raw parameters, never expected graph nodes or decisions.
"""

from itertools import product

DEADLINE_TEMPLATES = (
    "To qualify, submit a service ticket no later than {hours} hours after the incident.",
    "Eligibility requires filing an incident ticket within {hours} hours of the outage.",
)
BOUNDARIES = ("early", "exact", "late", "missing")
MATRIX = {
    f"HOLD-{index:02d}": (template, hours, boundary, duration)
    for index, (template, hours, boundary, duration) in enumerate(
        product(range(2), (6, 24, 48), BOUNDARIES, (89, 91)), 1)
}
