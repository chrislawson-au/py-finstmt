from finstmt.config.item import ForecastItemConfig, ItemConfig
from finstmt.config.manager import ConfigManager


def _config() -> ConfigManager:
    items = [
        ItemConfig(
            key="total_assets",
            display_name="Total Assets",
            forecast=ForecastItemConfig(balance_with="total_liab_and_equity"),
        ),
        ItemConfig(
            key="total_liab_and_equity",
            display_name="Total Liabilities and Equity",
            forecast=ForecastItemConfig(balance_with="total_assets"),
        ),
    ]
    return ConfigManager(configs={"Balance Sheet": items})


def test_balance_groups_are_deterministically_ordered():
    # Sets iterate in hash order, which varies across processes
    # (PYTHONHASHSEED) and previously made the plug solver's equation
    # ordering - and thus snapshot results - nondeterministic.
    groups = _config().balance_groups

    assert groups == [["total_assets", "total_liab_and_equity"]]
    assert all(isinstance(group, list) for group in groups)
    assert all(group == sorted(group) for group in groups)
