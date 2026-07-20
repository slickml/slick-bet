"""Tests for the Livescore API client and data classes."""

from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests
from assertpy import assert_that

from slickbet.api import (
    APIEndpoint,
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

# ---------------------------------------------------------------------------
# Data class tests
# ---------------------------------------------------------------------------


class TestOdds:
    def test_has_odds_true(self) -> None:
        assert_that(Odds(home_win=1.5).has_odds).is_true()

    def test_has_odds_false(self) -> None:
        assert_that(Odds().has_odds).is_false()

    def test_implied_probability(self) -> None:
        odds = Odds(home_win=2.0, draw=3.0, away_win=4.0)
        assert_that(odds.implied_probability("home")).is_close_to(0.5, 0.001)
        assert_that(odds.implied_probability("draw")).is_close_to(1 / 3, 0.001)
        assert_that(odds.implied_probability("away")).is_close_to(0.25, 0.001)

    def test_implied_probability_missing(self) -> None:
        odds = Odds()
        assert_that(odds.implied_probability("home")).is_none()
        assert_that(odds.implied_probability("unknown")).is_none()

    def test_implied_probability_zero(self) -> None:
        odds = Odds(home_win=0.0)
        assert_that(odds.implied_probability("home")).is_none()


class TestMatchScores:
    def test_parse_score(self) -> None:
        scores = MatchScores()
        assert_that(scores.parse_score("2 - 1")).is_equal_to((2, 1))
        assert_that(scores.parse_score("0-0")).is_equal_to((0, 0))

    def test_parse_score_invalid(self) -> None:
        scores = MatchScores()
        assert_that(scores.parse_score(None)).is_none()
        assert_that(scores.parse_score("")).is_none()
        assert_that(scores.parse_score("abc")).is_none()
        assert_that(scores.parse_score("1-2-3")).is_none()
        assert_that(scores.parse_score(123)).is_none()  # type: ignore[arg-type]

    def test_final_tuple(self) -> None:
        assert_that(MatchScores(final="3 - 1").final_tuple).is_equal_to((3, 1))
        assert_that(MatchScores(full_time="1 - 1").final_tuple).is_equal_to((1, 1))
        assert_that(MatchScores().final_tuple).is_none()


class TestMatchOutcome:
    def test_defaults(self) -> None:
        o = MatchOutcome()
        assert_that(o.full_time).is_none()


class TestHistoricalMatch:
    def test_scores_and_result(self, sample_historical_match: HistoricalMatch) -> None:
        assert_that(sample_historical_match.home_score).is_equal_to(2)
        assert_that(sample_historical_match.away_score).is_equal_to(1)
        assert_that(sample_historical_match.result).is_equal_to("H")

    def test_result_away(self, home_team: Team, away_team: Team) -> None:
        m = HistoricalMatch(
            id="1",
            fixture_id=None,
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            date=datetime.now(),
            status="FINISHED",
            scores=MatchScores(final="0 - 2"),
            outcomes=MatchOutcome(full_time="2"),
        )
        assert_that(m.result).is_equal_to("A")

    def test_result_draw(self, home_team: Team, away_team: Team) -> None:
        m = HistoricalMatch(
            id="1",
            fixture_id=None,
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            date=datetime.now(),
            status="FINISHED",
            scores=MatchScores(final="1 - 1"),
            outcomes=MatchOutcome(full_time="X"),
        )
        assert_that(m.result).is_equal_to("D")

    def test_result_unknown(self, home_team: Team, away_team: Team) -> None:
        m = HistoricalMatch(
            id="1",
            fixture_id=None,
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            date=datetime.now(),
            status="FINISHED",
            scores=MatchScores(),
            outcomes=MatchOutcome(full_time=None),
        )
        assert_that(m.result).is_none()
        assert_that(m.home_score).is_none()
        assert_that(m.away_score).is_none()


class TestMatchStatistics:
    def test_has_data(self, sample_match_statistics: MatchStatistics) -> None:
        assert_that(sample_match_statistics.has_data()).is_true()
        assert_that(MatchStatistics().has_data()).is_false()

    def test_parse_stat(self) -> None:
        assert_that(MatchStatistics.parse_stat("48:52")).is_equal_to((48, 52))
        assert_that(MatchStatistics.parse_stat(None)).is_none()
        assert_that(MatchStatistics.parse_stat("bad")).is_none()
        assert_that(MatchStatistics.parse_stat("1:2:3")).is_none()
        assert_that(MatchStatistics.parse_stat(1)).is_none()  # type: ignore[arg-type]

    def test_parse_float_stat(self) -> None:
        assert_that(MatchStatistics.parse_float_stat("1.5:0.8")).is_equal_to((1.5, 0.8))
        assert_that(MatchStatistics.parse_float_stat(None)).is_none()
        assert_that(MatchStatistics.parse_float_stat("x:y")).is_none()

    def test_calculate_xg_estimate_with_possession(self) -> None:
        xg = MatchStatistics.calculate_xg_estimate(5, 3, 40, 100, possession=60.0)
        assert_that(xg).is_greater_than(0)
        assert_that(xg).is_less_than_or_equal_to(4.0)

    def test_calculate_xg_estimate_no_possession(self) -> None:
        xg = MatchStatistics.calculate_xg_estimate(10, 10, 80, 150, possession=None)
        assert_that(xg).is_less_than_or_equal_to(4.0)

    def test_calculate_xg_capped(self) -> None:
        xg = MatchStatistics.calculate_xg_estimate(50, 50, 200, 500, possession=80.0)
        assert_that(xg).is_equal_to(4.0)


class TestTeamPerformanceStats:
    def test_defaults(self) -> None:
        s = TeamPerformanceStats(team_id="1")
        assert_that(s.matches_analyzed).is_equal_to(0)
        assert_that(s.reliability_score).is_equal_to(1.0)


# ---------------------------------------------------------------------------
# LivescoreClient tests
# ---------------------------------------------------------------------------


@pytest.fixture
def client(api_credentials: None) -> LivescoreClient:
    return LivescoreClient(api_key="test-key", api_secret="test-secret")


@pytest.fixture
def cached_client(api_credentials: None, tmp_cache_dir: Path) -> LivescoreClient:
    return LivescoreClient(
        api_key="test-key",
        api_secret="test-secret",
        cache_dir=tmp_cache_dir,
    )


def _mock_response(data: dict[str, Any], status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.raise_for_status = MagicMock()
    resp.json.return_value = data
    return resp


class TestLivescoreClientInit:
    def test_missing_credentials(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("LIVESCORE_API_KEY", raising=False)
        monkeypatch.delenv("LIVESCORE_API_SECRET", raising=False)
        with pytest.raises(LivescoreAPIError, match="credentials"):
            LivescoreClient()

    def test_cache_only_without_credentials(
        self, monkeypatch: pytest.MonkeyPatch, tmp_cache_dir: Path
    ) -> None:
        monkeypatch.delenv("LIVESCORE_API_KEY", raising=False)
        monkeypatch.delenv("LIVESCORE_API_SECRET", raising=False)
        c = LivescoreClient(cache_dir=tmp_cache_dir, cache_only=True)
        assert_that(c.cache_only).is_true()


class TestMakeRequest:
    def test_success(self, client: LivescoreClient) -> None:
        with patch.object(
            client.session, "get", return_value=_mock_response({"success": True, "data": {}})
        ) as mock_get:
            data = client._make_request(APIEndpoint.COUNTRIES_LIST)
            assert_that(data["success"]).is_true()
            mock_get.assert_called_once()

    def test_api_error_dict(self, client: LivescoreClient) -> None:
        body = {"success": False, "error": {"message": "Bad key"}}
        with patch.object(client.session, "get", return_value=_mock_response(body)):
            with pytest.raises(LivescoreAPIError, match="Bad key"):
                client._make_request("countries/list.json")

    def test_api_error_str(self, client: LivescoreClient) -> None:
        body = {"success": False, "error": "fail"}
        with patch.object(client.session, "get", return_value=_mock_response(body)):
            with pytest.raises(LivescoreAPIError, match="fail"):
                client._make_request("countries/list.json")

    def test_api_error_other(self, client: LivescoreClient) -> None:
        body = {"success": False, "error": 42}
        with patch.object(client.session, "get", return_value=_mock_response(body)):
            with pytest.raises(LivescoreAPIError, match="42"):
                client._make_request("countries/list.json")

    def test_request_exception(self, client: LivescoreClient) -> None:
        with patch.object(
            client.session, "get", side_effect=requests.exceptions.Timeout("timeout")
        ):
            with pytest.raises(LivescoreAPIError, match="Request failed"):
                client._make_request("countries/list.json")

    def test_cache_hit(self, cached_client: LivescoreClient) -> None:
        cached_client.cache.set("countries/list.json", None, {"success": True, "cached": True})
        with patch.object(cached_client.session, "get") as mock_get:
            data = cached_client._make_request("countries/list.json")
            assert_that(data["cached"]).is_true()
            mock_get.assert_not_called()

    def test_cache_miss_then_store(self, cached_client: LivescoreClient) -> None:
        with patch.object(
            cached_client.session,
            "get",
            return_value=_mock_response({"success": True, "data": {"ok": 1}}),
        ):
            data = cached_client._make_request("countries/list.json", params={"x": 1})
            assert_that(data["data"]["ok"]).is_equal_to(1)
        # second call hits cache
        with patch.object(cached_client.session, "get") as mock_get:
            data2 = cached_client._make_request("countries/list.json", params={"x": 1})
            assert_that(data2["data"]["ok"]).is_equal_to(1)
            mock_get.assert_not_called()

    def test_cache_only_miss(self, api_credentials: None, tmp_cache_dir: Path) -> None:
        c = LivescoreClient(api_key="k", api_secret="s", cache_dir=tmp_cache_dir, cache_only=True)
        with pytest.raises(LivescoreAPIError, match="Cache miss"):
            c._make_request("countries/list.json")


class TestSafeGetNested:
    def test_nested(self, client: LivescoreClient) -> None:
        assert_that(client._safe_get_nested({"a": {"b": 1}}, "a", "b")).is_equal_to(1)

    def test_non_dict_intermediate(self, client: LivescoreClient) -> None:
        assert_that(client._safe_get_nested({"a": "x"}, "a", "b", default=None)).is_none()


class TestGetFixtures:
    NESTED_FIXTURE = {
        "id": 100,
        "date": "2025-06-15",
        "time": "15:00:00",
        "status": "NS",
        "home": {"id": 1, "name": "Home FC"},
        "away": {"id": 2, "name": "Away Utd"},
        "country": {"name": "England"},
        "competition": {"id": 2, "name": "Premier League"},
        "odds": {"pre": {"1": 1.8, "X": 3.4, "2": 4.5}},
    }

    FLAT_FIXTURE = {
        "id": 200,
        "date": "2025-06-15",
        "time": "18:00",
        "status": "NS",
        "home_id": 3,
        "home_name": "Flat Home",
        "away_id": 4,
        "away_name": "Flat Away",
        "country_name": "Spain",
        "competition_name": "La Liga",
        "competition_id": 3,
        "odds_home": 2.0,
        "odds_draw": 3.0,
        "odds_away": 3.5,
        "home_score": 0,
        "away_score": 0,
    }

    def test_get_fixtures_by_date(self, client: LivescoreClient) -> None:
        page1 = {
            "success": True,
            "data": {
                "fixtures": [self.NESTED_FIXTURE, "bad", {"id": "x"}],  # bad entries skipped
                "next_page": True,
            },
        }
        page2 = {
            "success": True,
            "data": {"fixtures": [self.FLAT_FIXTURE], "next_page": False},
        }
        with patch.object(client, "_make_request", side_effect=[page1, page2]) as mock_req:
            matches = client.get_fixtures_by_date(datetime(2025, 6, 15), competition_id="2")
            assert_that(len(matches)).is_equal_to(3)
            assert_that(mock_req.call_count).is_equal_to(2)

    def test_get_fixtures_empty_then_data_list(self, client: LivescoreClient) -> None:
        resp = {"success": True, "data": [self.NESTED_FIXTURE]}
        with patch.object(client, "_make_request", return_value=resp):
            matches = client.get_fixtures_by_date(datetime(2025, 6, 15), fetch_all_pages=False)
            assert_that(len(matches)).is_equal_to(1)

    def test_get_fixtures_data_not_list(self, client: LivescoreClient) -> None:
        resp = {"success": True, "data": {"other": True}}
        with patch.object(client, "_make_request", return_value=resp):
            matches = client.get_fixtures_by_date(datetime(2025, 6, 15))
            assert_that(matches).is_empty()

    def test_get_tomorrow_fixtures(self, client: LivescoreClient) -> None:
        with patch.object(client, "get_fixtures_by_date", return_value=[]) as mock:
            client.get_tomorrow_fixtures()
            mock.assert_called_once()

    def test_get_fixtures_list(self, client: LivescoreClient) -> None:
        resp = {
            "success": True,
            "data": {"fixtures": [self.NESTED_FIXTURE], "next_page": False},
        }
        with patch.object(client, "_make_request", return_value=resp):
            matches = client.get_fixtures_list(
                date=datetime(2025, 6, 15),
                competition_ids=["1", "2"],
                country_id="1",
            )
            assert_that(len(matches)).is_equal_to(1)

    def test_get_fixtures_list_default_date(self, client: LivescoreClient) -> None:
        resp = {"success": True, "data": {"fixtures": [], "next_page": False}}
        with patch.object(client, "_make_request", return_value=resp):
            matches = client.get_fixtures_list()
            assert_that(matches).is_empty()

    def test_parse_fixture_bad_time(self, client: LivescoreClient) -> None:
        fixture = {
            "id": 1,
            "date": "bad",
            "time": "bad",
            "home_id": 1,
            "home_name": "H",
            "away_id": 2,
            "away_name": "A",
        }
        match = client._parse_fixture(fixture)
        assert_that(match.home_team.name).is_equal_to("H")

    def test_parse_fixture_non_dict_nested(self, client: LivescoreClient) -> None:
        fixture = {
            "id": 1,
            "date": "2025-01-01",
            "time": "12:00:00",
            "home": "not-dict",
            "away": "not-dict",
            "country": "x",
            "competition": "y",
            "odds": "z",
            "home_id": 1,
            "home_name": "H",
            "away_id": 2,
            "away_name": "A",
        }
        match = client._parse_fixture(fixture)
        assert_that(match.id).is_equal_to("1")


class TestCompetitionsCountriesStandings:
    def test_get_competitions(self, client: LivescoreClient) -> None:
        resp = {
            "success": True,
            "data": {
                "competition": [
                    {"id": 1, "name": "PL", "country_id": 1, "country_name": "England"},
                    "bad",
                ]
            },
        }
        with patch.object(client, "_make_request", return_value=resp):
            comps = client.get_competitions(country_id="1")
            assert_that(len(comps)).is_equal_to(1)

    def test_get_competitions_not_list(self, client: LivescoreClient) -> None:
        with patch.object(client, "_make_request", return_value={"data": {"competition": {}}}):
            assert_that(client.get_competitions()).is_empty()

    def test_get_countries(self, client: LivescoreClient) -> None:
        resp = {
            "success": True,
            "data": {"country": [{"id": 1, "name": "England"}, "bad"]},
        }
        with patch.object(client, "_make_request", return_value=resp):
            countries = client.get_countries()
            assert_that(len(countries)).is_equal_to(1)

    def test_get_countries_not_list(self, client: LivescoreClient) -> None:
        with patch.object(client, "_make_request", return_value={"data": {"country": {}}}):
            assert_that(client.get_countries()).is_empty()

    def test_get_team_standings(self, client: LivescoreClient) -> None:
        resp = {
            "success": True,
            "data": {
                "table": [
                    {"team_id": 1, "rank": 3},
                    {"team_id": 2, "rank": "bad"},
                    {"team_id": "", "rank": 1},
                    "bad",
                ]
            },
        }
        with patch.object(client, "_make_request", return_value=resp):
            standings = client.get_team_standings("2")
            assert_that(standings["1"]).is_equal_to(3)
            assert_that(standings["2"]).is_equal_to(0)

    def test_get_team_standings_not_list(self, client: LivescoreClient) -> None:
        with patch.object(client, "_make_request", return_value={"data": {"table": {}}}):
            assert_that(client.get_team_standings("2")).is_empty()


class TestTeamForm:
    def test_get_team_form(self, client: LivescoreClient) -> None:
        matches = [
            {"status": "FT", "ft_score": "2 - 1", "home_id": "1"},
            {"status": "FINISHED", "ft_score": "0 - 0", "home_id": "1"},
            {"status": "FT", "ft_score": "1 - 3", "home_id": "1"},
            {"status": "FT", "score": "0 - 2", "home_id": "99"},  # away
            {"status": "NS", "ft_score": "1 - 0", "home_id": "1"},  # skip
            {"status": "FT", "ft_score": "bad", "home_id": "1"},  # skip
            "not-dict",
            {"status": "AET", "home_score": 1, "away_score": 0, "home_id": "1"},
            {"status": "AP", "home_score": 0, "away_score": 1, "home_id": "99"},
            {"status": "FT", "home_score": 1, "away_score": 1, "home_id": "99"},
        ]
        resp = {"success": True, "data": {"match": matches}}
        with patch.object(client, "_make_request", return_value=resp):
            form = client.get_team_form("1", limit=5)
            assert_that(len(form)).is_less_than_or_equal_to(5)
            assert_that(form).contains("W")

    def test_get_team_form_data_list(self, client: LivescoreClient) -> None:
        resp = {
            "success": True,
            "data": [{"status": "FT", "ft_score": "1 - 0", "home_id": "1"}],
        }
        with patch.object(client, "_make_request", return_value=resp):
            form = client.get_team_form("1")
            assert_that(form).is_equal_to("W")

    def test_get_team_form_not_list(self, client: LivescoreClient) -> None:
        with patch.object(client, "_make_request", return_value={"data": {}}):
            assert_that(client.get_team_form("1")).is_equal_to("")


class TestTeamPerformanceStatsMethod:
    def _match(
        self,
        *,
        home_id: str = "1",
        ft: str = "2 - 1",
        status: str = "FT",
        mid: str = "m1",
        outcomes: dict | None = None,
    ) -> dict:
        return {
            "id": mid,
            "status": status,
            "ft_score": ft,
            "home_id": home_id,
            "outcomes": outcomes or {"half_time": "1"},
        }

    def test_performance_home_and_away(self, client: LivescoreClient) -> None:
        matches = [
            self._match(home_id="1", ft="3 - 0", mid="m1", outcomes={"half_time": "1"}),
            self._match(home_id="1", ft="1 - 1", mid="m2", outcomes={"half_time": "X"}),
            self._match(home_id="1", ft="0 - 2", mid="m3", outcomes={"half_time": "2"}),
            self._match(home_id="99", ft="0 - 2", mid="m4", outcomes={"half_time": "2"}),
            self._match(home_id="99", ft="1 - 1", mid="m5", outcomes={"half_time": "X"}),
            self._match(home_id="99", ft="2 - 0", mid="m6", outcomes={"half_time": "1"}),
            {"status": "NS", "ft_score": "1 - 0", "home_id": "1", "id": "skip"},
            "bad",
            {"status": "FT", "ft_score": "bad", "home_id": "1", "id": "badscore"},
        ]
        stats_obj = MatchStatistics(
            possession=(60, 40),
            corners=(5, 3),
            attacks=(100, 80),
            dangerous_attacks=(40, 20),
            shots_on_target=(6, 2),
            shots_off_target=(3, 4),
            saves=(1, 4),
            expected_goals=(1.5, 0.7),
            yellow_cards=(1, 2),
            red_cards=(0, 1),
        )
        with patch.object(client, "_make_request", return_value={"data": {"match": matches}}):
            with patch.object(client, "get_match_statistics", return_value=stats_obj):
                stats = client.get_team_performance_stats("1", num_matches=10, verbose=True)
        assert_that(stats.matches_analyzed).is_greater_than(0)
        assert_that(stats.matches_with_stats).is_greater_than(0)
        assert_that(stats.avg_possession).is_greater_than(0)

    def test_performance_api_error_on_stats(self, client: LivescoreClient) -> None:
        matches = [self._match(mid="m1")]
        with patch.object(client, "_make_request", return_value={"data": {"match": matches}}):
            with patch.object(
                client, "get_match_statistics", side_effect=LivescoreAPIError("no stats")
            ):
                stats = client.get_team_performance_stats("1", verbose=True)
        assert_that(stats.matches_analyzed).is_equal_to(1)
        assert_that(stats.matches_with_stats).is_equal_to(0)

    def test_performance_generic_error_on_stats(self, client: LivescoreClient) -> None:
        matches = [self._match(mid="m1")]
        with patch.object(client, "_make_request", return_value={"data": {"match": matches}}):
            with patch.object(client, "get_match_statistics", side_effect=RuntimeError("boom")):
                stats = client.get_team_performance_stats("1", verbose=True)
        assert_that(stats.matches_with_stats).is_equal_to(0)

    def test_performance_not_list(self, client: LivescoreClient) -> None:
        with patch.object(client, "_make_request", return_value={"data": {}}):
            stats = client.get_team_performance_stats("1")
            assert_that(stats.matches_analyzed).is_equal_to(0)

    def test_performance_data_list(self, client: LivescoreClient) -> None:
        with patch.object(
            client,
            "_make_request",
            return_value={"data": [self._match()]},
        ):
            with patch.object(client, "get_match_statistics", return_value=MatchStatistics()):
                stats = client.get_team_performance_stats("1")
        assert_that(stats.matches_analyzed).is_equal_to(1)

    def test_reliability_card_scales(self, client: LivescoreClient) -> None:
        """Cover reliability_score branches via matches_with_stats averages."""
        matches = [self._match(mid=f"m{i}") for i in range(3)]
        # high cards -> reliability 0
        high_cards = MatchStatistics(
            possession=(50, 50),
            yellow_cards=(5, 5),
            red_cards=(1, 1),
            attacks=(10, 10),
        )
        with patch.object(client, "_make_request", return_value={"data": {"match": matches}}):
            with patch.object(client, "get_match_statistics", return_value=high_cards):
                stats = client.get_team_performance_stats("1", num_matches=3)
        assert_that(stats.reliability_score).is_equal_to(0.0)

    def test_reliability_zero_cards(self, client: LivescoreClient) -> None:
        matches = [self._match(mid="m1")]
        zero = MatchStatistics(possession=(50, 50), yellow_cards=(0, 0), red_cards=(0, 0))
        with patch.object(client, "_make_request", return_value={"data": {"match": matches}}):
            with patch.object(client, "get_match_statistics", return_value=zero):
                stats = client.get_team_performance_stats("1", num_matches=1)
        assert_that(stats.reliability_score).is_equal_to(1.0)


class TestHeadToHead:
    def test_h2h(self, client: LivescoreClient) -> None:
        matches = [
            {"home_id": "1", "home_score": 2, "away_score": 0},
            {"home_id": "1", "home_score": 0, "away_score": 1},
            {"home_id": "2", "home_score": 1, "away_score": 0},  # away team was home
            {"home_id": "2", "home_score": 0, "away_score": 2},
            {"home_id": "1", "home_score": 1, "away_score": 1},
            {"home_id": "1", "home_score": "bad", "away_score": 0},
            "bad",
        ]
        resp = {"success": True, "data": {"matches": matches}}
        with patch.object(client, "_make_request", return_value=resp):
            h2h = client.get_head_to_head("1", "2", limit=10)
        assert_that(h2h["matches_played"]).is_greater_than(0)

    def test_h2h_empty(self, client: LivescoreClient) -> None:
        with patch.object(client, "_make_request", return_value={"data": []}):
            h2h = client.get_head_to_head("1", "2")
            assert_that(h2h["matches_played"]).is_equal_to(0)

    def test_h2h_matches_not_list(self, client: LivescoreClient) -> None:
        with patch.object(client, "_make_request", return_value={"data": {"matches": {}}}):
            h2h = client.get_head_to_head("1", "2")
            assert_that(h2h["matches_played"]).is_equal_to(0)


class TestMatchStatisticsFetch:
    def test_with_api_xg(self, client: LivescoreClient) -> None:
        resp = {
            "data": {
                "possesion": "55:45",
                "shots_on_target": "5:3",
                "shots_off_target": "4:4",
                "corners": "6:3",
                "fauls": "10:12",
                "yellow_cards": "2:1",
                "red_cards": "0:0",
                "offsides": "1:2",
                "saves": "2:4",
                "attacks": "100:80",
                "dangerous_attacks": "40:30",
                "expected_goals": "1.5:0.8",
            }
        }
        with patch.object(client, "_make_request", return_value=resp):
            stats = client.get_match_statistics("123")
        assert_that(stats.expected_goals).is_equal_to((1.5, 0.8))
        assert_that(stats.possession).is_equal_to((55, 45))

    def test_calculated_xg(self, client: LivescoreClient) -> None:
        resp = {
            "data": {
                "possesion": "60:40",
                "shots_on_target": "5:2",
                "shots_off_target": "3:4",
                "attacks": "110:90",
                "dangerous_attacks": "45:25",
            }
        }
        with patch.object(client, "_make_request", return_value=resp):
            stats = client.get_match_statistics("123")
        assert_that(stats.expected_goals).is_not_none()

    def test_no_stats_data(self, client: LivescoreClient) -> None:
        with patch.object(client, "_make_request", return_value={"data": []}):
            stats = client.get_match_statistics("123")
            assert_that(stats.has_data()).is_false()


class TestHistory:
    HIST_MATCH = {
        "id": 50,
        "fixture_id": 60,
        "date": "2025-01-10",
        "status": "FINISHED",
        "home": {"id": 1, "name": "Home"},
        "away": {"id": 2, "name": "Away"},
        "country": {"name": "England"},
        "competition": {"id": 2, "name": "PL"},
        "scores": {"score": "2 - 1", "ht_score": "1 - 0", "ft_score": "2 - 1"},
        "outcomes": {"half_time": "1", "full_time": "1"},
        "odds": {"pre": {"1": 1.8, "X": 3.4, "2": 4.5}},
        "location": "Stadium",
        "round": "20",
    }

    def test_get_history(self, client: LivescoreClient) -> None:
        resp = {"data": {"match": [self.HIST_MATCH, "bad", {"id": None}]}}
        with patch.object(client, "_make_request", return_value=resp):
            matches = client.get_history(
                competition_id="2",
                team_id="1",
                from_date=datetime(2025, 1, 1),
                to_date=datetime(2025, 1, 31),
            )
        assert_that(len(matches)).is_greater_than_or_equal_to(1)

    def test_get_history_not_list(self, client: LivescoreClient) -> None:
        with patch.object(client, "_make_request", return_value={"data": {"match": {}}}):
            assert_that(client.get_history()).is_empty()

    def test_parse_historical_bad_date(self, client: LivescoreClient) -> None:
        data = {
            **self.HIST_MATCH,
            "date": "bad",
            "home": "x",
            "away": "y",
            "country": "z",
            "competition": "c",
            "scores": "s",
            "outcomes": "o",
            "odds": "odds",
        }
        m = client._parse_historical_match(data)
        assert_that(m.home_team.name).is_equal_to("Unknown")

    def test_parse_historical_empty_odds(self, client: LivescoreClient) -> None:
        data = {**self.HIST_MATCH, "odds": {"pre": {}}}
        m = client._parse_historical_match(data)
        assert_that(m.pre_odds).is_none()

    def test_get_team_history(self, client: LivescoreClient) -> None:
        hist = client._parse_historical_match(self.HIST_MATCH)
        with patch.object(client, "get_history", side_effect=[[hist], []]):
            matches = client.get_team_history("1", limit=5)
            assert_that(len(matches)).is_equal_to(1)

    def test_get_team_history_api_error(self, client: LivescoreClient) -> None:
        with patch.object(client, "get_history", side_effect=LivescoreAPIError("fail")):
            assert_that(client.get_team_history("1")).is_empty()


class TestEnrichMatch:
    def test_enrich_success(self, client: LivescoreClient, sample_match: Match) -> None:
        with patch.object(client, "get_team_form", return_value="WWDLW"):
            with patch.object(client, "get_team_standings", return_value={"1": 1, "2": 18}):
                with patch.object(client, "get_head_to_head", return_value={"matches_played": 1}):
                    with patch.object(
                        client,
                        "get_team_performance_stats",
                        return_value=TeamPerformanceStats(team_id="1"),
                    ):
                        enriched = client.enrich_match_with_stats(sample_match)
        assert_that(enriched.home_form).is_equal_to("WWDLW")
        assert_that(enriched.home_position).is_equal_to(1)

    def test_enrich_cup_mapping(
        self, client: LivescoreClient, home_team: Team, away_team: Team
    ) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="FA Cup",
            competition_id="152",
            country="England",
            kickoff_time=datetime.now(),
            status="NS",
        )
        with patch.object(client, "get_team_form", return_value="W"):
            with patch.object(client, "get_team_standings", return_value={"1": 5}) as mock_st:
                with patch.object(client, "get_head_to_head", return_value={}):
                    with patch.object(
                        client,
                        "get_team_performance_stats",
                        return_value=TeamPerformanceStats(team_id="1"),
                    ):
                        client.enrich_match_with_stats(match)
            # FA Cup maps to Premier League (2)
            mock_st.assert_called_with("2")

    def test_enrich_missing_ids(self, client: LivescoreClient) -> None:
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
        result = client.enrich_match_with_stats(match)
        assert_that(result.home_form).is_none()

    def test_enrich_exceptions_swallowed(
        self, client: LivescoreClient, sample_match: Match
    ) -> None:
        with patch.object(client, "get_team_form", side_effect=Exception("fail")):
            with patch.object(client, "get_team_standings", side_effect=Exception("fail")):
                with patch.object(client, "get_head_to_head", side_effect=Exception("fail")):
                    with patch.object(
                        client, "get_team_performance_stats", side_effect=Exception("fail")
                    ):
                        result = client.enrich_match_with_stats(sample_match)
        assert_that(result.id).is_equal_to(sample_match.id)
