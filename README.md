# 🎰 SlickBet - Soccer Betting Screener

A Python-based betting screener for soccer games using the Livescore API. Fetches upcoming matches, analyzes team statistics, and ranks betting opportunities by win probability.

## Features

- 📅 **Multi-Day Screening** - Screen matches for the next N days
- 📊 **12-Factor Analysis** - Comprehensive statistical model with xG (Expected Goals), match stats, and reliability metrics
- 🎲 **Double Chance Bets** - Safer betting options (1X, X2, 12)
- 🏆 **Major European Leagues** - Bundesliga, Premier League, La Liga, Serie A, Ligue 1
- 🌍 **Minor European Leagues** - Belgian Pro League, Primeira Liga, Super Lig, Eredivisie, 1. HNL, Ekstraklasa, Premiership, Super League
- 🌏 **Asia Leagues** - Saudi Pro League, Hyundai A-League (Australia), J. League (Japan)
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
| `poe run-australia --days N`  | 🇦🇺 Hyundai A-League only            |
| `poe run-japan --days N`     | 🇯🇵 J. League only                  |

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
| `poe backtest-asia --weeks N`                 | Backtest ALL Asia leagues (Saudi, Australia, Japan)              |
| `poe backtest-all-global --weeks N`           | Backtest ALL leagues (Major + Minor European + Asia + Americas) |
| `poe backtest-all-global --weeks N --debug=1` | Same as above with detailed match-by-match debug output         |

**Note**: Add `--debug=1` to any backtest command (or `--debug` for direct CLI usage) to see detailed match-by-match information including:
- Match details (date, teams, competition)
- Actual match results
- Our predictions (team, probability, confidence)
- Whether the prediction was correct or incorrect
- Key reasoning factors

#### Backtest API cache (fast reruns & hyperparameter tuning)

When backtesting over many weeks (e.g. 12), the same API data is reused across runs. You can cache all API responses locally so later runs and hyperparameter optimization avoid the API entirely:

1. **First run** – fetch and cache (e.g. 12 weeks, one or more leagues):

   ```bash
   slickbet backtest --weeks 12 --cache-dir data/api_cache
   # or
   slickbet backtest-all --weeks 12 --cache-dir data/api_cache
   ```

2. **Later runs** – use cache only (no API calls, no credentials needed):

   ```bash
   slickbet backtest --weeks 12 --cache-dir data/api_cache --cache-only
   ```

Use the same `--cache-dir` for all runs so the cache is shared. The cache is keyed by endpoint and request parameters (e.g. competition, date range, team IDs), so it works across different backtest commands. Ideal for tuning model weights or running many backtest variants without re-fetching.

**Note**: For `poe backtest-all-global`, use `--cache-only=1` (with `=1`) when running offline.

#### Hyperparameter tuning

After populating the cache, run tuning to find better model weights:

```bash
# Tune with 20 random weight configurations (default)
slickbet tune --cache-dir data/api_cache

# Or via poe
poe tune --cache-dir data/12_weeks_cache

# More trials, optimize double-chance accuracy
slickbet tune --cache-dir data/api_cache --trials 50 --metric best_dc

# Perturb near defaults instead of fully random
slickbet tune --cache-dir data/api_cache --strategy near_default
```

The script reports the best weights and prints code you can copy into `model.py`.

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
| `poe backtest-japan --weeks N`      | 🇯🇵 J. League         |
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
| 28  | J. League        | 🇯🇵 Japan        |

### Americas Leagues
| ID  | League            | Country     |
| --- | ----------------- | ----------- |
| 23  | Liga Professional | 🇦🇷 Argentina |
| 24  | Serie A           | 🇧🇷 Brazil    |
| 45  | Liga MX           | 🇲🇽 Mexico    |

Use `slickbet competitions --country <name>` to find more competition IDs.

## 🧠 How the Model Works

The betting model uses a **12-factor weighted scoring system** (tuned weights) with advanced statistics:

| Factor             | Weight | Description                                                                                   |
| ------------------ | ------ | --------------------------------------------------------------------------------------------- |
| **Venue Form**     | 20.6%  | Home/away specific win rates                                                                  |
| **Momentum**       | 12.0%  | First-half lead rate + win rate + comeback ability                                            |
| **Defense**        | 10.4%  | Clean sheet rate                                                                              |
| **Home Advantage** | 9.5%   | Historical home team advantage                                                                |
| **Reliability**    | 8.7%   | Team discipline based on cards (fewer cards = more reliable)                                  |
| **Goals**          | 8.6%   | Attack/defense strength (goals scored/conceded per game)                                      |
| **Match Stats**    | 7.1%   | Possession, attacks, shots (xG is a separate factor below)                                    |
| **H2H**            | 6.1%   | Historical head-to-head record                                                                |
| **Odds**           | 5.5%   | Bookmaker pre-match odds (implied probability)                                                |
| **Position**       | 4.7%   | League table standing differential                                                            |
| **Form**           | 3.3%   | Recent match results (last 5 games)                                                           |
| **xG**             | 3.7%   | Expected Goals differential (quality of chances created)                                     |

**Note**: Weights are from hyperparameter tuning (`slickbet tune`). xG is a standalone factor; Match Stats covers possession, shots on target, shot accuracy, and related stats. Reliability measures discipline (fewer cards = more predictable).

### 📊 Key Statistical Predictors

The model incorporates advanced statistical metrics that are proven predictors of soccer match outcomes:

#### Expected Goals (xG)
- **Premier metric** for evaluating the quality of scoring chances
- Directly correlates with team success and future performance
- **Standalone factor (3.7% weight)** in the model; also referenced in Match Stats reasoning (xGD)
- Calculated from historical match statistics, measuring shot quality and chance creation
- Teams with higher xG averages are more likely to score and win

#### Expected Goal Difference (xGD)
- Strong predictor of a team's points per match over a season
- Calculated as the difference between team's xG and opponent's xG (xG - xGA)
- Shown in xG factor reasoning; Match Stats factor uses possession, shots, conversion, etc.
- Teams with positive xGD consistently outperform those with negative xGD

#### Shots on Target & Shot Accuracy
- Shots on target are often cited as the **strongest in-game correlate of winning**
- Shot accuracy (on target / total shots) indicates chance quality
- Both feed into the **Match Stats factor (7.1%)** along with possession, conversion, attacks, corners
- More reliable than raw possession or total shots alone

#### Goal Conversion Rate
- Measures efficiency in turning opportunities into actual goals
- Calculated from goals scored relative to shots on target
- Part of the Match Stats factor
- Teams with higher conversion rates are more clinical and dangerous

#### Defensive Metrics (xGA - Expected Goals Against)
- Lowering expected goals against is **as crucial for predicting wins** as high offensive xG
- Measured through **goals conceded per game** in the Goals factor
- **Defense factor (10.4% weight)** specifically evaluates clean sheet rates
- Teams that consistently limit opponent chances (low xGA) are more likely to win

#### How These Metrics Work Together

The model combines these statistical predictors with traditional factors (form, position, H2H) to create a comprehensive prediction:

- **Venue Form (20.6%)**: Home/away specific performance (tuned weight)
- **Momentum (12.0%)**: First-half dominance and consistency
- **Defense (10.4%)**: Clean sheet rate as a proxy for defensive solidity
- **Goals (8.6%)**: Attack/defense differential (goals scored vs conceded)
- **Match Stats (7.1%)**: Possession, shots on target, shot accuracy, conversion, attacks, corners (xG is a separate 3.7% factor)
- **xG (3.7%)**: Expected Goals differential as a standalone factor

This multi-layered approach ensures that both offensive quality (xG, goals, shots) and defensive solidity (clean sheets, goals conceded) are properly weighted in predictions.

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

Based on 1-week backtests across all leagues (165 matches, tuned weights):

#### League Comparison
| League                     | Matches | Accuracy | Excl. Draws | Best DC |
| -------------------------- | ------- | -------- | ----------- | ------- |
| 🇫🇷 Ligue 1                | 9       | 66.7%    | 100.0%      | 100.0%  |
| 🇧🇪 Belgian Pro League     | 8       | 75.0%    | 100.0%      | 100.0%  |
| 🇳🇱 Eredivisie             | 9       | 55.6%    | 100.0%      | 100.0%  |
| 🇵🇱 Ekstraklasa            | 9       | 100.0%   | 100.0%      | 100.0%  |
| 🇸🇦 Saudi Pro League       | 13      | 69.2%    | 100.0%      | 100.0%  |
| 🇧🇷 Serie A                 | 7       | 57.1%    | 100.0%      | 100.0%  |
| 🇲🇽 Liga MX                | 9       | 66.7%    | 100.0%      | 100.0%  |
| 🇦🇷 Liga Professional      | 17      | 47.1%    | 88.9%       | 94.1%   |
| 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Premiership       | 10      | 70.0%    | 87.5%       | 90.0%   |
| 🇩🇪 Bundesliga             | 9       | 66.7%    | 85.7%       | 88.9%   |
| 🇬🇧 Premier League         | 10      | 60.0%    | 85.7%       | 90.0%   |
| 🇵🇹 Primeira Liga          | 9       | 66.7%    | 85.7%       | 88.9%   |
| 🇹🇷 Super Lig              | 9       | 66.7%    | 85.7%       | 88.9%   |
| 🇬🇷 Super League           | 8       | 75.0%    | 85.7%       | 87.5%   |
| 🇮🇹 Serie A                | 10      | 70.0%    | 77.8%       | 80.0%   |
| 🇪🇸 La Liga                | 10      | 40.0%    | 66.7%       | 80.0%   |
| 🇭🇷 1. HNL                 | 5       | 40.0%    | 50.0%       | 60.0%   |
| 🇦🇺 Hyundai A-League       | 5       | 40.0%    | 50.0%       | 60.0%   |

#### Key Findings (1-Week Results)
- **Total matches**: 165 across 18 leagues (tuned model)
- **Leagues with 100% Excl. Draws / Best DC**: Ligue 1, Belgian Pro League, Eredivisie, Ekstraklasa, Saudi Pro League, Serie A (Brazil), Liga MX
- **Double Chance** remains the safest bet type; use it for leagues with lower win accuracy
- **Lower sample leagues** (1. HNL, Hyundai A-League: 5 matches each) show more variance

### 12-Week Backtest Results (Tuned Weights)

Weights below were tuned via `slickbet tune` on 12 weeks of cached data (all leagues). The model uses these weights by default.

#### Current model weights (`BettingModel.WEIGHTS`)

These are the tuned weights from `slickbet tune` (12-week backtest, all leagues). They are the single source of truth in `src/slickbet/model.py`.

| Factor      | Weight |
| ----------- | ------ |
| defense     | 10.42% |
| form        | 3.33%  |
| goals       | 8.55%  |
| h2h         | 6.05%  |
| home        | 9.45%  |
| match_stats | 7.06%  |
| momentum    | 11.95% |
| odds        | 5.49%  |
| position    | 4.74%  |
| reliability | 8.74%  |
| venue_form  | 20.57% |
| xg          | 3.65%  |

Raw values (copy from `model.py`):

```python
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
```

#### Latest league comparison with tuned parameters over 12-weeks of data

| League               | Matches | Accuracy | Excl. Draws | Best DC |
| -------------------- | ------- | -------- | ----------- | ------- |
| 🇸🇦 Saudi Pro League   | 102     | 69.6%    | 91.0%       | 93.1%   |
| 🇵🇹 Primeira Liga      | 81      | 67.9%    | 88.7%       | 91.4%   |
| 🇬🇷 Super League       | 60      | 70.0%    | 87.5%       | 90.0%   |
| 🇭🇷 1. HNL             | 33      | 60.6%    | 87.0%       | 90.9%   |
| 🇵🇱 Ekstraklasa        | 39      | 66.7%    | 86.7%       | 89.7%   |
| 🇳🇱 Eredivisie         | 79      | 57.0%    | 84.9%       | 89.9%   |
| 🇫🇷 Ligue 1            | 72      | 66.7%    | 82.8%       | 86.1%   |
| 🇹🇷 Super Lig          | 72      | 50.0%    | 81.8%       | 88.9%   |
| 🇮🇹 Serie A            | 120     | 63.3%    | 81.7%       | 85.8%   |
| 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Premiership        | 78      | 62.8%    | 81.7%       | 85.9%   |
| 🇲🇽 Liga MX            | 53      | 58.5%    | 79.5%       | 84.9%   |
| 🇪🇸 La Liga            | 99      | 58.6%    | 78.4%       | 83.8%   |
| 🇩🇪 Bundesliga         | 89      | 56.2%    | 78.1%       | 84.3%   |
| 🇦🇷 Liga Professional  | 75      | 49.3%    | 75.5%       | 84.0%   |
| 🇧🇷 Serie A            | 68      | 57.4%    | 75.0%       | 80.9%   |
| 🇧🇪 Belgian Pro League | 72      | 52.8%    | 74.5%       | 81.9%   |
| 🇬🇧 Premier League     | 130     | 50.0%    | 72.2%       | 80.8%   |
| 🇦🇺 Hyundai A-League   | 65      | 58.5%    | 70.4%       | 75.4%   |

#### Before vs after tuning (comparison)

| League             | Accuracy (before → after) | Excl. draws (before → after) | Best DC (before → after) |
| ------------------ | ------------------------- | ---------------------------- | ------------------------ |
| Saudi Pro League   | 67.6% → **69.6%** (+2.0)  | 88.5% → **91.0%** (+2.5)     | 91.2% → **93.1%** (+1.9) |
| Primeira Liga      | 66.7% → **67.9%** (+1.2)  | 87.1% → **88.7%** (+1.6)     | 90.1% → **91.4%** (+1.3) |
| Super League       | 70.0% → 70.0% (0)         | 87.5% → 87.5% (0)            | 90.0% → 90.0% (0)        |
| 1. HNL             | 57.6% → **60.6%** (+3.0)  | 82.6% → **87.0%** (+4.4)     | 87.9% → **90.9%** (+3.0) |
| Ekstraklasa        | 61.5% → **66.7%** (+5.2)  | 80.0% → **86.7%** (+6.7)     | 84.6% → **89.7%** (+5.1) |
| Eredivisie         | 57.0% → 57.0% (0)         | 84.9% → 84.9% (0)            | 89.9% → 89.9% (0)        |
| Ligue 1            | 65.3% → **66.7%** (+1.4)  | 81.0% → **82.8%** (+1.8)     | 84.7% → **86.1%** (+1.4) |
| Super Lig          | 50.0% → 50.0% (0)         | 81.8% → 81.8% (0)            | 88.9% → 88.9% (0)        |
| Serie A            | 62.5% → **63.3%** (+0.8)  | 80.6% → **81.7%** (+1.1)     | 85.0% → **85.8%** (+0.8) |
| Premiership        | 64.1% → 62.8% (−1.3)      | 83.3% → 81.7% (−1.6)         | 87.2% → 85.9% (−1.3)     |
| Liga MX            | 60.4% → 58.5% (−1.9)      | 82.1% → 79.5% (−2.6)         | 86.8% → 84.9% (−1.9)     |
| La Liga            | 57.6% → **58.6%** (+1.0)  | 77.0% → **78.4%** (+1.4)     | 82.8% → **83.8%** (+1.0) |
| Bundesliga         | 53.9% → **56.2%** (+2.3)  | 75.0% → **78.1%** (+3.1)     | 82.0% → **84.3%** (+2.3) |
| Liga Professional  | 50.7% → 49.3% (−1.4)      | 77.6% → 75.5% (−2.1)         | 85.3% → 84.0% (−1.3)     |
| Serie A (Brazil)   | 58.8% → 57.4% (−1.4)      | 76.9% → 75.0% (−1.9)         | 82.4% → 80.9% (−1.5)     |
| Belgian Pro League | 48.6% → **52.8%** (+4.2)  | 68.6% → **74.5%** (+5.9)     | 77.8% → **81.9%** (+4.1) |
| Premier League     | 49.2% → **50.0%** (+0.8)  | 71.1% → **72.2%** (+1.1)     | 80.0% → **80.8%** (+0.8) |
| Hyundai A-League   | 56.9% → **58.5%** (+1.6)  | 68.5% → **70.4%** (+1.9)     | 73.8% → **75.4%** (+1.6) |

Tuning improved most leagues (especially Ekstraklasa, 1. HNL, Belgian Pro League); a few (Premiership, Liga MX, Liga Professional, Serie A Brazil) are slightly worse with the tuned weights.

## 💻 Direct CLI Usage

```bash
# Basic screening
slickbet                          # Screen tomorrow's games
slickbet --top 10                 # Show top 10 opportunities
slickbet --days 5                 # Screen next 5 days

# League filters
slickbet --major-only             # Major European leagues only
slickbet --asia-only              # Asia leagues only (Saudi, Australia, Japan)
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
slickbet backtest-all --asia-only --weeks 4     # All Asia leagues (Saudi, Australia, Japan)
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
