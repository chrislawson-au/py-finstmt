import dataclasses
import operator
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    TypeVar,
    Union,
    get_args,
)

import pandas as pd
from typing_extensions import Literal, Self

T = TypeVar("T")

ForecastMethod = Literal["auto", "cagr", "trend", "mean", "recent", "manual"]
VALID_FORECAST_METHODS = frozenset(get_args(ForecastMethod))


@dataclass
class ForecastItemConfig:
    """Forecast settings for a single financial statement line item.

    Controls how a line item is projected: which model to use, whether it is
    expressed as a percentage of another item, manual overrides, and balance-sheet
    plug/balancing behavior.

    :param method: Forecast model name (``"auto"`` for Prophet, ``"cagr"``,
        ``"trend"``, ``"mean"``, ``"recent"``, ``"manual"``).
    :param pct_of: Key of another item to forecast this as a percentage of
        (e.g. ``"revenue"``). ``None`` to forecast the raw value.
    :param make_forecast: Whether to include this item in the forecast.
    :param prophet_kwargs: Extra keyword arguments passed to the Prophet model.
    :param cap: Upper bound for the forecast trend line.
    :param floor: Lower bound for the forecast trend line.
    :param manual_forecasts: Dict with ``"levels"`` and ``"growth"`` lists for
        manual override values.
    :param plug: Whether this item can be adjusted to balance the balance sheet.
    :param balance_with: Key of item to balance against (e.g.
        ``"total_liab_and_equity"`` for total assets).
    :param use_average: Use average of the ``pct_of`` item across adjacent periods
        (e.g. ``(debt[t] + debt[t-1]) / 2``) instead of the current period value.

    Examples:
        >>> fc = ForecastItemConfig(method="cagr", pct_of="revenue")
        >>> fc.plug = True
        >>> fc.manual_forecasts = {"levels": [100, 110], "growth": []}
    """

    method: ForecastMethod = "cagr"
    pct_of: Optional[str] = None
    make_forecast: bool = True
    prophet_kwargs: dict = field(default_factory=lambda: {})
    cap: Optional[Union[float, pd.Series]] = None
    floor: Optional[Union[float, pd.Series]] = None
    manual_forecasts: Dict[str, List[float]] = field(
        default_factory=lambda: {"levels": [], "growth": []}
    )
    plug: bool = False
    balance_with: Optional[str] = None
    use_average: bool = False

    def __post_init__(self) -> None:
        if self.method not in VALID_FORECAST_METHODS:
            raise ValueError(
                f"invalid forecast method {self.method!r}; "
                f"must be one of {sorted(VALID_FORECAST_METHODS)}"
            )

    def to_series(self) -> pd.Series:
        out_dict = {
            "Method": self.method,
            "% of": self.pct_of,
            "Cap": self.cap,
            "Floor": self.floor,
            "Plug": self.plug,
            "Use Average": self.use_average,
        }
        out_dict.update(self.prophet_kwargs)

        if "levels" in self.manual_forecasts and self.manual_forecasts["levels"]:
            out_dict.update({"Manual Levels": self.manual_forecasts["levels"]})
        if "growth" in self.manual_forecasts and self.manual_forecasts["growth"]:
            growth_pcts = [
                f"{growth:.2%}" for growth in self.manual_forecasts["growth"]
            ]
            out_dict.update({"Manual Growth": growth_pcts})
        return pd.Series(out_dict)

    def copy(self, **updates) -> Self:
        return dataclasses.replace(self, **updates)

    def __round__(self, n: Optional[int] = None) -> "ForecastItemConfig":
        return _apply_operation_to_forecast_item_config(self, n, round)  # type: ignore[misc,arg-type]

    def __add__(self, other: T) -> "ForecastItemConfig":
        return _apply_operation_to_forecast_item_config(self, other, operator.add)

    def __sub__(self, other: T) -> "ForecastItemConfig":
        return _apply_operation_to_forecast_item_config(self, other, operator.sub)

    def __mul__(self, other: T) -> "ForecastItemConfig":
        return _apply_operation_to_forecast_item_config(self, other, operator.mul)

    def __truediv__(self, other: T) -> "ForecastItemConfig":
        return _apply_operation_to_forecast_item_config(self, other, operator.truediv)


def _apply_operation_to_forecast_item_config(
    item_config: ForecastItemConfig,
    other: T,
    func: Callable[[Any, T], Any],
) -> ForecastItemConfig:
    updates: Dict[str, Any] = {}
    if item_config.cap is not None:
        updates["cap"] = func(item_config.cap, _get_forecast_attr_if_needed(other, "cap"))
    if item_config.floor is not None:
        updates["floor"] = func(item_config.floor, _get_forecast_attr_if_needed(other, "floor"))
    manual_forecast_keys = ["levels", "growth"]
    updates["manual_forecasts"] = {}
    for key in manual_forecast_keys:
        if item_config.manual_forecasts[key]:
            updates["manual_forecasts"][key] = [
                func(val, _get_manual_forecast_key_if_needed(other, key, i))
                for i, val in enumerate(item_config.manual_forecasts[key])
            ]
        else:
            updates["manual_forecasts"][key] = []
    return item_config.copy(**updates)


def _get_forecast_attr_if_needed(other: Any, attr: str) -> Any:
    if isinstance(other, ForecastItemConfig):
        return getattr(other, attr)
    return other


def _get_manual_forecast_key_if_needed(other: Any, key: str, i: int) -> Any:
    if isinstance(other, ForecastItemConfig):
        return other.manual_forecasts[key][i]
    return other


@dataclass
class ItemConfig:
    """Configuration for a single financial statement line item.

    Defines how a line item is identified, displayed, and forecasted.
    Calculated items use ``expr_str`` to define their formula.

    :param key: Internal identifier (e.g. ``"revenue"``).
    :param display_name: Human-readable label (e.g. ``"Revenue"``).
    :param extract_names: Names to match when parsing input data, in priority order.
    :param force_positive: Whether to force the extracted value positive.
    :param forecast: Forecast settings for this item.
    :param expr_str: Expression string for calculated items
        (e.g. ``"current_assets[t] + non_current_assets[t]"``). ``None`` for raw items.
    :param display_verbosity: Minimum verbosity level to show this item (0 = always).

    Examples:
        >>> cfg = ItemConfig(key="revenue", display_name="Revenue",
        ...                  extract_names=["Revenue", "Total Revenue", "Net Revenue"])
        >>> cfg.forecast.method = "cagr"
        >>> cfg.primary_name  # "Revenue"
    """

    key: str
    display_name: str

    extract_names: Optional[Sequence[str]] = None
    force_positive: bool = True
    forecast: ForecastItemConfig = field(
        default_factory=lambda: ForecastItemConfig()
    )
    expr_str: Optional[str] = None

    display_verbosity: int = 1

    # TODO [#19]: add config and logic for whether to take highest priority or add all of matching names
    #
    # When extracting impairment, in Capital IQ data it has Impairment of Goodwill and Asset Writedown,
    # both of which should be included. This is in contrast to most others where only the highest priority
    # key should be selected

    @property
    def primary_name(self) -> str:
        if self.extract_names is None:
            return self.key

        return self.extract_names[0]

    def copy(self, **updates) -> Self:
        return dataclasses.replace(self, **updates)

    def __round__(self, n=None) -> "ItemConfig":
        return _apply_operation_to_item_config(self, n, round)

    def __add__(self, other: T) -> "ItemConfig":
        return _apply_operation_to_item_config(self, other, operator.add)

    def __sub__(self, other: T) -> "ItemConfig":
        return _apply_operation_to_item_config(self, other, operator.sub)

    def __mul__(self, other: T) -> "ItemConfig":
        return _apply_operation_to_item_config(self, other, operator.mul)

    def __truediv__(self, other: T) -> "ItemConfig":
        return _apply_operation_to_item_config(self, other, operator.truediv)


def _apply_operation_to_item_config(
    item_config: ItemConfig,
    other: T,
    func: Callable[[ForecastItemConfig, T], ForecastItemConfig],
) -> ItemConfig:
    updates: Dict[str, Any] = {}
    updates["forecast"] = func(
        item_config.forecast,
        _get_item_attr_if_needed(other, "forecast"),
    )
    return item_config.copy(**updates)


def _get_item_attr_if_needed(other: Any, attr: str) -> Any:
    if isinstance(other, ItemConfig):
        return getattr(other, attr)
    return other
