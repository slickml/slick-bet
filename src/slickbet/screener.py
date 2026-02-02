"""
Betting screener for finding and ranking soccer betting opportunities.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from slickbet.api import LivescoreAPIError, LivescoreClient, Match
from slickbet.model import BetOutcome, BetPrediction, BettingModel

# Major European leagues we care about (by name patterns)
MAJOR_LEAGUE_NAMES = [
    "bundesliga",
    "premier league",
    "la liga",
    "laliga",
    "serie a",
    "ligue 1",
]

# Competition IDs for major leagues (from history API - used for backtesting)
MAJOR_LEAGUE_IDS = {"1", "2", "3", "4", "5"}

# Minor European leagues
MINOR_LEAGUE_NAMES = [
    "belgian pro league",
    "pro league",  # Belgian Pro League
    "primeira liga",
    "portugal",
    "super lig",
    "turkey",
    "eredivisie",
    "holland",
    "netherlands",
]

# Competition IDs for minor European leagues
MINOR_LEAGUE_IDS = {
    "68": "🇧🇪 Belgian Pro League",
    "8": "🇵🇹 Primeira Liga",
    "6": "🇹🇷 Super Lig",
    "196": "🇳🇱 Eredivisie",
}

# Persian Gulf leagues (Saudi Pro League, Qatar Stars League, UAE Pro League)
GULF_LEAGUE_NAMES = [
    "saudi",
    "pro league",  # Saudi Pro League often listed as just "Pro League" or "Premier League"
    "qatar stars",
    "uae pro",
    "emirates",
]

# Competition IDs for Persian Gulf leagues
GULF_LEAGUE_IDS = {
    "313": "🇸🇦 Saudi Pro League",
    "305": "🇶🇦 Qatar Stars League",
    "354": "🇦🇪 UAE Pro League",
}

# All supported league IDs (for reference)
ALL_LEAGUE_IDS = {
    # Major European
    "1": "🇩🇪 Bundesliga",
    "2": "🇬🇧 Premier League",
    "3": "🇪🇸 La Liga",
    "4": "🇮🇹 Serie A",
    "5": "🇫🇷 Ligue 1",
    # Minor European
    "68": "🇧🇪 Belgian Pro League",
    "8": "🇵🇹 Primeira Liga",
    "6": "🇹🇷 Super Lig",
    "196": "🇳🇱 Eredivisie",
    # Persian Gulf
    "313": "🇸🇦 Saudi Pro League",
    "305": "🇶🇦 Qatar Stars League",
    "354": "🇦🇪 UAE Pro League",
}

# Cup competition IDs to exclude (we only want league matches)
CUP_COMPETITION_IDS = {
    # European cups
    "152",
    "153",  # FA Cup, EFL Cup (England)
    "247",  # DFB Pokal (Germany)
    "150",  # Copa del Rey (Spain)
    "149",  # Coppa Italia (Italy)
    "148",  # Coupe de France (France)
    "243",
    "245",  # Champions League, Europa League
    "246",  # Conference League
    # Persian Gulf cups
    "421",
    "356",
    "357",  # UAE cups (Presidents Cup, Cup, League Cup)
    "315",  # Saudi King's Cup
    "307",  # Qatar Stars League Cup
}

# Cup name patterns to exclude
CUP_NAME_PATTERNS = [
    "cup",
    "copa",
    "coupe",
    "coppa",
    "pokal",
    "super cup",
    "supercup",
    "community shield",
    "charity shield",
    "trophy",
    "shield",
    "champions league",
    "europa league",
    "conference league",
]


@dataclass
class ScreenerConfig:
    """Configuration for the betting screener."""

    # Minimum probability threshold for a bet to be considered
    min_probability: float = 0.55

    # Minimum confidence threshold
    min_confidence: float = 0.10

    # Whether to fetch additional statistics (slower but more accurate)
    fetch_detailed_stats: bool = True

    # Maximum number of concurrent API requests for enrichment
    max_workers: int = 5

    # Filter by specific countries (empty = all countries)
    countries: list[str] = None

    # Filter by specific competitions by name (empty = all competitions)
    competitions: list[str] = None

    # Filter by specific competition IDs (empty = all)
    competition_ids: list[str] = None

    # Only show major European leagues (Bundesliga, PL, La Liga, Serie A, Ligue 1)
    major_leagues_only: bool = False

    # Only show Persian Gulf leagues (Saudi Pro League, Qatar Stars League, UAE Pro League)
    gulf_leagues_only: bool = False

    # Show all supported leagues (Major European + Persian Gulf)
    all_leagues: bool = False

    def __post_init__(self):
        if self.countries is None:
            self.countries = []
        if self.competitions is None:
            self.competitions = []
        if self.competition_ids is None:
            self.competition_ids = []


def get_best_double_chance_prob(prediction: BetPrediction) -> float:
    """Get the best double chance probability from a prediction."""
    if prediction.double_chance:
        _, prob = prediction.double_chance.best_double_chance
        return prob
    return prediction.probability  # Fallback to win probability


@dataclass
class ScreenerResult:
    """Result of running the betting screener."""

    predictions: list[BetPrediction]
    total_matches_scanned: int
    matches_filtered: int
    timestamp: datetime

    @property
    def top_bets(self) -> list[BetPrediction]:
        """Get predictions sorted by best double chance probability (highest first)."""
        return sorted(self.predictions, key=lambda p: get_best_double_chance_prob(p), reverse=True)

    @property
    def top_bets_by_win(self) -> list[BetPrediction]:
        """Get predictions sorted by win probability (highest first)."""
        return sorted(self.predictions, key=lambda p: p.probability, reverse=True)

    def get_top_k(self, k: int) -> list[BetPrediction]:
        """Get top K betting opportunities by double chance."""
        return self.top_bets[:k]

    def get_home_wins(self) -> list[BetPrediction]:
        """Get all predictions recommending home win."""
        return [p for p in self.predictions if p.recommended_outcome == BetOutcome.HOME_WIN]

    def get_away_wins(self) -> list[BetPrediction]:
        """Get all predictions recommending away win."""
        return [p for p in self.predictions if p.recommended_outcome == BetOutcome.AWAY_WIN]


class BettingScreener:
    """
    Main screener class for finding betting opportunities.

    Examples
    --------
    >>> screener = BettingScreener()
    >>> result = screener.screen_tomorrow()
    >>> for bet in result.get_top_k(10):
    ...     print(bet)
    """

    def __init__(
        self,
        config: ScreenerConfig | None = None,
        api_client: LivescoreClient | None = None,
        model: BettingModel | None = None,
    ):
        """
        Initialize the betting screener.

        Parameters
        ----------
        config : ScreenerConfig or None, optional
            Screener configuration
        api_client : LivescoreClient or None, optional
            Livescore API client (created if not provided)
        model : BettingModel or None, optional
            Betting model (created if not provided)
        """
        self.config = config or ScreenerConfig()
        self.client = api_client or LivescoreClient()
        self.model = model or BettingModel(min_confidence=self.config.min_confidence)

    def screen_tomorrow(self) -> ScreenerResult:
        """
        Screen tomorrow's matches for betting opportunities.

        Returns
        -------
        ScreenerResult
            ScreenerResult with ranked predictions
        """
        print("🔍 Fetching tomorrow's fixtures...")
        matches = self._get_filtered_fixtures(datetime.now() + timedelta(days=1))
        print(f"   Found {len(matches)} matches")

        return self._screen_matches(matches)

    def screen_date(self, date: datetime) -> ScreenerResult:
        """
        Screen matches for a specific date.

        Parameters
        ----------
        date : datetime
            The date to screen

        Returns
        -------
        ScreenerResult
            ScreenerResult with ranked predictions
        """
        print(f"🔍 Fetching fixtures for {date.strftime('%Y-%m-%d')}...")
        matches = self._get_filtered_fixtures(date)
        print(f"   Found {len(matches)} matches")

        return self._screen_matches(matches)

    def screen_days(self, days: int = 7) -> ScreenerResult:
        """
        Screen matches for the next N days.

        Parameters
        ----------
        days : int, optional
            Number of days to screen (default: 7)

        Returns
        -------
        ScreenerResult
            ScreenerResult with ranked predictions from all days
        """
        all_matches = []
        today = datetime.now()

        print(f"🔍 Fetching fixtures for the next {days} days...")

        for day_offset in range(1, days + 1):
            date = today + timedelta(days=day_offset)
            try:
                matches = self._get_filtered_fixtures(date)
                all_matches.extend(matches)
                print(f"   {date.strftime('%Y-%m-%d')}: {len(matches)} matches")
            except LivescoreAPIError as e:
                print(f"   {date.strftime('%Y-%m-%d')}: ⚠ Error fetching ({e})")
                continue

        print(f"   Total: {len(all_matches)} matches")

        return self._screen_matches(all_matches)

    def _get_filtered_fixtures(self, date: datetime) -> list[Match]:
        """
        Get fixtures for a date, using optimized API filtering when possible.

        Uses fixtures/list.json endpoint with competition_id filtering when
        filtering by league type (major, minor, gulf, all) for better performance.

        Parameters
        ----------
        date : datetime
            The date to fetch fixtures for

        Returns
        -------
        list[Match]
            List of Match objects
        """
        # If filtering by specific competition IDs, use the optimized endpoint
        if self.config.competition_ids:
            return self.client.get_fixtures_list(
                date=date, competition_ids=list(self.config.competition_ids)
            )

        # If filtering by league type, use competition IDs for that type
        competition_ids = None
        if self.config.major_leagues_only:
            competition_ids = list(MAJOR_LEAGUE_IDS)
        elif self.config.gulf_leagues_only:
            competition_ids = list(GULF_LEAGUE_IDS)
        elif self.config.all_leagues:
            # Combine all supported league IDs
            competition_ids = (
                list(MAJOR_LEAGUE_IDS) + list(MINOR_LEAGUE_IDS) + list(GULF_LEAGUE_IDS)
            )

        if competition_ids:
            # Use optimized endpoint with competition_id filtering
            return self.client.get_fixtures_list(date=date, competition_ids=competition_ids)

        # Fall back to regular endpoint for other filters
        return self.client.get_fixtures_by_date(date)

    def _screen_matches(self, matches: list[Match]) -> ScreenerResult:
        """
        Screen a list of matches and generate predictions.

        Parameters
        ----------
        matches : list[Match]
            List of matches to screen

        Returns
        -------
        ScreenerResult
            ScreenerResult with ranked predictions
        """
        total_scanned = len(matches)

        # Apply filters
        filtered_matches = self._apply_filters(matches)
        print(f"📋 After filtering: {len(filtered_matches)} matches")

        # Enrich matches with statistics if configured
        if self.config.fetch_detailed_stats:
            print("📊 Enriching matches with statistics...")
            filtered_matches = self._enrich_matches(filtered_matches)

        # Generate predictions
        print("🎯 Generating predictions...")
        predictions = []

        for match in filtered_matches:
            try:
                prediction = self.model.predict(match)

                # Apply probability and confidence thresholds
                if (
                    prediction.probability >= self.config.min_probability
                    and prediction.confidence >= self.config.min_confidence
                ):
                    predictions.append(prediction)

            except Exception as e:
                # Skip matches that fail prediction
                print(
                    f"   ⚠ Failed to predict {match.home_team.name} vs {match.away_team.name}: {e}"
                )
                continue

        print(f"✅ Generated {len(predictions)} actionable predictions")

        return ScreenerResult(
            predictions=predictions,
            total_matches_scanned=total_scanned,
            matches_filtered=len(filtered_matches),
            timestamp=datetime.now(),
        )

    def _apply_filters(self, matches: list[Match]) -> list[Match]:
        """Apply configured filters to matches."""
        filtered = matches

        # Filter by major leagues only (highest priority)
        if self.config.major_leagues_only:
            filtered = [m for m in filtered if self._is_major_league(m)]
            if filtered:
                leagues_found = set(f"{m.competition} ({m.country})" for m in filtered)
                print(f"   🏆 Major leagues: {', '.join(sorted(leagues_found))}")
            else:
                print("   ⚠️  No major European league fixtures found in API")
                print("   ℹ️  Try without --major-only to see all available matches")

        # Filter by Persian Gulf leagues only
        elif self.config.gulf_leagues_only:
            filtered = [m for m in filtered if self._is_gulf_league(m)]
            if filtered:
                leagues_found = set(f"{m.competition} ({m.country})" for m in filtered)
                print(f"   🏟️ Persian Gulf leagues: {', '.join(sorted(leagues_found))}")
            else:
                print("   ⚠️  No Persian Gulf league fixtures found in API")
                print(
                    "   ℹ️  Persian Gulf leagues: Saudi Pro League, Qatar Stars League, UAE Pro League"
                )

        # Filter by ALL supported leagues (Major + Minor + Persian Gulf)
        elif self.config.all_leagues:
            filtered = [
                m
                for m in filtered
                if self._is_major_league(m) or self._is_minor_league(m) or self._is_gulf_league(m)
            ]
            if filtered:
                major = [m for m in filtered if self._is_major_league(m)]
                minor = [m for m in filtered if self._is_minor_league(m)]
                gulf = [m for m in filtered if self._is_gulf_league(m)]
                print(
                    f"   🌍 All leagues: {len(major)} Major European + {len(minor)} Minor European + {len(gulf)} Persian Gulf matches"
                )
            else:
                print("   ⚠️  No supported league fixtures found")

        # Filter by specific competition IDs
        elif self.config.competition_ids:
            filtered = [m for m in filtered if m.competition_id in self.config.competition_ids]

        # Filter by countries
        if self.config.countries:
            countries_lower = [c.lower() for c in self.config.countries]
            filtered = [m for m in filtered if m.country.lower() in countries_lower]

        # Filter by competition names
        if self.config.competitions:
            competitions_lower = [c.lower() for c in self.config.competitions]
            filtered = [
                m
                for m in filtered
                if any(comp in m.competition.lower() for comp in competitions_lower)
            ]

        return filtered

    def _is_major_league(self, match: Match) -> bool:
        """
        Check if a match is from one of the major European leagues.

        Uses competition_id for reliable identification, avoiding name-based heuristics.
        """
        # Exclude cup competitions
        if self._is_cup_competition(match):
            return False

        # Check by competition ID (most reliable)
        return match.competition_id in MAJOR_LEAGUE_IDS

    def _is_cup_competition(self, match: Match) -> bool:
        """Check if a match is a cup competition (not a league match)."""
        # Check by competition ID
        if match.competition_id in CUP_COMPETITION_IDS:
            return True

        # Check by competition name patterns
        competition_lower = match.competition.lower()
        if any(pattern in competition_lower for pattern in CUP_NAME_PATTERNS):
            return True

        return False

    def _is_gulf_league(self, match: Match) -> bool:
        """
        Check if a match is from one of the Persian Gulf leagues (Saudi, Qatar, UAE).

        Uses competition_id for reliable identification, avoiding name-based heuristics.
        """
        # Exclude cup competitions
        if self._is_cup_competition(match):
            return False

        # Check by competition ID (most reliable)
        return match.competition_id in GULF_LEAGUE_IDS

    def _is_minor_league(self, match: Match) -> bool:
        """
        Check if a match is from one of the minor European leagues (Belgium, Portugal, Turkey, Netherlands).

        Uses competition_id for reliable identification, avoiding name-based heuristics.
        """
        # Exclude cup competitions
        if self._is_cup_competition(match):
            return False

        # Check by competition ID (most reliable)
        return match.competition_id in MINOR_LEAGUE_IDS

    def _enrich_matches(self, matches: list[Match]) -> list[Match]:
        """
        Enrich matches with additional statistics using parallel requests.
        """
        enriched = []

        def enrich_one(match: Match) -> Match:
            try:
                return self.client.enrich_match_with_stats(match)
            except LivescoreAPIError:
                return match

        # Use thread pool for parallel enrichment
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {executor.submit(enrich_one, match): match for match in matches}

            for i, future in enumerate(as_completed(futures)):
                match = future.result()
                enriched.append(match)

                # Progress indicator
                if (i + 1) % 10 == 0:
                    print(f"   Enriched {i + 1}/{len(matches)} matches...")

        return enriched


def to_central_time(dt: datetime) -> datetime:
    """
    Convert a datetime to Central Time (CST/CDT).

    Parameters
    ----------
    dt : datetime
        Datetime object (assumed to be naive/UTC)

    Returns
    -------
    datetime
        Datetime object in Central Time
    """
    # If datetime is naive, assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    # Convert to Central Time
    central_tz = ZoneInfo("America/Chicago")
    return dt.astimezone(central_tz)


def format_prediction(prediction: BetPrediction, rank: int = 0) -> str:
    """
    Format a prediction for display.

    Parameters
    ----------
    prediction : BetPrediction
        The prediction to format
    rank : int, optional
        Optional rank number to display

    Returns
    -------
    str
        Formatted string representation
    """
    match = prediction.match
    outcome = prediction.recommended_outcome

    # Determine which team to bet on
    if outcome == BetOutcome.HOME_WIN:
        bet_on = match.home_team.name
        bet_against = match.away_team.name
    else:
        bet_on = match.away_team.name
        bet_against = match.home_team.name

    # Build output
    lines = []

    # Header
    if rank > 0:
        lines.append(f"{'=' * 60}")
        lines.append(f"#{rank} BET RECOMMENDATION")
    else:
        lines.append(f"{'=' * 60}")
        lines.append("BET RECOMMENDATION")

    lines.append(f"{'=' * 60}")

    # Confidence Grade based on backtest findings
    best_dc_prob = get_best_double_chance_prob(prediction)
    if best_dc_prob >= 0.80 and prediction.probability >= 0.65:
        grade = "🔥 HIGH VALUE"
    elif best_dc_prob >= 0.75 and prediction.probability >= 0.60:
        grade = "✅ GOOD BET"
    elif best_dc_prob >= 0.70:
        grade = "👍 DECENT"
    else:
        grade = "⚠️ RISKY"

    # Match info with positions
    home_pos = f"({match.home_position})" if match.home_position else ""
    away_pos = f"({match.away_position})" if match.away_position else ""

    # Format: Team Name (Position) vs Team Name (Position)
    home_display = f"{match.home_team.name} {home_pos}".strip()
    away_display = f"{match.away_team.name} {away_pos}".strip()

    lines.append(f"🏟️  {home_display} vs {away_display}  [{grade}]")
    lines.append(f"🏆  {match.competition} ({match.country})")
    # Convert to Central Time for display
    central_time = to_central_time(match.kickoff_time)
    lines.append(f"⏰  {central_time.strftime('%Y-%m-%d %H:%M %Z')}")
    lines.append("")

    # PRIMARY: Double Chance Recommendation (shown first!)
    if prediction.double_chance:
        dc = prediction.double_chance
        best_type, best_prob = dc.best_double_chance

        # Determine which bet type and explain it
        if "1X" in best_type:
            bet_desc = f"{match.home_team.name} wins OR Draw"
            short_bet = "1X"
        elif "X2" in best_type:
            bet_desc = f"{match.away_team.name} wins OR Draw"
            short_bet = "X2"
        else:
            bet_desc = "Either team wins (no draw)"
            short_bet = "12"

        lines.append(f"⭐ RECOMMENDED BET: {short_bet}")
        lines.append(f"   {bet_desc}")
        lines.append(f"   Probability: {best_prob:.1%}")
        lines.append("")

        # Show all double chance options
        lines.append("🎲 ALL DOUBLE CHANCE OPTIONS:")
        home_or_draw_emoji = (
            "🟢" if dc.home_or_draw_prob >= 0.70 else "🟡" if dc.home_or_draw_prob >= 0.60 else "🔴"
        )
        away_or_draw_emoji = (
            "🟢" if dc.away_or_draw_prob >= 0.70 else "🟡" if dc.away_or_draw_prob >= 0.60 else "🔴"
        )
        no_draw_emoji = (
            "🟢" if dc.no_draw_prob >= 0.75 else "🟡" if dc.no_draw_prob >= 0.65 else "🔴"
        )

        lines.append(
            f"   {home_or_draw_emoji} 1X ({match.home_team.name} or Draw): {dc.home_or_draw_prob:.1%}"
        )
        lines.append(
            f"   {away_or_draw_emoji} X2 ({match.away_team.name} or Draw): {dc.away_or_draw_prob:.1%}"
        )
        lines.append(f"   {no_draw_emoji} 12 (No Draw): {dc.no_draw_prob:.1%}")
        lines.append("")

    # SECONDARY: Win bet (for higher risk/reward)
    lines.append(f"💰 WIN BET (Higher Risk): {bet_on.upper()} TO WIN")
    lines.append(f"   Probability: {prediction.probability:.1%}")
    lines.append("")

    # Draw Risk Warning
    if prediction.draw_risk > 0.30:
        lines.append(f"⚠️  DRAW RISK: {prediction.draw_risk:.1%}")
        lines.append("")

    # Factor breakdown
    lines.append("📊 ANALYSIS BREAKDOWN:")
    lines.append(f"   • Form Score: {prediction.form_score:+.2f}")
    lines.append(f"   • Position Score: {prediction.position_score:+.2f}")
    lines.append(f"   • Home Advantage: {prediction.home_advantage_score:+.2f}")
    lines.append(f"   • H2H Score: {prediction.h2h_score:+.2f}")
    if prediction.odds_score != 0:
        lines.append(f"   • Odds Score: {prediction.odds_score:+.2f}")
    # NEW: Enhanced factor scores
    if prediction.goal_score != 0:
        lines.append(f"   • Goals (Attack/Defense): {prediction.goal_score:+.2f}")
    if prediction.venue_form_score != 0:
        lines.append(f"   • Venue Form: {prediction.venue_form_score:+.2f}")
    if prediction.defense_score != 0:
        lines.append(f"   • Defense (Clean Sheets): {prediction.defense_score:+.2f}")
    if prediction.momentum_score != 0:
        lines.append(f"   • Momentum (HT Lead/Consistency): {prediction.momentum_score:+.2f}")
    lines.append("")

    # Reasoning (filtered for key points)
    key_reasons = [r for r in prediction.reasoning if not r.startswith("🎲")]
    if key_reasons:
        lines.append("📝 KEY INSIGHTS:")
        for reason in key_reasons[:5]:  # Limit to 5 key reasons
            lines.append(f"   {reason}")

    return "\n".join(lines)


def format_summary(result: ScreenerResult) -> str:
    """
    Format a summary of screener results.

    Parameters
    ----------
    result : ScreenerResult
        The screener result to summarize

    Returns
    -------
    str
        Formatted summary string
    """
    lines = [
        "=" * 60,
        "📊 SCREENING SUMMARY",
        "=" * 60,
        f"🔍 Total matches scanned: {result.total_matches_scanned}",
        f"📋 Matches after filtering: {result.matches_filtered}",
        f"✅ Actionable predictions: {len(result.predictions)}",
        f"🏠 Home win predictions: {len(result.get_home_wins())}",
        f"✈️  Away win predictions: {len(result.get_away_wins())}",
        f"⏰ Screened at: {to_central_time(result.timestamp).strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "=" * 60,
    ]

    return "\n".join(lines)
