from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import pandas as pd
from sympy import Eq, Expr, Idx, IndexedBase, sympify

from finstmt.config.item import ItemConfig
from finstmt.core.statement_series import StatementSeries
from finstmt.core.statements import FinancialStatements
from finstmt.solver.engine import (
    build_sympy_namespace,
    get_solve_eqs_and_full_subs_dict,
    solve_equations,
)


class SolverBase(ABC):
    """Template for solving statement item equations across periods.

    Subclasses supply the substitution values (``sympy_subs_dict``), the
    concrete per-period equations (``all_eqs``), and the right-hand side of
    each item's time-indexed equation (``_t_indexed_rhs``). The base class
    owns the shared machinery: building the sympy namespace, iteratively
    substituting known values, solving the residual system, and converting
    solutions back into :class:`StatementSeries` objects.
    """

    solve_eqs: List[Eq]
    subs_dict: Dict[IndexedBase, float]

    def __init__(
        self,
        stmts: FinancialStatements,
    ):
        self.stmts = stmts
        self.sympy_namespace = build_sympy_namespace(stmts.all_config_items)

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
        """Item configs per statement, preferring the (possibly adjusted)
        configs on the parent FinancialStatements."""
        return [
            self.stmts.config.configs.get(stmt_name, stmt.items_config_list)
            for stmt_name, stmt in self.stmts.statements.items()
        ]

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
                lhs = sympify(config.key + "[t]", locals=self.sympy_namespace)
                all_eqs.append(Eq(lhs, rhs))
        return all_eqs

    def _solved_values(self) -> Dict[IndexedBase, float]:
        """Solve the residual system, or return the substitutions unchanged
        when everything was already resolved by substitution."""
        if self.solve_eqs:
            return solve_equations(self.solve_eqs, self.subs_dict)
        return self.subs_dict

    def _results_to_statement_series(
        self, new_results: Dict[str, pd.Series]
    ) -> Dict[str, StatementSeries]:
        """Rebuild one StatementSeries per statement from solved item series."""
        all_results = pd.concat(list(new_results.values()), axis=1).T
        stmts = {}
        for stmt_name, stmt in self.stmts.statements.items():
            configs = self.stmts.config.configs.get(stmt_name, stmt.items_config_list)
            stmts[stmt.statement_name] = StatementSeries.from_df(
                all_results,
                stmt.statement_name,
                configs,
                disp_unextracted=False,
            )
        return stmts

    @abstractmethod
    def _t_indexed_rhs(self, config: ItemConfig) -> Optional[Expr]:
        """Right-hand side of the time-indexed equation for one item, or
        None if the item has no equation in this solver."""

    @abstractmethod
    def to_statements(self, **kwargs) -> FinancialStatements:
        ...

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
