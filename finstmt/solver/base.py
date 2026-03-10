from typing import Dict, List

from sympy import Eq, Idx, IndexedBase

from finstmt.core.statements import FinancialStatements
from finstmt.solver.engine import build_sympy_namespace, get_solve_eqs_and_full_subs_dict


class SolverBase:
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

    def to_statements(self) -> FinancialStatements:
        raise NotImplementedError

    @property
    def t_indexed_eqs(self) -> List[Eq]:
        raise NotImplementedError

    @property
    def all_eqs(self) -> List[Eq]:
        raise NotImplementedError

    @property
    def num_periods(self) -> int:
        raise NotImplementedError

    @property
    def sympy_subs_dict(self) -> Dict[IndexedBase, float]:
        raise NotImplementedError
