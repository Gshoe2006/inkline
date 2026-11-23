"""Money sums for the maths drill, in pounds, euros or dollars, written as people write them where that money is
used.

- Complexity 1-4: coins to count, eight to a sheet. Two or three small coins at 1-2, up to four of any coin at
  3-4, each drawn as a circle with its value, and the total to write ("= ____").
- 5-10: at most 18 sums to a sheet.
- 5-6: adding amounts in steps of ten pence (cents), up to 5.00.
- 7-8: adding and taking away amounts to the penny, up to 10.00.
- 9-10: the same up to 20.00, and change: what's left of a note after spending.

Amounts are kept in pennies (cents) and written for the currency and the language: £1.20 and 45p, $1.20 and 45¢,
€1.20 and 45c in English; 1,20 € and 0,45 € in Spanish and French.
"""

from .. import i18n
from ..rng import pick

CURRENCIES = {"auto": "Your language's money", "GBP": "Pounds (£)", "EUR": "Euros (€)", "USD": "Dollars ($)"}
COINS = {"GBP": (1, 2, 5, 10, 20, 50, 100, 200), "EUR": (1, 2, 5, 10, 20, 50, 100, 200), "USD": (1, 5, 10, 25)}


def currency(choice):
    """The currency for a setting: auto is the euro in Spanish and French, the pound otherwise."""
    if choice in COINS:
        return choice
    return "EUR" if i18n.LANG in ("es", "fr") else "GBP"


def fmt(cents, cur):
    """An amount written as it's written where the money is used."""
    comma = cur == "EUR" and i18n.LANG in ("es", "fr")
    units, rest = divmod(cents, 100)
    if comma:
        return f"{units},{rest:02d} €"
    if cents < 100:
        return f"{cents}{ {'GBP': 'p', 'EUR': 'c', 'USD': '¢'}[cur] }"
    sign = {"GBP": "£", "EUR": "€", "USD": "$"}[cur]
    return f"{sign}{units}.{rest:02d}"


def coin_label(cents, cur):
    """The value printed on a coin: 5p, 20c, 25¢, £1, 2 €."""
    if cents >= 100:
        units = cents // 100
        return f"{units} €" if cur == "EUR" and i18n.LANG in ("es", "fr") else f"{ {'GBP': '£', 'EUR': '€', 'USD': '$'}[cur] }{units}"
    return f"{cents}{ {'GBP': 'p', 'EUR': 'c', 'USD': '¢'}[cur] }"


def _between(rnd, lo, hi):
    return lo + pick(rnd, hi - lo + 1)


def make_sum(rnd, c, cur):
    """One money sum, in the maths drill's form (left, sign, right, answer, blank), its amounts written out; coins
    to count are (labels, "coins", values, total, "result")."""
    coins = COINS[cur]
    if c <= 4:
        pool = [v for v in coins if v <= (10 if c <= 2 else 200)]
        n = _between(rnd, 2, 3 if c <= 2 else 4)
        chosen = sorted((pool[pick(rnd, len(pool))] for _ in range(n)), reverse=True)
        return tuple(coin_label(v, cur) for v in chosen), "coins", tuple(chosen), fmt(sum(chosen), cur), "result"
    step, top = (10, 500) if c <= 6 else (1, 1000) if c <= 8 else (1, 2000)
    if c >= 9 and pick(rnd, 3) == 0:   # change from a note
        note = 1000 if pick(rnd, 2) else 2000
        spent = _between(rnd, 1, note // step - 1) * step
        return fmt(note, cur), "−", fmt(spent, cur), fmt(note - spent, cur), "result"
    a = _between(rnd, 1, top // step - 1) * step
    if c >= 7 and pick(rnd, 2):
        b = _between(rnd, 1, a // step) * step if a > step else step
        if b < a:
            return fmt(a, cur), "−", fmt(b, cur), fmt(a - b, cur), "result"
    b = _between(rnd, 1, max(1, (top - a) // step)) * step
    return fmt(a, cur), "+", fmt(b, cur), fmt(a + b, cur), "result"
