import pandas as pd

from finstmt.check import item_series_is_empty


def test_all_missing_is_empty():
    # A series with no data at all is empty; previously None/NaN made it
    # look non-empty and auto-adjust kept forecasting unforecastable items
    assert item_series_is_empty(pd.Series([None, None]))
    assert item_series_is_empty(pd.Series([float("nan")]))


def test_zeros_and_zero_nan_mix_are_empty():
    assert item_series_is_empty(pd.Series([0.0, 0.0]))
    assert item_series_is_empty(pd.Series([0.0, float("nan")]))


def test_any_value_is_not_empty():
    assert not item_series_is_empty(pd.Series([1.0, 0.0]))
    assert not item_series_is_empty(pd.Series([float("nan"), -5.0]))
