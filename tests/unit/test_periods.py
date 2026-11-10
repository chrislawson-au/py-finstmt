import pandas as pd
from sympy import IndexedBase

from finstmt.config.item import ItemConfig
from finstmt.solver.engine import (
    results_dict_to_sympy_dict,
    sympy_dict_to_results_dict,
)
from finstmt.solver.periods import FORECAST_INDEXING, HISTORICAL_INDEXING


def test_historical_indexing_is_zero_based():
    assert HISTORICAL_INDEXING.sympy_index(0) == 0
    assert HISTORICAL_INDEXING.position(2) == 2


def test_forecast_indexing_anchors_last_historical_at_zero():
    # Forecast period n (0-based position in the forecast dates) is sympy
    # index n + 1; sympy index 0 is the last historical period.
    assert FORECAST_INDEXING.sympy_index(0) == 1
    assert FORECAST_INDEXING.position(1) == 0
    assert FORECAST_INDEXING.position(0) == -1  # last historical: before dates


def test_results_and_sympy_dicts_round_trip_with_forecast_indexing():
    revenue = IndexedBase("revenue")
    ns = {"revenue": revenue}
    configs = [
        ItemConfig(key="revenue", display_name="Revenue", extract_names=["revenue"])
    ]
    dates = pd.DatetimeIndex(["2024-12-31", "2025-12-31"])
    results = {"revenue": pd.Series([100.0, 110.0], index=dates, name="revenue")}

    s_dict = results_dict_to_sympy_dict(results, ns)
    assert s_dict == {revenue[1]: 100.0, revenue[2]: 110.0}

    back = sympy_dict_to_results_dict(s_dict, dates, configs, FORECAST_INDEXING)
    assert list(back["revenue"]) == [100.0, 110.0]
