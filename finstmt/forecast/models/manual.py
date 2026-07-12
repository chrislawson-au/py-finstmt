from typing import Optional

import pandas as pd

from finstmt.exceptions import ImproperManualForecastException
from finstmt.config.forecast import ForecastConfig
from finstmt.forecast.models.base import ForecastModel
from finstmt.config.item import ItemConfig

# TODO: updated this to be more generic, but could break backwards compatibility
# could consider having "levels" and "growth" for backwards compatibility for some time
class ManualForecastModel(ForecastModel):
    recent: Optional[float] = None

    def __init__(
        self,
        config: ForecastConfig,
        item_config: ItemConfig,
    ):
        super().__init__(config, item_config)
        self._set_manual_forecasts()
        self._validate()

    def _validate(self):
        if not self.forecast_values:
            raise ImproperManualForecastException("must provide values for manual forecast")
        # If only one value is provided, then repeat it for all periods
        if len(self.forecast_values) == 1:
            self.forecast_values = [self.forecast_values[0]] * self.config.periods
        elif len(self.forecast_values) != self.config.periods:
            raise ImproperManualForecastException(
                f"{len(self.forecast_values)} values were provided for {self.config.periods} forecast periods"
            )

    def _set_manual_forecasts(self):
        manual = self.item_config.forecast.manual_forecasts
        if manual.get("levels"):
            self.forecast_type = "levels"
            self.forecast_values = manual["levels"]
        elif manual.get("growth"):
            self.forecast_type = "growth"
            self.forecast_values = manual["growth"]
        else:
            self.forecast_type = "levels"
            self.forecast_values = []

    def fit(self, series: pd.Series):
        self.recent = series.iloc[-1]
        super().fit(series)

    def predict(self) -> pd.Series:
        if self.forecast_type == "growth":
            values = []
            last_value = self.recent
            for growth in self.forecast_values:
                next_value = last_value * (1 + growth)
                values.append(next_value)
                last_value = next_value
        else:
            values = self.forecast_values

        # name matches the "mean" column the other models' results carry
        self.result = pd.Series(values, index=self._future_date_range, name="mean")
        self.result_df = pd.DataFrame(
            pd.concat([self.orig_series, self.result]), columns=["mean"]
        )
        super().predict()
        return self.result
