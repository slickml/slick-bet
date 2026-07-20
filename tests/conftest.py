"""Shared fixtures for slickbet tests."""

from datetime import datetime
from pathlib import Path

import pytest

from slickbet.api import (
    HistoricalMatch,
    Match,
    MatchOutcome,
    MatchScores,
    Odds,
    Team,
    TeamPerformanceStats,
)
from slickbet.model import (
    BetPrediction,
    BettingModel,
    DoubleChancePrediction,
)


@pytest.fixture
def tmp_cache_dir(tmp_path: Path) -> Path:
    """Temporary directory for API cache files."""
    cache = tmp_path / "api_cache"
    cache.mkdir()
    return cache


@pytest.fixture
def home_team() -> Team:
    """Sample home team."""
    return Team(id="1", name="Home FC", country="England")


@pytest.fixture
def away_team() -> Team:
    """Sample away team."""
    return Team(id="2", name="Away United", country="England")


@pytest.fixture
def sample_odds() -> Odds:
    """Sample bookmaker odds favoring home."""
    return Odds(home_win=1.80, draw=3.40, away_win=4.50)


@pytest.fixture
def sample_performance_home() -> TeamPerformanceStats:
    """Strong home team performance stats."""
    return TeamPerformanceStats(
        team_id="1",
        matches_analyzed=10,
        goals_scored=20,
        goals_conceded=8,
        goals_per_game=2.0,
        goals_conceded_per_game=0.8,
        goal_difference=12,
        clean_sheets=5,
        clean_sheet_rate=0.5,
        games_scored=9,
        scoring_rate=0.9,
        home_games=5,
        home_wins=4,
        home_win_rate=0.8,
        away_games=5,
        away_wins=2,
        away_win_rate=0.4,
        total_points=22,
        points_per_game=2.2,
        ht_wins=6,
        ht_draws=2,
        ht_losses=2,
        ht_lead_rate=0.6,
        comebacks=1,
        collapses=1,
        comeback_rate=0.5,
        wins=6,
        draws=2,
        losses=2,
        win_rate=0.6,
        matches_with_stats=5,
        matches_with_attacks=5,
        matches_with_dangerous_attacks=5,
        matches_with_shots=5,
        avg_possession=58.0,
        avg_corners=6.0,
        avg_attacks=110.0,
        avg_dangerous_attacks=45.0,
        avg_shots_on_target=5.5,
        avg_shots_off_target=4.0,
        avg_expected_goals=1.8,
        avg_expected_goals_against=0.9,
        avg_expected_goal_difference=0.9,
        goal_conversion_rate=0.36,
        shot_accuracy=0.58,
        avg_saves=2.0,
        avg_yellow_cards=1.5,
        avg_red_cards=0.1,
        avg_cards=1.7,
        reliability_score=0.66,
    )


@pytest.fixture
def sample_performance_away() -> TeamPerformanceStats:
    """Weaker away team performance stats."""
    return TeamPerformanceStats(
        team_id="2",
        matches_analyzed=10,
        goals_scored=8,
        goals_conceded=18,
        goals_per_game=0.8,
        goals_conceded_per_game=1.8,
        goal_difference=-10,
        clean_sheets=1,
        clean_sheet_rate=0.1,
        games_scored=5,
        scoring_rate=0.5,
        home_games=5,
        home_wins=1,
        home_win_rate=0.2,
        away_games=5,
        away_wins=0,
        away_win_rate=0.0,
        total_points=8,
        points_per_game=0.8,
        ht_wins=1,
        ht_draws=3,
        ht_losses=6,
        ht_lead_rate=0.1,
        comebacks=0,
        collapses=2,
        comeback_rate=0.0,
        wins=1,
        draws=3,
        losses=6,
        win_rate=0.1,
        matches_with_stats=5,
        matches_with_attacks=5,
        matches_with_dangerous_attacks=5,
        matches_with_shots=5,
        avg_possession=42.0,
        avg_corners=3.5,
        avg_attacks=80.0,
        avg_dangerous_attacks=25.0,
        avg_shots_on_target=2.5,
        avg_shots_off_target=5.0,
        avg_expected_goals=0.9,
        avg_expected_goals_against=1.7,
        avg_expected_goal_difference=-0.8,
        goal_conversion_rate=0.32,
        shot_accuracy=0.33,
        avg_saves=4.0,
        avg_yellow_cards=2.5,
        avg_red_cards=0.3,
        avg_cards=3.1,
        reliability_score=0.38,
    )


@pytest.fixture
def sample_match(
    home_team: Team,
    away_team: Team,
    sample_odds: Odds,
    sample_performance_home: TeamPerformanceStats,
    sample_performance_away: TeamPerformanceStats,
) -> Match:
    """Fully-populated sample match for model/screener tests."""
    return Match(
        id="12345",
        home_team=home_team,
        away_team=away_team,
        competition="Premier League",
        competition_id="2",
        country="England",
        kickoff_time=datetime(2025, 6, 15, 15, 0, 0),
        status="NS",
        pre_odds=sample_odds,
        home_form="WWWDW",
        away_form="LLDLL",
        home_position=1,
        away_position=18,
        head_to_head={
            "matches_played": 5,
            "home_wins": 4,
            "away_wins": 0,
            "draws": 1,
            "home_win_rate": 0.8,
            "away_win_rate": 0.0,
        },
        home_performance=sample_performance_home,
        away_performance=sample_performance_away,
    )


@pytest.fixture
def minimal_match(home_team: Team, away_team: Team) -> Match:
    """Match with no optional statistics."""
    return Match(
        id="99999",
        home_team=home_team,
        away_team=away_team,
        competition="Unknown League",
        competition_id="99",
        country="Unknown",
        kickoff_time=datetime.now(),
        status="NS",
    )


@pytest.fixture
def sample_historical_match(home_team: Team, away_team: Team, sample_odds: Odds) -> HistoricalMatch:
    """Completed historical match with home win."""
    return HistoricalMatch(
        id="h1",
        fixture_id="f1",
        home_team=home_team,
        away_team=away_team,
        competition="Premier League",
        competition_id="2",
        country="England",
        date=datetime(2025, 1, 10),
        status="FINISHED",
        scores=MatchScores(final="2 - 1", half_time="1 - 0", full_time="2 - 1"),
        outcomes=MatchOutcome(half_time="1", full_time="1"),
        pre_odds=sample_odds,
        location="Stadium",
        round="20",
    )


@pytest.fixture
def sample_match_statistics() -> "object":
    """Sample MatchStatistics with full data."""
    from slickbet.api import MatchStatistics

    return MatchStatistics(
        possession=(55, 45),
        shots_on_target=(6, 3),
        shots_off_target=(4, 5),
        corners=(7, 3),
        fouls=(10, 12),
        yellow_cards=(2, 3),
        red_cards=(0, 1),
        offsides=(1, 2),
        saves=(2, 5),
        attacks=(120, 90),
        dangerous_attacks=(50, 30),
        expected_goals=(1.8, 0.9),
    )


@pytest.fixture
def model() -> BettingModel:
    """Default betting model."""
    return BettingModel()


@pytest.fixture
def sample_prediction(sample_match: Match, model: BettingModel) -> BetPrediction:
    """Prediction generated from sample_match."""
    return model.predict(sample_match)


@pytest.fixture
def sample_double_chance() -> DoubleChancePrediction:
    """Sample double chance prediction."""
    return DoubleChancePrediction(
        home_or_draw_prob=0.75,
        away_or_draw_prob=0.45,
        no_draw_prob=0.70,
    )


@pytest.fixture
def api_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set fake API credentials in the environment."""
    monkeypatch.setenv("LIVESCORE_API_KEY", "test-key")
    monkeypatch.setenv("LIVESCORE_API_SECRET", "test-secret")
