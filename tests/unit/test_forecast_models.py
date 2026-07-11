from finstmt.config.forecast import ForecastConfig
from finstmt.config.item import ItemConfig
from finstmt.forecast.models.prophet import ProphetModel


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
