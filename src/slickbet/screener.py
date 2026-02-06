"""
Betting screener for finding and ranking soccer betting opportunities.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
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
    "1. hnl",
    "hnl",
    "croatia",
    "ekstraklasa",
    "poland",
    "premiership",
    "scotland",
    "super league",
    "greece",
]

# Competition IDs for minor European leagues
MINOR_LEAGUE_IDS = {
    "68": "🇧🇪 Belgian Pro League",
    "8": "🇵🇹 Primeira Liga",
    "6": "🇹🇷 Super Lig",
    "196": "🇳🇱 Eredivisie",
    "17": "🇭🇷 1. HNL",
    "60": "🇵🇱 Ekstraklasa",
    "75": "🏴󠁧󠁢󠁳󠁣󠁴󠁿 Premiership",
    "9": "🇬🇷 Super League",
}

# Asia leagues (Saudi Pro League, Australia, Japan)
ASIA_LEAGUE_NAMES = [
    "saudi",
    "pro league",  # Saudi Pro League often listed as just "Pro League" or "Premier League"
    "hyundai a-league",
    "a-league",
    "australia",
    "j. league",
    "j league",
    "japan",
]

# Competition IDs for Asia leagues
ASIA_LEAGUE_IDS = {
    "313": "🇸🇦 Saudi Pro League",
    "67": "🇦🇺 Hyundai A-League",
    "28": "🇯🇵 J. League",
}

# Americas leagues (Argentina, Brazil, Mexico)
AMERICAS_LEAGUE_NAMES = [
    "liga professional",
    "argentina",
    "serie a",  # Brazil Serie A
    "brazil",
    "liga mx",
    "mexico",
]

# Competition IDs for Americas leagues
AMERICAS_LEAGUE_IDS = {
    "23": "🇦🇷 Liga Professional",
    "24": "🇧🇷 Serie A",
    "45": "🇲🇽 Liga MX",
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
    "17": "🇭🇷 1. HNL",
    "60": "🇵🇱 Ekstraklasa",
    "75": "🏴󠁧󠁢󠁳󠁣󠁴󠁿 Premiership",
    "9": "🇬🇷 Super League",
    # Asia
    "313": "🇸🇦 Saudi Pro League",
    "67": "🇦🇺 Hyundai A-League",
    "28": "🇯🇵 J. League",
    # Americas
    "23": "🇦🇷 Liga Professional",
    "24": "🇧🇷 Serie A",
    "45": "🇲🇽 Liga MX",
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

    # Only show Asia leagues (Saudi Pro League, Australia, J. League Japan)
    asia_leagues_only: bool = False

    # Only show Americas leagues (Argentina, Brazil, Mexico)
    americas_leagues_only: bool = False

    # Show all supported leagues (Major European + Minor European + Asia + Americas)
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
        Screen tomorrow's matches (next calendar day, all fixtures that day).

        Uses calendar-day logic so results are invariant of run time:
        e.g. running at 8am or 11pm both get the same "tomorrow" fixtures.
        """
        tomorrow_date = date.today() + timedelta(days=1)
        target = datetime.combine(tomorrow_date, time.min)
        print("🔍 Fetching tomorrow's fixtures...")
        matches = self._get_filtered_fixtures(target)
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
        Screen matches for the next N calendar days (not 24-hour windows).

        Uses calendar-day logic so results are invariant of run time;
        each day includes all games that kick off that day in Central time.

        Parameters
        ----------
        days : int, optional
            Number of calendar days to screen (default: 7)

        Returns
        -------
        ScreenerResult
            ScreenerResult with ranked predictions from all days
        """
        all_matches = []
        today_date = date.today()

        print(f"🔍 Fetching fixtures for the next {days} days...")

        for day_offset in range(1, days + 1):
            day_date = today_date + timedelta(days=day_offset)
            target = datetime.combine(day_date, time.min)
            try:
                matches = self._get_filtered_fixtures(target)
                all_matches.extend(matches)
                print(f"   {day_date.strftime('%Y-%m-%d')}: {len(matches)} matches")
            except LivescoreAPIError as e:
                print(f"   {day_date.strftime('%Y-%m-%d')}: ⚠ Error fetching ({e})")
                continue

        print(f"   Total: {len(all_matches)} matches")

        return self._screen_matches(all_matches)

    def _get_filtered_fixtures(self, date: datetime) -> list[Match]:
        """
        Get fixtures for a calendar day, using optimized API filtering when possible.

        The API returns fixtures by UTC date. Late local-time games (e.g. 21:06 CST)
        can be 03:06 UTC next day, so we fetch this date and the next UTC day then
        filter by calendar day in Central time so --days=1 and day-one of --days=2
        show the same games.

        Parameters
        ----------
        date : datetime
            The calendar day to fetch fixtures for (local day, e.g. "tomorrow")

        Returns
        -------
        list[Match]
            List of Match objects whose kickoff falls on that day in Central time
        """
        target_date = date.date() if hasattr(date, "date") else date
        next_date = target_date + timedelta(days=1)
        date_dt = datetime.combine(target_date, time.min)
        next_dt = datetime.combine(next_date, time.min)

        def fetch(dt: datetime) -> list[Match]:
            if self.config.competition_ids:
                return self.client.get_fixtures_list(
                    date=dt, competition_ids=list(self.config.competition_ids)
                )
            competition_ids = None
            if self.config.major_leagues_only:
                competition_ids = list(MAJOR_LEAGUE_IDS)
            elif self.config.asia_leagues_only:
                competition_ids = list(ASIA_LEAGUE_IDS)
            elif self.config.americas_leagues_only:
                competition_ids = list(AMERICAS_LEAGUE_IDS)
            elif self.config.all_leagues:
                competition_ids = (
                    list(MAJOR_LEAGUE_IDS)
                    + list(MINOR_LEAGUE_IDS)
                    + list(ASIA_LEAGUE_IDS)
                    + list(AMERICAS_LEAGUE_IDS)
                )
            if competition_ids:
                return self.client.get_fixtures_list(
                    date=dt, competition_ids=competition_ids
                )
            return self.client.get_fixtures_by_date(dt)

        matches_today = fetch(date_dt)
        matches_next = fetch(next_dt)
        seen_ids: set[str] = set()
        merged: list[Match] = []
        for m in matches_today + matches_next:
            if m.id in seen_ids:
                continue
            seen_ids.add(m.id)
            merged.append(m)
        return [
            m
            for m in merged
            if to_central_time(m.kickoff_time).date() == target_date
        ]

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
        dropped_low_prob: list[tuple[BetPrediction, str]] = []
        dropped_low_conf: list[tuple[BetPrediction, str]] = []

        for match in filtered_matches:
            try:
                prediction = self.model.predict(match)

                # Apply probability and confidence thresholds
                if (
                    prediction.probability >= self.config.min_probability
                    and prediction.confidence >= self.config.min_confidence
                ):
                    predictions.append(prediction)
                else:
                    if prediction.probability < self.config.min_probability:
                        dropped_low_prob.append(
                            (prediction, f"prob={prediction.probability:.1%} < {self.config.min_probability:.2f}")
                        )
                    if prediction.confidence < self.config.min_confidence:
                        dropped_low_conf.append(
                            (prediction, f"conf={prediction.confidence:.2f} < {self.config.min_confidence:.2f}")
                        )

            except Exception as e:
                # Skip matches that fail prediction
                print(
                    f"   ⚠ Failed to predict {match.home_team.name} vs {match.away_team.name}: {e}"
                )
                continue

        print(f"✅ Generated {len(predictions)} actionable predictions")
        # Log dropped-by-threshold summary and list
        if dropped_low_prob or dropped_low_conf:
            # Dedupe: a match can be in both lists; count unique matches dropped
            dropped_matches: dict[str, tuple[BetPrediction, list[str]]] = {}
            for pred, reason in dropped_low_prob:
                key = f"{pred.match.home_team.name} vs {pred.match.away_team.name}"
                dropped_matches.setdefault(key, (pred, []))[1].append(reason)
            for pred, reason in dropped_low_conf:
                key = f"{pred.match.home_team.name} vs {pred.match.away_team.name}"
                dropped_matches.setdefault(key, (pred, []))[1].append(reason)
            n_dropped = len(dropped_matches)
            print(f"   📉 Dropped {n_dropped} match(es) below --min-prob/--min-conf:")
            for key, (pred, reasons) in sorted(dropped_matches.items(), key=lambda x: -get_best_double_chance_prob(x[1][0]))[:15]:
                prob_str = f"prob={pred.probability:.1%}"
                conf_str = f"conf={pred.confidence:.2f}"
                print(f"      • {key}: {prob_str}, {conf_str} ({'; '.join(reasons)})")
            if n_dropped > 15:
                print(f"      ... and {n_dropped - 15} more (lower ranked)")

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

        # Filter by Asia leagues only
        elif self.config.asia_leagues_only:
            filtered = [m for m in filtered if self._is_asia_league(m)]
            if filtered:
                leagues_found = set(f"{m.competition} ({m.country})" for m in filtered)
                print(f"   🏟️ Asia leagues: {', '.join(sorted(leagues_found))}")
            else:
                print("   ⚠️  No Asia league fixtures found in API")
                print(
                    "   ℹ️  Asia leagues: Saudi Pro League, Hyundai A-League (Australia), "
                    "J. League (Japan)"
                )

        # Filter by Americas leagues only
        elif self.config.americas_leagues_only:
            filtered = [m for m in filtered if self._is_americas_league(m)]
            if filtered:
                leagues_found = set(f"{m.competition} ({m.country})" for m in filtered)
                print(f"   🌎 Americas leagues: {', '.join(sorted(leagues_found))}")
            else:
                print("   ⚠️  No Americas league fixtures found in API")
                print(
                    "   ℹ️  Americas leagues: Liga Professional (Argentina), Serie A (Brazil), Liga MX (Mexico)"
                )

        # Filter by ALL supported leagues (Major + Minor + Asia + Americas)
        elif self.config.all_leagues:
            filtered = [
                m
                for m in filtered
                if self._is_major_league(m)
                or self._is_minor_league(m)
                or self._is_asia_league(m)
                or self._is_americas_league(m)
            ]
            if filtered:
                major = [m for m in filtered if self._is_major_league(m)]
                minor = [m for m in filtered if self._is_minor_league(m)]
                asia = [m for m in filtered if self._is_asia_league(m)]
                americas = [m for m in filtered if self._is_americas_league(m)]
                print(
                    f"   🌍 All leagues: {len(major)} Major European + {len(minor)} Minor European + {len(asia)} Asia + {len(americas)} Americas matches"
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

    def _is_americas_league(self, match: Match) -> bool:
        """
        Check if a match is from one of the Americas leagues (Argentina, Brazil, Mexico).

        Uses competition_id for reliable identification, avoiding name-based heuristics.
        """
        # Exclude cup competitions
        if self._is_cup_competition(match):
            return False

        # Check by competition ID (most reliable)
        return match.competition_id in AMERICAS_LEAGUE_IDS

    def _is_asia_league(self, match: Match) -> bool:
        """
        Check if a match is from one of the Asia leagues (Saudi, Australia, Japan).

        Uses competition_id for reliable identification, avoiding name-based heuristics.
        """
        # Exclude cup competitions
        if self._is_cup_competition(match):
            return False

        # Check by competition ID (most reliable)
        return match.competition_id in ASIA_LEAGUE_IDS

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

    # Match statistics indicator
    if prediction.match_stats_used:
        home_stats = match.home_performance.matches_with_stats if match.home_performance else 0
        away_stats = match.away_performance.matches_with_stats if match.away_performance else 0
        lines.append(
            f"📊 Match Statistics: ✅ Used (Home: {home_stats}, Away: {away_stats} matches)"
        )
    else:
        # Show why statistics weren't used
        if match.home_performance and match.away_performance:
            home_stats = match.home_performance.matches_with_stats
            away_stats = match.away_performance.matches_with_stats
            if home_stats == 0 and away_stats == 0:
                lines.append(
                    "📊 Match Statistics: ❌ Not available (no historical match statistics found)"
                )
            elif home_stats < 1 or away_stats < 1:
                lines.append(
                    f"📊 Match Statistics: ❌ Insufficient data (Home: {home_stats}, Away: {away_stats} matches, need ≥1 each)"
                )
            else:
                lines.append(
                    f"📊 Match Statistics: ❌ Not used (Home: {home_stats}, Away: {away_stats} matches, but score is 0)"
                )
        else:
            lines.append("📊 Match Statistics: ❌ Not available (no performance data)")
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
    # Match stats - show even if 0 to indicate status
    if prediction.match_stats_used:
        lines.append(
            f"   • Match Stats (Possession/Attacks): {prediction.match_stats_score:+.2f} ✅"
        )
    if prediction.xg_score != 0:
        lines.append(f"   • xG (Expected Goals): {prediction.xg_score:+.2f}")
    if prediction.match_stats_used is False and match.home_performance and match.away_performance:
        # Show why it wasn't used
        home_stats = match.home_performance.matches_with_stats
        away_stats = match.away_performance.matches_with_stats
        if home_stats < 1 or away_stats < 1:
            lines.append(
                f"   • Match Stats: ❌ Insufficient data (Home: {home_stats}, Away: {away_stats} matches, need ≥1 each)"
            )
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
