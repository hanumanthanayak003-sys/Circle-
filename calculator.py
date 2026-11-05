#!/usr/bin/env python3
"""
Calculator & Unit Converter
===========================
A beginner-friendly command-line tool with three modes:

  1. Calculator       e.g.  (2 + 3) * 4 ** 2
  2. Currency         e.g.  100 usd to inr
  3. Unit converter   e.g.  5 km to mi     or     98.6 f to c

Run it with:   python3 calculator.py
Needs only Python 3.8+ (no extra packages).
"""

import ast
import json
import operator
import re
import urllib.request

# ---------------------------------------------------------------------------
# 1. CALCULATOR
# ---------------------------------------------------------------------------
# We do NOT use eval() on user input (it can run arbitrary code).
# Instead we parse the expression and only allow plain math.

BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _evaluate(node):
    """Recursively evaluate a parsed math expression."""
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError("only numbers are allowed")
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY_OPS:
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("exponent is too large")
        return BINARY_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
        return UNARY_OPS[type(node.op)](_evaluate(node.operand))
    raise ValueError("unsupported expression")


def calculate(expression):
    """Return the numeric result of a math expression string."""
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        return _evaluate(tree)
    except ZeroDivisionError:
        raise ValueError("cannot divide by zero")
    except SyntaxError:
        raise ValueError("that doesn't look like a valid expression")


def fmt(number):
    """Show numbers nicely: 4.0 -> 4, 3.14159265358979 -> 3.141592654."""
    if isinstance(number, float) and number.is_integer() and abs(number) < 1e15:
        return str(int(number))
    if isinstance(number, float):
        return f"{number:.10g}"
    return str(number)


def calculator_mode():
    print("\n--- Calculator ---")
    print("Operators: + - * / // (whole-number divide) % (remainder) ** (power)")
    print("Use parentheses as needed. Type 'ans' to reuse the last result.")
    print("Type 'back' to return to the main menu.\n")
    last = 0
    while True:
        text = input("calc> ").strip()
        if text.lower() in ("back", "b", "quit", "q"):
            return
        if not text:
            continue
        text = re.sub(r"\bans\b", f"({last})", text, flags=re.IGNORECASE)
        try:
            last = calculate(text)
            print("  =", fmt(last))
        except ValueError as err:
            print("  Error:", err)


# ---------------------------------------------------------------------------
# 2. CURRENCY CONVERSION
# ---------------------------------------------------------------------------
# Live rates come from a free public API. If you're offline (or the API is
# down) we fall back to the SAMPLE rates below. Sample rates are only
# approximate -- don't use them for real money decisions!

RATES_URL = "https://open.er-api.com/v6/latest/USD"

SAMPLE_RATES = {  # value of 1 USD in each currency (approximate)
    "USD": 1.0, "EUR": 0.86, "GBP": 0.76, "INR": 88.0, "JPY": 150.0,
    "AUD": 1.52, "CAD": 1.40, "CNY": 7.10, "CHF": 0.80, "SGD": 1.30,
    "AED": 3.67,
}


def load_rates():
    """Try to download live rates; return (rates, is_live)."""
    try:
        with urllib.request.urlopen(RATES_URL, timeout=5) as response:
            data = json.load(response)
        if data.get("result") == "success":
            return data["rates"], True
    except Exception:
        pass  # any network problem -> use sample rates
    return SAMPLE_RATES, False


def convert_currency(amount, source, target, rates):
    """Convert via USD: source -> USD -> target."""
    if source not in rates:
        raise ValueError(f"unknown currency '{source}'")
    if target not in rates:
        raise ValueError(f"unknown currency '{target}'")
    return amount / rates[source] * rates[target]


CURRENCY_PATTERN = re.compile(
    r"^\s*([\d,]*\.?\d+)\s*([a-zA-Z]{3})\s*(?:to|in|->)\s*([a-zA-Z]{3})\s*$",
    re.IGNORECASE,
)


def currency_mode():
    print("\n--- Currency Converter ---")
    print("Fetching exchange rates...")
    rates, is_live = load_rates()
    if is_live:
        print("Using live rates.")
    else:
        print("Could not reach the rate service - using SAMPLE rates (approximate).")
    print("Format: <amount> <from> to <to>     e.g.  100 usd to inr")
    print("Type 'list' to see currencies, 'back' to return.\n")

    while True:
        text = input("currency> ").strip()
        if text.lower() in ("back", "b", "quit", "q"):
            return
        if text.lower() == "list":
            codes = sorted(rates if is_live else SAMPLE_RATES)
            print("  " + ", ".join(codes))
            continue
        match = CURRENCY_PATTERN.match(text)
        if not match:
            print("  Try something like: 100 usd to eur")
            continue
        amount = float(match.group(1).replace(",", ""))
        source, target = match.group(2).upper(), match.group(3).upper()
        try:
            result = convert_currency(amount, source, target, rates)
            print(f"  {fmt(amount)} {source} = {result:,.2f} {target}")
        except ValueError as err:
            print("  Error:", err)


# ---------------------------------------------------------------------------
# 3. UNIT CONVERSION
# ---------------------------------------------------------------------------
# Each category stores "how many base units is 1 of this unit?".
# Converting = multiply to base, then divide by the target's factor.
# Temperature is special (it uses offsets, not just multiplication).

CATEGORIES = {
    "length (base: metre)": {
        "mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0,
        "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344,
    },
    "mass (base: kilogram)": {
        "mg": 1e-6, "g": 0.001, "kg": 1.0, "t": 1000.0,
        "oz": 0.028349523125, "lb": 0.45359237,
    },
    "volume (base: litre)": {
        "ml": 0.001, "l": 1.0, "tsp": 0.00492892159375,
        "tbsp": 0.01478676478125, "floz": 0.0295735295625,
        "cup": 0.2365882365, "gal": 3.785411784,
    },
    "speed (base: m/s)": {
        "m/s": 1.0, "km/h": 1 / 3.6, "mph": 0.44704, "kn": 0.514444,
    },
    "time (base: second)": {
        "s": 1.0, "min": 60.0, "h": 3600.0, "day": 86400.0, "week": 604800.0,
    },
}

TEMPERATURE_UNITS = {"c", "f", "k"}

# Friendly spellings people might type -> the short code used above.
ALIASES = {
    "millimeter": "mm", "millimeters": "mm", "millimetre": "mm", "millimetres": "mm",
    "centimeter": "cm", "centimeters": "cm", "centimetre": "cm", "centimetres": "cm",
    "meter": "m", "meters": "m", "metre": "m", "metres": "m",
    "kilometer": "km", "kilometers": "km", "kilometre": "km", "kilometres": "km",
    "inch": "in", "inches": "in", "foot": "ft", "feet": "ft",
    "yard": "yd", "yards": "yd", "mile": "mi", "miles": "mi",
    "milligram": "mg", "milligrams": "mg", "gram": "g", "grams": "g",
    "kilogram": "kg", "kilograms": "kg", "kgs": "kg", "tonne": "t", "tonnes": "t",
    "ounce": "oz", "ounces": "oz", "pound": "lb", "pounds": "lb", "lbs": "lb",
    "milliliter": "ml", "milliliters": "ml", "millilitre": "ml", "millilitres": "ml",
    "liter": "l", "liters": "l", "litre": "l", "litres": "l",
    "teaspoon": "tsp", "teaspoons": "tsp", "tablespoon": "tbsp", "tablespoons": "tbsp",
    "cups": "cup", "gallon": "gal", "gallons": "gal", "fl oz": "floz",
    "kph": "km/h", "kmh": "km/h", "knot": "kn", "knots": "kn",
    "sec": "s", "second": "s", "seconds": "s", "minute": "min", "minutes": "min",
    "hr": "h", "hour": "h", "hours": "h", "days": "day", "weeks": "week",
    "celsius": "c", "fahrenheit": "f", "kelvin": "k",
    "°c": "c", "°f": "f",
}


def normalize_unit(text):
    text = text.strip().lower()
    return ALIASES.get(text, text)


def find_category(unit):
    for name, units in CATEGORIES.items():
        if unit in units:
            return name
    return None


def convert_temperature(value, source, target):
    # Go through Celsius as the middle step.
    if source == "c":
        celsius = value
    elif source == "f":
        celsius = (value - 32) * 5 / 9
    else:  # kelvin
        celsius = value - 273.15

    if target == "c":
        return celsius
    if target == "f":
        return celsius * 9 / 5 + 32
    return celsius + 273.15


def convert_unit(value, source, target):
    source, target = normalize_unit(source), normalize_unit(target)

    if source in TEMPERATURE_UNITS and target in TEMPERATURE_UNITS:
        return convert_temperature(value, source, target)

    category = find_category(source)
    if category is None:
        raise ValueError(f"unknown unit '{source}'")
    if target not in CATEGORIES[category]:
        if find_category(target) or target in TEMPERATURE_UNITS:
            raise ValueError(f"can't convert {source} to {target} (different kinds of unit)")
        raise ValueError(f"unknown unit '{target}'")

    units = CATEGORIES[category]
    return value * units[source] / units[target]


UNIT_PATTERN = re.compile(
    r"^\s*(-?[\d,]*\.?\d+)\s*([a-zA-Z°/ ]+?)\s*(?:to|in|->)\s*([a-zA-Z°/ ]+?)\s*$",
    re.IGNORECASE,
)


def show_units():
    print("  Supported units:")
    for name, units in CATEGORIES.items():
        print(f"    {name}: {', '.join(units)}")
    print("    temperature: c, f, k")


def units_mode():
    print("\n--- Unit Converter ---")
    print("Format: <number> <from> to <to>     e.g.  5 km to mi,  98.6 f to c")
    print("Type 'list' to see units, 'back' to return.\n")
    while True:
        text = input("units> ").strip()
        if text.lower() in ("back", "b", "quit", "q"):
            return
        if text.lower() == "list":
            show_units()
            continue
        match = UNIT_PATTERN.match(text)
        if not match:
            print("  Try something like: 10 kg to lb")
            continue
        value = float(match.group(1).replace(",", ""))
        try:
            result = convert_unit(value, match.group(2), match.group(3))
            print(f"  {fmt(value)} {normalize_unit(match.group(2))} = "
                  f"{fmt(result)} {normalize_unit(match.group(3))}")
        except ValueError as err:
            print("  Error:", err)


# ---------------------------------------------------------------------------
# MAIN MENU
# ---------------------------------------------------------------------------

def main():
    print("=" * 40)
    print("  Calculator & Unit Converter")
    print("=" * 40)
    while True:
        print("\nMain menu")
        print("  1) Calculator")
        print("  2) Currency converter")
        print("  3) Unit converter")
        print("  4) Quit")
        try:
            choice = input("Choose 1-4: ").strip()
            if choice == "1":
                calculator_mode()
            elif choice == "2":
                currency_mode()
            elif choice == "3":
                units_mode()
            elif choice in ("4", "q", "quit", "exit"):
                print("Goodbye!")
                return
            else:
                print("Please enter 1, 2, 3 or 4.")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            return


if __name__ == "__main__":
    main()
