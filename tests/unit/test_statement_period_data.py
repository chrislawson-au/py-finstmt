import warnings

import pandas as pd
import pytest

from finstmt.config.item import ItemConfig
from finstmt.core.statement_period_data import StatementPeriodData

CONFIGS = [
    ItemConfig(key="revenue", display_name="Revenue", extract_names=["revenue"]),
    ItemConfig(key="net_income", display_name="Net Income", extract_names=["net income"]),
]


def test_duplicate_display_names_extract_scalar():
    # The same label can appear twice in an extract, e.g. "Net Income" on
    # both the income statement and the cash flow statement. Label-based
    # access returns a Series for duplicated labels, which used to crash
    # with "truth value of a Series is ambiguous".
    series = pd.Series(
        [1000.0, 200.0, 200.0], index=["Revenue", "Net Income", "Net Income"]
    )

    period = StatementPeriodData.from_series(series, CONFIGS)

    assert period.net_income == 200.0
    assert isinstance(period.net_income, float)


def test_conflicting_duplicate_names_keep_first_and_warn():
    series = pd.Series(
        [1000.0, 200.0, 999.0], index=["Revenue", "Net Income", "Net Income"]
    )

    with pytest.warns(UserWarning, match="higher priority"):
        period = StatementPeriodData.from_series(series, CONFIGS)

    assert period.net_income == 200.0


def test_extract_name_priority_still_respected():
    configs = [
        ItemConfig(
            key="ebit",
            display_name="EBIT",
            extract_names=["ebit", "operating income"],
        )
    ]
    series = pd.Series([50.0, 77.0], index=["Operating Income", "EBIT"])

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        period = StatementPeriodData.from_series(series, configs)

    assert period.ebit == 77.0
