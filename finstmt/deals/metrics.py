"""Post-solve metrics: IRR, MOIC, NPV, and per-period expression ratios.

Metrics are derived from solved series and never enter the equation system.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Union

import pandas as pd
from sympy import Indexed, sympify

MetricValue = Union[float, pd.Series, None]


def _clean_flows(cashflows: Sequence[float]) -> list:
    """Missing flows are no flow (0.0) — dropping them would silently shift
    later flows earlier in time."""
    return [
        0.0 if v is None or pd.isna(v) else float(v) for v in cashflows
    ]


def irr(cashflows: Sequence[float]) -> Optional[float]:
    """Internal rate of return of a cash-flow series (first flow at t=0),
    found by bisection. Requires at least one negative and one positive flow."""
    flows = _clean_flows(cashflows)
    if len(flows) < 2:
        return None
    if not any(v < 0 for v in flows) or not any(v > 0 for v in flows):
        return None

    def npv_at(rate: float) -> float:
        return sum(cf / (1 + rate) ** i for i, cf in enumerate(flows))

    lo, hi = -0.99, 10.0
    npv_lo = npv_at(lo)
    if npv_lo * npv_at(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        v = npv_at(mid)
        if abs(v) < 1e-9:
            return mid
        if v * npv_lo > 0:
            lo, npv_lo = mid, v
        else:
            hi = mid
    return (lo + hi) / 2


def moic(cashflows: Sequence[float]) -> Optional[float]:
    """Multiple of invested capital: total inflows over total outflows."""
    flows = _clean_flows(cashflows)
    inflows = sum(v for v in flows if v > 0)
    outflows = sum(v for v in flows if v < 0)
    if outflows == 0:
        return None
    return inflows / abs(outflows)


def npv(cashflows: Sequence[float], rate: float) -> Optional[float]:
    """Net present value of a cash-flow series (first flow at t=0)."""
    flows = _clean_flows(cashflows)
    if not flows:
        return None
    return sum(cf / (1 + rate) ** i for i, cf in enumerate(flows))


@dataclass
class Metric:
    """A derived measure.

    Either ``expr`` (a per-period expression over item keys, e.g.
    ``"total_debt / ebitda"`` — yields a :class:`pandas.Series`) or ``kind``
    (``"irr"``, ``"moic"``, ``"npv"`` over the ``cashflows`` item — yields a
    float).
    """

    key: str
    expr: Optional[str] = None
    kind: Optional[str] = None
    cashflows: Optional[str] = None
    rate: Optional[float] = None

    def __post_init__(self):
        if (self.expr is None) == (self.kind is None):
            raise ValueError(f"Metric {self.key}: provide exactly one of expr or kind")
        if self.kind is not None:
            if self.kind not in ("irr", "moic", "npv"):
                raise ValueError(f"Metric {self.key}: unknown kind {self.kind!r}")
            if self.cashflows is None:
                raise ValueError(f"Metric {self.key}: kind metrics need a cashflows item key")
            if self.kind == "npv" and self.rate is None:
                raise ValueError(f"Metric {self.key}: npv needs a rate")


def _eval_expr_metric(expr: str, series_by_key: Dict[str, pd.Series]) -> pd.Series:
    """Evaluate a plain expression over item keys per period via sympy."""
    sym_expr = sympify(expr)
    if sym_expr.atoms(Indexed):
        raise ValueError(
            f"Metric expressions are per-period; do not use [t] indexing: {expr!r}"
        )
    symbols = sorted(sym_expr.free_symbols, key=lambda s: str(s))
    missing = [str(s) for s in symbols if str(s) not in series_by_key]
    if missing:
        raise KeyError(f"Metric expression references unknown items: {missing}")

    index = next(iter(series_by_key.values())).index if series_by_key else []
    values = []
    for i in range(len(index)):
        subs = {s: series_by_key[str(s)].iloc[i] for s in symbols}
        if any(v is None or pd.isna(v) for v in subs.values()):
            values.append(float("nan"))
            continue
        try:
            values.append(float(sym_expr.subs(subs)))
        except (TypeError, ZeroDivisionError):
            values.append(float("nan"))
    return pd.Series(values, index=index)


def compute_metrics(
    series_by_key: Dict[str, pd.Series], metrics: Sequence[Metric]
) -> Dict[str, MetricValue]:
    """Compute every metric from solved item series."""
    out: Dict[str, MetricValue] = {}
    for metric in metrics:
        if metric.expr is not None:
            out[metric.key] = _eval_expr_metric(metric.expr, series_by_key)
            continue
        flows_series = series_by_key.get(metric.cashflows or "")
        flows = list(flows_series.values) if flows_series is not None else []
        if metric.kind == "irr":
            out[metric.key] = irr(flows)
        elif metric.kind == "moic":
            out[metric.key] = moic(flows)
        else:
            out[metric.key] = npv(flows, metric.rate or 0.0)
    return out
