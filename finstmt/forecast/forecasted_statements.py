from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
from typing_extensions import Self

from finstmt._plot_helpers import (
    DEFAULT_HEIGHT_PER_ROW,
    DEFAULT_WIDTH,
    NUM_PLOT_COLUMNS,
    plot_grid,
)
from finstmt.core.statements import FinancialStatements
from finstmt.forecast.forecast_item_series import ForecastItemSeries


@dataclass
class ForecastedStatements(FinancialStatements):
    """Financial statements extended with forecast data.

    Inherits all capabilities of :class:`FinancialStatements` and adds
    forecast-specific features like plotting forecasted vs. historical values.

    The ``forecasts`` dict holds :class:`ForecastItemSeries` objects keyed by
    item key, used for plotting. Accessing item attributes (e.g.
    ``forecasted.revenue``) returns the forecasted values as a ``pd.Series``.

    Examples:
        >>> forecasted = stmts.forecast(periods=5)
        >>> forecasted.revenue  # pd.Series of forecasted revenue
        >>> forecasted.plot()   # plot all forecasted items
    """
    forecasts: Dict[str, ForecastItemSeries] = field(default_factory=lambda: {})

    def __round__(self, n: Optional[int] = None) -> Self:
        result = super().__round__(n)
        new_forecasts = {k: round(v, n) for k, v in self.forecasts.items()}
        return result.copy(forecasts=new_forecasts)

    def _apply_op(self, other: Any, op: Callable) -> Self:
        """Apply arithmetic to both statements and forecasts."""
        result = super()._apply_op(other, op)
        if isinstance(other, (float, int)):
            new_forecasts = {k: op(v, other) for k, v in self.forecasts.items()}
        elif hasattr(other, 'forecasts'):
            new_forecasts = {k: op(v, other.forecasts[k]) for k, v in self.forecasts.items()}
        else:
            new_forecasts = self.forecasts
        return result.copy(forecasts=new_forecasts)

    def plot(
        self,
        subset: Optional[Sequence[str]] = None,
        figsize: Optional[Tuple[float, float]] = None,
        num_cols: int = NUM_PLOT_COLUMNS,
        height_per_row: float = DEFAULT_HEIGHT_PER_ROW,
        plot_width: float = DEFAULT_WIDTH,
    ) -> plt.Figure:
        if subset is not None:
            plot_items = {k: v for k, v in self.forecasts.items() if k in subset}
        else:
            plot_items = self.forecasts

        return plot_grid(
            plot_items,
            figsize=figsize,
            num_cols=num_cols,
            height_per_row=height_per_row,
            plot_width=plot_width,
        )
