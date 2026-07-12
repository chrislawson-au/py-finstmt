"""Deal composition: entry transaction, waterfall, exit, and returns."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from finstmt.core.statements import FinancialStatements
from finstmt.deals.metrics import Metric, MetricValue, compute_metrics, irr, moic
from finstmt.deals.transaction import Transaction
from finstmt.deals.waterfall import Waterfall, WaterfallResult


@dataclass
class ExitTerms:
    """Sell in forecast period ``period`` (1-based) at ``multiple`` × the
    ``on`` item, less the outstanding ``less_debt`` balances."""

    period: int
    multiple: float
    on: str
    less_debt: List[str] = field(default_factory=list)


@dataclass
class DealResult:
    equity_cashflows: pd.Series
    irr: Optional[float]
    moic: Optional[float]
    exit_enterprise_value: Optional[float]
    exit_equity_value: Optional[float]
    waterfall: Optional[WaterfallResult]
    metrics: Dict[str, MetricValue]


@dataclass
class Deal:
    """An investment: equity in at entry, distributions along the way,
    equity out at exit.

    :param entry_equity: The sponsor's equity check at entry (positive).
    :param entry: Optional transaction applied to the statements first
        (e.g. sources & uses adjusting cash, debt, goodwill, fees).
    :param waterfall: Optional debt waterfall; its Residual step is treated
        as the cash distributed to equity each period.
    :param exit: Exit terms; proceeds are added to the exit period's flow.
    :param metrics: Extra metrics computed over the post-waterfall series.
    """

    entry_equity: float
    entry: Optional[Transaction] = None
    waterfall: Optional[Waterfall] = None
    exit: Optional[ExitTerms] = None
    metrics: List[Metric] = field(default_factory=list)

    def apply(
        self,
        stmts: FinancialStatements,
        periods: int = 5,
        forecast_kwargs: Optional[dict] = None,
    ) -> DealResult:
        if self.exit and not (1 <= self.exit.period <= periods):
            raise ValueError(
                f"Exit period {self.exit.period} outside forecast horizon {periods}"
            )

        working = self.entry.apply(stmts) if self.entry else stmts

        waterfall_result: Optional[WaterfallResult] = None
        if self.waterfall:
            waterfall_result = self.waterfall.apply(
                working, periods, forecast_kwargs=forecast_kwargs
            )
            series_by_key = dict(waterfall_result.values)
        else:
            kwargs = dict(periods=periods, balance=False)
            kwargs.update(forecast_kwargs or {})
            forecasted = working.forecast(**kwargs)
            series_by_key = {
                c.key: getattr(forecasted, c.key) for c in working.all_config_items
            }

        # Equity cash flows: -equity at entry, distributions, exit proceeds
        distributions = (
            list(waterfall_result.residual.values)
            if waterfall_result is not None and waterfall_result.residual is not None
            else [0.0] * periods
        )

        exit_ev: Optional[float] = None
        exit_equity: Optional[float] = None
        flows = [-abs(self.entry_equity)]
        for p in range(periods):
            flow = distributions[p] if p < len(distributions) else 0.0
            if self.exit and (p + 1) == self.exit.period:
                on_series = series_by_key[self.exit.on]
                exit_ev = float(on_series.iloc[p]) * self.exit.multiple
                debt_out = 0.0
                for key in self.exit.less_debt:
                    debt_out += float(series_by_key[key].iloc[p])
                exit_equity = exit_ev - debt_out
                flow += exit_equity
            flows.append(flow)

        # Flows after exit are not the sponsor's
        if self.exit:
            flows = flows[: self.exit.period + 1]

        equity_cashflows = pd.Series(flows, index=range(len(flows)))

        extra = compute_metrics(series_by_key, self.metrics) if self.metrics else {}

        return DealResult(
            equity_cashflows=equity_cashflows,
            irr=irr(list(equity_cashflows.values)),
            moic=moic(list(equity_cashflows.values)),
            exit_enterprise_value=exit_ev,
            exit_equity_value=exit_equity,
            waterfall=waterfall_result,
            metrics=extra,
        )
