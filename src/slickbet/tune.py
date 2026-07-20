"""
Hyperparameter tuning for the betting model.

Uses cached API data to run backtests across different weight configurations
and find the best parameters. No API calls during tuning.

Examples
--------
>>> # 1. Populate cache:
>>> #    slickbet backtest-all --weeks 12 --cache-dir data/12_weeks_cache
>>> # 2. Run tuning:
>>> #    slickbet tune --cache-dir data/12_weeks_cache --trials 20
>>> from slickbet.tune import tune
>>> best = tune(cache_dir="data/12_weeks_cache", weeks=12, trials=20)
"""

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from slickbet.api import LivescoreClient
from slickbet.backtest import Backtester, BacktestResults
from slickbet.model import BettingModel

# Same league sets as backtest-all with --include-asia --include-americas
MAJOR_LEAGUES = [
    ("1", "Bundesliga", "Germany"),
    ("2", "Premier League", "England"),
    ("3", "La Liga", "Spain"),
    ("4", "Serie A", "Italy"),
    ("5", "Ligue 1", "France"),
]
MINOR_LEAGUES = [
    ("68", "Belgian Pro League", "Belgium"),
    ("8", "Primeira Liga", "Portugal"),
    ("6", "Super Lig", "Turkey"),
    ("196", "Eredivisie", "Netherlands"),
    ("17", "1. HNL", "Croatia"),
    ("60", "Ekstraklasa", "Poland"),
    ("75", "Premiership", "Scotland"),
    ("9", "Super League", "Greece"),
]
ASIA_LEAGUES = [
    ("313", "Saudi Pro League", "Saudi Arabia"),
    ("67", "Hyundai A-League", "Australia"),
    ("28", "J. League", "Japan"),
]
AMERICAS_LEAGUES = [
    ("23", "Liga Professional", "Argentina"),
    ("24", "Serie A Brazil", "Brazil"),
    ("45", "Liga MX", "Mexico"),
]
ALL_LEAGUES = MAJOR_LEAGUES + MINOR_LEAGUES + ASIA_LEAGUES + AMERICAS_LEAGUES


@dataclass
class TuneResult:
    """
    Result of a single tuning trial.

    Attributes
    ----------
    weights : dict[str, float]
        Factor weights used for this trial (sum to 1.0).
    accuracy : float
        Overall win-prediction accuracy (0-1).
    accuracy_excl_draws : float
        Accuracy excluding matches that ended in a draw.
    best_dc_accuracy : float
        Accuracy of the recommended double-chance bet.
    total_matches : int
        Number of predictions evaluated.
    correct : int
        Number of correct win predictions.
    """

    weights: dict[str, float]
    accuracy: float
    accuracy_excl_draws: float
    best_dc_accuracy: float
    total_matches: int
    correct: int


def _random_weights() -> dict[str, float]:
    """Generate random weights that sum to 1.0."""
    names = [
        "form",
        "position",
        "home",
        "h2h",
        "odds",
        "goals",
        "venue_form",
        "defense",
        "momentum",
        "match_stats",
        "xg",
        "reliability",
    ]
    raw = [random.uniform(0.02, 0.25) for _ in names]
    total = sum(raw)
    return dict(zip(names, (r / total for r in raw)))


def _grid_near_default() -> dict[str, float]:
    """Weights near defaults with small random perturbations."""
    base = {
        "form": 0.15,
        "position": 0.19,
        "home": 0.09,
        "h2h": 0.07,
        "odds": 0.17,
        "goals": 0.11,
        "venue_form": 0.06,
        "defense": 0.05,
        "momentum": 0.06,
        "match_stats": 0.05,
        "xg": 0.05,
        "reliability": 0.04,
    }
    scale = 0.15
    raw = {k: max(0.01, v + random.uniform(-scale, scale)) for k, v in base.items()}
    total = sum(raw.values())
    return {k: v / total for k, v in raw.items()}


def run_backtest_with_weights(
    cache_dir: str | Path,
    weeks: int,
    weights: dict[str, float],
    min_probability: float = 0.0,
) -> BacktestResults | None:
    """
    Run backtest-all-global with given weights using cached data.

    Parameters
    ----------
    cache_dir : str or Path
        Directory with cached API data.
    weeks : int
        Weeks of history (must match what was cached).
    weights : dict[str, float]
        Factor name → weight mapping for BettingModel.
    min_probability : float, optional
        Minimum prediction probability to include.

    Returns
    -------
    BacktestResults or None
        Aggregated results, or None if no matches.
    """
    client = LivescoreClient(cache_dir=cache_dir, cache_only=True)
    model = BettingModel(
        form_weight=weights.get("form", 0.15),
        position_weight=weights.get("position", 0.19),
        home_weight=weights.get("home", 0.09),
        h2h_weight=weights.get("h2h", 0.07),
        odds_weight=weights.get("odds", 0.17),
        goals_weight=weights.get("goals", 0.11),
        venue_form_weight=weights.get("venue_form", 0.06),
        defense_weight=weights.get("defense", 0.05),
        momentum_weight=weights.get("momentum", 0.06),
        match_stats_weight=weights.get("match_stats", 0.05),
        xg_weight=weights.get("xg", 0.05),
        reliability_weight=weights.get("reliability", 0.04),
    )
    backtester = Backtester(client=client, model=model)

    all_results: list[Any] = []
    for comp_id, _league_name, _country in ALL_LEAGUES:
        try:
            results = backtester.run(
                competition_id=comp_id,
                weeks=weeks,
                min_probability=min_probability,
                verbose=False,
                debug=False,
            )
            all_results.extend(results.results)
        except Exception:
            continue

    if not all_results:
        return None

    return BacktestResults(
        results=all_results,
        competition="all",
        from_date=None,
        to_date=None,
    )


def tune(
    cache_dir: str | Path,
    weeks: int = 12,
    trials: int = 20,
    strategy: str = "random",
    min_probability: float = 0.0,
    metric: str = "accuracy_excl_draws",
    verbose: bool = True,
) -> TuneResult | None:
    """
    Run hyperparameter tuning over weight configurations.

    Parameters
    ----------
    cache_dir : str or Path
        Directory with cached API data (from prior backtest with --cache-dir).
    weeks : int
        Weeks of data (must match what was cached).
    trials : int
        Number of weight configurations to try.
    strategy : str
        "random" = random weights, "near_default" = perturb defaults.
    min_probability : float
        Minimum prediction probability to include.
    metric : str
        "accuracy", "accuracy_excl_draws", or "best_dc".
    verbose : bool
        Print progress.

    Returns
    -------
    TuneResult or None
        Best result, or None if no valid trials.
    """
    results: list[TuneResult] = []
    attr = "best_dc_accuracy" if metric == "best_dc" else metric

    for i in range(trials):
        if strategy == "near_default":
            weights = _grid_near_default()
        else:
            weights = _random_weights()

        try:
            bt = run_backtest_with_weights(
                cache_dir=cache_dir,
                weeks=weeks,
                weights=weights,
                min_probability=min_probability,
            )
        except Exception as e:
            if verbose:
                print(f"   Trial {i + 1}/{trials}: ⚠ {e}")
            continue

        if bt is None or not bt.results:
            if verbose:
                print(f"   Trial {i + 1}/{trials}: no matches")
            continue

        r = TuneResult(
            weights=weights,
            accuracy=bt.accuracy,
            accuracy_excl_draws=bt.accuracy_excluding_draws,
            best_dc_accuracy=bt.best_double_chance_accuracy,
            total_matches=bt.total_predictions,
            correct=bt.correct_predictions,
        )
        results.append(r)

        if verbose:
            val = getattr(r, attr)
            print(f"   Trial {i + 1}/{trials}: {metric}={val:.1%} ({r.correct}/{r.total_matches})")

    if not results:
        return None

    def _key(r: TuneResult) -> float:
        """Return the optimization metric for ranking trials."""
        return float(getattr(r, attr))

    best = max(results, key=_key)
    return best


def format_best_weights(weights: dict[str, float]) -> str:
    """
    Format weights for copying into BettingModel.

    Parameters
    ----------
    weights : dict[str, float]
        Factor name → weight mapping.

    Returns
    -------
    str
        Indented ``"name": value,`` lines sorted by name.
    """
    lines = [f'        "{k}": {v:.4f},' for k, v in sorted(weights.items())]
    return "\n".join(lines)
