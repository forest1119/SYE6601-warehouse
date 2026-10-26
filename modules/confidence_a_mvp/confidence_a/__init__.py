"""07A evidence scoring MVP. No model calls or business rule inference."""

from .contracts import ContractError
from .scoring import score_snapshot
from .metrics import evaluate_runs

__all__ = ["ContractError", "score_snapshot", "evaluate_runs"]
__version__ = "0.1.0"
