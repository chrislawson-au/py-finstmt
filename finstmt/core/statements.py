import dataclasses
import operator
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import pandas as pd
from typing_extensions import Self

from finstmt._logging import logger
from finstmt._plot_helpers import (
    DEFAULT_HEIGHT_PER_ROW,
    DEFAULT_WIDTH,
    NUM_PLOT_COLUMNS,
    plot_grid,
)
from finstmt.check import item_series_is_empty
from finstmt.config.forecast import ForecastConfig
from finstmt.config.item import ItemConfig
from finstmt.config.manager import ConfigManager
from finstmt.config.statement import StatementConfig, load_statement_configs
from finstmt.core.statement_item_series import StatementItemSeries
from finstmt.core.statement_series import StatementSeries
from finstmt.exceptions import MismatchingDatesException

if TYPE_CHECKING:
    from finstmt.forecast.forecasted_statements import ForecastedStatements


@dataclass
class FinancialStatements:
    """Main class that holds a group of financial statements.

    Each statement type (e.g. Income Statement, Balance Sheet) is stored as a
    :class:`StatementSeries` keyed by its display name. Item values are accessible
    as attributes: ``stmts.revenue`` returns a ``pd.Series`` indexed by date.

    :param statements: Dict mapping statement names to StatementSeries objects,
        or a list of StatementSeries (auto-converted to dict).
    :param calculate: Whether to resolve calculated items via the solver.
    :param auto_adjust_config: Whether to automatically adjust the configuration
        based on the loaded data. Turns forecasting off for empty items and on
        for calculated items whose components are all missing.

    Examples:
        >>> from finstmt import FinancialStatements
        >>> stmts = FinancialStatements.from_df(df, statement_config_list)
        >>> stmts.revenue          # pd.Series of revenue by date
        >>> stmts.forecast(periods=5)  # returns ForecastedStatements
    """

    statements: Dict[str, StatementSeries]  # Changed from List to Dict
    calculate: bool = True
    auto_adjust_config: bool = True
    #: When True, calculated items are always recomputed from their equations
    #: across the historical periods (extracted values only seed equations that
    #: reach outside the historical window, e.g. ``revenue[t-1]`` at t=0).
    #: The default (False) preserves the data-priority contract: extracted
    #: values win and equations only fill gaps. Enable for models built from
    #: scratch where accounting identities must hold exactly; leave off for
    #: real reported filings, whose aggregates legitimately differ from the
    #: config's simplified identities.
    recompute_calculated: bool = False

    def __post_init__(self):
        # Convert list to dict if needed for backwards compatibility
        if isinstance(self.statements, list):
            self.statements = {stmt.statement_name: stmt for stmt in self.statements}
        self._resolve_initial_expressions()
        self.update_statements()
        self.resolve_statements()

    def _resolve_initial_expressions(self):
        """Resolve calculated items from expression strings using numpy linear algebra.

        Collects expression strings from each StatementPeriodData, delegates to
        solver/engine.py for the actual sympy-based solving, then writes results back.
        """
        from finstmt.solver.engine import resolve_initial_expressions

        # Collect all unique configs
        all_configs: List[ItemConfig] = []
        for statement_series in self.statements.values():
            for config in statement_series.items_config_list:
                if config not in all_configs:
                    all_configs.append(config)

        # Collect expression strings per period across all statements
        period_expression_strings = []
        for statement_series in self.statements.values():
            for idx, period in enumerate(statement_series.statements):
                # Extend the list to have enough slots
                while len(period_expression_strings) <= idx:
                    period_expression_strings.append([])
                period_expressions = statement_series.statements[
                    period
                ].get_t_indexed_expression_strings()
                period_expression_strings[idx].extend(period_expressions)

        res = resolve_initial_expressions(all_configs, period_expression_strings)

        for k, v in res.items():
            statement_item_key = k.base
            period_index = k.indices[0]
            statement_item_value = v
            for statement_series in self.statements.values():
                statement_series.update_statement_item_calculated_value(
                    statement_item_key, period_index, statement_item_value
                )

    def update_statements(self):
        for statement_series in self.statements.values():
            statement_series.df = statement_series.to_df()

    def resolve_statements(self):
        from finstmt.solver.historical import HistoricalSolver

        self._create_config_from_statements()

        if self.calculate:
            self._validate_dates()
            solver = HistoricalSolver(
                self._effective_statement_configs(),
                self._item_values(),
                recompute_calculated=self.recompute_calculated,
            )
            stmts = self._statement_series_from_results(solver.solve())
            new_stmts = FinancialStatements(
                stmts,
                calculate=False,
                auto_adjust_config=self.auto_adjust_config,
                recompute_calculated=self.recompute_calculated,
            )
            self.statements = dict(new_stmts.statements)
            self._create_config_from_statements()

    def _effective_statement_configs(self) -> Dict[str, List[ItemConfig]]:
        """Item configs per statement, preferring the (possibly adjusted)
        configs on this object's ConfigManager."""
        return {
            stmt_name: self.config.configs.get(stmt_name, stmt.items_config_list)
            for stmt_name, stmt in self.statements.items()
        }

    def _item_values(self) -> Dict[str, pd.Series]:
        """One series of values by date per item key, as solver input."""
        return {config.key: getattr(self, config.key) for config in self.all_config_items}

    def _statement_series_from_results(
        self, results: Dict[str, pd.Series]
    ) -> Dict[str, StatementSeries]:
        """Rebuild one StatementSeries per statement from solver results."""
        all_results = pd.concat(list(results.values()), axis=1).T
        stmts = {}
        for stmt_name, configs in self._effective_statement_configs().items():
            stmts[stmt_name] = StatementSeries.from_df(
                all_results,
                stmt_name,
                configs,
                disp_unextracted=False,
            )
        return stmts

    def _create_config_from_statements(self):
        config_dict = {}
        for statement_name, statement_series in self.statements.items():
            # Use deepcopied configs from first period's StatementPeriodData.
            # This prevents mutations (from _adjust_config_based_on_data) from
            # leaking back into the original items_config_list on the StatementSeries,
            # which is important when StatementSeries objects are reused (e.g. in
            # session-scoped test fixtures).
            first_period = next(iter(statement_series.statements.values()))
            config_dict[statement_name] = deepcopy(first_period.configs)
        self.config = ConfigManager(configs=config_dict)
        if self.auto_adjust_config:
            self._adjust_config_based_on_data()

    def _adjust_config_based_on_data(self):
        from finstmt.solver.dependencies import ItemDependencies

        dependencies = ItemDependencies(self.config.items)
        for item in self.config.items:
            if self.item_is_empty(item.key):
                if self.config.get(item.key).forecast.plug:
                    # It is OK for plug items to be empty, won't affect the forecast
                    continue

                # Useless to make forecasts on empty items
                logger.debug(f"Setting {item.key} to not forecast as it is empty")
                item.forecast.make_forecast = False
                # But this may mean another item should be forecasted instead.
                # E.g. normally net_ppe is calculated from gross_ppe and dep,
                # so it is not forecasted. But if gross_ppe is missing from
                # the data, then net_ppe should be forecasted directly.

                # So first, get the keys involved in equations containing this item
                relevant_keys = dependencies.in_equations_involving(item.key)
                relevant_keys.discard(item.key)
                for key in relevant_keys:
                    if self.item_is_empty(key):
                        continue
                    conf = self.config.get(key)
                    if conf.expr_str is None:
                        # Not a calculated item, so it doesn't make sense to turn forecasting on
                        continue

                    # Check to make sure that all components of the calculated item are also empty
                    component_keys = dependencies.referenced_by(key)
                    if not all(self.item_is_empty(c_key) for c_key in component_keys):
                        continue
                    # Now this is a calculated item which is non-empty, and all the components of the
                    # calculated are empty, so we need to forecast this item instead
                    logger.debug(
                        f"Setting {conf.key} to forecast as it is a calculated item which is not empty "
                        f"and yet none of the components have data"
                    )
                    conf.forecast.make_forecast = True

    def change(self, data_key: str) -> pd.Series:
        """
        Get the change between this period and last for a data series

        :param data_key: key of variable, how it would be accessed with FinancialStatements.data_key
        """
        series = getattr(self, data_key)
        return series - self.lag(data_key, 1)

    def lag(self, data_key: str, num_lags: int) -> pd.Series:
        """
        Get a data series lagged for a number of periods

        :param data_key: key of variable, how it would be accessed with FinancialStatements.data_key
        :param num_lags: Number of lags
        """
        series = getattr(self, data_key)
        return series.shift(num_lags)

    def average(self, data_key: str, num_periods: int = 2) -> pd.Series:
        """
        Get the average of a data series over a number of periods

        :param data_key: key of variable, how it would be accessed with FinancialStatements.data_key
        :param num_periods: Number of periods to average over (default is 2)
        """
        series = getattr(self, data_key)
        return series.rolling(num_periods).mean()

    def item_is_empty(self, data_key: str) -> bool:
        """
        Whether the passed item has no data

        :param data_key: key of variable, how it would be accessed with FinancialStatements.data_key
        :return:
        """
        series = getattr(self, data_key)
        return item_series_is_empty(series)

    def _repr_html_(self):
        result = ""
        for statement_series in self.statements.values():
            result += f"""
            <h2>{statement_series.statement_name}</h2>
            {statement_series._repr_html_()}
            """
        return result

    # TODO: consider implementing a breaking change to return a StatementItemSeries
    # and have a similar approach on the forecasted statements
    def __getattr__(self, item):
        for statement_series in self.statements.values():
            if item in dir(statement_series):
                return getattr(statement_series, item)

        raise AttributeError(item)

    def get_statement_item_series(self, item: str) -> StatementItemSeries:
        for statement_series in self.statements.values():
            if item in dir(statement_series):
                return statement_series.get_statement_item_series(item)

        raise AttributeError(item)


    def __getitem__(self, item):
        stmts_hetrogeneous = []
        if not isinstance(item, (list, tuple)):
            date_item = pd.to_datetime(item)
            for statement_series in self.statements.values():
                stmts_hetrogeneous.append(
                    StatementSeries(
                        {date_item: statement_series[item]},
                        statement_series.items_config_list,
                        statement_series.statement_name,
                    )
                )
        else:
            for statement_series in self.statements.values():
                stmts_hetrogeneous.append(statement_series[item])

        return FinancialStatements(stmts_hetrogeneous)

    def __dir__(self):
        normal_attrs = [
            "forecast",
            "forecasts",
            "forecast_assumptions",
            "dates",
            "copy",
        ]
        item_attrs = [config_item.key for config_item in self.all_config_items]
        return normal_attrs + item_attrs

    def forecast(self, **kwargs) -> "ForecastedStatements":
        """
        Run a forecast, returning forecasted financial statements

        :param kwargs: Attributes of :class:`finstmt.config.forecast.ForecastConfig`

        :Examples:

            >>> stmts.forecast(periods=2)

        """
        from finstmt.forecast.forecasted_statements import ForecastedStatements
        from finstmt.solver.forecast import ForecastSolver

        bs_diff_max = kwargs.get("bs_diff_max", ForecastConfig.bs_diff_max)
        balance = kwargs.get("balance", ForecastConfig.balance)
        timeout = kwargs.get("timeout", ForecastConfig.timeout)

        self._validate_dates()

        all_forecast_dict = {}
        for statement_series in self.statements.values():
            statement_forecast_dict = statement_series._forecast(self, **kwargs)
            all_forecast_dict.update(statement_forecast_dict)

        # Solvers take plain data: the percentage series for pct-of items,
        # the value series otherwise
        forecast_results = {
            key: (
                item_series.result_pct
                if item_series.item_config.forecast.pct_of is not None
                else item_series.result
            )
            for key, item_series in all_forecast_dict.items()
        }

        solver = ForecastSolver(
            self._effective_statement_configs(),
            self._item_values(),
            forecast_results,
            self.config.balance_groups,
            bs_diff_max,
            timeout,
            balance=balance,
        )
        results = solver.solve()

        if balance:
            # Write solved plug values back into the forecasts so plots and
            # further adjustments reflect the balanced values
            for config in solver.plug_configs:
                all_forecast_dict[config.key].to_manual(
                    use_levels=True, replacements=results[config.key].values
                )

        stmt_dfs = self._statement_series_from_results(results)
        # the forecasts passed are just used for plotting
        return ForecastedStatements(
            stmt_dfs,
            forecasts=all_forecast_dict,
            calculate=False,
            recompute_calculated=self.recompute_calculated,
        )

    @property
    def forecast_assumptions(self) -> pd.DataFrame:
        all_series = []
        for config in self.all_config_items:
            if not config.forecast.make_forecast:
                continue
            config_series = config.forecast.to_series()
            config_series.name = config.display_name
            all_series.append(config_series)
        return pd.concat(all_series, axis=1).T

    @property
    def all_config_items(self) -> List[ItemConfig]:
        return self.config.items

    @property
    def dates(self) -> List[pd.Timestamp]:
        self._validate_dates()
        return list(self.balance_sheets.statements.keys())

    def _validate_dates(self):
        stmt_list = list(self.statements.values())
        for i in range(len(stmt_list)):
            for j in range(i + 1, len(stmt_list)):
                stmts1_dates = set(stmt_list[i].statements.keys())
                stmts2_dates = set(stmt_list[j].statements.keys())
                if stmts1_dates != stmts2_dates:
                    stmts1_unique = stmts1_dates.difference(stmts2_dates)
                    stmts2_unique = stmts2_dates.difference(stmts1_dates)
                    message = "Got mismatching dates between historical statements. "
                    if stmts1_unique:
                        message += f"{stmt_list[i].statement_name} has {stmts1_unique} dates not in {stmt_list[j].statement_name}. "
                    if stmts2_unique:
                        message += f"{stmt_list[j].statement_name} has {stmts2_unique} dates not in {stmt_list[i].statement_name}. "
                    raise MismatchingDatesException(message)

    def copy(self, **updates) -> Self:
        return dataclasses.replace(self, **updates)

    def _apply_op(self, other: Any, op: Callable) -> Self:
        """Apply arithmetic operation to all child statement series."""
        if isinstance(other, (float, int)):
            new_stmts = {}
            for statement in self.statements.values():
                new_stmt = op(statement, other)
                new_stmts[new_stmt.statement_name] = new_stmt
        elif isinstance(other, FinancialStatements):
            new_stmts = {}
            for left, right in zip(self.statements.values(), other.statements.values()):
                new_stmt = op(left, right)
                new_stmts[new_stmt.statement_name] = new_stmt
        else:
            raise NotImplementedError(
                f"cannot {op.__name__} type {type(self)} with type {type(other)}"
            )
        return self.copy(statements=new_stmts)

    def __add__(self, other) -> Self:
        return self._apply_op(other, operator.add)

    def __radd__(self, other) -> Self:
        return self.__add__(other)

    def __sub__(self, other) -> Self:
        return self._apply_op(other, operator.sub)

    def __rsub__(self, other) -> Self:
        return (-1 * self) + other

    def __mul__(self, other) -> Self:
        return self._apply_op(other, operator.mul)

    def __rmul__(self, other) -> Self:
        return self.__mul__(other)

    def __truediv__(self, other) -> Self:
        return self._apply_op(other, operator.truediv)

    def __rtruediv__(self, other):
        # TODO [#41]: implement right division for statements
        raise NotImplementedError(
            f"cannot divide type {type(other)} by type {type(self)}"
        )

    def __round__(self, n: Optional[int] = None) -> Self:
        new_stmts = {}
        for statement in self.statements.values():
            rounded = round(statement, n)  # type: ignore
            new_stmts[rounded.statement_name] = rounded
        return self.copy(statements=new_stmts)

    @classmethod
    def from_df(
        cls,
        df: pd.DataFrame,
        statement_config_list: List[StatementConfig],
        disp_unextracted: bool = True,
        recompute_calculated: bool = False,
    ):
        """
        DataFrame must have columns as dates and index as names of financial statement items

        :param recompute_calculated: Always recompute calculated items from
            their equations across historical periods instead of preferring
            extracted values. Use for models built from scratch where
            accounting identities must hold; leave off for real reported data.
        """
        dates = list(df.columns)
        dates.sort(key=lambda t: pd.to_datetime(t))

        stmts = {}
        for statment_config in statement_config_list:
            stmt = StatementSeries.from_df(
                df,
                statment_config.display_name,
                statment_config.items_config_list,
                disp_unextracted=disp_unextracted,
            )
            stmts[statment_config.display_name] = stmt

        return cls(stmts, recompute_calculated=recompute_calculated)

    @classmethod
    def from_yaml_config(
        cls,
        df: pd.DataFrame,
        config_path: str,
        disp_unextracted: bool = True,
        recompute_calculated: bool = False,
    ):
        """
        Create FinancialStatements from DataFrame using YAML config file

        :param df: DataFrame with financial data
        :param config_path: Path to YAML config file
        :param disp_unextracted: Whether to display unextracted items
        :param recompute_calculated: Always recompute calculated items from
            their equations across historical periods instead of preferring
            extracted values. Use for models built from scratch where
            accounting identities must hold; leave off for real reported data.
        :return: FinancialStatements object
        """
        statement_configs = load_statement_configs(config_path)
        return cls.from_df(
            df,
            statement_configs,
            disp_unextracted,
            recompute_calculated=recompute_calculated,
        )

    def to_excel(self, filepath: str, separate_sheets: bool = True) -> None:
        """
        Save the financial statements to an Excel file with statement headers.

        :param filepath: Path where the Excel file should be saved
        :param separate_sheets: If True, creates separate sheet for each statement.
                              If False, combines all statements into one sheet
        """
        from finstmt.io.excel import statements_to_excel

        statements_to_excel(self.statements, filepath, separate_sheets)

    def plot(
        self,
        subset: Optional[Sequence[str]] = None,
        figsize: Optional[Tuple[float, float]] = None,
        num_cols: int = NUM_PLOT_COLUMNS,
        height_per_row: float = DEFAULT_HEIGHT_PER_ROW,
        plot_width: float = DEFAULT_WIDTH,
    ) -> plt.Figure:
        if subset is not None:
            plot_items = {k: self.get_statement_item_series(k) for k in subset}
        else:
            plot_items = {item.key: self.get_statement_item_series(item.key) for item in self.all_config_items}

        return plot_grid(
            plot_items,
            figsize=figsize,
            num_cols=num_cols,
            height_per_row=height_per_row,
            plot_width=plot_width,
        )
