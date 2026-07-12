"""Tests for the ``recompute_calculated`` historical-solver option.

Default (False): extracted values win — the library's data-priority contract
for real reported filings, whose aggregates legitimately differ from the
config's simplified identities.

Opt-in (True): calculated items are always recomputed from their equations,
for models built from scratch where accounting identities must hold. Extracted
values still seed equations that reach outside the historical window
(recurrences like ``revenue[t-1]`` at t=0).
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


def test_default_keeps_extracted_values_for_calculated_items():
    """An extracted aggregate that disagrees with the identity is kept by default."""
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
    assert list(recomputed.c.values) == [60.0]


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
