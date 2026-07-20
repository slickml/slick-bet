"""Tests for PDF export functionality."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from assertpy import assert_that

from slickbet.api import (
    HistoricalMatch,
    Match,
    MatchOutcome,
    MatchScores,
    Team,
    TeamPerformanceStats,
)
from slickbet.backtest import BacktestResults, PredictionResult
from slickbet.model import BetOutcome, BetPrediction, BettingModel, DoubleChancePrediction
from slickbet.pdf_export import (
    export_backtest_all_to_pdf,
    export_backtest_to_pdf,
    export_screener_to_pdf,
    get_pdf_output_path,
)
from slickbet.screener import ScreenerResult


class TestGetPdfOutputPath:
    def test_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        path = get_pdf_output_path("report.pdf")
        assert_that(path).contains("assets/predictions")
        assert_that(path).ends_with(".pdf")

    def test_empty_string(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        path = get_pdf_output_path("report.pdf", "")
        assert_that(Path(path).name).is_equal_to("report.pdf")

    def test_absolute_path(self, tmp_path: Path) -> None:
        out = tmp_path / "custom" / "out.pdf"
        path = get_pdf_output_path("ignored.pdf", str(out))
        assert_that(path).is_equal_to(str(out))

    def test_existing_directory(self, tmp_path: Path) -> None:
        d = tmp_path / "pdfs"
        d.mkdir()
        path = get_pdf_output_path("report.pdf", str(d))
        assert_that(path).is_equal_to(str(d / "report.pdf"))

    def test_relative_with_dirs(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        path = get_pdf_output_path("x.pdf", "subdir/my.pdf")
        assert_that(path).contains("subdir")

    def test_bare_filename(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        path = get_pdf_output_path("default.pdf", "custom_name")
        assert_that(Path(path).name).is_equal_to("custom_name.pdf")

    def test_adds_pdf_suffix(self, tmp_path: Path) -> None:
        out = tmp_path / "file"
        path = get_pdf_output_path("x.pdf", str(out))
        assert_that(path).ends_with(".pdf")


def _pred(
    sample_match: Match,
    *,
    outcome: BetOutcome = BetOutcome.HOME_WIN,
    dc: DoubleChancePrediction | None = None,
    prob: float = 0.7,
    with_stats: bool = True,
) -> BetPrediction:
    if not with_stats:
        sample_match.home_performance = None
        sample_match.away_performance = None
    return BetPrediction(
        match=sample_match,
        recommended_outcome=outcome,
        probability=prob,
        confidence=0.4,
        form_score=0.2,
        position_score=0.3,
        home_advantage_score=0.1,
        h2h_score=0.1,
        odds_score=0.1,
        goal_score=0.1,
        venue_form_score=0.1,
        defense_score=0.1,
        momentum_score=0.1,
        match_stats_score=0.1 if with_stats else 0.0,
        xg_score=0.1,
        draw_risk=0.2,
        double_chance=dc or DoubleChancePrediction(0.8, 0.4, 0.6),
        reasoning=["Home form: WWW", "🎲 skip", "Position good"],
    )


class TestExportScreener:
    def test_export_with_predictions(self, sample_match: Match, tmp_path: Path) -> None:
        result = ScreenerResult(
            predictions=[_pred(sample_match)],
            total_matches_scanned=5,
            matches_filtered=3,
            timestamp=datetime.now(timezone.utc),
        )
        preds = [
            _pred(sample_match, dc=DoubleChancePrediction(0.85, 0.3, 0.5), prob=0.7),
            _pred(
                sample_match,
                outcome=BetOutcome.AWAY_WIN,
                dc=DoubleChancePrediction(0.3, 0.78, 0.5),
                prob=0.62,
            ),
            _pred(sample_match, dc=DoubleChancePrediction(0.4, 0.4, 0.75), prob=0.55),
            _pred(sample_match, dc=DoubleChancePrediction(0.5, 0.5, 0.5), prob=0.5),
        ]
        out = tmp_path / "screener.pdf"
        path = export_screener_to_pdf(result, preds, output_path=str(out))
        assert_that(Path(path).exists()).is_true()

    def test_export_empty_predictions(self, tmp_path: Path) -> None:
        result = ScreenerResult(
            predictions=[],
            total_matches_scanned=0,
            matches_filtered=0,
            timestamp=datetime.now(timezone.utc),
        )
        path = export_screener_to_pdf(result, [], output_path=str(tmp_path / "empty.pdf"))
        assert_that(Path(path).exists()).is_true()

    def test_export_default_path(
        self, sample_match: Match, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = ScreenerResult(
            predictions=[],
            total_matches_scanned=0,
            matches_filtered=0,
            timestamp=datetime.now(timezone.utc),
        )
        path = export_screener_to_pdf(result, [], output_path="")
        assert_that(Path(path).exists()).is_true()

    def test_stats_branches(self, sample_match: Match, tmp_path: Path) -> None:
        # no performance
        m1 = Match(
            id="1",
            home_team=sample_match.home_team,
            away_team=sample_match.away_team,
            competition="PL",
            competition_id="2",
            country="England",
            kickoff_time=datetime.now(),
            status="NS",
            home_position=1,
            away_position=2,
        )
        # zero stats both
        m2 = Match(
            id="2",
            home_team=sample_match.home_team,
            away_team=sample_match.away_team,
            competition="PL",
            competition_id="2",
            country="England",
            kickoff_time=datetime.now(),
            status="NS",
            home_performance=TeamPerformanceStats(team_id="1", matches_with_stats=0),
            away_performance=TeamPerformanceStats(team_id="2", matches_with_stats=0),
        )
        # insufficient
        m3 = Match(
            id="3",
            home_team=sample_match.home_team,
            away_team=sample_match.away_team,
            competition="PL",
            competition_id="2",
            country="England",
            kickoff_time=datetime.now(),
            status="NS",
            home_performance=TeamPerformanceStats(team_id="1", matches_with_stats=0),
            away_performance=TeamPerformanceStats(team_id="2", matches_with_stats=3),
        )
        preds = [_pred(m1, with_stats=False), _pred(m2), _pred(m3)]
        # fix match_stats_used for m2/m3
        for p in preds:
            pass
        result = ScreenerResult(
            predictions=preds,
            total_matches_scanned=3,
            matches_filtered=3,
            timestamp=datetime.now(timezone.utc),
        )
        path = export_screener_to_pdf(result, preds, output_path=str(tmp_path / "stats.pdf"))
        assert_that(Path(path).exists()).is_true()

    def test_with_real_model_stats(self, sample_match: Match, tmp_path: Path) -> None:
        pred = BettingModel().predict(sample_match)
        result = ScreenerResult(
            predictions=[pred],
            total_matches_scanned=1,
            matches_filtered=1,
            timestamp=datetime.now(timezone.utc),
        )
        path = export_screener_to_pdf(result, [pred], output_path=str(tmp_path / "model.pdf"))
        assert_that(Path(path).exists()).is_true()


class TestExportBacktest:
    def _results(self) -> BacktestResults:
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
            draw_risk=0.2,
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
        return BacktestResults(
            results=[pr],
            competition="2",
            from_date=datetime(2025, 1, 1),
            to_date=datetime(2025, 2, 1),
        )

    def test_export(self, tmp_path: Path) -> None:
        path = export_backtest_to_pdf(self._results(), output_path=str(tmp_path / "bt.pdf"))
        assert_that(Path(path).exists()).is_true()

    def test_export_empty(self, tmp_path: Path) -> None:
        path = export_backtest_to_pdf(
            BacktestResults(competition="2"),
            output_path=str(tmp_path / "bt_empty.pdf"),
        )
        assert_that(Path(path).exists()).is_true()

    def test_export_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        path = export_backtest_to_pdf(self._results(), output_path="")
        assert_that(Path(path).exists()).is_true()


class TestExportBacktestAll:
    def test_export(self, tmp_path: Path) -> None:
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
        summaries = [
            {
                "name": "Premier League",
                "country": "England",
                "total": 1,
                "correct": 1,
                "accuracy": 1.0,
                "accuracy_excl_draws": 1.0,
                "draws": 0,
                "home_or_draw": 1.0,
                "away_or_draw": 0.0,
                "best_dc": 1.0,
            }
        ]
        path = export_backtest_all_to_pdf(
            league_summaries=summaries,
            all_results=[pr],
            league_type="Major",
            weeks=4,
            output_path=str(tmp_path / "all.pdf"),
        )
        assert_that(Path(path).exists()).is_true()

    def test_export_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
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
        path = export_backtest_all_to_pdf(
            league_summaries=[
                {
                    "name": "L",
                    "country": "C",
                    "total": 1,
                    "correct": 1,
                    "accuracy": 1.0,
                    "accuracy_excl_draws": 1.0,
                    "draws": 0,
                    "home_or_draw": 1.0,
                    "away_or_draw": 0.0,
                    "best_dc": 1.0,
                }
            ],
            all_results=[pr],
            league_type="Asia",
            weeks=2,
            output_path="",
        )
        assert_that(Path(path).exists()).is_true()
