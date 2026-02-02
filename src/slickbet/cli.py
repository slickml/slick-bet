"""
Command-line interface for the SlickBet betting screener.
"""

import argparse
import sys
from datetime import datetime

from slickbet.api import LivescoreAPIError, LivescoreClient
from slickbet.backtest import Backtester, format_backtest_report
from slickbet.pdf_export import (
    export_backtest_all_to_pdf,
    export_backtest_to_pdf,
    export_screener_to_pdf,
)
from slickbet.screener import (
    BettingScreener,
    ScreenerConfig,
    format_prediction,
    format_summary,
)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="slickbet",
        description="🎰 SlickBet - Soccer Betting Screener",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  slickbet                      # Screen tomorrow's games, show top 5
  slickbet --top 10             # Show top 10 betting opportunities
  slickbet --date 2025-02-15    # Screen games for specific date
  slickbet --min-prob 0.60      # Only show bets with >60% probability
  slickbet --country England    # Filter by country
  slickbet --no-stats           # Fast mode (skip detailed stats)

  slickbet backtest             # Backtest on Premier League (4 weeks)
  slickbet backtest --weeks 8   # Backtest on 8 weeks of data
  slickbet backtest --competition 3  # Backtest on La Liga

Environment Variables:
  LIVESCORE_API_KEY     Your Livescore API key
  LIVESCORE_API_SECRET  Your Livescore API secret
        """,
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Competitions subcommand
    comp_parser = subparsers.add_parser(
        "competitions",
        help="List available competitions and their IDs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  slickbet competitions                    # List all competitions
  slickbet competitions --country England  # English competitions
  slickbet competitions --search "Premier" # Search by name
        """,
    )

    comp_parser.add_argument(
        "--country", type=str, metavar="NAME", help="Filter by country name"
    )

    comp_parser.add_argument(
        "-s", "--search", type=str, metavar="TERM", help="Search competition names"
    )

    # Backtest subcommand
    backtest_parser = subparsers.add_parser(
        "backtest",
        help="Backtest the model against historical data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Competition IDs:
  1 = Bundesliga (Germany)
  2 = Premier League (England)
  3 = La Liga (Spain)
  4 = Serie A (Italy)
  5 = Ligue 1 (France)

Examples:
  slickbet backtest                    # Premier League, 4 weeks
  slickbet backtest --weeks 8          # 8 weeks of data
  slickbet backtest --competition 3    # La Liga
  slickbet backtest --min-prob 0.60    # Only predictions ≥60%
        """,
    )

    backtest_parser.add_argument(
        "-c",
        "--competition",
        type=str,
        default="2",
        metavar="ID",
        help="Competition ID to backtest (default: 2 = Premier League)",
    )

    backtest_parser.add_argument(
        "-w",
        "--weeks",
        type=int,
        default=4,
        metavar="N",
        help="Number of weeks of historical data (default: 4)",
    )

    backtest_parser.add_argument(
        "--from",
        type=str,
        dest="from_date",
        metavar="YYYY-MM-DD",
        help="Start date for backtest (overrides --weeks)",
    )

    backtest_parser.add_argument(
        "--to",
        type=str,
        dest="to_date",
        metavar="YYYY-MM-DD",
        help="End date for backtest (default: yesterday)",
    )

    backtest_parser.add_argument(
        "--min-prob",
        type=float,
        default=0.0,
        metavar="PROB",
        help="Minimum probability threshold (default: 0.0 = all)",
    )

    backtest_parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )

    backtest_parser.add_argument(
        "--pdf",
        type=str,
        metavar="PATH",
        nargs="?",
        const="",
        help="Export results to PDF file (optional: specify filename, otherwise auto-generated)",
    )

    # Backtest-all subcommand (all major leagues)
    backtest_all_parser = subparsers.add_parser(
        "backtest-all",
        help="Backtest model on ALL major leagues with aggregated results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Runs backtests on all 5 major European leagues and shows aggregated results.

Leagues:
  1 = Bundesliga (Germany)
  2 = Premier League (England)
  3 = La Liga (Spain)
  4 = Serie A (Italy)
  5 = Ligue 1 (France)

Examples:
  slickbet backtest-all             # All leagues, 4 weeks each
  slickbet backtest-all --weeks 17  # All leagues, ~120 days each
        """,
    )

    backtest_all_parser.add_argument(
        "-w",
        "--weeks",
        type=int,
        default=4,
        metavar="N",
        help="Number of weeks of historical data (default: 4)",
    )

    backtest_all_parser.add_argument(
        "--min-prob",
        type=float,
        default=0.0,
        metavar="PROB",
        help="Minimum probability threshold (default: 0.0 = all)",
    )

    backtest_all_parser.add_argument(
        "--include-gulf",
        action="store_true",
        help="Include Persian Gulf leagues (Saudi, Qatar, UAE) in backtest",
    )

    backtest_all_parser.add_argument(
        "--gulf-only",
        action="store_true",
        help="Only test Persian Gulf leagues (Saudi, Qatar, UAE)",
    )

    backtest_all_parser.add_argument(
        "--pdf",
        type=str,
        metavar="PATH",
        nargs="?",
        const="",
        help="Export results to PDF file (optional: specify filename, otherwise auto-generated)",
    )

    # Main screener options (default command)
    parser.add_argument(
        "-k",
        "--top",
        type=int,
        default=5,
        metavar="K",
        help="Number of top betting opportunities to show (default: 5)",
    )

    parser.add_argument(
        "-d",
        "--date",
        type=str,
        metavar="YYYY-MM-DD",
        help="Date to screen (default: tomorrow)",
    )

    parser.add_argument(
        "--days",
        type=int,
        default=1,
        metavar="N",
        help="Number of days to screen ahead (0 = today, default: 1 = tomorrow only)",
    )

    # Filtering options
    filter_group = parser.add_argument_group("Filtering Options")

    filter_group.add_argument(
        "--min-prob",
        type=float,
        default=0.55,
        metavar="PROB",
        help="Minimum probability threshold (default: 0.55)",
    )

    filter_group.add_argument(
        "--min-conf",
        type=float,
        default=0.10,
        metavar="CONF",
        help="Minimum confidence threshold (default: 0.10)",
    )

    filter_group.add_argument(
        "--country",
        type=str,
        action="append",
        metavar="NAME",
        help="Filter by country (can be used multiple times)",
    )

    filter_group.add_argument(
        "--competition",
        type=str,
        action="append",
        metavar="NAME",
        help="Filter by competition name (can be used multiple times)",
    )

    filter_group.add_argument(
        "--major-only",
        action="store_true",
        help="Only show major European leagues (Bundesliga, PL, La Liga, Serie A, Ligue 1)",
    )

    filter_group.add_argument(
        "--gulf-only",
        action="store_true",
        help="Only show Persian Gulf leagues (Saudi Pro League, Qatar Stars, UAE Pro League)",
    )

    filter_group.add_argument(
        "--all-leagues",
        action="store_true",
        help="Show all supported leagues (Major European + Persian Gulf)",
    )

    filter_group.add_argument(
        "--league",
        type=str,
        action="append",
        metavar="ID",
        help="Filter by league ID: 1=Bundesliga, 2=PL, 3=LaLiga, 4=SerieA, 5=Ligue1, 313=Saudi, 305=Qatar, 354=UAE",
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")

    output_group.add_argument(
        "--home-only", action="store_true", help="Only show home win predictions"
    )

    output_group.add_argument(
        "--away-only", action="store_true", help="Only show away win predictions"
    )

    output_group.add_argument(
        "--summary-only",
        action="store_true",
        help="Only show summary, not individual predictions",
    )

    output_group.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )

    output_group.add_argument(
        "--pdf",
        type=str,
        metavar="PATH",
        nargs="?",
        const="",
        help="Export results to PDF file (optional: specify filename, otherwise auto-generated)",
    )

    # Performance options
    perf_group = parser.add_argument_group("Performance Options")

    perf_group.add_argument(
        "--no-stats",
        action="store_true",
        help="Skip fetching detailed stats (faster but less accurate)",
    )

    perf_group.add_argument(
        "--workers",
        type=int,
        default=5,
        metavar="N",
        help="Number of parallel workers for API calls (default: 5)",
    )

    # Debug subcommand
    debug_parser = subparsers.add_parser("debug", help="Debug API responses")
    debug_parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date to check fixtures (YYYY-MM-DD, default: tomorrow)",
    )

    return parser


def run_competitions(args: argparse.Namespace) -> int:
    """
    List available competitions.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    print()
    print("🏆 SlickBet - Available Competitions")
    print("=" * 60)
    print()

    try:
        client = LivescoreClient()

        # Get countries if filtering by country
        country_id = None
        if args.country:
            print(f"🔍 Finding country: {args.country}")
            countries = client.get_countries()
            for c in countries:
                if args.country.lower() in c["name"].lower():
                    country_id = c["id"]
                    print(f"   Found: {c['name']} (ID: {c['id']})")
                    break

            if not country_id:
                print(f"   ❌ Country '{args.country}' not found")
                print()
                print("Available countries:")
                for c in sorted(countries, key=lambda x: x["name"])[:30]:
                    print(f"   - {c['name']}")
                return 1

            print()

        # Get competitions
        competitions = client.get_competitions(country_id=country_id)

        if not competitions:
            print("❌ No competitions found")
            return 1

        # Filter by search term if provided
        if args.search:
            search_lower = args.search.lower()
            competitions = [
                c for c in competitions if search_lower in c["name"].lower()
            ]
            print(f"🔍 Searching for: {args.search}")
            print()

        if not competitions:
            print(f"❌ No competitions matching '{args.search}'")
            return 1

        # Sort by country and name
        competitions = sorted(
            competitions, key=lambda x: (x.get("country_name", ""), x.get("name", ""))
        )

        # Print competitions
        print(f"{'ID':<6} {'Competition':<35} {'Country':<20}")
        print("-" * 60)

        current_country = None
        for comp in competitions:
            country = comp.get("country_name", "International")
            if country != current_country:
                if current_country is not None:
                    print()
                current_country = country
            print(f"{comp['id']:<6} {comp['name']:<35} {country:<20}")

        print()
        print(f"Total: {len(competitions)} competitions")
        print()
        print("Use competition ID with: slickbet backtest --competition <ID>")
        return 0

    except LivescoreAPIError as e:
        print(f"❌ API Error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


def run_backtest(args: argparse.Namespace) -> int:
    """
    Run the backtest with the given arguments.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    print()
    print("🎰 SlickBet - Model Backtesting")
    print("=" * 40)
    print()

    # Parse dates
    to_date = None
    from_date = None

    if args.to_date:
        try:
            to_date = datetime.strptime(args.to_date, "%Y-%m-%d")
        except ValueError:
            print(f"❌ Invalid date format: {args.to_date}")
            return 1

    if args.from_date:
        try:
            from_date = datetime.strptime(args.from_date, "%Y-%m-%d")
        except ValueError:
            print(f"❌ Invalid date format: {args.from_date}")
            return 1

    try:
        backtester = Backtester()

        results = backtester.run(
            competition_id=args.competition,
            weeks=args.weeks,
            from_date=from_date,
            to_date=to_date,
            min_probability=args.min_prob,
            verbose=True,
        )

        if args.json:
            output_backtest_json(results)
        elif args.pdf is not None:
            # Export to PDF
            pdf_path = export_backtest_to_pdf(
                results, output_path=args.pdf if args.pdf else None
            )
            print(f"✅ PDF exported to: {pdf_path}")
        else:
            print(format_backtest_report(results))

        return 0

    except LivescoreAPIError as e:
        print(f"❌ API Error: {e}")
        print(
            "   Check your LIVESCORE_API_KEY and LIVESCORE_API_SECRET environment variables."
        )
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


def run_backtest_all(args: argparse.Namespace) -> int:
    """
    Run backtest on all major leagues and show aggregated results.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Major European leagues
    MAJOR_LEAGUES = [
        ("1", "🇩🇪 Bundesliga", "Germany"),
        ("2", "🇬🇧 Premier League", "England"),
        ("3", "🇪🇸 La Liga", "Spain"),
        ("4", "🇮🇹 Serie A", "Italy"),
        ("5", "🇫🇷 Ligue 1", "France"),
    ]

    # Minor European leagues
    MINOR_LEAGUES = [
        ("34", "🇧🇪 Belgian Pro League", "Belgium"),
        ("8", "🇵🇹 Primeira Liga", "Portugal"),
        ("6", "🇹🇷 Super Lig", "Turkey"),
        ("196", "🇳🇱 Eredivisie", "Netherlands"),
    ]

    # Persian Gulf leagues
    GULF_LEAGUES = [
        ("313", "🇸🇦 Saudi Pro League", "Saudi Arabia"),
        ("305", "🇶🇦 Qatar Stars League", "Qatar"),
        ("354", "🇦🇪 UAE Pro League", "UAE"),
    ]

    # Determine which leagues to test
    include_gulf = getattr(args, "include_gulf", False)
    gulf_only = getattr(args, "gulf_only", False)

    if gulf_only:
        LEAGUES = GULF_LEAGUES
        league_type = "Persian Gulf"
    elif include_gulf:
        # Include Major + Minor European + Persian Gulf
        LEAGUES = MAJOR_LEAGUES + MINOR_LEAGUES + GULF_LEAGUES
        league_type = "ALL (Major + Minor European + Persian Gulf)"
    else:
        # Default: Major + Minor European (for backtest-all-global)
        LEAGUES = MAJOR_LEAGUES + MINOR_LEAGUES
        league_type = "Major + Minor European"

    print()
    print("🏆 SlickBet - ALL LEAGUES Backtesting")
    print("=" * 70)
    print(f"   Testing {len(LEAGUES)} {league_type} leagues")
    print(f"   Period: {args.weeks} weeks")
    print("=" * 70)
    print()

    # Collect results from all leagues
    all_results = []
    league_summaries = []

    backtester = Backtester()

    for comp_id, league_name, country in LEAGUES:
        print(f"\n{league_name}")
        print("-" * 40)

        try:
            results = backtester.run(
                competition_id=comp_id,
                weeks=args.weeks,
                min_probability=args.min_prob,
                verbose=False,
            )

            # Store results
            all_results.extend(results.results)

            # Print league summary
            print(f"   Matches: {results.total_predictions}")
            print(f"   Accuracy: {results.accuracy:.1%}")
            print(f"   Accuracy (excl. draws): {results.accuracy_excluding_draws:.1%}")
            print(
                f"   Draws: {results.draws_encountered} ({results.draws_encountered / max(results.total_predictions, 1) * 100:.1f}%)"
            )
            print(f"   1X (Home or Draw): {results.home_or_draw_accuracy:.1%}")
            print(f"   X2 (Away or Draw): {results.away_or_draw_accuracy:.1%}")

            league_summaries.append(
                {
                    "name": league_name,
                    "country": country,
                    "total": results.total_predictions,
                    "correct": results.correct_predictions,
                    "accuracy": results.accuracy,
                    "accuracy_excl_draws": results.accuracy_excluding_draws,
                    "draws": results.draws_encountered,
                    "home_or_draw": results.home_or_draw_accuracy,
                    "away_or_draw": results.away_or_draw_accuracy,
                    "best_dc": results.best_double_chance_accuracy,
                }
            )

        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue

    # Calculate and display aggregated results
    print()
    print("=" * 70)
    print("📊 AGGREGATED RESULTS (ALL LEAGUES)")
    print("=" * 70)

    total_matches = len(all_results)
    if total_matches == 0:
        print("❌ No results collected")
        return 1

    correct = sum(1 for r in all_results if r.is_correct)
    draws = sum(1 for r in all_results if r.actual_outcome == "D")
    non_draws = [r for r in all_results if r.actual_outcome != "D"]

    home_or_draw_correct = sum(1 for r in all_results if r.home_or_draw_correct)
    away_or_draw_correct = sum(1 for r in all_results if r.away_or_draw_correct)
    best_dc_correct = sum(1 for r in all_results if r.best_double_chance_correct)

    print()
    print(f"Total Matches: {total_matches}")
    print(f"Correct Predictions: {correct}")
    print(f"Overall Accuracy: {correct / total_matches:.1%}")
    print()
    print(f"Draws Encountered: {draws} ({draws / total_matches * 100:.1f}%)")
    print(
        f"Accuracy (excl. draws): {sum(1 for r in non_draws if r.is_correct) / max(len(non_draws), 1):.1%}"
    )
    print()
    print("=" * 70)
    print("🎲 DOUBLE CHANCE (AGGREGATED)")
    print("=" * 70)
    print(f"1X (Home or Draw): {home_or_draw_correct / total_matches:.1%}")
    print(f"X2 (Away or Draw): {away_or_draw_correct / total_matches:.1%}")
    print(f"Best Recommended DC: {best_dc_correct / total_matches:.1%}")
    print()

    # League comparison table
    print("=" * 70)
    print("📈 LEAGUE COMPARISON")
    print("=" * 70)
    print(
        f"{'League':<25} {'Matches':>8} {'Accuracy':>10} {'Excl.Draws':>12} {'Best DC':>10}"
    )
    print("-" * 70)

    for league in sorted(
        league_summaries, key=lambda x: x["accuracy_excl_draws"], reverse=True
    ):
        print(
            f"{league['name']:<25} "
            f"{league['total']:>8} "
            f"{league['accuracy']:>9.1%} "
            f"{league['accuracy_excl_draws']:>11.1%} "
            f"{league['best_dc']:>9.1%}"
        )

    print("=" * 70)

    # Export to PDF if requested
    if args.pdf is not None:
        pdf_path = export_backtest_all_to_pdf(
            league_summaries=league_summaries,
            all_results=all_results,
            league_type=league_type,
            weeks=args.weeks,
            output_path=args.pdf if args.pdf else None,
        )
        print()
        print(f"✅ PDF exported to: {pdf_path}")

    return 0


def output_backtest_json(results) -> None:
    """Output backtest results as JSON."""
    import json

    output = {
        "summary": {
            "competition": results.competition,
            "from_date": results.from_date.isoformat() if results.from_date else None,
            "to_date": results.to_date.isoformat() if results.to_date else None,
            "total_predictions": results.total_predictions,
            "correct_predictions": results.correct_predictions,
            "accuracy": round(results.accuracy, 4),
            "accuracy_excluding_draws": round(results.accuracy_excluding_draws, 4),
            "draws_encountered": results.draws_encountered,
            "home_predictions": len(results.home_predictions),
            "home_accuracy": round(results.home_accuracy, 4),
            "away_predictions": len(results.away_predictions),
            "away_accuracy": round(results.away_accuracy, 4),
            "high_confidence_predictions": len(results.high_confidence_results),
            "high_confidence_accuracy": round(results.high_confidence_accuracy, 4),
        },
        "predictions": [
            {
                "match": {
                    "home_team": r.match.home_team.name,
                    "away_team": r.match.away_team.name,
                    "date": r.match.date.isoformat(),
                    "score": r.match.scores.final,
                },
                "predicted_outcome": r.predicted_outcome,
                "actual_outcome": r.actual_outcome,
                "probability": round(r.probability, 4),
                "confidence": round(r.confidence, 4),
                "is_correct": r.is_correct,
            }
            for r in results.results
        ],
    }

    print(json.dumps(output, indent=2))


def run_screener(args: argparse.Namespace) -> int:
    """
    Run the betting screener with the given arguments.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Create configuration
    config = ScreenerConfig(
        min_probability=args.min_prob,
        min_confidence=args.min_conf,
        fetch_detailed_stats=not args.no_stats,
        max_workers=args.workers,
        countries=args.country or [],
        competitions=args.competition or [],
        competition_ids=args.league or [],
        major_leagues_only=args.major_only,
        gulf_leagues_only=getattr(args, "gulf_only", False),
        all_leagues=getattr(args, "all_leagues", False),
    )

    try:
        # Initialize screener
        screener = BettingScreener(config=config)

        # Determine which date(s) to screen
        if args.date:
            # Specific date provided
            try:
                date = datetime.strptime(args.date, "%Y-%m-%d")
            except ValueError:
                print(f"❌ Invalid date format: {args.date}")
                print("   Use YYYY-MM-DD format (e.g., 2025-02-15)")
                return 1
            result = screener.screen_date(date)
        elif args.days == 0:
            # Screen matches for today
            today = datetime.now()
            result = screener.screen_date(today)
        elif args.days > 1:
            # Multiple days ahead
            result = screener.screen_days(days=args.days)
        else:
            # Default: tomorrow only
            result = screener.screen_tomorrow()

        # Filter by outcome type if requested
        predictions = result.predictions

        if args.home_only:
            predictions = result.get_home_wins()
        elif args.away_only:
            predictions = result.get_away_wins()

        # Helper to get best double chance probability
        def get_best_dc_prob(p):
            if p.double_chance:
                _, prob = p.double_chance.best_double_chance
                return prob
            return p.probability

        # Sort by best double chance probability (highest first)
        predictions = sorted(predictions, key=get_best_dc_prob, reverse=True)[
            : args.top
        ]

        # Output results
        if args.json:
            output_json(predictions, result)
        elif args.pdf is not None:
            # Export to PDF
            pdf_path = export_screener_to_pdf(
                result, predictions, output_path=args.pdf if args.pdf else None
            )
            print(f"✅ PDF exported to: {pdf_path}")
        elif args.summary_only:
            print(format_summary(result))
        else:
            print(format_summary(result))
            print()

            if not predictions:
                print("😕 No betting opportunities found matching your criteria.")
                print("   Try adjusting --min-prob or --min-conf thresholds.")
            else:
                print(f"🎰 TOP {min(args.top, len(predictions))} BETTING OPPORTUNITIES")
                print()

                for i, pred in enumerate(predictions, 1):
                    print(format_prediction(pred, rank=i))
                    print()

        return 0

    except LivescoreAPIError as e:
        print(f"❌ API Error: {e}")
        print(
            "   Check your LIVESCORE_API_KEY and LIVESCORE_API_SECRET environment variables."
        )
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


def output_json(predictions: list, result) -> None:
    """Output results as JSON."""
    import json

    output = {
        "summary": {
            "total_scanned": result.total_matches_scanned,
            "filtered": result.matches_filtered,
            "predictions": len(result.predictions),
            "timestamp": result.timestamp.isoformat(),
        },
        "predictions": [
            {
                "match": {
                    "home_team": pred.match.home_team.name,
                    "away_team": pred.match.away_team.name,
                    "competition": pred.match.competition,
                    "country": pred.match.country,
                    "kickoff_time": pred.match.kickoff_time.isoformat(),
                },
                "recommendation": {
                    "outcome": pred.recommended_outcome.value,
                    "bet_on": (
                        pred.match.home_team.name
                        if pred.recommended_outcome.value == "home_win"
                        else pred.match.away_team.name
                    ),
                    "probability": round(pred.probability, 4),
                    "confidence": round(pred.confidence, 4),
                },
                "analysis": {
                    "form_score": round(pred.form_score, 4),
                    "position_score": round(pred.position_score, 4),
                    "home_advantage_score": round(pred.home_advantage_score, 4),
                    "h2h_score": round(pred.h2h_score, 4),
                },
                "reasoning": pred.reasoning,
            }
            for pred in predictions
        ],
    }

    print(json.dumps(output, indent=2))


def run_debug(args: argparse.Namespace) -> int:
    """
    Debug API responses to understand data structure.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    import json

    print()
    print("🔧 SlickBet - API Debug")
    print("=" * 60)
    print()

    try:
        client = LivescoreClient()

        # Determine date
        if args.date:
            from datetime import datetime

            date = datetime.strptime(args.date, "%Y-%m-%d")
        else:
            from datetime import datetime, timedelta

            date = datetime.now() + timedelta(days=1)

        print(f"📅 Fetching fixtures for: {date.strftime('%Y-%m-%d')}")
        print()

        # Make raw API request
        date_str = date.strftime("%Y-%m-%d")
        data = client._make_request("fixtures/matches.json", params={"date": date_str})

        print("📦 RAW API RESPONSE STRUCTURE:")
        print("-" * 60)

        # Show top-level keys
        if isinstance(data, dict):
            print(f"Top-level keys: {list(data.keys())}")

            if "data" in data:
                data_section = data["data"]
                if isinstance(data_section, dict):
                    print(f"data keys: {list(data_section.keys())}")

                    # Try to find fixtures
                    fixtures = None
                    if "fixtures" in data_section:
                        fixtures = data_section["fixtures"]
                        print(
                            f"Found 'fixtures': {len(fixtures) if isinstance(fixtures, list) else type(fixtures)}"
                        )
                    elif "match" in data_section:
                        fixtures = data_section["match"]
                        print(
                            f"Found 'match': {len(fixtures) if isinstance(fixtures, list) else type(fixtures)}"
                        )
                    elif isinstance(data_section, list):
                        fixtures = data_section
                        print(f"data is a list: {len(fixtures)} items")

                    # Show sample fixture structure
                    if fixtures and isinstance(fixtures, list) and len(fixtures) > 0:
                        print()
                        print("📋 SAMPLE FIXTURE (first item):")
                        print("-" * 60)
                        sample = fixtures[0]
                        print(json.dumps(sample, indent=2, default=str))

                        print()
                        print("📋 FIXTURE KEYS:")
                        if isinstance(sample, dict):
                            for key in sample.keys():
                                value = sample[key]
                                value_type = type(value).__name__
                                if isinstance(value, dict):
                                    print(
                                        f"  {key}: dict with keys {list(value.keys())}"
                                    )
                                elif isinstance(value, str) and len(value) > 50:
                                    print(f"  {key}: {value_type} = '{value[:50]}...'")
                                else:
                                    print(f"  {key}: {value_type} = {value}")
                elif isinstance(data_section, list) and len(data_section) > 0:
                    print(f"data is a list with {len(data_section)} items")
                    print()
                    print("📋 SAMPLE FIXTURE (first item):")
                    print("-" * 60)
                    sample = data_section[0]
                    print(json.dumps(sample, indent=2, default=str))

        return 0

    except LivescoreAPIError as e:
        print(f"❌ API Error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


def main() -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle subcommands
    if args.command == "competitions":
        return run_competitions(args)

    if args.command == "backtest":
        return run_backtest(args)

    if args.command == "backtest-all":
        return run_backtest_all(args)

    if args.command == "debug":
        return run_debug(args)

    # Default: run screener
    print()
    print("🎰 SlickBet - Soccer Betting Screener")
    print("=" * 40)
    print()

    return run_screener(args)


if __name__ == "__main__":
    sys.exit(main())
