from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import pandas as pd
from sympy import Eq, Expr, Idx, IndexedBase

from finstmt.config.item import ItemConfig
from finstmt.solver.engine import (
    build_sympy_namespace,
    get_solve_eqs_and_full_subs_dict,
    solve_equations,
)


class SolverBase(ABC):
    """Template for solving statement item equations across periods.

    Solvers operate on plain data — item configs per statement and item
    value series — and return plain per-item result series from ``solve``.
    They have no knowledge of the statement classes; ``FinancialStatements``
    orchestrates building solver inputs and rebuilding statements from
    results.

    Subclasses supply the substitution values (``sympy_subs_dict``), the
    concrete per-period equations (``all_eqs``), and the right-hand side of
    each item's time-indexed equation (``_t_indexed_rhs``). The base class
    owns the shared machinery: building the sympy namespace and iteratively
    substituting known values.

    :param statement_configs: Item configs per statement name, in statement
        order.
    :param item_values: Item key mapped to its series of values by date.
    """

    solve_eqs: List[Eq]
    subs_dict: Dict[IndexedBase, float]

    def __init__(
        self,
        statement_configs: Dict[str, List[ItemConfig]],
        item_values: Dict[str, pd.Series],
    ):
        self.statement_configs = statement_configs
        self.item_values = item_values

        all_items: Dict[str, ItemConfig] = {}
        for configs in statement_configs.values():
            for config in configs:
                all_items.setdefault(config.key, config)
        self.all_config_items: List[ItemConfig] = list(all_items.values())

        self.sympy_namespace = build_sympy_namespace(self.all_config_items)

        self.set_solve_eqs_and_full_subs_dict()

    def set_solve_eqs_and_full_subs_dict(self):
        """
        Initialize solving equations and substitution dictionary for financial calculations.

        Gets all equations from all_eqs and substitutes known values from sympy_subs_dict.
        Attempts to solve as many equations as possible through substitution and stores
        both the remaining unsolved equations and the dictionary of solved values.

        Sets:
            solve_eqs: List[Eq] - Equations that still need to be solved
            subs_dict: Dict[IndexedBase, float] - Dictionary of known/solved values
        """
        self.solve_eqs, self.subs_dict = get_solve_eqs_and_full_subs_dict(
            self.all_eqs, self.sympy_subs_dict
        )

    @property
    def t(self) -> Idx:
        return self.sympy_namespace["t"]

    @property
    def config_lists(self) -> List[List[ItemConfig]]:
        return list(self.statement_configs.values())

    @property
    def t_indexed_eqs(self) -> List[Eq]:
        """One time-indexed equation (``Eq(key[t], rhs)``) per item that has
        a right-hand side, as determined by ``_t_indexed_rhs``."""
        all_eqs = []
        for config_list in self.config_lists:
            for config in config_list:
                rhs = self._t_indexed_rhs(config)
                if rhs is None:
                    continue
                lhs = self.sympy_namespace[config.key][self.t]
                all_eqs.append(Eq(lhs, rhs))
        return all_eqs

    def _solved_values(self) -> Dict[IndexedBase, float]:
        """Solve the residual system, or return the substitutions unchanged
        when everything was already resolved by substitution."""
        if self.solve_eqs:
            return solve_equations(self.solve_eqs, self.subs_dict)
        return self.subs_dict

    @abstractmethod
    def _t_indexed_rhs(self, config: ItemConfig) -> Optional[Expr]:
        """Right-hand side of the time-indexed equation for one item, or
        None if the item has no equation in this solver."""

    @abstractmethod
    def solve(self) -> Dict[str, pd.Series]:
        """Solve the system and return one result series per item key."""

    @property
    @abstractmethod
    def all_eqs(self) -> List[Eq]:
        ...

    @property
    @abstractmethod
    def num_periods(self) -> int:
        ...

    @property
    @abstractmethod
    def sympy_subs_dict(self) -> Dict[IndexedBase, float]:
        ...
