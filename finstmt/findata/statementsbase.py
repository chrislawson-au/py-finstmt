from typing import Dict

import pandas as pd

from finstmt.findata.database import FinDataBase


class FinStatementsBase:
    statement_cls = FinDataBase  # to be overridden with individual class
    statements: Dict[pd.Timestamp, FinDataBase]

    def __post_init__(self):
        self.df = self.to_df()

    def _repr_html_(self):
        return self._formatted_df._repr_html_()

    @classmethod
    def from_df(cls, df: pd.DataFrame):
        statements_dict = {}
        for col in df.columns:
            statement = cls.statement_cls.from_series(df[col])
            statement_date = pd.to_datetime(col)
            statements_dict[statement_date] = statement
        return cls(statements_dict)

    def to_df(self) -> pd.DataFrame:
        all_series = []
        for date, statement in self.statements.items():
            series = statement.to_series()
            series.name = date
            all_series.append(series)
        return pd.concat(all_series, axis=1)

    @property
    def _formatted_df(self) -> pd.DataFrame:
        out_df = self.df.copy()
        out_df.columns = [col.strftime('%m/%d/%Y') for col in out_df.columns]
        return out_df.applymap(lambda x: f'${x:,.0f}')