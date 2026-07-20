"""Targeted tests to close remaining coverage gaps."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from assertpy import assert_that

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
from slickbet.backtest import Backtester, BacktestResults, PredictionResult, format_backtest_report
from slickbet.model import BetOutcome, BetPrediction, BettingModel, DoubleChancePrediction
from slickbet.screener import BettingScreener, ScreenerConfig, format_prediction


@pytest.fixture
def client(api_credentials: None) -> LivescoreClient:
    return LivescoreClient(api_key="k", api_secret="s")


class TestApiGaps:
    def test_parse_score_value_error(self) -> None:
        scores = MatchScores()
        assert_that(scores.parse_score("a-b")).is_none()
        assert_that(scores.parse_score("1-")).is_none()

    def test_parse_stat_value_error(self) -> None:
        assert_that(MatchStatistics.parse_stat("a:b")).is_none()
        assert_that(MatchStatistics.parse_float_stat("a:b")).is_none()

    def test_fixtures_list_malformed_and_pagination(self, client: LivescoreClient) -> None:
        good = {
            "id": 1,
            "date": "2025-06-15",
            "time": "15:00:00",
            "home_id": 1,
            "home_name": "H",
            "away_id": 2,
            "away_name": "A",
        }
        page1 = {
            "success": True,
            "data": {
                "fixtures": [good, "bad", {"id": object()}],
                "next_page": True,
            },
        }
        page2 = {"success": True, "data": {"fixtures": [good], "next_page": False}}
        with patch.object(client, "_make_request", side_effect=[page1, page2]):
            with patch.object(
                client,
                "_parse_fixture",
                side_effect=[
                    Match(
                        id="1",
                        home_team=Team(id="1", name="H"),
                        away_team=Team(id="2", name="A"),
                        competition="PL",
                        competition_id="2",
                        country="E",
                        kickoff_time=datetime.now(),
                        status="NS",
                    ),
                    KeyError("bad"),
                    Match(
                        id="2",
                        home_team=Team(id="1", name="H"),
                        away_team=Team(id="2", name="A"),
                        competition="PL",
                        competition_id="2",
                        country="E",
                        kickoff_time=datetime.now(),
                        status="NS",
                    ),
                ],
            ):
                matches = client.get_fixtures_list(date=datetime(2025, 6, 15))
        assert_that(len(matches)).is_greater_than_or_equal_to(1)

    def test_team_form_away_results(self, client: LivescoreClient) -> None:
        matches = [
            {"status": "FT", "ft_score": "2 - 0", "home_id": "99"},  # away loss
            {"status": "FT", "ft_score": "1 - 1", "home_id": "99"},  # away draw
            {"status": "FT", "ft_score": "0 - 3", "home_id": "99"},  # away win
            {"status": "FT", "ft_score": "1 - ", "home_id": "1"},  # IndexError/ValueError
        ]
        with patch.object(client, "_make_request", return_value={"data": {"match": matches}}):
            form = client.get_team_form("1", limit=5)
        assert_that("L" in form or "D" in form or "W" in form).is_true()

    def test_performance_comebacks_collapses(self, client: LivescoreClient) -> None:
        matches = [
            # home: trailing at HT (2), didn't lose -> comeback
            {
                "id": "m1",
                "status": "FT",
                "ft_score": "2 - 1",
                "home_id": "1",
                "outcomes": {"half_time": "2"},
            },
            # home: leading at HT (1), drew -> collapse
            {
                "id": "m2",
                "status": "FT",
                "ft_score": "1 - 1",
                "home_id": "1",
                "outcomes": {"half_time": "1"},
            },
            # away: trailing at HT (1), didn't lose -> comeback
            {
                "id": "m3",
                "status": "FT",
                "ft_score": "1 - 1",
                "home_id": "99",
                "outcomes": {"half_time": "1"},
            },
            # away: leading at HT (2), lost -> collapse
            {
                "id": "m4",
                "status": "FT",
                "ft_score": "2 - 0",
                "home_id": "99",
                "outcomes": {"half_time": "2"},
            },
            # score parse error
            {
                "id": "m5",
                "status": "FT",
                "ft_score": "1 - ",
                "home_id": "1",
                "outcomes": {},
            },
        ]
        with patch.object(client, "_make_request", return_value={"data": {"match": matches}}):
            with patch.object(client, "get_match_statistics", return_value=MatchStatistics()):
                stats = client.get_team_performance_stats("1", num_matches=10)
        assert_that(stats.comebacks).is_greater_than(0)
        assert_that(stats.collapses).is_greater_than(0)

    def test_history_parse_skip(self, client: LivescoreClient) -> None:
        with patch.object(
            client,
            "_make_request",
            return_value={"data": {"match": [{"id": 1}]}},
        ):
            with patch.object(client, "_parse_historical_match", side_effect=ValueError("bad")):
                assert_that(client.get_history()).is_empty()

    def test_parse_historical_empty_odds_no_has(self, client: LivescoreClient) -> None:
        data = {
            "id": 1,
            "date": "2025-01-01",
            "home": {"id": 1, "name": "H"},
            "away": {"id": 2, "name": "A"},
            "country": {},
            "competition": {"id": 2, "name": "PL"},
            "scores": {},
            "outcomes": {},
            "odds": {"pre": {"1": None, "X": None, "2": None}},
        }
        m = client._parse_historical_match(data)
        assert_that(m.pre_odds).is_none()

    def test_parse_fixture_non_dict_pre_odds(self, client: LivescoreClient) -> None:
        fixture = {
            "id": 1,
            "date": "2025-01-01",
            "time": "12:00:00",
            "home_id": 1,
            "home_name": "H",
            "away_id": 2,
            "away_name": "A",
            "odds": {"pre": "not-a-dict"},
        }
        match = client._parse_fixture(fixture)
        assert_that(match.pre_odds).is_none()

    def test_xg_estimate_possession_branches(self) -> None:
        # high possession and no possession already covered; hit off-target possession branch
        xg = MatchStatistics.calculate_xg_estimate(0, 20, 0, 0, possession=80.0)
        assert_that(xg).is_greater_than(0)

    def test_fixtures_by_date_parse_error(self, client: LivescoreClient) -> None:
        resp = {
            "success": True,
            "data": {
                "fixtures": [{"id": 1}],
                "next_page": False,
            },
        }
        with patch.object(client, "_make_request", return_value=resp):
            with patch.object(client, "_parse_fixture", side_effect=ValueError("bad")):
                matches = client.get_fixtures_by_date(datetime(2025, 6, 15))
        assert_that(matches).is_empty()

    def test_team_form_non_dict_first(self, client: LivescoreClient) -> None:
        matches = [
            "not-a-dict",
            {"status": "FT", "ft_score": "1 - 0", "home_id": "1"},
        ]
        with patch.object(client, "_make_request", return_value={"data": {"match": matches}}):
            form = client.get_team_form("1", limit=5)
        assert_that(form).is_equal_to("W")

    def test_performance_away_full_stats(self, client: LivescoreClient) -> None:
        """Cover away-side accumulation of all match statistic fields."""
        matches = [
            {
                "id": "m1",
                "status": "FT",
                "ft_score": "1 - 2",
                "home_id": "99",
                "outcomes": {"half_time": "X"},
            }
        ]
        stats_obj = MatchStatistics(
            possession=(40, 60),
            corners=(2, 7),
            attacks=(80, 120),
            dangerous_attacks=(20, 50),
            shots_on_target=(2, 6),
            shots_off_target=(3, 4),
            saves=(5, 1),
            expected_goals=(0.8, 1.9),
            yellow_cards=(3, 1),
            red_cards=(1, 0),
        )
        with patch.object(client, "_make_request", return_value={"data": {"match": matches}}):
            with patch.object(client, "get_match_statistics", return_value=stats_obj):
                stats = client.get_team_performance_stats("1", num_matches=5, verbose=False)
        assert_that(stats.matches_with_stats).is_equal_to(1)
        assert_that(stats.avg_possession).is_greater_than(0)

    def test_performance_away_ht_unknown(self, client: LivescoreClient) -> None:
        """Away side with unrecognized HT outcome skips ht_wins/losses/draws."""
        matches = [
            {
                "id": "m1",
                "status": "FT",
                "ft_score": "1 - 2",
                "home_id": "99",
                "outcomes": {"half_time": "", "full_time": "2"},
            }
        ]
        with patch.object(client, "_make_request", return_value={"data": {"match": matches}}):
            with patch.object(
                client, "get_match_statistics", side_effect=LivescoreAPIError("no stats")
            ):
                stats = client.get_team_performance_stats("1", num_matches=5, verbose=False)
        assert_that(stats.matches_analyzed).is_equal_to(1)
        assert_that(stats.ht_draws).is_equal_to(0)

    def test_performance_partial_stats_home(self, client: LivescoreClient) -> None:
        """Home stats with only some fields present (branch partials)."""
        matches = [
            {
                "id": "m1",
                "status": "FT",
                "ft_score": "2 - 0",
                "home_id": "1",
                "outcomes": {"half_time": "1"},
            }
        ]
        # Only possession and yellow — no attacks/shots etc.
        stats_obj = MatchStatistics(
            possession=(55, 45),
            yellow_cards=(1, 2),
        )
        with patch.object(client, "_make_request", return_value={"data": {"match": matches}}):
            with patch.object(client, "get_match_statistics", return_value=stats_obj):
                stats = client.get_team_performance_stats("1", num_matches=1)
        assert_that(stats.matches_with_stats).is_equal_to(1)

    def test_h2h_swapped_home(self, client: LivescoreClient) -> None:
        matches = [
            {"home_id": "2", "home_score": 2, "away_score": 0},  # away was home, won
            {"home_id": "2", "home_score": 0, "away_score": 1},  # away was home, lost
        ]
        with patch.object(client, "_make_request", return_value={"data": {"matches": matches}}):
            h2h = client.get_head_to_head("1", "2")
        assert_that(h2h["matches_played"]).is_equal_to(2)

    def test_parse_stat_wrong_arity(self) -> None:
        assert_that(MatchStatistics.parse_stat("1:2:3")).is_none()
        assert_that(MatchStatistics.parse_float_stat("1:2:3")).is_none()

    def test_fixtures_max_pages(self, client: LivescoreClient) -> None:
        good = {
            "id": 1,
            "date": "2025-06-15",
            "time": "15:00:00",
            "home_id": 1,
            "home_name": "H",
            "away_id": 2,
            "away_name": "A",
        }
        pages = [
            {"success": True, "data": {"fixtures": [good], "next_page": True}} for _ in range(12)
        ]
        with patch.object(client, "_make_request", side_effect=pages):
            matches = client.get_fixtures_by_date(datetime(2025, 6, 15))
        assert_that(len(matches)).is_equal_to(10)  # max_pages=10

    def test_fixtures_list_data_not_list_fallback(self, client: LivescoreClient) -> None:
        # empty fixtures key path → data is dict → not list → []
        with patch.object(
            client,
            "_make_request",
            return_value={"success": True, "data": {"foo": 1}},
        ):
            assert_that(client.get_fixtures_list(date=datetime(2025, 6, 15))).is_empty()

        # no fixtures key; data is a list → fallback list path (810→813)
        good = {
            "id": 1,
            "date": "2025-06-15",
            "time": "15:00:00",
            "home_id": 1,
            "home_name": "H",
            "away_id": 2,
            "away_name": "A",
        }
        with patch.object(
            client,
            "_make_request",
            return_value={"success": True, "data": [good]},
        ):
            matches = client.get_fixtures_list(date=datetime(2025, 6, 15))
        assert_that(matches).is_not_empty()

    def test_fixtures_list_max_pages(self, client: LivescoreClient) -> None:
        good = {
            "id": 1,
            "date": "2025-06-15",
            "time": "15:00:00",
            "home_id": 1,
            "home_name": "H",
            "away_id": 2,
            "away_name": "A",
        }
        pages = [
            {"success": True, "data": {"fixtures": [good], "next_page": True}} for _ in range(12)
        ]
        with patch.object(client, "_make_request", side_effect=pages):
            matches = client.get_fixtures_list(date=datetime(2025, 6, 15))
        assert_that(len(matches)).is_equal_to(10)

    def test_performance_edge_branches(self, client: LivescoreClient) -> None:
        matches = [
            # non-dict outcomes, empty id
            {
                "id": "",
                "status": "FT",
                "ft_score": "1 - 0",
                "home_id": "1",
                "outcomes": "not-dict",
            },
            # home with partial stats (no possession/corners)
            {
                "id": "m2",
                "status": "FT",
                "ft_score": "2 - 1",
                "home_id": "1",
                "outcomes": {"half_time": "X"},
            },
            # away with partial stats
            {
                "id": "m3",
                "status": "FT",
                "ft_score": "0 - 1",
                "home_id": "99",
                "outcomes": {"half_time": "X"},
            },
        ]
        partial = MatchStatistics(
            attacks=(10, 20),
            # no possession, corners, etc.
        )
        with patch.object(client, "_make_request", return_value={"data": {"match": matches}}):
            with patch.object(client, "get_match_statistics", return_value=partial):
                stats = client.get_team_performance_stats("1", num_matches=10)
        assert_that(stats.matches_analyzed).is_greater_than(0)

    def test_performance_no_finished(self, client: LivescoreClient) -> None:
        matches = [{"status": "NS", "ft_score": "0 - 0", "home_id": "1", "id": "m1"}]
        with patch.object(client, "_make_request", return_value={"data": {"match": matches}}):
            stats = client.get_team_performance_stats("1")
        assert_that(stats.matches_analyzed).is_equal_to(0)

    def test_performance_mid_reliability_and_shot_accuracy(self, client: LivescoreClient) -> None:
        matches = [
            {
                "id": "m1",
                "status": "FT",
                "ft_score": "1 - 0",
                "home_id": "1",
                "outcomes": {"half_time": "1"},
            }
        ]
        # mid cards for linear reliability; shots for accuracy
        mid = MatchStatistics(
            possession=(50, 50),
            shots_on_target=(4, 2),
            shots_off_target=(6, 3),
            yellow_cards=(2, 2),
            red_cards=(0, 0),
            attacks=(50, 50),
        )
        with patch.object(client, "_make_request", return_value={"data": {"match": matches}}):
            with patch.object(client, "get_match_statistics", return_value=mid):
                stats = client.get_team_performance_stats("1", num_matches=1)
        assert_that(0.0 < stats.reliability_score < 1.0).is_true()
        assert_that(stats.shot_accuracy).is_greater_than(0)

    def test_team_history_max_pages(self, client: LivescoreClient) -> None:
        hist = HistoricalMatch(
            id="1",
            fixture_id=None,
            home_team=Team(id="1", name="H"),
            away_team=Team(id="2", name="A"),
            competition="PL",
            competition_id="2",
            country="E",
            date=datetime.now(),
            status="FINISHED",
            scores=MatchScores(final="1 - 0"),
            outcomes=MatchOutcome(full_time="1"),
        )
        # Always return matches so while exits on page limit
        with patch.object(client, "get_history", return_value=[hist] * 30):
            matches = client.get_team_history("1", limit=5)
        assert_that(len(matches)).is_equal_to(5)

    def test_enrich_no_comp_id_and_non_dict_standings(
        self, client: LivescoreClient, home_team: Team, away_team: Team
    ) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
        )
        with patch.object(client, "get_team_form", return_value="W"):
            with patch.object(client, "get_team_standings", return_value=["not", "dict"]):
                with patch.object(client, "get_head_to_head", return_value={}):
                    with patch.object(
                        client,
                        "get_team_performance_stats",
                        return_value=TeamPerformanceStats(team_id="1"),
                    ):
                        result = client.enrich_match_with_stats(match)
        assert_that(result.home_form).is_equal_to("W")

    def test_xg_no_possession(self) -> None:
        xg = MatchStatistics.calculate_xg_estimate(5, 5, 10, 50, possession=None)
        assert_that(xg).is_greater_than(0)

    def test_fixtures_list_data_is_list(self, client: LivescoreClient) -> None:
        fixture = {
            "id": 1,
            "date": "2025-06-15",
            "time": "15:00:00",
            "home_id": 1,
            "home_name": "H",
            "away_id": 2,
            "away_name": "A",
        }
        # No fixtures key; data itself is a list
        with patch.object(
            client,
            "_make_request",
            return_value={"success": True, "data": [fixture]},
        ):
            matches = client.get_fixtures_list(date=datetime(2025, 6, 15))
        assert_that(len(matches)).is_equal_to(1)

    def test_performance_remaining_branches(self, client: LivescoreClient) -> None:
        matches = [
            # away HT draw
            {
                "id": "m1",
                "status": "FT",
                "ft_score": "1 - 1",
                "home_id": "99",
                "outcomes": {"half_time": "X"},
            },
            # home with xG length-1 tuple (no away xGA)
            {
                "id": "m2",
                "status": "FT",
                "ft_score": "1 - 0",
                "home_id": "1",
                "outcomes": {"half_time": "1"},
            },
            # away without attacks
            {
                "id": "m3",
                "status": "FT",
                "ft_score": "0 - 2",
                "home_id": "99",
                "outcomes": {"half_time": "2"},
            },
        ]

        def stats_for(mid: str) -> MatchStatistics:
            if mid == "m2":
                return MatchStatistics(
                    possession=(50, 50),
                    expected_goals=(1.5,),  # type: ignore[arg-type]
                    yellow_cards=(1, 1),
                )
            if mid == "m3":
                return MatchStatistics(
                    possession=(40, 60),
                    shots_on_target=(1, 5),
                    # no attacks
                )
            return MatchStatistics(possession=(50, 50), attacks=(10, 10))

        with patch.object(client, "_make_request", return_value={"data": {"match": matches}}):
            with patch.object(
                client,
                "get_match_statistics",
                side_effect=lambda mid: stats_for(mid),
            ):
                # silent API error + silent generic error
                stats = client.get_team_performance_stats("1", num_matches=10, verbose=False)

        with patch.object(client, "_make_request", return_value={"data": {"match": [matches[1]]}}):
            with patch.object(client, "get_match_statistics", side_effect=LivescoreAPIError("x")):
                client.get_team_performance_stats("1", num_matches=1, verbose=False)
            with patch.object(client, "get_match_statistics", side_effect=RuntimeError("x")):
                client.get_team_performance_stats("1", num_matches=1, verbose=False)

        assert_that(stats.matches_analyzed).is_greater_than(0)

    def test_away_ht_unknown_outcome(self, client: LivescoreClient) -> None:
        """Away match with HT outcome not in {1,2,X}."""
        matches = [
            {
                "id": "m1",
                "status": "FT",
                "ft_score": "0 - 1",
                "home_id": "99",
                "outcomes": {"half_time": ""},
            }
        ]
        with patch.object(client, "_make_request", return_value={"data": {"match": matches}}):
            with patch.object(client, "get_match_statistics", return_value=MatchStatistics()):
                stats = client.get_team_performance_stats("1", num_matches=1)
        assert_that(stats.ht_draws).is_equal_to(0)
        assert_that(stats.ht_wins).is_equal_to(0)

    def test_enrich_non_dict_standings_with_comp(
        self, client: LivescoreClient, home_team: Team, away_team: Team
    ) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
        )
        with patch.object(client, "get_team_form", return_value="W"):
            with patch.object(client, "get_team_standings", return_value="nope"):
                with patch.object(client, "get_head_to_head", return_value={}):
                    with patch.object(
                        client,
                        "get_team_performance_stats",
                        return_value=TeamPerformanceStats(team_id="1"),
                    ):
                        client.enrich_match_with_stats(match)
        assert_that(match.home_position).is_none()


class TestModelGaps:
    def test_odds_infinite_total_zero(
        self, model: BettingModel, home_team: Team, away_team: Team
    ) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            pre_odds=Odds(home_win=float("inf"), draw=3.0, away_win=float("inf")),
        )
        score, _ = model._calculate_odds_score(match)
        assert_that(score).is_equal_to(0.0)

    def test_form_empty_string_points(
        self, model: BettingModel, home_team: Team, away_team: Team
    ) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            home_form="",
            away_form="W",
        )
        score, _ = model._calculate_form_score(match)
        assert_that(score).is_less_than_or_equal_to(0)

    def test_reliability_home_more(
        self, model: BettingModel, home_team: Team, away_team: Team
    ) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            home_performance=TeamPerformanceStats(
                team_id="1", matches_with_stats=5, reliability_score=0.95, avg_cards=0.2
            ),
            away_performance=TeamPerformanceStats(
                team_id="2", matches_with_stats=0, reliability_score=0.5, avg_cards=2.0
            ),
        )
        score, reasons = model._calculate_reliability_score(match)
        assert_that(score).is_greater_than(0.15)
        assert_that(any("Home team more reliable" in r for r in reasons)).is_true()


# Import model helpers used below - keep within TestModelGaps by extending file
class TestModelBranchGaps:
    def test_low_draw_risk_no_warning(
        self, model: BettingModel, home_team: Team, away_team: Team
    ) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            home_form="WWWWW",
            away_form="LLLLL",
            home_position=1,
            away_position=20,
        )
        model.DRAW_RISK_THRESHOLD = 0.99
        pred = model.predict(match)
        assert_that(any("High draw risk" in r for r in pred.reasoning)).is_false()

    def test_xg_neutral_score(self, model: BettingModel, home_team: Team, away_team: Team) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            home_performance=TeamPerformanceStats(
                team_id="1", avg_expected_goals=1.0, avg_expected_goal_difference=0.0
            ),
            away_performance=TeamPerformanceStats(
                team_id="2", avg_expected_goals=1.0, avg_expected_goal_difference=0.0
            ),
        )
        score, reasons = model._calculate_xg_score(match)
        assert_that(abs(score)).is_less_than_or_equal_to(0.15)
        assert_that(any("higher quality" in r for r in reasons)).is_false()

    def test_draw_odds_zero(self, model: BettingModel, home_team: Team, away_team: Team) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            pre_odds=Odds(home_win=2.0, draw=-1.0, away_win=2.0),
        )
        risk = model._calculate_draw_risk(0.0, 0.0, 0.0, match)
        assert_that(risk).is_between(0.15, 0.55)


class TestScreenerGaps:
    def test_screen_with_enrichment(self, sample_match: Match) -> None:
        client = MagicMock()
        client.enrich_match_with_stats.return_value = sample_match
        s = BettingScreener(
            config=ScreenerConfig(
                fetch_detailed_stats=True,
                min_probability=0.0,
                min_confidence=0.0,
                max_workers=2,
            ),
            api_client=client,
        )
        result = s._screen_matches([sample_match])
        assert_that(result.predictions).is_not_empty()
        client.enrich_match_with_stats.assert_called()

    def test_cup_exclusions(self, home_team: Team, away_team: Team) -> None:
        s = BettingScreener(
            config=ScreenerConfig(fetch_detailed_stats=False),
            api_client=MagicMock(),
        )
        cup = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="Cup",
            competition_id="152",
            country="England",
            kickoff_time=datetime.now(),
            status="NS",
        )
        assert_that(s._is_minor_league(cup)).is_false()
        assert_that(s._is_americas_league(cup)).is_false()
        assert_that(s._is_asia_league(cup)).is_false()

    def test_format_stats_unused_branch(self, sample_match: Match) -> None:
        """Force match_stats_used False while both sides report stats >= 1."""
        pred = BettingModel().predict(sample_match)
        with patch.object(type(pred), "match_stats_used", property(lambda self: False)):
            text = format_prediction(pred)
        assert_that(text).contains("but score is 0")

    def test_screen_drop_low_conf_only(self, sample_match: Match) -> None:
        """Hit confidence-only drop branch (prob ok, conf low)."""
        client = MagicMock()
        model = MagicMock()
        model.predict.return_value = BetPrediction(
            match=sample_match,
            recommended_outcome=BetOutcome.HOME_WIN,
            probability=0.90,
            confidence=0.01,
            form_score=0.0,
            position_score=0.0,
            home_advantage_score=0.0,
            h2h_score=0.0,
            reasoning=[],
        )
        s = BettingScreener(
            config=ScreenerConfig(
                fetch_detailed_stats=False,
                min_probability=0.55,
                min_confidence=0.5,
            ),
            api_client=client,
            model=model,
        )
        result = s._screen_matches([sample_match])
        assert_that(result.predictions).is_empty()


class TestBacktestGaps:
    def test_run_defaults_and_away_and_progress(
        self, sample_historical_match: HistoricalMatch, api_credentials: None
    ) -> None:
        client = MagicMock()
        now = datetime.now()
        matches = []
        for i in range(12):
            matches.append(
                HistoricalMatch(
                    id=str(i),
                    fixture_id=None,
                    home_team=Team(id="1", name="H"),
                    away_team=Team(id="2", name="A"),
                    competition="PL",
                    competition_id="2",
                    country="England",
                    date=now - __import__("datetime").timedelta(days=i),
                    status="FINISHED",
                    scores=MatchScores(final="0 - 1" if i % 2 else "2 - 0"),
                    outcomes=MatchOutcome(full_time="2" if i % 2 else "1"),
                )
            )
        client.get_history.side_effect = [matches, []]
        client.get_team_form.return_value = "LLLLL"
        client.get_team_standings.return_value = {"1": 20, "2": 1}
        client.get_head_to_head.return_value = {
            "matches_played": 5,
            "home_wins": 0,
            "away_wins": 5,
            "draws": 0,
        }
        client.get_team_performance_stats.return_value = TeamPerformanceStats(team_id="1")

        bt = Backtester(client=client, model=BettingModel())
        results = bt.run(competition_id="2", weeks=4, verbose=True, debug=False)
        assert_that(results.total_predictions).is_greater_than(0)

    def test_country_flag_partial(self) -> None:
        bt = Backtester(client=MagicMock())
        assert_that(bt._get_country_flag("West Germany Region")).is_equal_to("🇩🇪")

    def test_report_threshold_skip(self) -> None:
        """Threshold filter with zero predictions at high thresholds."""
        home = Team(id="1", name="H")
        away = Team(id="2", name="A")
        hist = HistoricalMatch(
            id="1",
            fixture_id=None,
            home_team=home,
            away_team=away,
            competition="PL",
            competition_id="2",
            country=None,
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
            kickoff_time=datetime.now(),
            status="NS",
        )
        pred = BetPrediction(
            match=match,
            recommended_outcome=BetOutcome.HOME_WIN,
            probability=0.56,
            confidence=0.1,
            form_score=0.0,
            position_score=0.0,
            home_advantage_score=0.0,
            h2h_score=0.0,
            double_chance=None,
            reasoning=[],
        )
        pr = PredictionResult(
            match=hist,
            prediction=pred,
            actual_outcome="H",
            predicted_outcome="H",
            is_correct=True,
            probability=0.56,
            confidence=0.1,
        )
        report = format_backtest_report(
            BacktestResults(
                results=[pr],
                competition="2",
                from_date=None,
                to_date=None,
            )
        )
        assert_that(report).contains("OVERALL")

    def test_enrich_verbose_no_stats(self) -> None:
        client = MagicMock()
        client.get_team_form.return_value = "W"
        client.get_team_standings.return_value = {"1": 1}
        client.get_head_to_head.return_value = {}
        client.get_team_performance_stats.return_value = TeamPerformanceStats(
            team_id="1", matches_with_stats=0
        )
        bt = Backtester(client=client)
        match = Match(
            id="1",
            home_team=Team(id="1", name="H"),
            away_team=Team(id="2", name="A"),
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
        )
        bt._enrich_for_backtest(match, datetime.now(), verbose=True)

    def test_print_debug_no_dc_no_reasons(self, capsys: pytest.CaptureFixture[str]) -> None:
        bt = Backtester(client=MagicMock())
        home = Team(id="1", name="H")
        away = Team(id="2", name="A")
        hist = HistoricalMatch(
            id="1",
            fixture_id=None,
            home_team=home,
            away_team=away,
            competition="PL",
            competition_id="2",
            country="Unknownland",
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
            kickoff_time=datetime.now(),
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
            double_chance=None,
            reasoning=[],
        )
        result = PredictionResult(
            match=hist,
            prediction=pred,
            actual_outcome="H",
            predicted_outcome="H",
            is_correct=True,
            probability=0.7,
            confidence=0.4,
        )
        bt._print_debug_match(result)
        assert_that(capsys.readouterr().out).contains("ACTUAL")

    def test_enrich_partial_ids(self) -> None:
        client = MagicMock()
        client.get_team_form.return_value = "W"
        client.get_team_standings.return_value = "not-dict"
        client.get_head_to_head.return_value = {}
        client.get_team_performance_stats.return_value = TeamPerformanceStats(team_id="1")
        bt = Backtester(client=client)
        # only home id
        match = Match(
            id="1",
            home_team=Team(id="1", name="H"),
            away_team=Team(id="", name="A"),
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
        )
        # missing away -> returns early
        assert_that(bt._enrich_for_backtest(match, datetime.now()).away_form).is_none()

        match2 = Match(
            id="2",
            home_team=Team(id="1", name="H"),
            away_team=Team(id="2", name="A"),
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
        )
        client.get_team_standings.return_value = "not-dict"
        bt._enrich_for_backtest(match2, datetime.now(), verbose=False)

        # both IDs present, empty competition_id -> skip standings block
        match3 = Match(
            id="3",
            home_team=Team(id="1", name="H"),
            away_team=Team(id="2", name="A"),
            competition="PL",
            competition_id="",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
        )
        bt._enrich_for_backtest(match3, datetime.now(), verbose=False)

        # Empty competition_id skips standings block entirely (601 -> 610)
        match3 = Match(
            id="3",
            home_team=Team(id="1", name="H"),
            away_team=Team(id="2", name="A"),
            competition="PL",
            competition_id="",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
        )
        bt._enrich_for_backtest(match3, datetime.now(), verbose=False)

    def test_fetch_max_pages_and_quiet_error(self) -> None:
        client = MagicMock()
        hist = HistoricalMatch(
            id="1",
            fixture_id=None,
            home_team=Team(id="1", name="H"),
            away_team=Team(id="2", name="A"),
            competition="PL",
            competition_id="2",
            country="E",
            date=datetime(2025, 1, 15),
            status="FINISHED",
            scores=MatchScores(final="1 - 0"),
            outcomes=MatchOutcome(full_time="1"),
        )
        client.get_history.side_effect = [[hist]] * 25
        bt = Backtester(client=client)
        matches = bt._fetch_all_history(
            "2", datetime(2025, 1, 1), datetime(2025, 1, 31), verbose=False
        )
        assert_that(len(matches)).is_equal_to(20)

        client.get_history.side_effect = LivescoreAPIError("x")
        assert_that(
            bt._fetch_all_history("2", datetime(2025, 1, 1), datetime(2025, 1, 31), verbose=False)
        ).is_empty()

    def test_run_exception_quiet(self) -> None:
        client = MagicMock()
        hist = HistoricalMatch(
            id="1",
            fixture_id=None,
            home_team=Team(id="1", name="H"),
            away_team=Team(id="2", name="A"),
            competition="PL",
            competition_id="2",
            country="E",
            date=datetime(2025, 1, 15),
            status="FINISHED",
            scores=MatchScores(final="1 - 0"),
            outcomes=MatchOutcome(full_time="1"),
        )
        client.get_history.side_effect = [[hist], []]
        bt = Backtester(client=client)
        with patch.object(bt, "_enrich_for_backtest", side_effect=RuntimeError("x")):
            results = bt.run(
                competition_id="2",
                from_date=datetime(2025, 1, 1),
                to_date=datetime(2025, 1, 31),
                verbose=False,
            )
        assert_that(results.total_predictions).is_equal_to(0)


class TestCliGaps:
    def test_screener_api_error_on_construct(self) -> None:
        from argparse import Namespace

        from slickbet.cli import run_screener

        args = Namespace(
            min_prob=0.55,
            min_conf=0.1,
            no_stats=True,
            workers=2,
            country=None,
            competition=None,
            league=None,
            major_only=False,
            asia_only=False,
            americas_only=False,
            all_leagues=False,
            date=None,
            days=1,
            home_only=False,
            away_only=False,
            summary_only=False,
            json=False,
            pdf=None,
            top=5,
        )
        with patch("slickbet.cli.BettingScreener", side_effect=LivescoreAPIError("no key")):
            assert_that(run_screener(args)).is_equal_to(1)

    def test_debug_dead_list_branch(self) -> None:
        """Cover the unreachable-looking elif list branch via patched structure."""
        from argparse import Namespace

        from slickbet.cli import run_debug

        args = Namespace(date="2025-06-15")
        # The elif isinstance(data_section, list) is nested under dict check — unreachable.
        # Cover nearby: fixtures non-list type print path
        data = {"data": {"fixtures": {"not": "list"}, "match": None}}
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.return_value._make_request.return_value = data
            assert_that(run_debug(args)).is_equal_to(0)

    def test_main_module(self) -> None:
        import runpy
        import sys

        with patch.object(sys, "argv", ["slickbet", "--help"]):
            with pytest.raises(SystemExit) as exc:
                runpy.run_module("slickbet.cli", run_name="__main__")
            assert_that(exc.value.code).is_in(0, 2)  # help exits 0 or argparse may use 0

    def test_competitions_same_country_twice(self) -> None:
        from argparse import Namespace

        from slickbet.cli import run_competitions

        args = Namespace(country=None, search=None)
        comps = [
            {"id": "1", "name": "A", "country_name": "England"},
            {"id": "2", "name": "B", "country_name": "England"},
        ]
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.return_value.get_competitions.return_value = comps
            assert_that(run_competitions(args)).is_equal_to(0)

    def test_debug_non_dict_top(self) -> None:
        from argparse import Namespace

        from slickbet.cli import run_debug

        args = Namespace(date="2025-06-15")
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.return_value._make_request.return_value = ["not", "dict"]
            assert_that(run_debug(args)).is_equal_to(0)

    def test_debug_empty_list_and_no_fixture_keys(self) -> None:
        from argparse import Namespace

        from slickbet.cli import run_debug

        args = Namespace(date="2025-06-15")
        with patch("slickbet.cli.LivescoreClient") as MockClient:
            MockClient.return_value._make_request.return_value = {"data": []}
            assert_that(run_debug(args)).is_equal_to(0)
            MockClient.return_value._make_request.return_value = {"data": {"other": 1}}
            assert_that(run_debug(args)).is_equal_to(0)


class TestPdfGaps:
    def test_export_all_score_branches(self, sample_match: Match, tmp_path: Path) -> None:
        from datetime import timezone

        from slickbet.pdf_export import export_screener_to_pdf
        from slickbet.screener import ScreenerResult

        preds = []
        # HIGH VALUE
        preds.append(
            BetPrediction(
                match=sample_match,
                recommended_outcome=BetOutcome.HOME_WIN,
                probability=0.70,
                confidence=0.5,
                form_score=0.2,
                position_score=0.2,
                home_advantage_score=0.1,
                h2h_score=0.1,
                odds_score=0.1,
                goal_score=0.1,
                venue_form_score=0.1,
                defense_score=0.1,
                momentum_score=0.1,
                match_stats_score=0.1,
                xg_score=0.1,
                double_chance=DoubleChancePrediction(0.85, 0.3, 0.4),
                reasoning=["🔥 insight"],
            )
        )
        # X2 best
        preds.append(
            BetPrediction(
                match=sample_match,
                recommended_outcome=BetOutcome.AWAY_WIN,
                probability=0.62,
                confidence=0.3,
                form_score=0.0,
                position_score=0.0,
                home_advantage_score=0.0,
                h2h_score=0.0,
                double_chance=DoubleChancePrediction(0.3, 0.78, 0.4),
                reasoning=[],
            )
        )
        # 12 best + insufficient stats path in PDF
        m = Match(
            id="x",
            home_team=sample_match.home_team,
            away_team=sample_match.away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            home_position=1,
            away_position=2,
            home_performance=TeamPerformanceStats(team_id="1", matches_with_stats=0),
            away_performance=TeamPerformanceStats(team_id="2", matches_with_stats=2),
        )
        preds.append(
            BetPrediction(
                match=m,
                recommended_outcome=BetOutcome.HOME_WIN,
                probability=0.55,
                confidence=0.2,
                form_score=0.0,
                position_score=0.0,
                home_advantage_score=0.0,
                h2h_score=0.0,
                double_chance=DoubleChancePrediction(0.4, 0.4, 0.8),
                reasoning=[],
            )
        )
        result = ScreenerResult(
            predictions=preds,
            total_matches_scanned=3,
            matches_filtered=3,
            timestamp=datetime.now(timezone.utc),
        )
        path = export_screener_to_pdf(result, preds, str(tmp_path / "gaps.pdf"))
        assert_that(Path(path).exists()).is_true()

    def test_export_no_dc_and_stats_used(self, sample_match: Match, tmp_path: Path) -> None:
        from datetime import timezone

        from slickbet.pdf_export import export_screener_to_pdf
        from slickbet.screener import ScreenerResult

        pred = BettingModel().predict(sample_match)
        pred.double_chance = None
        # both have stats >= 1 and match_stats_used True — skip insufficient branch
        result = ScreenerResult(
            predictions=[pred],
            total_matches_scanned=1,
            matches_filtered=1,
            timestamp=datetime.now(timezone.utc),
        )
        path = export_screener_to_pdf(result, [pred], str(tmp_path / "nodc.pdf"))
        assert_that(Path(path).exists()).is_true()

        # both stats >= 1 but match_stats_used False -> elif home_stats < 1 false path
        pred2 = BettingModel().predict(sample_match)
        with patch.object(type(pred2), "match_stats_used", property(lambda self: False)):
            path2 = export_screener_to_pdf(result, [pred2], str(tmp_path / "forced.pdf"))
        assert_that(Path(path2).exists()).is_true()


class TestTuneBranches:
    def test_quiet_exception_and_none(self, tmp_cache_dir: Path) -> None:
        from slickbet.tune import tune

        with patch("slickbet.tune.run_backtest_with_weights", side_effect=RuntimeError("x")):
            assert_that(tune(cache_dir=tmp_cache_dir, trials=1, verbose=False)).is_none()
        with patch("slickbet.tune.run_backtest_with_weights", return_value=None):
            assert_that(tune(cache_dir=tmp_cache_dir, trials=1, verbose=False)).is_none()
