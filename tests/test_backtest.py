"""Tests for backtesting module."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from assertpy import assert_that

from slickbet.api import (
    HistoricalMatch,
    LivescoreAPIError,
    Match,
    MatchOutcome,
    MatchScores,
    Team,
    TeamPerformanceStats,
)
from slickbet.backtest import (
    Backtester,
    BacktestResults,
    PredictionResult,
    format_backtest_report,
)
from slickbet.model import BetOutcome, BetPrediction, BettingModel, DoubleChancePrediction


def _make_pred_result(
    *,
    actual: str = "H",
    predicted: str = "H",
    correct: bool = True,
    probability: float = 0.7,
    confidence: float = 0.4,
    draw_risk: float = 0.2,
    dc_type: str = "1X (Home or Draw)",
    home_team: Team | None = None,
    away_team: Team | None = None,
    date: datetime | None = None,
) -> PredictionResult:
    home = home_team or Team(id="1", name="Home FC")
    away = away_team or Team(id="2", name="Away Utd")
    hist = HistoricalMatch(
        id="h1",
        fixture_id="f1",
        home_team=home,
        away_team=away,
        competition="PL",
        competition_id="2",
        country="England",
        date=date or datetime(2025, 1, 10),
        status="FINISHED",
        scores=MatchScores(final="2 - 1"),
        outcomes=MatchOutcome(full_time="1" if actual == "H" else ("2" if actual == "A" else "X")),
    )
    match = Match(
        id="h1",
        home_team=home,
        away_team=away,
        competition="PL",
        competition_id="2",
        country="England",
        kickoff_time=hist.date,
        status="NS",
    )
    dc_probs = {
        "1X (Home or Draw)": (0.8, 0.4, 0.6),
        "X2 (Away or Draw)": (0.4, 0.8, 0.6),
        "12 (No Draw)": (0.4, 0.4, 0.9),
    }
    h, a, n = dc_probs[dc_type]
    pred = BetPrediction(
        match=match,
        recommended_outcome=BetOutcome.HOME_WIN if predicted == "H" else BetOutcome.AWAY_WIN,
        probability=probability,
        confidence=confidence,
        form_score=0.1,
        position_score=0.1,
        home_advantage_score=0.1,
        h2h_score=0.1,
        draw_risk=draw_risk,
        double_chance=DoubleChancePrediction(h, a, n),
        reasoning=["reason1", "reason2", "reason3"],
    )
    return PredictionResult(
        match=hist,
        prediction=pred,
        actual_outcome=actual,
        predicted_outcome=predicted,
        is_correct=correct,
        probability=probability,
        confidence=confidence,
        home_or_draw_correct=actual in ("H", "D"),
        away_or_draw_correct=actual in ("A", "D"),
        no_draw_correct=actual in ("H", "A"),
    )


class TestPredictionResult:
    def test_properties(self) -> None:
        r = _make_pred_result(actual="H", predicted="H")
        assert_that(r.predicted_team).is_equal_to("Home FC")
        assert_that(r.actual_winner).is_equal_to("Home FC")
        assert_that(r.best_double_chance_correct).is_true()

    def test_away_and_draw(self) -> None:
        r = _make_pred_result(actual="A", predicted="A", dc_type="X2 (Away or Draw)")
        assert_that(r.predicted_team).is_equal_to("Away Utd")
        assert_that(r.actual_winner).is_equal_to("Away Utd")
        assert_that(r.best_double_chance_correct).is_true()

        r2 = _make_pred_result(actual="D", predicted="H")
        assert_that(r2.actual_winner).is_equal_to("Draw")

        r3 = _make_pred_result(actual="H", predicted="H", dc_type="12 (No Draw)")
        assert_that(r3.best_double_chance_correct).is_true()

    def test_no_double_chance(self) -> None:
        r = _make_pred_result()
        r.prediction.double_chance = None
        assert_that(r.best_double_chance_correct).is_false()


class TestBacktestResults:
    def test_empty_metrics(self) -> None:
        br = BacktestResults()
        assert_that(br.accuracy).is_equal_to(0.0)
        assert_that(br.home_accuracy).is_equal_to(0.0)
        assert_that(br.away_accuracy).is_equal_to(0.0)
        assert_that(br.high_confidence_accuracy).is_equal_to(0.0)
        assert_that(br.high_confidence_accuracy_excl_draws).is_equal_to(0.0)
        assert_that(br.low_draw_risk_accuracy).is_equal_to(0.0)
        assert_that(br.high_probability_accuracy).is_equal_to(0.0)
        assert_that(br.high_probability_accuracy_excl_draws).is_equal_to(0.0)
        assert_that(br.accuracy_excluding_draws).is_equal_to(0.0)
        assert_that(br.home_or_draw_accuracy).is_equal_to(0.0)
        assert_that(br.away_or_draw_accuracy).is_equal_to(0.0)
        assert_that(br.no_draw_accuracy).is_equal_to(0.0)
        assert_that(br.best_double_chance_accuracy).is_equal_to(0.0)

    def test_populated_metrics(self) -> None:
        results = [
            _make_pred_result(
                actual="H", predicted="H", correct=True, probability=0.7, confidence=0.4
            ),
            _make_pred_result(
                actual="A", predicted="A", correct=True, probability=0.65, confidence=0.35
            ),
            _make_pred_result(
                actual="D",
                predicted="H",
                correct=False,
                probability=0.55,
                confidence=0.2,
                draw_risk=0.4,
            ),
            _make_pred_result(
                actual="H", predicted="A", correct=False, probability=0.5, confidence=0.1
            ),
        ]
        br = BacktestResults(
            results=results,
            competition="2",
            from_date=datetime(2025, 1, 1),
            to_date=datetime(2025, 2, 1),
        )
        assert_that(br.total_predictions).is_equal_to(4)
        assert_that(br.correct_predictions).is_equal_to(2)
        assert_that(br.accuracy).is_equal_to(0.5)
        assert_that(br.draws_encountered).is_equal_to(1)
        assert_that(br.home_predictions).is_not_empty()
        assert_that(br.away_predictions).is_not_empty()
        assert_that(br.home_accuracy).is_greater_than_or_equal_to(0)
        assert_that(br.away_accuracy).is_greater_than_or_equal_to(0)
        assert_that(br.high_confidence_results).is_not_empty()
        assert_that(br.high_probability_results).is_not_empty()
        assert_that(br.low_draw_risk_results).is_not_empty()
        filtered = br.by_probability_threshold(0.6)
        assert_that(filtered.total_predictions).is_equal_to(2)


class TestBacktester:
    @pytest.fixture
    def mock_client(self) -> MagicMock:
        return MagicMock()

    def test_init_with_client(self, mock_client: MagicMock) -> None:
        bt = Backtester(client=mock_client)
        assert_that(bt.client).is_equal_to(mock_client)

    def test_init_creates_client(self, api_credentials: None, tmp_cache_dir: Path) -> None:
        bt = Backtester(cache_dir=tmp_cache_dir, cache_only=False)
        assert_that(bt.client).is_not_none()

    def test_historical_to_match(self, sample_historical_match: HistoricalMatch) -> None:
        bt = Backtester(client=MagicMock())
        match = bt._historical_to_match(sample_historical_match)
        assert_that(match.status).is_equal_to("NS")
        assert_that(match.id).is_equal_to(sample_historical_match.id)

    def test_get_country_flag(self) -> None:
        bt = Backtester(client=MagicMock())
        assert_that(bt._get_country_flag("Germany")).is_equal_to("🇩🇪")
        assert_that(bt._get_country_flag("")).is_equal_to("")
        assert_that(bt._get_country_flag("Unknownland")).is_equal_to("")
        assert_that(bt._get_country_flag("Saudi")).is_equal_to("🇸🇦")  # partial

    def test_fetch_all_history(self, mock_client: MagicMock) -> None:
        hist = HistoricalMatch(
            id="1",
            fixture_id=None,
            home_team=Team(id="1", name="H"),
            away_team=Team(id="2", name="A"),
            competition="PL",
            competition_id="2",
            country="England",
            date=datetime(2025, 1, 15),
            status="FINISHED",
            scores=MatchScores(final="1 - 0"),
            outcomes=MatchOutcome(full_time="1"),
        )
        out_of_range = HistoricalMatch(
            id="2",
            fixture_id=None,
            home_team=Team(id="1", name="H"),
            away_team=Team(id="2", name="A"),
            competition="PL",
            competition_id="99",
            country="England",
            date=datetime(2025, 1, 15),
            status="FINISHED",
            scores=MatchScores(final="1 - 0"),
            outcomes=MatchOutcome(full_time="1"),
        )
        mock_client.get_history.side_effect = [[hist, out_of_range], []]
        bt = Backtester(client=mock_client)
        matches = bt._fetch_all_history(
            "2", datetime(2025, 1, 1), datetime(2025, 1, 31), verbose=True
        )
        assert_that(len(matches)).is_equal_to(1)

    def test_fetch_api_error(self, mock_client: MagicMock) -> None:
        mock_client.get_history.side_effect = LivescoreAPIError("fail")
        bt = Backtester(client=mock_client)
        matches = bt._fetch_all_history(
            "2", datetime(2025, 1, 1), datetime(2025, 1, 31), verbose=True
        )
        assert_that(matches).is_empty()

    def test_enrich_for_backtest(self, mock_client: MagicMock, sample_match: Match) -> None:
        mock_client.get_team_form.return_value = "WWW"
        mock_client.get_team_standings.return_value = {"1": 1, "2": 18}
        mock_client.get_head_to_head.return_value = {"matches_played": 1}
        mock_client.get_team_performance_stats.return_value = TeamPerformanceStats(
            team_id="1", matches_with_stats=0
        )
        bt = Backtester(client=mock_client)
        enriched = bt._enrich_for_backtest(sample_match, datetime.now(), verbose=True)
        assert_that(enriched.home_form).is_equal_to("WWW")

    def test_enrich_missing_ids(self, mock_client: MagicMock) -> None:
        match = Match(
            id="1",
            home_team=Team(id="", name="H"),
            away_team=Team(id="", name="A"),
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
        )
        bt = Backtester(client=mock_client)
        assert_that(bt._enrich_for_backtest(match, datetime.now())).is_equal_to(match)

    def test_enrich_exceptions(self, mock_client: MagicMock, sample_match: Match) -> None:
        mock_client.get_team_form.side_effect = Exception("x")
        mock_client.get_team_standings.side_effect = Exception("x")
        mock_client.get_head_to_head.side_effect = Exception("x")
        mock_client.get_team_performance_stats.side_effect = Exception("x")
        bt = Backtester(client=mock_client)
        result = bt._enrich_for_backtest(sample_match, datetime.now())
        assert_that(result.id).is_equal_to(sample_match.id)

    def test_print_debug_match(self, capsys: pytest.CaptureFixture[str]) -> None:
        bt = Backtester(client=MagicMock())
        r = _make_pred_result(predicted="A", actual="A")
        bt._print_debug_match(r)
        out = capsys.readouterr().out
        assert_that(out).contains("ACTUAL RESULT")
        assert_that(out).contains("OUR PREDICTION")

        r2 = _make_pred_result(predicted="H", actual="H")
        bt._print_debug_match(r2)

    def test_run(self, mock_client: MagicMock, sample_historical_match: HistoricalMatch) -> None:
        hist_away = HistoricalMatch(
            id="h2",
            fixture_id=None,
            home_team=Team(id="1", name="H"),
            away_team=Team(id="2", name="A"),
            competition="PL",
            competition_id="2",
            country="England",
            date=datetime(2025, 1, 12),
            status="FINISHED",
            scores=MatchScores(final="0 - 2"),
            outcomes=MatchOutcome(full_time="2"),
        )
        invalid = HistoricalMatch(
            id="h3",
            fixture_id=None,
            home_team=Team(id="1", name="H"),
            away_team=Team(id="2", name="A"),
            competition="PL",
            competition_id="2",
            country="England",
            date=datetime(2025, 1, 13),
            status="LIVE",
            scores=MatchScores(),
            outcomes=MatchOutcome(full_time=None),
        )
        mock_client.get_history.side_effect = [
            [sample_historical_match, hist_away, invalid],
            [],
        ]
        mock_client.get_team_form.return_value = "WWDLW"
        mock_client.get_team_standings.return_value = {"1": 1, "2": 18}
        mock_client.get_head_to_head.return_value = {
            "matches_played": 5,
            "home_wins": 4,
            "away_wins": 0,
            "draws": 1,
        }
        mock_client.get_team_performance_stats.return_value = TeamPerformanceStats(
            team_id="1", matches_analyzed=5, matches_with_stats=2
        )

        bt = Backtester(client=mock_client, model=BettingModel())
        results = bt.run(
            competition_id="2",
            weeks=2,
            from_date=datetime(2025, 1, 1),
            to_date=datetime(2025, 1, 31),
            min_probability=0.0,
            verbose=True,
            debug=True,
        )
        assert_that(results.total_predictions).is_greater_than(0)

    def test_run_min_probability_skip(
        self, mock_client: MagicMock, sample_historical_match: HistoricalMatch
    ) -> None:
        mock_client.get_history.side_effect = [[sample_historical_match], []]
        mock_client.get_team_form.return_value = ""
        mock_client.get_team_standings.return_value = {}
        mock_client.get_head_to_head.return_value = {}
        mock_client.get_team_performance_stats.return_value = TeamPerformanceStats(team_id="1")

        bt = Backtester(client=mock_client)
        results = bt.run(
            competition_id="2",
            from_date=datetime(2025, 1, 1),
            to_date=datetime(2025, 1, 31),
            min_probability=0.99,
            verbose=False,
            debug=False,
        )
        assert_that(results.total_predictions).is_equal_to(0)

    def test_run_process_exception(
        self, mock_client: MagicMock, sample_historical_match: HistoricalMatch
    ) -> None:
        mock_client.get_history.side_effect = [[sample_historical_match], []]
        bt = Backtester(client=mock_client)
        with patch.object(bt, "_enrich_for_backtest", side_effect=RuntimeError("boom")):
            results = bt.run(
                competition_id="2",
                from_date=datetime(2025, 1, 1),
                to_date=datetime(2025, 1, 31),
                verbose=True,
            )
        assert_that(results.total_predictions).is_equal_to(0)


class TestFormatBacktestReport:
    def test_empty(self) -> None:
        report = format_backtest_report(BacktestResults(competition="2"))
        assert_that(report).contains("No predictions")

    def test_empty_with_dates(self) -> None:
        report = format_backtest_report(
            BacktestResults(
                competition="2",
                from_date=datetime(2025, 1, 1),
                to_date=datetime(2025, 2, 1),
            )
        )
        assert_that(report).contains("2025-01-01")

    def test_populated(self) -> None:
        results = BacktestResults(
            results=[
                _make_pred_result(actual="H", predicted="H", correct=True, probability=0.7),
                _make_pred_result(
                    actual="A",
                    predicted="A",
                    correct=True,
                    probability=0.65,
                    date=datetime(2025, 1, 11),
                ),
            ],
            competition="2",
            from_date=datetime(2025, 1, 1),
            to_date=datetime(2025, 2, 1),
        )
        report = format_backtest_report(results)
        assert_that(report).contains("OVERALL PERFORMANCE")
        assert_that(report).contains("DOUBLE CHANCE")
        assert_that(report).contains("ALL PREDICTIONS")
