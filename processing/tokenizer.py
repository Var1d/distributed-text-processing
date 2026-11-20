import re


def tokenize(text: str) -> list[str]:
    """Tokenisasi Unicode, huruf kecil, angka dipertahankan, apostrof internal diizinkan."""
    if not isinstance(text, str):
        raise TypeError("Input harus berupa string.")
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)*", text.lower(), flags=re.UNICODE)
