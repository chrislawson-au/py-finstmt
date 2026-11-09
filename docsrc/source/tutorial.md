# Getting started with finstmt

## Install

finstmt 2.0 is in alpha and installs from GitHub (Python 3.12 or newer):

```
pip install "finstmt @ git+https://github.com/chrislawson-au/py-finstmt@v2.0.0-alpha.1"
```

Use `finstmt[forecast] @ git+...` to add Prophet for the `auto` forecast method.

## Usage

Load an income statement and a balance sheet with the bundled configs. The
DataFrame needs item names as its index and one column per period:

```
import pandas as pd

from finstmt import FinancialStatements
from finstmt.config.statement import STATEMENT_CONFIGS

inc_df = pd.read_excel("WMT Income Statement.xlsx", index_col=0)
bs_df = pd.read_excel("WMT Balance Sheet.xlsx", index_col=0)
stmts = FinancialStatements.from_df(pd.concat([inc_df, bs_df]), STATEMENT_CONFIGS)
```

## Forecasting

`stmts.forecast(periods=5)` returns `ForecastedStatements`. Choose a method per
item with `stmts.config.update(key, ["forecast", "method"], method)`:

- `auto`: Prophet (needs the `forecast` extra)
- `trend`: a linear trend regression
- `cagr`: the compound annual growth rate (the default)
- `mean`: the historical average
- `recent`: the most recent value
- `manual`: levels or growth rates you supply

See the example notebooks, and MIGRATION.md in the repository for 1.x users.
