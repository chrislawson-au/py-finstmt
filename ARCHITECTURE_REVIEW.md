# Architecture Review — `fork-restructure` branch

*Reviewed 2026-07-10, against the `unify-config` branch. File/line references are as of commit `7e4e8a6`.*

This document records a full structural review of the package after the module-layout
restructure, for future reference. It covers what changed vs `unify-config`, three
likely bugs, the major structural findings, and a prioritized cleanup roadmap.
Items are checked off as they are addressed.

## 1. What changed vs `unify-config`

Four commits:

1. **`1fa292e` — module layout restructure** (95% of the diff). The flat/legacy layout
   became four intentional layers:
   - `config/` — absorbs the old `config_manage/` package (5 files → `manager.py`) plus
     `findata/item_config.py` + `item_forecast_config.py` (→ `item.py`),
     `forecast/config.py` (→ `forecast.py`), and the YAML loader.
   - `core/` — the old `findata/` statement model (`statements`, `statement_series`,
     `statement_period_data`, `statement_item`).
   - `solver/` — the old `resolver/` (`solve.py` → `engine.py`, `history.py` →
     `historical.py`), with `ForecastResolver` → `ForecastSolver`.
   - `io/` — the old `loaders/capiq.py` → `excel.py`.
   - Deleted `findata/combinator.py` (arithmetic folded into the classes). Renamed
     `exc.py` → `exceptions.py`, `logger.py` → `_logging.py`, `clean/name.py` → `clean.py`.
   - Net ~400 fewer lines in the package.
2. **`8dc4976` / `cd6b3c5` / `7e4e8a6`** — guards so a model with no plugs / no equations
   doesn't crash (`ForecastSolver.to_statements` gates on `plug_configs`; `numpy_solve`
   and `_x_arr_to_plug_solutions` return empty on empty input).

The −212k-line snapshot churn is test snapshots shrinking, not behavior.

**Verdict:** the four-package split is the right shape and the names are honest
(`solver/engine.py` beats `resolver/solve.py`). Nearly everything below is pre-existing
debt the restructure made visible, plus a few things the restructure started but didn't
finish.

## 2. Likely bugs

- [x] **`HistoricalSolver.to_statements` throws away its own solution**
  (`finstmt/solver/historical.py:28`). It computes `all_results` via `solve_equations`,
  then calls `stmt.from_df(...)` — a classmethod returning a *new* series — **discards
  the return value**, and stores the original unmodified `stmt`. Compare
  `ForecastSolver.to_statements` (`solver/forecast.py:109`) which correctly captures
  `StatementSeries.from_df(...)`. Tests likely pass only because
  `resolve_initial_expressions` already filled calculated values in `__post_init__` —
  so either this line is a bug, or the whole historical solve is redundant work. Either
  answer simplifies the code.

- [x] **Empty-system handling raises the wrong error** (`solver/engine.py:284`). The new
  guard makes `numpy_solve` return `{}` for an empty system, but `solve_equations` then
  hits `if not res_set: raise ValueError("could not solve equations")`. Callers gate on
  the *pre-substitution* `self.solve_eqs`, so a system fully resolved by substitution
  (residual collapses to empty) reaches this and raises a misleading error. Root issue:
  "nothing to solve" and "unsolvable" are conflated. Fix: treat an empty system as
  first-class success at the `solve_equations` boundary — then the deep guards in
  `numpy_solve` / `_x_arr_to_plug_solutions` can be deleted.

- [x] **Prophet kwargs merge order is backwards** (`forecast/models/prophet.py:26-27`).
  Item-level `prophet_kwargs` are applied first, then
  `all_kwargs.update(config.prophet_kwargs)` lets the *global* config clobber per-item
  settings. Per-item should win.

- [x] **`method` docs don't match the chooser** (`config/item.py:20` vs
  `models/chooser.py:19-32`). Docstring lists `"average"` / `"prophet"`; the chooser
  accepts `"mean"` / `"auto"` — the documented values raise `NotImplementedError`.
  Should be a `Literal`/`Enum` with validation.

## 3. Structural findings — the big five

1. - [x] **Layering is inverted: `core` secretly depends on `solver`.**
   *(Fixed: solvers now take plain data — `statement_configs` + `item_values` +
   `forecast_results` — and return plain per-item series from `solve()`. The solver
   package imports only `config`/`exceptions`/`_logging`. `FinancialStatements`
   orchestrates: builds solver inputs, rebuilds `StatementSeries` from results, does
   the plug write-back, and constructs `ForecastedStatements`. The solver no longer
   mutates the forecast items itself.)*

2. - [x] **Three parallel equation-building pipelines.**
   *(Fixed: `SolverBase` is a real ABC owning the template — config-list gathering,
   the `t_indexed_eqs` loop with a `_t_indexed_rhs` subclass hook for the
   pct-of/`use_average` branch, and the shared solve step. `resolve_initial_expressions`
   remains a separate seed-value pass by design.)*

3. - [x] **One period-index convention, written down once.**
   *(Fixed: `finstmt/solver/periods.py` defines `HISTORICAL_INDEXING` and
   `FORECAST_INDEXING` with `sympy_index`/`position` mappers; all `t_offset` params
   and `+1`/`-1` sprinkles route through them.)*

4. - [x] **Stop round-tripping sympy through strings.**
   *(Fixed: all `sympify(f"{key}[{t}]")` sites now use `sympy_namespace[key][t]`
   directly; only `expr_str` parsing still uses `sympify`, which is its job. The
   exception-message-sniffing in `ForecastSolver.sympy_subs_dict` was replaced with
   an explicit `is_pct_item` check.)*

5. - [x] **Two dependency engines for the same `expr_str`.**
   *(Fixed: `finstmt/solver/dependencies.py:ItemDependencies` parses each `expr_str`
   once with sympy and owns `referenced_by` / `in_equations_involving` /
   `item_determinant_keys` with deterministic traversal. The regex engine was deleted;
   `ConfigManager` is pure storage/lookup plus `balance_groups`.)*

## 4. Unfinished restructure business

- [x] `to_excel` (~80 lines of xlsxwriter) still lives in `core/statements.py:426` while
  `io/excel.py` exists as its natural home. *(Moved to `io/excel.py:statements_to_excel`;
  method is now a thin delegate.)*
- [x] `io/excel.py` actually contains a *CapIQ loader* (vendor-specific, `skiprows=14`)
  — should be `io/capiq.py`, freeing `io/excel.py` for the export. *(Renamed.)*
- [x] Grid-plot loop copy-pasted between `FinancialStatements.plot`
  (`statements.py:509-564`) and `ForecastedStatements.plot`
  (`forecasted_statements.py:52-106`), including the three layout constants.
  *(Unified as `_plot_helpers.plot_grid`.)*
- [x] `StatementItemSeries.plot` computes `y_lim` values it never uses — removed. The
  remaining overlap with `forecast/plot.py:plot_forecast` is minor (they genuinely
  differ: confidence band, combined min/max, ylim); left as is.
- [x] `config/__init__.py` and `io/__init__.py` are empty — added curated re-exports.
- [x] Rename residue: `ForecastResolver`/`resolver` docstrings, `-> "Forecast"`
  annotations, stale "Base class" docstring on `StatementPeriodData`, and the
  `cls.items_config_list` fallback (made `items_config_list` a required parameter).
  All fixed.

## 5. Model-level cleanups

- [x] **Dead scaffolding:** `prior_statement`, `eq_subs_dict`, `round_results`,
  `save_yaml_config`, `ConfigManager.get_value`/`set_value`/`dict`/`json`, unused
  `ForecastItemConfig` imports, `ItemConfigOperationData` alias, commented-out code in
  `forecast_item_series.py` — all deleted. Kept `update_all` (used in example
  notebooks and coherent with `update`). Kept the empty-input guards in
  `numpy_solve`/`_x_arr_to_plug_solutions`: `resolve_initial_expressions` can still
  legitimately pass an empty system, and the boundary fix in `solve_equations` now
  handles the semantic distinction.
- [ ] **Four hand-rolled `__getattr__` proxies** (`statements.py:222`,
  `statement_series.py:69`, `statement_period_data.py:180`, `manager.py:63`) implement
  "expose item keys as attributes" four different ways — one mixin/descriptor would
  unify them with consistent errors. The top-level one is O(n·dir) per attribute miss,
  and `FinancialStatements.__dir__` (`statements.py:255`) hardcodes a whitelist.
- [ ] **Three copies of the arithmetic-dunder machinery** (`_apply_operation_*` in
  `config/item.py` ×2 and `forecast_item_series.py`), each with its own
  `T = TypeVar("T")`; plus `StatementSeries`'s five near-identical dunder blocks
  (`statement_series.py:249-335`) — apply the `_apply_op` collapse everywhere.
- [ ] **Config lifecycle is heavy:** configs deep-copied three times on the way in
  (`statement_period_data.py:34`, `:43`, `statements.py:129`), then mutated in place at
  runtime (`_adjust_config_based_on_data`, `ConfigManager.update`). Long-term: frozen
  config (frozen dataclasses or pydantic, `method: Literal[...]`, referential checks on
  `pct_of`/`balance_with`) where adjustments produce new configs — makes the deep-copies
  unnecessary rather than load-bearing. `ConfigManager.set_value`/`update` mutate the
  retrieved object then call `self.set(...)`, which re-assigns the identical reference —
  dead weight.
- [ ] **Import-time file I/O**: `statement.py:64-69` loads YAML at import to build
  module-global singletons (`STATEMENT_CONFIGS`, `BALANCE_SHEET_CONFIG`, …) only test
  fixtures still use.
- [x] **Solver writes back into the model layer:** plug results injected via
  `forecast_dict[...].to_manual(...)`, mutating item configs/models as a side effect.
  *(Fixed as part of the layering inversion: the solver returns plain results and
  `FinancialStatements.forecast` does the write-back explicitly at the orchestration
  layer.)*
- [ ] **Model interface nits:** `ForecastModel.fit/predict` rely on subclasses
  remembering `super()` calls to set flags (template-method with abstract
  `_fit`/`_predict` is safer); base `predict` returns an empty Series instead of being
  abstract; `desired_freq_t_multiplier` only honored by `cagr`/`trend` — a
  quarterly→annual `mean`/`recent` forecast silently doesn't rescale;
  growth-compounding loop duplicated in `cagr.py:74-79` / `manual.py:54-58`;
  build-forecast-DataFrame boilerplate duplicated across 4+ model files.
- [ ] **God methods in `solver/forecast.py`:** `resolve_balance_sheet`
  (`:406-575`) mixes matrix assembly, x0 seeding, optimizer invocation, and paragraph-long
  error f-strings; `_adjust_x0_to_initial_balance_guess` (`:644-719`) similar. Split the
  "which plug affects this balance item" search and the user-guidance text into helpers.
- [ ] **Misc:** `load_yaml_config` return annotation wrong (fixed);
  `ItemConfig.__eq__`/`in` breaks when `cap`/`floor` hold a `pd.Series`
  (`core/statements.py:78`); `item_determinant_keys` returned `list(set(...))`
  discarding deterministic order (fixed — see determinism note below);
  `ForecastItemConfig.to_series` mixes presentation into config (`item.py:55-73`);
  naming overlap `_result`/`result`/`result_pct`/`result_df` on `ForecastItemSeries`
  vs model; `subs_dict`/`solutions_dict`/`all_hardcoded` near-synonyms.
- [x] **Nondeterministic solver results across processes (hash-order dependence).**
  `ConfigManager.balance_groups` returned `List[Set[str]]` and the solver iterated
  those sets (`itertools.combinations(balance_set, 2)` in `bs_balance_eqs`) —
  set iteration order depends on `PYTHONHASHSEED`, so the plug equation ordering,
  and therefore which of the many balanced plug solutions TNC converged to, varied
  per process. This made the capiq forecast snapshot tests flaky (their stored
  snapshots had even captured an *unbalanced* lucky run: `total_assets` 50 vs
  `total_liab_and_equity` 59). Fixed: `balance_groups` returns sorted lists,
  `item_determinant_keys` dedupes order-preservingly, snapshots regenerated and
  verified stable and balanced across processes.

## 6. Suggested order of attack

1. **The bugs** (§2) — small, high-value; the empty-system fix deletes two deep guards.
2. **Finish the restructure** (§4) — `to_excel` → `io/`, `io/capiq.py` rename, dedupe
   plotting into `_plot_helpers.py`, purge rename residue and dead code. Mechanical.
3. **Unify the solver** (§3.2–3.4) — shared equation-building template on an abstract
   `SolverBase`, one period-index convention, `ns[key][t]` instead of string sympify.
   Deepest quality win.
4. **Config hardening** (§5) — `method` as `Literal`/enum, delete dead `ConfigManager`
   API and the regex dependency engine, move toward frozen configs.
5. **The layering inversion** (§3.1) — solvers take data, not `FinancialStatements`.
   Biggest change; easiest after step 3.

## 7. Work log

**2026-07-11** — Completed §2 (all four bugs) and §4 (restructure finish), plus the
dead-code items in §5. Root cause found while fixing the first bug:
`get_solve_eqs_and_full_subs_dict` returned the *pre-iteration* equation list instead
of the empty residual when a system fully solved by substitution; `solve_equations`
then re-solved those stale equations and `numpy_solve` silently dropped terms for
unknown variables, overwriting correct values with garbage (e.g. `profit = 0`).
Fixed in `engine.py` with unit tests (`tests/unit/test_solver_engine.py`,
`tests/unit/test_historical_solver.py`, `tests/unit/test_item_config.py`,
`tests/unit/test_forecast_models.py`, `tests/unit/test_io.py`).
Also fixed the pre-existing failure `test_forecast_quarterly_stockrow_cat` (broken
since before `unify-config` — fixture crashed there): quarterly CAT data has no cash
values, so the plug must be `cash_and_st_invest` rather than `cash`; snapshot
regenerated and verified to balance. Also found and fixed the hash-order
nondeterminism in plug solving (§5) — the capiq forecast snapshots were flaky
across processes before this branch's changes.

**2026-07-11 (second pass)** — Completed all of §3, in order, each phase verified
against an unchanged snapshot suite:
1. Solver unification: abstract `SolverBase` template with `_t_indexed_rhs` hook
   (`solver/base.py`).
2. Period-index convention: `solver/periods.py` (`HISTORICAL_INDEXING` /
   `FORECAST_INDEXING`).
3. Sympy string round-trips removed; exception-sniffing branch in
   `sympy_subs_dict` made explicit.
4. Dependency analysis: `solver/dependencies.py:ItemDependencies` (single sympy
   parser, deterministic traversal); regex engine deleted from `ConfigManager`.
   Note: plug *selection* iterates determinant keys, so this order matters — it is
   now sorted-deterministic rather than hash-ordered.
5. Layering inversion: solvers take `statement_configs` + `item_values`
   (+ `forecast_results`, `balance_groups`) and return plain series from `solve()`;
   `FinancialStatements` owns statement rebuild, plug write-back, and
   `ForecastedStatements` construction. Solver package no longer imports core or
   forecast layers. One behavioral contract preserved explicitly: constructing
   `FinancialStatements` with mismatched dates still raises
   `MismatchingDatesException` (validation moved from the solver's implicit
   `stmts.dates` call to `resolve_statements`).

Remaining open items: the non-dead-code parts of §5 (frozen configs, `__getattr__`
mixin, model-interface template method, god-method split in `resolve_balance_sheet`,
`to_series` presentation split, `pd.Series` cap/floor equality hazard).
