# Contributing to miguel_angel

Thank you for your interest in contributing! miguel_angel welcomes contributions from electrical engineers, software developers, UX designers, and technical writers.

## Ways to contribute

- **Report bugs** — open a GitHub Discussion in the Bug category
- **Request features** — open a GitHub Discussion in the Feature request category
- **Submit code** — fork, branch, and open a pull request
- **Improve documentation** — fix typos, add examples, improve clarity
- **Add component symbols** — expand the ISA / IEC / ANSI / IEEE libraries
- **Translate** — help localise the application

## Development setup

```bash
git clone https://github.com/RiCrypto/miguel_angel.git
cd miguel_angel
conda create -n miguel_angel python=3.11
conda activate miguel_angel
pip install -r requirements.txt
pip install -r requirements-auth.txt
pytest tests/ -v
```

## Commit convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add DXF export for SolidWorks Electrical
fix: correct TOTP clock drift window
docs: update security guide with YubiKey instructions
test: add ERC engine unit tests
refactor: extract netlist engine to core module
chore: update ruff to 0.3.0
```

## Pull request checklist

- [ ] Tests pass locally: `pytest tests/ -v`
- [ ] No ruff errors: `ruff check .`
- [ ] Type hints present on all public functions
- [ ] Docstring added to new modules and classes
- [ ] CHANGELOG.md updated if applicable

## Code style

- `ruff` for linting and formatting (replaces flake8 + black)
- `mypy` for static type checking
- Maximum line length: 100 characters
- All public APIs must have type annotations

## Security

Please report security vulnerabilities via GitHub's private advisory system — **not** as public issues. See [docs/guides/security.md](docs/guides/security.md).

## Questions?

Open a Discussion or ask **MiguelBot** inside the application (`F1`).
