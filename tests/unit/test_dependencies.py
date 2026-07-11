from finstmt.config.item import ForecastItemConfig, ItemConfig
from finstmt.solver.dependencies import ItemDependencies

CONFIGS = [
    ItemConfig(key="revenue", display_name="Revenue", extract_names=["revenue"]),
    ItemConfig(key="cogs", display_name="COGS", extract_names=["cogs"]),
    ItemConfig(
        key="gross_profit",
        display_name="Gross Profit",
        expr_str="revenue[t] - cogs[t]",
    ),
    ItemConfig(key="opex", display_name="OpEx", extract_names=["opex"]),
    ItemConfig(
        key="net_income",
        display_name="Net Income",
        expr_str="gross_profit[t] - opex[t]",
    ),
]


def _deps() -> ItemDependencies:
    return ItemDependencies(CONFIGS)


def test_referenced_by_returns_expression_components():
    deps = _deps()
    assert deps.referenced_by("gross_profit") == ["cogs", "revenue"]
    assert deps.referenced_by("net_income") == ["gross_profit", "opex"]
    assert deps.referenced_by("revenue") == []


def test_in_equations_involving_includes_lhs_and_rhs_keys():
    deps = _deps()
    # revenue appears in gross_profit's equation
    assert deps.in_equations_involving("revenue") == {"gross_profit", "revenue", "cogs"}
    # gross_profit has its own equation and appears in net_income's
    assert deps.in_equations_involving("gross_profit") == {
        "gross_profit",
        "revenue",
        "cogs",
        "net_income",
        "opex",
    }


def test_determinant_keys_walk_dependency_chain():
    deps = _deps()
    determinants = deps.item_determinant_keys("net_income", for_forecast=False)
    # Everything net_income transitively depends on or co-occurs with
    assert set(determinants) >= {"gross_profit", "opex", "revenue", "cogs"}


def test_determinant_keys_include_but_do_not_expand_forecasted_items():
    # gross_profit is calculated, but if the user forces make_forecast on it,
    # the walk records it without traversing through it
    configs = [c.copy() for c in CONFIGS]
    for config in configs:
        if config.key == "gross_profit":
            config.forecast.make_forecast = True
        else:
            config.forecast.make_forecast = False

    deps = ItemDependencies(configs)
    determinants = deps.item_determinant_keys("net_income", for_forecast=True)

    assert "gross_profit" in determinants
    # revenue/cogs are only reachable through gross_profit, which is not expanded
    assert "revenue" not in determinants
    assert "cogs" not in determinants


def test_pct_of_targets_of_determinants_are_included():
    configs = [
        ItemConfig(key="revenue", display_name="Revenue", extract_names=["revenue"]),
        ItemConfig(
            key="receivables",
            display_name="Receivables",
            extract_names=["receivables"],
            forecast=ForecastItemConfig(pct_of="revenue"),
        ),
        ItemConfig(
            key="working_capital",
            display_name="Working Capital",
            expr_str="receivables[t]",
        ),
    ]
    deps = ItemDependencies(configs)

    determinants = deps.item_determinant_keys("working_capital", for_forecast=False)

    assert "receivables" in determinants
    # receivables is a determinant and is forecasted as % of revenue, so
    # revenue drives working_capital too
    assert "revenue" in determinants


def test_walk_is_deterministic():
    runs = {tuple(ItemDependencies(CONFIGS).item_determinant_keys("net_income")) for _ in range(5)}
    assert len(runs) == 1
