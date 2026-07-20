"""Tests for hyperparameter tuning."""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from assertpy import assert_that

from slickbet.api import HistoricalMatch, Match, MatchOutcome, MatchScores, Team
from slickbet.backtest import BacktestResults, PredictionResult
from slickbet.model import BetOutcome, BetPrediction, DoubleChancePrediction
from slickbet.tune import (
    _grid_near_default,
    _random_weights,
    format_best_weights,
    run_backtest_with_weights,
    tune,
)


def _fake_backtest_results() -> BacktestResults:
    home = Team(id="1", name="H")
    away = Team(id="2", name="A")
    hist = HistoricalMatch(
        id="1",
        fixture_id=None,
        home_team=home,
        away_team=away,
        competition="PL",
        competition_id="2",
        country="E",
        date=datetime(2025, 1, 1),
        status="FINISHED",
        scores=MatchScores(final="1 - 0"),
        outcomes=MatchOutcome(full_time="1"),
    )
    match = Match(
        id="1",
        home_team=home,
        away_team=away,
        competition="PL",
        competition_id="2",
        country="E",
        kickoff_time=datetime(2025, 1, 1),
        status="NS",
    )
    pred = BetPrediction(
        match=match,
        recommended_outcome=BetOutcome.HOME_WIN,
        probability=0.7,
        confidence=0.4,
        form_score=0.0,
        position_score=0.0,
        home_advantage_score=0.0,
        h2h_score=0.0,
        double_chance=DoubleChancePrediction(0.8, 0.4, 0.6),
        reasoning=[],
    )
    pr = PredictionResult(
        match=hist,
        prediction=pred,
        actual_outcome="H",
        predicted_outcome="H",
        is_correct=True,
        probability=0.7,
        confidence=0.4,
        home_or_draw_correct=True,
        away_or_draw_correct=False,
        no_draw_correct=True,
    )
    return BacktestResults(results=[pr], competition="2")


class TestWeightGenerators:
    def test_random_weights_sum(self) -> None:
        w = _random_weights()
        assert_that(sum(w.values())).is_close_to(1.0, 0.001)
        assert_that(len(w)).is_equal_to(12)

    def test_grid_near_default_sum(self) -> None:
        w = _grid_near_default()
        assert_that(sum(w.values())).is_close_to(1.0, 0.001)


class TestFormatBestWeights:
    def test_format(self) -> None:
        text = format_best_weights({"form": 0.1, "position": 0.2})
        assert_that(text).contains('"form": 0.1000')
        assert_that(text).contains('"position": 0.2000')


class TestRunBacktestWithWeights:
    def test_aggregates_results(self, tmp_cache_dir: Path) -> None:
        fake = _fake_backtest_results()
        with patch("slickbet.tune.LivescoreClient"):
            with patch("slickbet.tune.Backtester") as MockBT:
                instance = MockBT.return_value
                instance.run.return_value = fake
                result = run_backtest_with_weights(
                    cache_dir=tmp_cache_dir,
                    weeks=4,
                    weights=_random_weights(),
                )
        assert_that(result).is_not_none()
        assert_that(result.total_predictions).is_greater_than(0)

    def test_no_matches(self, tmp_cache_dir: Path) -> None:
        with patch("slickbet.tune.LivescoreClient"):
            with patch("slickbet.tune.Backtester") as MockBT:
                instance = MockBT.return_value
                instance.run.return_value = BacktestResults(results=[])
                result = run_backtest_with_weights(
                    cache_dir=tmp_cache_dir,
                    weeks=4,
                    weights=_random_weights(),
                )
        assert_that(result).is_none()

    def test_exceptions_continue(self, tmp_cache_dir: Path) -> None:
        with patch("slickbet.tune.LivescoreClient"):
            with patch("slickbet.tune.Backtester") as MockBT:
                instance = MockBT.return_value
                instance.run.side_effect = Exception("fail")
                result = run_backtest_with_weights(
                    cache_dir=tmp_cache_dir,
                    weeks=4,
                    weights=_random_weights(),
                )
        assert_that(result).is_none()


class TestTune:
    def test_tune_random(self, tmp_cache_dir: Path) -> None:
        fake = _fake_backtest_results()
        with patch("slickbet.tune.run_backtest_with_weights", return_value=fake):
            best = tune(
                cache_dir=tmp_cache_dir,
                weeks=4,
                trials=3,
                strategy="random",
                metric="accuracy_excl_draws",
                verbose=True,
            )
        assert_that(best).is_not_none()
        assert_that(best.accuracy).is_greater_than(0)

    def test_tune_near_default_best_dc(self, tmp_cache_dir: Path) -> None:
        fake = _fake_backtest_results()
        with patch("slickbet.tune.run_backtest_with_weights", return_value=fake):
            best = tune(
                cache_dir=tmp_cache_dir,
                trials=2,
                strategy="near_default",
                metric="best_dc",
                verbose=False,
            )
        assert_that(best).is_not_none()

    def test_tune_no_results(self, tmp_cache_dir: Path) -> None:
        with patch("slickbet.tune.run_backtest_with_weights", return_value=None):
            best = tune(cache_dir=tmp_cache_dir, trials=2, verbose=True)
        assert_that(best).is_none()

    def test_tune_exception(self, tmp_cache_dir: Path) -> None:
        with patch("slickbet.tune.run_backtest_with_weights", side_effect=RuntimeError("boom")):
            best = tune(cache_dir=tmp_cache_dir, trials=2, verbose=True)
        assert_that(best).is_none()

    def test_tune_empty_results(self, tmp_cache_dir: Path) -> None:
        with patch(
            "slickbet.tune.run_backtest_with_weights",
            return_value=BacktestResults(results=[]),
        ):
            best = tune(cache_dir=tmp_cache_dir, trials=1, verbose=True)
        assert_that(best).is_none()
