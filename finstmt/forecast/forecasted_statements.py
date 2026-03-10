import math
import warnings
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
from typing_extensions import Self

from finstmt._plot_helpers import get_selected_ax, is_last_plot_in_col, plot_finished
from finstmt.core.statements import FinancialStatements
from finstmt.forecast.forecast_item_series import ForecastItemSeries

NUM_PLOT_COLUMNS = 3
DEFAULT_WIDTH = 15
DEFAULT_HEIGHT_PER_ROW = 3


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

        num_plot_rows = math.ceil(len(plot_items) / num_cols)
        num_plot_columns = min(len(plot_items), num_cols)

        if figsize is None:
            figsize = (plot_width, height_per_row * num_plot_rows)

        fig, axes = plt.subplots(
            num_plot_rows, num_plot_columns, sharex=False, sharey=False, figsize=figsize
        )
        row = 0
        col = 0
        with warnings.catch_warnings():
            warnings.filterwarnings(
                action="ignore", message="Attempting to set identical bottom == top"
            )
            for i, (item_key, forecast) in enumerate(plot_items.items()):
                selected_ax = get_selected_ax(
                    axes, row, col, num_plot_rows, num_plot_columns
                )
                forecast.plot(ax=selected_ax)

                # For before final row, don't display x-axis
                if not is_last_plot_in_col(
                    row, col, num_plot_rows, num_plot_columns, len(plot_items)
                ):
                    selected_ax.get_xaxis().set_visible(False)

                if i == len(plot_items) - 1 or plot_finished(
                    row, col, num_plot_rows, num_plot_columns
                ):
                    break
                col += 1
                if col == num_plot_columns:
                    row += 1
                    col = 0
        while not plot_finished(row, col, num_plot_rows, num_plot_columns):
            col += 1
            if col == num_plot_columns:
                row += 1
                col = 0
            fig.delaxes(axes[row][col])
        return fig
