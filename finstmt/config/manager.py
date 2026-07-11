import re
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Set, Tuple, Union


from finstmt.exceptions import (
    InvalidBalanceConfigException,
    NoSuchItemException,
)
from finstmt.config.item import ItemConfig
from finstmt._logging import logger


@dataclass
class ConfigManager:
    """Holds all item configurations organized by statement type.

    Provides lookup, dependency analysis, and bulk updates for
    :class:`ItemConfig` objects. Access individual configs as attributes:
    ``config.revenue`` returns the ``ItemConfig`` for revenue.

    :param configs: Dict mapping statement names (e.g. ``"Income Statement"``)
        to lists of :class:`ItemConfig`.

    Examples:
        >>> config = ConfigManager(configs={"Income Statement": [revenue_cfg, cogs_cfg]})
        >>> config.revenue              # ItemConfig for revenue
        >>> config.get("revenue")       # same, explicit lookup
        >>> config.keys                 # all config keys
        >>> config.items                # all ItemConfig objects
    """

    configs: Dict[str, List[ItemConfig]]

    def get(self, item_key: str) -> ItemConfig:
        """Find config by key across all statement types."""
        for configs in self.configs.values():
            for config in configs:
                if config.key == item_key:
                    return config
        raise NoSuchItemException(item_key)

    def _get(self, item_key: str) -> Tuple[ItemConfig, str]:
        """Get the config as well as the key of the financial statement type it belongs to."""
        for stmt_name, configs in self.configs.items():
            for config in configs:
                if config.key == item_key:
                    return config, stmt_name
        raise NoSuchItemException(item_key)

    def set(self, item_key: str, config: ItemConfig) -> None:
        """Set entire configuration for item by key."""
        for stmt_name, configs in self.configs.items():
            for i, c in enumerate(configs):
                if c.key == item_key:
                    self.configs[stmt_name][i] = config
                    return
        raise NoSuchItemException(item_key)

    def __getattr__(self, item_key: str) -> ItemConfig:
        if item_key == "configs":
            return object.__getattribute__(self, item_key)
        try:
            return self.get(item_key)
        except NoSuchItemException:
            raise AttributeError(item_key)

    def __dir__(self) -> List[str]:
        return self.keys

    @property
    def items(self) -> List[ItemConfig]:
        """All configs across all statement types, maintaining order."""
        seen: Set[str] = set()
        all_items: List[ItemConfig] = []
        for configs in self.configs.values():
            for item in configs:
                if item.key not in seen:
                    seen.add(item.key)
                    all_items.append(item)
        return all_items

    @property
    def keys(self) -> List[str]:
        """All config keys across all statement types, maintaining order."""
        return [item.key for item in self.items]

    def update(self, item_key: str, config_keys: Union[str, Sequence[str]], value: Any):
        """Update configuration for item by item key and nested config keys."""
        if isinstance(config_keys, str):
            config_keys = [config_keys]

        orig_config, stmt_name = self._get(item_key)
        nested_config = orig_config
        for i, config_key in enumerate(config_keys):
            if i == len(config_keys) - 1:
                setattr(nested_config, config_key, value)
                logger.debug(
                    f"Set {config_key} for {item_key} on {type(nested_config)} to {value}"
                )
            else:
                nested_config = getattr(nested_config, config_key)
        self.set(item_key, orig_config)

    def update_all(self, config_keys: Union[str, Sequence[str]], value: Any):
        """Update configuration for all items by nested config keys."""
        for item_key in self.keys:
            self.update(item_key, config_keys, value)

    # --- String-based dependency analysis (no sympy) ---

    def _extract_keys_from_expr(self, expr_str: str) -> List[str]:
        """Extract item keys referenced in an expression string.

        Parses strings like 'current_assets[t] + non_current_assets[t]'
        and returns keys that match known config keys.
        """
        all_keys = set(self.keys)
        return [m for m in re.findall(r'(\w+)\[', expr_str) if m in all_keys]

    def keys_referenced_by(self, item_key: str) -> List[str]:
        """Get keys that appear in the expression for item_key."""
        config = self.get(item_key)
        if config.expr_str is None:
            return []
        return self._extract_keys_from_expr(config.expr_str)

    def keys_in_equations_involving(self, item_key: str) -> Set[str]:
        """Get all keys that appear in equations containing item_key.

        Includes both the LHS key and all RHS keys of any equation that
        references item_key. Also includes keys from item_key's own expression.
        """
        relevant_keys: Set[str] = set()
        for config in self.items:
            if config.expr_str is None:
                continue
            referenced = self._extract_keys_from_expr(config.expr_str)
            if item_key in referenced:
                relevant_keys.add(config.key)  # the LHS
                relevant_keys.update(referenced)  # all RHS keys
        # Also add keys from this item's own expression
        own_config = self.get(item_key)
        if own_config.expr_str is not None:
            relevant_keys.add(item_key)
            relevant_keys.update(self._extract_keys_from_expr(own_config.expr_str))
        return relevant_keys

    def _calculated_item_determinant_keys(
        self, item_key: str, for_forecast: bool = True
    ) -> List[str]:
        """Walk the dependency graph using string-based expression parsing."""
        determinant_keys: List[str] = []
        to_process_keys: List[str] = [item_key]
        is_root = True
        while to_process_keys:
            process_key = to_process_keys.pop()
            if not is_root:
                determinant_keys.append(process_key)
            is_root = False
            involved = self.keys_in_equations_involving(process_key)
            already_seen = set(to_process_keys + determinant_keys)
            new_keys = [
                key
                for key in involved
                if key != process_key and key not in already_seen
            ]
            if for_forecast:
                accepted_keys: List[str] = []
                for key in new_keys:
                    if self.get(key).forecast.make_forecast:
                        determinant_keys.append(key)
                        continue
                    accepted_keys.append(key)
                new_keys = accepted_keys
            to_process_keys.extend(new_keys)
        return determinant_keys

    def item_determinant_keys(
        self, item_key: str, include_pct_of: bool = True, for_forecast: bool = True
    ) -> List[str]:
        determinant_keys = self._calculated_item_determinant_keys(
            item_key, for_forecast=for_forecast
        )
        if include_pct_of:
            for item in self.items:
                # TODO [$5fed05c64df698000808428a]: multiple passes through determinants may be necessary for complicated pct_of structures
                if (
                    item.key in determinant_keys
                    and item.forecast.pct_of is not None
                ):
                    pct_conf = self.get(item.forecast.pct_of)
                    if pct_conf.expr_str is None:
                        determinant_keys.append(item.forecast.pct_of)
                    else:
                        determinant_keys.extend(
                            self._calculated_item_determinant_keys(pct_conf.key)
                        )
        # Order-preserving dedupe: set() iteration order is not deterministic
        # across processes
        return list(dict.fromkeys(determinant_keys))

    @property
    def balance_groups(self) -> List[List[str]]:
        """Groups of item keys that must balance against each other.

        Each group is sorted so ordering is deterministic across processes
        (set iteration order depends on PYTHONHASHSEED, and the plug solver's
        equation ordering must be stable for reproducible results).
        """
        balance_sets: List[Set[str]] = []
        for item in self.items:
            if item.forecast.balance_with is not None:
                item_tracked = False
                for bl in balance_sets:
                    if item.key in bl:
                        item_tracked = True
                        break
                if item_tracked:
                    continue

                balance_group: Set[str] = {item.key, item.forecast.balance_with}
                balance_with_conf = self.get(item.forecast.balance_with)
                if balance_with_conf.forecast.balance_with != item.key:
                    changed = True
                    while changed:
                        num_balanced = len(balance_group)
                        balance_with_key = (
                            balance_with_conf.forecast.balance_with
                        )
                        if balance_with_key is None:
                            raise InvalidBalanceConfigException(
                                f"{balance_with_conf.key} is part of balance group {balance_group} but in its "
                                f"forecast it has None for balance_with. Set balance_with for "
                                f"{balance_with_conf.key} to be another key in the balance group"
                            )
                        balance_group.add(balance_with_key)
                        new_num_balanced = len(balance_group)
                        changed = num_balanced != new_num_balanced
                        balance_with_conf = self.get(balance_with_key)

                balance_sets.append(balance_group)
        return [sorted(balance_set) for balance_set in balance_sets]
