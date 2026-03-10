from typing import Type

from finstmt.config.item import ForecastItemConfig
from finstmt.config.forecast import ForecastConfig
from finstmt.forecast.models.average import AverageModel
from finstmt.forecast.models.base import ForecastModel
from finstmt.forecast.models.cagr import CAGRModel
from finstmt.forecast.models.manual import ManualForecastModel
from finstmt.forecast.models.prophet import ProphetModel
from finstmt.forecast.models.recent import RecentValueModel
from finstmt.forecast.models.trend import LinearTrendModel
from finstmt.config.item import ItemConfig


def get_model(
    config: ForecastConfig, item_config: ItemConfig
) -> ForecastModel:
    model_class: Type[ForecastModel]
    if item_config.forecast.method == "auto":
        model_class = ProphetModel
    elif item_config.forecast.method == "trend":
        model_class = LinearTrendModel
    elif item_config.forecast.method == "cagr":
        model_class = CAGRModel
    elif item_config.forecast.method == "mean":
        model_class = AverageModel
    elif item_config.forecast.method == "recent":
        model_class = RecentValueModel
    elif item_config.forecast.method == "manual":
        model_class = ManualForecastModel
    else:
        raise NotImplementedError(f"need to implement method {item_config.forecast.method}")

    return model_class(config, item_config)
