# Repository Guidelines

## Project Structure

- `alloy_cli.py` and `alloy_tui.py` are the command-line and interactive entry points. TUI workflows and saved-case storage live in `alloy_tui_lib/`.
- `alloy_engine.py` coordinates report generation. Property calculations live in `engine_compute_*.py`, material formulas in `physics_*.py`, and tuning defaults in `config/tuning_defaults.py`.
- `elements/` contains per-element JSON data. Preserve names such as `Fe-Iron.json` and keep units explicit in property names. `bolvanki/` contains grayscale texture templates, and `artifacts/` holds generated outputs and experiments.
- `tests/` contains validation, material-modeling, and regression tests. Expected report outputs live in `tests/golden_reports.json`.

## Run, Build, and Test

Run these commands from the repository root.

- `python3 alloy_cli.py --composition Fe:0.98,Cr:0.02 --pretty` prints a JSON compatibility report.
- `python3 alloy_tui.py` opens the interactive alloy calculator.
- `python3 build_alloy_properties_sqlite.py --db /tmp/alloy_properties.sqlite` builds a SQLite database of predefined alloys.
- `python3 -m unittest discover` runs the full suite. Use `python3 -m unittest tests.test_regression_reports` to run the report regression tests alone.
- Texture generation via `generate_tinted_items.py` requires Pillow. Install it in a virtual environment if working on textures. Local tint settings can go in the ignored `.env`.

## Coding and Testing Conventions

Use four-space indentation, `snake_case` for modules and functions, and `PascalCase` for classes. Follow the surrounding type annotations and reuse shared composition parsing and input validation. The repository has no configured formatter, linter, or coverage threshold.

Use `unittest.TestCase`, with files named `test_*.py` and methods named `test_*`. Cover relevant material regimes and invalid inputs when changing calculations or validation. Update golden outputs when a report change is intentional, and explain the changed values.

## Commits and Pull Requests

Git history currently contains only `Initial commit`. Use short, descriptive commit subjects. In pull requests, summarize the behavior change and list the checks you ran. Link the issue when applicable. Include before-and-after report excerpts or images for changes to report output or generated textures.
