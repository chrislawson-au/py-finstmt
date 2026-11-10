# py-finstmt

[![CI](https://github.com/chrislawson-au/py-finstmt/actions/workflows/package.yml/badge.svg?branch=master)](https://github.com/chrislawson-au/py-finstmt/actions/workflows/package.yml)
![Python 3.12 to 3.15](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14%20%7C%203.15-blue)
![MIT license](https://img.shields.io/badge/license-MIT-green)

Work with financial statement data in Python. finstmt loads income statements
and balance sheets, calculates derived items such as free cash flow, forecasts
the statements while keeping the balance sheet balanced, and models deals
(transactions, debt waterfalls, IRR and MOIC) on top of a forecast.

> **finstmt 2.0 is in alpha.** This fork of
> [nickderobertis/py-finstmt](https://github.com/nickderobertis/py-finstmt)
> restructures the API. Code written for 1.x needs changes: see
> [MIGRATION.md](MIGRATION.md). The 1.x releases remain on PyPI.

## Install

2.0 is not on PyPI yet. Install the alpha from its tag (Python 3.12 or newer):

```bash
pip install "finstmt @ git+https://github.com/chrislawson-au/py-finstmt@v2.0.0-alpha.1"
```

The `forecast` extra adds Prophet, which the `auto` forecast method uses:

```bash
pip install "finstmt[forecast] @ git+https://github.com/chrislawson-au/py-finstmt@v2.0.0-alpha.1"
```

## Quick start

Describe the line items, load their history, and forecast:

```python
import pandas as pd

from finstmt import FinancialStatements, ForecastItemConfig, ItemConfig, StatementConfig

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
    {"2022-12-31": [100.0, 60.0], "2023-12-31": [110.0, 65.0], "2024-12-31": [121.0, 70.0]},
    index=["Revenue", "COGS"],
)
stmts = FinancialStatements.from_df(history, [income], recompute_calculated=True)

forecast = stmts.forecast(periods=2)
assert forecast.revenue.round(2).tolist() == [133.1, 146.41]  # 10% CAGR
assert forecast.gross_profit.round(2).tolist() == [54.6, 60.06]  # COGS at its mean share of revenue
```

Rows match an item when their label equals one of its `extract_names` once
the label is standardized (lower-cased, punctuation removed), so write
`extract_names` in lower case. Calculated items use `expr_str`, where
`[t]` is the current period and `[t-1]` the previous one.

Deal metrics work on any cash flow series:

```python
from finstmt.deals import irr, moic

flows = [-100, 10, 10, 120]
assert round(irr(flows), 4) == 0.1294
assert moic(flows) == 1.4
```

## Reported statements

finstmt ships configs for a standard income statement, balance sheet and a
metrics statement (free cash flow and friends). This uses the sample data in
this repository:

```python
from finstmt.config.statement import STATEMENT_CONFIGS

income_df = pd.read_csv("tests/sources/stockrow/CAT/annual_income.csv", index_col=0)
balance_df = pd.read_csv("tests/sources/stockrow/CAT/annual_bs.csv", index_col=0)

cat = FinancialStatements.from_df(pd.concat([income_df, balance_df]), STATEMENT_CONFIGS)
cat.revenue  # a pandas Series indexed by period end
cat.fcf  # free cash flow
```

## More

- [MIGRATION.md](MIGRATION.md): moving from 1.x to 2.0.
- [nbexamples/](nbexamples/): notebooks on forecasting and on combining and
  scaling statements.
- [DEVELOPING.md](DEVELOPING.md): development setup, including the local Sphinx
  docs (`just docs`).

## Credits

Created by Nick DeRobertis. The 2.0 restructure and the deals layer are
developed in this fork by [chrislawson-au](https://github.com/chrislawson-au).
MIT License.
