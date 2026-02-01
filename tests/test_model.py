"""Tests for the betting model."""

from datetime import datetime

import pytest
from assertpy import assert_that

from slickbet.api import Match, Team
from slickbet.model import BetOutcome, BettingModel


@pytest.fixture
def sample_match() -> Match:
    """Create a sample match for testing."""
    return Match(
        id="12345",
        home_team=Team(id="1", name="Home FC", country="England"),
        away_team=Team(id="2", name="Away United", country="England"),
        competition="Premier League",
        competition_id="1",
        country="England",
        kickoff_time=datetime.now(),
        status="NS",
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
    )


@pytest.fixture
def model() -> BettingModel:
    """Create a betting model for testing."""
    return BettingModel()


class TestBettingModel:
    """Test cases for BettingModel."""

    def test_predict_returns_prediction(
        self, model: BettingModel, sample_match: Match
    ) -> None:
        """Test that predict returns a BetPrediction."""
        prediction = model.predict(sample_match)

        assert_that(prediction).is_not_none()
        assert_that(prediction.match).is_equal_to(sample_match)
        assert_that(prediction.probability).is_between(0.0, 1.0)
        assert_that(prediction.confidence).is_between(0.0, 1.0)

    def test_predict_favors_stronger_team(
        self, model: BettingModel, sample_match: Match
    ) -> None:
        """Test that prediction favors the clearly stronger team."""
        prediction = model.predict(sample_match)

        # Home team is clearly stronger (better form, position, h2h)
        assert_that(prediction.recommended_outcome).is_equal_to(BetOutcome.HOME_WIN)
        assert_that(prediction.probability).is_greater_than(0.5)

    def test_predict_with_no_stats(self, model: BettingModel) -> None:
        """Test prediction with minimal statistics."""
        match = Match(
            id="99999",
            home_team=Team(id="10", name="Unknown FC"),
            away_team=Team(id="11", name="Mystery United"),
            competition="Unknown League",
            competition_id="99",
            country="Unknown",
            kickoff_time=datetime.now(),
            status="NS",
        )

        prediction = model.predict(match)

        # Should still return a prediction
        assert_that(prediction).is_not_none()
        # With no stats, home advantage should slightly favor home
        assert_that(prediction.probability).is_greater_than_or_equal_to(0.5)

    def test_form_score_calculation(
        self, model: BettingModel, sample_match: Match
    ) -> None:
        """Test that form score is calculated correctly."""
        prediction = model.predict(sample_match)

        # Home team has much better form, should have positive form score
        assert_that(prediction.form_score).is_greater_than(0)

    def test_position_score_calculation(
        self, model: BettingModel, sample_match: Match
    ) -> None:
        """Test that position score is calculated correctly."""
        prediction = model.predict(sample_match)

        # Home team is position 1, away is 18 - should favor home
        assert_that(prediction.position_score).is_greater_than(0)

    def test_reasoning_is_populated(
        self, model: BettingModel, sample_match: Match
    ) -> None:
        """Test that reasoning list is populated."""
        prediction = model.predict(sample_match)

        assert_that(prediction.reasoning).is_not_empty()
        assert_that(prediction.reasoning).extracting(lambda r: r.lower()).contains_match(
            lambda r: "form" in r
        )


class TestBetOutcome:
    """Test cases for BetOutcome enum."""

    def test_outcome_values(self) -> None:
        """Test that outcome enum has expected values."""
        assert_that(BetOutcome.HOME_WIN.value).is_equal_to("home_win")
        assert_that(BetOutcome.AWAY_WIN.value).is_equal_to("away_win")
        assert_that(BetOutcome.DRAW.value).is_equal_to("draw")

    def test_all_outcomes_exist(self) -> None:
        """Test that all expected outcomes are defined."""
        assert_that(list(BetOutcome)).is_length(3)
        assert_that([o.value for o in BetOutcome]).contains(
            "home_win", "away_win", "draw"
        )
