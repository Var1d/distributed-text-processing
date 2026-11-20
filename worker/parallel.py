from concurrent.futures import ProcessPoolExecutor
from processing.tokenizer import tokenize
from processing.frequency import count_words


def _count_chunk(text_chunk):
    tokens = tokenize(text_chunk)
    return count_words(tokens)


def split_text(text: str, number_of_chunks: int) -> list[str]:
    words = text.split()

    if not words:
        return []

    number_of_chunks = max(1, min(number_of_chunks, len(words)))

    chunk_size = (len(words) + number_of_chunks - 1) // number_of_chunks

    chunks = []

    for start in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[start : start + chunk_size]))

    return chunks


def parallel_count_words(text: str, processes: int | None = None) -> dict:
    """
    Menghitung frekuensi kata menggunakan multiprocessing.
    """

    if not isinstance(text, str):
        raise TypeError("Text harus berupa string.")

    if processes is None:
        import os

        processes = os.cpu_count() or 1

    if isinstance(processes, bool) or not isinstance(processes, int):
        raise TypeError("Processes harus berupa integer.")

    if processes < 1:
        raise ValueError("Processes minimal 1.")

    chunks = split_text(text, processes)

    if not chunks:
        return {}

    if processes == 1 or len(chunks) == 1:
        return _count_chunk(chunks[0])

    with ProcessPoolExecutor(max_workers=processes) as executor:
        partial_results = list(executor.map(_count_chunk, chunks))

    total_frequency = {}

    for partial in partial_results:
        for word, count in partial.items():
            total_frequency[word] = total_frequency.get(word, 0) + count

    return total_frequency
