🛠 Installation
=================

- Install a [Python version >=3.10,<3.14](https://www.python.org).
- All SlickBet development uses [*uv*](https://docs.astral.sh/uv/). Install `uv`, then sync 🏃‍♀️:

  ```bash
  uv sync --locked --all-extras --all-groups
  ```

- Documentation build extras (Sphinx / Furo / MyST):

  ```bash
  uv sync --group docs
  ```

- From PyPI (when published):

  ```bash
  pip install slickbet
  # or
  uv add slickbet
  ```

- CLI entry point:

  ```bash
  uv run slickbet --help
  ```

- Task runner is [Poe the Poet](https://poethepoet.natn.io/installation.html):

  ```bash
  uv tool install poethepoet
  poe greet
  ```

Set Livescore API credentials:

```bash
export LIVESCORE_API_KEY="your_api_key"
export LIVESCORE_API_SECRET="your_api_secret"
```
