% pypi-sphinx-quickstart documentation master file, created by
% pypi-sphinx-quickstart.
% You can adapt this file completely to your liking, but it should at least
% contain the root `toctree` directive.

# Welcome to finstmt documentation!

```{include} ../../README.md

```

For more information on getting started, take a look at the tutorial and examples.

```{toctree}
:caption: Tutorial

tutorial
auto_examples/index
```

## An overview

### Quick Links

Find the source code [on Github](https://github.com/chrislawson-au/py-finstmt).

```{eval-rst}
.. autosummarynameonly::

      finstmt.core.statements.FinancialStatements
      finstmt.core.statement_series.StatementSeries
      finstmt.config.statement.StatementConfig
      finstmt.config.item.ItemConfig
      finstmt.config.item.ForecastItemConfig
      finstmt.forecast.forecasted_statements.ForecastedStatements
      finstmt.deals.deal.Deal

```

## API Documentation

```{eval-rst}
.. toctree:: api/modules
   :maxdepth: 3
```

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
