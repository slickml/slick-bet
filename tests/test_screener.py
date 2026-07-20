"""Tests for the betting screener."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from assertpy import assert_that

from slickbet.api import LivescoreAPIError, Match, Team, TeamPerformanceStats
from slickbet.model import BetOutcome, BetPrediction, BettingModel, DoubleChancePrediction
from slickbet.screener import (
    BettingScreener,
    ScreenerConfig,
    ScreenerResult,
    format_prediction,
    format_summary,
    get_best_double_chance_prob,
    to_central_time,
)


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def screener(mock_client: MagicMock) -> BettingScreener:
    return BettingScreener(
        config=ScreenerConfig(fetch_detailed_stats=False, min_probability=0.0, min_confidence=0.0),
        api_client=mock_client,
        model=BettingModel(),
    )


class TestScreenerConfig:
    def test_defaults(self) -> None:
        cfg = ScreenerConfig()
        assert_that(cfg.countries).is_equal_to([])
        assert_that(cfg.competitions).is_equal_to([])
        assert_that(cfg.competition_ids).is_equal_to([])
        assert_that(cfg.min_probability).is_equal_to(0.55)


class TestScreenerResult:
    def test_properties(self, sample_prediction: BetPrediction) -> None:
        away_pred = BetPrediction(
            match=sample_prediction.match,
            recommended_outcome=BetOutcome.AWAY_WIN,
            probability=0.6,
            confidence=0.2,
            form_score=0.0,
            position_score=0.0,
            home_advantage_score=0.0,
            h2h_score=0.0,
            double_chance=DoubleChancePrediction(0.5, 0.8, 0.6),
            reasoning=[],
        )
        result = ScreenerResult(
            predictions=[sample_prediction, away_pred],
            total_matches_scanned=10,
            matches_filtered=5,
            timestamp=datetime.now(timezone.utc),
        )
        assert_that(result.get_top_k(1)).is_length(1)
        assert_that(result.get_home_wins()).is_not_empty()
        assert_that(result.get_away_wins()).is_length(1)
        assert_that(result.top_bets_by_win).is_not_empty()


class TestHelpers:
    def test_get_best_dc_prob_with_dc(self, sample_prediction: BetPrediction) -> None:
        prob = get_best_double_chance_prob(sample_prediction)
        assert_that(prob).is_greater_than(0)

    def test_get_best_dc_prob_fallback(self, sample_match: Match) -> None:
        pred = BetPrediction(
            match=sample_match,
            recommended_outcome=BetOutcome.HOME_WIN,
            probability=0.66,
            confidence=0.3,
            form_score=0.0,
            position_score=0.0,
            home_advantage_score=0.0,
            h2h_score=0.0,
            double_chance=None,
            reasoning=[],
        )
        assert_that(get_best_double_chance_prob(pred)).is_equal_to(0.66)

    def test_to_central_time_naive(self) -> None:
        dt = datetime(2025, 6, 15, 18, 0, 0)
        central = to_central_time(dt)
        assert_that(central.tzinfo).is_not_none()

    def test_to_central_time_aware(self) -> None:
        dt = datetime(2025, 6, 15, 18, 0, 0, tzinfo=timezone.utc)
        central = to_central_time(dt)
        assert_that(str(central.tzinfo)).contains("Chicago")


class TestLeagueChecks:
    def test_major_league(self, screener: BettingScreener, sample_match: Match) -> None:
        assert_that(screener._is_major_league(sample_match)).is_true()

    def test_cup_by_id(self, screener: BettingScreener, home_team: Team, away_team: Team) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="Premier League",
            competition_id="152",
            country="England",
            kickoff_time=datetime.now(),
            status="NS",
        )
        assert_that(screener._is_cup_competition(match)).is_true()
        assert_that(screener._is_major_league(match)).is_false()

    def test_cup_by_name(self, screener: BettingScreener, home_team: Team, away_team: Team) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="FA Cup Round",
            competition_id="999",
            country="England",
            kickoff_time=datetime.now(),
            status="NS",
        )
        assert_that(screener._is_cup_competition(match)).is_true()

    def test_minor_asia_americas(
        self, screener: BettingScreener, home_team: Team, away_team: Team
    ) -> None:
        minor = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="Eredivisie",
            competition_id="196",
            country="Netherlands",
            kickoff_time=datetime.now(),
            status="NS",
        )
        asia = Match(
            id="2",
            home_team=home_team,
            away_team=away_team,
            competition="J. League",
            competition_id="28",
            country="Japan",
            kickoff_time=datetime.now(),
            status="NS",
        )
        americas = Match(
            id="3",
            home_team=home_team,
            away_team=away_team,
            competition="Liga MX",
            competition_id="45",
            country="Mexico",
            kickoff_time=datetime.now(),
            status="NS",
        )
        assert_that(screener._is_minor_league(minor)).is_true()
        assert_that(screener._is_asia_league(asia)).is_true()
        assert_that(screener._is_americas_league(americas)).is_true()


class TestApplyFilters:
    def _make_match(
        self,
        home_team: Team,
        away_team: Team,
        comp_id: str,
        country: str = "England",
        competition: str = "Premier League",
    ) -> Match:
        return Match(
            id=comp_id,
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            competition_id=comp_id,
            country=country,
            kickoff_time=datetime(2025, 6, 15, 15, 0),
            status="NS",
        )

    def test_major_only(self, mock_client: MagicMock, home_team: Team, away_team: Team) -> None:
        cfg = ScreenerConfig(major_leagues_only=True, fetch_detailed_stats=False)
        s = BettingScreener(config=cfg, api_client=mock_client)
        matches = [
            self._make_match(home_team, away_team, "2"),
            self._make_match(home_team, away_team, "99", competition="Other"),
        ]
        filtered = s._apply_filters(matches)
        assert_that(filtered).is_length(1)

    def test_major_only_empty(
        self, mock_client: MagicMock, home_team: Team, away_team: Team
    ) -> None:
        cfg = ScreenerConfig(major_leagues_only=True, fetch_detailed_stats=False)
        s = BettingScreener(config=cfg, api_client=mock_client)
        filtered = s._apply_filters([self._make_match(home_team, away_team, "99")])
        assert_that(filtered).is_empty()

    def test_asia_only(self, mock_client: MagicMock, home_team: Team, away_team: Team) -> None:
        cfg = ScreenerConfig(asia_leagues_only=True, fetch_detailed_stats=False)
        s = BettingScreener(config=cfg, api_client=mock_client)
        matches = [self._make_match(home_team, away_team, "28", "Japan", "J. League")]
        assert_that(s._apply_filters(matches)).is_length(1)
        assert_that(s._apply_filters([])).is_empty()

    def test_americas_only(self, mock_client: MagicMock, home_team: Team, away_team: Team) -> None:
        cfg = ScreenerConfig(americas_leagues_only=True, fetch_detailed_stats=False)
        s = BettingScreener(config=cfg, api_client=mock_client)
        matches = [self._make_match(home_team, away_team, "45", "Mexico", "Liga MX")]
        assert_that(s._apply_filters(matches)).is_length(1)
        assert_that(s._apply_filters([self._make_match(home_team, away_team, "99")])).is_empty()

    def test_all_leagues(self, mock_client: MagicMock, home_team: Team, away_team: Team) -> None:
        cfg = ScreenerConfig(all_leagues=True, fetch_detailed_stats=False)
        s = BettingScreener(config=cfg, api_client=mock_client)
        matches = [
            self._make_match(home_team, away_team, "2"),
            self._make_match(home_team, away_team, "196", "Netherlands", "Eredivisie"),
            self._make_match(home_team, away_team, "28", "Japan", "J. League"),
            self._make_match(home_team, away_team, "45", "Mexico", "Liga MX"),
            self._make_match(home_team, away_team, "999"),
        ]
        filtered = s._apply_filters(matches)
        assert_that(len(filtered)).is_equal_to(4)
        assert_that(s._apply_filters([self._make_match(home_team, away_team, "999")])).is_empty()

    def test_competition_ids_and_country(
        self, mock_client: MagicMock, home_team: Team, away_team: Team
    ) -> None:
        cfg = ScreenerConfig(
            competition_ids=["2"],
            countries=["England"],
            competitions=["Premier"],
            fetch_detailed_stats=False,
        )
        s = BettingScreener(config=cfg, api_client=mock_client)
        matches = [
            self._make_match(home_team, away_team, "2"),
            self._make_match(home_team, away_team, "3", "Spain", "La Liga"),
        ]
        filtered = s._apply_filters(matches)
        assert_that(filtered).is_length(1)


class TestScreening:
    def test_screen_matches(self, screener: BettingScreener, sample_match: Match) -> None:
        result = screener._screen_matches([sample_match])
        assert_that(result.total_matches_scanned).is_equal_to(1)
        assert_that(result.predictions).is_not_empty()

    def test_screen_drops_low_prob(self, mock_client: MagicMock, sample_match: Match) -> None:
        cfg = ScreenerConfig(fetch_detailed_stats=False, min_probability=0.99, min_confidence=0.0)
        s = BettingScreener(config=cfg, api_client=mock_client)
        result = s._screen_matches([sample_match])
        assert_that(result.predictions).is_empty()

    def test_screen_prediction_failure(self, mock_client: MagicMock, sample_match: Match) -> None:
        model = MagicMock()
        model.predict.side_effect = RuntimeError("fail")
        s = BettingScreener(
            config=ScreenerConfig(fetch_detailed_stats=False),
            api_client=mock_client,
            model=model,
        )
        result = s._screen_matches([sample_match])
        assert_that(result.predictions).is_empty()

    def test_screen_many_dropped(
        self, mock_client: MagicMock, home_team: Team, away_team: Team
    ) -> None:
        cfg = ScreenerConfig(fetch_detailed_stats=False, min_probability=0.99, min_confidence=0.99)
        s = BettingScreener(config=cfg, api_client=mock_client)
        matches = []
        for i in range(20):
            matches.append(
                Match(
                    id=str(i),
                    home_team=Team(id=str(i), name=f"H{i}"),
                    away_team=Team(id=str(i + 100), name=f"A{i}"),
                    competition="PL",
                    competition_id="2",
                    country="England",
                    kickoff_time=datetime(2025, 6, 15, 15, 0),
                    status="NS",
                )
            )
        result = s._screen_matches(matches)
        assert_that(result.predictions).is_empty()

    def test_enrich_matches(self, mock_client: MagicMock, sample_match: Match) -> None:
        mock_client.enrich_match_with_stats.return_value = sample_match
        s = BettingScreener(
            config=ScreenerConfig(fetch_detailed_stats=True, max_workers=2),
            api_client=mock_client,
        )
        enriched = s._enrich_matches([sample_match] * 10)
        assert_that(len(enriched)).is_equal_to(10)

    def test_enrich_api_error(self, mock_client: MagicMock, sample_match: Match) -> None:
        mock_client.enrich_match_with_stats.side_effect = LivescoreAPIError("fail")
        s = BettingScreener(
            config=ScreenerConfig(fetch_detailed_stats=True),
            api_client=mock_client,
        )
        enriched = s._enrich_matches([sample_match])
        assert_that(enriched[0]).is_equal_to(sample_match)

    def test_get_filtered_fixtures_paths(self, mock_client: MagicMock, sample_match: Match) -> None:
        # kickoff in Central on 2025-06-15: use UTC afternoon
        sample_match.kickoff_time = datetime(2025, 6, 15, 20, 0, 0)
        mock_client.get_fixtures_list.return_value = [sample_match]
        mock_client.get_fixtures_by_date.return_value = [sample_match]

        for kwargs in [
            {"competition_ids": ["2"]},
            {"major_leagues_only": True},
            {"asia_leagues_only": True},
            {"americas_leagues_only": True},
            {"all_leagues": True},
        ]:
            cfg = ScreenerConfig(fetch_detailed_stats=False, **kwargs)
            s = BettingScreener(config=cfg, api_client=mock_client)
            matches = s._get_filtered_fixtures(datetime(2025, 6, 15))
            assert_that(isinstance(matches, list)).is_true()

        # default path uses get_fixtures_by_date
        s = BettingScreener(
            config=ScreenerConfig(fetch_detailed_stats=False),
            api_client=mock_client,
        )
        s._get_filtered_fixtures(datetime(2025, 6, 15))
        mock_client.get_fixtures_by_date.assert_called()

    def test_screen_tomorrow_and_date(self, screener: BettingScreener, sample_match: Match) -> None:
        with patch.object(screener, "_get_filtered_fixtures", return_value=[sample_match]):
            r1 = screener.screen_tomorrow()
            r2 = screener.screen_date(datetime(2025, 6, 15))
        assert_that(r1.total_matches_scanned).is_equal_to(1)
        assert_that(r2.total_matches_scanned).is_equal_to(1)

    def test_screen_days(self, screener: BettingScreener, sample_match: Match) -> None:
        with patch.object(
            screener, "_get_filtered_fixtures", side_effect=[[sample_match], LivescoreAPIError("x")]
        ):
            result = screener.screen_days(days=2)
        assert_that(result.total_matches_scanned).is_equal_to(1)


class TestFormatPrediction:
    def test_format_home_win(self, sample_prediction: BetPrediction) -> None:
        text = format_prediction(sample_prediction, rank=1)
        assert_that(text).contains("BET RECOMMENDATION")
        assert_that(text).contains("DOUBLE CHANCE")

    def test_format_away_win_no_rank(self, sample_match: Match) -> None:
        pred = BetPrediction(
            match=sample_match,
            recommended_outcome=BetOutcome.AWAY_WIN,
            probability=0.55,
            confidence=0.1,
            form_score=0.1,
            position_score=0.1,
            home_advantage_score=0.1,
            h2h_score=0.1,
            odds_score=0.1,
            goal_score=0.1,
            venue_form_score=0.1,
            defense_score=0.1,
            momentum_score=0.1,
            match_stats_score=0.1,
            xg_score=0.1,
            draw_risk=0.35,
            double_chance=DoubleChancePrediction(0.4, 0.75, 0.6),
            reasoning=["Home form: WWW", "🎲 Best double chance: X2"],
        )
        text = format_prediction(pred, rank=0)
        assert_that(text).contains("DRAW RISK")
        assert_that(text).contains("X2")

    def test_format_dc_12(self, sample_match: Match) -> None:
        pred = BetPrediction(
            match=sample_match,
            recommended_outcome=BetOutcome.HOME_WIN,
            probability=0.7,
            confidence=0.4,
            form_score=0.0,
            position_score=0.0,
            home_advantage_score=0.0,
            h2h_score=0.0,
            double_chance=DoubleChancePrediction(0.5, 0.5, 0.9),
            reasoning=[],
        )
        text = format_prediction(pred, rank=2)
        assert_that(text).contains("12")

    def test_format_grades(self, sample_match: Match) -> None:
        for dc_prob, win_prob, grade_fragment in [
            (0.85, 0.70, "HIGH VALUE"),
            (0.76, 0.62, "GOOD BET"),
            (0.72, 0.50, "DECENT"),
            (0.60, 0.50, "RISKY"),
        ]:
            pred = BetPrediction(
                match=sample_match,
                recommended_outcome=BetOutcome.HOME_WIN,
                probability=win_prob,
                confidence=0.3,
                form_score=0.0,
                position_score=0.0,
                home_advantage_score=0.0,
                h2h_score=0.0,
                double_chance=DoubleChancePrediction(dc_prob, 0.3, 0.3),
                reasoning=[],
            )
            text = format_prediction(pred)
            assert_that(text).contains(grade_fragment)

    def test_format_stats_indicators(self, sample_match: Match, minimal_match: Match) -> None:
        # with stats
        pred = BettingModel().predict(sample_match)
        text = format_prediction(pred)
        assert_that(text).contains("Match Statistics")

        # no performance
        pred2 = BettingModel().predict(minimal_match)
        text2 = format_prediction(pred2)
        assert_that(text2).contains("Not available")

        # insufficient
        match = Match(
            id="1",
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
        pred3 = BettingModel().predict(match)
        text3 = format_prediction(pred3)
        assert_that(text3).contains("Not available")

        match2 = Match(
            id="2",
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
        pred4 = BettingModel().predict(match2)
        text4 = format_prediction(pred4)
        assert_that(text4).contains("Insufficient")

    def test_format_summary(self, sample_prediction: BetPrediction) -> None:
        result = ScreenerResult(
            predictions=[sample_prediction],
            total_matches_scanned=5,
            matches_filtered=3,
            timestamp=datetime.now(timezone.utc),
        )
        summary = format_summary(result)
        assert_that(summary).contains("SCREENING SUMMARY")
        assert_that(summary).contains("Actionable predictions")
