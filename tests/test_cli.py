"""Tests for the slickbet CLI."""

from argparse import Namespace
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from assertpy import assert_that

from slickbet.api import LivescoreAPIError, Match
from slickbet.backtest import BacktestResults, PredictionResult
from slickbet.cli import (
    create_parser,
    main,
    output_backtest_json,
    output_json,
    run_backtest,
    run_backtest_all,
    run_competitions,
    run_debug,
    run_screener,
    run_tune,
)
from slickbet.model import BetOutcome, BetPrediction, DoubleChancePrediction
from slickbet.screener import ScreenerResult
from slickbet.tune import TuneResult


def _ns(**kwargs: object) -> Namespace:
    defaults: dict[str, object] = {
        "command": None,
        "top": 5,
        "date": None,
        "days": 1,
        "min_prob": 0.55,
        "min_conf": 0.0,
        "country": None,
        "competition": None,
        "league": None,
        "no_stats": False,
        "workers": 4,
        "major_only": False,
        "asia_only": False,
        "americas_only": False,
        "all_leagues": False,
        "json": False,
        "pdf": None,
        "weeks": 4,
        "from_date": None,
        "to_date": None,
        "debug": False,
        "cache_dir": None,
        "cache_only": False,
        "include_asia": False,
        "include_americas": False,
        "include_african": False,
        "african_only": False,
        "search": None,
        "trials": 5,
        "strategy": "random",
        "metric": "accuracy_excl_draws",
        "quiet": False,
        "home_only": False,
        "away_only": False,
        "summary_only": False,
    }
    defaults.update(kwargs)
    return Namespace(**defaults)


@pytest.fixture
def sample_pred(sample_match: Match) -> BetPrediction:
    return BetPrediction(
        match=sample_match,
        recommended_outcome=BetOutcome.HOME_WIN,
        probability=0.7,
        confidence=0.4,
        form_score=0.2,
        position_score=0.3,
        home_advantage_score=0.1,
        h2h_score=0.1,
        double_chance=DoubleChancePrediction(0.85, 0.4, 0.7),
        reasoning=["strong form"],
    )


@pytest.fixture
def sample_screener_result(sample_pred: BetPrediction) -> ScreenerResult:
    return ScreenerResult(
        predictions=[sample_pred],
        total_matches_scanned=10,
        matches_filtered=1,
        timestamp=datetime.now(),
    )


@pytest.fixture
def sample_backtest_results(sample_historical_match, sample_pred: BetPrediction) -> BacktestResults:
    pred = PredictionResult(
        match=sample_historical_match,
        prediction=sample_pred,
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
        results=[pred],
        competition="Premier League",
        from_date=datetime(2025, 1, 1),
        to_date=datetime(2025, 1, 31),
    )


class TestCreateParser:
    def test_default_screener_args(self) -> None:
        parser = create_parser()
        args = parser.parse_args([])
        assert_that(args.command).is_none()
        assert_that(args.top).is_equal_to(5)

    def test_subcommands(self) -> None:
        parser = create_parser()
        for cmd in ("competitions", "backtest", "backtest-all", "debug"):
            args = parser.parse_args([cmd])
            assert_that(args.command).is_equal_to(cmd)
        args = parser.parse_args(["tune", "--cache-dir", "/tmp/cache"])
        assert_that(args.command).is_equal_to("tune")

    def test_backtest_flags(self) -> None:
        parser = create_parser()
        args = parser.parse_args(
            ["backtest", "--competition", "2", "--weeks", "8", "--json", "--debug"]
        )
        assert_that(args.competition).is_equal_to("2")
        assert_that(args.weeks).is_equal_to(8)
        assert_that(args.json).is_true()
        assert_that(args.debug).is_true()


class TestMainRouting:
    def test_routes_competitions(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.argv", ["slickbet", "competitions"])
        with patch("slickbet.cli.run_competitions", return_value=0) as mock:
            assert_that(main()).is_equal_to(0)
            mock.assert_called_once()

    def test_routes_backtest(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.argv", ["slickbet", "backtest"])
        with patch("slickbet.cli.run_backtest", return_value=0) as mock:
            assert_that(main()).is_equal_to(0)
            mock.assert_called_once()

    def test_routes_backtest_all(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.argv", ["slickbet", "backtest-all"])
        with patch("slickbet.cli.run_backtest_all", return_value=0) as mock:
            assert_that(main()).is_equal_to(0)
            mock.assert_called_once()

    def test_routes_tune(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.argv", ["slickbet", "tune", "--cache-dir", "data/cache"])
        with patch("slickbet.cli.run_tune", return_value=0) as mock:
            assert_that(main()).is_equal_to(0)
            mock.assert_called_once()

    def test_routes_debug(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.argv", ["slickbet", "debug"])
        with patch("slickbet.cli.run_debug", return_value=0) as mock:
            assert_that(main()).is_equal_to(0)
            mock.assert_called_once()

    def test_routes_default_screener(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.argv", ["slickbet", "--top", "3"])
        with patch("slickbet.cli.run_screener", return_value=0) as mock:
            assert_that(main()).is_equal_to(0)
            mock.assert_called_once()


class TestRunCompetitions:
    def test_success(self) -> None:
        args = _ns(command="competitions", country=None, search=None)
        comps = [
            {"id": "2", "name": "Premier League", "country_name": "England"},
            {"id": "1", "name": "Bundesliga", "country_name": "Germany"},
            {"id": "3", "name": "La Liga", "country_name": "Spain"},
        ]
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.return_value.get_competitions.return_value = comps
            assert_that(run_competitions(args)).is_equal_to(0)

    def test_filter_country_found(self) -> None:
        args = _ns(command="competitions", country="England", search=None)
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            client = MockClient.return_value
            client.get_countries.return_value = [
                {"id": "1", "name": "England"},
                {"id": "2", "name": "Spain"},
            ]
            client.get_competitions.return_value = [
                {"id": "2", "name": "Premier League", "country_name": "England"},
            ]
            assert_that(run_competitions(args)).is_equal_to(0)

    def test_country_not_found(self) -> None:
        args = _ns(command="competitions", country="Atlantis", search=None)
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.return_value.get_countries.return_value = [
                {"id": "1", "name": "England"},
            ]
            assert_that(run_competitions(args)).is_equal_to(1)

    def test_search_filter(self) -> None:
        args = _ns(command="competitions", country=None, search="Premier")
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.return_value.get_competitions.return_value = [
                {"id": "2", "name": "Premier League", "country_name": "England"},
                {"id": "1", "name": "Bundesliga", "country_name": "Germany"},
            ]
            assert_that(run_competitions(args)).is_equal_to(0)

    def test_search_no_match(self) -> None:
        args = _ns(command="competitions", country=None, search="zzzz")
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.return_value.get_competitions.return_value = [
                {"id": "2", "name": "Premier League", "country_name": "England"},
            ]
            assert_that(run_competitions(args)).is_equal_to(1)

    def test_no_competitions(self) -> None:
        args = _ns(command="competitions")
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.return_value.get_competitions.return_value = []
            assert_that(run_competitions(args)).is_equal_to(1)

    def test_api_error(self) -> None:
        args = _ns(command="competitions")
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.side_effect = LivescoreAPIError("fail")
            assert_that(run_competitions(args)).is_equal_to(1)

    def test_unexpected_error(self) -> None:
        args = _ns(command="competitions")
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.side_effect = RuntimeError("boom")
            assert_that(run_competitions(args)).is_equal_to(1)


class TestRunBacktest:
    def test_report(self, sample_backtest_results: BacktestResults) -> None:
        args = _ns(command="backtest", competition="2", json=False, pdf=None)
        with patch("slickbet.cli.Backtester") as MockBT:
            MockBT.return_value.run.return_value = sample_backtest_results
            assert_that(run_backtest(args)).is_equal_to(0)

    def test_json(
        self, sample_backtest_results: BacktestResults, capsys: pytest.CaptureFixture
    ) -> None:
        args = _ns(command="backtest", competition="2", json=True)
        with patch("slickbet.cli.Backtester") as MockBT:
            MockBT.return_value.run.return_value = sample_backtest_results
            assert_that(run_backtest(args)).is_equal_to(0)
            assert_that(capsys.readouterr().out).contains("accuracy")

    def test_pdf(self, sample_backtest_results: BacktestResults, tmp_path: Path) -> None:
        out = str(tmp_path / "bt.pdf")
        args = _ns(command="backtest", competition="2", pdf=out)
        with (
            patch("slickbet.cli.Backtester") as MockBT,
            patch("slickbet.cli.export_backtest_to_pdf", return_value=out) as mock_pdf,
        ):
            MockBT.return_value.run.return_value = sample_backtest_results
            assert_that(run_backtest(args)).is_equal_to(0)
            mock_pdf.assert_called_once()

    def test_pdf_empty_flag(self, sample_backtest_results: BacktestResults) -> None:
        args = _ns(command="backtest", competition="2", pdf="")
        with (
            patch("slickbet.cli.Backtester") as MockBT,
            patch("slickbet.cli.export_backtest_to_pdf", return_value="x.pdf"),
        ):
            MockBT.return_value.run.return_value = sample_backtest_results
            assert_that(run_backtest(args)).is_equal_to(0)

    def test_invalid_to_date(self) -> None:
        args = _ns(to_date="bad")
        assert_that(run_backtest(args)).is_equal_to(1)

    def test_invalid_from_date(self) -> None:
        args = _ns(from_date="bad")
        assert_that(run_backtest(args)).is_equal_to(1)

    def test_valid_dates(self, sample_backtest_results: BacktestResults) -> None:
        args = _ns(from_date="2025-01-01", to_date="2025-01-31", competition="2")
        with patch("slickbet.cli.Backtester") as MockBT:
            MockBT.return_value.run.return_value = sample_backtest_results
            assert_that(run_backtest(args)).is_equal_to(0)

    def test_api_error(self) -> None:
        args = _ns(competition="2")
        with patch("slickbet.cli.Backtester") as MockBT:
            MockBT.return_value.run.side_effect = LivescoreAPIError("x")
            assert_that(run_backtest(args)).is_equal_to(1)

    def test_unexpected_error(self) -> None:
        args = _ns(competition="2")
        with patch("slickbet.cli.Backtester") as MockBT:
            MockBT.return_value.run.side_effect = RuntimeError("x")
            assert_that(run_backtest(args)).is_equal_to(1)


class TestRunBacktestAll:
    def _league_run(self, sample_backtest_results: BacktestResults) -> MagicMock:
        mock = MagicMock()
        mock.run.return_value = sample_backtest_results
        return mock

    def test_success(self, sample_backtest_results: BacktestResults) -> None:
        args = _ns(
            command="backtest-all",
            weeks=1,
            include_asia=False,
            include_americas=False,
            asia_only=False,
            americas_only=False,
            pdf=None,
            debug=False,
        )
        with patch("slickbet.cli.Backtester") as MockBT:
            MockBT.return_value = self._league_run(sample_backtest_results)
            assert_that(run_backtest_all(args)).is_equal_to(0)

    def test_asia_only(self, sample_backtest_results: BacktestResults) -> None:
        args = _ns(asia_only=True, americas_only=False, weeks=1, pdf=None)
        with patch("slickbet.cli.Backtester") as MockBT:
            MockBT.return_value = self._league_run(sample_backtest_results)
            assert_that(run_backtest_all(args)).is_equal_to(0)

    def test_americas_only(self, sample_backtest_results: BacktestResults) -> None:
        args = _ns(asia_only=False, americas_only=True, weeks=1, pdf=None)
        with patch("slickbet.cli.Backtester") as MockBT:
            MockBT.return_value = self._league_run(sample_backtest_results)
            assert_that(run_backtest_all(args)).is_equal_to(0)

    def test_include_asia_americas(self, sample_backtest_results: BacktestResults) -> None:
        args = _ns(
            include_asia=True,
            include_americas=True,
            asia_only=False,
            americas_only=False,
            weeks=1,
            pdf=None,
        )
        with patch("slickbet.cli.Backtester") as MockBT:
            MockBT.return_value = self._league_run(sample_backtest_results)
            assert_that(run_backtest_all(args)).is_equal_to(0)

    def test_pdf(self, sample_backtest_results: BacktestResults, tmp_path: Path) -> None:
        out = str(tmp_path / "all.pdf")
        args = _ns(weeks=1, pdf=out, asia_only=True)
        with (
            patch("slickbet.cli.Backtester") as MockBT,
            patch("slickbet.cli.export_backtest_all_to_pdf", return_value=out),
        ):
            MockBT.return_value = self._league_run(sample_backtest_results)
            assert_that(run_backtest_all(args)).is_equal_to(0)

    def test_league_exception_continues(self, sample_backtest_results: BacktestResults) -> None:
        args = _ns(asia_only=True, weeks=1, pdf=None)
        bt = MagicMock()
        bt.run.side_effect = [
            RuntimeError("skip"),
            sample_backtest_results,
            sample_backtest_results,
        ]
        with patch("slickbet.cli.Backtester", return_value=bt):
            # Asia has 3 leagues — first fails, rest succeed
            assert_that(run_backtest_all(args)).is_equal_to(0)

    def test_no_results(self) -> None:
        args = _ns(asia_only=True, weeks=1, pdf=None)
        empty = BacktestResults(results=[], competition="x", from_date=None, to_date=None)
        with patch("slickbet.cli.Backtester") as MockBT:
            MockBT.return_value.run.return_value = empty
            code = run_backtest_all(args)
            assert_that(code).is_equal_to(1)


class TestRunTune:
    def test_success(self) -> None:
        args = _ns(
            cache_dir="data/c",
            weeks=4,
            trials=2,
            strategy="random",
            metric="accuracy",
            quiet=False,
            min_prob=0.0,
        )
        best = TuneResult(
            weights={"form": 1.0},
            accuracy=0.6,
            accuracy_excl_draws=0.7,
            best_dc_accuracy=0.8,
            total_matches=10,
            correct=6,
        )
        with patch("slickbet.cli.tune", return_value=best):
            assert_that(run_tune(args)).is_equal_to(0)

    def test_none_result(self) -> None:
        args = _ns(cache_dir="data/c", weeks=4, trials=1, quiet=True, min_prob=0.0)
        with patch("slickbet.cli.tune", return_value=None):
            assert_that(run_tune(args)).is_equal_to(1)

    def test_exception(self) -> None:
        args = _ns(cache_dir="data/c", weeks=4, trials=1, quiet=True, min_prob=0.0)
        with patch("slickbet.cli.tune", side_effect=RuntimeError("x")):
            assert_that(run_tune(args)).is_equal_to(1)


class TestRunScreener:
    def test_days(self, sample_screener_result: ScreenerResult) -> None:
        args = _ns(days=3, date=None, json=False, pdf=None)
        with patch("slickbet.cli.BettingScreener") as MockS:
            MockS.return_value.screen_days.return_value = sample_screener_result
            assert_that(run_screener(args)).is_equal_to(0)

    def test_specific_date(self, sample_screener_result: ScreenerResult) -> None:
        args = _ns(date="2025-06-15", days=1, json=False, pdf=None)
        with patch("slickbet.cli.BettingScreener") as MockS:
            MockS.return_value.screen_date.return_value = sample_screener_result
            assert_that(run_screener(args)).is_equal_to(0)

    def test_invalid_date(self) -> None:
        args = _ns(date="not-a-date")
        with patch("slickbet.cli.BettingScreener"):
            assert_that(run_screener(args)).is_equal_to(1)

    def test_days_zero_today(self, sample_screener_result: ScreenerResult) -> None:
        args = _ns(days=0, date=None, json=False, pdf=None)
        with patch("slickbet.cli.BettingScreener") as MockS:
            MockS.return_value.screen_date.return_value = sample_screener_result
            assert_that(run_screener(args)).is_equal_to(0)

    def test_json(
        self, sample_screener_result: ScreenerResult, capsys: pytest.CaptureFixture
    ) -> None:
        args = _ns(days=1, json=True, pdf=None)
        with patch("slickbet.cli.BettingScreener") as MockS:
            MockS.return_value.screen_days.return_value = sample_screener_result
            assert_that(run_screener(args)).is_equal_to(0)
            assert_that(capsys.readouterr().out).contains("predictions")

    def test_pdf(self, sample_screener_result: ScreenerResult, tmp_path: Path) -> None:
        out = str(tmp_path / "s.pdf")
        args = _ns(days=1, pdf=out, json=False)
        with (
            patch("slickbet.cli.BettingScreener") as MockS,
            patch("slickbet.cli.export_screener_to_pdf", return_value=out),
        ):
            MockS.return_value.screen_days.return_value = sample_screener_result
            assert_that(run_screener(args)).is_equal_to(0)

    def test_pdf_empty_flag(self, sample_screener_result: ScreenerResult) -> None:
        args = _ns(days=1, pdf="", json=False)
        with (
            patch("slickbet.cli.BettingScreener") as MockS,
            patch("slickbet.cli.export_screener_to_pdf", return_value="x.pdf"),
        ):
            MockS.return_value.screen_days.return_value = sample_screener_result
            assert_that(run_screener(args)).is_equal_to(0)

    def test_home_only(self, sample_screener_result: ScreenerResult) -> None:
        args = _ns(days=1, home_only=True, json=False, pdf=None)
        with patch("slickbet.cli.BettingScreener") as MockS:
            MockS.return_value.screen_days.return_value = sample_screener_result
            assert_that(run_screener(args)).is_equal_to(0)

    def test_away_only(self, sample_screener_result: ScreenerResult) -> None:
        args = _ns(days=1, away_only=True, json=False, pdf=None)
        with patch("slickbet.cli.BettingScreener") as MockS:
            MockS.return_value.screen_days.return_value = sample_screener_result
            assert_that(run_screener(args)).is_equal_to(0)

    def test_summary_only(self, sample_screener_result: ScreenerResult) -> None:
        args = _ns(days=1, summary_only=True, json=False, pdf=None)
        with patch("slickbet.cli.BettingScreener") as MockS:
            MockS.return_value.screen_days.return_value = sample_screener_result
            assert_that(run_screener(args)).is_equal_to(0)

    def test_no_predictions(self, sample_screener_result: ScreenerResult) -> None:
        empty = ScreenerResult(
            predictions=[],
            total_matches_scanned=5,
            matches_filtered=0,
            timestamp=datetime.now(),
        )
        args = _ns(days=1, json=False, pdf=None)
        with patch("slickbet.cli.BettingScreener") as MockS:
            MockS.return_value.screen_days.return_value = empty
            assert_that(run_screener(args)).is_equal_to(0)

    def test_pred_without_dc(
        self, sample_match: Match, sample_screener_result: ScreenerResult
    ) -> None:
        pred = BetPrediction(
            match=sample_match,
            recommended_outcome=BetOutcome.HOME_WIN,
            probability=0.7,
            confidence=0.4,
            form_score=0.2,
            position_score=0.3,
            home_advantage_score=0.1,
            h2h_score=0.1,
            double_chance=None,
            reasoning=[],
        )
        sample_screener_result.predictions = [pred]
        args = _ns(days=1, json=False, pdf=None)
        with patch("slickbet.cli.BettingScreener") as MockS:
            MockS.return_value.screen_days.return_value = sample_screener_result
            assert_that(run_screener(args)).is_equal_to(0)

    def test_unexpected_error(self) -> None:
        args = _ns(days=1)
        with patch("slickbet.cli.BettingScreener") as MockS:
            MockS.return_value.screen_days.side_effect = RuntimeError("x")
            assert_that(run_screener(args)).is_equal_to(1)

    def test_summary_home_away_empty(self, sample_screener_result: ScreenerResult) -> None:
        with patch("slickbet.cli.BettingScreener") as MockS:
            MockS.return_value.screen_days.return_value = sample_screener_result
            assert_that(run_screener(_ns(days=1, summary_only=True))).is_equal_to(0)
            assert_that(run_screener(_ns(days=1, home_only=True))).is_equal_to(0)
            assert_that(run_screener(_ns(days=1, away_only=True))).is_equal_to(0)
        empty = ScreenerResult(
            predictions=[],
            total_matches_scanned=0,
            matches_filtered=0,
            timestamp=datetime.now(),
        )
        with patch("slickbet.cli.BettingScreener") as MockS:
            MockS.return_value.screen_days.return_value = empty
            assert_that(run_screener(_ns(days=1))).is_equal_to(0)


class TestOutputHelpers:
    def test_output_json(
        self, sample_screener_result: ScreenerResult, sample_pred: BetPrediction, capsys
    ) -> None:
        output_json([sample_pred], sample_screener_result)
        assert_that(capsys.readouterr().out).contains("Home FC")

    def test_output_json_away(
        self, sample_match: Match, sample_screener_result: ScreenerResult, capsys
    ) -> None:
        pred = BetPrediction(
            match=sample_match,
            recommended_outcome=BetOutcome.AWAY_WIN,
            probability=0.6,
            confidence=0.3,
            form_score=0.0,
            position_score=0.0,
            home_advantage_score=0.0,
            h2h_score=0.0,
            double_chance=DoubleChancePrediction(0.4, 0.8, 0.7),
            reasoning=[],
        )
        output_json([pred], sample_screener_result)
        assert_that(capsys.readouterr().out).contains("away_win")

    def test_output_backtest_json(self, sample_backtest_results: BacktestResults, capsys) -> None:
        output_backtest_json(sample_backtest_results)
        assert_that(capsys.readouterr().out).contains("Premier League")


class TestRunDebug:
    def test_default_tomorrow(self) -> None:
        args = _ns(date=None)
        data = {
            "success": True,
            "data": {
                "fixtures": [
                    {
                        "id": "1",
                        "home": {"name": "A"},
                        "away": {"name": "B"},
                        "nested": {"x": 1},
                        "long": "x" * 80,
                    }
                ]
            },
        }
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.return_value._make_request.return_value = data
            assert_that(run_debug(args)).is_equal_to(0)

    def test_with_date_match_key(self) -> None:
        args = _ns(date="2025-06-15")
        data = {"data": {"match": [{"id": "1", "home": "A"}]}}
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.return_value._make_request.return_value = data
            assert_that(run_debug(args)).is_equal_to(0)

    def test_data_is_list(self) -> None:
        args = _ns(date="2025-06-15")
        data = {"data": [{"id": "1"}]}
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.return_value._make_request.return_value = data
            assert_that(run_debug(args)).is_equal_to(0)

    def test_empty_data(self) -> None:
        args = _ns(date=None)
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.return_value._make_request.return_value = {"other": True}
            assert_that(run_debug(args)).is_equal_to(0)

    def test_api_error(self) -> None:
        args = _ns(date=None)
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.side_effect = LivescoreAPIError("x")
            assert_that(run_debug(args)).is_equal_to(1)

    def test_unexpected_error(self) -> None:
        args = _ns(date=None)
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.side_effect = RuntimeError("x")
            assert_that(run_debug(args)).is_equal_to(1)

    def test_non_dict_sample(self) -> None:
        args = _ns(date="2025-06-15")
        data = {"data": {"fixtures": ["not-a-dict"]}}
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.return_value._make_request.return_value = data
            assert_that(run_debug(args)).is_equal_to(0)
