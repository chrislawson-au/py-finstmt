import pandas as pd
import pytest

from finstmt.config.forecast import ForecastConfig
from finstmt.config.item import ItemConfig
from finstmt.forecast.models.cagr import CAGRModel
from finstmt.forecast.models.prophet import ProphetModel


def _cagr_model() -> CAGRModel:
    return CAGRModel(
        ForecastConfig(),
        ItemConfig(key="revenue", display_name="Revenue", extract_names=["revenue"]),
    )


def test_cagr_uses_number_of_growth_periods():
    # Two 10% growth periods across three observations: CAGR is
    # (y_T / y_0) ** (1 / (T - 1)) - 1, not 1 / T
    series = pd.Series(
        [100.0, 110.0, 121.0],
        index=pd.DatetimeIndex(["2021-12-31", "2022-12-31", "2023-12-31"]),
    )
    model = _cagr_model()

    model.fit(series)

    assert model.cagr == pytest.approx(0.10)


def test_cagr_back_fit_reproduces_first_value():
    # The model's own fit-assessment walks back from the last value; at the
    # correct rate it must land on the first observed value
    series = pd.Series(
        [100.0, 110.0, 121.0],
        index=pd.DatetimeIndex(["2021-12-31", "2022-12-31", "2023-12-31"]),
    )
    model = _cagr_model()

    model.fit(series)

    implied_y0 = series.iloc[-1] / (1 + model.cagr) ** (len(series) - 1)
    assert implied_y0 == pytest.approx(series.iloc[0])


def test_cagr_single_period_falls_back_to_zero_growth():
    series = pd.Series([100.0], index=pd.DatetimeIndex(["2023-12-31"]))
    model = _cagr_model()

    with pytest.warns(UserWarning, match="only one period"):
        model.fit(series)

    assert model.cagr == 0
    assert model.stderr == 0


def test_to_manual_replacements_are_reflected_in_result():
    # The balance-plug write-back calls to_manual(use_levels=True,
    # replacements=...) and downstream consumers (including snapshot reprs)
    # read .result afterwards; it must reflect the replaced values, not the
    # stale pre-manual forecast. Historically this only worked because
    # .values returned a writable view - the write-back must be explicit.
    from finstmt.forecast.forecast_item_series import ForecastItemSeries

    series = pd.Series(
        [100.0, 110.0, 121.0],
        index=pd.DatetimeIndex(["2021-12-31", "2022-12-31", "2023-12-31"]),
    )
    fis = ForecastItemSeries(
        orig_series=series,
        config=ForecastConfig(periods=2, freq="Y"),
        item_config=ItemConfig(key="revenue", display_name="Revenue", extract_names=["revenue"]),
    )
    fis.fit()
    fis.predict()

    fis.to_manual(use_levels=True, replacements=[500.0, 600.0])

    assert list(fis.result.values) == [500.0, 600.0]
    assert fis.result.name == "mean"


def test_item_level_prophet_kwargs_override_global():
    config = ForecastConfig(prophet_kwargs={"n_changepoints": 10})
    item_config = ItemConfig(
        key="revenue",
        display_name="Revenue",
        extract_names=["revenue"],
    )
    item_config.forecast.prophet_kwargs = {"n_changepoints": 5}

    model = ProphetModel(config, item_config)

    assert model.model.n_changepoints == 5
