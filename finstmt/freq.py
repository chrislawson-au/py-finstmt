"""Frequency inference helpers."""

import warnings
from typing import List, Optional, Sequence

import pandas as pd
from pandas.tseries.frequencies import to_offset


def _first_valid_freq(*candidates: str) -> str:
    """Return the first alias this pandas version accepts without complaint.

    pandas 2.2+ renamed month-end aliases from ``M`` to ``ME`` (the old
    spelling emits a FutureWarning before removal); older versions only
    accept ``M``. Treat a deprecation warning as a rejection so the returned
    alias never causes downstream ``date_range`` calls to warn.
    """
    for candidate in candidates:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", FutureWarning)
                to_offset(candidate)
            return candidate
        except (ValueError, FutureWarning):
            continue
    return candidates[-1]


def infer_freq_or_default(
    dates: Sequence[pd.Timestamp], default: Optional[str] = None
) -> Optional[str]:
    """Infer the frequency of a date index, tolerating short histories.

    ``pd.infer_freq`` requires at least three dates. Models built from one or
    two historical periods are common (e.g. a single starting year that is
    then forecast forward), so fall back to estimating from the spacing of two
    dates, or to annual for a single date.

    Returns ``None`` only when there are three or more dates and pandas cannot
    infer a frequency (genuinely mixed frequencies) so callers can raise their
    usual error.
    """
    annual = _first_valid_freq("12ME", "12M")
    if default is None:
        default = annual

    date_list: List[pd.Timestamp] = list(dates)
    if len(date_list) >= 3:
        return pd.infer_freq(date_list)
    if len(date_list) == 2:
        days = abs((date_list[1] - date_list[0]).days)
        if days >= 300:
            return annual
        if days >= 80:
            return _first_valid_freq("3ME", "3M")
        if days >= 25:
            return _first_valid_freq("1ME", "1M")
        return default
    return default
