from typing import Dict, Type

from finstmt.config.forecast import ForecastConfig
from finstmt.config.item import ItemConfig
from finstmt.forecast.models.average import AverageModel
from finstmt.forecast.models.base import ForecastModel
from finstmt.forecast.models.cagr import CAGRModel
from finstmt.forecast.models.manual import ManualForecastModel
from finstmt.forecast.models.prophet import ProphetModel
from finstmt.forecast.models.recent import RecentValueModel
from finstmt.forecast.models.trend import LinearTrendModel

MODEL_BY_METHOD: Dict[str, Type[ForecastModel]] = {
    "auto": ProphetModel,
    "trend": LinearTrendModel,
    "cagr": CAGRModel,
    "mean": AverageModel,
    "recent": RecentValueModel,
    "manual": ManualForecastModel,
}


def get_model(config: ForecastConfig, item_config: ItemConfig) -> ForecastModel:
    try:
        model_class = MODEL_BY_METHOD[item_config.forecast.method]
    except KeyError:
        raise NotImplementedError(
            f"no forecast model for method {item_config.forecast.method!r}; "
            f"must be one of {sorted(MODEL_BY_METHOD)}"
        ) from None
    return model_class(config, item_config)
