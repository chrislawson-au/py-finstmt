# Migrating from finstmt 1.x to 2.0

finstmt 2.0 builds every statement from configuration objects:
- one `StatementSeries` class, driven by a `StatementConfig`, replaces the 1.x
  class per statement;
- the solver was rewritten;
- a deals layer was added.

Forecasting and statement math work as before once the statements exist. Most
imports, and the way statements are built, change.

## Requirements

| | 1.x | 2.0 |
|---|---|---|
| Python | 3.8+ | 3.12+ |
| pandas | below 2.0 | 2.2 or newer, including 3.x |
| Runtime dependencies | pandas, sympy, xlrd, matplotlib, tqdm, statsmodels, typing-extensions | Adds numpy, scipy, pyyaml and xlsxwriter, which 1.x used without declaring. Drops typing-extensions. |
| Prophet (`auto` method) | `finstmt[forecast]` | `finstmt[forecast]` |

## Loading statements

1.x had a class per statement:

```py
from finstmt import BalanceSheets, IncomeStatements, FinancialStatements

bs = BalanceSheets.from_df(bs_df)
inc = IncomeStatements.from_df(inc_df)
stmts = FinancialStatements(inc, bs)
```

In 2.0 every statement is a `StatementSeries` built from a `StatementConfig`.
The default configs ship with finstmt:

```python
import pandas as pd

from finstmt import FinancialStatements, StatementSeries
from finstmt.config.statement import BALANCE_SHEET_CONFIG, INCOME_STATEMENT_CONFIG

inc_df = pd.read_csv("tests/sources/stockrow/CAT/annual_income.csv", index_col=0)
bs_df = pd.read_csv("tests/sources/stockrow/CAT/annual_bs.csv", index_col=0)

inc = StatementSeries.from_df(
    inc_df, INCOME_STATEMENT_CONFIG.display_name, INCOME_STATEMENT_CONFIG.items_config_list
)
bs = StatementSeries.from_df(
    bs_df, BALANCE_SHEET_CONFIG.display_name, BALANCE_SHEET_CONFIG.items_config_list
)
stmts = FinancialStatements([inc, bs])  # a list or dict instead of positional arguments
```

1.x calculated metrics such as free cash flow implicitly. In 2.0 they live in
a metrics statement. `FinancialStatements.from_df` builds every statement from
one DataFrame, and `STATEMENT_CONFIGS` includes the metrics:

```python
from finstmt.config.statement import STATEMENT_CONFIGS

stmts = FinancialStatements.from_df(pd.concat([inc_df, bs_df]), STATEMENT_CONFIGS)
stmts.fcf
```

You can also define your own statements with `ItemConfig` and
`StatementConfig` (see the README), or load them from YAML with
`finstmt.load_from_yaml(df, path)`. The bundled
`finstmt/config/statement_config.yaml` shows the format. Row labels are
standardized (lower-cased, punctuation removed) before they are matched, so
write `extract_names` in that form.

## Configuration

| 1.x | 2.0 |
|---|---|
| `from finstmt import CONFIG`: one global config | `stmts.config`: a `ConfigManager` for each `FinancialStatements` |
| `ItemConfig.forecast_config` | `ItemConfig.forecast` (a `ForecastItemConfig`) |
| `stmts.config.update(key, ["forecast_config", "method"], value)` | `stmts.config.update(key, ["forecast", "method"], value)` |
| `stmts.config.update_all(["forecast_config", "method"], value)` | `stmts.config.update_all(["forecast", "method"], value)` |
| `finstmt.bs.config.BALANCE_SHEET_INPUT_ITEMS` | `BALANCE_SHEET_CONFIG.items_config_list` (`finstmt.config.statement`) |
| `finstmt.inc.config.INCOME_STATEMENT_INPUT_ITEMS` | `INCOME_STATEMENT_CONFIG.items_config_list` |

## Forecasting

`stmts.forecast(...)` returns `ForecastedStatements`. In 1.x it returned
`ForecastedFinancialStatements`. `fcst.plot(subset=[...])` and
`fcst.forecasts[key].to_manual(...)` work as before.

```python
for key in ["cash_and_st_invest", "net_ppe", "op_exp"]:
    stmts.config.update(key, ["forecast", "make_forecast"], False)

stmts.config.update("revenue", ["forecast", "method"], "trend")
fcst = stmts.forecast(periods=3)
fcst.revenue
```

**Known issues in 2.0.0-alpha.1:**
- **A calculated item can be switched to forecasting.** finstmt does this when
  the inputs to the item's formula are missing from the data. In the CAT
  sample above, that cuts the link between the cash plug and total assets, and
  the forecast fails with `InvalidBalancePlugsException`. The loop above
  switches those items back to being calculated, and the exception's message
  names the items involved.
- **`to_manual` does not support items forecast as a percent of another item
  (`pct_of`).** Set the item's method to `"manual"` and its
  `manual_forecasts["levels"]` to the ratios instead.

## Module map

| 1.x | 2.0 |
|---|---|
| `finstmt.bs.main.BalanceSheets`, `finstmt.inc.main.IncomeStatements` | `finstmt.core.statement_series.StatementSeries` with `BALANCE_SHEET_CONFIG` / `INCOME_STATEMENT_CONFIG` |
| `finstmt.bs.config`, `finstmt.inc.config` | `finstmt.config.statement`, with items in `finstmt/config/statement_config.yaml` |
| `finstmt.combined.statements.FinancialStatements` | `finstmt.core.statements.FinancialStatements` (`from finstmt import FinancialStatements` still works) |
| `finstmt.combined.combinator` | Removed: statement math lives on `FinancialStatements` |
| `finstmt.config_manage` (`CONFIG` and the config managers) | `finstmt.config.manager.ConfigManager` |
| `finstmt.items.config.ItemConfig` | `finstmt.config.item.ItemConfig` |
| `finstmt.forecast.config.ForecastConfig` | `finstmt.config.forecast.ForecastConfig` |
| `finstmt.forecast.config.ForecastItemConfig` | `finstmt.config.item.ForecastItemConfig` |
| `finstmt.findata.statementsbase.FinStatementsBase` | `finstmt.core.statement_series.StatementSeries` |
| `finstmt.findata.period_data.PeriodFinancialData` | `finstmt.core.statement_period_data.StatementPeriodData` |
| `finstmt.findata.statement_item.StatementItem` | `finstmt.core.statement_item.StatementItem` |
| `finstmt.forecast.main.Forecast` | `finstmt.forecast.forecast_item_series.ForecastItemSeries` |
| `finstmt.forecast.statements.ForecastedFinancialStatements` | `finstmt.forecast.forecasted_statements.ForecastedStatements` |
| `finstmt.forecast.models.prophet.FBProphetModel` | `finstmt.forecast.models.prophet.ProphetModel` |
| `finstmt.resolver.base.ResolverBase` | `finstmt.solver.base.SolverBase` |
| `finstmt.resolver.history.StatementsResolver` | `finstmt.solver.historical.HistoricalSolver` |
| `finstmt.resolver.forecast.ForecastResolver` | `finstmt.solver.forecast.ForecastSolver` |
| `finstmt.resolver.solve` | `finstmt.solver.engine` |
| `finstmt.loaders.capiq.load_capiq_df` | `finstmt.io.capiq.load_capiq_df` |
| `finstmt.clean.name` | `finstmt.clean` |
| `finstmt.exc` | `finstmt.exceptions` (same exception classes) |
| `finstmt.logger` | `finstmt._logging` (private) |

**Unchanged paths:**
- `finstmt.check`;
- `finstmt.forecast.dataframe` and `finstmt.forecast.plot`;
- the other `finstmt.forecast.models` modules.

**New modules:**
- `finstmt.freq`;
- `finstmt.io.excel`, behind `FinancialStatements.to_excel`;
- `finstmt.solver.dependencies` and `finstmt.solver.periods`;
- `finstmt.deals`.

## Behavior changes that move numbers

- **CAGR** now uses the number of growth periods. For `[100, 110, 121]` that
  is 10% a year; 1.x divided by the number of observations and gave 6.56%.
  CAGR is the default method, so most forecasts change.
- **Balance sheet plugs** are chosen in a fixed, sorted order. 1.x used hash
  order, so balanced results could differ between runs.
- **References before the first period** are now NaN. 1.x silently treated a
  reference like `debt[t-1]` in the first historical period as zero, which
  fabricated values such as `interest = 0`.
- **Items with no data** are treated as empty, which turns forecasting off for
  them.
- **Mixed-frequency history** now raises `MixedFrequencyException`. 1.x
  silently treated the missing frequency as daily.
- **Frequencies** use pandas 2.2+ aliases. `forecast(freq="Y")` and
  `freq="Q"` still work and map to `"12ME"` and `"3ME"`. pandas 3 rejects the
  old `"M"` and `"A"` spellings, so pass `"ME"` or `"YE"` forms.

## New in 2.0

- **`recompute_calculated=True`** on `FinancialStatements.from_df`,
  `from_yaml_config` and the constructor. Values you provide always win, and
  every calculated item without a provided value is recomputed from its
  formula. Use it for models built from scratch; leave it off for reported
  filings.
- **`finstmt.deals`:**
  - `Transaction` and `Entry` for sources and uses;
  - `Waterfall` with `Pay`, `Sweep` and `Residual` steps;
  - `Deal` with `ExitTerms`;
  - the metrics `irr`, `moic`, `npv` and `compute_metrics`.
- **`ForecastItemConfig.use_average`:** forecast a `pct_of` item against the
  average of its base over two periods.
- **Item-level `prophet_kwargs`** override the forecast-wide ones.
- **`FinancialStatements.to_excel(path)`.**
