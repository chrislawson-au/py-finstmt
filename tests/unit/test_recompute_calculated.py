"""Tests for the ``recompute_calculated`` historical-solver option.

In both modes, explicitly provided values win — the library's data-priority
contract. The modes differ only in how *unreported* calculated items are
treated:

Default (False): any nonzero value wins, including per-statement precomputed
values; equations only fill zero-valued gaps.

Opt-in (True): calculated items are solved from clean inputs — only genuine
seed values (explicitly present in the source data, including explicit zeros)
are substituted, and everything else is recomputed from the equations. Stale
precomputed values never leak into the solve.
"""

import pandas as pd
import pytest

from finstmt import FinancialStatements, ItemConfig, StatementConfig


@pytest.fixture
def cross_statement_configs():
    """margin lives in another statement than the chain b = margin*a, c = a - b.

    The per-statement extraction pass precomputes c with b unresolved (b needs
    the cross-statement margin), so c arrives at the global solver stale.
    """
    p_items = [ItemConfig(key="margin", display_name="Margin", extract_names=["margin"])]
    s_items = [
        ItemConfig(key="a", display_name="A", extract_names=["a"]),
        ItemConfig(key="b", display_name="B", extract_names=["b"], expr_str="margin[t] * a[t]"),
        ItemConfig(key="c", display_name="C", extract_names=["c"], expr_str="a[t] - b[t]"),
    ]
    return [
        StatementConfig(key="p", display_name="P", items_config_list=p_items),
        StatementConfig(key="s", display_name="S", items_config_list=s_items),
    ]


@pytest.fixture
def cross_statement_df():
    return pd.DataFrame(
        {"Margin": [0.5], "A": [100.0]}, index=pd.to_datetime(["2023-12-31"])
    ).T


def test_recompute_solves_cross_statement_chain(cross_statement_configs, cross_statement_df):
    stmts = FinancialStatements.from_df(
        cross_statement_df,
        cross_statement_configs,
        disp_unextracted=False,
        recompute_calculated=True,
    )
    assert list(stmts.b.values) == [50.0]
    assert list(stmts.c.values) == [50.0]


def test_explicit_values_win_in_both_modes():
    """An explicitly reported aggregate that disagrees with the identity is
    kept in both modes — the flag only changes how *unreported* calculated
    items are treated (recomputed from clean inputs instead of trusting
    per-statement precomputed values)."""
    df = pd.DataFrame(
        # Reported C (70) intentionally differs from A - B (60): real filings
        # contain items the simplified identity does not carry.
        {"A": [100.0], "B": [40.0], "C": [70.0]},
        index=pd.to_datetime(["2023-12-31"]),
    ).T
    items = [
        ItemConfig(key="a", display_name="A", extract_names=["a"]),
        ItemConfig(key="b", display_name="B", extract_names=["b"]),
        ItemConfig(key="c", display_name="C", extract_names=["c"], expr_str="a[t] - b[t]"),
    ]
    configs = [StatementConfig(key="s", display_name="S", items_config_list=items)]

    stmts = FinancialStatements.from_df(df, configs, disp_unextracted=False)
    assert list(stmts.c.values) == [70.0]

    recomputed = FinancialStatements.from_df(
        df, configs, disp_unextracted=False, recompute_calculated=True
    )
    assert list(recomputed.c.values) == [70.0]


def test_recompute_preserves_recurrence_seed():
    """revenue[t-1] at t=0 reaches outside the window: the extracted value seeds it."""
    df = pd.DataFrame(
        {"Growth": [0.1], "Revenue": [1000.0]}, index=pd.to_datetime(["2023-12-31"])
    ).T
    p_items = [ItemConfig(key="growth", display_name="Growth", extract_names=["growth"])]
    s_items = [
        ItemConfig(
            key="revenue",
            display_name="Revenue",
            extract_names=["revenue"],
            expr_str="revenue[t-1] * (1 + growth[t])",
        )
    ]
    configs = [
        StatementConfig(key="p", display_name="P", items_config_list=p_items),
        StatementConfig(key="s", display_name="S", items_config_list=s_items),
    ]

    stmts = FinancialStatements.from_df(
        df, configs, disp_unextracted=False, recompute_calculated=True
    )
    assert list(stmts.revenue.values) == [1000.0]


def test_recompute_keeps_actual_history_for_recurrences():
    """Recurrences describe evolution, not identity: actual historical values
    win over the equation; only same-period identities are recomputed."""
    df = pd.DataFrame(
        {
            "Growth": [0.12, 0.12, 0.12],
            "Revenue": [1000.0, 1100.0, 1210.0],  # actual growth is 10%, not 12%
            "Costs": [400.0, 440.0, 484.0],
        },
        index=pd.to_datetime(["2021-12-31", "2022-12-31", "2023-12-31"]),
    ).T
    items_p = [ItemConfig(key="growth", display_name="Growth", extract_names=["growth"])]
    items_s = [
        ItemConfig(
            key="revenue",
            display_name="Revenue",
            extract_names=["revenue"],
            expr_str="revenue[t-1] * (1 + growth[t])",
        ),
        ItemConfig(key="costs", display_name="Costs", extract_names=["costs"]),
        ItemConfig(
            key="profit",
            display_name="Profit",
            extract_names=["profit"],
            expr_str="revenue[t] - costs[t]",
        ),
    ]
    stmts = FinancialStatements.from_df(
        df,
        [
            StatementConfig(key="p", display_name="P", items_config_list=items_p),
            StatementConfig(key="s", display_name="S", items_config_list=items_s),
        ],
        disp_unextracted=False,
        recompute_calculated=True,
    )
    # actual history preserved, not restated to 12% growth
    assert list(stmts.revenue.values) == [1000.0, 1100.0, 1210.0]
    # the same-period identity is still computed
    assert list(stmts.profit.values) == [600.0, 660.0, 726.0]
