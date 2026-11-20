from collections import Counter


def count_words(tokens: list[str]) -> dict:
    """
    Menghitung frekuensi kemunculan setiap kata.

    Input:
        ["python", "java", "python"]

    Output:
        {
            "python": 2,
            "java": 1
        }
    """

    if not isinstance(tokens, list):
        raise TypeError("Input tokens harus berupa list.")

    for token in tokens:
        if not isinstance(token, str):
            raise TypeError("Setiap token harus berupa string.")

        if not token:
            raise ValueError("Token tidak boleh kosong.")

    frequencies = Counter(tokens)

    return dict(frequencies)


def get_most_common(frequencies: dict, limit: int = 10) -> list[tuple[str, int]]:
    """
    Mengambil kata yang paling sering muncul.

    Contoh:
        {
            "python": 5,
            "java": 3,
            "c": 1
        }

    Output:
        [
            ("python", 5),
            ("java", 3)
        ]
    """

    if not isinstance(frequencies, dict):
        raise TypeError("Frequencies harus berupa dictionary.")

    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("Limit harus berupa integer.")

    if limit < 0:
        raise ValueError("Limit tidak boleh negatif.")

    for word, count in frequencies.items():
        if not isinstance(word, str) or not word:
            raise ValueError("Nama kata tidak valid.")

        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("Frekuensi harus berupa integer nonnegatif.")

    counter = Counter(frequencies)

    return counter.most_common(limit)
