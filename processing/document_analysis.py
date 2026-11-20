from processing.tokenizer import tokenize
from processing.frequency import count_words, get_most_common


def analyze_document(document_id: str, text: str, top_n: int = 10) -> dict:
    """
    Menganalisis dokumen teks secara sequential.
    """

    if not isinstance(document_id, str) or not document_id:
        raise ValueError("Document ID tidak valid.")

    if not isinstance(text, str):
        raise TypeError("Isi dokumen harus berupa string.")

    if isinstance(top_n, bool) or not isinstance(top_n, int):
        raise TypeError("top_n harus berupa integer.")

    if top_n < 0:
        raise ValueError("top_n tidak boleh negatif.")

    tokens = tokenize(text)
    frequencies = count_words(tokens)

    return {
        "document_id": document_id,
        "total_words": len(tokens),
        "unique_words": len(frequencies),
        "word_frequency": frequencies,
        "most_common": [
            [word, count] for word, count in get_most_common(frequencies, top_n)
        ],
    }
