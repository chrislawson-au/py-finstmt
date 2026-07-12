from typing import Dict, List, Optional

import pandas as pd
from sympy import Eq, Expr, Indexed, IndexedBase

from finstmt.config.item import ItemConfig
from finstmt.solver.base import SolverBase
from finstmt.solver.engine import expr_for, sympy_dict_to_results_dict


class HistoricalSolver(SolverBase):
    """Solves calculated items across the historical periods.

    :param recompute_calculated: When True, calculated items are always
        recomputed from their equations (extracted values only seed equations
        that reference data outside the historical window, e.g.
        ``revenue[t-1]`` at t=0). When False (default), extracted values win
        and equations only fill gaps — the library's data-priority contract
        for real reported data, whose aggregates legitimately differ from the
        config's simplified identities.
    """

    def __init__(self, statement_configs, item_values, recompute_calculated: bool = False):
        self.recompute_calculated = recompute_calculated
        super().__init__(statement_configs, item_values)

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

    def _rhs_references_out_of_range(self, rhs: Expr, period: int) -> bool:
        """Whether an equation's RHS at this period needs data from outside
        the historical window (e.g. ``revenue[t-1]`` at period 0)."""
        for indexed in rhs.atoms(Indexed):
            for index in indexed.indices:
                resolved = index.subs({self.t: period})
                if not resolved.is_number:
                    continue
                if resolved < 0 or resolved >= self.num_periods:
                    return True
        return False

    @property
    def sympy_subs_dict(self) -> Dict[IndexedBase, float]:
        nper = self.num_periods
        rhs_by_key: Dict[str, Optional[Expr]] = {}
        if self.recompute_calculated:
            rhs_by_key = {
                config.key: self._t_indexed_rhs(config)
                for config in self.all_config_items
                if config.expr_str is not None
            }
        subs_dict = {}
        for config in self.all_config_items:
            key = config.key
            for period in range(nper):
                lhs = self.sympy_namespace[key][period]
                value = self.item_values[key].iloc[period]
                if config.expr_str is not None:
                    if self.recompute_calculated:
                        rhs = rhs_by_key[key]
                        needs_seed = rhs is not None and self._rhs_references_out_of_range(
                            rhs, period
                        )
                        if not needs_seed:
                            # Always recompute calculated items from their
                            # equations: per-statement precomputed values may
                            # be stale (computed before cross-statement
                            # references were available).
                            continue
                        if value is None or pd.isna(value) or value == 0:
                            # Nothing extracted to seed the recurrence with;
                            # leave the item unsolved for this period rather
                            # than substituting a non-numeric value
                            continue
                    elif value == 0:
                        # Don't have a value but it can be calculated,
                        # calculate it by not adding to substitutions
                        continue
                subs_dict[lhs] = value
        return subs_dict
