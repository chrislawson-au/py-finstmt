import warnings

import pandas as pd
import pytest
from pandas.tseries.frequencies import to_offset

from finstmt.freq import infer_freq_or_default


def _offset_without_deprecation(alias: str):
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        return to_offset(alias)


def test_two_annual_dates_infer_annual():
    dates = pd.DatetimeIndex(["2022-12-31", "2023-12-31"])
    freq = infer_freq_or_default(dates)
    offset = _offset_without_deprecation(freq)
    assert offset == to_offset(pd.DateOffset(months=12)) or "12M" in freq.upper()


def test_two_quarterly_dates_infer_quarterly():
    dates = pd.DatetimeIndex(["2023-03-31", "2023-06-30"])
    freq = infer_freq_or_default(dates)
    assert freq.upper().startswith("3M")
    _offset_without_deprecation(freq)


def test_two_monthly_dates_infer_monthly():
    dates = pd.DatetimeIndex(["2023-01-31", "2023-02-28"])
    freq = infer_freq_or_default(dates)
    assert freq.upper().startswith("1M")
    _offset_without_deprecation(freq)


def test_single_date_defaults_to_annual():
    dates = pd.DatetimeIndex(["2023-12-31"])
    freq = infer_freq_or_default(dates)
    assert freq.upper().startswith("12M")
    _offset_without_deprecation(freq)


def test_three_or_more_dates_delegate_to_pandas():
    regular = pd.DatetimeIndex(["2021-12-31", "2022-12-31", "2023-12-31"])
    assert infer_freq_or_default(regular) == pd.infer_freq(regular)

    mixed = pd.DatetimeIndex(["2021-12-31", "2022-03-31", "2023-12-31"])
    assert infer_freq_or_default(mixed) is None


def test_inferred_freq_is_not_a_deprecated_alias():
    # The fallback must prefer whichever alias this pandas version accepts
    # without a FutureWarning, or downstream date_range calls will warn on
    # every forecast
    for dates in [
        pd.DatetimeIndex(["2022-12-31", "2023-12-31"]),
        pd.DatetimeIndex(["2023-12-31"]),
    ]:
        freq = infer_freq_or_default(dates)
        _offset_without_deprecation(freq)


def test_two_period_statement_has_usable_freq():
    from finstmt.config.item import ItemConfig
    from finstmt.core.statement_series import StatementSeries

    config = [ItemConfig(key="revenue", display_name="Revenue", extract_names=["revenue"])]
    data = {"12/31/2022": {"revenue": 1000}, "12/31/2023": {"revenue": 1100}}
    stmt = StatementSeries.from_dict(data, "Income Statement", config)

    freq = stmt.freq

    assert freq is not None
    pd.date_range("2023-12-31", periods=3, freq=freq)
