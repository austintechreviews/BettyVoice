"""Number-to-English-words conversion for cockpit-assistant responses."""

_ONES = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen",
]

_TENS = [
    "", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
    "eighty", "ninety",
]


def number_to_words(n: int) -> str:
    """Convert a non-negative integer to English words.

    Handles 0 through 999,999. Falls back to digit string beyond that.
    """
    if n < 0:
        return f"minus {number_to_words(-n)}"
    if n < 20:
        return _ONES[n]
    if n < 100:
        t = _TENS[n // 10]
        r = n % 10
        return t if r == 0 else f"{t}-{_ONES[r]}"
    if n < 1000:
        h = _ONES[n // 100] + " hundred"
        r = n % 100
        return h if r == 0 else f"{h} {number_to_words(r)}"
    if n < 1_000_000:
        t = number_to_words(n // 1000) + " thousand"
        r = n % 1000
        return t if r == 0 else f"{t} {number_to_words(r)}"
    return str(n)


def number_to_words_digits(n: int) -> str:
    """Convert an integer to space-separated digit words.

    Example: 270 -> "two seven zero"
    """
    return " ".join(_ONES[int(d)] for d in str(abs(n)))
