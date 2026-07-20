📌 Quick Start
================

Screen all leagues for tomorrow (top 20):

```bash
poe run-all --days=1 --top=20
```

Major European leagues only:

```bash
poe run-major
```

Backtest all leagues for 1 week:

```bash
poe backtest-all-global --weeks=1
```

Python API:

```python
from slickbet import BettingScreener, ScreenerConfig

config = ScreenerConfig(min_probability=0.60, all_leagues=True)
screener = BettingScreener(config=config)
result = screener.screen_days(3)

for bet in result.get_top_k(10):
    best_dc, prob = bet.double_chance.best_double_chance
    print(f"{bet.match.home_team.name} vs {bet.match.away_team.name}: {best_dc} @ {prob:.1%}")
```

Hyperparameter tuning (after populating an API cache):

```bash
slickbet backtest-all --weeks 12 --cache-dir data/api_cache
slickbet tune --cache-dir data/api_cache --trials 20
```
