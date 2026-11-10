"""Period-index conventions for the solvers.

The sympy equation system indexes items as ``key[i]``. What ``i`` means
depends on the solver:

- :data:`HISTORICAL_INDEXING`: ``i`` is the position in the historical dates
  (0-based). Used by ``HistoricalSolver``.
- :data:`FORECAST_INDEXING`: ``i == 0`` is the *last historical* period, and
  forecast periods are 1-based — ``key[n]`` is the n'th forecasted period,
  at position ``n - 1`` in the forecast dates / result arrays. Used by
  ``ForecastSolver`` and the plug machinery.

All conversion between sympy indices and array positions should go through
one of these objects rather than ad-hoc ``+1``/``-1`` arithmetic.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PeriodIndexing:
    """Maps between sympy time indices and 0-based positions in a dates array.

    :param offset: The sympy index corresponding to position 0.
    """

    offset: int

    def sympy_index(self, position: int) -> int:
        """The sympy time index for a 0-based position in the dates array."""
        return position + self.offset

    def position(self, sympy_index: int) -> int:
        """The 0-based position in the dates array for a sympy time index.

        May be negative for indices before the dates array (e.g. the last
        historical period under forecast indexing).
        """
        return sympy_index - self.offset


HISTORICAL_INDEXING = PeriodIndexing(offset=0)
FORECAST_INDEXING = PeriodIndexing(offset=1)
