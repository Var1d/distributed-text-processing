import pytest

from processing.tokenizer import tokenize


def test_basic_tokenization():
    text = "Python adalah bahasa pemrograman"

    result = tokenize(text)

    assert result == ["python", "adalah", "bahasa", "pemrograman"]


def test_lowercase_conversion():
    text = "PYTHON Java JAVASCRIPT"

    result = tokenize(text)

    assert result == ["python", "java", "javascript"]


def test_remove_punctuation():
    text = "Halo! Apa kabar? Saya baik."

    result = tokenize(text)

    assert result == ["halo", "apa", "kabar", "saya", "baik"]


def test_empty_string():
    assert tokenize("") == []


def test_whitespace_only():
    assert tokenize("   \n\t  ") == []


def test_numbers_are_preserved():
    text = "Python 3.12 dan Java 21"

    result = tokenize(text)

    assert result == ["python", "3", "12", "dan", "java", "21"]


def test_unicode_characters():
    text = "Café naïve Über"

    result = tokenize(text)

    assert result == ["café", "naïve", "über"]


def test_apostrophe_preserved():
    text = "don't stop it's working"

    result = tokenize(text)

    assert result == ["don't", "stop", "it's", "working"]


def test_non_string_input():
    with pytest.raises(TypeError):
        tokenize(123)


def test_underscore_is_separator():
    text = "hello_world"

    result = tokenize(text)

    assert result == ["hello", "world"]
