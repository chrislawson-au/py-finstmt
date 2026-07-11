import pytest

from finstmt.config.item import VALID_FORECAST_METHODS, ForecastItemConfig


def test_invalid_forecast_method_raises_with_valid_options():
    with pytest.raises(ValueError) as exc_info:
        ForecastItemConfig(method="average")

    assert "average" in str(exc_info.value)
    assert "mean" in str(exc_info.value)


def test_all_valid_forecast_methods_are_accepted():
    for method in VALID_FORECAST_METHODS:
        config = ForecastItemConfig(method=method)
        assert config.method == method


def test_chooser_has_a_model_for_every_valid_method():
    from finstmt.forecast.models.chooser import MODEL_BY_METHOD

    assert set(MODEL_BY_METHOD) == set(VALID_FORECAST_METHODS)
