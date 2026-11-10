"""
Work with financial statement data in Python. Can calculate free cash flows and help project
financial statements, automatically balancing the balance sheet.
"""

__version__ = "2.0.0-alpha.1"

from finstmt.config.forecast import ForecastConfig
from finstmt.config.item import ForecastItemConfig, ItemConfig
from finstmt.config.manager import ConfigManager
from finstmt.config.statement import StatementConfig
from finstmt.core.statement_series import StatementSeries
from finstmt.core.statements import FinancialStatements
from finstmt.forecast.forecasted_statements import ForecastedStatements


def load_from_yaml(df, config_path, disp_unextracted=True):
    """Convenience function to load financial statements from a YAML config file.

    :param df: DataFrame with financial data
    :param config_path: Path to YAML config file
    :param disp_unextracted: Whether to display unextracted items
    :return: FinancialStatements object
    """
    return FinancialStatements.from_yaml_config(df, config_path, disp_unextracted)
