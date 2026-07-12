"""Deal modeling layer: transactions, waterfalls, and metrics.

A complement to the core statement engine for the things a simultaneous
equation solve cannot express:

- :class:`Transaction` — a point-in-time set of adjustments (a journal
  entry). Sources & uses is one balanced transaction. Applied by rebuilding
  the statements with adjusted explicit values, so the core's
  "explicitly-provided values win" rule does the accounting.
- :class:`Waterfall` — ordered, conditional cash allocation (mandatory
  amortization, cash sweeps, residual to cash) evaluated as a sequential
  forward pass per forecast period. Item expressions are still the source
  of truth: the waterfall re-evaluates them period by period with updated
  balances. With the standard convention that interest accrues on the
  prior period's balance, a single forward pass is exact.
- :class:`Metric` — post-solve derivations (IRR, MOIC, NPV, per-period
  expression ratios like leverage or DSCR). Metrics never enter the
  equation system.
- :class:`Deal` — composes an entry transaction, a debt waterfall, exit
  terms, and metrics into equity cash flows and returns.

Design rule: this layer never adds solver semantics. Order and conditional
logic live here; identities and recurrences live in the core.
"""

from finstmt.deals.metrics import Metric, compute_metrics, irr, moic, npv
from finstmt.deals.transaction import Entry, Transaction
from finstmt.deals.waterfall import Pay, Residual, Sweep, Waterfall, WaterfallResult
from finstmt.deals.deal import Deal, DealResult, ExitTerms

__all__ = [
    "Entry",
    "Transaction",
    "Pay",
    "Sweep",
    "Residual",
    "Waterfall",
    "WaterfallResult",
    "Metric",
    "compute_metrics",
    "irr",
    "moic",
    "npv",
    "ExitTerms",
    "Deal",
    "DealResult",
]
