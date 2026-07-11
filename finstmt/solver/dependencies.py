"""Dependency analysis over item expression strings.

Parses each ``ItemConfig.expr_str`` once with sympy and answers questions
about which items reference which. This is the single expression parser for
dependency questions — the config layer stores ``expr_str`` as opaque
strings and does no parsing of its own.

All traversal here is deterministic (sorted where a set boundary is
crossed): the plug solver selects plugs by iterating determinant keys, so
ordering must be stable across processes.
"""

from typing import Dict, List, Set

from sympy import Indexed, sympify

from finstmt.config.item import ItemConfig
from finstmt.exceptions import NoSuchItemException
from finstmt.solver.engine import build_sympy_namespace


class ItemDependencies:
    """Answers dependency questions about a set of item configs."""

    def __init__(self, item_configs: List[ItemConfig]):
        # Dedupe by key, order-preserving (mirrors ConfigManager.items)
        self._configs: Dict[str, ItemConfig] = {}
        for config in item_configs:
            self._configs.setdefault(config.key, config)

        namespace = build_sympy_namespace(list(self._configs.values()))
        known_keys = set(self._configs)
        self._referenced: Dict[str, List[str]] = {}
        for key, config in self._configs.items():
            if config.expr_str is None:
                self._referenced[key] = []
                continue
            expr = sympify(config.expr_str, locals=namespace)
            bases = {str(sym.base) for sym in expr.atoms(Indexed)}
            self._referenced[key] = sorted(bases & known_keys)

    def _get(self, item_key: str) -> ItemConfig:
        try:
            return self._configs[item_key]
        except KeyError:
            raise NoSuchItemException(item_key)

    def referenced_by(self, item_key: str) -> List[str]:
        """Keys that appear in the expression for item_key."""
        self._get(item_key)
        return list(self._referenced[item_key])

    def in_equations_involving(self, item_key: str) -> Set[str]:
        """All keys that appear in equations containing item_key.

        Includes both the LHS key and all RHS keys of any equation that
        references item_key. Also includes keys from item_key's own expression.
        """
        relevant_keys: Set[str] = set()
        for key, referenced in self._referenced.items():
            if item_key in referenced:
                relevant_keys.add(key)  # the LHS
                relevant_keys.update(referenced)  # all RHS keys
        # Also add keys from this item's own expression
        own_config = self._get(item_key)
        if own_config.expr_str is not None:
            relevant_keys.add(item_key)
            relevant_keys.update(self._referenced[item_key])
        return relevant_keys

    def _calculated_item_determinant_keys(
        self, item_key: str, for_forecast: bool = True
    ) -> List[str]:
        """Walk the dependency graph collecting keys that determine item_key.

        With ``for_forecast=True``, items that are directly forecasted
        (``make_forecast``) are recorded but not expanded — their inputs
        cannot flow through to item_key.
        """
        determinant_keys: List[str] = []
        to_process_keys: List[str] = [item_key]
        is_root = True
        while to_process_keys:
            process_key = to_process_keys.pop()
            if not is_root:
                determinant_keys.append(process_key)
            is_root = False
            involved = self.in_equations_involving(process_key)
            already_seen = set(to_process_keys + determinant_keys)
            new_keys = [
                key
                for key in sorted(involved)
                if key != process_key and key not in already_seen
            ]
            if for_forecast:
                accepted_keys: List[str] = []
                for key in new_keys:
                    if self._get(key).forecast.make_forecast:
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
            for item in self._configs.values():
                # TODO [$5fed05c64df698000808428a]: multiple passes through determinants may be necessary for complicated pct_of structures
                if (
                    item.key in determinant_keys
                    and item.forecast.pct_of is not None
                ):
                    pct_conf = self._get(item.forecast.pct_of)
                    if pct_conf.expr_str is None:
                        determinant_keys.append(item.forecast.pct_of)
                    else:
                        determinant_keys.extend(
                            self._calculated_item_determinant_keys(pct_conf.key)
                        )
        return list(dict.fromkeys(determinant_keys))
