from typing import Dict, List, Optional

import pandas as pd
from sympy import Eq, Expr, IndexedBase

from finstmt.config.item import ItemConfig
from finstmt.solver.base import SolverBase
from finstmt.solver.engine import expr_for, sympy_dict_to_results_dict


class HistoricalSolver(SolverBase):
    """Solves calculated items across the historical periods."""

    def solve(self) -> Dict[str, pd.Series]:
        solutions_dict = self._solved_values()
        return sympy_dict_to_results_dict(
            solutions_dict,
            self.dates,
            self.all_config_items,
        )

    @property
    def dates(self) -> pd.DatetimeIndex:
        return pd.DatetimeIndex(next(iter(self.item_values.values())).index)

    def _t_indexed_rhs(self, config: ItemConfig) -> Optional[Expr]:
        if config.expr_str is None:
            return None
        return expr_for(config.key, self.all_config_items, self.sympy_namespace)

    @property
    def all_eqs(self) -> List[Eq]:
        t_eqs = self.t_indexed_eqs
        out_eqs = []
        subs_dict = self.sympy_subs_dict
        for period in range(self.num_periods):
            for eq in t_eqs:
                period_eq = eq.subs({self.t: period})
                if period_eq.lhs in subs_dict:
                    # Already have data for this, no need to calculate
                    continue
                out_eqs.append(period_eq)
        return out_eqs

    @property
    def num_periods(self) -> int:
        return len(self.dates)

    @property
    def sympy_subs_dict(self) -> Dict[IndexedBase, float]:
        nper = self.num_periods
        subs_dict = {}
        for config in self.all_config_items:
            key = config.key
            for period in range(nper):
                lhs = self.sympy_namespace[key][period]
                value = self.item_values[key].iloc[period]
                if config.expr_str is not None and value == 0:
                    # Don't have a value but it can be calculated, calculate it by not adding to substitutions
                    continue
                subs_dict[lhs] = value
        return subs_dict
