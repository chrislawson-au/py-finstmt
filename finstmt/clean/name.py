import string

import pandas as pd


def standardize_names_in_series_index(series: pd.Series):
    """
    Used internally to standardize names in DataFrames before looking up in name configs to match DataFrame
    data to data classes

    Note: inplace
    """
    series.index = [standardize_name_for_look_up(name) for name in series.index]


def standardize_name_for_look_up(name: str) -> str:
    """
    Used internally to standardize names in DataFrames before looking up in name configs to match DataFrame
    data to data classes
    """
    name = name.lower().strip()
    name = ' '.join(name.split('_'))
    name = name.translate(str.maketrans('', '', string.punctuation))  # remove punctuation
    return name
