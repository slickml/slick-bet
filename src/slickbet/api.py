"""
Livescore API client for fetching soccer matches and statistics.
"""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import requests


@dataclass
class Team:
    """Represents a soccer team."""

    id: str
    name: str
    country: str | None = None


@dataclass
class Odds:
    """Represents betting odds for a match."""

    home_win: float | None = None  # "1" in API
    draw: float | None = None  # "X" in API
    away_win: float | None = None  # "2" in API

    @property
    def has_odds(self) -> bool:
        """Check if any odds are available."""
        return any(o is not None for o in [self.home_win, self.draw, self.away_win])

    def implied_probability(self, outcome: str) -> float | None:
        """
        Calculate implied probability from odds.

        Parameters
        ----------
        outcome : str
            "home", "draw", or "away"

        Returns
        -------
        float or None
            Implied probability (0-1) or None if odds not available
        """
        odds_map = {"home": self.home_win, "draw": self.draw, "away": self.away_win}
        odds = odds_map.get(outcome)
        if odds and odds > 0:
            return 1 / odds
        return None


@dataclass
class MatchScores:
    """Match scores at different periods."""

    final: str | None = None  # e.g., "2 - 1"
    half_time: str | None = None  # e.g., "1 - 0"
    full_time: str | None = None  # e.g., "2 - 1"
    extra_time: str | None = None  # e.g., "3 - 2"
    penalties: str | None = None  # e.g., "5 - 4"

    def parse_score(self, score_str: str | None) -> tuple[int, int] | None:
        """Parse score string to (home, away) tuple."""
        if not score_str or not isinstance(score_str, str):
            return None
        try:
            parts = score_str.replace(" ", "").split("-")
            if len(parts) == 2:
                return (int(parts[0]), int(parts[1]))
        except (ValueError, AttributeError):
            pass
        return None

    @property
    def final_tuple(self) -> tuple[int, int] | None:
        """Get final score as (home, away) tuple."""
        return self.parse_score(self.final or self.full_time)


@dataclass
class MatchOutcome:
    """
    Match outcomes (betting results) at different periods.

    Values are "1" (home win), "X" (draw), or "2" (away win).
    """

    half_time: str | None = None
    full_time: str | None = None
    extra_time: str | None = None
    penalties: str | None = None


@dataclass
class HistoricalMatch:
    """
    A completed historical match with scores and outcomes.

    Per https://live-score-api.com/documentation/reference/15/football_data_history_matches
    """

    id: str
    fixture_id: str | None
    home_team: Team
    away_team: Team
    competition: str
    competition_id: str
    country: str | None
    date: datetime
    status: str
    scores: MatchScores
    outcomes: MatchOutcome
    pre_odds: Odds | None = None
    location: str | None = None
    round: str | None = None

    @property
    def home_score(self) -> int | None:
        """Get home team final score."""
        result = self.scores.final_tuple
        return result[0] if result else None

    @property
    def away_score(self) -> int | None:
        """Get away team final score."""
        result = self.scores.final_tuple
        return result[1] if result else None

    @property
    def result(self) -> str | None:
        """Get match result: 'H' (home win), 'A' (away win), 'D' (draw)."""
        outcome = self.outcomes.full_time
        if outcome == "1":
            return "H"
        elif outcome == "2":
            return "A"
        elif outcome == "X":
            return "D"
        return None


@dataclass
class MatchStatistics:
    """
    Match statistics from the API.

    Per https://live-score-api.com/documentation/reference/23/match-statistics
    Statistics are only available for live/completed matches, not fixtures.
    Values are "home:away" format (e.g., "48:52" for possession).
    """

    possession: tuple[int, int] | None = None  # Ball possession %
    shots_on_target: tuple[int, int] | None = None
    shots_off_target: tuple[int, int] | None = None
    corners: tuple[int, int] | None = None
    fouls: tuple[int, int] | None = None
    yellow_cards: tuple[int, int] | None = None
    red_cards: tuple[int, int] | None = None
    offsides: tuple[int, int] | None = None
    saves: tuple[int, int] | None = None
    attacks: tuple[int, int] | None = None
    dangerous_attacks: tuple[int, int] | None = None

    @staticmethod
    def parse_stat(value: str | None) -> tuple[int, int] | None:
        """Parse 'home:away' format to tuple."""
        if not value or not isinstance(value, str):
            return None
        try:
            parts = value.split(":")
            if len(parts) == 2:
                return (int(parts[0]), int(parts[1]))
        except (ValueError, AttributeError):
            pass
        return None


@dataclass
class TeamPerformanceStats:
    """
    Detailed team performance statistics from recent matches.
    Used to improve betting predictions with goal-based metrics.

    Based on: https://live-score-api.com/documentation/reference/27/getting-teams-last-matches
    """

    team_id: str
    matches_analyzed: int = 0

    # Goals statistics
    goals_scored: int = 0
    goals_conceded: int = 0

    # Calculated metrics
    goals_per_game: float = 0.0
    goals_conceded_per_game: float = 0.0
    goal_difference: int = 0

    # Clean sheets (games without conceding)
    clean_sheets: int = 0
    clean_sheet_rate: float = 0.0

    # Scoring consistency (games where they scored)
    games_scored: int = 0
    scoring_rate: float = 0.0

    # Home/Away specific form
    home_games: int = 0
    home_wins: int = 0
    home_win_rate: float = 0.0

    away_games: int = 0
    away_wins: int = 0
    away_win_rate: float = 0.0

    # Points per game
    total_points: int = 0
    points_per_game: float = 0.0

    # NEW: First half performance (from outcomes.half_time)
    ht_wins: int = 0  # Leading at half time
    ht_draws: int = 0  # Level at half time
    ht_losses: int = 0  # Trailing at half time
    ht_lead_rate: float = 0.0  # % of games leading at HT

    # NEW: Second half improvement / comeback ability
    comebacks: int = 0  # Trailing at HT but won/drew
    collapses: int = 0  # Leading at HT but lost/drew
    comeback_rate: float = 0.0

    # NEW: Consistency metrics
    wins: int = 0
    draws: int = 0
    losses: int = 0
    win_rate: float = 0.0


@dataclass
class Match:
    """Represents a soccer match."""

    id: str
    home_team: Team
    away_team: Team
    competition: str
    competition_id: str
    country: str
    kickoff_time: datetime
    status: str
    home_score: int | None = None
    away_score: int | None = None

    # Pre-match odds from bookmakers
    pre_odds: Odds | None = None

    # Statistics for betting analysis
    home_form: str | None = None  # e.g., "WWDLW"
    away_form: str | None = None
    home_position: int | None = None
    away_position: int | None = None
    head_to_head: dict | None = None

    # NEW: Detailed performance statistics
    home_performance: TeamPerformanceStats | None = None
    away_performance: TeamPerformanceStats | None = None

    # Live/post-match statistics (only available after match starts)
    statistics: MatchStatistics | None = None


class LivescoreAPIError(Exception):
    """Custom exception for Livescore API errors."""

    pass


class APIEndpoint(str, Enum):
    """Enumeration of Livescore API endpoints."""

    FIXTURES_MATCHES = "fixtures/matches.json"
    FIXTURES_LIST = "fixtures/list.json"
    COMPETITIONS_LIST = "competitions/list.json"
    COUNTRIES_LIST = "countries/list.json"
    LEAGUES_TABLE = "leagues/table.json"
    TEAMS_MATCHES = "teams/matches.json"
    TEAMS_HEAD2HEAD = "teams/head2head.json"
    SCORES_MATCH_STATS = "scores/match_stats.json"
    MATCHES_HISTORY = "matches/history.json"


class LivescoreClient:
    """
    Client for interacting with the Livescore API.

    Uses LIVESCORE_API_KEY and LIVESCORE_API_SECRET environment variables.
    """

    BASE_URL = "https://livescore-api.com/api-client"

    def __init__(self, api_key: str | None = None, api_secret: str | None = None):
        """
        Initialize the Livescore API client.

        Parameters
        ----------
        api_key : str or None, optional
            API key (defaults to LIVESCORE_API_KEY env var)
        api_secret : str or None, optional
            API secret (defaults to LIVESCORE_API_SECRET env var)
        """
        self.api_key = api_key or os.environ.get("LIVESCORE_API_KEY")
        self.api_secret = api_secret or os.environ.get("LIVESCORE_API_SECRET")

        if not self.api_key or not self.api_secret:
            raise LivescoreAPIError(
                "API credentials not found. Set LIVESCORE_API_KEY and "
                "LIVESCORE_API_SECRET environment variables."
            )

        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "User-Agent": "SlickBet/1.0"})

    def _make_request(self, endpoint: APIEndpoint | str, params: dict | None = None) -> dict:
        """
        Make an authenticated request to the API.

        Parameters
        ----------
        endpoint : APIEndpoint or str
            API endpoint (APIEndpoint enum or string)
        params : dict or None, optional
            Additional query parameters

        Returns
        -------
        dict
            JSON response as dictionary
        """
        # Convert enum to string if needed
        endpoint_str = endpoint.value if isinstance(endpoint, APIEndpoint) else endpoint
        url = f"{self.BASE_URL}/{endpoint_str}"

        # Build request parameters with authentication
        request_params = {
            "key": self.api_key,
            "secret": self.api_secret,
        }

        if params:
            request_params.update(params)

        try:
            response = self.session.get(url, params=request_params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Check for API-level errors
            if isinstance(data, dict) and not data.get("success", True):
                error_obj = data.get("error", {})
                if isinstance(error_obj, dict):
                    error_msg = error_obj.get("message", "Unknown API error")
                elif isinstance(error_obj, str):
                    error_msg = error_obj
                else:
                    error_msg = str(error_obj)
                raise LivescoreAPIError(f"API error: {error_msg}")

            return data

        except requests.exceptions.RequestException as e:
            raise LivescoreAPIError(f"Request failed: {e}")

    def _safe_get_nested(self, data: dict, *keys: str, default: Any = None) -> Any:
        """
        Safely get nested values from a dictionary.

        Handles cases where intermediate values are not dicts.
        """
        result = data
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key, default)
            else:
                return default
        return result

    def get_fixtures_by_date(
        self,
        date: datetime,
        competition_id: str | None = None,
        fetch_all_pages: bool = True,
    ) -> list[Match]:
        """
        Get all fixtures for a specific date.

        Parameters
        ----------
        date : datetime
            The date to fetch fixtures for
        competition_id : str or None, optional
            Optional competition ID to filter by
        fetch_all_pages : bool, optional
            Whether to fetch all pages (default: True)

        Returns
        -------
        list[Match]
            List of Match objects
        """
        date_str = date.strftime("%Y-%m-%d")
        all_matches = []
        page = 1
        max_pages = 10  # Safety limit

        while page <= max_pages:
            params = {"date": date_str, "page": page}
            if competition_id:
                params["competition_id"] = competition_id

            data = self._make_request(APIEndpoint.FIXTURES_MATCHES, params=params)

            fixtures = self._safe_get_nested(data, "data", "fixtures", default=[])

            # Handle case where fixtures might be at different path
            if not fixtures:
                fixtures = self._safe_get_nested(data, "data", default=[])
                if not isinstance(fixtures, list):
                    fixtures = []

            if not fixtures:
                break  # No more fixtures

            for fixture in fixtures:
                if not isinstance(fixture, dict):
                    continue
                try:
                    match = self._parse_fixture(fixture)
                    all_matches.append(match)
                except (KeyError, ValueError, TypeError):
                    # Skip malformed fixtures
                    continue

            # Check if there's a next page
            next_page = self._safe_get_nested(data, "data", "next_page", default=False)
            if not next_page or not fetch_all_pages:
                break

            page += 1

        return all_matches

    def get_tomorrow_fixtures(self) -> list[Match]:
        """
        Get all fixtures scheduled for tomorrow.

        Returns
        -------
        list[Match]
            List of Match objects for tomorrow's games
        """
        tomorrow = datetime.now() + timedelta(days=1)
        return self.get_fixtures_by_date(tomorrow)

    def get_fixtures_list(
        self,
        date: datetime | None = None,
        competition_ids: list[str] | None = None,
        country_id: str | None = None,
        fetch_all_pages: bool = True,
    ) -> list[Match]:
        """
        Get fixtures using the list endpoint with competition_id and country_id filtering.

        This endpoint is more efficient for filtering by competition/country as it
        provides these fields directly, avoiding the need for name-based heuristics.

        Parameters
        ----------
        date : datetime or None, optional
            The date to fetch fixtures for (defaults to tomorrow)
        competition_ids : list[str] or None, optional
            List of competition IDs to filter by
        country_id : str or None, optional
            Country ID to filter by
        fetch_all_pages : bool, optional
            Whether to fetch all pages (default: True)

        Returns
        -------
        list[Match]
            List of Match objects
        """
        if date is None:
            date = datetime.now() + timedelta(days=1)

        date_str = date.strftime("%Y-%m-%d")
        all_matches = []
        page = 1
        max_pages = 10  # Safety limit

        while page <= max_pages:
            params: dict[str, Any] = {"date": date_str, "page": page}

            if competition_ids:
                # API accepts comma-separated competition IDs
                params["competition_id"] = ",".join(competition_ids)

            if country_id:
                params["country_id"] = country_id

            data = self._make_request(APIEndpoint.FIXTURES_LIST, params=params)

            fixtures = self._safe_get_nested(data, "data", "fixtures", default=[])

            # Handle case where fixtures might be at different path
            if not fixtures:
                fixtures = self._safe_get_nested(data, "data", default=[])
                if not isinstance(fixtures, list):
                    fixtures = []

            if not fixtures:
                break  # No more fixtures

            for fixture in fixtures:
                if not isinstance(fixture, dict):
                    continue
                try:
                    match = self._parse_fixture(fixture)
                    all_matches.append(match)
                except (KeyError, ValueError, TypeError):
                    # Skip malformed fixtures
                    continue

            # Check if there's a next page
            next_page = self._safe_get_nested(data, "data", "next_page", default=False)
            if not next_page or not fetch_all_pages:
                break

            page += 1

        return all_matches

    def get_competitions(self, country_id: str | None = None) -> list[dict[str, Any]]:
        """
        Get list of available competitions.

        Parameters
        ----------
        country_id : str or None, optional
            Optional country ID to filter competitions

        Returns
        -------
        list[dict[str, Any]]
            List of competition dictionaries with id, name, country
        """
        params: dict[str, Any] = {}
        if country_id:
            params["country_id"] = country_id

        data = self._make_request(APIEndpoint.COMPETITIONS_LIST, params=params)

        competitions = []
        comp_list = self._safe_get_nested(data, "data", "competition", default=[])

        if not isinstance(comp_list, list):
            return competitions

        for comp in comp_list:
            if not isinstance(comp, dict):
                continue
            competitions.append(
                {
                    "id": str(comp.get("id", "")),
                    "name": comp.get("name", "Unknown"),
                    "country_id": str(comp.get("country_id", "")),
                    "country_name": comp.get("country_name", ""),
                }
            )

        return competitions

    def get_countries(self) -> list[dict[str, Any]]:
        """
        Get list of available countries.

        Returns
        -------
        list[dict[str, Any]]
            List of country dictionaries with id and name
        """
        data = self._make_request(APIEndpoint.COUNTRIES_LIST)

        countries = []
        country_list = self._safe_get_nested(data, "data", "country", default=[])

        if not isinstance(country_list, list):
            return countries

        for country in country_list:
            if not isinstance(country, dict):
                continue
            countries.append(
                {
                    "id": str(country.get("id", "")),
                    "name": country.get("name", "Unknown"),
                }
            )

        return countries

    def get_team_standings(self, competition_id: str) -> dict[str, int]:
        """
        Get team standings/positions for a competition.

        Parameters
        ----------
        competition_id : str
            The competition/league ID

        Returns
        -------
        dict[str, int]
            Dictionary mapping team ID to position
        """
        data = self._make_request(
            APIEndpoint.LEAGUES_TABLE, params={"competition_id": competition_id}
        )

        standings = {}
        table = self._safe_get_nested(data, "data", "table", default=[])

        if not isinstance(table, list):
            return standings

        for entry in table:
            if not isinstance(entry, dict):
                continue
            team_id = str(entry.get("team_id", ""))
            position = entry.get("rank", 0)
            # Ensure position is an integer
            try:
                position = int(position) if position else 0
            except (ValueError, TypeError):
                position = 0
            if team_id:
                standings[team_id] = position

        return standings

    def get_team_form(self, team_id: str, limit: int = 5) -> str:
        """
        Get recent form for a team (last N matches).

        Parameters
        ----------
        team_id : str
            The team ID
        limit : int, optional
            Number of recent matches to consider

        Returns
        -------
        str
            Form string like "WWDLW" (W=win, D=draw, L=loss)
        """
        data = self._make_request(
            APIEndpoint.TEAMS_MATCHES, params={"team_id": team_id, "number": limit * 2}
        )

        form = []
        # Handle different API response formats
        matches = self._safe_get_nested(data, "data", "match", default=[])
        if not matches:
            # API might return data directly as a list
            matches = data.get("data", [])

        if not isinstance(matches, list):
            return ""

        for match in matches[: limit * 2]:  # Fetch extra to account for non-finished
            if not isinstance(match, dict):
                continue

            # Check for finished match (status can be "FT", "FINISHED", etc.)
            status = str(match.get("status", "")).upper()
            if status not in ("FT", "FINISHED", "AET", "AP"):
                continue

            # Parse score - can be in different formats
            try:
                # Try ft_score format first (e.g., "0 - 2")
                ft_score = match.get("ft_score", "") or match.get("score", "")
                if ft_score and " - " in ft_score:
                    parts = ft_score.split(" - ")
                    home_score = int(parts[0].strip())
                    away_score = int(parts[1].strip())
                else:
                    # Try home_score/away_score fields
                    home_score = int(match.get("home_score", 0) or 0)
                    away_score = int(match.get("away_score", 0) or 0)
            except (ValueError, TypeError, IndexError):
                continue

            is_home = str(match.get("home_id", "")) == team_id

            if is_home:
                if home_score > away_score:
                    form.append("W")
                elif home_score < away_score:
                    form.append("L")
                else:
                    form.append("D")
            else:
                if away_score > home_score:
                    form.append("W")
                elif away_score < home_score:
                    form.append("L")
                else:
                    form.append("D")

            # Stop once we have enough
            if len(form) >= limit:
                break

        return "".join(form[:limit])

    def get_team_performance_stats(
        self, team_id: str, num_matches: int = 10
    ) -> TeamPerformanceStats:
        """
        Calculate detailed performance statistics for a team from recent matches.

        This provides goal-based metrics that improve prediction accuracy:
        - Goals scored/conceded per game (attack/defense strength)
        - Clean sheet rate (defensive solidity)
        - Home/Away specific win rates
        - Points per game

        Parameters
        ----------
        team_id : str
            The team ID
        num_matches : int, optional
            Number of recent matches to analyze

        Returns
        -------
        TeamPerformanceStats
            TeamPerformanceStats with calculated metrics
        """
        data = self._make_request(
            APIEndpoint.TEAMS_MATCHES,
            params={"team_id": team_id, "number": num_matches * 2},
        )

        stats = TeamPerformanceStats(team_id=team_id)

        # Handle different API response formats
        matches = self._safe_get_nested(data, "data", "match", default=[])
        if not matches:
            matches = data.get("data", [])

        if not isinstance(matches, list):
            return stats

        finished_matches = 0

        for match in matches:
            if not isinstance(match, dict):
                continue

            # Only count finished matches
            status = str(match.get("status", "")).upper()
            if status not in ("FT", "FINISHED", "AET", "AP"):
                continue

            # Parse score
            try:
                ft_score = match.get("ft_score", "") or match.get("score", "")
                if ft_score and " - " in ft_score:
                    parts = ft_score.split(" - ")
                    home_score = int(parts[0].strip())
                    away_score = int(parts[1].strip())
                else:
                    home_score = int(match.get("home_score", 0) or 0)
                    away_score = int(match.get("away_score", 0) or 0)
            except (ValueError, TypeError, IndexError):
                continue

            is_home = str(match.get("home_id", "")) == team_id

            # Determine full time result
            if home_score > away_score:
                ft_result = "1"  # Home win
            elif away_score > home_score:
                ft_result = "2"  # Away win
            else:
                ft_result = "X"  # Draw

            if is_home:
                team_scored = home_score
                team_conceded = away_score
                stats.home_games += 1
                if home_score > away_score:
                    stats.home_wins += 1
                    stats.total_points += 3
                    stats.wins += 1
                elif home_score == away_score:
                    stats.total_points += 1
                    stats.draws += 1
                else:
                    stats.losses += 1
            else:
                team_scored = away_score
                team_conceded = home_score
                stats.away_games += 1
                if away_score > home_score:
                    stats.away_wins += 1
                    stats.total_points += 3
                    stats.wins += 1
                elif away_score == home_score:
                    stats.total_points += 1
                    stats.draws += 1
                else:
                    stats.losses += 1

            stats.goals_scored += team_scored
            stats.goals_conceded += team_conceded

            if team_conceded == 0:
                stats.clean_sheets += 1

            if team_scored > 0:
                stats.games_scored += 1

            # NEW: Parse half-time outcomes from API
            # Per https://live-score-api.com/documentation/reference/27/getting-teams-last-matches
            outcomes = match.get("outcomes", {})
            if isinstance(outcomes, dict):
                ht_outcome = outcomes.get("half_time", "")

                # Determine if team was winning/losing at HT
                if is_home:
                    if ht_outcome == "1":  # Home leading at HT
                        stats.ht_wins += 1
                    elif ht_outcome == "2":  # Home trailing at HT
                        stats.ht_losses += 1
                    elif ht_outcome == "X":  # Level at HT
                        stats.ht_draws += 1
                else:
                    if ht_outcome == "2":  # Away leading at HT
                        stats.ht_wins += 1
                    elif ht_outcome == "1":  # Away trailing at HT
                        stats.ht_losses += 1
                    elif ht_outcome == "X":  # Level at HT
                        stats.ht_draws += 1

                # Track comebacks and collapses
                # Comeback: Trailing at HT but won/drew
                if is_home:
                    if ht_outcome == "2" and ft_result in (
                        "1",
                        "X",
                    ):  # Was losing, didn't lose
                        stats.comebacks += 1
                    if ht_outcome == "1" and ft_result in (
                        "2",
                        "X",
                    ):  # Was winning, didn't win
                        stats.collapses += 1
                else:
                    if ht_outcome == "1" and ft_result in (
                        "2",
                        "X",
                    ):  # Was losing, didn't lose
                        stats.comebacks += 1
                    if ht_outcome == "2" and ft_result in (
                        "1",
                        "X",
                    ):  # Was winning, didn't win
                        stats.collapses += 1

            finished_matches += 1

            # Stop once we have enough
            if finished_matches >= num_matches:
                break

        # Calculate derived metrics
        stats.matches_analyzed = finished_matches

        if finished_matches > 0:
            stats.goals_per_game = stats.goals_scored / finished_matches
            stats.goals_conceded_per_game = stats.goals_conceded / finished_matches
            stats.goal_difference = stats.goals_scored - stats.goals_conceded
            stats.clean_sheet_rate = stats.clean_sheets / finished_matches
            stats.scoring_rate = stats.games_scored / finished_matches
            stats.points_per_game = stats.total_points / finished_matches
            stats.win_rate = stats.wins / finished_matches
            stats.ht_lead_rate = stats.ht_wins / finished_matches

            # Comeback rate: of games where they trailed at HT, how many did they not lose?
            if stats.ht_losses > 0:
                stats.comeback_rate = stats.comebacks / stats.ht_losses

        if stats.home_games > 0:
            stats.home_win_rate = stats.home_wins / stats.home_games

        if stats.away_games > 0:
            stats.away_win_rate = stats.away_wins / stats.away_games

        return stats

    def get_head_to_head(self, home_team_id: str, away_team_id: str, limit: int = 5) -> dict:
        """
        Get head-to-head statistics between two teams.

        Parameters
        ----------
        home_team_id : str
            Home team ID
        away_team_id : str
            Away team ID
        limit : int, optional
            Number of recent H2H matches to consider

        Returns
        -------
        dict
            Dictionary with H2H statistics
        """
        data = self._make_request(
            APIEndpoint.TEAMS_HEAD2HEAD,
            params={"team1_id": home_team_id, "team2_id": away_team_id},
        )

        h2h_data = self._safe_get_nested(data, "data", default={})
        if not isinstance(h2h_data, dict):
            h2h_data = {}

        matches = h2h_data.get("matches", [])
        if not isinstance(matches, list):
            matches = []

        home_wins = 0
        away_wins = 0
        draws = 0

        for match in matches[:limit]:
            if not isinstance(match, dict):
                continue

            try:
                home_score = int(match.get("home_score", 0) or 0)
                away_score = int(match.get("away_score", 0) or 0)
            except (ValueError, TypeError):
                continue

            match_home_id = str(match.get("home_id", ""))

            if home_score > away_score:
                if match_home_id == home_team_id:
                    home_wins += 1
                else:
                    away_wins += 1
            elif home_score < away_score:
                if match_home_id == home_team_id:
                    away_wins += 1
                else:
                    home_wins += 1
            else:
                draws += 1

        total = home_wins + away_wins + draws

        return {
            "matches_played": total,
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": home_wins / total if total > 0 else 0.0,
            "away_win_rate": away_wins / total if total > 0 else 0.0,
        }

    def get_match_statistics(self, match_id: str) -> MatchStatistics:
        """
        Get statistics for a live or completed match.

        Per https://live-score-api.com/documentation/reference/23/match-statistics
        Statistics are only available after the match has started.

        Parameters
        ----------
        match_id : str
            The match ID

        Returns
        -------
        MatchStatistics
            MatchStatistics object with available stats
        """
        data = self._make_request(APIEndpoint.SCORES_MATCH_STATS, params={"match_id": match_id})

        stats_data = self._safe_get_nested(data, "data", default={})
        if not isinstance(stats_data, dict):
            stats_data = {}

        parse = MatchStatistics.parse_stat

        return MatchStatistics(
            possession=parse(stats_data.get("possesion")),  # API typo: "possesion"
            shots_on_target=parse(stats_data.get("shots_on_target")),
            shots_off_target=parse(stats_data.get("shots_off_target")),
            corners=parse(stats_data.get("corners")),
            fouls=parse(stats_data.get("fauls")),  # API typo: "fauls"
            yellow_cards=parse(stats_data.get("yellow_cards")),
            red_cards=parse(stats_data.get("red_cards")),
            offsides=parse(stats_data.get("offsides")),
            saves=parse(stats_data.get("saves")),
            attacks=parse(stats_data.get("attacks")),
            dangerous_attacks=parse(stats_data.get("dangerous_attacks")),
        )

    def get_history(
        self,
        competition_id: str | None = None,
        team_id: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        page: int = 1,
    ) -> list[HistoricalMatch]:
        """
        Get historical match data.

        Per https://live-score-api.com/documentation/reference/15/football_data_history_matches

        Parameters
        ----------
        competition_id : str or None, optional
            Filter by competition (comma-separated for multiple)
        team_id : str or None, optional
            Filter by team (comma-separated for multiple)
        from_date : datetime or None, optional
            Get matches from this date onwards
        to_date : datetime or None, optional
            Get matches until this date
        page : int, optional
            Page number for pagination

        Returns
        -------
        list[HistoricalMatch]
            List of HistoricalMatch objects
        """
        params: dict[str, Any] = {"page": page}

        if competition_id:
            params["competition_id"] = competition_id
        if team_id:
            params["team_id"] = team_id
        if from_date:
            params["from"] = from_date.strftime("%Y-%m-%d")
        if to_date:
            params["to"] = to_date.strftime("%Y-%m-%d")

        data = self._make_request(APIEndpoint.MATCHES_HISTORY, params=params)

        matches = []
        match_list = self._safe_get_nested(data, "data", "match", default=[])

        if not isinstance(match_list, list):
            return matches

        for match_data in match_list:
            if not isinstance(match_data, dict):
                continue
            try:
                match = self._parse_historical_match(match_data)
                matches.append(match)
            except (KeyError, ValueError, TypeError):
                continue

        return matches

    def _parse_historical_match(self, data: dict) -> HistoricalMatch:
        """Parse a historical match from the API response."""
        # Extract nested objects with type safety
        home_data = data.get("home") or {}
        if not isinstance(home_data, dict):
            home_data = {}

        away_data = data.get("away") or {}
        if not isinstance(away_data, dict):
            away_data = {}

        country_data = data.get("country") or {}
        if not isinstance(country_data, dict):
            country_data = {}

        competition_data = data.get("competition") or {}
        if not isinstance(competition_data, dict):
            competition_data = {}

        scores_data = data.get("scores") or {}
        if not isinstance(scores_data, dict):
            scores_data = {}

        outcomes_data = data.get("outcomes") or {}
        if not isinstance(outcomes_data, dict):
            outcomes_data = {}

        odds_data = data.get("odds") or {}
        if not isinstance(odds_data, dict):
            odds_data = {}

        # Parse date
        date_str = data.get("date", "")
        try:
            match_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            match_date = datetime.now()

        # Country name (can be None for international competitions)
        country_name = None
        if isinstance(country_data, dict) and country_data:
            country_name = country_data.get("name")

        # Parse pre-match odds
        pre_odds_data = odds_data.get("pre", {}) if isinstance(odds_data, dict) else {}
        pre_odds = None
        if isinstance(pre_odds_data, dict) and pre_odds_data:
            pre_odds = Odds(
                home_win=pre_odds_data.get("1"),
                draw=pre_odds_data.get("X"),
                away_win=pre_odds_data.get("2"),
            )
            if not pre_odds.has_odds:
                pre_odds = None

        return HistoricalMatch(
            id=str(data.get("id", "")),
            fixture_id=str(data.get("fixture_id", "")) or None,
            home_team=Team(
                id=str(home_data.get("id", "")),
                name=home_data.get("name", "Unknown"),
                country=country_name,
            ),
            away_team=Team(
                id=str(away_data.get("id", "")),
                name=away_data.get("name", "Unknown"),
                country=country_name,
            ),
            competition=competition_data.get("name", "Unknown"),
            competition_id=str(competition_data.get("id", "")),
            country=country_name,
            date=match_date,
            status=data.get("status", "FINISHED"),
            scores=MatchScores(
                final=scores_data.get("score"),
                half_time=scores_data.get("ht_score"),
                full_time=scores_data.get("ft_score"),
                extra_time=scores_data.get("et_score") or None,
                penalties=scores_data.get("ps_score") or None,
            ),
            outcomes=MatchOutcome(
                half_time=outcomes_data.get("half_time"),
                full_time=outcomes_data.get("full_time"),
                extra_time=outcomes_data.get("extra_time"),
                penalties=outcomes_data.get("penalty_shootout"),
            ),
            pre_odds=pre_odds,
            location=data.get("location"),
            round=data.get("round"),
        )

    def get_team_history(self, team_id: str, limit: int = 10) -> list[HistoricalMatch]:
        """
        Get recent match history for a specific team.

        Parameters
        ----------
        team_id : str
            The team ID
        limit : int, optional
            Maximum number of matches to return

        Returns
        -------
        list[HistoricalMatch]
            List of HistoricalMatch objects (most recent first)
        """
        # Get enough pages to hopefully get limit matches
        matches = []
        page = 1
        max_pages = (limit // 30) + 2  # API returns max 30 per page

        while len(matches) < limit and page <= max_pages:
            try:
                page_matches = self.get_history(team_id=team_id, page=page)
                if not page_matches:
                    break
                matches.extend(page_matches)
                page += 1
            except LivescoreAPIError:
                break

        return matches[:limit]

    def _parse_fixture(self, fixture: dict) -> Match:
        """
        Parse a fixture from the API response into a Match object.

        TODO(amir): refactor this; API may return two formats:
        Format 1 (nested):
        {
            "id": 1712210,
            "home": {"id": 864, "name": "Asteras Tripolis", ...},
            "away": {"id": 1157, "name": "Lamia", ...},
            ...
        }

        Format 2 (flat):
        {
            "id": 1712210,
            "home_id": 864,
            "home_name": "Asteras Tripolis",
            "away_id": 1157,
            "away_name": "Lamia",
            ...
        }
        """
        # Try nested format first
        home_data = fixture.get("home", {}) or {}
        away_data = fixture.get("away", {}) or {}
        country_data = fixture.get("country", {}) or {}
        competition_data = fixture.get("competition", {}) or {}

        # Ensure they are dicts
        if not isinstance(home_data, dict):
            home_data = {}
        if not isinstance(away_data, dict):
            away_data = {}
        if not isinstance(country_data, dict):
            country_data = {}
        if not isinstance(competition_data, dict):
            competition_data = {}

        # Parse kickoff time (format: "HH:MM:SS")
        date_str = fixture.get("date", "")
        time_str = fixture.get("time", "00:00:00")
        kickoff_str = f"{date_str} {time_str}"

        try:
            # Try HH:MM:SS format first
            kickoff_time = datetime.strptime(kickoff_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                # Fallback to HH:MM format
                kickoff_time = datetime.strptime(kickoff_str, "%Y-%m-%d %H:%M")
            except ValueError:
                kickoff_time = datetime.now()

        # Get country name - try both nested and flat formats
        country_name = (
            country_data.get("name")
            or fixture.get("country_name")
            or fixture.get("location")
            or "Unknown"
        )

        # Get competition name - try both nested and flat formats
        competition_name = (
            competition_data.get("name")
            or fixture.get("competition_name")
            or fixture.get("league_name")
            or "Unknown"
        )
        competition_id = str(
            competition_data.get("id")
            or fixture.get("competition_id")
            or fixture.get("league_id")
            or ""
        )

        # Get team data - try both nested and flat formats
        home_id = str(home_data.get("id") or fixture.get("home_id") or "")
        home_name = (
            home_data.get("name")
            or fixture.get("home_name")
            or fixture.get("home_team")
            or "Unknown"
        )
        away_id = str(away_data.get("id") or fixture.get("away_id") or "")
        away_name = (
            away_data.get("name")
            or fixture.get("away_name")
            or fixture.get("away_team")
            or "Unknown"
        )

        home_team = Team(
            id=home_id,
            name=home_name,
            country=country_name,
        )

        away_team = Team(
            id=away_id,
            name=away_name,
            country=country_name,
        )

        # Parse pre-match odds - try multiple formats
        odds_data = fixture.get("odds", {}) or {}
        if not isinstance(odds_data, dict):
            odds_data = {}
        pre_odds_data = odds_data.get("pre", {}) or {}
        if not isinstance(pre_odds_data, dict):
            pre_odds_data = {}

        # Try to get odds from various locations
        home_odds = pre_odds_data.get("1") or fixture.get("odds_home") or fixture.get("home_odds")
        draw_odds = pre_odds_data.get("X") or fixture.get("odds_draw") or fixture.get("draw_odds")
        away_odds = pre_odds_data.get("2") or fixture.get("odds_away") or fixture.get("away_odds")

        pre_odds = Odds(
            home_win=home_odds,
            draw=draw_odds,
            away_win=away_odds,
        )

        # Get score if available
        home_score = fixture.get("home_score") or fixture.get("score_home")
        away_score = fixture.get("away_score") or fixture.get("score_away")

        return Match(
            id=str(fixture.get("id", "")),
            home_team=home_team,
            away_team=away_team,
            competition=competition_name,
            competition_id=competition_id,
            country=country_name,
            kickoff_time=kickoff_time,
            status=fixture.get("status", "NS"),
            home_score=home_score,
            away_score=away_score,
            pre_odds=pre_odds if pre_odds.has_odds else None,
        )

    # TODO(amir): I did this in case we wanna bet on cup matches.
    # Mapping from cup competitions to their respective leagues for standings lookup
    # This allows us to show league positions even for cup matches
    CUP_TO_LEAGUE_MAPPING = {
        # UAE
        "421": "354",  # UAE Presidents Cup -> UAE Pro League
        "356": "354",  # UAE Cup -> UAE Pro League
        "357": "354",  # UAE League Cup -> UAE Pro League
        # Saudi Arabia
        "315": "313",  # Saudi King's Cup -> Saudi Pro League
        # Qatar
        "307": "305",  # Qatar Stars League Cup -> Qatar Stars League
        # European
        "152": "2",  # FA Cup -> Premier League
        "153": "2",  # EFL Cup -> Premier League
        "247": "1",  # DFB Pokal -> Bundesliga
        "150": "3",  # Copa del Rey -> La Liga
        "149": "4",  # Coppa Italia -> Serie A
        "148": "5",  # Coupe de France -> Ligue 1
    }

    def enrich_match_with_stats(self, match: Match) -> Match:
        """
        Enrich a match object with additional statistics.

        Parameters
        ----------
        match : Match
            The match to enrich

        Returns
        -------
        Match
            Match with additional stats (form, standings, H2H, performance)
        """
        # Get IDs safely
        home_id = ""
        away_id = ""
        comp_id = ""

        if match.home_team and match.home_team.id:
            home_id = match.home_team.id
        if match.away_team and match.away_team.id:
            away_id = match.away_team.id
        if match.competition_id:
            comp_id = match.competition_id

        # Skip if we don't have valid IDs
        if not home_id or not away_id:
            return match

        try:
            # Get team forms
            match.home_form = self.get_team_form(home_id)
            match.away_form = self.get_team_form(away_id)
        except Exception:
            pass

        # Determine which competition to use for standings
        # For cup competitions, use the corresponding league
        standings_comp_id = self.CUP_TO_LEAGUE_MAPPING.get(comp_id, comp_id)

        try:
            # Get standings (use league standings for cup competitions)
            if standings_comp_id:
                standings = self.get_team_standings(standings_comp_id)
                if isinstance(standings, dict):
                    match.home_position = standings.get(home_id)
                    match.away_position = standings.get(away_id)
        except Exception:
            pass

        try:
            # Get head-to-head
            match.head_to_head = self.get_head_to_head(home_id, away_id)
        except Exception:
            pass

        try:
            # NEW: Get detailed performance stats (goals, clean sheets, etc.)
            match.home_performance = self.get_team_performance_stats(home_id)
            match.away_performance = self.get_team_performance_stats(away_id)
        except Exception:
            pass

        return match
