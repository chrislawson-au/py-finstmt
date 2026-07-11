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
    ItemConfig(
        key="profit",
        display_name="Profit",
        extract_names=["profit"],
        expr_str="revenue[t] - cost[t]",
    ),
]


def test_zero_valued_calculated_item_is_recalculated_from_expression():
    # The historical solver treats a 0 value on a calculated item as missing
    # data and solves it from its expression. The solved value must end up in
    # the resulting statements.
    data = {
        "12/31/2022": {"revenue": 1000, "cost": 600, "profit": 0},
        "12/31/2023": {"revenue": 2000, "cost": 1100, "profit": 0},
    }
    stmt = StatementSeries.from_dict(data, "Income Statement", CONFIG)

    stmts = FinancialStatements([stmt])

    assert stmts.profit.iloc[0] == 400
    assert stmts.profit.iloc[1] == 900
