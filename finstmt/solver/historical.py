from typing import Dict, List, Optional

import pandas as pd
from sympy import Eq, Expr, IndexedBase, sympify

from finstmt.config.item import ItemConfig
from finstmt.core.statements import FinancialStatements
from finstmt.solver.base import SolverBase
from finstmt.solver.engine import expr_for, sympy_dict_to_results_dict


class HistoricalSolver(SolverBase):
    def to_statements(self, **kwargs) -> FinancialStatements:
        solutions_dict = self._solved_values()

        new_results = sympy_dict_to_results_dict(
            solutions_dict,
            pd.DatetimeIndex(self.stmts.dates),
            self.stmts.all_config_items,
        )

        stmts = self._results_to_statement_series(new_results)
        return FinancialStatements(stmts, calculate=False, **kwargs)

    def _t_indexed_rhs(self, config: ItemConfig) -> Optional[Expr]:
        if config.expr_str is None:
            return None
        return expr_for(config.key, self.stmts.all_config_items, self.sympy_namespace)

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
        return len(self.stmts.dates)

    @property
    def sympy_subs_dict(self) -> Dict[IndexedBase, float]:
        nper = self.num_periods
        subs_dict = {}
        for config in self.stmts.all_config_items:
            key = config.key
            for period in range(nper):
                t_key = f"{key}[{period}]"
                lhs = sympify(t_key, locals=self.sympy_namespace)
                value = getattr(self.stmts, key).iloc[period]
                if config.expr_str is not None and value == 0:
                    # Don't have a value but it can be calculated, calculate it by not adding to substitutions
                    continue
                subs_dict[lhs] = value
        return subs_dict
