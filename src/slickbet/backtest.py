"""
Backtesting module for evaluating prediction accuracy against historical data.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from slickbet.api import (
    HistoricalMatch,
    LivescoreAPIError,
    LivescoreClient,
    Match,
)
from slickbet.model import BetOutcome, BetPrediction, BettingModel


@dataclass
class PredictionResult:
    """Result of a single prediction compared to actual outcome."""

    match: HistoricalMatch
    prediction: BetPrediction
    actual_outcome: str  # "H", "A", or "D"
    predicted_outcome: str  # "H" or "A" (we don't predict draws)
    is_correct: bool
    probability: float
    confidence: float

    # Double chance results
    home_or_draw_correct: bool = False  # 1X bet would have won
    away_or_draw_correct: bool = False  # X2 bet would have won
    no_draw_correct: bool = False  # 12 bet would have won

    @property
    def predicted_team(self) -> str:
        """Name of the team we predicted to win."""
        if self.predicted_outcome == "H":
            return self.match.home_team.name
        return self.match.away_team.name

    @property
    def actual_winner(self) -> str:
        """Name of the actual winner (or 'Draw')."""
        if self.actual_outcome == "H":
            return self.match.home_team.name
        elif self.actual_outcome == "A":
            return self.match.away_team.name
        return "Draw"

    @property
    def best_double_chance_correct(self) -> bool:
        """Whether the recommended double chance bet would have won."""
        if self.prediction.double_chance is None:
            return False
        dc = self.prediction.double_chance
        best_type, _ = dc.best_double_chance
        if "Home or Draw" in best_type:
            return self.home_or_draw_correct
        elif "Away or Draw" in best_type:
            return self.away_or_draw_correct
        else:
            return self.no_draw_correct


@dataclass
class BacktestResults:
    """Aggregated results from a backtest run."""

    results: list[PredictionResult] = field(default_factory=list)
    competition: str = ""
    from_date: datetime | None = None
    to_date: datetime | None = None

    @property
    def total_predictions(self) -> int:
        """Total number of predictions made."""
        return len(self.results)

    @property
    def correct_predictions(self) -> int:
        """Number of correct predictions."""
        return sum(1 for r in self.results if r.is_correct)

    @property
    def accuracy(self) -> float:
        """Overall accuracy (0-1)."""
        if not self.results:
            return 0.0
        return self.correct_predictions / self.total_predictions

    @property
    def home_predictions(self) -> list[PredictionResult]:
        """Predictions where we bet on home team."""
        return [r for r in self.results if r.predicted_outcome == "H"]

    @property
    def away_predictions(self) -> list[PredictionResult]:
        """Predictions where we bet on away team."""
        return [r for r in self.results if r.predicted_outcome == "A"]

    @property
    def home_accuracy(self) -> float:
        """Accuracy for home win predictions."""
        home = self.home_predictions
        if not home:
            return 0.0
        return sum(1 for r in home if r.is_correct) / len(home)

    @property
    def away_accuracy(self) -> float:
        """Accuracy for away win predictions."""
        away = self.away_predictions
        if not away:
            return 0.0
        return sum(1 for r in away if r.is_correct) / len(away)

    @property
    def high_confidence_results(self) -> list[PredictionResult]:
        """Predictions with confidence > 0.3."""
        return [r for r in self.results if r.confidence > 0.3]

    @property
    def high_confidence_accuracy(self) -> float:
        """Accuracy for high confidence predictions."""
        high_conf = self.high_confidence_results
        if not high_conf:
            return 0.0
        return sum(1 for r in high_conf if r.is_correct) / len(high_conf)

    @property
    def high_confidence_accuracy_excl_draws(self) -> float:
        """Accuracy for high confidence predictions, excluding draws."""
        high_conf = [r for r in self.results if r.confidence > 0.3 and r.actual_outcome != "D"]
        if not high_conf:
            return 0.0
        return sum(1 for r in high_conf if r.is_correct) / len(high_conf)

    @property
    def low_draw_risk_results(self) -> list[PredictionResult]:
        """Predictions where draw risk < 30%."""
        return [r for r in self.results if r.prediction.draw_risk < 0.30]

    @property
    def low_draw_risk_accuracy(self) -> float:
        """Accuracy for low draw risk predictions."""
        low_dr = self.low_draw_risk_results
        if not low_dr:
            return 0.0
        return sum(1 for r in low_dr if r.is_correct) / len(low_dr)

    @property
    def high_probability_results(self) -> list[PredictionResult]:
        """Predictions with probability > 60%."""
        return [r for r in self.results if r.probability > 0.60]

    @property
    def high_probability_accuracy(self) -> float:
        """Accuracy for high probability predictions (>60%)."""
        high_prob = self.high_probability_results
        if not high_prob:
            return 0.0
        return sum(1 for r in high_prob if r.is_correct) / len(high_prob)

    @property
    def high_probability_accuracy_excl_draws(self) -> float:
        """Accuracy for high probability predictions (>60%), excluding draws."""
        high_prob = [r for r in self.results if r.probability > 0.60 and r.actual_outcome != "D"]
        if not high_prob:
            return 0.0
        return sum(1 for r in high_prob if r.is_correct) / len(high_prob)

    @property
    def draws_encountered(self) -> int:
        """Number of matches that ended in a draw."""
        return sum(1 for r in self.results if r.actual_outcome == "D")

    @property
    def accuracy_excluding_draws(self) -> float:
        """Accuracy excluding matches that ended in draws."""
        non_draws = [r for r in self.results if r.actual_outcome != "D"]
        if not non_draws:
            return 0.0
        return sum(1 for r in non_draws if r.is_correct) / len(non_draws)

    # Double Chance statistics
    @property
    def home_or_draw_accuracy(self) -> float:
        """Accuracy for 1X (Home or Draw) double chance bets."""
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.home_or_draw_correct) / len(self.results)

    @property
    def away_or_draw_accuracy(self) -> float:
        """Accuracy for X2 (Away or Draw) double chance bets."""
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.away_or_draw_correct) / len(self.results)

    @property
    def no_draw_accuracy(self) -> float:
        """Accuracy for 12 (No Draw) double chance bets."""
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.no_draw_correct) / len(self.results)

    @property
    def best_double_chance_accuracy(self) -> float:
        """Accuracy when following the recommended double chance bet."""
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.best_double_chance_correct) / len(self.results)

    def by_probability_threshold(self, threshold: float) -> "BacktestResults":
        """Filter results by minimum probability threshold."""
        filtered = BacktestResults(
            results=[r for r in self.results if r.probability >= threshold],
            competition=self.competition,
            from_date=self.from_date,
            to_date=self.to_date,
        )
        return filtered


class Backtester:
    """
    Backtester for evaluating betting model against historical data.

    Examples
    --------
    >>> backtester = Backtester()
    >>> results = backtester.run(
    ...     competition_id="1",  # Premier League
    ...     weeks=4,
    ... )
    >>> print(f"Accuracy: {results.accuracy:.1%}")
    """

    # Known competition IDs (from Livescore API)
    BUNDESLIGA = "1"  # Germany
    PREMIER_LEAGUE = "2"  # England
    LA_LIGA = "3"  # Spain
    SERIE_A = "4"  # Italy
    LIGUE_1 = "5"  # France

    def __init__(
        self,
        client: LivescoreClient | None = None,
        model: BettingModel | None = None,
    ):
        """
        Initialize the backtester.

        Parameters
        ----------
        client : LivescoreClient or None, optional
            Livescore API client
        model : BettingModel or None, optional
            Betting model to evaluate
        """
        self.client = client or LivescoreClient()
        self.model = model or BettingModel()

    def run(
        self,
        competition_id: str = "1",
        weeks: int = 4,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        min_probability: float = 0.0,
        verbose: bool = True,
        debug: bool = False,
    ) -> BacktestResults:
        """
        Run backtest on historical data.

        Parameters
        ----------
        competition_id : str, optional
            Competition ID to backtest
        weeks : int, optional
            Number of weeks of history (if from_date not specified)
        from_date : datetime or None, optional
            Start date for historical data
        to_date : datetime or None, optional
            End date for historical data (defaults to today)
        min_probability : float, optional
            Minimum probability threshold for predictions
        verbose : bool, optional
            Print progress information
        debug : bool, optional
            Print detailed match-by-match predictions and results

        Returns
        -------
        BacktestResults
            BacktestResults with all predictions and accuracy metrics
        """
        # Calculate date range: current date minus n weeks
        if to_date is None:
            to_date = datetime.now()
        if from_date is None:
            from_date = to_date - timedelta(weeks=weeks)

        if verbose:
            print("🔍 Fetching historical data...")
            print(f"   Competition ID: {competition_id}")
            print(
                f"   Date range: {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}"
            )

        # Fetch historical matches
        matches = self._fetch_all_history(
            competition_id=competition_id,
            from_date=from_date,
            to_date=to_date,
            verbose=verbose,
        )

        if verbose:
            print(f"   Found {len(matches)} completed matches")

        # Filter to only finished matches with clear outcomes
        valid_matches = [
            m for m in matches if m.status == "FINISHED" and m.outcomes.full_time in ("1", "X", "2")
        ]

        if verbose:
            print(f"   Valid matches with outcomes: {len(valid_matches)}")
            print()
            print("🎯 Running predictions...")

        # Run predictions
        results = BacktestResults(
            competition=competition_id,
            from_date=from_date,
            to_date=to_date,
        )

        for i, hist_match in enumerate(valid_matches):
            try:
                # Convert HistoricalMatch to Match for prediction
                # (simulating not knowing the outcome)
                match = self._historical_to_match(hist_match)

                # Enrich with stats (this simulates what we'd do pre-match)
                match = self._enrich_for_backtest(match, hist_match.date)

                # Generate prediction
                prediction = self.model.predict(match)

                # Skip if below probability threshold
                if prediction.probability < min_probability:
                    continue

                # Determine predicted outcome
                if prediction.recommended_outcome == BetOutcome.HOME_WIN:
                    predicted = "H"
                else:
                    predicted = "A"

                # Get actual outcome
                actual = hist_match.result  # "H", "A", or "D"

                # Check if correct
                is_correct = predicted == actual

                # Calculate double chance results
                # 1X (Home or Draw): correct if actual is H or D
                home_or_draw_correct = actual in ("H", "D")
                # X2 (Away or Draw): correct if actual is A or D
                away_or_draw_correct = actual in ("A", "D")
                # 12 (No Draw): correct if actual is H or A
                no_draw_correct = actual in ("H", "A")

                result = PredictionResult(
                    match=hist_match,
                    prediction=prediction,
                    actual_outcome=actual or "D",
                    predicted_outcome=predicted,
                    is_correct=is_correct,
                    probability=prediction.probability,
                    confidence=prediction.confidence,
                    home_or_draw_correct=home_or_draw_correct,
                    away_or_draw_correct=away_or_draw_correct,
                    no_draw_correct=no_draw_correct,
                )
                results.results.append(result)

                # Debug output: show match details, prediction, and actual result
                if debug:
                    self._print_debug_match(result)

                if verbose and (i + 1) % 10 == 0:
                    print(f"   Processed {i + 1}/{len(valid_matches)} matches...")

            except Exception as e:
                if verbose:
                    print(f"   ⚠ Failed to process match: {e}")
                continue

        if verbose:
            print(f"   Completed {len(results.results)} predictions")
            print()

        return results

    def _fetch_all_history(
        self,
        competition_id: str,
        from_date: datetime,
        to_date: datetime,
        verbose: bool = True,
    ) -> list[HistoricalMatch]:
        """Fetch all historical matches, handling pagination."""
        all_matches = []
        page = 1
        max_pages = 20  # Safety limit

        while page <= max_pages:
            try:
                matches = self.client.get_history(
                    competition_id=competition_id,
                    from_date=from_date,
                    to_date=to_date,
                    page=page,
                )

                if not matches:
                    break

                # Filter to date range AND competition (API might return unexpected data)
                matches = [
                    m
                    for m in matches
                    if from_date <= m.date <= to_date and m.competition_id == competition_id
                ]

                all_matches.extend(matches)
                page += 1

                if verbose:
                    print(f"   Fetched page {page - 1}: {len(matches)} matches")

            except LivescoreAPIError as e:
                if verbose:
                    print(f"   ⚠ API error on page {page}: {e}")
                break

        return all_matches

    def _historical_to_match(self, hist: HistoricalMatch) -> Match:
        """Convert a HistoricalMatch to a Match for prediction."""
        return Match(
            id=hist.id,
            home_team=hist.home_team,
            away_team=hist.away_team,
            competition=hist.competition,
            competition_id=hist.competition_id,
            country=hist.country or "Unknown",
            kickoff_time=hist.date,
            status="NS",  # Pretend it hasn't started
            pre_odds=hist.pre_odds,
        )

    def _enrich_for_backtest(self, match: Match, match_date: datetime) -> Match:
        """
        Enrich match with stats for backtesting.

        Note: For a true backtest, we should only use data available
        BEFORE the match date. This is a simplified version.
        """
        home_id = match.home_team.id if match.home_team else ""
        away_id = match.away_team.id if match.away_team else ""
        comp_id = match.competition_id or ""

        # Skip enrichment if we don't have valid IDs
        if not home_id or not away_id:
            return match

        try:
            # Get team forms (recent matches before this match)
            if home_id:
                match.home_form = self.client.get_team_form(home_id)
            if away_id:
                match.away_form = self.client.get_team_form(away_id)
        except Exception:
            # Catch all exceptions during form retrieval
            pass

        try:
            # Get standings
            if comp_id:
                standings = self.client.get_team_standings(comp_id)
                if isinstance(standings, dict):
                    match.home_position = standings.get(home_id)
                    match.away_position = standings.get(away_id)
        except Exception:
            # Catch all exceptions during standings retrieval
            pass

        try:
            # Get H2H
            if home_id and away_id:
                match.head_to_head = self.client.get_head_to_head(home_id, away_id)
        except Exception:
            # Catch all exceptions during H2H retrieval
            pass

        try:
            # Get detailed performance stats (goals, clean sheets, etc.)
            if home_id:
                match.home_performance = self.client.get_team_performance_stats(home_id)
            if away_id:
                match.away_performance = self.client.get_team_performance_stats(away_id)
        except Exception:
            # Catch all exceptions during performance stats retrieval
            pass

        return match

    def _get_country_flag(self, country: str) -> str:
        """
        Get country flag emoji based on country name.

        Parameters
        ----------
        country : str
            Country name

        Returns
        -------
        str
            Flag emoji or empty string if not found
        """
        if not country:
            return ""

        country_lower = country.lower().strip()

        # Country to flag mapping (with variations)
        country_flags = {
            "germany": "🇩🇪",
            "deutschland": "🇩🇪",
            "england": "🇬🇧",
            "united kingdom": "🇬🇧",
            "uk": "🇬🇧",
            "spain": "🇪🇸",
            "espana": "🇪🇸",
            "italy": "🇮🇹",
            "italia": "🇮🇹",
            "france": "🇫🇷",
            "belgium": "🇧🇪",
            "belgie": "🇧🇪",
            "portugal": "🇵🇹",
            "turkey": "🇹🇷",
            "turkiye": "🇹🇷",
            "netherlands": "🇳🇱",
            "holland": "🇳🇱",
            "croatia": "🇭🇷",
            "hrvatska": "🇭🇷",
            "poland": "🇵🇱",
            "polska": "🇵🇱",
            "scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
            "greece": "🇬🇷",
            "hellas": "🇬🇷",
            "saudi arabia": "🇸🇦",
            "saudi": "🇸🇦",
            "australia": "🇦🇺",
            "argentina": "🇦🇷",
            "brazil": "🇧🇷",
            "brasil": "🇧🇷",
            "mexico": "🇲🇽",
            "méxico": "🇲🇽",
        }

        # Try exact match first
        if country_lower in country_flags:
            return country_flags[country_lower]

        # Try partial match (country name contains key or vice versa)
        for country_name, flag in country_flags.items():
            if country_name in country_lower or country_lower in country_name:
                return flag

        return ""

    def _print_debug_match(self, result: PredictionResult) -> None:
        """
        Print detailed debug information for a single match prediction.

        Parameters
        ----------
        result : PredictionResult
            The prediction result to display
        """
        match = result.match
        pred = result.prediction

        # Get country flag
        country_flag = self._get_country_flag(match.country) if match.country else ""
        competition_display = (
            f"{country_flag} {match.competition}" if country_flag else match.competition
        )

        # Match header
        print()
        print("=" * 80)
        print(f"📅 {match.date.strftime('%Y-%m-%d')} | {competition_display}")
        print(f"🏠 {match.home_team.name} vs ✈️ {match.away_team.name}")
        print("-" * 80)

        # Actual result
        home_score = match.home_score or 0
        away_score = match.away_score or 0
        actual_winner = result.actual_winner
        print(f"⚽ ACTUAL RESULT: {home_score} - {away_score} ({actual_winner})")

        # Our prediction
        predicted_team = result.predicted_team
        outcome_symbol = "✅" if result.is_correct else "❌"
        print(
            f"🎯 OUR PREDICTION: {outcome_symbol} {predicted_team} "
            f"(Prob: {pred.probability:.1%}, Conf: {pred.confidence:.1%})"
        )

        # Prediction details
        if pred.recommended_outcome == BetOutcome.HOME_WIN:
            print(f"   → Bet on: {match.home_team.name} (Home Win)")
        else:
            print(f"   → Bet on: {match.away_team.name} (Away Win)")

        # Double chance info
        if pred.double_chance:
            dc = pred.double_chance
            best_type, best_prob = dc.best_double_chance
            print(f"   → Best Double Chance: {best_type} ({best_prob:.1%})")

        # Key reasoning (first 3 reasons)
        if pred.reasoning:
            print("   📝 Key Factors:")
            for reason in pred.reasoning[:3]:
                print(f"      • {reason}")

        print("=" * 80)


def format_backtest_report(results: BacktestResults) -> str:
    """Generate a formatted report of backtest results."""
    total = results.total_predictions

    # Handle empty results
    if total == 0:
        return "\n".join(
            [
                "=" * 70,
                "📊 BACKTEST RESULTS",
                "=" * 70,
                f"Competition: {results.competition}",
                f"Period: {results.from_date.strftime('%Y-%m-%d') if results.from_date else 'N/A'} to "
                f"{results.to_date.strftime('%Y-%m-%d') if results.to_date else 'N/A'}",
                "",
                "❌ No predictions were generated.",
                "   This could be due to API errors or missing data.",
                "=" * 70,
            ]
        )

    # Calculate percentages safely
    draws_pct = (results.draws_encountered / total * 100) if total > 0 else 0
    home_pct = (len(results.home_predictions) / total * 100) if total > 0 else 0
    away_pct = (len(results.away_predictions) / total * 100) if total > 0 else 0

    lines = [
        "=" * 70,
        "📊 BACKTEST RESULTS",
        "=" * 70,
        f"Competition: {results.competition}",
        f"Period: {results.from_date.strftime('%Y-%m-%d') if results.from_date else 'N/A'} to "
        f"{results.to_date.strftime('%Y-%m-%d') if results.to_date else 'N/A'}",
        "",
        "=" * 70,
        "📈 OVERALL PERFORMANCE",
        "=" * 70,
        f"Total Predictions: {total}",
        f"Correct Predictions: {results.correct_predictions}",
        f"Overall Accuracy: {results.accuracy:.1%}",
        "",
        f"Draws Encountered: {results.draws_encountered} ({draws_pct:.1f}% of matches)",
        f"Accuracy (excl. draws): {results.accuracy_excluding_draws:.1%}",
        "",
        "=" * 70,
        "🏠 HOME vs ✈️ AWAY PREDICTIONS",
        "=" * 70,
        f"Home Win Predictions: {len(results.home_predictions)} ({home_pct:.1f}%)",
        f"Home Win Accuracy: {results.home_accuracy:.1%}",
        "",
        f"Away Win Predictions: {len(results.away_predictions)} ({away_pct:.1f}%)",
        f"Away Win Accuracy: {results.away_accuracy:.1%}",
        "",
        "=" * 70,
        "🎯 CONFIDENCE & PROBABILITY ANALYSIS",
        "=" * 70,
        f"High Confidence (>30%): {len(results.high_confidence_results)} predictions",
        f"  → Accuracy: {results.high_confidence_accuracy:.1%}",
        f"  → Accuracy (excl. draws): {results.high_confidence_accuracy_excl_draws:.1%}",
        "",
        f"High Probability (>60%): {len(results.high_probability_results)} predictions",
        f"  → Accuracy: {results.high_probability_accuracy:.1%}",
        f"  → Accuracy (excl. draws): {results.high_probability_accuracy_excl_draws:.1%}",
        "",
        f"Low Draw Risk (<30%): {len(results.low_draw_risk_results)} predictions",
        f"  → Accuracy: {results.low_draw_risk_accuracy:.1%}",
        "",
        "=" * 70,
        "🎲 DOUBLE CHANCE ANALYSIS (Safer Bets)",
        "=" * 70,
        f"1X (Home or Draw) Accuracy: {results.home_or_draw_accuracy:.1%}",
        f"X2 (Away or Draw) Accuracy: {results.away_or_draw_accuracy:.1%}",
        f"12 (No Draw) Accuracy: {results.no_draw_accuracy:.1%}",
        "",
        f"Best Double Chance (Recommended) Accuracy: {results.best_double_chance_accuracy:.1%}",
        "",
    ]

    # Accuracy by probability threshold
    lines.extend(
        [
            "=" * 70,
            "📊 ACCURACY BY PROBABILITY THRESHOLD",
            "=" * 70,
        ]
    )

    for threshold in [0.55, 0.60, 0.65, 0.70]:
        filtered = results.by_probability_threshold(threshold)
        if filtered.total_predictions > 0:
            lines.append(
                f"  ≥{threshold:.0%}: {filtered.accuracy:.1%} accuracy "
                f"({filtered.correct_predictions}/{filtered.total_predictions} predictions)"
            )

    lines.extend(["", "=" * 70])

    # All predictions sorted by date
    lines.extend(
        [
            f"📝 ALL PREDICTIONS ({total} matches)",
            "=" * 70,
        ]
    )

    # Sort results by date
    sorted_results = sorted(results.results, key=lambda r: r.match.date)

    for result in sorted_results:
        status = "✅" if result.is_correct else "❌"
        match_date = result.match.date.strftime("%Y-%m-%d")
        lines.append(
            f"{status} [{match_date}] {result.match.home_team.name} vs {result.match.away_team.name}"
        )
        # Build double chance status
        dc_status = ""
        if result.prediction.double_chance:
            dc = result.prediction.double_chance
            best_type, best_prob = dc.best_double_chance
            dc_correct = "✅" if result.best_double_chance_correct else "❌"
            dc_status = f" | DC: {best_type[:2]} {dc_correct}"
        lines.append(
            f"   Score: {result.match.scores.final} | "
            f"Predicted: {result.predicted_outcome} ({result.probability:.1%}) | "
            f"Actual: {result.actual_outcome}{dc_status}"
        )

    lines.append("=" * 70)

    return "\n".join(lines)
