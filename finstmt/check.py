import pandas as pd


def item_series_is_empty(s: pd.Series) -> bool:
    """Whether an item series carries no meaningful data: every value is
    missing (None/NaN) or zero."""
    return bool((s.isna() | (s == 0)).all())
