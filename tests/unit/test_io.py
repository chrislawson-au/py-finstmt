import matplotlib

matplotlib.use("Agg")

import pandas as pd

from finstmt import FinancialStatements
from finstmt.config.item import ItemConfig
from finstmt.core.statement_series import StatementSeries

CONFIG = [
    ItemConfig(
        key="revenue",
        display_name="Revenue",
        extract_names=["revenue"],
    ),
    ItemConfig(
        key="cost",
        display_name="Cost",
        extract_names=["cost"],
    ),
]

DATA = {
    "12/31/2022": {"revenue": 1000, "cost": 600},
    "12/31/2023": {"revenue": 2000, "cost": 1100},
}


def _build_stmts() -> FinancialStatements:
    stmt = StatementSeries.from_dict(DATA, "Income Statement", CONFIG)
    return FinancialStatements([stmt])


def test_to_excel_separate_sheets(tmp_path):
    stmts = _build_stmts()
    path = str(tmp_path / "out.xlsx")

    stmts.to_excel(path)

    df = pd.read_excel(path, sheet_name="Income Statement", skiprows=1, index_col=0)
    assert df.loc["Revenue", "12/31/2022"] == 1000
    assert df.loc["Cost", "12/31/2023"] == 1100


def test_to_excel_single_sheet(tmp_path):
    stmts = _build_stmts()
    path = str(tmp_path / "out.xlsx")

    stmts.to_excel(path, separate_sheets=False)

    df = pd.read_excel(path, sheet_name="Financial Statements", header=None)
    assert (df == "Income Statement").any().any()


def test_plot_grid_smoke():
    stmts = _build_stmts()

    fig = stmts.plot()

    assert len(fig.axes) == 2
