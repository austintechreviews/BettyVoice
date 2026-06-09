"""Tests for number-to-words conversion."""

from betty_voice.number_words import number_to_words, number_to_words_digits


def test_zero():
    assert number_to_words(0) == "zero"


def test_ones():
    assert number_to_words(1) == "one"
    assert number_to_words(9) == "nine"
    assert number_to_words(12) == "twelve"
    assert number_to_words(19) == "nineteen"


def test_tens():
    assert number_to_words(20) == "twenty"
    assert number_to_words(42) == "forty-two"
    assert number_to_words(99) == "ninety-nine"


def test_hundreds():
    assert number_to_words(100) == "one hundred"
    assert number_to_words(270) == "two hundred seventy"
    assert number_to_words(999) == "nine hundred ninety-nine"


def test_thousands():
    assert number_to_words(1000) == "one thousand"
    assert number_to_words(3000) == "three thousand"
    assert number_to_words(12000) == "twelve thousand"
    assert number_to_words(42000) == "forty-two thousand"
    assert number_to_words(999999) == "nine hundred ninety-nine thousand nine hundred ninety-nine"


def test_negative():
    assert number_to_words(-5) == "minus five"


def test_digits():
    assert number_to_words_digits(0) == "zero"
    assert number_to_words_digits(270) == "two seven zero"
    assert number_to_words_digits(45) == "four five"
    assert number_to_words_digits(180) == "one eight zero"
