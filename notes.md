# Calculator & Unit Converter: Notes

## What it is
A command-line program in one file (`calculator.py`) with three modes: calculator, currency converter and unit converter. It uses only Python's standard library (Python 3.8+).

Run it: `python3 calculator.py`

## Quick usage

| Mode | Example input | Output |
|---|---|---|
| Calculator | `(2+3)*4**2` | `80` |
| Calculator | `ans/3` | reuses the last result |
| Currency | `100 usd to inr` | `100 USD = 8,800.00 INR` (sample rates) |
| Units | `5 km to mi` | `5 km = 3.106855961 mi` |
| Units | `98.6 f to c` | `98.6 f = 37 c` |

Commands that work in every mode: `list` (show supported items), `back` (return to menu).

## How the code is organised

1. **Calculator**
   - Uses Python's `ast` module to parse the expression, then walks the tree and only allows numbers and the operators `+ - * / // % **`.
   - Avoids `eval()` because `eval` would run any code a user types (for example `__import__("os")`). The program rejects that with "unsupported expression".
   - Guards: division by zero gives a friendly error, and exponents above 1000 are refused so a huge power can't freeze the program.
   - `fmt()` tidies output (`4.0` becomes `4`, and long decimals are trimmed to 10 significant digits).

2. **Currency**
   - `load_rates()` tries a free public API (`open.er-api.com`) with a 5-second timeout.
   - If that fails, it falls back to `SAMPLE_RATES`, a built-in approximate table.
   - Every rate is "how much of this currency equals 1 USD", so any conversion goes source -> USD -> target (`amount / rate[source] * rate[target]`).
   - A regular expression parses input like `100 usd to inr`.

3. **Units**
   - Each category stores a factor to a base unit (metre, kilogram, litre, m/s, second).
   - Convert with `value * factor[source] / factor[target]`.
   - Temperature is special because it needs offsets (for example +32), so it has its own function that goes through Celsius.
   - `ALIASES` maps friendly names (`miles`, `kilograms`) to short codes.
   - Mixing categories (km to kg) gives a clear error.

4. **Main menu**
   - A simple `while True` loop that calls one mode function at a time.
   - Catches Ctrl+C and end-of-input so the program exits cleanly.

## Concepts you can learn from this project
- Functions and loops: the menu loop and each mode's input loop.
- Dictionaries: unit factors, aliases and exchange rates.
- Regular expressions (`re`): parsing `<number> <unit> to <unit>`.
- Error handling: `try/except` and raising `ValueError` with clear messages.
- Safe input handling: parsing instead of `eval()`.
- Network calls with fallback: `urllib` plus a plan for being offline.
- Base-unit design: one factor per unit rather than a rule for every pair.

## Things to be aware of
- Sample currency rates are approximate. Don't use them for real money decisions.
- Gallons, cups and fluid ounces are US measures.
- Results are rounded for display (currency to 2 decimals, others to 10 significant digits).

## Ideas to extend it
- Add more units: area, data size (KB/MB/GB), pressure or energy.
- Add more currencies to `SAMPLE_RATES`.
- Cache live rates to a file so they work offline with recent values.
- Add maths functions such as `sqrt`, `sin` and `pi` to the calculator (whitelist them in `_evaluate`).
- Keep a history of calculations and save it to a file.
- Take command-line arguments (`python3 calculator.py "5 km to mi"`) using `argparse`.
- Write tests for `calculate`, `convert_unit` and `convert_currency`.
