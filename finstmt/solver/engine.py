from typing import Dict, List, Sequence, Tuple, Union

import numpy as np
import pandas as pd
from sympy import Eq, Expr, Idx, Indexed, IndexedBase, Symbol, expand, symbols, sympify
from sympy.logic.boolalg import BooleanFalse, BooleanTrue

from finstmt.config.item import ItemConfig
from finstmt.exceptions import NoSuchItemException, NotACalculatedItemException

PLUG_SCALE = 1e11


def _key_pct_of_key(base_key: str, pct_of_key: str) -> str:
    return f"{base_key}_pct_{pct_of_key}"


def build_sympy_namespace(item_configs: List[ItemConfig]) -> Dict[str, IndexedBase]:
    """Build the sympy namespace from item configs. Includes pct_of keys."""
    t = symbols("t", cls=Idx)
    ns: Dict[str, IndexedBase] = {"t": t}
    for config in item_configs:
        ns[config.key] = IndexedBase(config.key)
        if config.forecast.pct_of is not None:
            pct_key = _key_pct_of_key(config.key, config.forecast.pct_of)
            ns[pct_key] = IndexedBase(pct_key)
    return ns


def expr_for(item_key: str, item_configs: List[ItemConfig], ns: Dict[str, IndexedBase]) -> Expr:
    """Parse expr_str for item_key into a sympy expression."""
    for config in item_configs:
        if config.key == item_key:
            if config.expr_str is None:
                raise NotACalculatedItemException(item_key)
            return sympify(config.expr_str, locals=ns)
    raise NoSuchItemException(item_key)


def eq_subs_dict(
    values_dict: Dict[str, float], ns: Dict[str, IndexedBase], t_offset: int = 0
) -> Dict[IndexedBase, float]:
    """Convert plain key->value dict to sympy indexed substitution dict."""
    out_dict = {}
    t = ns["t"]
    for key, sym in ns.items():
        if key in values_dict:
            out_dict[sym[t + t_offset]] = values_dict[key]
    return out_dict


def resolve_initial_expressions(
    all_configs: List[ItemConfig],
    period_expression_strings: List[List[Tuple[str, str]]],
) -> Dict:
    """Solve calculated items from expression strings using numpy linear algebra.

    Takes expression strings from each period and solves the linear system.
    Returns a dict mapping (sympy_key, period_index) -> solved_value that
    the caller can use to update StatementPeriodData objects.

    Args:
        all_configs: All ItemConfig objects across all statements (deduplicated)
        period_expression_strings: For each period, a list of (lhs_str, rhs_str) tuples

    Returns:
        Dict mapping sympy indexed keys to solved values. Each key has .base (the item key)
        and .indices[0] (the period index).
    """
    ns = build_sympy_namespace(all_configs)
    eqns = []
    for idx, period_exprs in enumerate(period_expression_strings):
        for lhs_str, rhs_str in period_exprs:
            if rhs_str is None:
                continue
            lhs = sympify(lhs_str, locals=ns).subs(ns["t"], idx)
            rhs = sympify(rhs_str, locals=ns).subs(ns["t"], idx)
            # Skip equations referencing negative time indices (e.g. t-1 at t=0)
            if any(
                isinstance(sym, Indexed) and sym.indices[0] < 0
                for sym in rhs.free_symbols
            ):
                continue
            eqns.append(Eq(lhs, rhs))

    all_to_solve = {}
    for eqn in eqns:
        expr = eqn.rhs - eqn.lhs
        all_to_solve[eqn.lhs] = expr

    to_solve_for = list(all_to_solve.keys())
    solve_exprs = list(all_to_solve.values())

    return numpy_solve(solve_exprs, to_solve_for)


def sympy_dict_to_results_dict(
    s_dict: Dict[IndexedBase, float],
    forecast_dates: pd.DatetimeIndex,
    item_configs: List[ItemConfig],
    t_offset: int = 0,
) -> Dict[str, pd.Series]:
    item_config_dict: Dict[str, ItemConfig] = {
        config.key: config for config in item_configs
    }
    new_results = {}
    for expr in s_dict:
        key = str(expr.base)  # type: ignore[attr-defined]
        try:
            config = item_config_dict[key]
        except KeyError:
            # Must be pct of item, don't need in final results
            continue
        new_results[key] = pd.Series(
            index=forecast_dates, dtype="float", name=config.primary_name
        )
    for expr, val in s_dict.items():
        key = str(expr.base)  # type: ignore[attr-defined]
        t = int(expr.indices[0]) - t_offset  # type: ignore[attr-defined]
        if t < 0:
            # Don't need to store historical results
            continue
        if key not in new_results:
            # Pct of item, skip it, don't need in final results
            continue
        new_results[key].iloc[t] = float(val)
    return new_results


def results_dict_to_sympy_dict(
    results_dict: Dict[str, pd.Series], sympy_namespace: Dict[str, Expr]
) -> Dict[IndexedBase, float]:
    """
    Convert dictionary of pandas Series to SymPy symbolic expressions.

    Args:
        results_dict: Dictionary mapping variable names to pandas Series
        sympy_namespace: Dictionary of SymPy variables for symbolic conversion

    Returns:
        Dictionary mapping indexed SymPy expressions to their values

    Example:
        >>> import pandas as pd
        >>> from sympy import IndexedBase
        >>>
        >>> # Financial statement data
        >>> financial_results = {
        ...     'cash': pd.Series([100, 200, 300], name='Cash'),
        ...     'debt': pd.Series([500, 600, 700], name='Total Debt')
        ... }
        >>>
        >>> # SymPy variable definitions
        >>> sympy_variables = {
        ...     'cash': IndexedBase('cash'),
        ...     'debt': IndexedBase('debt')
        ... }
        >>>
        >>> # Convert to SymPy expressions
        >>> sympy_expressions = results_dict_to_sympy_dict(financial_results, sympy_variables)
        >>> # Results in:
        >>> # {
        >>> #     cash[1]: 100.0,
        >>> #     cash[2]: 200.0,
        >>> #     cash[3]: 300.0,
        >>> #     debt[1]: 500.0,
        >>> #     debt[2]: 600.0,
        >>> #     debt[3]: 700.0
        >>> # }
    """
    out_dict = {}
    for key, series in results_dict.items():
        arr = series.values
        for i, val in enumerate(arr):
            t_str = f"{key}[{i + 1}]"
            lhs = sympify(t_str, locals=sympy_namespace)
            out_dict[lhs] = val
    return out_dict


def get_solve_eqs_and_full_subs_dict(
    eqs_for_sub: List[Eq], subs_dict: Dict[IndexedBase, float]
) -> Tuple[List[Eq], Dict[IndexedBase, float]]:
    """
    Iteratively substitute known values and solve equations until no more progress can be made.

    Takes a list of equations and dictionary of known values, then:
    1. Substitutes known values into equations
    2. If an equation becomes fully solved (RHS has no symbols), adds it to solutions
    3. Uses new solutions to substitute in remaining equations
    4. Repeats until no more equations can be solved

    Args:
        eqs_for_sub: List of SymPy equations to solve/substitute
        subs_dict: Dictionary mapping variables to their known values

    Returns:
        Tuple containing:
        - List[Eq]: Remaining unsolved equations after substitution
        - Dict[IndexedBase, float]: Updated dictionary with all solved values

    Examples:
        >>> # Example 1: Fully solvable system
        >>> eqs = [
        ...     Eq(revenue[1], 1000),              # Known revenue
        ...     Eq(costs[1], revenue[1] * 0.6),    # Costs are 60% of revenue
        ...     Eq(profit[1], revenue[1] - costs[1])  # Profit equation
        ... ]
        >>> known_vals = {revenue[1]: 1000}
        >>> remaining_eqs, solutions = get_solve_eqs_and_full_subs_dict(eqs, known_vals)
        >>> solutions
        {
            revenue[1]: 1000,    # Original known value
            costs[1]: 600,       # Solved: 1000 * 0.6
            profit[1]: 400       # Solved: 1000 - 600
        }
        >>> remaining_eqs
        []  # All equations were solved

        >>> # Example 2: Partially solvable system
        >>> eqs = [
        ...     Eq(costs[1], revenue[1] * 0.6),    # Costs are 60% of revenue
        ...     Eq(profit[1], revenue[1] - costs[1]),  # Profit equation
        ...     Eq(cash[1], profit[1] * cash_ratio[1])  # Cash is ratio of profit
        ... ]
        >>> known_vals = {revenue[1]: 1000}
        >>> remaining_eqs, solutions = get_solve_eqs_and_full_subs_dict(eqs, known_vals)
        >>> solutions
        {
            revenue[1]: 1000,    # Original known value
            costs[1]: 600,       # Solved: 1000 * 0.6
            profit[1]: 400       # Solved: 1000 - 600
        }
        >>> remaining_eqs
        [
            Eq(cash[1], 400 * cash_ratio[1])  # Still contains unknown cash_ratio
        ]
    """
    subbed_eqs = []
    subs_dict = subs_dict.copy()
    while True:
        next_eqs_to_sub = []
        for eq in eqs_for_sub:
            subbed = Eq(eq.lhs, eq.rhs.xreplace(subs_dict))
            if isinstance(subbed, (BooleanFalse, BooleanTrue)):
                # Both lhs and rhs was subbed. This means it is a calculated item which was
                # added to the forecast because it is being used as pct_of in other items.
                # Simply don't solve the equation again as the result is already in the subs dict.
                continue
            elif not subbed.rhs.free_symbols:
                # Equation is completely solved
                subbed_eqs.append(subbed)
                subs_dict[subbed.lhs] = subbed.rhs
            else:
                # Equation still has remaining symbols, handle on next loop
                next_eqs_to_sub.append(subbed)
        if not next_eqs_to_sub or eqs_for_sub == next_eqs_to_sub:
            # Either all solved, or no progress was made this iteration
            break
        eqs_for_sub = next_eqs_to_sub
    return eqs_for_sub, subs_dict


def solve_equations(
    solve_eqs: List[Eq],
    subs_dict: Dict[IndexedBase, float],
    substitute: bool = True,
    round_results: bool = True,
):
    solutions_dict = subs_dict.copy()

    if substitute:
        solve_eqs, solutions_dict = get_solve_eqs_and_full_subs_dict(
            solve_eqs, solutions_dict
        )
    solve_exprs = []
    to_solve_for = []
    for eq in solve_eqs:
        solve_exprs.append(eq.rhs - eq.lhs)
        to_solve_for.append(eq.lhs)
    to_solve_for = sorted(set(to_solve_for), key=str)

    res_set = numpy_solve(solve_exprs, to_solve_for)
    if not res_set:
        raise ValueError("could not solve equations")
    solutions_dict.update(res_set)

    return solutions_dict


def _solve_eqs_with_plug_solutions(
    eqs: List[Eq],
    plug_solutions: Dict[IndexedBase, float],
    subs_dict: Dict[IndexedBase, float],
    forecast_dates: pd.DatetimeIndex,
    item_configs: List[ItemConfig],
) -> Dict[IndexedBase, float]:
    subs_dict = subs_dict.copy()
    subs_dict.update(plug_solutions)
    sub_eqs = [Eq(lhs, rhs) for lhs, rhs in subs_dict.items()]
    solutions_dict = solve_equations(eqs + sub_eqs, {}, substitute=False)

    return solutions_dict


def _x_arr_to_plug_solutions(
    x: np.ndarray, plug_keys: Sequence[str], sympy_namespace: Dict[str, IndexedBase]
) -> Dict[IndexedBase, float]:
    """
    Convert array of plug values to a dictionary mapping SymPy expressions to values.

    Args:
        x: Array of plug values scaled down by PLUG_SCALE. Length should be number of plug_keys * number of periods
        plug_keys: Keys identifying the plug variables, e.g. ['cash', 'debt']
        sympy_namespace: Dictionary mapping variable names to SymPy IndexedBase objects

    Returns:
        Dictionary mapping SymPy indexed expressions to their values

    Example:
        >>> import numpy as np
        >>> from sympy import IndexedBase
        >>> x = np.array([1, 2, 3, 4, 5, 6])  # Values for two plug variables over 3 periods
        >>> plug_keys = ['cash', 'debt']
        >>> sympy_namespace = {
        ...     'cash': IndexedBase('cash'),
        ...     'debt': IndexedBase('debt')
        ... }
        >>> solutions = _x_arr_to_plug_solutions(x, plug_keys, sympy_namespace)
        >>> # Results in (after multiplying by PLUG_SCALE):
        >>> # {
        >>> #    cash[1]: 1e11,
        >>> #    cash[2]: 2e11,
        >>> #    cash[3]: 3e11,
        >>> #    debt[1]: 4e11,
        >>> #    debt[2]: 5e11,
        >>> #    debt[3]: 6e11
        >>> # }
    """
    x_arrs = np.split(x * PLUG_SCALE, len(plug_keys))
    plug_dict = {key: pd.Series(x_arrs[i]) for i, key in enumerate(plug_keys)}
    # TODO: Is Expr or IndexedBase the correct type?
    plug_solutions = results_dict_to_sympy_dict(plug_dict, sympy_namespace)  # type: ignore[arg-type]
    return plug_solutions


def _symbolic_to_matrix(exprs: Sequence[Expr], variables: Sequence[Symbol]):
    """
    Expr should be in the format of eq.lhs - eq.rhs

    Assuming that there exists numeric matrix A such that equation F = 0
    is equivalent to linear equation Ax = b, this function returns
    tuple (A, b)
    """
    A = []
    b = []
    for expr in exprs:
        coeffs = expand(expr).as_coefficients_dict()
        A.append([float(coeffs[x]) for x in variables])
        b.append(-float(coeffs[1]))
    return np.array(A), np.array(b)


def numpy_solve(exprs: Sequence[Expr], variables: Sequence[Symbol]):
    a_arr, b_arr = _symbolic_to_matrix(exprs, variables)
    x = np.linalg.solve(a_arr, b_arr)
    solution_dict = {var: x[i] for i, var in enumerate(variables)}
    return solution_dict


def _get_indexed_symbols(expr: Union[Eq, Expr]) -> List[Indexed]:
    return sorted(
        [sym for sym in expr.free_symbols if isinstance(sym, Indexed)], key=str
    )
