"""
Betting screener for finding and ranking soccer betting opportunities.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta

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
        return sorted(
            self.predictions, key=lambda p: get_best_double_chance_prob(p), reverse=True
        )

    @property
    def top_bets_by_win(self) -> list[BetPrediction]:
        """Get predictions sorted by win probability (highest first)."""
        return sorted(self.predictions, key=lambda p: p.probability, reverse=True)

    def get_top_k(self, k: int) -> list[BetPrediction]:
        """Get top K betting opportunities by double chance."""
        return self.top_bets[:k]

    def get_home_wins(self) -> list[BetPrediction]:
        """Get all predictions recommending home win."""
        return [
            p for p in self.predictions if p.recommended_outcome == BetOutcome.HOME_WIN
        ]

    def get_away_wins(self) -> list[BetPrediction]:
        """Get all predictions recommending away win."""
        return [
            p for p in self.predictions if p.recommended_outcome == BetOutcome.AWAY_WIN
        ]


class BettingScreener:
    """
    Main screener class for finding betting opportunities.

    Usage:
        screener = BettingScreener()
        result = screener.screen_tomorrow()
        for bet in result.get_top_k(10):
            print(bet)
    """

    def __init__(
        self,
        config: ScreenerConfig | None = None,
        api_client: LivescoreClient | None = None,
        model: BettingModel | None = None,
    ):
        """
        Initialize the betting screener.

        Args:
            config: Screener configuration
            api_client: Livescore API client (created if not provided)
            model: Betting model (created if not provided)
        """
        self.config = config or ScreenerConfig()
        self.client = api_client or LivescoreClient()
        self.model = model or BettingModel(min_confidence=self.config.min_confidence)

    def screen_tomorrow(self) -> ScreenerResult:
        """
        Screen tomorrow's matches for betting opportunities.

        Returns:
            ScreenerResult with ranked predictions
        """
        print("🔍 Fetching tomorrow's fixtures...")
        matches = self.client.get_tomorrow_fixtures()
        print(f"   Found {len(matches)} matches")

        return self._screen_matches(matches)

    def screen_date(self, date: datetime) -> ScreenerResult:
        """
        Screen matches for a specific date.

        Args:
            date: The date to screen

        Returns:
            ScreenerResult with ranked predictions
        """
        print(f"🔍 Fetching fixtures for {date.strftime('%Y-%m-%d')}...")
        matches = self.client.get_fixtures_by_date(date)
        print(f"   Found {len(matches)} matches")

        return self._screen_matches(matches)

    def screen_days(self, days: int = 7) -> ScreenerResult:
        """
        Screen matches for the next N days.

        Args:
            days: Number of days to screen (default: 7)

        Returns:
            ScreenerResult with ranked predictions from all days
        """
        all_matches = []
        today = datetime.now()

        print(f"🔍 Fetching fixtures for the next {days} days...")

        for day_offset in range(1, days + 1):
            date = today + timedelta(days=day_offset)
            try:
                matches = self.client.get_fixtures_by_date(date)
                all_matches.extend(matches)
                print(f"   {date.strftime('%Y-%m-%d')}: {len(matches)} matches")
            except LivescoreAPIError as e:
                print(f"   {date.strftime('%Y-%m-%d')}: ⚠ Error fetching ({e})")
                continue

        print(f"   Total: {len(all_matches)} matches")

        return self._screen_matches(all_matches)

    def _screen_matches(self, matches: list[Match]) -> ScreenerResult:
        """
        Screen a list of matches and generate predictions.

        Args:
            matches: List of matches to screen

        Returns:
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

        # Filter by ALL supported leagues (Major + Persian Gulf)
        elif self.config.all_leagues:
            filtered = [
                m
                for m in filtered
                if self._is_major_league(m) or self._is_gulf_league(m)
            ]
            if filtered:
                major = [m for m in filtered if self._is_major_league(m)]
                gulf = [m for m in filtered if self._is_gulf_league(m)]
                print(
                    f"   🌍 All leagues: {len(major)} Major European + {len(gulf)} Persian Gulf matches"
                )
            else:
                print("   ⚠️  No supported league fixtures found")

        # Filter by specific competition IDs
        elif self.config.competition_ids:
            filtered = [
                m for m in filtered if m.competition_id in self.config.competition_ids
            ]

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
        """Check if a match is from one of the major European leagues."""
        # Exclude cup competitions
        if self._is_cup_competition(match):
            return False

        competition_lower = match.competition.lower()
        country_lower = match.country.lower()  # Note: This is often the stadium name

        # German Bundesliga (exact match to avoid 2nd Bundesliga, etc.)
        if competition_lower == "bundesliga":
            return True

        # Spanish La Liga (LaLiga Santander, La Liga, Primera Division)
        if "laliga" in competition_lower or "la liga" in competition_lower:
            # Exclude other countries' La Liga
            if "santander" in competition_lower or "primera" in competition_lower:
                return True
            # Check for Spanish stadiums
            spanish_indicators = [
                "bernab",
                "camp nou",
                "mestalla",
                "sanchez pizjuan",
                "ramón sánchez",
                "estadio",
                "san mam",
                "coliseum",
            ]
            if any(ind in country_lower for ind in spanish_indicators):
                return True

        # Italian Serie A (exact match to avoid Serie B, Serie C, Brazilian Serie A)
        if competition_lower == "serie a":
            # Check for Italian stadiums
            italian_indicators = [
                "stadio",
                "olimpico",
                "san siro",
                "juventus",
                "maradona",
                "giuseppe",
                "artemio",
                "allianz stadium",
                "sinigaglia",
            ]
            if any(ind in country_lower for ind in italian_indicators):
                return True

        # French Ligue 1 (exact match)
        if competition_lower == "ligue 1":
            # Check for French stadiums
            french_indicators = [
                "parc des princes",
                "velodrome",
                "groupama",
                "roazhon",
                "stade",
                "meinau",
                "allianz riviera",
                "bollaert",
            ]
            if any(ind in country_lower for ind in french_indicators):
                return True

        # English Premier League (need to filter out other Premier Leagues)
        if competition_lower == "premier league":
            # Known English Premier League stadiums
            english_stadiums = [
                "old trafford",
                "anfield",
                "emirates",
                "stamford bridge",
                "etihad",
                "tottenham",
                "villa park",
                "st james",
                "goodison",
                "king power",
                "london stadium",
                "city ground",
                "molineux",
                "selhurst",
                "craven cottage",
                "gtech",
                "amex",
                "vitality",
                "carrow",
                "elland",
                "bramall",
                "the hawthorns",
                "falmer",
                "portman",
                "turf moor",
            ]
            if any(stadium in country_lower for stadium in english_stadiums):
                return True

            # Also check for well-known English teams in home team name
            english_teams = [
                "manchester united",
                "manchester city",
                "liverpool",
                "chelsea",
                "arsenal",
                "tottenham",
                "newcastle",
                "aston villa",
                "west ham",
                "brighton",
                "crystal palace",
                "brentford",
                "fulham",
                "bournemouth",
                "nottingham forest",
                "wolves",
                "wolverhampton",
                "everton",
                "leicester",
                "leeds",
            ]
            home_lower = match.home_team.name.lower()
            if any(team in home_lower for team in english_teams):
                return True

        return False

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
        """Check if a match is from one of the Persian Gulf leagues (Saudi, Qatar, UAE)."""
        # Exclude cup competitions
        if self._is_cup_competition(match):
            return False

        competition_lower = match.competition.lower()
        country_lower = match.country.lower()  # Often contains stadium name
        home_lower = match.home_team.name.lower() if match.home_team else ""

        # Check competition ID first (most reliable)
        if match.competition_id in GULF_LEAGUE_IDS:
            return True

        # Saudi Pro League indicators
        saudi_teams = [
            "al hilal",
            "al nassr",
            "al ahli",
            "al ittihad",
            "al shabab",
            "al fateh",
            "al feiha",
            "al taawon",
            "al raed",
            "damac",
            "al ettifaq",
            "al khaleej",
            "al riyadh",
            "al hazm",
            "al okhdood",
            "neom",
            "al qadasiya",
            "al kholood",
            "dhamk",
        ]
        saudi_stadiums = [
            "king fahd",
            "king abdullah",
            "prince faisal",
            "prince sultan",
            "mrsool park",
            "king saud",
            "jeddah",
            "riyadh",
        ]

        if any(team in home_lower for team in saudi_teams):
            return True
        if any(stadium in country_lower for stadium in saudi_stadiums):
            return True
        if "premier league" in competition_lower and any(
            s in country_lower for s in saudi_stadiums
        ):
            return True

        # Qatar Stars League indicators
        qatar_teams = [
            "al sadd",
            "al duhail",
            "al rayyan",
            "al arabi",
            "al gharafa",
            "al wakrah",
            "al ahli doha",
            "qatar sc",
            "al shamal",
            "umm salal",
            "al sailiya",
            "muaither",
            "al khor",
        ]
        qatar_stadiums = [
            "khalifa international",
            "al janoub",
            "education city",
            "lusail",
            "ahmad bin ali",
            "al thumama",
            "jassim bin hamad",
            "doha",
        ]

        if "qatar" in competition_lower:
            return True
        if any(team in home_lower for team in qatar_teams):
            return True
        if any(stadium in country_lower for stadium in qatar_stadiums):
            return True

        # UAE Pro League indicators
        uae_teams = [
            "al ain",
            "al wasl",
            "al jazira",
            "shabab al ahli",
            "al nasr dubai",
            "al wahda",
            "baniyas",
            "ajman",
            "al sharjah",
            "emirates club",
            "al dhafra",
            "hatta",
            "khor fakkan",
            "kalba",
            "al ittihad kalba",
        ]
        uae_stadiums = [
            "hazza bin zayed",
            "mohammed bin zayed",
            "al nahyan",
            "rashid",
            "zabeel",
            "sharjah",
            "dubai",
            "abu dhabi",
        ]

        if "uae" in competition_lower or "emirates" in competition_lower:
            return True
        if any(team in home_lower for team in uae_teams):
            return True
        if any(stadium in country_lower for stadium in uae_stadiums):
            return True

        return False

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


def format_prediction(prediction: BetPrediction, rank: int = 0) -> str:
    """
    Format a prediction for display.

    Args:
        prediction: The prediction to format
        rank: Optional rank number to display

    Returns:
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
    lines.append(f"⏰  {match.kickoff_time.strftime('%Y-%m-%d %H:%M')}")
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
            "🟢"
            if dc.home_or_draw_prob >= 0.70
            else "🟡"
            if dc.home_or_draw_prob >= 0.60
            else "🔴"
        )
        away_or_draw_emoji = (
            "🟢"
            if dc.away_or_draw_prob >= 0.70
            else "🟡"
            if dc.away_or_draw_prob >= 0.60
            else "🔴"
        )
        no_draw_emoji = (
            "🟢"
            if dc.no_draw_prob >= 0.75
            else "🟡"
            if dc.no_draw_prob >= 0.65
            else "🔴"
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
        lines.append(
            f"   • Momentum (HT Lead/Consistency): {prediction.momentum_score:+.2f}"
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

    Args:
        result: The screener result to summarize

    Returns:
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
        f"⏰ Screened at: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
    ]

    return "\n".join(lines)
