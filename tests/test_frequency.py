import pytest

from processing.frequency import count_words, get_most_common


def test_count_words():
    tokens = ["python", "java", "python", "java", "python"]

    result = count_words(tokens)

    assert result == {"python": 3, "java": 2}


def test_count_empty_tokens():
    assert count_words([]) == {}


def test_count_single_word():
    assert count_words(["python"]) == {"python": 1}


def test_count_case_sensitive():
    tokens = ["Python", "python", "PYTHON"]

    result = count_words(tokens)

    assert result == {"Python": 1, "python": 1, "PYTHON": 1}


def test_invalid_input_type():
    with pytest.raises(TypeError):
        count_words("python java")


def test_invalid_token_type():
    with pytest.raises(TypeError):
        count_words(["python", 123])


def test_empty_token_rejected():
    with pytest.raises(ValueError):
        count_words(["python", ""])


def test_get_most_common():
    frequencies = {"python": 5, "java": 3, "javascript": 7, "c": 1}

    result = get_most_common(frequencies, limit=2)

    assert result == [("javascript", 7), ("python", 5)]


def test_get_most_common_empty():
    assert get_most_common({}) == []


def test_get_most_common_limit_zero():
    frequencies = {"python": 5, "java": 3}

    assert get_most_common(frequencies, limit=0) == []


def test_invalid_limit():
    with pytest.raises(ValueError):
        get_most_common({"python": 5}, limit=-1)


def test_invalid_frequency():
    with pytest.raises(ValueError):
        get_most_common({"python": -5})


def test_invalid_frequency_type():
    with pytest.raises(ValueError):
        get_most_common({"python": 2.5})


def test_invalid_frequencies_type():
    with pytest.raises(TypeError):
        get_most_common(["python", "java"])
