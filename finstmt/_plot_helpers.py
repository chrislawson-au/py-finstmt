"""Shared helper functions for matplotlib grid plotting."""

import math
import warnings
from typing import Mapping, Optional, Tuple

import matplotlib.pyplot as plt
from matplotlib.axes import Subplot

NUM_PLOT_COLUMNS = 3
DEFAULT_WIDTH = 15
DEFAULT_HEIGHT_PER_ROW = 3


def plot_grid(
    plot_items: Mapping,
    figsize: Optional[Tuple[float, float]] = None,
    num_cols: int = NUM_PLOT_COLUMNS,
    height_per_row: float = DEFAULT_HEIGHT_PER_ROW,
    plot_width: float = DEFAULT_WIDTH,
) -> plt.Figure:
    """Plot each item in a grid layout. Items must have a ``plot(ax=...)`` method."""
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
        for i, item in enumerate(plot_items.values()):
            selected_ax = get_selected_ax(
                axes, row, col, num_plot_rows, num_plot_columns
            )
            item.plot(ax=selected_ax)

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
    plt.close()
    return fig


def plot_finished(row: int, col: int, max_rows: int, max_cols: int) -> bool:
    return row == max_rows - 1 and col == max_cols - 1


def get_selected_ax(
    axes: plt.GridSpec, row: int, col: int, num_plot_rows: int, num_plot_columns: int
) -> Subplot:
    if num_plot_rows == num_plot_columns == 1:
        return axes
    elif num_plot_rows == 1:
        return axes[col]
    elif num_plot_columns == 1:
        return axes[row]
    else:
        return axes[row, col]


def is_last_plot_in_col(
    row: int, col: int, num_plot_rows: int, num_plot_columns: int, num_plots: int
) -> bool:
    if row == num_plot_rows - 1:
        return True
    if row != num_plot_rows - 2:
        return False
    # In the next-to-last row. Determine if there is going to be a plot below.
    plot_number = row * num_plot_columns + (col + 1)
    return plot_number + num_plot_columns > num_plots
