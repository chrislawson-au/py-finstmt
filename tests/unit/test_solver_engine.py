from sympy import Eq, Idx, IndexedBase, symbols

from finstmt.solver.engine import get_solve_eqs_and_full_subs_dict, solve_equations

t = symbols("t", cls=Idx)
revenue = IndexedBase("revenue")
cost = IndexedBase("cost")
profit = IndexedBase("profit")


def test_fully_substituted_system_returns_empty_residual():
    eqs = [Eq(profit[0], revenue[0] - cost[0])]
    subs = {revenue[0]: 1000.0, cost[0]: 600.0}

    remaining, solutions = get_solve_eqs_and_full_subs_dict(eqs, subs)

    assert remaining == []
    assert float(solutions[profit[0]]) == 400


def test_solve_equations_on_fully_substitutable_system():
    eqs = [Eq(profit[0], revenue[0] - cost[0])]
    subs = {revenue[0]: 1000.0, cost[0]: 600.0}

    solutions = solve_equations(eqs, subs)

    assert float(solutions[profit[0]]) == 400


def test_solve_equations_empty_system_returns_subs():
    subs = {revenue[0]: 1000.0}

    solutions = solve_equations([], subs)

    assert solutions == subs
