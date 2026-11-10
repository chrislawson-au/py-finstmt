import pytest

from finstmt import FinancialStatements
from finstmt.forecast.forecasted_statements import ForecastedStatements
from tests.fixtures.forecast.adjust_config import (
    FORECAST_ADJUSTS,
    adjust_forecast_methods,
)


@pytest.fixture(scope="session")
def ro_annual_capiq_fcst_stmts(
    ro_annual_capiq_stmts: FinancialStatements,
) -> ForecastedStatements:
    stmts = ro_annual_capiq_stmts

    to_fcst = stmts.copy()
    adjust_dict = FORECAST_ADJUSTS["capiq"]
    adjust_forecast_methods(to_fcst, adjust_dict)
    fcst = to_fcst.forecast()
    return fcst
