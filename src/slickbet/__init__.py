"""
SlickBet - Soccer Betting Screener.

Public package API for screening upcoming soccer matches, ranking betting
opportunities, and backtesting the prediction model against historical data.

Examples
--------
>>> from slickbet import BettingScreener
>>> screener = BettingScreener()
>>> result = screener.screen_tomorrow()
>>> for bet in result.get_top_k(5):
...     print(f"Bet on {bet.match.home_team.name}: {bet.probability:.1%}")
"""

__version__ = "0.1.0"
__author__ = "Amirhessam Tahmassebi"

from slickbet.api import (
    HistoricalMatch,
    LivescoreAPIError,
    LivescoreClient,
    Match,
    MatchOutcome,
    MatchScores,
    MatchStatistics,
    Odds,
    Team,
    TeamPerformanceStats,
)
from slickbet.backtest import (
    Backtester,
    BacktestResults,
    PredictionResult,
    format_backtest_report,
)
from slickbet.model import (
    BetOutcome,
    BetPrediction,
    BettingModel,
)
from slickbet.screener import (
    BettingScreener,
    ScreenerConfig,
    ScreenerResult,
    format_prediction,
    format_summary,
)

__all__ = [
    # Version
    "__version__",
    # API
    "HistoricalMatch",
    "LivescoreAPIError",
    "LivescoreClient",
    "Match",
    "MatchOutcome",
    "MatchScores",
    "MatchStatistics",
    "Odds",
    "Team",
    "TeamPerformanceStats",
    # Model
    "BettingModel",
    "BetPrediction",
    "BetOutcome",
    # Screener
    "BettingScreener",
    "ScreenerConfig",
    "ScreenerResult",
    "format_prediction",
    "format_summary",
    # Backtesting
    "Backtester",
    "BacktestResults",
    "PredictionResult",
    "format_backtest_report",
]
