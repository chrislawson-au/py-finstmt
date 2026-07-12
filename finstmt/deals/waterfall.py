"""Debt waterfalls: ordered, conditional cash allocation per forecast period.

The waterfall is a sequential forward pass that the simultaneous solver
cannot express: within each period, cash available flows through steps in
priority order (mandatory payments, sweeps, residual). Item expressions
remain the source of truth — the pass re-evaluates them period by period
with the updated balances.

Convention: expressions feeding the waterfall (interest, cash available)
should reference balances at ``[t-1]`` (interest accrues on the prior
period's balance). Under that convention a single forward pass is exact.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Union

import pandas as pd
from sympy import Expr, Indexed

from finstmt.core.statements import FinancialStatements
from finstmt.solver.engine import expr_for, build_sympy_namespace


@dataclass
class Pay:
    """Mandatory payment reducing ``balance`` by ``amount`` (an item key or a
    fixed number), limited by available cash and the remaining balance."""

    balance: str
    amount: Union[str, float]


@dataclass
class Sweep:
    """Optional prepayment: ``pct`` of the cash remaining after prior steps,
    limited by the remaining balance."""

    balance: str
    pct: float = 1.0


@dataclass
class Residual:
    """Whatever cash remains accumulates on ``target`` (e.g. ``cash``)."""

    target: str


Step = Union[Pay, Sweep, Residual]


@dataclass
class WaterfallResult:
    """Per-period series produced by the pass."""

    source: pd.Series
    balances: Dict[str, pd.Series]
    payments: Dict[str, pd.Series]
    residual: Optional[pd.Series]
    values: Dict[str, pd.Series]
    """Every item series under the waterfall (balances updated, dependents
    re-evaluated) over the forecast periods."""


@dataclass
class Waterfall:
    source: str
    steps: List[Step] = field(default_factory=list)

    def _balance_keys(self) -> List[str]:
        return [s.balance for s in self.steps if isinstance(s, (Pay, Sweep))]

    def apply(
        self,
        stmts: FinancialStatements,
        periods: int,
        forecast_kwargs: Optional[dict] = None,
    ) -> WaterfallResult:
        """Run the forward pass over ``periods`` forecast periods.

        Non-dependent items take their values from a plain (unbalanced)
        forecast; items that depend on the waterfall balances — directly or
        transitively — are re-evaluated each period from their expressions.
        """
        kwargs = dict(periods=periods, balance=False)
        kwargs.update(forecast_kwargs or {})
        forecasted = stmts.forecast(**kwargs)

        configs = {c.key: c for c in stmts.all_config_items}
        namespace = build_sympy_namespace(stmts.all_config_items)
        balance_keys = self._balance_keys()
        for key in balance_keys + [self.source]:
            if key not in configs:
                raise KeyError(f"Waterfall references unknown item {key!r}")

        # Dependency closure: items whose expressions (transitively) touch a
        # waterfall balance must be re-evaluated inside the pass.
        exprs: Dict[str, Expr] = {}
        for key, config in configs.items():
            if config.expr_str is not None:
                exprs[key] = expr_for(key, stmts.all_config_items, namespace)

        def references(expr: Expr, keys: set) -> bool:
            for atom in expr.atoms(Indexed):
                if str(atom.base) in keys:
                    return True
            return False

        closure = set(balance_keys)
        changed = True
        while changed:
            changed = False
            for key, expr in exprs.items():
                if key not in closure and references(expr, closure):
                    closure.add(key)
                    changed = True

        # Timeline: historical values then forecast values per item
        hist_dates = list(stmts.dates)
        sample = getattr(forecasted, self.source)
        forecast_index = list(sample.index)

        values: Dict[str, List[float]] = {}
        for key in configs:
            hist_series = getattr(stmts, key)
            fcst_series = getattr(forecasted, key)
            values[key] = [
                float(v) if not pd.isna(v) else float("nan") for v in hist_series.values
            ] + [float(v) if not pd.isna(v) else float("nan") for v in fcst_series.values]

        n_hist = len(hist_dates)

        def value_at(key: str, index: int) -> float:
            series = values.get(key)
            if series is None or index < 0 or index >= len(series):
                return float("nan")
            return series[index]

        def eval_expr(key: str, index: int) -> float:
            expr = exprs[key]
            subs = {}
            for atom in expr.atoms(Indexed):
                base = str(atom.base)
                offset = atom.indices[0]
                # index expressions are t or t+k; resolve k
                k = int(offset - namespace["t"]) if offset.has(namespace["t"]) else None
                target = index + k if k is not None else int(offset)
                subs[atom] = value_at(base, target)
            try:
                return float(expr.subs(subs))
            except (TypeError, ValueError):
                return float("nan")

        payments: Dict[str, List[float]] = {}
        residual_values: List[float] = []
        source_values: List[float] = []

        for p in range(periods):
            index = n_hist + p

            # Re-evaluate dependent non-balance items for this period, in
            # passes until stable (dependencies among them resolve within
            # len(closure) iterations)
            pending = [k for k in closure if k not in balance_keys and k in exprs]
            for _ in range(len(pending) + 1):
                for key in pending:
                    values[key][index] = eval_expr(key, index)

            available = value_at(self.source, index)
            if pd.isna(available):
                available = 0.0
            source_values.append(available)

            for step in self.steps:
                if isinstance(step, Pay):
                    prior_balance = value_at(step.balance, index - 1)
                    scheduled = (
                        value_at(step.amount, index)
                        if isinstance(step.amount, str)
                        else float(step.amount)
                    )
                    payment = max(0.0, min(scheduled, prior_balance, available))
                    label = f"pay_{step.balance}"
                    payments.setdefault(label, [0.0] * periods)[p] = payment
                    available -= payment
                    values[step.balance][index] = prior_balance - payment
                elif isinstance(step, Sweep):
                    current_balance = value_at(step.balance, index)
                    if pd.isna(current_balance):
                        current_balance = value_at(step.balance, index - 1)
                    sweep_amount = max(0.0, min(step.pct * available, current_balance))
                    label = f"sweep_{step.balance}"
                    payments.setdefault(label, [0.0] * periods)[p] = sweep_amount
                    available -= sweep_amount
                    values[step.balance][index] = current_balance - sweep_amount
                elif isinstance(step, Residual):
                    prior = value_at(step.target, index - 1)
                    base = 0.0 if pd.isna(prior) else prior
                    residual_values.append(available)
                    values[step.target][index] = base + available
                    available = 0.0

            # Stabilize again after the steps so same-period identities
            # (e.g. total_debt = a + b) reflect post-payment balances in the
            # result. Items on the [t-1] convention are unchanged by this.
            for _ in range(len(pending) + 1):
                for key in pending:
                    values[key][index] = eval_expr(key, index)

        def to_series(vals: Sequence[float]) -> pd.Series:
            return pd.Series(list(vals), index=forecast_index)

        result_values = {
            key: to_series(values[key][n_hist : n_hist + periods]) for key in configs
        }
        return WaterfallResult(
            source=to_series(source_values),
            balances={k: result_values[k] for k in balance_keys},
            payments={k: to_series(v) for k, v in payments.items()},
            residual=to_series(residual_values) if residual_values else None,
            values=result_values,
        )
