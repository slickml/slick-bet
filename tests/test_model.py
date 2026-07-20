"""Tests for the betting model."""

from datetime import datetime

from assertpy import assert_that

from slickbet.api import Match, Odds, Team, TeamPerformanceStats
from slickbet.model import (
    BetOutcome,
    BetPrediction,
    BettingModel,
    DoubleChancePrediction,
)


class TestBetOutcome:
    """Test cases for BetOutcome enum."""

    def test_outcome_values(self) -> None:
        assert_that(BetOutcome.HOME_WIN.value).is_equal_to("home_win")
        assert_that(BetOutcome.AWAY_WIN.value).is_equal_to("away_win")
        assert_that(BetOutcome.DRAW.value).is_equal_to("draw")
        assert_that(BetOutcome.HOME_OR_DRAW.value).is_equal_to("home_or_draw")
        assert_that(BetOutcome.AWAY_OR_DRAW.value).is_equal_to("away_or_draw")
        assert_that(BetOutcome.HOME_OR_AWAY.value).is_equal_to("home_or_away")

    def test_all_outcomes_exist(self) -> None:
        assert_that(list(BetOutcome)).is_length(6)
        assert_that([o.value for o in BetOutcome]).contains(
            "home_win", "away_win", "draw", "home_or_draw", "away_or_draw", "home_or_away"
        )


class TestDoubleChancePrediction:
    """Tests for DoubleChancePrediction."""

    def test_best_double_chance_1x(self) -> None:
        dc = DoubleChancePrediction(
            home_or_draw_prob=0.80, away_or_draw_prob=0.40, no_draw_prob=0.60
        )
        best, prob = dc.best_double_chance
        assert_that(best).contains("1X")
        assert_that(prob).is_equal_to(0.80)

    def test_best_double_chance_x2(self) -> None:
        dc = DoubleChancePrediction(
            home_or_draw_prob=0.40, away_or_draw_prob=0.85, no_draw_prob=0.50
        )
        best, prob = dc.best_double_chance
        assert_that(best).contains("X2")
        assert_that(prob).is_equal_to(0.85)

    def test_best_double_chance_12(self) -> None:
        dc = DoubleChancePrediction(
            home_or_draw_prob=0.50, away_or_draw_prob=0.50, no_draw_prob=0.90
        )
        best, prob = dc.best_double_chance
        assert_that(best).contains("12")
        assert_that(prob).is_equal_to(0.90)


class TestBetPredictionProperties:
    """Tests for BetPrediction properties."""

    def test_expected_value(self, sample_match: Match) -> None:
        pred = BetPrediction(
            match=sample_match,
            recommended_outcome=BetOutcome.HOME_WIN,
            probability=0.75,
            confidence=0.5,
            form_score=0.3,
            position_score=0.4,
            home_advantage_score=0.2,
            h2h_score=0.1,
            reasoning=[],
        )
        # EV = 0.75 - 0.25 = 0.5
        assert_that(pred.expected_value).is_close_to(0.5, 0.001)

    def test_match_stats_used_true(self, sample_match: Match) -> None:
        pred = BetPrediction(
            match=sample_match,
            recommended_outcome=BetOutcome.HOME_WIN,
            probability=0.7,
            confidence=0.4,
            form_score=0.0,
            position_score=0.0,
            home_advantage_score=0.0,
            h2h_score=0.0,
            reasoning=[],
        )
        assert_that(pred.match_stats_used).is_true()

    def test_match_stats_used_no_performance(self, minimal_match: Match) -> None:
        pred = BetPrediction(
            match=minimal_match,
            recommended_outcome=BetOutcome.HOME_WIN,
            probability=0.5,
            confidence=0.1,
            form_score=0.0,
            position_score=0.0,
            home_advantage_score=0.0,
            h2h_score=0.0,
            reasoning=[],
        )
        assert_that(pred.match_stats_used).is_false()

    def test_match_stats_used_insufficient(self, home_team: Team, away_team: Team) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="England",
            kickoff_time=datetime.now(),
            status="NS",
            home_performance=TeamPerformanceStats(team_id="1", matches_with_stats=0),
            away_performance=TeamPerformanceStats(team_id="2", matches_with_stats=3),
        )
        pred = BetPrediction(
            match=match,
            recommended_outcome=BetOutcome.HOME_WIN,
            probability=0.5,
            confidence=0.1,
            form_score=0.0,
            position_score=0.0,
            home_advantage_score=0.0,
            h2h_score=0.0,
            reasoning=[],
        )
        assert_that(pred.match_stats_used).is_false()


class TestBettingModel:
    """Test cases for BettingModel."""

    def test_predict_returns_prediction(self, model: BettingModel, sample_match: Match) -> None:
        prediction = model.predict(sample_match)
        assert_that(prediction).is_not_none()
        assert_that(prediction.match).is_equal_to(sample_match)
        assert_that(prediction.probability).is_between(0.0, 1.0)
        assert_that(prediction.confidence).is_between(0.0, 1.0)
        assert_that(prediction.double_chance).is_not_none()

    def test_predict_favors_stronger_team(self, model: BettingModel, sample_match: Match) -> None:
        prediction = model.predict(sample_match)
        assert_that(prediction.recommended_outcome).is_equal_to(BetOutcome.HOME_WIN)
        assert_that(prediction.probability).is_greater_than(0.5)

    def test_predict_with_no_stats(self, model: BettingModel, minimal_match: Match) -> None:
        prediction = model.predict(minimal_match)
        assert_that(prediction).is_not_none()
        assert_that(prediction.probability).is_greater_than_or_equal_to(0.5)

    def test_form_score_calculation(self, model: BettingModel, sample_match: Match) -> None:
        prediction = model.predict(sample_match)
        assert_that(prediction.form_score).is_greater_than(0)

    def test_position_score_calculation(self, model: BettingModel, sample_match: Match) -> None:
        prediction = model.predict(sample_match)
        assert_that(prediction.position_score).is_greater_than(0)

    def test_reasoning_is_populated(self, model: BettingModel, sample_match: Match) -> None:
        prediction = model.predict(sample_match)
        assert_that(prediction.reasoning).is_not_empty()
        assert_that(any("form" in r.lower() for r in prediction.reasoning)).is_true()

    def test_custom_weights(self) -> None:
        model = BettingModel(
            form_weight=0.5,
            position_weight=0.1,
            home_weight=0.1,
            h2h_weight=0.05,
            odds_weight=0.05,
            goals_weight=0.05,
            venue_form_weight=0.05,
            defense_weight=0.05,
            momentum_weight=0.025,
            match_stats_weight=0.025,
            xg_weight=0.0,
            reliability_weight=0.0,
            min_confidence=0.6,
        )
        total = sum(model.weights.values())
        assert_that(total).is_close_to(1.0, 0.001)
        assert_that(model.min_confidence).is_equal_to(0.6)

    def test_filter_confident_predictions(
        self, model: BettingModel, sample_match: Match, minimal_match: Match
    ) -> None:
        preds = [model.predict(sample_match), model.predict(minimal_match)]
        filtered = model.filter_confident_predictions(preds, min_confidence=0.99)
        assert_that(filtered).is_empty()
        filtered_low = model.filter_confident_predictions(preds, min_confidence=0.0)
        assert_that(filtered_low).is_length(2)
        # default threshold
        filtered_default = model.filter_confident_predictions(preds)
        assert_that(len(filtered_default)).is_less_than_or_equal_to(2)

    def test_score_to_probability_edge_cases(self, model: BettingModel) -> None:
        assert_that(model._score_to_probability(0.0)).is_close_to(0.5, 0.01)
        high = model._score_to_probability(10.0)
        low = model._score_to_probability(-10.0)
        assert_that(high).is_less_than_or_equal_to(0.75)
        assert_that(low).is_greater_than_or_equal_to(0.25)
        assert_that(high).is_greater_than(low)

    def test_away_favored_prediction(
        self, model: BettingModel, home_team: Team, away_team: Team
    ) -> None:
        match = Match(
            id="away",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="England",
            kickoff_time=datetime.now(),
            status="NS",
            home_form="LLLLL",
            away_form="WWWWW",
            home_position=20,
            away_position=1,
            pre_odds=Odds(home_win=5.0, draw=3.5, away_win=1.5),
            head_to_head={
                "matches_played": 5,
                "home_wins": 0,
                "away_wins": 5,
                "draws": 0,
            },
        )
        pred = model.predict(match)
        assert_that(pred.recommended_outcome).is_equal_to(BetOutcome.AWAY_WIN)

    def test_high_draw_risk_reasoning(
        self, model: BettingModel, home_team: Team, away_team: Team
    ) -> None:
        match = Match(
            id="draw",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="England",
            kickoff_time=datetime.now(),
            status="NS",
            home_form="DWDWD",
            away_form="DWDWD",
            home_position=10,
            away_position=10,
            pre_odds=Odds(home_win=2.5, draw=2.8, away_win=2.6),
        )
        pred = model.predict(match)
        assert_that(pred.draw_risk).is_greater_than(0)


class TestScoreCalculators:
    """Unit tests for individual score calculation methods."""

    def test_form_no_data(self, model: BettingModel, minimal_match: Match) -> None:
        score, reasons = model._calculate_form_score(minimal_match)
        assert_that(score).is_equal_to(0.0)
        assert_that(reasons[0]).contains("No form")

    def test_form_only_home(self, model: BettingModel, home_team: Team, away_team: Team) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            home_form="WWW",
        )
        score, reasons = model._calculate_form_score(match)
        assert_that(score).is_greater_than(0)
        assert_that(any("Home form" in r for r in reasons)).is_true()

    def test_form_only_away_better(
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
            home_form="LLL",
            away_form="WWW",
        )
        score, reasons = model._calculate_form_score(match)
        assert_that(score).is_less_than(-0.2)
        assert_that(any("Away team in significantly better form" in r for r in reasons)).is_true()

    def test_position_none(self, model: BettingModel, minimal_match: Match) -> None:
        score, reasons = model._calculate_position_score(minimal_match)
        assert_that(score).is_equal_to(0.0)
        assert_that(reasons[0]).contains("No standings")

    def test_position_invalid(self, model: BettingModel, home_team: Team, away_team: Team) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            home_position="bad",  # type: ignore[arg-type]
            away_position="worse",  # type: ignore[arg-type]
        )
        score, reasons = model._calculate_position_score(match)
        assert_that(score).is_equal_to(0.0)
        assert_that(reasons[0]).contains("Invalid")

    def test_position_same(self, model: BettingModel, home_team: Team, away_team: Team) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            home_position=5,
            away_position=5,
        )
        score, reasons = model._calculate_position_score(match)
        assert_that(score).is_equal_to(0.0)
        assert_that(any("same position" in r for r in reasons)).is_true()

    def test_position_away_higher(
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
            home_position=15,
            away_position=3,
        )
        score, reasons = model._calculate_position_score(match)
        assert_that(score).is_less_than(0)
        assert_that(any("Away team" in r for r in reasons)).is_true()

    def test_home_advantage(self, model: BettingModel, sample_match: Match) -> None:
        score, reasons = model._calculate_home_advantage_score(sample_match)
        assert_that(score).is_greater_than(0)
        assert_that(reasons).is_not_empty()

    def test_h2h_no_data(self, model: BettingModel, minimal_match: Match) -> None:
        score, reasons = model._calculate_h2h_score(minimal_match)
        assert_that(score).is_equal_to(0.0)

    def test_h2h_zero_matches(self, model: BettingModel, home_team: Team, away_team: Team) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            head_to_head={"matches_played": 0, "home_wins": 0, "away_wins": 0, "draws": 0},
        )
        score, _ = model._calculate_h2h_score(match)
        assert_that(score).is_equal_to(0.0)

    def test_h2h_away_dominates(
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
            head_to_head={"matches_played": 4, "home_wins": 0, "away_wins": 4, "draws": 0},
        )
        score, reasons = model._calculate_h2h_score(match)
        assert_that(score).is_less_than(0)
        assert_that(any("Away team dominates" in r for r in reasons)).is_true()

    def test_h2h_even(self, model: BettingModel, home_team: Team, away_team: Team) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            head_to_head={"matches_played": 4, "home_wins": 2, "away_wins": 2, "draws": 0},
        )
        _, reasons = model._calculate_h2h_score(match)
        assert_that(any("Even" in r for r in reasons)).is_true()

    def test_odds_no_data(self, model: BettingModel, minimal_match: Match) -> None:
        score, reasons = model._calculate_odds_score(minimal_match)
        assert_that(score).is_equal_to(0.0)

    def test_odds_incomplete(self, model: BettingModel, home_team: Team, away_team: Team) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            pre_odds=Odds(home_win=None, draw=3.0, away_win=None),
        )
        # has_odds is True because draw is set
        score, reasons = model._calculate_odds_score(match)
        assert_that(score).is_equal_to(0.0)
        assert_that(reasons[0]).contains("Incomplete")

    def test_odds_favor_away(self, model: BettingModel, home_team: Team, away_team: Team) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            pre_odds=Odds(home_win=4.0, draw=3.5, away_win=1.5),
        )
        score, reasons = model._calculate_odds_score(match)
        assert_that(score).is_less_than(0)
        assert_that(any("favor away" in r for r in reasons)).is_true()

    def test_odds_even(self, model: BettingModel, home_team: Team, away_team: Team) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            pre_odds=Odds(home_win=2.5, draw=3.2, away_win=2.5),
        )
        _, reasons = model._calculate_odds_score(match)
        assert_that(any("evenly matched" in r for r in reasons)).is_true()

    def test_odds_zero_odds(self, model: BettingModel, home_team: Team, away_team: Team) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            pre_odds=Odds(home_win=0.0, draw=3.0, away_win=0.0),
        )
        # has_odds: 0.0 is falsy for `any(o is not None)` - wait, 0.0 is not None so has_odds is True
        score, _ = model._calculate_odds_score(match)
        assert_that(score).is_equal_to(0.0)

    def test_goal_score_no_perf(self, model: BettingModel, minimal_match: Match) -> None:
        score, reasons = model._calculate_goal_score(minimal_match)
        assert_that(score).is_equal_to(0.0)
        assert_that(reasons).is_empty()

    def test_goal_score_zero_matches(
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
            home_performance=TeamPerformanceStats(team_id="1", matches_analyzed=0),
            away_performance=TeamPerformanceStats(team_id="2", matches_analyzed=5),
        )
        score, _ = model._calculate_goal_score(match)
        assert_that(score).is_equal_to(0.0)

    def test_goal_score_with_stats(self, model: BettingModel, sample_match: Match) -> None:
        score, reasons = model._calculate_goal_score(sample_match)
        assert_that(score).is_greater_than(0.15)
        assert_that(any("stronger goal stats" in r for r in reasons)).is_true()

    def test_goal_score_away_stronger(
        self,
        model: BettingModel,
        home_team: Team,
        away_team: Team,
        sample_performance_home: TeamPerformanceStats,
        sample_performance_away: TeamPerformanceStats,
    ) -> None:
        # Swap so away has stronger stats
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            home_performance=sample_performance_away,
            away_performance=sample_performance_home,
        )
        score, reasons = model._calculate_goal_score(match)
        assert_that(score).is_less_than(-0.15)
        assert_that(any("Away team has stronger goal stats" in r for r in reasons)).is_true()

    def test_venue_form_no_perf(self, model: BettingModel, minimal_match: Match) -> None:
        score, _ = model._calculate_venue_form_score(minimal_match)
        assert_that(score).is_equal_to(0.0)

    def test_venue_form_strong_home(self, model: BettingModel, sample_match: Match) -> None:
        score, reasons = model._calculate_venue_form_score(sample_match)
        assert_that(score).is_greater_than(0.2)
        assert_that(any("excels at home" in r for r in reasons)).is_true()

    def test_venue_form_strong_away(
        self,
        model: BettingModel,
        home_team: Team,
        away_team: Team,
    ) -> None:
        home = TeamPerformanceStats(team_id="1", home_games=5, home_wins=0, home_win_rate=0.0)
        away = TeamPerformanceStats(team_id="2", away_games=5, away_wins=4, away_win_rate=0.8)
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            home_performance=home,
            away_performance=away,
        )
        score, reasons = model._calculate_venue_form_score(match)
        assert_that(score).is_less_than(-0.2)
        assert_that(any("strong on the road" in r for r in reasons)).is_true()

    def test_defense_no_perf(self, model: BettingModel, minimal_match: Match) -> None:
        score, _ = model._calculate_defense_score(minimal_match)
        assert_that(score).is_equal_to(0.0)

    def test_defense_with_stats(self, model: BettingModel, sample_match: Match) -> None:
        score, reasons = model._calculate_defense_score(sample_match)
        assert_that(any("Clean sheet" in r for r in reasons)).is_true()
        assert_that(any("Home team defensively solid" in r for r in reasons)).is_true()

    def test_defense_away_solid(
        self, model: BettingModel, home_team: Team, away_team: Team
    ) -> None:
        home = TeamPerformanceStats(team_id="1", matches_analyzed=10, clean_sheet_rate=0.1)
        away = TeamPerformanceStats(team_id="2", matches_analyzed=10, clean_sheet_rate=0.5)
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            home_performance=home,
            away_performance=away,
        )
        _, reasons = model._calculate_defense_score(match)
        assert_that(any("Away team defensively solid" in r for r in reasons)).is_true()

    def test_momentum_no_perf(self, model: BettingModel, minimal_match: Match) -> None:
        score, _ = model._calculate_momentum_score(minimal_match)
        assert_that(score).is_equal_to(0.0)

    def test_momentum_zero_matches(
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
            home_performance=TeamPerformanceStats(team_id="1", matches_analyzed=0),
            away_performance=TeamPerformanceStats(team_id="2", matches_analyzed=0),
        )
        score, _ = model._calculate_momentum_score(match)
        assert_that(score).is_equal_to(0.0)

    def test_momentum_with_stats(self, model: BettingModel, sample_match: Match) -> None:
        score, reasons = model._calculate_momentum_score(sample_match)
        assert_that(score).is_greater_than(0)
        assert_that(any("stronger momentum" in r for r in reasons)).is_true()

    def test_momentum_away_stronger(
        self,
        model: BettingModel,
        home_team: Team,
        away_team: Team,
        sample_performance_home: TeamPerformanceStats,
        sample_performance_away: TeamPerformanceStats,
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
            home_performance=sample_performance_away,
            away_performance=sample_performance_home,
        )
        score, reasons = model._calculate_momentum_score(match)
        assert_that(score).is_less_than(0)
        assert_that(any("Away team has stronger momentum" in r for r in reasons)).is_true()

    def test_match_stats_no_perf(self, model: BettingModel, minimal_match: Match) -> None:
        score, _ = model._calculate_match_stats_score(minimal_match)
        assert_that(score).is_equal_to(0.0)

    def test_match_stats_insufficient(
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
            home_performance=TeamPerformanceStats(team_id="1", matches_with_stats=0),
            away_performance=TeamPerformanceStats(team_id="2", matches_with_stats=5),
        )
        score, _ = model._calculate_match_stats_score(match)
        assert_that(score).is_equal_to(0.0)

    def test_match_stats_with_data(self, model: BettingModel, sample_match: Match) -> None:
        score, reasons = model._calculate_match_stats_score(sample_match)
        assert_that(score).is_not_equal_to(0.0)
        assert_that(any("Possession" in r for r in reasons)).is_true()
        assert_that(any("superior match statistics" in r for r in reasons)).is_true()

    def test_match_stats_away_superior(
        self,
        model: BettingModel,
        home_team: Team,
        away_team: Team,
        sample_performance_home: TeamPerformanceStats,
        sample_performance_away: TeamPerformanceStats,
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
            home_performance=sample_performance_away,
            away_performance=sample_performance_home,
        )
        score, reasons = model._calculate_match_stats_score(match)
        assert_that(score).is_less_than(-0.15)
        assert_that(any("Away team has superior" in r for r in reasons)).is_true()

    def test_xg_no_perf(self, model: BettingModel, minimal_match: Match) -> None:
        score, _ = model._calculate_xg_score(minimal_match)
        assert_that(score).is_equal_to(0.0)

    def test_xg_zero(self, model: BettingModel, home_team: Team, away_team: Team) -> None:
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            home_performance=TeamPerformanceStats(team_id="1", avg_expected_goals=0),
            away_performance=TeamPerformanceStats(team_id="2", avg_expected_goals=0),
        )
        score, _ = model._calculate_xg_score(match)
        assert_that(score).is_equal_to(0.0)

    def test_xg_with_data(self, model: BettingModel, sample_match: Match) -> None:
        score, reasons = model._calculate_xg_score(sample_match)
        assert_that(score).is_greater_than(0)
        assert_that(any("xG" in r for r in reasons)).is_true()
        assert_that(any("xGD" in r for r in reasons)).is_true()
        assert_that(any("higher quality chances" in r for r in reasons)).is_true()

    def test_xg_away_better(
        self,
        model: BettingModel,
        home_team: Team,
        away_team: Team,
        sample_performance_home: TeamPerformanceStats,
        sample_performance_away: TeamPerformanceStats,
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
            home_performance=sample_performance_away,
            away_performance=sample_performance_home,
        )
        score, reasons = model._calculate_xg_score(match)
        assert_that(score).is_less_than(-0.15)
        assert_that(any("Away team creates" in r for r in reasons)).is_true()

    def test_reliability_no_perf(self, model: BettingModel, minimal_match: Match) -> None:
        score, _ = model._calculate_reliability_score(minimal_match)
        assert_that(score).is_equal_to(0.0)

    def test_reliability_with_stats(self, model: BettingModel, sample_match: Match) -> None:
        score, reasons = model._calculate_reliability_score(sample_match)
        assert_that(any("Reliability" in r for r in reasons)).is_true()
        assert_that(any("Cards/game" in r for r in reasons)).is_true()

    def test_reliability_similar(
        self, model: BettingModel, home_team: Team, away_team: Team
    ) -> None:
        home = TeamPerformanceStats(
            team_id="1", matches_with_stats=5, reliability_score=0.5, avg_cards=2.0
        )
        away = TeamPerformanceStats(
            team_id="2", matches_with_stats=5, reliability_score=0.5, avg_cards=2.0
        )
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            home_performance=home,
            away_performance=away,
        )
        score, reasons = model._calculate_reliability_score(match)
        assert_that(abs(score)).is_less_than_or_equal_to(0.15)
        assert_that(any("Similar reliability" in r for r in reasons)).is_true()

    def test_reliability_away_better(
        self, model: BettingModel, home_team: Team, away_team: Team
    ) -> None:
        home = TeamPerformanceStats(
            team_id="1", matches_with_stats=5, reliability_score=0.2, avg_cards=4.0
        )
        away = TeamPerformanceStats(
            team_id="2", matches_with_stats=5, reliability_score=0.9, avg_cards=0.5
        )
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            home_performance=home,
            away_performance=away,
        )
        score, reasons = model._calculate_reliability_score(match)
        assert_that(score).is_less_than(-0.15)
        assert_that(any("Away team more reliable" in r for r in reasons)).is_true()


class TestDrawRisk:
    """Tests for draw risk calculation."""

    def test_draw_risk_basic(self, model: BettingModel) -> None:
        risk = model._calculate_draw_risk(0.0, 0.0, 0.0, None)
        assert_that(risk).is_between(0.15, 0.55)

    def test_draw_risk_with_odds(
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
            pre_odds=Odds(home_win=2.5, draw=2.9, away_win=2.6),  # high draw implied
        )
        risk = model._calculate_draw_risk(0.0, 0.0, 0.0, match)
        assert_that(risk).is_greater_than(0.15)

    def test_draw_risk_low_draw_odds(
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
            pre_odds=Odds(home_win=1.5, draw=5.0, away_win=6.0),  # low draw implied
        )
        risk = model._calculate_draw_risk(0.5, 0.5, 0.5, match)
        assert_that(risk).is_between(0.15, 0.55)

    def test_draw_risk_with_ppg(
        self,
        model: BettingModel,
        sample_match: Match,
    ) -> None:
        # similar PPG
        sample_match.home_performance.points_per_game = 1.5
        sample_match.away_performance.points_per_game = 1.4
        sample_match.home_performance.draws = 4
        sample_match.away_performance.draws = 4
        risk = model._calculate_draw_risk(0.1, 0.1, 0.1, sample_match)
        assert_that(risk).is_between(0.15, 0.55)

    def test_draw_risk_ppg_mid(self, model: BettingModel, home_team: Team, away_team: Team) -> None:
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
                team_id="1", matches_analyzed=10, points_per_game=1.5, draws=1
            ),
            away_performance=TeamPerformanceStats(
                team_id="2", matches_analyzed=10, points_per_game=0.7, draws=1
            ),
        )
        risk = model._calculate_draw_risk(0.2, 0.2, 0.2, match)
        assert_that(risk).is_between(0.15, 0.55)

    def test_adaptive_xg_weight_zero(
        self, model: BettingModel, home_team: Team, away_team: Team
    ) -> None:
        """When xG is missing, predict still works (xg_weight -> 0)."""
        match = Match(
            id="1",
            home_team=home_team,
            away_team=away_team,
            competition="PL",
            competition_id="2",
            country="E",
            kickoff_time=datetime.now(),
            status="NS",
            home_form="WWW",
            away_form="LLL",
            home_performance=TeamPerformanceStats(
                team_id="1",
                matches_analyzed=5,
                matches_with_stats=3,
                avg_expected_goals=0,
            ),
            away_performance=TeamPerformanceStats(
                team_id="2",
                matches_analyzed=5,
                matches_with_stats=3,
                avg_expected_goals=0,
            ),
        )
        pred = model.predict(match)
        assert_that(pred).is_not_none()
