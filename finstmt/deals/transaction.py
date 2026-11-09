"""Point-in-time transactions: journal entries against the statements.

A transaction is a set of adjustments applied at one date — an LBO's
sources & uses, an acquisition's opening entries, a refinancing. It is
applied by rebuilding the statements with the adjusted explicit values,
so the core solver's "explicitly-provided values win" rule handles the
accounting and every identity recomputes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Union

import pandas as pd

from finstmt.config.statement import StatementConfig
from finstmt.core.statements import FinancialStatements


@dataclass
class Entry:
    """One adjustment: add ``amount`` to item ``key`` at the transaction date
    (negative to reduce)."""

    key: str
    amount: float


@dataclass
class Transaction:
    """A named set of entries applied at a date.

    Entries adjust explicitly-provided (raw) item values; calculated items
    are recomputed from their expressions after the adjustment.
    """

    date: Union[str, pd.Timestamp]
    entries: List[Entry] = field(default_factory=list)
    name: str = "Transaction"

    @classmethod
    def sources_and_uses(
        cls,
        date: Union[str, pd.Timestamp],
        sources: Dict[str, float],
        uses: Dict[str, float],
        name: str = "Sources & Uses",
        tolerance: float = 1e-6,
    ) -> "Transaction":
        """Build a transaction from a sources & uses table, validating that
        they balance. Both sides are positive amounts; map each label to the
        item it increases (e.g. sources: new debt, sponsor equity; uses:
        purchase consideration, fees)."""
        total_sources = sum(sources.values())
        total_uses = sum(uses.values())
        if abs(total_sources - total_uses) > tolerance:
            raise ValueError(
                f"Sources ({total_sources}) and uses ({total_uses}) must balance"
            )
        entries = [Entry(key, amount) for key, amount in sources.items()]
        entries += [Entry(key, amount) for key, amount in uses.items()]
        return cls(date=date, entries=entries, name=name)

    def net(self) -> float:
        """Sum of all entry amounts (useful for balance assertions)."""
        return sum(e.amount for e in self.entries)

    def apply(self, stmts: FinancialStatements) -> FinancialStatements:
        """Return new statements with the entries applied at the date.

        Entries must target raw (non-calculated) items. The rebuilt input
        contains only raw item values, so every identity recomputes from the
        adjusted inputs — under ``recompute_calculated`` a stale calculated
        seed can never mask the transaction's effect.
        """
        date = pd.to_datetime(self.date)

        configs_by_stmt = stmts._effective_statement_configs()
        raw_keys = {
            c.key for cs in configs_by_stmt.values() for c in cs if c.expr_str is None
        }
        all_keys = {c.key for cs in configs_by_stmt.values() for c in cs}
        unknown = [e.key for e in self.entries if e.key not in all_keys]
        if unknown:
            raise KeyError(f"{self.name}: unknown item keys {unknown}")
        calculated = [e.key for e in self.entries if e.key not in raw_keys]
        if calculated:
            raise ValueError(
                f"{self.name}: entries must target raw items; {calculated} are "
                "calculated — adjust their inputs instead"
            )

        dates = stmts.dates
        if date not in dates:
            raise ValueError(
                f"{self.name}: date {date.date()} not in statement dates "
                f"{[d.date() for d in dates]}"
            )
        adjustments: Dict[str, float] = {}
        for entry in self.entries:
            adjustments[entry.key] = adjustments.get(entry.key, 0.0) + entry.amount

        # Raw items contribute their (adjusted) values; calculated items
        # contribute only their ORIGINAL explicit seeds — recurrence anchors
        # and reported actuals survive, while solved identity values are
        # dropped so they recompute from the adjusted inputs.
        seed_values = stmts.item_seed_values()
        rows: Dict[str, List[float]] = {}
        for configs in configs_by_stmt.values():
            for config in configs:
                source = (
                    getattr(stmts, config.key)
                    if config.expr_str is None
                    else seed_values.get(config.key)
                )
                if source is None:
                    continue
                values = []
                for d in dates:
                    raw_v = source.loc[d] if d in source.index else float("nan")
                    v = float(raw_v) if not pd.isna(raw_v) else float("nan")
                    if d == date and config.key in adjustments:
                        v = (0.0 if pd.isna(v) else v) + adjustments[config.key]
                        if v < 0 and config.force_positive:
                            raise ValueError(
                                f"{self.name}: adjustment takes {config.key} to {v}, "
                                f"but the item is force_positive and the rebuild "
                                f"would silently flip the sign. Set "
                                f"force_positive=False on the item or adjust inputs."
                            )
                    values.append(v)
                if all(pd.isna(v) for v in values):
                    continue
                # Key rows by primary_name (the first extract name): display
                # names are not always extractable, and the row must survive
                # the from_df round-trip. Matches the core rebuild convention.
                rows[config.primary_name] = values

        df = pd.DataFrame(rows, index=dates).T

        statement_configs = [
            StatementConfig(key=name, display_name=name, items_config_list=configs)
            for name, configs in configs_by_stmt.items()
        ]
        return FinancialStatements.from_df(
            df,
            statement_configs,
            disp_unextracted=False,
            recompute_calculated=stmts.recompute_calculated,
        )
