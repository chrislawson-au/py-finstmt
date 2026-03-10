"""Shared helper functions for matplotlib grid plotting."""

import matplotlib.pyplot as plt
from matplotlib.axes import Subplot


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
