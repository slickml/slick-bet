"""
Betting model for calculating win/loss probabilities.

Implements a weighted scoring system over form, league position, home
advantage, H2H, bookmaker odds, goals, venue form, defense, momentum,
match statistics, expected goals (xG), and discipline/reliability.
Produces ``BetPrediction`` objects including draw risk and double-chance
probabilities.
"""

from dataclasses import dataclass
from enum import Enum

from slickbet.api import Match


class BetOutcome(Enum):
    """Possible betting outcomes."""

    HOME_WIN = "home_win"
    AWAY_WIN = "away_win"
    DRAW = "draw"
    # Double Chance outcomes
    HOME_OR_DRAW = "home_or_draw"  # 1X: Home doesn't lose
    AWAY_OR_DRAW = "away_or_draw"  # X2: Away doesn't lose
    HOME_OR_AWAY = "home_or_away"  # 12: No draw


@dataclass
class DoubleChancePrediction:
    """
    Represents double chance betting predictions for a match.
    Double chance allows betting on two outcomes at once (safer but lower odds).
    """

    # 1X: Home wins OR Draw (Home doesn't lose)
    home_or_draw_prob: float = 0.0
    # X2: Away wins OR Draw (Away doesn't lose)
    away_or_draw_prob: float = 0.0
    # 12: Home wins OR Away wins (No draw)
    no_draw_prob: float = 0.0

    @property
    def best_double_chance(self) -> tuple[str, float]:
        """
        Return the best double chance bet and its probability.

        Returns
        -------
        tuple[str, float]
            ``(label, probability)`` for the highest double-chance option.
        """
        options = {
            "1X (Home or Draw)": self.home_or_draw_prob,
            "X2 (Away or Draw)": self.away_or_draw_prob,
            "12 (No Draw)": self.no_draw_prob,
        }
        best = max(options.items(), key=lambda x: x[1])
        return best


@dataclass
class BetPrediction:
    """
    Represents a betting prediction for a match.
    """

    match: Match
    recommended_outcome: BetOutcome
    probability: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0 (how confident we are in the prediction)

    # Breakdown of factors (core)
    form_score: float
    position_score: float
    home_advantage_score: float
    h2h_score: float
    odds_score: float = 0.0

    # NEW: Enhanced factors
    goal_score: float = 0.0  # Attack/defense strength differential
    venue_form_score: float = 0.0  # Home/away specific performance
    defense_score: float = 0.0  # Clean sheet and goals conceded differential
    momentum_score: float = 0.0  # First-half dominance and consistency
    match_stats_score: float = 0.0  # Match statistics averages (possession, attacks, shots)
    xg_score: float = 0.0  # Expected Goals (xG) differential
    reliability_score: float = 0.0  # Team reliability based on discipline (cards)

    # Draw risk assessment
    draw_risk: float = 0.0  # 0.0 to 1.0 (probability of draw)

    # Double chance predictions
    double_chance: DoubleChancePrediction | None = None

    # Reasoning
    reasoning: list[str] = None  # type: ignore

    @property
    def expected_value(self) -> float:
        """
        Calculate expected value assuming fair 2.0 odds.

        EV = (probability * potential_win) - (1 - probability) * stake

        Returns
        -------
        float
            Expected value per unit stake at even money.
        """
        # Assuming stake of 1 unit and odds of 2.0 (fair odds for 50%)
        return (self.probability * 1.0) - ((1 - self.probability) * 1.0)

    @property
    def match_stats_used(self) -> bool:
        """
        Check if match statistics were used in this prediction.

        Returns
        -------
        bool
            True if match statistics contributed to the prediction
        """
        if not self.match.home_performance or not self.match.away_performance:
            return False

        # Match stats were used if both teams have at least 1 match with statistics
        # We check if statistics were available, not if the score is non-zero
        # (score can be 0.0 if teams are evenly matched, but stats were still used)
        home_stats = self.match.home_performance.matches_with_stats
        away_stats = self.match.away_performance.matches_with_stats

        # Statistics were used if we have data for both teams
        # The score being 0.0 just means teams are evenly matched, not that stats weren't used
        return home_stats >= 1 and away_stats >= 1


class BettingModel:
    """
    Model for calculating betting probabilities based on match statistics.

    The model uses a weighted scoring system combining multiple factors.

    ENHANCED VERSION with 12 factors:
    - Core: Form, Position, Home Advantage, H2H, Odds
    - Goals: Attack/defense strength, Venue Form, Defense (clean sheets)
    - Momentum: First-half performance and consistency
    - Match Stats: Historical averages (possession, attacks, shots on target)
    - xG: Expected Goals differential (quality of chances created)
    - Reliability: Team discipline based on card counts (fewer cards = more reliable)

    Weights optimized based on 120-day backtest across 5 major leagues (704 matches):
    - Bundesliga: 81.3% accuracy (excl. draws)
    - Premier League: 78.2% accuracy (excl. draws)
    - Serie A: 74.8% accuracy (excl. draws)
    - Ligue 1: 70.9% accuracy (excl. draws)
    - La Liga: 68.9% accuracy (excl. draws)
    """

    # Weights for different factors (should sum to 1.0)
    # Updated to include momentum metrics and match statistics from API
    # WEIGHTS = {
    #     "defense": 0.05,  # Clean sheets and defensive solidity
    #     "form": 0.15,  # Recent form - reliable predictor
    #     "goals": 0.11,  # Attack/defense strength differential
    #     "h2h": 0.07,  # Head-to-head - less reliable due to sample size
    #     "home": 0.09,  # Home advantage - consistent ~10% boost
    #     "match_stats": 0.05,  # Match statistics averages (possession, attacks, shots)
    #     "momentum": 0.06,  # First-half dominance and consistency
    #     "odds": 0.17,  # Bookmaker odds - highly predictive when available
    #     "position": 0.19,  # League standing - MOST predictive factor
    #     "reliability": 0.04,  # Team reliability based on discipline (cards)
    #     "venue_form": 0.06,  # Home/away specific performance
    #     "xg": 0.05,  # Expected Goals (xG) - quality of chances created
    # }

    # Copy of the weights from hyperparameter tuning
    WEIGHTS = {
        "defense": 0.1042,
        "form": 0.0333,
        "goals": 0.0855,
        "h2h": 0.0605,
        "home": 0.0945,
        "match_stats": 0.0706,
        "momentum": 0.1195,
        "odds": 0.0549,
        "position": 0.0474,
        "reliability": 0.0874,
        "venue_form": 0.2057,
        "xg": 0.0365,
    }

    # Home advantage baseline (home teams win ~46% of matches historically)
    HOME_ADVANTAGE = 0.12

    # Minimum confidence threshold for recommendations
    MIN_CONFIDENCE = 0.55

    # Draw risk threshold - matches with score close to 0 are draw-prone
    DRAW_RISK_THRESHOLD = 0.15

    def __init__(
        self,
        form_weight: float | None = None,
        position_weight: float | None = None,
        home_weight: float | None = None,
        h2h_weight: float | None = None,
        odds_weight: float | None = None,
        goals_weight: float | None = None,
        venue_form_weight: float | None = None,
        defense_weight: float | None = None,
        momentum_weight: float | None = None,
        match_stats_weight: float | None = None,
        xg_weight: float | None = None,
        reliability_weight: float | None = None,
        min_confidence: float = 0.55,
    ):
        """
        Initialize the betting model with custom weights.

        Parameters
        ----------
        form_weight : float
            Weight for recent form factor
        position_weight : float
            Weight for league position factor
        home_weight : float
            Weight for home advantage factor
        h2h_weight : float
            Weight for head-to-head factor
        odds_weight : float
            Weight for bookmaker odds factor
        goals_weight : float
            Weight for attack/defense strength factor
        venue_form_weight : float
            Weight for home/away specific performance
        defense_weight : float
            Weight for clean sheet/defensive factor
        momentum_weight : float
            Weight for first-half dominance and consistency
        match_stats_weight : float
            Weight for match statistics averages (possession, attacks, shots)
        xg_weight : float
            Weight for Expected Goals (xG) differential
        reliability_weight : float
            Weight for team reliability based on discipline (cards)
        min_confidence : float
            Minimum confidence threshold for recommendations
        """
        w = self.WEIGHTS
        form_weight = form_weight if form_weight is not None else w["form"]
        position_weight = position_weight if position_weight is not None else w["position"]
        home_weight = home_weight if home_weight is not None else w["home"]
        h2h_weight = h2h_weight if h2h_weight is not None else w["h2h"]
        odds_weight = odds_weight if odds_weight is not None else w["odds"]
        goals_weight = goals_weight if goals_weight is not None else w["goals"]
        venue_form_weight = venue_form_weight if venue_form_weight is not None else w["venue_form"]
        defense_weight = defense_weight if defense_weight is not None else w["defense"]
        momentum_weight = momentum_weight if momentum_weight is not None else w["momentum"]
        match_stats_weight = (
            match_stats_weight if match_stats_weight is not None else w["match_stats"]
        )
        xg_weight = xg_weight if xg_weight is not None else w["xg"]
        reliability_weight = (
            reliability_weight if reliability_weight is not None else w["reliability"]
        )

        total = (
            form_weight
            + position_weight
            + home_weight
            + h2h_weight
            + odds_weight
            + goals_weight
            + venue_form_weight
            + defense_weight
            + momentum_weight
            + match_stats_weight
            + xg_weight
            + reliability_weight
        )

        # Normalize weights to sum to 1.0
        self.weights = {
            "form": form_weight / total,
            "position": position_weight / total,
            "home": home_weight / total,
            "h2h": h2h_weight / total,
            "odds": odds_weight / total,
            "goals": goals_weight / total,
            "venue_form": venue_form_weight / total,
            "defense": defense_weight / total,
            "momentum": momentum_weight / total,
            "match_stats": match_stats_weight / total,
            "xg": xg_weight / total,
            "reliability": reliability_weight / total,
        }

        self.min_confidence = min_confidence

    def predict(self, match: Match) -> BetPrediction:
        """
        Generate a betting prediction for a match.

        Parameters
        ----------
        match : Match
            Match object with statistics

        Returns
        -------
        BetPrediction
            BetPrediction with probabilities and recommendation
        """
        reasoning = []

        # Calculate individual factor scores (Core factors)
        form_score, form_reasons = self._calculate_form_score(match)
        reasoning.extend(form_reasons)

        position_score, position_reasons = self._calculate_position_score(match)
        reasoning.extend(position_reasons)

        home_score, home_reasons = self._calculate_home_advantage_score(match)
        reasoning.extend(home_reasons)

        h2h_score, h2h_reasons = self._calculate_h2h_score(match)
        reasoning.extend(h2h_reasons)

        odds_score, odds_reasons = self._calculate_odds_score(match)
        reasoning.extend(odds_reasons)

        # NEW: Calculate enhanced factors
        goal_score, goal_reasons = self._calculate_goal_score(match)
        reasoning.extend(goal_reasons)

        venue_form_score, venue_reasons = self._calculate_venue_form_score(match)
        reasoning.extend(venue_reasons)

        defense_score, defense_reasons = self._calculate_defense_score(match)
        reasoning.extend(defense_reasons)

        momentum_score, momentum_reasons = self._calculate_momentum_score(match)
        reasoning.extend(momentum_reasons)

        match_stats_score, match_stats_reasons = self._calculate_match_stats_score(match)
        reasoning.extend(match_stats_reasons)

        xg_score, xg_reasons = self._calculate_xg_score(match)
        reasoning.extend(xg_reasons)

        reliability_score, reliability_reasons = self._calculate_reliability_score(match)
        reasoning.extend(reliability_reasons)

        # Adaptive weighting for match statistics based on data quality
        # More weight when we have more matches with statistics
        match_stats_weight = self.weights["match_stats"]
        if match.home_performance and match.away_performance:
            # Scale weight based on average matches with stats (0.0 to 1.0)
            # Full weight at 5+ matches, reduced proportionally below that
            home_stats = match.home_performance.matches_with_stats
            away_stats = match.away_performance.matches_with_stats
            avg_matches_with_stats = (home_stats + away_stats) / 2.0
            # Scale factor: 0.0 (no data) to 1.0 (5+ matches)
            data_quality_factor = min(avg_matches_with_stats / 5.0, 1.0)
            match_stats_weight = match_stats_weight * data_quality_factor

        # Adaptive weighting for xG when both teams have xG data
        xg_weight = self.weights["xg"]
        if match.home_performance and match.away_performance:
            if (
                match.home_performance.avg_expected_goals <= 0
                or match.away_performance.avg_expected_goals <= 0
            ):
                xg_weight = 0.0
            else:
                avg_matches = (
                    match.home_performance.matches_with_stats
                    + match.away_performance.matches_with_stats
                ) / 2.0
                xg_weight = xg_weight * min(avg_matches / 5.0, 1.0)

        # Calculate weighted composite score
        # Score > 0 favors home team, score < 0 favors away team
        composite_score = (
            form_score * self.weights["form"]
            + position_score * self.weights["position"]
            + home_score * self.weights["home"]
            + h2h_score * self.weights["h2h"]
            + odds_score * self.weights["odds"]
            + goal_score * self.weights["goals"]
            + venue_form_score * self.weights["venue_form"]
            + defense_score * self.weights["defense"]
            + momentum_score * self.weights["momentum"]
            + match_stats_score * match_stats_weight
            + xg_score * xg_weight
            + reliability_score * self.weights["reliability"]
        )

        # Convert score to probability using sigmoid-like transformation
        # Score range is roughly -1 to 1, map to probability 0.2 to 0.8
        home_probability = self._score_to_probability(composite_score)
        away_probability = 1.0 - home_probability

        # Calculate draw risk based on how close the composite score is to 0
        # Matches with evenly-matched teams are more likely to draw
        # Now also considers bookmaker draw odds and PPG proximity
        draw_risk = self._calculate_draw_risk(composite_score, form_score, position_score, match)
        if draw_risk > self.DRAW_RISK_THRESHOLD:
            reasoning.append(f"⚠️ High draw risk detected ({draw_risk:.1%})")

        # Calculate double chance probabilities
        # These assume draw probability = draw_risk (simplified model)
        draw_prob = draw_risk
        # Adjust home/away probs to account for draw
        adjusted_home = home_probability * (1 - draw_prob)
        adjusted_away = away_probability * (1 - draw_prob)

        double_chance = DoubleChancePrediction(
            home_or_draw_prob=adjusted_home + draw_prob,  # 1X
            away_or_draw_prob=adjusted_away + draw_prob,  # X2
            no_draw_prob=adjusted_home + adjusted_away,  # 12 (= 1 - draw_prob)
        )

        best_dc, best_dc_prob = double_chance.best_double_chance
        reasoning.append(f"🎲 Best double chance: {best_dc} ({best_dc_prob:.1%})")

        # Determine recommended outcome and confidence
        if home_probability > away_probability:
            recommended = BetOutcome.HOME_WIN
            probability = home_probability
            # Reduce confidence if draw risk is high
            base_confidence = abs(home_probability - 0.5) * 2
            confidence = base_confidence * (1.0 - draw_risk * 0.5)
        else:
            recommended = BetOutcome.AWAY_WIN
            probability = away_probability
            base_confidence = abs(away_probability - 0.5) * 2
            confidence = base_confidence * (1.0 - draw_risk * 0.5)

        return BetPrediction(
            match=match,
            recommended_outcome=recommended,
            probability=probability,
            confidence=confidence,
            form_score=form_score,
            position_score=position_score,
            home_advantage_score=home_score,
            h2h_score=h2h_score,
            odds_score=odds_score,
            goal_score=goal_score,
            venue_form_score=venue_form_score,
            defense_score=defense_score,
            momentum_score=momentum_score,
            match_stats_score=match_stats_score,
            xg_score=xg_score,
            reliability_score=reliability_score,
            draw_risk=draw_risk,
            double_chance=double_chance,
            reasoning=reasoning,
        )

    def _calculate_form_score(self, match: Match) -> tuple[float, list[str]]:
        """
        Calculate score based on recent form.

        Parameters
        ----------
        match : Match
            Match with ``home_form`` / ``away_form`` strings.

        Returns
        -------
        tuple[float, list[str]]
            Tuple of (score, reasoning_list).
            Score range: -1.0 to 1.0 (positive favors home)
        """
        reasons = []

        home_form = match.home_form or ""
        away_form = match.away_form or ""

        if not home_form and not away_form:
            return 0.0, ["No form data available"]

        def form_to_points(form: str) -> float:
            """Convert form string to points (3 for W, 1 for D, 0 for L)."""
            if not form:
                return 0.0
            points = sum(3 if r == "W" else (1 if r == "D" else 0) for r in form)
            max_points = len(form) * 3
            return points / max_points if max_points > 0 else 0.0

        home_points = form_to_points(home_form)
        away_points = form_to_points(away_form)

        # Score difference normalized to -1 to 1
        score = home_points - away_points

        if home_form:
            reasons.append(f"Home form: {home_form} ({home_points:.2%} of max points)")
        if away_form:
            reasons.append(f"Away form: {away_form} ({away_points:.2%} of max points)")

        if score > 0.2:
            reasons.append("→ Home team in significantly better form")
        elif score < -0.2:
            reasons.append("→ Away team in significantly better form")

        return score, reasons

    def _calculate_position_score(self, match: Match) -> tuple[float, list[str]]:
        """
        Calculate score based on league position.

        Parameters
        ----------
        match : Match
            Match with ``home_position`` / ``away_position``.

        Returns
        -------
        tuple[float, list[str]]
            Tuple of (score, reasoning_list).
            Score range: -1.0 to 1.0 (positive favors home)
        """
        reasons = []

        home_pos = match.home_position
        away_pos = match.away_position

        if home_pos is None or away_pos is None:
            return 0.0, ["No standings data available"]

        # Convert to int if they're strings
        try:
            home_pos = int(home_pos)
            away_pos = int(away_pos)
        except (ValueError, TypeError):
            return 0.0, ["Invalid standings data"]

        # Position difference (lower is better)
        # Normalize assuming max 20 teams in league
        pos_diff = (away_pos - home_pos) / 20.0

        # Clamp to -1 to 1
        score = max(-1.0, min(1.0, pos_diff))

        reasons.append(f"Home position: {home_pos}, Away position: {away_pos}")

        if home_pos < away_pos:
            reasons.append(f"→ Home team {away_pos - home_pos} places higher")
        elif away_pos < home_pos:
            reasons.append(f"→ Away team {home_pos - away_pos} places higher")
        else:
            reasons.append("→ Teams at same position")

        return score, reasons

    def _calculate_home_advantage_score(self, match: Match) -> tuple[float, list[str]]:
        """
        Calculate score based on home advantage.

        Parameters
        ----------
        match : Match
            Match being scored (unused beyond signature consistency).

        Returns
        -------
        tuple[float, list[str]]
            Tuple of (score, reasoning_list).
            Score range: 0.0 to 0.5 (always favors home)
        """
        # Historical home advantage is significant in soccer
        # Home teams win about 46% of matches, away about 27%, draw about 27%

        score = self.HOME_ADVANTAGE * 2  # Normalize to contribute positively

        reasons = [f"Home advantage factor applied (+{self.HOME_ADVANTAGE:.0%} to home team)"]

        return score, reasons

    def _calculate_h2h_score(self, match: Match) -> tuple[float, list[str]]:
        """
        Calculate score based on head-to-head record.

        Parameters
        ----------
        match : Match
            Match with ``head_to_head`` dict when available.

        Returns
        -------
        tuple[float, list[str]]
            Tuple of (score, reasoning_list).
            Score range: -1.0 to 1.0 (positive favors home)
        """
        reasons = []

        h2h = match.head_to_head

        if not h2h or h2h.get("matches_played", 0) == 0:
            return 0.0, ["No head-to-head data available"]

        total = h2h["matches_played"]
        home_wins = h2h["home_wins"]
        away_wins = h2h["away_wins"]
        draws = h2h["draws"]

        # Calculate win rate difference
        home_win_rate = home_wins / total
        away_win_rate = away_wins / total

        # Score based on win rate difference
        score = home_win_rate - away_win_rate

        reasons.append(
            f"H2H record (last {total}): "
            f"Home wins: {home_wins}, Away wins: {away_wins}, Draws: {draws}"
        )

        if home_wins > away_wins:
            reasons.append("→ Home team dominates head-to-head")
        elif away_wins > home_wins:
            reasons.append("→ Away team dominates head-to-head")
        else:
            reasons.append("→ Even head-to-head record")

        return score, reasons

    def _calculate_odds_score(self, match: Match) -> tuple[float, list[str]]:
        """
        Calculate score based on bookmaker odds.

        Bookmaker odds are highly predictive as they incorporate vast amounts
        of information and are adjusted based on betting patterns.

        Parameters
        ----------
        match : Match
            Match with ``pre_odds`` when available.

        Returns
        -------
        tuple[float, list[str]]
            Tuple of (score, reasoning_list).
            Score range: -1.0 to 1.0 (positive favors home)
        """
        reasons = []

        odds = match.pre_odds
        if not odds or not odds.has_odds:
            return 0.0, ["No odds data available"]

        home_odds = odds.home_win
        away_odds = odds.away_win

        if home_odds is None or away_odds is None:
            return 0.0, ["Incomplete odds data"]

        # Convert odds to implied probability
        # Implied prob = 1 / decimal_odds
        home_implied = 1.0 / home_odds if home_odds > 0 else 0.5
        away_implied = 1.0 / away_odds if away_odds > 0 else 0.5

        # Normalize (bookmaker margin means probs sum to >1)
        total_implied = home_implied + away_implied
        if total_implied > 0:
            home_prob = home_implied / total_implied
            away_prob = away_implied / total_implied
        else:
            home_prob = away_prob = 0.5

        # Score is the probability difference
        score = home_prob - away_prob

        reasons.append(
            f"Odds: Home {home_odds:.2f}, Away {away_odds:.2f} "
            f"(implied: {home_prob:.1%} vs {away_prob:.1%})"
        )

        if home_prob > 0.55:
            reasons.append("→ Bookmakers favor home team")
        elif away_prob > 0.55:
            reasons.append("→ Bookmakers favor away team")
        else:
            reasons.append("→ Bookmakers see evenly matched teams")

        return score, reasons

    def _calculate_goal_score(self, match: Match) -> tuple[float, list[str]]:
        """
        Calculate score based on goal statistics (attack/defense strength).

        Teams that score more and concede less are stronger.
        This captures attacking threat and defensive stability.

        Parameters
        ----------
        match : Match
            Match with ``home_performance`` / ``away_performance``.

        Returns
        -------
        tuple[float, list[str]]
            Tuple of (score, reasoning_list).
            Score range: -1.0 to 1.0 (positive favors home)
        """
        reasons = []

        home_perf = match.home_performance
        away_perf = match.away_performance

        if not home_perf or not away_perf:
            return 0.0, []

        if home_perf.matches_analyzed == 0 or away_perf.matches_analyzed == 0:
            return 0.0, []

        # Compare goals per game (attack strength)
        home_attack = home_perf.goals_per_game
        away_attack = away_perf.goals_per_game

        # Compare goals conceded (defense - lower is better)
        home_defense = home_perf.goals_conceded_per_game
        away_defense = away_perf.goals_conceded_per_game

        # Attack differential (normalized by typical 1.5 goals/game)
        attack_diff = (home_attack - away_attack) / 1.5

        # Defense differential (inverted - lower is better)
        defense_diff = (away_defense - home_defense) / 1.5

        # Combined score (attack matters more than defense)
        score = attack_diff * 0.6 + defense_diff * 0.4

        # Clamp to -1 to 1
        score = max(-1.0, min(1.0, score))

        reasons.append(f"⚽ Goals/game: Home {home_attack:.2f}, Away {away_attack:.2f}")
        reasons.append(f"🛡️ Conceded/game: Home {home_defense:.2f}, Away {away_defense:.2f}")

        if score > 0.15:
            reasons.append("→ Home team has stronger goal stats")
        elif score < -0.15:
            reasons.append("→ Away team has stronger goal stats")

        return score, reasons

    def _calculate_venue_form_score(self, match: Match) -> tuple[float, list[str]]:
        """
        Calculate score based on home/away specific performance.

        Some teams perform very differently at home vs away.
        This captures venue-specific form.

        Parameters
        ----------
        match : Match
            Match with venue-specific rates on performance stats.

        Returns
        -------
        tuple[float, list[str]]
            Tuple of (score, reasoning_list).
            Score range: -1.0 to 1.0 (positive favors home)
        """
        reasons = []

        home_perf = match.home_performance
        away_perf = match.away_performance

        if not home_perf or not away_perf:
            return 0.0, []

        # Home team's home win rate vs Away team's away win rate
        home_rate = home_perf.home_win_rate if home_perf.home_games > 0 else 0.0
        away_rate = away_perf.away_win_rate if away_perf.away_games > 0 else 0.0

        # Differential - positive favors home
        score = home_rate - away_rate

        if home_perf.home_games > 0 or away_perf.away_games > 0:
            reasons.append(
                f"🏠 Home win rate at home: {home_rate:.0%} | Away win rate away: {away_rate:.0%}"
            )

        if score > 0.2:
            reasons.append("→ Home team excels at home; Away struggles away")
        elif score < -0.2:
            reasons.append("→ Away team strong on the road")

        return max(-1.0, min(1.0, score)), reasons

    def _calculate_defense_score(self, match: Match) -> tuple[float, list[str]]:
        """
        Calculate score based on defensive solidity (clean sheets).

        Teams that keep clean sheets regularly are defensively strong.

        Parameters
        ----------
        match : Match
            Match with clean-sheet rates on performance stats.

        Returns
        -------
        tuple[float, list[str]]
            Tuple of (score, reasoning_list).
            Score range: -1.0 to 1.0 (positive favors home)
        """
        reasons = []

        home_perf = match.home_performance
        away_perf = match.away_performance

        if not home_perf or not away_perf:
            return 0.0, []

        home_cs_rate = home_perf.clean_sheet_rate
        away_cs_rate = away_perf.clean_sheet_rate

        # Differential
        score = home_cs_rate - away_cs_rate

        if home_perf.matches_analyzed > 0 and away_perf.matches_analyzed > 0:
            reasons.append(f"🧤 Clean sheet rate: Home {home_cs_rate:.0%}, Away {away_cs_rate:.0%}")

        if home_cs_rate > 0.4:
            reasons.append("→ Home team defensively solid")
        if away_cs_rate > 0.4:
            reasons.append("→ Away team defensively solid")

        return max(-1.0, min(1.0, score)), reasons

    def _calculate_momentum_score(self, match: Match) -> tuple[float, list[str]]:
        """
        Calculate score based on first-half dominance and consistency.

        Teams that consistently lead at half-time and don't collapse are more reliable.
        Based on: https://live-score-api.com/documentation/reference/27/getting-teams-last-matches

        Parameters
        ----------
        match : Match
            Match with HT/win/comeback rates on performance stats.

        Returns
        -------
        tuple[float, list[str]]
            Tuple of (score, reasoning_list).
            Score range: -1.0 to 1.0 (positive favors home)
        """
        reasons = []

        home_perf = match.home_performance
        away_perf = match.away_performance

        if not home_perf or not away_perf:
            return 0.0, []

        if home_perf.matches_analyzed == 0 or away_perf.matches_analyzed == 0:
            return 0.0, []

        # First half dominance: How often does team lead at HT?
        home_ht_lead = home_perf.ht_lead_rate
        away_ht_lead = away_perf.ht_lead_rate

        # Win rate (consistency)
        home_win_rate = home_perf.win_rate
        away_win_rate = away_perf.win_rate

        # Comeback ability (resilience when trailing)
        home_comeback = home_perf.comeback_rate
        away_comeback = away_perf.comeback_rate

        # Calculate momentum score:
        # - HT lead rate shows early dominance (40% weight)
        # - Win rate shows consistency (40% weight)
        # - Comeback rate shows resilience (20% weight)
        home_momentum = home_ht_lead * 0.4 + home_win_rate * 0.4 + home_comeback * 0.2
        away_momentum = away_ht_lead * 0.4 + away_win_rate * 0.4 + away_comeback * 0.2

        score = home_momentum - away_momentum

        # Add reasoning if significant
        if home_perf.ht_wins > 0 or away_perf.ht_wins > 0:
            reasons.append(f"⏱️ HT lead rate: Home {home_ht_lead:.0%}, Away {away_ht_lead:.0%}")

        if home_perf.wins > 0 or away_perf.wins > 0:
            reasons.append(f"📈 Win rate: Home {home_win_rate:.0%}, Away {away_win_rate:.0%}")

        if home_momentum > away_momentum + 0.1:
            reasons.append("→ Home team has stronger momentum")
        elif away_momentum > home_momentum + 0.1:
            reasons.append("→ Away team has stronger momentum")

        return max(-1.0, min(1.0, score)), reasons

    def _calculate_match_stats_score(self, match: Match) -> tuple[float, list[str]]:
        """
        Calculate score based on match statistics averages.

        Teams with better possession, more attacks, and more shots on target
        are generally stronger and more likely to win.

        Based on historical match statistics from:
        https://live-score-api.com/documentation/reference/23/match-statistics

        Parameters
        ----------
        match : Match
            Match with aggregated match-stat averages on performance.

        Returns
        -------
        tuple[float, list[str]]
            Tuple of (score, reasoning_list).
            Score range: -1.0 to 1.0 (positive favors home)
        """
        reasons = []

        home_perf = match.home_performance
        away_perf = match.away_performance

        if not home_perf or not away_perf:
            return 0.0, []

        # Need at least some matches with statistics to make meaningful comparison
        # Lowered to 1 to maximize coverage (statistics may not be available for all matches)
        # If no stats available, return 0.0 but log for debugging
        if home_perf.matches_with_stats < 1 or away_perf.matches_with_stats < 1:
            # Match statistics not available - this is common for older matches
            # The model will still work using other factors (form, position, etc.)
            return 0.0, []

        # Add info about data availability
        reasons.append(
            f"📊 Statistics data: Home {home_perf.matches_with_stats} matches, "
            f"Away {away_perf.matches_with_stats} matches"
        )

        # Calculate differentials (normalized to -1 to 1 range)
        # Possession: 0-100%, normalize by 100
        possession_diff = (home_perf.avg_possession - away_perf.avg_possession) / 100.0

        # Corners: typically 0-15 per game, normalize by 10
        corners_diff = (home_perf.avg_corners - away_perf.avg_corners) / 10.0

        # Attacks: typically 50-150 per game, normalize by 50
        attacks_diff = (home_perf.avg_attacks - away_perf.avg_attacks) / 50.0

        # Dangerous attacks: typically 20-80 per game, normalize by 30
        dangerous_attacks_diff = (
            home_perf.avg_dangerous_attacks - away_perf.avg_dangerous_attacks
        ) / 30.0

        # Shots on target: typically 2-8 per game, normalize by 5
        shots_on_target_diff = (home_perf.avg_shots_on_target - away_perf.avg_shots_on_target) / 5.0

        # Goal Conversion Rate: goals per shot on target
        # Measures efficiency in turning opportunities into actual goals
        conversion_diff = 0.0
        if home_perf.goal_conversion_rate > 0 and away_perf.goal_conversion_rate > 0:
            # Normalize by typical conversion rate (0.3 = 30%)
            conversion_diff = (
                home_perf.goal_conversion_rate - away_perf.goal_conversion_rate
            ) / 0.3

        # Shot Accuracy: shots on target / total shots
        # Higher shot accuracy indicates better chance quality
        shot_accuracy_diff = 0.0
        if home_perf.shot_accuracy > 0 and away_perf.shot_accuracy > 0:
            # Normalize by typical shot accuracy (0.4 = 40%)
            shot_accuracy_diff = (home_perf.shot_accuracy - away_perf.shot_accuracy) / 0.4

        # Weighted combination (xG/xGD moved to separate xg factor)
        # Weights scaled so remaining factors sum to 1.0
        score = (
            possession_diff * 0.32
            + shots_on_target_diff * 0.21
            + shot_accuracy_diff * 0.18  # Shot accuracy (quality)
            + conversion_diff * 0.14  # Goal conversion rate
            + dangerous_attacks_diff * 0.11
            + attacks_diff * 0.03
            + corners_diff * 0.01
        )

        # Clamp to -1 to 1
        score = max(-1.0, min(1.0, score))

        # Add reasoning (xG/xGD reasoning in _calculate_xg_score)
        # Expected Goals Against (xGA) - defensive metric
        if home_perf.avg_expected_goals_against > 0 and away_perf.avg_expected_goals_against > 0:
            reasons.append(
                f"🛡️ xGA (Expected Goals Against): Home {home_perf.avg_expected_goals_against:.2f} vs Away {away_perf.avg_expected_goals_against:.2f}"
            )
        reasons.append(
            f"📊 Possession: Home {home_perf.avg_possession:.1f}% vs Away {away_perf.avg_possession:.1f}%"
        )
        reasons.append(
            f"🎯 Shots on target: Home {home_perf.avg_shots_on_target:.1f} vs Away {away_perf.avg_shots_on_target:.1f}"
        )
        # Shot Accuracy - quality indicator
        if home_perf.shot_accuracy > 0 and away_perf.shot_accuracy > 0:
            reasons.append(
                f"🎪 Shot Accuracy: Home {home_perf.shot_accuracy:.1%} vs Away {away_perf.shot_accuracy:.1%}"
            )
        # Goal Conversion Rate - efficiency metric
        if home_perf.goal_conversion_rate > 0 and away_perf.goal_conversion_rate > 0:
            reasons.append(
                f"🎪 Conversion Rate: Home {home_perf.goal_conversion_rate:.1%} vs Away {away_perf.goal_conversion_rate:.1%}"
            )
        reasons.append(
            f"⚡ Attacks: Home {home_perf.avg_attacks:.1f} vs Away {away_perf.avg_attacks:.1f}"
        )

        if score > 0.15:
            reasons.append("→ Home team has superior match statistics")
        elif score < -0.15:
            reasons.append("→ Away team has superior match statistics")

        return score, reasons

    def _calculate_xg_score(self, match: Match) -> tuple[float, list[str]]:
        """
        Calculate score based on Expected Goals (xG) differential.

        xG measures quality of chances created; higher xG indicates better
        chance creation. Used as a standalone factor with its own weight.

        Parameters
        ----------
        match : Match
            Match with average xG on performance stats.

        Returns
        -------
        tuple[float, list[str]]
            Tuple of (score, reasoning_list).
            Score range: -1.0 to 1.0 (positive favors home).
        """
        reasons: list[str] = []
        if not match.home_performance or not match.away_performance:
            return 0.0, reasons

        home_perf = match.home_performance
        away_perf = match.away_performance

        if home_perf.avg_expected_goals <= 0 and away_perf.avg_expected_goals <= 0:
            return 0.0, reasons

        # Normalize xG diff by typical range (e.g. 2.0 per game)
        xg_diff = (home_perf.avg_expected_goals - away_perf.avg_expected_goals) / 2.0
        score = max(-1.0, min(1.0, xg_diff))

        reasons.append(
            f"⚽ xG (Expected Goals): Home {home_perf.avg_expected_goals:.2f} vs Away {away_perf.avg_expected_goals:.2f}"
        )
        if (
            home_perf.avg_expected_goal_difference != 0
            or away_perf.avg_expected_goal_difference != 0
        ):
            reasons.append(
                f"📈 xGD: Home {home_perf.avg_expected_goal_difference:.2f} vs Away {away_perf.avg_expected_goal_difference:.2f}"
            )
        if score > 0.15:
            reasons.append("→ Home team creates higher quality chances (xG)")
        elif score < -0.15:
            reasons.append("→ Away team creates higher quality chances (xG)")

        return score, reasons

    def _calculate_reliability_score(self, match: Match) -> tuple[float, list[str]]:
        """
        Calculate score based on team reliability (discipline).

        Teams with fewer cards are more reliable and predictable.
        Cards indicate:
        - Discipline issues (yellow cards)
        - Player dismissals (red cards) = playing with fewer players
        - Aggressive/unpredictable play style
        - Higher risk of penalties and free kicks in dangerous areas

        Lower cards = higher reliability = more predictable outcomes.

        Parameters
        ----------
        match : Match
            Match with reliability/card stats on performance.

        Returns
        -------
        tuple[float, list[str]]
            Tuple of (score, reasoning_list).
            Score range: -1.0 to 1.0 (positive favors home)
        """
        reasons = []

        home_perf = match.home_performance
        away_perf = match.away_performance

        if not home_perf or not away_perf:
            return 0.0, []

        # Use reliability_score from TeamPerformanceStats (0.0 to 1.0)
        # Higher reliability = more predictable = better for betting
        home_reliability = home_perf.reliability_score
        away_reliability = away_perf.reliability_score

        # Differential: positive favors home (home more reliable)
        score = home_reliability - away_reliability

        # Scale to -1.0 to 1.0 range
        # Reliability difference of 1.0 (perfect vs unreliable) = 1.0 score
        score = max(-1.0, min(1.0, score))

        # Add reasoning
        reasons.append(f"🎯 Reliability: Home {home_reliability:.2f}, Away {away_reliability:.2f}")

        if home_perf.matches_with_stats > 0:
            reasons.append(
                f"   Cards/game: Home {home_perf.avg_cards:.1f} "
                f"(Y: {home_perf.avg_yellow_cards:.1f}, "
                f"R: {home_perf.avg_red_cards:.1f})"
            )
        if away_perf.matches_with_stats > 0:
            reasons.append(
                f"   Cards/game: Away {away_perf.avg_cards:.1f} "
                f"(Y: {away_perf.avg_yellow_cards:.1f}, "
                f"R: {away_perf.avg_red_cards:.1f})"
            )

        if score > 0.15:
            reasons.append("→ Home team more reliable (fewer cards)")
        elif score < -0.15:
            reasons.append("→ Away team more reliable (fewer cards)")
        else:
            reasons.append("→ Similar reliability levels")

        return score, reasons

    def _calculate_draw_risk(
        self,
        composite_score: float,
        form_score: float,
        position_score: float,
        match: Match | None = None,
    ) -> float:
        """
        Calculate the risk of a match ending in a draw.

        Draws occur ~26% of the time in top leagues. They're more likely when:
        - Teams are evenly matched (composite score close to 0)
        - Both teams have similar form
        - Teams are close in the table
        - Bookmaker draw odds are low (high implied probability)
        - Teams have similar PPG (points per game)
        - Teams have high draw rates in recent matches

        Parameters
        ----------
        composite_score : float
            Overall match score
        form_score : float
            Form differential
        position_score : float
            Position differential
        match : Match or None, optional
            Optional match object for odds and performance data

        Returns
        -------
        float
            Draw risk probability (0.0 to 1.0)
        """
        # Base draw rate in top leagues
        base_draw_rate = 0.26

        # Calculate how evenly matched the teams are
        # Lower scores = more evenly matched = higher draw risk
        score_factor = 1.0 - min(abs(composite_score), 1.0)
        form_factor = 1.0 - min(abs(form_score), 1.0)
        position_factor = 1.0 - min(abs(position_score), 1.0)

        # NEW: Factor in bookmaker draw odds if available
        odds_draw_factor = 0.0
        if match and match.pre_odds and match.pre_odds.draw:
            draw_odds = match.pre_odds.draw
            # Convert odds to implied probability
            # Lower odds = higher probability of draw
            # Typical draw odds: 3.0-4.0 (25-33% implied)
            if draw_odds > 0:
                implied_draw_prob = 1.0 / draw_odds
                # Scale: if implied > 30%, increase draw factor
                if implied_draw_prob > 0.30:
                    odds_draw_factor = (implied_draw_prob - 0.26) * 2  # Boost for high draw odds
                elif implied_draw_prob < 0.22:
                    odds_draw_factor = -0.1  # Reduce for low draw odds

        # NEW: Factor in PPG proximity
        ppg_factor = 0.0
        if match and match.home_performance and match.away_performance:
            home_ppg = match.home_performance.points_per_game
            away_ppg = match.away_performance.points_per_game

            # If both teams have similar PPG, more likely to draw
            ppg_diff = abs(home_ppg - away_ppg)
            if ppg_diff < 0.5:  # Very similar performance
                ppg_factor = 0.10
            elif ppg_diff < 1.0:
                ppg_factor = 0.05

            # NEW: Factor in team draw rates
            home_draws = match.home_performance.draws
            away_draws = match.away_performance.draws
            home_matches = match.home_performance.matches_analyzed
            away_matches = match.away_performance.matches_analyzed

            if home_matches > 0 and away_matches > 0:
                home_draw_rate = home_draws / home_matches
                away_draw_rate = away_draws / away_matches
                avg_draw_rate = (home_draw_rate + away_draw_rate) / 2

                # If teams draw a lot, increase draw risk
                if avg_draw_rate > 0.30:
                    ppg_factor += 0.08

        # Weighted combination
        evenness = (
            score_factor * 0.40
            + form_factor * 0.20
            + position_factor * 0.20
            + max(0, odds_draw_factor) * 0.10  # Only positive contributions
            + ppg_factor * 0.10
        )

        # Scale draw risk: evenly matched games have up to 45% draw chance
        draw_risk = base_draw_rate + (evenness * 0.20) + odds_draw_factor * 0.5

        return max(0.15, min(draw_risk, 0.55))  # Cap between 15-55%

    def _score_to_probability(self, score: float) -> float:
        """
        Convert composite score to win probability.

        Uses a modified sigmoid function to map scores to probabilities.
        Optimized based on backtest analysis for better calibration.

        Parameters
        ----------
        score : float
            Composite score (-1 to 1)

        Returns
        -------
        float
            Probability (0.25 to 0.75, centered at 0.5)
        """
        import math

        # Sigmoid transformation with scaling
        # k controls steepness - increased from 3.0 to 3.5 for more decisive predictions
        k = 3.5

        # Raw sigmoid maps to 0-1
        sigmoid = 1 / (1 + math.exp(-k * score))

        # Scale to 0.25-0.75 range (slightly narrower to avoid overconfidence)
        # This better reflects that even strong favorites only win ~70-75% in soccer
        probability = 0.25 + (sigmoid * 0.50)

        return probability

    def filter_confident_predictions(
        self, predictions: list[BetPrediction], min_confidence: float | None = None
    ) -> list[BetPrediction]:
        """
        Filter predictions by minimum confidence threshold.

        Parameters
        ----------
        predictions : list[BetPrediction]
            List of predictions to filter
        min_confidence : float or None, optional
            Minimum confidence (defaults to model's threshold)

        Returns
        -------
        list[BetPrediction]
            Filtered list of predictions
        """
        threshold = self.min_confidence if min_confidence is None else min_confidence

        return [p for p in predictions if p.confidence >= threshold]
