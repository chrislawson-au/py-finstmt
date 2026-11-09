"""Run inside Pyodide by pyodide_smoke.mjs: build, forecast and price a tiny model."""

import os

# Node has no DOM for Pyodide's browser backend; draw nothing, headlessly
os.environ["MPLBACKEND"] = "Agg"

import pandas as pd  # noqa: E402

import finstmt  # noqa: E402
from finstmt import (  # noqa: E402
    FinancialStatements,
    ForecastItemConfig,
    ItemConfig,
    StatementConfig,
)
from finstmt.deals import irr  # noqa: E402

income = StatementConfig(
    key="inc",
    display_name="Income Statement",
    items_config_list=[
        ItemConfig(
            "revenue",
            "Revenue",
            extract_names=["revenue"],
            forecast=ForecastItemConfig(method="cagr"),
        ),
        ItemConfig(
            "cogs",
            "Cost of Goods Sold",
            extract_names=["cogs"],
            forecast=ForecastItemConfig(method="mean", pct_of="revenue"),
        ),
        ItemConfig(
            "gross_profit",
            "Gross Profit",
            expr_str="revenue[t] - cogs[t]",
            forecast=ForecastItemConfig(make_forecast=False),
        ),
    ],
)
history = pd.DataFrame(
    {
        "2022-12-31": [100.0, 60.0],
        "2023-12-31": [110.0, 65.0],
        "2024-12-31": [121.0, 70.0],
    },
    index=["Revenue", "COGS"],
)
stmts = FinancialStatements.from_df(
    history, [income], disp_unextracted=False, recompute_calculated=True
)
forecast = stmts.forecast(periods=2)

assert round(forecast.revenue.iloc[0], 2) == 133.10, forecast.revenue
assert round(forecast.gross_profit.iloc[1], 2) == 60.06, forecast.gross_profit
assert round(irr([-100, 10, 10, 120]), 4) == 0.1294
print(f"finstmt {finstmt.__version__} OK in Pyodide with pandas {pd.__version__}")
