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

    Provides lookup and bulk updates for
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
