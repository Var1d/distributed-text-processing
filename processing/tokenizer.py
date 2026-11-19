import re


def tokenize(text: str) -> list[str]:
    """
    Memecah teks menjadi token atau kata.

    Ketentuan:
    - Mengubah semua huruf menjadi lowercase.
    - Mengabaikan tanda baca.
    - Mempertahankan angka.
    - Mendukung karakter Unicode.
    - Mempertahankan apostrof di dalam kata.

    Contoh:
    "Python adalah Bahasa Pemrograman!"

    Menjadi:
    ["python", "adalah", "bahasa", "pemrograman"]
    """

    if not isinstance(text, str):
        raise TypeError("Input harus berupa string.")

    text = text.lower()

    tokens = re.findall(r"[^\W_]+(?:['’][^\W_]+)*", text, flags=re.UNICODE)

    return tokens
