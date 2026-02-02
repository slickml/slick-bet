# 🎰 SlickBet - Soccer Betting Screener

A Python-based betting screener for soccer games using the Livescore API. Fetches upcoming matches, analyzes team statistics, and ranks betting opportunities by win probability.

## Features

- 📅 **Multi-Day Screening** - Screen matches for the next N days
- 📊 **9-Factor Analysis** - Comprehensive statistical model for predictions
- 🎲 **Double Chance Bets** - Safer betting options (1X, X2, 12)
- 🏆 **Major European Leagues** - Bundesliga, Premier League, La Liga, Serie A, Ligue 1
- 🌍 **Minor European Leagues** - Belgian Pro League, Primeira Liga, Super Lig, Eredivisie
- 🏟️ **Persian Gulf Leagues** - Saudi Pro League, Qatar Stars League, UAE Pro League
- 🎯 **Confidence Grades** - Visual indicators (🔥 HIGH VALUE, ✅ GOOD BET, 👍 DECENT, ⚠️ RISKY)
- 📈 **Backtesting** - Validate model accuracy against historical data
- 💻 **CLI Interface** - Easy-to-use command-line tool
- 📄 **PDF Export** - Export results to shareable PDF reports

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for fast, reliable Python package management.

```bash
# Clone the repository
git clone https://github.com/your-username/slick-bet.git
cd slick-bet

# Install dependencies with uv
uv sync

# Install with dev dependencies
uv sync --dev
```

## Configuration

Set your [Livescore API](https://live-score-api.com/football-api) credentials as environment variables:

```bash
export LIVESCORE_API_KEY="your_api_key"
export LIVESCORE_API_SECRET="your_api_secret"
```

## Quick Start

```bash
# Screen all leagues for tomorrow with top 20 results
poe run-all --days=1 --top=20

# Screen major European leagues only (tomorrow's games)
poe run-major

# Screen Persian Gulf leagues only for 3 days
poe run-gulf --days=3

# Backtest all leagues for 4 weeks
poe backtest-all-global --weeks=4
```

## 📋 All Commands

### Screener Commands

#### All Leagues (Major + Minor European + Persian Gulf)
| Command                | Description                        |
| ---------------------- | ---------------------------------- |
| `poe run-all --days N` | Screen ALL leagues for next N days |
| `poe run-all-week`     | Screen ALL leagues for next 7 days |

#### Major European Leagues
| Command                       | Description                              |
| ----------------------------- | ---------------------------------------- |
| `poe run-major`               | Screen major European leagues (tomorrow) |
| `poe run-major-week`          | Screen major European leagues for 7 days |
| `poe run-bundesliga --days N` | 🇩🇪 Bundesliga only                        |
| `poe run-pl --days N`         | 🇬🇧 Premier League only                    |
| `poe run-laliga --days N`     | 🇪🇸 La Liga only                           |
| `poe run-seriea --days N`     | 🇮🇹 Serie A only                           |
| `poe run-ligue1 --days N`     | 🇫🇷 Ligue 1 only                           |

#### Persian Gulf Leagues
| Command                  | Description                                |
| ------------------------ | ------------------------------------------ |
| `poe run-gulf --days N`  | Screen all Persian Gulf leagues for N days |
| `poe run-saudi --days N` | 🇸🇦 Saudi Pro League only                    |
| `poe run-qatar --days N` | 🇶🇦 Qatar Stars League only                  |
| `poe run-uae --days N`   | 🇦🇪 UAE Pro League only                      |

#### Basic Commands
| Command                 | Description                      |
| ----------------------- | -------------------------------- |
| `poe run`               | Screen tomorrow's games          |
| `poe run-top --top K`   | Show top K betting opportunities |
| `poe run-days --days N` | Screen next N days               |

### Backtest Commands

#### Aggregated Backtests
| Command                                       | Description                                                  |
| --------------------------------------------- | ------------------------------------------------------------ |
| `poe backtest-all --weeks N`                  | Backtest ALL major + minor European leagues                  |
| `poe backtest-gulf --weeks N`                 | Backtest ALL Persian Gulf leagues                            |
| `poe backtest-all-global --weeks N`           | Backtest ALL leagues (Major + Minor European + Persian Gulf) |
| `poe backtest-all-global --weeks N --debug=1` | Same as above with detailed match-by-match debug output      |

**Note**: Add `--debug=1` to any backtest command (or `--debug` for direct CLI usage) to see detailed match-by-match information including:
- Match details (date, teams, competition)
- Actual match results
- Our predictions (team, probability, confidence)
- Whether the prediction was correct or incorrect
- Key reasoning factors

#### Individual League Backtests
| Command                             | Description          |
| ----------------------------------- | -------------------- |
| `poe backtest-bundesliga --weeks N` | 🇩🇪 Bundesliga         |
| `poe backtest-pl --weeks N`         | 🇬🇧 Premier League     |
| `poe backtest-liga --weeks N`       | 🇪🇸 La Liga            |
| `poe backtest-seriea --weeks N`     | 🇮🇹 Serie A            |
| `poe backtest-ligue1 --weeks N`     | 🇫🇷 Ligue 1            |
| `poe backtest-saudi --weeks N`      | 🇸🇦 Saudi Pro League   |
| `poe backtest-qatar --weeks N`      | 🇶🇦 Qatar Stars League |
| `poe backtest-uae --weeks N`        | 🇦🇪 UAE Pro League     |

### Development Commands
| Command         | Description                 |
| --------------- | --------------------------- |
| `poe lint`      | Run linter                  |
| `poe lint-fix`  | Fix linting issues          |
| `poe format`    | Format code                 |
| `poe typecheck` | Run type checker            |
| `poe test`      | Run tests                   |
| `poe test-cov`  | Run tests with coverage     |
| `poe check`     | Run all code quality checks |
| `poe fix`       | Fix linting and format code |
| `poe dev`       | Fix code and run tests      |

## 🏆 League IDs

### Major European Leagues
| ID  | League         | Country   |
| --- | -------------- | --------- |
| 1   | Bundesliga     | 🇩🇪 Germany |
| 2   | Premier League | 🇬🇧 England |
| 3   | La Liga        | 🇪🇸 Spain   |
| 4   | Serie A        | 🇮🇹 Italy   |
| 5   | Ligue 1        | 🇫🇷 France  |

### Minor European Leagues
| ID  | League             | Country       |
| --- | ------------------ | ------------- |
| 68  | Belgian Pro League | 🇧🇪 Belgium     |
| 8   | Primeira Liga      | 🇵🇹 Portugal    |
| 6   | Super Lig          | 🇹🇷 Turkey      |
| 196 | Eredivisie         | 🇳🇱 Netherlands |

### Persian Gulf Leagues
| ID  | League             | Country        |
| --- | ------------------ | -------------- |
| 313 | Saudi Pro League   | 🇸🇦 Saudi Arabia |
| 305 | Qatar Stars League | 🇶🇦 Qatar        |
| 354 | UAE Pro League     | 🇦🇪 UAE          |

Use `slickbet competitions --country <name>` to find more competition IDs.

## 🧠 How the Model Works

The betting model uses a **9-factor weighted scoring system**:

| Factor             | Weight | Description                                              |
| ------------------ | ------ | -------------------------------------------------------- |
| **Position**       | 20%    | League table standing differential                       |
| **Odds**           | 18%    | Bookmaker pre-match odds (implied probability)           |
| **Form**           | 16%    | Recent match results (last 5 games)                      |
| **Goals**          | 12%    | Attack/defense strength (goals scored/conceded per game) |
| **Home Advantage** | 9%     | Historical home team advantage                           |
| **Momentum**       | 7%     | First-half lead rate + win rate + comeback ability       |
| **H2H**            | 7%     | Historical head-to-head record                           |
| **Venue Form**     | 6%     | Home/away specific win rates                             |
| **Defense**        | 5%     | Clean sheet rate                                         |

### Double Chance Betting

The model also calculates **double chance** probabilities for safer bets:
- **1X** - Home wins OR Draw (Home doesn't lose)
- **X2** - Away wins OR Draw (Away doesn't lose)
- **12** - Home OR Away wins (No draw)

### Confidence Grades

Each prediction is assigned a grade based on backtest performance:
- 🔥 **HIGH VALUE** - Best picks (DC ≥80%, Win ≥65%)
- ✅ **GOOD BET** - Reliable picks (DC ≥75%, Win ≥60%)
- 👍 **DECENT** - Ok picks (DC ≥70%)
- ⚠️ **RISKY** - Use double chance only

## 📊 Backtest Results

### 1-Week Backtest Results

Based on 1-week backtests across all leagues (103 matches):

#### Aggregated Results
- **Total Matches**: 103
- **Correct Predictions**: 59
- **Overall Accuracy**: 57.3%
- **Draws Encountered**: 31 (30.1%)
- **Accuracy (excl. draws)**: 81.9%
- **Best Recommended Double Chance**: 87.4%

#### League Comparison
| League               | Matches | Accuracy | Excl. Draws | Best DC |
| -------------------- | ------- | -------- | ----------- | ------- |
| 🇮🇹 Serie A            | 8       | 87.5%    | **100.0%**  | 100.0%  |
| 🇵🇹 Primeira Liga      | 7       | 71.4%    | **100.0%**  | 100.0%  |
| 🇩🇪 Bundesliga         | 11      | 63.6%    | **87.5%**   | 90.9%   |
| 🇸🇦 Saudi Pro League   | 12      | 58.3%    | **87.5%**   | 91.7%   |
| 🇬🇧 Premier League     | 9       | 55.6%    | **83.3%**   | 88.9%   |
| 🇫🇷 Ligue 1            | 9       | 55.6%    | **83.3%**   | 88.9%   |
| 🇹🇷 Super Lig          | 8       | 62.5%    | **83.3%**   | 87.5%   |
| 🇳🇱 Eredivisie         | 9       | 44.4%    | **80.0%**   | 88.9%   |
| 🇶🇦 Qatar Stars League | 6       | 50.0%    | **75.0%**   | 83.3%   |
| 🇧🇪 Belgian Pro League | 8       | 50.0%    | **66.7%**   | 75.0%   |
| 🇦🇪 UAE Pro League     | 7       | 57.1%    | **66.7%**   | 71.4%   |
| 🇪🇸 La Liga            | 9       | 33.3%    | **60.0%**   | 77.8%   |

### 12-Week Backtest Results

Based on 12-week backtests across all leagues (979 matches):

#### Aggregated Results
- **Total Matches**: 979
- **Correct Predictions**: 553
- **Overall Accuracy**: 56.5%
- **Draws Encountered**: 262 (26.8%)
- **Accuracy (excl. draws)**: 77.1%
- **Best Recommended Double Chance**: 83.2%

#### League Comparison
| League               | Matches | Accuracy | Excl. Draws | Best DC |
| -------------------- | ------- | -------- | ----------- | ------- |
| 🇵🇹 Primeira Liga      | 79      | 64.6%    | **85.0%**   | 88.6%   |
| 🇸🇦 Saudi Pro League   | 94      | 63.8%    | **82.2%**   | 86.2%   |
| 🇹🇷 Super Lig          | 71      | 49.3%    | **81.4%**   | 88.7%   |
| 🇩🇪 Bundesliga         | 89      | 58.4%    | **81.2%**   | 86.5%   |
| 🇮🇹 Serie A            | 118     | 60.2%    | **78.0%**   | 83.1%   |
| 🇫🇷 Ligue 1            | 72      | 62.5%    | **77.6%**   | 81.9%   |
| 🇪🇸 La Liga            | 98      | 57.1%    | **76.7%**   | 82.7%   |
| 🇳🇱 Eredivisie         | 79      | 50.6%    | **75.5%**   | 83.5%   |
| 🇦🇪 UAE Pro League     | 49      | 55.1%    | **73.0%**   | 79.6%   |
| 🇶🇦 Qatar Stars League | 29      | 62.1%    | **72.0%**   | 75.9%   |
| 🇬🇧 Premier League     | 129     | 48.8%    | **70.8%**   | 79.8%   |
| 🇧🇪 Belgian Pro League | 72      | 48.6%    | **68.6%**   | 77.8%   |

### Key Findings
- **1-week results** show higher accuracy (81.9% excl. draws) but smaller sample size (103 matches)
- **12-week results** provide more reliable statistics with 77.1% accuracy (excl. draws) across 979 matches
- **Double Chance** is the safest bet type with 83.2% accuracy (12-week) and 87.4% (1-week)
- **Primeira Liga** and **Saudi Pro League** consistently show high accuracy across both time periods
- **Draw rate**: 26.8% (12-week) to 30.1% (1-week) - use Double Chance for safer bets
- **Best leagues for predictions**: Primeira Liga, Saudi Pro League, Super Lig, Bundesliga

## 💻 Direct CLI Usage

```bash
# Basic screening
slickbet                          # Screen tomorrow's games
slickbet --top 10                 # Show top 10 opportunities
slickbet --days 5                 # Screen next 5 days

# League filters
slickbet --major-only             # Major European leagues only
slickbet --gulf-only              # Persian Gulf leagues only
slickbet --all-leagues            # All supported leagues (Major + Minor European + Persian Gulf)
slickbet --league 2               # Specific league by ID

# Probability filters
slickbet --min-prob 0.60          # Only ≥60% probability
slickbet --min-conf 0.30          # Only ≥30% confidence

# Output options
slickbet --json                   # JSON output
slickbet --pdf                    # Export to PDF (auto-generated filename)
slickbet --pdf my_report.pdf      # Export to specific PDF file
slickbet --no-stats               # Fast mode (skip detailed stats)

# Backtesting
slickbet backtest --competition 2 --weeks 4     # Premier League, 4 weeks
slickbet backtest --competition 2 --weeks 4 --pdf  # Export backtest to PDF
slickbet backtest --competition 2 --weeks 4 --debug  # With detailed match-by-match debug output
slickbet backtest-all --weeks 4                 # All major + minor European leagues
slickbet backtest-all --weeks 4 --pdf           # Export aggregated results to PDF
slickbet backtest-all --gulf-only --weeks 4     # All Persian Gulf leagues
slickbet backtest-all --include-gulf --weeks 4  # Major + Minor European + Persian Gulf
slickbet backtest-all --include-gulf --weeks 4 --debug  # With detailed match-by-match debug output
```

## 🐍 Python API

```python
from slickbet import BettingScreener, ScreenerConfig

# Create a screener for all leagues
config = ScreenerConfig(
    min_probability=0.60,
    all_leagues=True,
)
screener = BettingScreener(config=config)

# Screen next 3 days
result = screener.screen_days(3)

# Get top 10 betting opportunities (sorted by double chance probability)
for bet in result.get_top_k(10):
    match = bet.match
    dc = bet.double_chance
    
    print(f"🏟️  {match.home_team.name} ({match.home_position}) vs "
          f"{match.away_team.name} ({match.away_position})")
    print(f"🏆  {match.competition}")
    
    # Double chance recommendation
    best_dc, prob = dc.best_double_chance
    print(f"⭐ Recommended: {best_dc} - {prob:.1%}")
    
    # Win bet
    print(f"💰 Win bet: {bet.probability:.1%}")
    print()
```

### Backtesting

```python
from slickbet import Backtester, format_backtest_report

backtester = Backtester()

# Run backtest on Saudi Pro League (4 weeks)
results = backtester.run(
    competition_id="313",
    weeks=4,
)

# Print report
print(format_backtest_report(results))

# Access metrics
print(f"Accuracy (excl. draws): {results.accuracy_excluding_draws:.1%}")
print(f"Best Double Chance: {results.best_double_chance_accuracy:.1%}")
```

## 📁 Project Structure

```
slick-bet/
├── src/
│   └── slickbet/
│       ├── __init__.py      # Package exports
│       ├── api.py           # Livescore API client
│       ├── model.py         # 9-factor betting model
│       ├── screener.py      # Main screener logic
│       ├── backtest.py      # Backtesting module
│       ├── cli.py           # Command-line interface
│       └── pdf_export.py    # PDF report generation
├── tests/                   # Test files
│   ├── __init__.py
│   └── test_model.py
├── assets/
│   └── predictions/        # Generated PDF reports
├── pyproject.toml          # Project config (uv, poe, ruff, mypy)
├── uv.lock                 # Lock file (auto-generated)
├── LICENSE
└── README.md
```

## ⚠️ Disclaimer

This tool is for **educational and entertainment purposes only**. 

- Past performance does not guarantee future results
- Sports betting involves risk of financial loss
- Always predict responsibly and within your means
- Check local laws regarding sports betting in your jurisdiction

## License

MIT License - See [LICENSE](LICENSE) for details.
