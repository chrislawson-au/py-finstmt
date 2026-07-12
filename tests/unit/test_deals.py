"""Tests for the deals layer: transactions, waterfalls, metrics, deals."""

import pandas as pd
import pytest

from finstmt import FinancialStatements, ItemConfig, ForecastItemConfig, StatementConfig
from finstmt.deals import (
    Deal,
    Entry,
    ExitTerms,
    Metric,
    Pay,
    Residual,
    Sweep,
    Transaction,
    Waterfall,
    compute_metrics,
    irr,
    moic,
    npv,
)


# ------------------------------------------------------------------ helpers

def lbo_statements() -> FinancialStatements:
    """EBITDA 100 flat; debt 400 at 10% on prior balance; 25% tax.

    cash_available = ebitda - interest - taxes, all expression-driven so the
    waterfall re-evaluates them as balances change.
    """
    df = pd.DataFrame(
        {"EBITDA": [100.0], "Debt": [400.0], "Cash": [50.0]},
        index=pd.to_datetime(["2023-12-31"]),
    ).T
    items = [
        ItemConfig(
            key="ebitda", display_name="EBITDA", extract_names=["ebitda"],
            forecast=ForecastItemConfig(method="recent"),
        ),
        ItemConfig(key="debt", display_name="Debt", extract_names=["debt"],
                   forecast=ForecastItemConfig(method="recent")),
        ItemConfig(key="cash", display_name="Cash", extract_names=["cash"],
                   forecast=ForecastItemConfig(method="recent")),
        ItemConfig(key="interest", display_name="Interest", extract_names=["interest"],
                   expr_str="0.10 * debt[t-1]"),
        ItemConfig(key="taxes", display_name="Taxes", extract_names=["taxes"],
                   expr_str="0.25 * (ebitda[t] - interest[t])"),
        ItemConfig(key="cash_available", display_name="Cash Available",
                   extract_names=["cash available"],
                   expr_str="ebitda[t] - interest[t] - taxes[t]"),
    ]
    return FinancialStatements.from_df(
        df,
        [StatementConfig(key="deal", display_name="Deal", items_config_list=items)],
        disp_unextracted=False,
        recompute_calculated=True,
    )


# ------------------------------------------------------------------ metrics

def test_irr_moic_npv():
    assert irr([-1000, 500, 500, 500]) == pytest.approx(0.2338, abs=1e-3)
    assert irr([-100, 200]) == pytest.approx(1.0, abs=1e-6)
    assert irr([100, 200]) is None
    assert moic([-1000, 500, 500, 500]) == pytest.approx(1.5)
    assert npv([-100, 60, 60], 0.1) == pytest.approx(-100 + 60 / 1.1 + 60 / 1.21)


def test_expr_metric_per_period():
    series = {
        "total_debt": pd.Series([400.0, 350.0], index=[0, 1]),
        "ebitda": pd.Series([100.0, 110.0], index=[0, 1]),
    }
    out = compute_metrics(series, [Metric("leverage", expr="total_debt / ebitda")])
    assert list(out["leverage"].values) == pytest.approx([4.0, 350 / 110])


def test_metric_validation():
    with pytest.raises(ValueError):
        Metric("bad")  # neither expr nor kind
    with pytest.raises(ValueError):
        Metric("bad", kind="irr")  # no cashflows
    with pytest.raises(ValueError):
        Metric("bad", expr="a", kind="moic", cashflows="x")  # both


# -------------------------------------------------------------- transaction

def test_sources_and_uses_must_balance():
    with pytest.raises(ValueError):
        Transaction.sources_and_uses("2023-12-31", {"debt": 480}, {"cash": 400})


def test_transaction_adjusts_raw_items_and_recomputes_identities():
    stmts = lbo_statements()
    txn = Transaction(
        date="2023-12-31",
        entries=[Entry("debt", 80), Entry("cash", -30)],
        name="Refi",
    )
    adjusted = txn.apply(stmts)
    assert float(adjusted.debt.iloc[0]) == 480.0
    assert float(adjusted.cash.iloc[0]) == 20.0
    # interest is on the prior balance, so period-0 interest needs t=-1 data
    # that does not exist: it must be honestly NaN, not a stale solved value
    assert pd.isna(adjusted.interest.iloc[0])

    with pytest.raises(ValueError):
        Transaction(date="2023-12-31", entries=[Entry("taxes", 5)]).apply(stmts)
    with pytest.raises(KeyError):
        Transaction(date="2023-12-31", entries=[Entry("nope", 5)]).apply(stmts)


def test_transaction_rejects_sign_flip_on_force_positive_items():
    """An adjustment that takes a force_positive item negative must raise:
    the rebuild would silently abs() the value (cash -30 becoming +30)."""
    stmts = lbo_statements()
    txn = Transaction(date="2023-12-31", entries=[Entry("cash", -80.0)])  # cash is 50

    with pytest.raises(ValueError, match="force_positive"):
        txn.apply(stmts)


def test_transaction_survives_display_names_that_do_not_reextract():
    """Rows must round-trip via extract names (primary_name), not display
    names: shipped configs contain items (e.g. cash, nwc) whose display name
    is not one of their extract names, which would silently drop the row."""
    df = pd.DataFrame(
        {"Cash": [50.0], "Debt": [400.0]}, index=pd.to_datetime(["2023-12-31"])
    ).T
    items = [
        # display name deliberately not extractable; only "cash" is
        ItemConfig(
            key="cash",
            display_name="Cash and Cash Equivalents",
            extract_names=["cash"],
        ),
        ItemConfig(key="debt", display_name="Debt", extract_names=["debt"]),
    ]
    stmts = FinancialStatements.from_df(
        df,
        [StatementConfig(key="s", display_name="S", items_config_list=items)],
        disp_unextracted=False,
        recompute_calculated=True,
    )

    adjusted = Transaction(date="2023-12-31", entries=[Entry("cash", 25.0)]).apply(stmts)

    assert float(adjusted.cash.iloc[0]) == 75.0
    assert float(adjusted.debt.iloc[0]) == 400.0


# ---------------------------------------------------------------- waterfall

def test_waterfall_sweep_hand_checked():
    stmts = lbo_statements()
    waterfall = Waterfall(
        source="cash_available",
        steps=[Pay("debt", 20.0), Sweep("debt", 0.5), Residual("cash")],
    )
    result = waterfall.apply(stmts, periods=2)

    # Period 1: interest = 40, taxes = 15, available = 45
    #   pay 20 -> debt 380; sweep 0.5 * 25 = 12.5 -> debt 367.5; residual 12.5
    assert result.source.iloc[0] == pytest.approx(45.0)
    assert result.balances["debt"].iloc[0] == pytest.approx(367.5)
    assert result.payments["pay_debt"].iloc[0] == pytest.approx(20.0)
    assert result.payments["sweep_debt"].iloc[0] == pytest.approx(12.5)
    assert result.residual.iloc[0] == pytest.approx(12.5)

    # Period 2: interest = 36.75, taxes = 15.8125, available = 47.4375
    #   pay 20 -> 347.5; sweep 13.71875 -> 333.78125; residual 13.71875
    assert result.source.iloc[1] == pytest.approx(47.4375)
    assert result.balances["debt"].iloc[1] == pytest.approx(333.78125)
    assert result.residual.iloc[1] == pytest.approx(13.71875)


def test_waterfall_pay_limited_by_balance_and_cash():
    stmts = lbo_statements()
    waterfall = Waterfall(
        source="cash_available",
        steps=[Pay("debt", 1000.0), Residual("cash")],
    )
    result = waterfall.apply(stmts, periods=1)
    # available 45 < scheduled 1000 -> pay all 45, nothing residual
    assert result.payments["pay_debt"].iloc[0] == pytest.approx(45.0)
    assert result.balances["debt"].iloc[0] == pytest.approx(355.0)
    assert result.residual.iloc[0] == pytest.approx(0.0)


def test_waterfall_result_identities_hold_post_step():
    """Same-period identities in the result must reflect post-step balances,
    not the pre-payment values."""
    df = pd.DataFrame(
        {"EBITDA": [100.0], "Debt A": [200.0], "Debt B": [200.0], "Cash": [50.0]},
        index=pd.to_datetime(["2023-12-31"]),
    ).T

    def calc(key, name, extract, expr):
        return ItemConfig(
            key=key, display_name=name, extract_names=[extract], expr_str=expr,
            forecast=ForecastItemConfig(make_forecast=False),
        )

    items = [
        ItemConfig(key="ebitda", display_name="EBITDA", extract_names=["ebitda"],
                   forecast=ForecastItemConfig(method="recent")),
        ItemConfig(key="debt_a", display_name="Debt A", extract_names=["debt a"],
                   forecast=ForecastItemConfig(method="recent")),
        ItemConfig(key="debt_b", display_name="Debt B", extract_names=["debt b"],
                   forecast=ForecastItemConfig(method="recent")),
        ItemConfig(key="cash", display_name="Cash", extract_names=["cash"],
                   forecast=ForecastItemConfig(method="recent")),
        calc("interest", "Interest", "interest", "0.10 * (debt_a[t-1] + debt_b[t-1])"),
        calc("total_debt", "Total Debt", "total debt", "debt_a[t] + debt_b[t]"),
        calc("cash_available", "Cash Available", "cash available",
             "ebitda[t] - interest[t]"),
    ]
    stmts = FinancialStatements.from_df(
        df,
        [StatementConfig(key="s", display_name="S", items_config_list=items)],
        disp_unextracted=False,
        recompute_calculated=True,
    )
    waterfall = Waterfall(
        source="cash_available", steps=[Pay("debt_a", 30.0), Residual("cash")]
    )

    result = waterfall.apply(stmts, periods=1)

    assert result.values["debt_a"].iloc[0] == pytest.approx(170.0)
    assert result.values["total_debt"].iloc[0] == pytest.approx(370.0)


def test_irr_npv_treat_missing_flows_as_zero():
    """A NaN flow is no flow; dropping it would shift later flows earlier."""
    assert irr([-100.0, float("nan"), 0.0, 121.0]) == pytest.approx(
        1.21 ** (1 / 3) - 1, abs=1e-6
    )
    assert npv([-100.0, float("nan"), 110.0], 0.10) == pytest.approx(
        -100 + 110 / 1.21
    )


# --------------------------------------------------------------------- deal

def test_deal_end_to_end():
    stmts = lbo_statements()
    deal = Deal(
        entry_equity=336.0,
        waterfall=Waterfall(
            source="cash_available",
            steps=[Pay("debt", 20.0), Sweep("debt", 0.5), Residual("cash")],
        ),
        exit=ExitTerms(period=2, multiple=8.0, on="ebitda", less_debt=["debt"]),
        metrics=[Metric("leverage", expr="debt / ebitda")],
    )
    result = deal.apply(stmts, periods=3)

    # exit EV = 8 x 100 = 800; equity = 800 - 333.78125
    assert result.exit_enterprise_value == pytest.approx(800.0)
    assert result.exit_equity_value == pytest.approx(800.0 - 333.78125)

    flows = list(result.equity_cashflows.values)
    assert flows[0] == pytest.approx(-336.0)
    assert flows[1] == pytest.approx(12.5)
    assert flows[2] == pytest.approx(13.71875 + 800.0 - 333.78125)
    assert len(flows) == 3  # truncated at exit

    assert result.moic == pytest.approx((12.5 + 13.71875 + 466.21875) / 336.0)
    assert result.irr is not None and 0.1 < result.irr < 0.5
    assert list(result.metrics["leverage"].values)[0] == pytest.approx(367.5 / 100)
