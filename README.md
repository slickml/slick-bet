# 🎰 SlickBet - Soccer Betting Screener

A Python-based betting screener for soccer games using the Livescore API. Fetches upcoming matches, analyzes team statistics, and ranks betting opportunities by win probability.

## Features

- 📅 **Multi-Day Screening** - Screen matches for the next N days
- 📊 **11-Factor Analysis** - Comprehensive statistical model with xG and reliability metrics
- 🎲 **Double Chance Bets** - Safer betting options (1X, X2, 12)
- 🏆 **Major European Leagues** - Bundesliga, Premier League, La Liga, Serie A, Ligue 1
- 🌍 **Minor European Leagues** - Belgian Pro League, Primeira Liga, Super Lig, Eredivisie, 1. HNL, Ekstraklasa, Premiership, Super League
- 🌏 **Asia Leagues** - Saudi Pro League, Hyundai A-League (Australia)
- 🌎 **Americas Leagues** - Liga Professional (Argentina), Serie A (Brazil), Liga MX (Mexico)
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

# Screen Asia leagues only for 3 days
poe run-asia --days=3

# Screen Americas leagues only for 3 days
poe run-americas --days=3

# Backtest all leagues for 1 week
poe backtest-all-global --weeks=1
```

## 📋 All Commands

### Screener Commands

#### All Leagues (Major + Minor European + Asia + Americas)
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

#### Asia Leagues
| Command                      | Description                        |
| ---------------------------- | ---------------------------------- |
| `poe run-asia --days N`      | Screen all Asia leagues for N days |
| `poe run-saudi --days N`     | 🇸🇦 Saudi Pro League only            |
| `poe run-australia --days N` | 🇦🇺 Hyundai A-League only            |

#### Americas Leagues
| Command                      | Description                            |
| ---------------------------- | -------------------------------------- |
| `poe run-americas --days N`  | Screen all Americas leagues for N days |
| `poe run-argentina --days N` | 🇦🇷 Liga Professional only               |
| `poe run-brazil --days N`    | 🇧🇷 Serie A only                         |
| `poe run-mexico --days N`    | 🇲🇽 Liga MX only                         |

#### Basic Commands
| Command                 | Description                      |
| ----------------------- | -------------------------------- |
| `poe run`               | Screen tomorrow's games          |
| `poe run-top --top K`   | Show top K betting opportunities |
| `poe run-days --days N` | Screen next N days               |

### Backtest Commands

#### Aggregated Backtests
| Command                                       | Description                                                     |
| --------------------------------------------- | --------------------------------------------------------------- |
| `poe backtest-all --weeks N`                  | Backtest ALL major + minor European leagues                     |
| `poe backtest-asia --weeks N`                 | Backtest ALL Asia leagues (Saudi, Australia)                    |
| `poe backtest-all-global --weeks N`           | Backtest ALL leagues (Major + Minor European + Asia + Americas) |
| `poe backtest-all-global --weeks N --debug=1` | Same as above with detailed match-by-match debug output         |

**Note**: Add `--debug=1` to any backtest command (or `--debug` for direct CLI usage) to see detailed match-by-match information including:
- Match details (date, teams, competition)
- Actual match results
- Our predictions (team, probability, confidence)
- Whether the prediction was correct or incorrect
- Key reasoning factors

#### Individual League Backtests
| Command                             | Description         |
| ----------------------------------- | ------------------- |
| `poe backtest-bundesliga --weeks N` | 🇩🇪 Bundesliga        |
| `poe backtest-pl --weeks N`         | 🇬🇧 Premier League    |
| `poe backtest-liga --weeks N`       | 🇪🇸 La Liga           |
| `poe backtest-seriea --weeks N`     | 🇮🇹 Serie A           |
| `poe backtest-ligue1 --weeks N`     | 🇫🇷 Ligue 1           |
| `poe backtest-saudi --weeks N`      | 🇸🇦 Saudi Pro League  |
| `poe backtest-australia --weeks N`  | 🇦🇺 Hyundai A-League  |
| `poe backtest-argentina --weeks N`  | 🇦🇷 Liga Professional |
| `poe backtest-brazil --weeks N`     | 🇧🇷 Serie A           |
| `poe backtest-mexico --weeks N`     | 🇲🇽 Liga MX           |

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
| 17  | 1. HNL             | 🇭🇷 Croatia     |
| 60  | Ekstraklasa        | 🇵🇱 Poland      |
| 75  | Premiership        | 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland    |
| 9   | Super League       | 🇬🇷 Greece      |

### Asia Leagues
| ID  | League           | Country        |
| --- | ---------------- | -------------- |
| 313 | Saudi Pro League | 🇸🇦 Saudi Arabia |
| 67  | Hyundai A-League | 🇦🇺 Australia    |

### Americas Leagues
| ID  | League            | Country     |
| --- | ----------------- | ----------- |
| 23  | Liga Professional | 🇦🇷 Argentina |
| 24  | Serie A           | 🇧🇷 Brazil    |
| 45  | Liga MX           | 🇲🇽 Mexico    |

Use `slickbet competitions --country <name>` to find more competition IDs.

## 🧠 How the Model Works

The betting model uses an **11-factor weighted scoring system** with advanced statistics:

| Factor             | Weight | Description                                                                                   |
| ------------------ | ------ | --------------------------------------------------------------------------------------------- |
| **Position**       | 19%    | League table standing differential                                                            |
| **Odds**           | 17%    | Bookmaker pre-match odds (implied probability)                                                |
| **Form**           | 15%    | Recent match results (last 5 games)                                                           |
| **Goals**          | 11%    | Attack/defense strength (goals scored/conceded per game)                                      |
| **Home Advantage** | 9%     | Historical home team advantage                                                                |
| **Momentum**       | 6%     | First-half lead rate + win rate + comeback ability                                            |
| **H2H**            | 7%     | Historical head-to-head record                                                                |
| **Venue Form**     | 6%     | Home/away specific win rates                                                                  |
| **Defense**        | 5%     | Clean sheet rate                                                                              |
| **Match Stats**    | 5%     | Possession, attacks, shots (includes **xG** at 28%, **xGD** at 15%, **Shot Accuracy** at 10%) |
| **Reliability**    | 4%     | Team discipline based on cards (fewer cards = more reliable)                                  |

**Note**: The Match Stats factor includes **xG (Expected Goals)** weighted at 28%, **xGD (Expected Goal Difference)** at 15%, and **Shot Accuracy** at 10% within that factor. The Reliability factor measures team discipline - teams with fewer yellow/red cards are more predictable and reliable for betting.

### 📊 Key Statistical Predictors

The model incorporates advanced statistical metrics that are proven predictors of soccer match outcomes:

#### Expected Goals (xG)
- **Premier metric** for evaluating the quality of scoring chances
- Directly correlates with team success and future performance
- Weighted at **28%** within the Match Stats factor (highest weight)
- Calculated from historical match statistics, measuring shot quality and chance creation
- Teams with higher xG averages are more likely to score and win

#### Expected Goal Difference (xGD)
- Strong predictor of a team's points per match over a season
- Calculated as the difference between team's xG and opponent's xG (xG - xGA)
- Weighted at **15%** within the Match Stats factor
- Teams with positive xGD consistently outperform those with negative xGD

#### Shots on Target
- Often cited as the **strongest in-game correlate of winning**
- Outperforms raw possession or total shots in predictive power
- Weighted at **12%** within the Match Stats factor
- More reliable indicator than total shots, as it measures actual goal-scoring opportunities

#### Shot Accuracy
- Measures the quality of chances created (shots on target / total shots)
- **More predictive than total shots alone** - indicates better chance quality
- Weighted at **10%** within the Match Stats factor
- Teams with higher shot accuracy create better scoring opportunities

#### Goal Conversion Rate
- Measures efficiency in turning opportunities into actual goals
- Calculated from goals scored relative to shots on target
- Weighted at **8%** within the Match Stats factor
- Teams with higher conversion rates are more clinical and dangerous

#### Defensive Metrics (xGA - Expected Goals Against)
- Lowering expected goals against is **as crucial for predicting wins** as high offensive xG
- Measured through **goals conceded per game** in the Goals factor
- **Defense factor (5% weight)** specifically evaluates clean sheet rates
- Teams that consistently limit opponent chances (low xGA) are more likely to win

#### How These Metrics Work Together

The model combines these statistical predictors with traditional factors (form, position, H2H) to create a comprehensive prediction:

- **Match Stats (5% total)**: 
  - xG: **28%** (most predictive metric)
  - xGD: **15%** (strong predictor of points per match)
  - Possession: **18%**
  - Shots on Target: **12%** (strongest in-game correlate)
  - Shot Accuracy: **10%** (quality indicator)
  - Goal Conversion Rate: **8%** (efficiency)
  - Dangerous Attacks: **6%**
  - Attacks: **2%**
  - Corners: **1%**
- **Goals (11%)**: Incorporates attack/defense differential (goals scored vs conceded)
- **Defense (5%)**: Clean sheet rate as a proxy for defensive xGA performance

This multi-layered approach ensures that both offensive quality (xG, xGD, shots on target, shot accuracy) and defensive solidity (xGA, clean sheets) are properly weighted in predictions.

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

Based on 1-week backtests across all leagues (147 matches):

#### Aggregated Results
- **Total Matches**: 147
- **Correct Predictions**: 84
- **Overall Accuracy**: 57.1%
- **Draws Encountered**: 42 (28.6%)
- **Accuracy (excl. draws)**: 80.0%
- **Best Recommended Double Chance**: 84.3%

#### League Comparison
| League               | Matches | Accuracy | Excl. Draws | Best DC |
| -------------------- | ------- | -------- | ----------- | ------- |
| 🇫🇷 Ligue 1            | 9       | 66.7%    | **100.0%**  | 100.0%  |
| 🇬🇷 Super League       | 7       | 85.7%    | **100.0%**  | 100.0%  |
| 🇸🇦 Saudi Pro League   | 15      | 60.0%    | **100.0%**  | 100.0%  |
| 🇧🇷 Serie A            | 3       | 100.0%   | **100.0%**  | 100.0%  |
| 🇲🇽 Liga MX            | 9       | 66.7%    | **100.0%**  | 100.0%  |
| 🇮🇹 Serie A            | 10      | 80.0%    | **88.9%**   | 90.0%   |
| 🇩🇪 Bundesliga         | 9       | 66.7%    | **85.7%**   | 88.9%   |
| 🇬🇧 Premier League     | 10      | 60.0%    | **85.7%**   | 90.0%   |
| 🇵🇹 Primeira Liga      | 9       | 66.7%    | **85.7%**   | 88.9%   |
| 🇹🇷 Super Lig          | 9       | 66.7%    | **85.7%**   | 88.9%   |
| 🇳🇱 Eredivisie         | 9       | 44.4%    | **80.0%**   | 88.9%   |
| 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Premiership        | 7       | 57.1%    | **80.0%**   | 85.7%   |
| 🇵🇱 Ekstraklasa        | 9       | 77.8%    | **77.8%**   | 77.8%   |
| 🇪🇸 La Liga            | 10      | 40.0%    | **66.7%**   | 80.0%   |
| 🇧🇪 Belgian Pro League | 8       | 50.0%    | **66.7%**   | 75.0%   |
| 🇦🇷 Liga Professional  | 21      | 38.1%    | **66.7%**   | 81.0%   |
| 🇭🇷 1. HNL             | 5       | 40.0%    | **50.0%**   | 60.0%   |
| 🇦🇺 Hyundai A-League   | 5       | 40.0%    | **50.0%**   | 60.0%   |

### Key Findings (1-Week Results)
- **Overall accuracy**: 57.1% (80.0% excluding draws) across 147 matches
- **Double Chance** is the safest bet type with **84.3% accuracy**
- **Top performing leagues** (excl. draws):
  - 🇫🇷 Ligue 1: 100.0% (9 matches)
  - 🇬🇷 Super League: 100.0% (7 matches)
  - 🇸🇦 Saudi Pro League: 100.0% (15 matches)
  - 🇧🇷 Serie A: 100.0% (3 matches)
  - 🇲🇽 Liga MX: 100.0% (9 matches)
  - 🇮🇹 Serie A: 88.9% (10 matches)
- **Draw rate**: 28.6% - use Double Chance for safer bets
- **Best leagues for predictions**: Ligue 1, Super League, Saudi Pro League, Serie A (Brazil), Liga MX

## 💻 Direct CLI Usage

```bash
# Basic screening
slickbet                          # Screen tomorrow's games
slickbet --top 10                 # Show top 10 opportunities
slickbet --days 5                 # Screen next 5 days

# League filters
slickbet --major-only             # Major European leagues only
slickbet --asia-only              # Asia leagues only (Saudi, Australia)
slickbet --americas-only          # Americas leagues only (Argentina, Brazil, Mexico)
slickbet --all-leagues            # All supported leagues (Major + Minor European + Asia + Americas)
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
slickbet backtest-all --asia-only --weeks 4     # All Asia leagues (Saudi, Australia)
slickbet backtest-all --americas-only --weeks 4 # All Americas leagues (Argentina, Brazil, Mexico)
slickbet backtest-all --include-asia --weeks 4 # Major + Minor European + Asia
slickbet backtest-all --include-asia --include-americas --weeks 4  # Major + Minor European + Asia + Americas
slickbet backtest-all --include-asia --include-americas --weeks 4 --debug  # With detailed match-by-match debug output
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
│       ├── model.py         # 11-factor betting model (includes xG and reliability)
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
