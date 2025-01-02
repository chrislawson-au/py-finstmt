import dataclasses
import operator
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Sequence, Tuple, TypeVar, Union

import matplotlib.pyplot as plt
import pandas as pd
from typing_extensions import Self

from finstmt.exc import ForecastNotFitException, ForecastNotPredictedException
from finstmt.findata.item_forecast_config import ForecastItemConfig
from finstmt.forecast.config import ForecastConfig
from finstmt.forecast.models.chooser import get_model
from finstmt.forecast.models.manual import ManualForecastModel
from finstmt.findata.item_config import ItemConfig

T = TypeVar("T")


@dataclass
class ForecastItemSeries:
    """
    The main class to represent a forecast of an individual item.
    """

    orig_series: pd.Series
    config: ForecastConfig
    item_config: ItemConfig
    pct_of_series: Optional[pd.Series] = None
    pct_of_config: Optional[ItemConfig] = None
    _result: Optional[pd.Series] = None  # Changed from result to _result
    _result_pct: Optional[pd.Series] = None  # Changed from result_pct to _result_pct

    def __post_init__(self):
        self.model = get_model(self.config, self.item_config)

    def fit(self):
        self.model.fit(self.series)

    def predict(self) -> pd.Series:
        if not self.model.has_been_fit:
            raise ForecastNotFitException("call .fit before .predict")
        result = self.model.predict()
        
        # if result is not None:
        #     self._result.name = self.item_config.primary_name

        # Handle percentage result if needed
        if (self.item_config.forecast_config.pct_of is not None):
            self._result_pct = result
        else:                    # Store results
            self._result = result
                        
        return result

    def plot(
        self, ax: Optional[plt.Axes] = None, figsize: Tuple[int, int] = (12, 5)
    ) -> plt.Figure:
        if not self.model.has_prediction:
            raise ForecastNotPredictedException("call .predict before .plot")
        return self.model.plot(ax=ax, figsize=figsize, title=self.name)

    def to_manual(
        self,
        use_levels: bool = False,
        adjustments: Optional[Union[Sequence[float], Dict[int, float]]] = None,
        replacements: Optional[Union[Sequence[float], Dict[int, float]]] = None,
    ):
        if not self.model.has_prediction:
            raise ForecastNotPredictedException(
                "call .fit then .predict before .to_manual"
            )

        if use_levels:
            values = self._result.values  # Changed from result to _result
        else:
            # Growth
            values = self._result.pct_change().values  # Changed from result to _result
            # Fill in first growth
            values[0] = (self._result.iloc[0] - self.series.iloc[-1]) / self.series.iloc[
                -1
            ]

        self.item_config.forecast_config.method = "manual"

        if adjustments is not None:
            if not isinstance(adjustments, dict) and len(adjustments) != len(values):
                raise ValueError(
                    f"must pass equal length adjustments as number of periods. "
                    f"Got {len(adjustments)} adjustments for {len(values)} periods"
                )
            adjustments = _adjust_to_dict(adjustments)
            for i, adj in adjustments.items():
                values[i] += adj

        if replacements is not None:
            if not isinstance(replacements, dict) and len(replacements) != len(values):
                raise ValueError(
                    f"must pass equal length adjustments as number of periods. "
                    f"Got {len(replacements)} adjustments for {len(values)} periods"
                )
            replacements = _replace_to_dict(replacements)
            for i, replace in replacements.items():
                values[i] = replace

        self.item_config.forecast_config.manual_forecasts["type"] = "levels" if use_levels else "growth"
        self.item_config.forecast_config.manual_forecasts["values"] = list(values)
        self.model = ManualForecastModel(
            self.config, self.item_config
        )
        self.model.fit(self.series)
        self.model.predict()

    @property
    def series(self) -> pd.Series:
        if self.pct_of_series is None:
            return self.orig_series
        else:
            return self.orig_series / self.pct_of_series

    @property
    def result(self) -> pd.Series:
        if not self.model.has_prediction:
            raise ForecastNotPredictedException(
                "call .fit then .predict before .result"
            )
        # return self.model.result
        return self._result

    @property
    def result_pct(self) -> Optional[pd.Series]:
        """Get percentage forecast result if applicable"""
        return self._result_pct

    @property
    def name(self) -> str:
        if self.pct_of_config is None:
            return self.item_config.display_name

        # Percentage of series
        return f"{self.item_config.display_name} % {self.pct_of_config.display_name}"

    def copy(self, **updates) -> Self:
        return dataclasses.replace(self, **updates)

    def __round__(self, n: Optional[int] = None) -> "Forecast":
        return _apply_operation_to_forecast(self, n, round)  # type: ignore[arg-type]

    def __add__(self, other: T) -> "Forecast":
        return _apply_operation_to_forecast(self, other, operator.add)

    def __sub__(self, other: T) -> "Forecast":
        return _apply_operation_to_forecast(self, other, operator.sub)

    def __mul__(self, other: T) -> "Forecast":
        return _apply_operation_to_forecast(self, other, operator.mul)

    def __truediv__(self, other: T) -> "Forecast":
        return _apply_operation_to_forecast(self, other, operator.truediv)


def _apply_operation_to_forecast(
    forecast: ForecastItemSeries,
    other: T,
    func: Callable[[Any, T], Any],
) -> ForecastItemSeries:
    updates: Dict[str, Any] = {}
    updates["orig_series"] = func(
        forecast.orig_series, _get_attr_if_needed(other, "orig_series")
    )
    if forecast.pct_of_series is not None:
        updates["pct_of_series"] = func(
            forecast.pct_of_series, _get_attr_if_needed(other, "pct_of_series")
        )
    if forecast.pct_of_config is not None:
        updates["pct_of_config"] = func(
            forecast.pct_of_config, _get_attr_if_needed(other, "pct_of_config")
        )
    updates["forecast_item_config"] = func(
        forecast.forecast_item_config, _get_attr_if_needed(other, "forecast_item_config")
    )
    updates["item_config"] = func(
        forecast.item_config, _get_attr_if_needed(other, "item_config")
    )
    return forecast.copy(**updates)


def _get_attr_if_needed(other: Any, attr: str) -> Any:
    if isinstance(other, Forecast):
        return getattr(other, attr)
    else:
        return other


def _adjust_to_dict(
    seq_or_dict: Union[Sequence[float], Dict[int, float]]
) -> Dict[int, float]:
    if isinstance(seq_or_dict, dict):
        return seq_or_dict

    # If adjustment is 0 or None, skip the entry, otherwise add to the dict
    adjust_dict = {i: val for i, val in enumerate(seq_or_dict) if val}
    return adjust_dict


def _replace_to_dict(
    seq_or_dict: Union[Sequence[float], Dict[int, float]]
) -> Dict[int, float]:
    if isinstance(seq_or_dict, dict):
        return seq_or_dict

    replace_dict = {i: val for i, val in enumerate(seq_or_dict)}
    return replace_dict